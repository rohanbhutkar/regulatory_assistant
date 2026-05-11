"""
Healthcare Analytics Agent
Combines claims and payer data for comprehensive healthcare analytics
"""
import asyncio
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from config import settings
from utils.logger import log_error
from models.schemas import AnalyticsResult, CostAnalysisResult, UtilizationResult
import logging

logger = logging.getLogger(__name__)

class HealthcareAnalyticsAgent:
    def __init__(self):
        self.claims_agent = None
        self.payer_agent = None
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize the claims and payer data agents"""
        try:
            from agents.claims_data_agent import claims_data_agent
            from agents.payer_data_agent import payer_data_agent
            
            self.claims_agent = claims_data_agent
            self.payer_agent = payer_data_agent
            
            logger.info("Healthcare Analytics Agent initialized successfully")
            
        except Exception as e:
            log_error(e, "Failed to initialize Healthcare Analytics Agent")
            raise
    
    async def analyze_drug_utilization(self, query: str, max_results: int = 50) -> List[UtilizationResult]:
        """Analyze drug utilization patterns combining claims and sales data"""
        try:
            query_lower = query.lower()
            results = []
            
            # Extract drug terms from query
            drug_terms = self._extract_drug_terms(query)
            
            if not drug_terms:
                return results
            
            # Get prescription data from claims (using available methods)
            # Since search_prescriptions doesn't exist, we'll use search_diagnoses for drug-related queries
            prescriptions = await self.claims_agent.search_diagnoses(query, max_results)
            
            # Get sales data from payer data (check if method exists)
            sales_data = []
            if hasattr(self.payer_agent, 'search_sales_data'):
                sales_data = await self.payer_agent.search_sales_data(query, max_results)
            elif hasattr(self.payer_agent, 'search_products'):
                sales_data = await self.payer_agent.search_products(query)
            
            # Combine and analyze
            for prescription in prescriptions:
                # Since we're using search_diagnoses, adapt the data structure
                if isinstance(prescription, dict):
                    # Extract relevant information from diagnosis data
                    drug_name = str(prescription.get('diagnosis_code', 'Unknown Drug'))
                    ndc = str(prescription.get('diagnosis_code', 'Unknown NDC'))
                    
                    # Find matching sales data
                    matching_sales = [s for s in sales_data if hasattr(s, 'product_id') and s.product_id == ndc]
                    
                    utilization_data = {
                        'drug_name': drug_name,
                        'ndc': ndc,
                        'total_prescriptions': int(prescription.get('total_claims', 0)),
                        'average_days_supply': int(prescription.get('avg_days_supply', 30)),
                        'average_quantity': int(prescription.get('avg_quantity', 1)),
                        'total_allowed_amount': float(prescription.get('total_allowed_amount', 0)),
                        'total_paid_amount': float(prescription.get('total_paid_amount', 0)),
                        'copay_amount': float(prescription.get('copay_amount', 0)),
                        'metadata': {
                            'source': 'healthcare_analytics',
                            'analysis_type': 'drug_utilization',
                            'query': query,
                            'data_source': 'claims_diagnoses'
                        }
                    }
                    
                    # Add sales data if available
                    if matching_sales:
                        utilization_data['sales_data'] = matching_sales[0]
                    
                    results.append(UtilizationResult(**utilization_data))
            
            return results
            
        except Exception as e:
            log_error(e, f"Drug utilization analysis failed for query: {query}")
            return []
    
    async def analyze_cost_trends(self, query: str, max_results: int = 50) -> List[CostAnalysisResult]:
        """Analyze cost trends across different dimensions"""
        try:
            query_lower = query.lower()
            results = []
            
            # Analyze by region
            if 'region' in query_lower or 'geographic' in query_lower:
                cost_data = await self.claims_agent.get_cost_analysis(query, max_results)
                
                for cost_item in cost_data:
                    results.append(CostAnalysisResult(
                        dimension='region',
                        dimension_value=cost_item.get('region', ''),
                        average_allowed_amount=cost_item.get('average_allowed_amount', 0),
                        average_paid_amount=cost_item.get('average_paid_amount', 0),
                        total_providers=cost_item.get('total_providers', 0),
                        total_payers=cost_item.get('total_payers', 0),
                        metadata=cost_item.get('metadata', {})
                    ))
            
            # Analyze by payer type
            elif 'payer' in query_lower or 'insurance' in query_lower:
                enrollment_data = await self.claims_agent.get_enrollment_analysis(query, max_results)
                
                for enrollment_item in enrollment_data:
                    results.append(CostAnalysisResult(
                        dimension='payer_type',
                        dimension_value=enrollment_item.get('payer_type', ''),
                        average_allowed_amount=0,  # Not available in enrollment data
                        average_paid_amount=0,
                        total_providers=0,
                        total_payers=enrollment_item.get('enrollment_count', 0),
                        metadata=enrollment_item.get('metadata', {})
                    ))
            
            # Analyze by procedure
            elif 'procedure' in query_lower or 'cpt' in query_lower:
                cost_data = await self.claims_agent.get_cost_analysis(query, max_results)
                
                for cost_item in cost_data:
                    results.append(CostAnalysisResult(
                        dimension='procedure',
                        dimension_value=cost_item.get('procedure_code', ''),
                        average_allowed_amount=cost_item.get('average_allowed_amount', 0),
                        average_paid_amount=cost_item.get('average_paid_amount', 0),
                        total_providers=cost_item.get('total_providers', 0),
                        total_payers=cost_item.get('total_payers', 0),
                        metadata=cost_item.get('metadata', {})
                    ))
            
            return results
            
        except Exception as e:
            log_error(e, f"Cost trends analysis failed for query: {query}")
            return []
    
    async def analyze_patient_populations(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Analyze patient populations by demographics and conditions"""
        try:
            query_lower = query.lower()
            results = []
            
            # Analyze by demographics
            if any(term in query_lower for term in ['demographic', 'age', 'gender', 'race', 'ethnicity']):
                patients = await self.claims_agent.search_patients(query, max_results)
                
                # Group by demographics
                demographics = {}
                for patient in patients:
                    key = f"{patient.gender}_{patient.race}_{patient.ethnicity}"
                    if key not in demographics:
                        demographics[key] = {
                            'gender': patient.gender,
                            'race': patient.race,
                            'ethnicity': patient.ethnicity,
                            'count': 0,
                            'age_groups': {'<18': 0, '18-65': 0, '>65': 0}
                        }
                    
                    demographics[key]['count'] += 1
                    
                    # Calculate age group
                    current_year = datetime.now().year
                    age = current_year - patient.year_of_birth
                    if age < 18:
                        demographics[key]['age_groups']['<18'] += 1
                    elif age <= 65:
                        demographics[key]['age_groups']['18-65'] += 1
                    else:
                        demographics[key]['age_groups']['>65'] += 1
                
                for demo_key, demo_data in demographics.items():
                    results.append({
                        'demographic_group': demo_key,
                        'gender': demo_data['gender'],
                        'race': demo_data['race'],
                        'ethnicity': demo_data['ethnicity'],
                        'total_count': demo_data['count'],
                        'age_distribution': demo_data['age_groups'],
                        'metadata': {'source': 'healthcare_analytics'}
                    })
            
            # Analyze by conditions
            elif any(term in query_lower for term in ['condition', 'disease', 'diagnosis']):
                diagnoses = await self.claims_agent.search_diagnoses(query, max_results)
                
                # Group by diagnosis
                diagnosis_groups = {}
                for diagnosis in diagnoses:
                    code = diagnosis['diagnosis_code']
                    if code not in diagnosis_groups:
                        diagnosis_groups[code] = {
                            'diagnosis_code': code,
                            'diagnosis_description': diagnosis['diagnosis_description'],
                            'count': 0,
                            'primary_count': 0,
                            'admit_count': 0
                        }
                    
                    diagnosis_groups[code]['count'] += 1
                    if diagnosis['primary_indicator'] == 'Y':
                        diagnosis_groups[code]['primary_count'] += 1
                    if diagnosis['admit_indicator'] == 'Y':
                        diagnosis_groups[code]['admit_count'] += 1
                
                for code, group_data in diagnosis_groups.items():
                    results.append({
                        'diagnosis_code': code,
                        'diagnosis_description': group_data['diagnosis_description'],
                        'total_count': group_data['count'],
                        'primary_count': group_data['primary_count'],
                        'admit_count': group_data['admit_count'],
                        'metadata': {'source': 'healthcare_analytics'}
                    })
            
            return results
            
        except Exception as e:
            log_error(e, f"Patient population analysis failed for query: {query}")
            return []
    
    async def analyze_market_opportunities(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Analyze market opportunities by combining sales and utilization data"""
        try:
            query_lower = query.lower()
            results = []
            
            # Analyze by therapeutic area
            if 'therapeutic' in query_lower or 'market' in query_lower:
                market_data = await self.payer_agent.get_market_analysis(query, max_results)
                
                for market_item in market_data:
                    # Get utilization data for this therapeutic area
                    utilization_query = f"therapeutic area {market_item.get('therapeutic_area_name', '')}"
                    utilization_data = await self.analyze_drug_utilization(utilization_query, max_results)
                    
                    results.append({
                        'therapeutic_area_id': market_item.get('therapeutic_area_id', ''),
                        'therapeutic_area_name': market_item.get('therapeutic_area_name', ''),
                        'product_count': market_item.get('product_count', 0),
                        'utilization_count': len(utilization_data),
                        'market_opportunity_score': self._calculate_market_opportunity_score(
                            market_item.get('product_count', 0),
                            len(utilization_data)
                        ),
                        'metadata': {'source': 'healthcare_analytics'}
                    })
            
            # Analyze competitive landscape
            elif 'competitive' in query_lower or 'competitor' in query_lower:
                competitive_data = await self.payer_agent.get_competitive_analysis(query, max_results)
                
                for comp_item in competitive_data:
                    results.append({
                        'therapeutic_area_id': comp_item.get('therapeutic_area_id', ''),
                        'therapeutic_area_name': comp_item.get('therapeutic_area_name', ''),
                        'competitor_count': comp_item.get('competitor_count', 0),
                        'competitive_intensity': self._calculate_competitive_intensity(
                            comp_item.get('competitor_count', 0)
                        ),
                        'metadata': {'source': 'healthcare_analytics'}
                    })
            
            return results
            
        except Exception as e:
            log_error(e, f"Market opportunity analysis failed for query: {query}")
            return []
    
    def _calculate_market_opportunity_score(self, product_count: int, utilization_count: int) -> float:
        """Calculate market opportunity score based on product count and utilization"""
        if product_count == 0:
            return 0.0
        
        # Simple scoring: higher utilization relative to products = higher opportunity
        utilization_ratio = utilization_count / product_count if product_count > 0 else 0
        return min(utilization_ratio / 10.0, 1.0)  # Normalize to 0-1 scale
    
    def _calculate_competitive_intensity(self, competitor_count: int) -> str:
        """Calculate competitive intensity based on competitor count"""
        if competitor_count == 0:
            return "Low"
        elif competitor_count <= 3:
            return "Medium"
        elif competitor_count <= 7:
            return "High"
        else:
            return "Very High"
    
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

# Create global instance
healthcare_analytics_agent = HealthcareAnalyticsAgent()


