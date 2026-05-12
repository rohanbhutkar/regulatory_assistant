"""
Claims Data Agent
Provides access to healthcare claims, prescription, and patient data
"""
import asyncio
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from config import settings
from utils.regulatory_data_io import read_regulatory_csv
from utils.logger import log_error
from models.schemas import ClaimsResult, PatientResult, PrescriptionResult, ProviderResult
import logging

# Import pgeocode for ZIP code geocoding
try:
    import pgeocode
except ImportError:
    pgeocode = None

logger = logging.getLogger(__name__)

class ClaimsDataAgent:
    def __init__(self):
        self.cache = {}
        self.geocoder = None  # Initialize geocoder for lazy loading
        self._load_data()
    
    def _load_data(self):
        """Load claims data into memory for fast access"""
        try:
            # Load main claims data
            self.claims_df = read_regulatory_csv("claims/combined_claims.csv", low_memory=False)
            
            logger.info(f"Loaded {len(self.claims_df)} claims from combined_claims.csv")
            
            # Create a mock diagnosis reference dataframe for compatibility
            # Extract unique diagnosis codes from the claims data
            diagnosis_codes = set()
            for col in self.claims_df.columns:
                if col.startswith('D') and col != 'DIAGNOSIS_CODE':
                    diagnosis_codes.update(self.claims_df[col].dropna().astype(str).unique())
            
            # Create mock diagnosis reference dataframe
            self.ref_diagnosis_df = pd.DataFrame({
                'icd10_code': list(diagnosis_codes),
                'short_description': [f"Condition {code}" for code in diagnosis_codes],
                'long_description': [f"Medical condition with code {code}" for code in diagnosis_codes]
            })
            
            logger.info(f"Created diagnosis reference with {len(self.ref_diagnosis_df)} codes")
            logger.info("Claims data loaded successfully")
            
        except Exception as e:
            log_error(e, "Failed to load claims data")
            raise
    
    def _create_indexes(self):
        """Create indexes for faster lookups"""
        try:
            # Create indexes for common lookups
            if hasattr(self, 'ref_diagnosis_df') and not self.ref_diagnosis_df.empty:
                self.diagnosis_index = self.ref_diagnosis_df.set_index('icd10_code')
            else:
                self.diagnosis_index = None
            
            # Note: ref_procedure_df and ref_ndc_df are not loaded from claims data
            # They would need to be loaded from separate reference files if needed
            self.procedure_index = None
            self.ndc_index = None
            
            logger.info("Indexes created successfully")
        except Exception as e:
            log_error(e, "Failed to create indexes")
    
    async def analyze_icd_codes(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Analyze ICD codes with flexible search terms and filtering"""
        try:
            query_lower = query.lower()
            results = []
            
            # Extract search terms
            search_terms = self._extract_medical_terms(query)
            
            # Search in diagnosis reference
            matching_diagnoses = self.ref_diagnosis_df[
                self.ref_diagnosis_df['short_description'].str.lower().str.contains('|'.join(search_terms), na=False) |
                self.ref_diagnosis_df['long_description'].str.lower().str.contains('|'.join(search_terms), na=False) |
                self.ref_diagnosis_df['icd10_code'].str.contains('|'.join(search_terms), na=False)
            ]
            
            if not matching_diagnoses.empty:
                # Get claims for matching diagnoses
                icd_codes = matching_diagnoses['icd10_code'].tolist()
                
                # Find diagnosis columns in claims data
                diagnosis_cols = [col for col in self.claims_df.columns if col.startswith('D') and col != 'DIAGNOSIS_CODE']
                if not diagnosis_cols:
                    diagnosis_cols = ['DIAGNOSIS_CODE'] if 'DIAGNOSIS_CODE' in self.claims_df.columns else []
                
                if not diagnosis_cols:
                    return results
                
                # Filter claims by ICD codes in any diagnosis column
                mask = pd.Series([False] * len(self.claims_df))
                for icd_code in icd_codes:
                    for col in diagnosis_cols:
                        mask |= self.claims_df[col].astype(str).str.contains(icd_code, case=False, na=False)
                
                diagnosis_claims = self.claims_df[mask]
                
                if diagnosis_claims.empty:
                    return results
                
                # Merge with diagnosis reference
                # Create a diagnosis_code column from the first matching diagnosis column
                diagnosis_claims = diagnosis_claims.copy()
                diagnosis_claims['diagnosis_code'] = None
                for col in diagnosis_cols:
                    matching_mask = diagnosis_claims[col].astype(str).isin([str(c) for c in icd_codes])
                    diagnosis_claims.loc[matching_mask, 'diagnosis_code'] = diagnosis_claims.loc[matching_mask, col].astype(str)
                
                merged = diagnosis_claims.merge(
                    matching_diagnoses[['icd10_code', 'short_description', 'long_description']], 
                    left_on='diagnosis_code', 
                    right_on='icd10_code', 
                    how='left'
                )
                
                # Group by ICD code and calculate statistics
                # Use actual column names from claims data: VISIT_ID, PATIENT_TOKEN_1, D1 (primary diagnosis)
                agg_dict = {
                    'VISIT_ID': 'count',  # Count claims
                }
                
                # Count unique patients - use PATIENT_TOKEN_1 (primary patient identifier)
                if 'PATIENT_TOKEN_1' in merged.columns:
                    agg_dict['PATIENT_TOKEN_1'] = 'nunique'
                
                # Count primary diagnoses (D1 column)
                if 'D1' in merged.columns:
                    agg_dict['D1'] = lambda x: x.notna().sum()  # Count non-null primary diagnoses
                
                # Count admissions (ADMIT_TYPE_CODE indicates admission)
                if 'ADMIT_TYPE_CODE' in merged.columns:
                    agg_dict['ADMIT_TYPE_CODE'] = lambda x: x.notna().sum()  # Count admissions
                
                grouped = merged.groupby('diagnosis_code').agg(agg_dict).reset_index()
                
                # Add description information
                grouped = grouped.merge(
                    matching_diagnoses[['icd10_code', 'short_description', 'long_description']], 
                    left_on='diagnosis_code', 
                    right_on='icd10_code', 
                    how='left'
                )
                
                for _, row in grouped.head(max_results).iterrows():
                    results.append({
                        'icd_code': row['diagnosis_code'],
                        'short_description': row.get('short_description', ''),
                        'long_description': row.get('long_description', ''),
                        'total_claims': row.get('VISIT_ID', 0),
                        'unique_patients': row.get('PATIENT_TOKEN_1', 0),
                        'primary_diagnosis_count': row.get('D1', 0),
                        'admission_count': row.get('ADMIT_TYPE_CODE', 0),
                        'metadata': {'source': 'claims_data', 'analysis_type': 'icd_codes'}
                    })
            
            return results
            
        except Exception as e:
            log_error(e, f"ICD code analysis failed for query: {query}")
            return []
    
    async def analyze_hcpcs_codes(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Analyze HCPCS codes with flexible search terms and filtering"""
        try:
            query_lower = query.lower()
            results = []
            
            # Extract search terms
            search_terms = self._extract_medical_terms(query)
            
            # Search in procedure reference for HCPCS codes
            matching_procedures = self.ref_procedure_df[
                (self.ref_procedure_df['code_qual'] == 'HCPCS') &
                (
                    self.ref_procedure_df['short_description'].str.lower().str.contains('|'.join(search_terms), na=False) |
                    self.ref_procedure_df['long_description'].str.lower().str.contains('|'.join(search_terms), na=False) |
                    self.ref_procedure_df['code'].str.contains('|'.join(search_terms), na=False)
                )
            ]
            
            if not matching_procedures.empty:
                # Get claims for matching procedures
                procedure_codes = matching_procedures['code'].tolist()
                procedure_claims = self.procedures_df[
                    self.procedures_df['procedure_code'].isin(procedure_codes)
                ]
                
                # Merge with procedure reference
                merged = procedure_claims.merge(
                    matching_procedures[['code', 'short_description', 'long_description']], 
                    left_on='procedure_code', 
                    right_on='code', 
                    how='left'
                )
                
                # Group by procedure code and calculate statistics
                grouped = merged.groupby('procedure_code').agg({
                    'visit_id': 'count',
                    'hvid': 'nunique',
                    'procedure_units': 'sum',
                    'allowed_amt_supplier': ['sum', 'mean', 'std'],
                    'paid_amt_supplier': ['sum', 'mean', 'std'],
                    'primary_ind': lambda x: (x == 'Y').sum()
                }).reset_index()
                
                # Flatten column names
                grouped.columns = ['procedure_code', 'total_claims', 'unique_patients', 'total_units', 
                                 'total_allowed', 'avg_allowed', 'std_allowed', 
                                 'total_paid', 'avg_paid', 'std_paid', 'primary_count']
                
                # Add description information
                grouped = grouped.merge(
                    matching_procedures[['code', 'short_description', 'long_description']], 
                    left_on='procedure_code', 
                    right_on='code', 
                    how='left'
                )
                
                for _, row in grouped.head(max_results).iterrows():
                    results.append({
                        'hcpcs_code': row['procedure_code'],
                        'short_description': row['short_description'],
                        'long_description': row['long_description'],
                        'total_claims': row['total_claims'],
                        'unique_patients': row['unique_patients'],
                        'total_units': row['total_units'],
                        'total_allowed_amount': row['total_allowed'],
                        'average_allowed_amount': row['avg_allowed'],
                        'total_paid_amount': row['total_paid'],
                        'average_paid_amount': row['avg_paid'],
                        'primary_procedure_count': row['primary_count'],
                        'metadata': {'source': 'claims_data', 'analysis_type': 'hcpcs_codes'}
                    })
            
            return results
            
        except Exception as e:
            log_error(e, f"HCPCS code analysis failed for query: {query}")
            return []
    
    async def analyze_cpt_codes(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Analyze CPT codes with flexible search terms and filtering"""
        try:
            query_lower = query.lower()
            results = []
            
            # Extract search terms
            search_terms = self._extract_medical_terms(query)
            
            # Search in procedure reference for CPT codes
            matching_procedures = self.ref_procedure_df[
                (self.ref_procedure_df['code_qual'] == 'CPT') &
                (
                    self.ref_procedure_df['short_description'].str.lower().str.contains('|'.join(search_terms), na=False) |
                    self.ref_procedure_df['long_description'].str.lower().str.contains('|'.join(search_terms), na=False) |
                    self.ref_procedure_df['code'].str.contains('|'.join(search_terms), na=False)
                )
            ]
            
            if not matching_procedures.empty:
                # Get claims for matching procedures
                procedure_codes = matching_procedures['code'].tolist()
                procedure_claims = self.procedures_df[
                    self.procedures_df['procedure_code'].isin(procedure_codes)
                ]
                
                # Merge with procedure reference
                merged = procedure_claims.merge(
                    matching_procedures[['code', 'short_description', 'long_description']], 
                    left_on='procedure_code', 
                    right_on='code', 
                    how='left'
                )
                
                # Group by procedure code and calculate statistics
                grouped = merged.groupby('procedure_code').agg({
                    'visit_id': 'count',
                    'hvid': 'nunique',
                    'procedure_units': 'sum',
                    'allowed_amt_supplier': ['sum', 'mean', 'std'],
                    'paid_amt_supplier': ['sum', 'mean', 'std'],
                    'primary_ind': lambda x: (x == 'Y').sum()
                }).reset_index()
                
                # Flatten column names
                grouped.columns = ['procedure_code', 'total_claims', 'unique_patients', 'total_units', 
                                 'total_allowed', 'avg_allowed', 'std_allowed', 
                                 'total_paid', 'avg_paid', 'std_paid', 'primary_count']
                
                # Add description information
                grouped = grouped.merge(
                    matching_procedures[['code', 'short_description', 'long_description']], 
                    left_on='procedure_code', 
                    right_on='code', 
                    how='left'
                )
                
                for _, row in grouped.head(max_results).iterrows():
                    results.append({
                        'cpt_code': row['procedure_code'],
                        'short_description': row['short_description'],
                        'long_description': row['long_description'],
                        'total_claims': row['total_claims'],
                        'unique_patients': row['unique_patients'],
                        'total_units': row['total_units'],
                        'total_allowed_amount': row['total_allowed'],
                        'average_allowed_amount': row['avg_allowed'],
                        'total_paid_amount': row['total_paid'],
                        'average_paid_amount': row['avg_paid'],
                        'primary_procedure_count': row['primary_count'],
                        'metadata': {'source': 'claims_data', 'analysis_type': 'cpt_codes'}
                    })
            
            return results
            
        except Exception as e:
            log_error(e, f"CPT code analysis failed for query: {query}")
            return []
    
    async def analyze_comprehensive_claims(self, query: str, filters: Dict[str, Any] = None, max_results: int = 50) -> List[Dict[str, Any]]:
        """Perform comprehensive claims analysis with flexible filtering"""
        try:
            query_lower = query.lower()
            results = []
            
            # Start with all claims
            claims_data = self.diagnosis_df.copy()
            
            # Apply filters if provided
            if filters:
                # Date range filter
                if 'date_start' in filters and 'date_end' in filters:
                    claims_data = claims_data[
                        (claims_data['date_start'] >= filters['date_start']) &
                        (claims_data['date_end'] <= filters['date_end'])
                    ]
                
                # Patient demographics filter
                if 'patient_ids' in filters:
                    claims_data = claims_data[claims_data['hvid'].isin(filters['patient_ids'])]
                
                # Primary diagnosis filter
                if filters.get('primary_only', False):
                    claims_data = claims_data[claims_data['primary_ind'] == 'Y']
                
                # Admission filter
                if filters.get('admissions_only', False):
                    claims_data = claims_data[claims_data['admit_ind'] == 'Y']
            
            # Extract search terms for diagnosis analysis
            search_terms = self._extract_medical_terms(query)
            
            if search_terms:
                # Find matching diagnoses
                matching_diagnoses = self.ref_diagnosis_df[
                    self.ref_diagnosis_df['short_description'].str.lower().str.contains('|'.join(search_terms), na=False) |
                    self.ref_diagnosis_df['long_description'].str.lower().str.contains('|'.join(search_terms), na=False) |
                    self.ref_diagnosis_df['icd10_code'].str.contains('|'.join(search_terms), na=False)
                ]
                
                if not matching_diagnoses.empty:
                    # Filter claims by matching diagnoses
                    icd_codes = matching_diagnoses['icd10_code'].tolist()
                    filtered_claims = claims_data[claims_data['diagnosis_code'].isin(icd_codes)]
                    
                    # Merge with diagnosis reference
                    merged = filtered_claims.merge(
                        matching_diagnoses[['icd10_code', 'short_description', 'long_description']], 
                        left_on='diagnosis_code', 
                        right_on='icd10_code', 
                        how='left'
                    )
                    
                    # Group by diagnosis and calculate comprehensive statistics
                    grouped = merged.groupby('diagnosis_code').agg({
                        'visit_id': 'count',
                        'hvid': 'nunique',
                        'primary_ind': lambda x: (x == 'Y').sum(),
                        'admit_ind': lambda x: (x == 'Y').sum(),
                        'date_start': ['min', 'max']
                    }).reset_index()
                    
                    # Flatten column names
                    grouped.columns = ['diagnosis_code', 'total_claims', 'unique_patients', 
                                     'primary_count', 'admission_count', 'earliest_date', 'latest_date']
                    
                    # Add description information
                    grouped = grouped.merge(
                        matching_diagnoses[['icd10_code', 'short_description', 'long_description']], 
                        left_on='diagnosis_code', 
                        right_on='icd10_code', 
                        how='left'
                    )
                    
                    # Calculate additional metrics
                    for _, row in grouped.head(max_results).iterrows():
                        # Get patient demographics for this diagnosis
                        diagnosis_patients = merged[merged['diagnosis_code'] == row['diagnosis_code']]['hvid'].unique()
                        patient_demographics = self.patients_df[self.patients_df['hvid'].isin(diagnosis_patients)]
                        
                        # Calculate age distribution
                        current_year = datetime.now().year
                        patient_demographics['age'] = current_year - patient_demographics['year_of_birth']
                        age_stats = patient_demographics['age'].describe()
                        
                        results.append({
                            'diagnosis_code': row['diagnosis_code'],
                            'short_description': row['short_description'],
                            'long_description': row['long_description'],
                            'total_claims': row['total_claims'],
                            'unique_patients': row['unique_patients'],
                            'primary_diagnosis_count': row['primary_count'],
                            'admission_count': row['admission_count'],
                            'earliest_claim_date': row['earliest_date'],
                            'latest_claim_date': row['latest_date'],
                            'age_statistics': {
                                'mean_age': age_stats['mean'],
                                'median_age': age_stats['50%'],
                                'min_age': age_stats['min'],
                                'max_age': age_stats['max'],
                                'std_age': age_stats['std']
                            },
                            'gender_distribution': patient_demographics['gender'].value_counts().to_dict(),
                            'race_distribution': patient_demographics['race'].value_counts().to_dict(),
                            'metadata': {'source': 'claims_data', 'analysis_type': 'comprehensive_claims'}
                        })
            
            return results
            
        except Exception as e:
            log_error(e, f"Comprehensive claims analysis failed for query: {query}")
            return []
    
    async def analyze_cost_patterns(self, query: str, group_by: str = 'diagnosis', max_results: int = 50) -> List[Dict[str, Any]]:
        """Analyze cost patterns by various dimensions"""
        try:
            query_lower = query.lower()
            results = []
            
            # Extract search terms
            search_terms = self._extract_medical_terms(query)
            
            if group_by == 'diagnosis':
                # Analyze costs by diagnosis
                matching_diagnoses = self.ref_diagnosis_df[
                    self.ref_diagnosis_df['short_description'].str.lower().str.contains('|'.join(search_terms), na=False) |
                    self.ref_diagnosis_df['long_description'].str.lower().str.contains('|'.join(search_terms), na=False)
                ]
                
                if not matching_diagnoses.empty:
                    icd_codes = matching_diagnoses['icd10_code'].tolist()
                    diagnosis_claims = self.diagnosis_df[self.diagnosis_df['diagnosis_code'].isin(icd_codes)]
                    
                    # Get associated procedure costs
                    visit_ids = diagnosis_claims['visit_id'].unique()
                    procedure_costs = self.procedures_df[self.procedures_df['visit_id'].isin(visit_ids)]
                    
                    # Group by diagnosis and calculate cost statistics
                    grouped = procedure_costs.groupby('visit_id').agg({
                        'allowed_amt_supplier': 'sum',
                        'paid_amt_supplier': 'sum',
                        'copaycoins_amt_supplier': 'sum',
                        'deductible_amt_supplier': 'sum'
                    }).reset_index()
                    
                    # Merge with diagnosis information
                    merged = grouped.merge(
                        diagnosis_claims[['visit_id', 'diagnosis_code']], 
                        on='visit_id', 
                        how='left'
                    )
                    
                    # Group by diagnosis code
                    diagnosis_costs = merged.groupby('diagnosis_code').agg({
                        'allowed_amt_supplier': ['sum', 'mean', 'std', 'min', 'max'],
                        'paid_amt_supplier': ['sum', 'mean', 'std'],
                        'copaycoins_amt_supplier': ['sum', 'mean'],
                        'deductible_amt_supplier': ['sum', 'mean']
                    }).reset_index()
                    
                    # Flatten column names
                    diagnosis_costs.columns = ['diagnosis_code', 'total_allowed', 'avg_allowed', 'std_allowed', 
                                            'min_allowed', 'max_allowed', 'total_paid', 'avg_paid', 
                                            'std_paid', 'total_copay', 'avg_copay', 'total_deductible', 'avg_deductible']
                    
                    # Add description information
                    diagnosis_costs = diagnosis_costs.merge(
                        matching_diagnoses[['icd10_code', 'short_description']], 
                        left_on='diagnosis_code', 
                        right_on='icd10_code', 
                        how='left'
                    )
                    
                    for _, row in diagnosis_costs.head(max_results).iterrows():
                        results.append({
                            'diagnosis_code': row['diagnosis_code'],
                            'description': row['short_description'],
                            'total_allowed_amount': row['total_allowed'],
                            'average_allowed_amount': row['avg_allowed'],
                            'cost_standard_deviation': row['std_allowed'],
                            'min_allowed_amount': row['min_allowed'],
                            'max_allowed_amount': row['max_allowed'],
                            'total_paid_amount': row['total_paid'],
                            'average_paid_amount': row['avg_paid'],
                            'total_copay_amount': row['total_copay'],
                            'average_copay_amount': row['avg_copay'],
                            'total_deductible_amount': row['total_deductible'],
                            'average_deductible_amount': row['avg_deductible'],
                            'metadata': {'source': 'claims_data', 'analysis_type': 'cost_patterns', 'group_by': group_by}
                        })
            
            elif group_by == 'procedure':
                # Analyze costs by procedure
                matching_procedures = self.ref_procedure_df[
                    self.ref_procedure_df['short_description'].str.lower().str.contains('|'.join(search_terms), na=False) |
                    self.ref_procedure_df['long_description'].str.lower().str.contains('|'.join(search_terms), na=False)
                ]
                
                if not matching_procedures.empty:
                    procedure_codes = matching_procedures['code'].tolist()
                    procedure_claims = self.procedures_df[self.procedures_df['procedure_code'].isin(procedure_codes)]
                    
                    # Group by procedure code and calculate cost statistics
                    grouped = procedure_claims.groupby('procedure_code').agg({
                        'allowed_amt_supplier': ['sum', 'mean', 'std', 'min', 'max'],
                        'paid_amt_supplier': ['sum', 'mean', 'std'],
                        'copaycoins_amt_supplier': ['sum', 'mean'],
                        'deductible_amt_supplier': ['sum', 'mean'],
                        'procedure_units': 'sum',
                        'visit_id': 'count'
                    }).reset_index()
                    
                    # Flatten column names
                    grouped.columns = ['procedure_code', 'total_allowed', 'avg_allowed', 'std_allowed', 
                                    'min_allowed', 'max_allowed', 'total_paid', 'avg_paid', 
                                    'std_paid', 'total_copay', 'avg_copay', 'total_deductible', 
                                    'avg_deductible', 'total_units', 'total_claims']
                    
                    # Add description information
                    grouped = grouped.merge(
                        matching_procedures[['code', 'short_description', 'long_description']], 
                        left_on='procedure_code', 
                        right_on='code', 
                        how='left'
                    )
                    
                    for _, row in grouped.head(max_results).iterrows():
                        results.append({
                            'procedure_code': row['procedure_code'],
                            'short_description': row['short_description'],
                            'long_description': row['long_description'],
                            'total_claims': row['total_claims'],
                            'total_units': row['total_units'],
                            'total_allowed_amount': row['total_allowed'],
                            'average_allowed_amount': row['avg_allowed'],
                            'cost_standard_deviation': row['std_allowed'],
                            'min_allowed_amount': row['min_allowed'],
                            'max_allowed_amount': row['max_allowed'],
                            'total_paid_amount': row['total_paid'],
                            'average_paid_amount': row['avg_paid'],
                            'total_copay_amount': row['total_copay'],
                            'average_copay_amount': row['avg_copay'],
                            'total_deductible_amount': row['total_deductible'],
                            'average_deductible_amount': row['avg_deductible'],
                            'metadata': {'source': 'claims_data', 'analysis_type': 'cost_patterns', 'group_by': group_by}
                        })
            
            return results
            
        except Exception as e:
            log_error(e, f"Cost patterns analysis failed for query: {query}")
            return []
    
    def _extract_medical_terms(self, query: str) -> List[str]:
        """Extract medical terms from query for flexible searching"""
        query_lower = query.lower()
        
        # Common medical terms
        medical_terms = [
            'diabetes', 'hypertension', 'cancer', 'heart', 'cardiac', 'stroke', 'cerebrovascular',
            'respiratory', 'asthma', 'copd', 'pneumonia', 'infection', 'sepsis', 'fracture',
            'surgery', 'procedure', 'therapy', 'treatment', 'diagnosis', 'condition', 'disease',
            'chronic', 'acute', 'emergency', 'trauma', 'injury', 'pain', 'depression', 'anxiety',
            'mental', 'psychiatric', 'neurological', 'neurological', 'orthopedic', 'dermatology',
            'gastroenterology', 'urology', 'gynecology', 'pediatric', 'geriatric', 'oncology'
        ]
        
        # Extract terms that appear in the query
        found_terms = [term for term in medical_terms if term in query_lower]
        
        # Also extract capitalized words that might be medical terms
        words = query.split()
        capitalized_words = [word.strip('.,!?') for word in words if word[0].isupper() and len(word) > 2]
        
        # Extract ICD/CPT/HCPCS codes (alphanumeric patterns)
        import re
        code_patterns = [
            r'\b[A-Z]\d{2,3}\b',  # ICD-10 codes like A12, B34
            r'\b\d{5}\b',         # CPT codes like 99213
            r'\b[A-Z]\d{4}\b',    # HCPCS codes like A1234
            r'\b[A-Z]{2}\d{3}\b'  # Other medical codes
        ]
        
        codes = []
        for pattern in code_patterns:
            codes.extend(re.findall(pattern, query))
        
        # Combine all terms
        all_terms = found_terms + capitalized_words[:5] + codes[:5]  # Limit to avoid too many terms
        
        return list(set(all_terms))  # Remove duplicates
    
    async def search_patients(self, query: str, max_results: int = 50) -> List[PatientResult]:
        """Search patient data based on demographics or conditions"""
        try:
            query_lower = query.lower()
            results = []
            
            # Search by demographics
            if any(term in query_lower for term in ['age', 'gender', 'race', 'ethnicity']):
                filtered_df = self.patients_df.copy()
                
                # Age filtering
                if 'age' in query_lower:
                    current_year = datetime.now().year
                    filtered_df['age'] = current_year - filtered_df['year_of_birth']
                    
                    if 'older' in query_lower or 'senior' in query_lower:
                        filtered_df = filtered_df[filtered_df['age'] >= 65]
                    elif 'young' in query_lower or 'pediatric' in query_lower:
                        filtered_df = filtered_df[filtered_df['age'] < 18]
                
                # Gender filtering
                if 'male' in query_lower:
                    filtered_df = filtered_df[filtered_df['gender'] == 'M']
                elif 'female' in query_lower:
                    filtered_df = filtered_df[filtered_df['gender'] == 'F']
                
                # Race/ethnicity filtering
                if 'white' in query_lower:
                    filtered_df = filtered_df[filtered_df['race'] == 'WHITE']
                elif 'black' in query_lower:
                    filtered_df = filtered_df[filtered_df['race'] == 'BLACK']
                elif 'hispanic' in query_lower:
                    filtered_df = filtered_df[filtered_df['ethnicity'] == 'HISPANIC']
                
                # Convert to results
                for _, row in filtered_df.head(max_results).iterrows():
                    results.append(PatientResult(
                        patient_id=row['hvid'],
                        gender=row['gender'],
                        year_of_birth=row['year_of_birth'],
                        race=row['race'],
                        ethnicity=row['ethnicity'],
                        death_indicator=row['death_ind'],
                        death_month=row['death_month'],
                        metadata={'source': 'claims_data'}
                    ))
            
            return results
            
        except Exception as e:
            log_error(e, f"Patient search failed for query: {query}")
            return []
    
    async def search_prescriptions(self, query: str, max_results: int = 50) -> List[PrescriptionResult]:
        """Search prescription data by drug name, NDC, or cost"""
        try:
            query_lower = query.lower()
            results = []
            
            # Search by drug name in NDC reference (default for drug names)
            drug_terms = self._extract_drug_terms(query)
            
            if drug_terms:
                # Find matching NDCs
                matching_ndcs = self.ref_ndc_df[
                    self.ref_ndc_df['proprietary_name'].str.lower().str.contains('|'.join(drug_terms), na=False) |
                    self.ref_ndc_df['nonproprietary_name'].str.lower().str.contains('|'.join(drug_terms), na=False)
                ]
                
                if not matching_ndcs.empty:
                    # Get prescriptions for matching NDCs
                    # Convert NDC to string for comparison since ref_ndc has string NDCs
                    ndc_list = matching_ndcs['ndc'].astype(str).tolist()
                    prescription_matches = self.prescriptions_df[
                        self.prescriptions_df['ndc'].astype(str).isin(ndc_list)
                    ]
                    
                    # Merge with NDC reference for drug names
                    # Convert prescription NDC to string for merge
                    prescription_matches = prescription_matches.copy()
                    prescription_matches['ndc_str'] = prescription_matches['ndc'].astype(str)
                    merged = prescription_matches.merge(
                        matching_ndcs[['ndc', 'proprietary_name', 'nonproprietary_name']], 
                        left_on='ndc_str', 
                        right_on='ndc', 
                        how='left'
                    )
                    
                    # Claims data doesn't have prescription-specific columns
                    # Prescription data would need to be in a separate file
                    # For now, return empty results with a note
                    logger.warning("Prescription search not available - claims data does not contain prescription-specific columns")
                    return results
            
            return results
            
        except Exception as e:
            log_error(e, f"Prescription search failed for query: {query}")
            return []
            log_error(e, f"Prescription search failed for query: {query}")
            return []
    
    async def search_diagnoses(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Search diagnosis data by condition or ICD codes"""
        try:
            query_lower = query.lower()
            results = []
            
            # Search by condition name
            if any(term in query_lower for term in ['condition', 'disease', 'diagnosis', 'icd']):
                # Find matching diagnoses in reference
                matching_diagnoses = self.ref_diagnosis_df[
                    self.ref_diagnosis_df['short_description'].str.lower().str.contains(query_lower, na=False) |
                    self.ref_diagnosis_df['long_description'].str.lower().str.contains(query_lower, na=False)
                ]
                
                if not matching_diagnoses.empty:
                    # Get claims for matching diagnoses
                    icd_codes = matching_diagnoses['icd10_code'].tolist()
                    diagnosis_matches = self.diagnosis_df[
                        self.diagnosis_df['diagnosis_code'].isin(icd_codes)
                    ]
                    
                    # Merge with diagnosis reference
                    merged = diagnosis_matches.merge(
                        matching_diagnoses[['icd10_code', 'short_description', 'long_description']], 
                        left_on='diagnosis_code', 
                        right_on='icd10_code', 
                        how='left'
                    )
                    
                    for _, row in merged.head(max_results).iterrows():
                        results.append({
                            'visit_id': row['visit_id'],
                            'patient_id': row['hvid'],
                            'diagnosis_code': row['diagnosis_code'],
                            'diagnosis_description': row.get('short_description', ''),
                            'date_start': row['date_start'],
                            'date_end': row['date_end'],
                            'primary_indicator': row['primary_ind'],
                            'admit_indicator': row['admit_ind'],
                            'metadata': {'source': 'claims_data'}
                        })
            
            return results
            
        except Exception as e:
            log_error(e, f"Diagnosis search failed for query: {query}")
            return []
    
    async def get_cost_analysis(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Analyze healthcare costs by procedure, region, or payer type"""
        try:
            if self.market_cost_df is None:
                return []
            
            query_lower = query.lower()
            results = []
            
            # Filter by procedure code
            if 'procedure' in query_lower or 'cpt' in query_lower:
                filtered_df = self.market_cost_df.copy()
                
                # Extract procedure codes from query
                procedure_codes = self._extract_procedure_codes(query)
                if procedure_codes:
                    filtered_df = filtered_df[filtered_df['procedure_code'].isin(procedure_codes)]
                
                # Group by procedure and calculate statistics
                grouped = filtered_df.groupby('procedure_code').agg({
                    'allowed_amt_median': 'mean',
                    'paid_amt_median': 'mean',
                    'sample_providers': 'sum',
                    'sample_payers': 'sum'
                }).reset_index()
                
                for _, row in grouped.head(max_results).iterrows():
                    results.append({
                        'procedure_code': row['procedure_code'],
                        'average_allowed_amount': row['allowed_amt_median'],
                        'average_paid_amount': row['paid_amt_median'],
                        'total_providers': row['sample_providers'],
                        'total_payers': row['sample_payers'],
                        'metadata': {'source': 'claims_data'}
                    })
            
            # Filter by region
            elif any(term in query_lower for term in ['region', 'geographic', 'midwest', 'northeast', 'south', 'west']):
                filtered_df = self.market_cost_df.copy()
                
                if 'midwest' in query_lower:
                    filtered_df = filtered_df[filtered_df['census_region'] == 'MIDWEST']
                elif 'northeast' in query_lower:
                    filtered_df = filtered_df[filtered_df['census_region'] == 'NORTHEAST']
                elif 'south' in query_lower:
                    filtered_df = filtered_df[filtered_df['census_region'] == 'SOUTH']
                elif 'west' in query_lower:
                    filtered_df = filtered_df[filtered_df['census_region'] == 'WEST']
                
                # Group by region and calculate statistics
                grouped = filtered_df.groupby('census_region').agg({
                    'allowed_amt_median': 'mean',
                    'paid_amt_median': 'mean',
                    'sample_providers': 'sum',
                    'sample_payers': 'sum'
                }).reset_index()
                
                for _, row in grouped.head(max_results).iterrows():
                    results.append({
                        'region': row['census_region'],
                        'average_allowed_amount': row['allowed_amt_median'],
                        'average_paid_amount': row['paid_amt_median'],
                        'total_providers': row['sample_providers'],
                        'total_payers': row['sample_payers'],
                        'metadata': {'source': 'claims_data'}
                    })
            
            return results
            
        except Exception as e:
            log_error(e, f"Cost analysis failed for query: {query}")
            return []
    
    async def analyze_patient_population(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Analyze patient population demographics"""
        try:
            logger.info(f"Analyzing patient population for query: {query}")
            
            # Extract demographic criteria from query
            age_range = None
            gender_preference = None
            
            if 'age_range' in query.lower():
                # Extract age range from query
                import re
                age_match = re.search(r'age[:\s]*(\d+)-(\d+)', query.lower())
                if age_match:
                    age_range = (int(age_match.group(1)), int(age_match.group(2)))
            
            if 'gender' in query.lower():
                if 'male' in query.lower() and 'female' not in query.lower():
                    gender_preference = 'male'
                elif 'female' in query.lower() and 'male' not in query.lower():
                    gender_preference = 'female'
                else:
                    gender_preference = 'both'
            
            # Filter claims based on demographics
            filtered_df = self.claims_df.copy()
            
            if age_range:
                # Filter by age using DOB if available
                if 'PATIENT_DOB' in self.claims_df.columns:
                    # Calculate age from DOB (simplified)
                    import datetime
                    current_year = datetime.datetime.now().year
                    filtered_df['AGE'] = current_year - pd.to_datetime(filtered_df['PATIENT_DOB'], errors='coerce').dt.year
                    filtered_df = filtered_df[
                        (filtered_df['AGE'] >= age_range[0]) & 
                        (filtered_df['AGE'] <= age_range[1])
                    ]
            
            if gender_preference and gender_preference != 'both':
                # Filter by gender using correct column name
                if 'PATIENT_GENDER' in self.claims_df.columns:
                    filtered_df = filtered_df[filtered_df['PATIENT_GENDER'] == gender_preference]
            
            # Get unique patients
            if 'PATIENT_TOKEN_1' in filtered_df.columns:
                unique_patients = filtered_df['PATIENT_TOKEN_1'].nunique()
            else:
                unique_patients = len(filtered_df)
            
            # Return demographic analysis
            results = [{
                'query': query,
                'total_patients': unique_patients,
                'age_range': age_range,
                'gender_preference': gender_preference,
                'filtered_claims_count': len(filtered_df),
                'demographics': {
                    'age_range': age_range,
                    'gender_preference': gender_preference,
                    'total_unique_patients': unique_patients
                }
            }]
            
            logger.info(f"Found {unique_patients} unique patients matching demographics")
            return results[:max_results]
            
        except Exception as e:
            log_error(e, f"Failed to analyze patient population for query: {query}")
            return []

    async def get_enrollment_analysis(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Analyze enrollment data by payer type, benefit type, or region"""
        try:
            query_lower = query.lower()
            results = []
            
            # Use claims data instead of enrollment_df (which doesn't exist)
            # Analyze by payer type if payer columns exist
            if any(term in query_lower for term in ['payer', 'insurance', 'commercial', 'medicare', 'medicaid']):
                # Use the correct payer column names
                if 'INSURANCE_TYPE_CODE' in self.claims_df.columns:
                    payer_col = 'INSURANCE_TYPE_CODE'
                elif 'PAYMENT_TYPE' in self.claims_df.columns:
                    payer_col = 'PAYMENT_TYPE'
                else:
                    payer_col = None
                
                if payer_col:
                    # Use available columns for aggregation
                    agg_dict = {}
                    if 'PATIENT_TOKEN_1' in self.claims_df.columns:
                        agg_dict['PATIENT_TOKEN_1'] = 'nunique'
                    else:
                        # Use first column as fallback
                        agg_dict[self.claims_df.columns[0]] = 'count'
                    
                    payer_analysis = self.claims_df.groupby(payer_col).agg(agg_dict).reset_index()
                    
                    # Rename columns based on what we actually have
                    if len(payer_analysis.columns) == 2:
                        payer_analysis.columns = ['payer_type', 'unique_patients']
                        payer_analysis['total_claims'] = payer_analysis['unique_patients']  # Use same value
                    else:
                        payer_analysis.columns = ['payer_type', 'unique_patients', 'total_claims']
                    
                    payer_analysis = payer_analysis.sort_values('unique_patients', ascending=False)
                    
                    for _, row in payer_analysis.head(max_results).iterrows():
                        results.append({
                            'query': query,
                            'analysis_type': 'payer_type',
                            'payer_type': row['payer_type'],
                            'unique_patients': int(row['unique_patients']),
                            'total_claims': int(row['total_claims']),
                            'enrollment_metrics': {
                                'payer_type': row['payer_type'],
                                'unique_patients': int(row['unique_patients']),
                                'total_claims': int(row['total_claims'])
                            }
                        })
                else:
                    # Fallback: return basic analysis
                    results.append({
                        'query': query,
                        'analysis_type': 'payer_type',
                        'payer_type': 'Unknown',
                        'unique_patients': self.claims_df['PATIENT_TOKEN_1'].nunique() if 'PATIENT_TOKEN_1' in self.claims_df.columns else len(self.claims_df),
                        'total_claims': len(self.claims_df),
                        'enrollment_metrics': {
                            'payer_type': 'Unknown',
                            'unique_patients': self.claims_df['PATIENT_TOKEN_1'].nunique() if 'PATIENT_TOKEN_1' in self.claims_df.columns else len(self.claims_df),
                            'total_claims': len(self.claims_df)
                        }
                    })
            
            # Search by region using ZIP codes
            if any(term in query_lower for term in ['region', 'state', 'geographic']):
                # Extract ZIP codes and group by state (first 2 digits)
                if 'BILLING_ADR_ZIP' in self.claims_df.columns:
                    zip_data = self.claims_df['BILLING_ADR_ZIP'].dropna().astype(str)
                    # Extract first 2 digits as state approximation
                    zip_data = zip_data[zip_data.str.len() >= 2]
                    zip_data = zip_data.str[:2]
                    
                    region_analysis = zip_data.value_counts().reset_index()
                    region_analysis.columns = ['state_code', 'total_claims']
                    
                    for _, row in region_analysis.head(max_results).iterrows():
                        results.append({
                            'query': query,
                            'analysis_type': 'region',
                            'state_code': row['state_code'],
                            'unique_patients': int(row['total_claims']),  # Approximate
                            'total_claims': int(row['total_claims']),
                            'enrollment_metrics': {
                                'state_code': row['state_code'],
                                'unique_patients': int(row['total_claims']),
                                'total_claims': int(row['total_claims'])
                            }
                        })
            
            logger.info(f"Enrollment analysis completed: {len(results)} results")
            return results[:max_results]
            
        except Exception as e:
            log_error(e, f"Enrollment analysis failed for query: {query}")
            return []
    
    def _extract_drug_terms(self, query: str) -> List[str]:
        """Extract drug names from query"""
        # Simple drug name extraction - can be enhanced
        common_drugs = [
            'aspirin', 'metformin', 'lisinopril', 'atorvastatin', 'metoprolol',
            'omeprazole', 'simvastatin', 'losartan', 'albuterol', 'gabapentin',
            'hydrochlorothiazide', 'sertraline', 'montelukast', 'tramadol',
            'furosemide', 'amlodipine', 'prednisone', 'trazodone', 'pantoprazole'
        ]
        
        query_lower = query.lower()
        found_drugs = [drug for drug in common_drugs if drug in query_lower]
        
        # Also try to extract capitalized words that might be drug names
        words = query.split()
        capitalized_words = [word.strip('.,!?') for word in words if word[0].isupper() and len(word) > 3]
        
        return found_drugs + capitalized_words[:3]  # Limit to avoid too many terms
    
    def _extract_procedure_codes(self, query: str) -> List[str]:
        """Extract procedure codes from query"""
        import re
        # Look for CPT codes (5-digit numbers)
        cpt_pattern = r'\b\d{5}\b'
        codes = re.findall(cpt_pattern, query)
        return codes

    async def analyze_geographic_distribution(self, therapeutic_area: str = 'general', max_results: int = 100) -> Dict[str, Any]:
        """Analyze geographic distribution of patients and claims"""
        try:
            results = {
                'zip_code_data': [],
                'state_data': [],
                'county_data': []
            }
            
            # Analyze by billing address ZIP codes (ZIP+4 format) - DEDUPLICATED BY PATIENT
            if 'BILLING_ADR_ZIP' in self.claims_df.columns:
                # Convert ZIP codes to string and extract 5-digit ZIP from ZIP+4 format
                self.claims_df['BILLING_ADR_ZIP'] = self.claims_df['BILLING_ADR_ZIP'].astype(str)
                
                # Extract 5-digit ZIP codes from ZIP+4 format (9 digits) or 8-digit format
                def extract_zip_5(zip_val):
                    if pd.isna(zip_val) or zip_val == 'nan':
                        return None
                    zip_str = str(int(float(zip_val))) if str(zip_val).replace('.', '').isdigit() else str(zip_val)
                    if len(zip_str) == 9 and zip_str.isdigit():
                        return zip_str[:5]  # Extract first 5 digits from 9-digit ZIP+4
                    elif len(zip_str) == 8 and zip_str.isdigit():
                        return zip_str[:5]  # Extract first 5 digits from 8-digit ZIP
                    elif len(zip_str) == 5 and zip_str.isdigit():
                        return zip_str  # Already 5 digits
                    return None
                
                self.claims_df['ZIP_5_DIGIT'] = self.claims_df['BILLING_ADR_ZIP'].apply(extract_zip_5)
                
                # Deduplicate by patient to avoid counting same patient multiple times
                if 'PATIENT_TOKEN_1' in self.claims_df.columns:
                    # Get unique patients per ZIP code
                    unique_patients_by_zip = self.claims_df[
                        (self.claims_df['ZIP_5_DIGIT'].notna()) & 
                        (self.claims_df['ZIP_5_DIGIT'] != '00000') &
                        (self.claims_df['PATIENT_TOKEN_1'].notna())
                    ].groupby('ZIP_5_DIGIT')['PATIENT_TOKEN_1'].nunique()
                    
                    # Scale to US population (approximately 331 million) - MORE AGGRESSIVE SCALING
                    us_population = 331_000_000
                    total_unique_patients = self.claims_df['PATIENT_TOKEN_1'].nunique()
                    scaling_factor = us_population / total_unique_patients
                    
                    logger.info(f"Scaling population data: {total_unique_patients} unique patients -> {us_population:,} US population (factor: {scaling_factor:.1f})")
                    
                    # Get ALL ZIP codes with unique patients - no limit
                    # Include every ZIP code that has at least 1 unique patient
                    sorted_zips = sorted(unique_patients_by_zip.items(), key=lambda x: x[1], reverse=True)
                    
                    logger.info(f"Found {len(sorted_zips)} ZIP codes with unique patients")
                    
                    for zip_code, unique_patient_count in sorted_zips:
                        # Scale patient count to represent US population - MORE AGGRESSIVE SCALING
                        scaled_patient_count = int(unique_patient_count * scaling_factor)
                        # Estimate population for ZIP code - MORE REALISTIC NUMBERS
                        # ZIP codes typically have 5K-50K people, so use more aggressive scaling
                        estimated_population = max(scaled_patient_count // 50, 5000)  # Divide by 50 instead of 100 for darker bubbles
                        density = estimated_population / 500  # More aggressive density calculation for darker visualization
                        
                        # Get coordinates for this ZIP code using pgeocode
                        coordinates = self.get_zip_coordinates(str(zip_code))
                        
                        results['zip_code_data'].append({
                            'zip_code': str(zip_code),
                            'population': estimated_population,
                            'patient_count': unique_patient_count,  # Store original patient count, not scaled
                            'density': density,
                            'coordinates': coordinates,
                            'demographics': {
                                'therapeutic_area': therapeutic_area,
                                'unique_patients': unique_patient_count,
                                'scaling_factor': scaling_factor
                            }
                        })
                else:
                    # Fallback if no patient identifier available
                    valid_zips = self.claims_df[
                        (self.claims_df['ZIP_5_DIGIT'].notna()) & 
                        (self.claims_df['ZIP_5_DIGIT'] != '00000')
                    ]
                    
                    if len(valid_zips) > 0:
                        zip_dist = valid_zips['ZIP_5_DIGIT'].value_counts().head(max_results)
                        
                        for zip_code, count in zip_dist.items():
                            # Scale to US population (more conservative scaling)
                            us_population = 331_000_000
                            total_claims = len(self.claims_df)
                            scaling_factor = us_population / total_claims
                            
                            scaled_patient_count = int(count * scaling_factor)
                            estimated_population = max(scaled_patient_count, 5000)  # At least 5K people per ZIP
                            density = estimated_population / 1000  # More realistic density calculation
                            
                            # Get coordinates for this ZIP code using pgeocode
                            coordinates = self.get_zip_coordinates(str(zip_code))
                            
                            results['zip_code_data'].append({
                                'zip_code': str(zip_code),
                                'population': estimated_population,
                                'patient_count': scaled_patient_count,
                                'density': density,
                                'coordinates': coordinates,
                                'demographics': {
                                    'therapeutic_area': therapeutic_area,
                                    'claim_count': count,
                                    'scaling_factor': scaling_factor
                                }
                            })
            
            return results
            
        except Exception as e:
            log_error(e, f"Geographic distribution analysis failed for query: {therapeutic_area}")
            return {'zip_code_data': [], 'state_data': [], 'county_data': []}

    def get_zip_coordinates(self, zip_code: str) -> Dict[str, float]:
        """Get coordinates for a ZIP code using pgeocode"""
        try:
            # Lazy initialization of pgeocode
            if self.geocoder is None:
                try:
                    self.geocoder = pgeocode.Nominatim('us')
                    logger.info("pgeocode initialized successfully")
                except Exception as e:
                    logger.warning(f"Failed to initialize pgeocode: {e}")
                    logger.info("Falling back to approximation method")
                    return self._get_zip_coordinates_approximation(zip_code)
            
            # Query pgeocode for coordinates
            result = self.geocoder.query_postal_code(zip_code)
            
            if result is not None and not pd.isna(result.latitude) and not pd.isna(result.longitude):
                return {
                    'lat': float(result.latitude),
                    'lng': float(result.longitude)
                }
            else:
                logger.info(f"No coordinates found for ZIP {zip_code} in pgeocode database (likely PO Box or newer ZIP), using regional approximation")
                return self._get_zip_coordinates_approximation(zip_code)
                
        except Exception as e:
            logger.warning(f"pgeocode query failed for ZIP {zip_code}: {e}")
            return self._get_zip_coordinates_approximation(zip_code)

    def _get_zip_coordinates_approximation(self, zip_code: str) -> Dict[str, float]:
        """Fallback method to approximate ZIP code coordinates"""
        try:
            # Simple approximation based on ZIP code patterns
            zip_num = int(zip_code[:3])
            
            # Rough geographic mapping of ZIP code prefixes
            if zip_num >= 100 and zip_num <= 149:  # NYC area
                return {'lat': 40.7128, 'lng': -74.0060}
            elif zip_num >= 200 and zip_num <= 209:  # DC area
                return {'lat': 38.9072, 'lng': -77.0369}
            elif zip_num >= 210 and zip_num <= 219:  # Maryland
                return {'lat': 39.0458, 'lng': -76.6413}  # Baltimore
            elif zip_num >= 220 and zip_num <= 229:  # Virginia (including 22986)
                return {'lat': 38.2911, 'lng': -78.1222}  # Woodberry Forest area
            elif zip_num >= 230 and zip_num <= 299:  # Rest of VA/MD/DC
                return {'lat': 37.5407, 'lng': -77.4360}  # Richmond, VA
            elif zip_num >= 300 and zip_num <= 399:  # Southeast
                return {'lat': 33.7490, 'lng': -84.3880}  # Atlanta
            elif zip_num >= 400 and zip_num <= 499:  # Kentucky/Indiana
                return {'lat': 38.2527, 'lng': -85.7585}  # Louisville
            elif zip_num >= 500 and zip_num <= 599:  # Iowa/Minnesota
                return {'lat': 44.9778, 'lng': -93.2650}  # Minneapolis
            elif zip_num >= 600 and zip_num <= 699:  # Illinois/Wisconsin
                return {'lat': 41.8781, 'lng': -87.6298}  # Chicago
            elif zip_num >= 700 and zip_num <= 799:  # Louisiana/Arkansas
                return {'lat': 29.9511, 'lng': -90.0715}  # New Orleans
            elif zip_num >= 800 and zip_num <= 899:  # Colorado/Wyoming
                return {'lat': 39.7392, 'lng': -104.9903}  # Denver
            elif zip_num >= 900 and zip_num <= 999:  # California/Nevada
                return {'lat': 34.0522, 'lng': -118.2437}  # Los Angeles
            else:
                return {'lat': 39.8283, 'lng': -98.5795}  # Center of US
        except:
            return {'lat': 39.8283, 'lng': -98.5795}  # Default to center of US

# Create global instance (single copy — full combined_claims is multi-GB in RAM)
claims_data_agent = ClaimsDataAgent()

