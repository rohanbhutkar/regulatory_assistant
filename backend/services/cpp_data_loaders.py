"""
CPP Data Loaders
Load reference data from CSV files for CPP calculations
"""

import pandas as pd
import os
from typing import List, Dict, Optional
from decimal import Decimal
from pathlib import Path
import logging

from models.cpp_models import (
    Procedure, ProcedureCategory,
    SPUProcedure, SPUPrice,
    Rule, RuleType, RuleAction
)

logger = logging.getLogger(__name__)

# Base path for CPP data
CPP_DATA_PATH = Path(__file__).parent.parent / "data" / "cpp"


class CPPDataLoader:
    """Load all CPP reference data from CSV files"""
    
    def __init__(self):
        self.clinical_procedures: Dict[str, Procedure] = {}
        self.spu_procedures: Dict[str, SPUProcedure] = {}
        self.spu_prices: Dict[tuple, SPUPrice] = {}  # (code, country) -> price
        self.rules: Dict[str, Rule] = {}
        self._loaded = False
    
    def load_all(self):
        """Load all reference data"""
        if self._loaded:
            return
        
        logger.info("Loading CPP reference data...")
        self.load_clinical_procedures()
        self.load_spu_data()
        self.load_rules()
        self._loaded = True
        logger.info("✅ CPP reference data loaded successfully")
    
    def load_clinical_procedures(self):
        """Load clinical procedures from Reference_Clinical_Procedures_2025_Q2.csv"""
        file_path = CPP_DATA_PATH / "clinical_procedures" / "Reference_Clinical_Procedures_2025_Q2.csv"
        
        if not file_path.exists():
            logger.warning(f"Clinical procedures file not found: {file_path}")
            return
        
        logger.info(f"Loading clinical procedures from {file_path}...")
        
        try:
            df = pd.read_csv(file_path)
            
            for _, row in df.iterrows():
                # Use safe column access with case-insensitive fallbacks
                code_col = 'CPT_CODE' if 'CPT_CODE' in df.columns else 'cpt_code'
                short_desc_col = 'SHORT_DESC' if 'SHORT_DESC' in df.columns else 'short_desc'
                long_desc_col = 'LONG_DESC' if 'LONG_DESC' in df.columns else 'long_desc'
                proc_level_col = 'PROCEDURE_LEVEL' if 'PROCEDURE_LEVEL' in df.columns else 'procedure_level'
                proc_group_col = 'PROC_GROUP' if 'PROC_GROUP' in df.columns else 'proc_group'
                
                code = str(row.get(code_col, '')).strip()
                if not code:
                    continue
                    
                short_desc = str(row.get(short_desc_col, '')).strip()
                long_desc = str(row.get(long_desc_col, '')).strip()
                proc_level = str(row.get(proc_level_col, 'Visit')).strip()
                proc_group = str(row.get(proc_group_col, 'Other')).strip()
                
                # Map PROC_GROUP to ProcedureCategory
                category = self._map_category(proc_group)
                
                procedure = Procedure(
                    code=code,
                    short_description=short_desc,
                    long_description=long_desc if long_desc else None,
                    category=category,
                    procedure_level=proc_level,
                    active=True
                )
                
                self.clinical_procedures[code] = procedure
            
            logger.info(f"✅ Loaded {len(self.clinical_procedures)} clinical procedures")
        
        except Exception as e:
            logger.error(f"Error loading clinical procedures: {e}")
    
    def load_spu_data(self):
        """Load SPU pricing data from Reference_SPU_All_Countries_2025.csv"""
        file_path = CPP_DATA_PATH / "spu" / "Reference_SPU_All_Countries_2025.csv"
        
        if not file_path.exists():
            logger.warning(f"SPU data file not found: {file_path}")
            return
        
        logger.info(f"Loading SPU data from {file_path}...")
        
        try:
            df = pd.read_csv(file_path)
            
            # Verify actual column names exist
            cpt_code_col = 'CPT_CODE' if 'CPT_CODE' in df.columns else None
            short_desc_col = 'SHORT_DESC' if 'SHORT_DESC' in df.columns else None
            proc_group_col = 'PROC_GROUP' if 'PROC_GROUP' in df.columns else None
            
            if not cpt_code_col:
                logger.error("CPT_CODE column not found in SPU data")
                return
            
            # Group by procedure code to get procedure info
            for code in df[cpt_code_col].unique():
                code_str = str(code).strip()
                if not code_str:
                    continue
                    
                proc_data = df[df[cpt_code_col] == code].iloc[0]
                
                spu_proc = SPUProcedure(
                    code=code_str,
                    description=str(proc_data.get(short_desc_col, '')).strip() if short_desc_col else '',
                    category=str(proc_data.get(proc_group_col, 'Other')).strip() if proc_group_col else 'Other',
                    active=True
                )
                self.spu_procedures[code_str] = spu_proc
            
            # Load prices by country
            # Exclude known non-country columns
            excluded_cols = {'CPT_CODE', 'LONG_DESC', 'SHORT_DESC', 'PROCEDURE_LEVEL', 'PROC_GROUP'}
            for _, row in df.iterrows():
                code = str(row.get(cpt_code_col, '')).strip()
                if not code:
                    continue
                
                # Get all country columns (columns that are not in excluded list and contain numeric values)
                for col in df.columns:
                    if col not in excluded_cols and col != cpt_code_col:
                        if pd.notna(row[col]) and row[col] != '':
                            try:
                                price_value = float(row[col])
                                if price_value > 0:
                                    country_code = col.strip()
                                    
                                    # Determine currency from country
                                    currency = self._get_currency(country_code)
                                    
                                    spu_price = SPUPrice(
                                        procedure_code=code,
                                        country_code=country_code,
                                        local_price=Decimal(str(price_value)),
                                        currency=currency,
                                        source="SPU"
                                    )
                                    
                                    self.spu_prices[(code, country_code)] = spu_price
                            except (ValueError, TypeError):
                                pass  # Skip invalid prices
            
            logger.info(f"✅ Loaded {len(self.spu_procedures)} SPU procedures with {len(self.spu_prices)} prices")
        
        except Exception as e:
            logger.error(f"Error loading SPU data: {e}")
    
    def load_rules(self):
        """Load all rules (Golden, Country, Indication)"""
        self.load_golden_rules()
        self.load_country_rules()
        self.load_indication_rules()
    
    def load_golden_rules(self):
        """Load golden rules from Reference_Golden_Rules.csv"""
        file_path = CPP_DATA_PATH / "rules" / "Reference_Golden_Rules.csv"
        
        if not file_path.exists():
            logger.warning(f"Golden rules file not found: {file_path}")
            return
        
        logger.info(f"Loading golden rules from {file_path}...")
        
        try:
            df = pd.read_csv(file_path)
            
            for _, row in df.iterrows():
                rule_id = f"golden_{row.get('Rule_ID', len(self.rules))}"
                
                rule = Rule(
                    id=rule_id,
                    name=str(row.get('Rule_Name', '')).strip(),
                    rule_type=RuleType.GOLDEN,
                    description=str(row.get('Description', '')).strip(),
                    conditions={},  # Golden rules apply globally
                    action=self._parse_action(row.get('Action', 'add_percentage')),
                    value=float(row.get('Value', 0)),
                    priority=int(row.get('Priority', 0)),
                    active=bool(row.get('Active', True))
                )
                
                self.rules[rule_id] = rule
            
            logger.info(f"✅ Loaded {len([r for r in self.rules.values() if r.rule_type == RuleType.GOLDEN])} golden rules")
        
        except Exception as e:
            logger.error(f"Error loading golden rules: {e}")
    
    def load_country_rules(self):
        """Load country-specific rules from Reference_Country_Specifications.csv"""
        file_path = CPP_DATA_PATH / "rules" / "Reference_Country_Specifications.csv"
        
        if not file_path.exists():
            logger.warning(f"Country rules file not found: {file_path}")
            return
        
        logger.info(f"Loading country rules from {file_path}...")
        
        try:
            df = pd.read_csv(file_path)
            
            for _, row in df.iterrows():
                country = str(row.get('Country', '')).strip()
                rule_id = f"country_{country}_{len(self.rules)}"
                
                rule = Rule(
                    id=rule_id,
                    name=f"{country} - {row.get('Rule_Type', 'Adjustment')}",
                    rule_type=RuleType.COUNTRY,
                    description=str(row.get('Description', '')).strip(),
                    conditions={"country_code": country},
                    action=RuleAction.ADD_COST,
                    value=float(row.get('Amount', 0)),
                    priority=int(row.get('Priority', 0)),
                    active=bool(row.get('Active', True))
                )
                
                self.rules[rule_id] = rule
            
            logger.info(f"✅ Loaded {len([r for r in self.rules.values() if r.rule_type == RuleType.COUNTRY])} country rules")
        
        except Exception as e:
            logger.error(f"Error loading country rules: {e}")
    
    def load_indication_rules(self):
        """Load indication-specific rules from Reference_Indications_2025_Q1.csv"""
        file_path = CPP_DATA_PATH / "rules" / "Reference_Indications_2025_Q1.csv"
        
        if not file_path.exists():
            logger.warning(f"Indication rules file not found: {file_path}")
            return
        
        logger.info(f"Loading indication rules from {file_path}...")
        
        try:
            df = pd.read_csv(file_path)
            
            for _, row in df.iterrows():
                indication = str(row.get('Indication', '')).strip()
                if not indication:
                    continue
                
                rule_id = f"indication_{indication.replace(' ', '_')}_{len(self.rules)}"
                
                rule = Rule(
                    id=rule_id,
                    name=f"{indication} - {row.get('Adjustment_Type', 'Multiplier')}",
                    rule_type=RuleType.INDICATION,
                    description=str(row.get('Description', '')).strip(),
                    conditions={"indication": indication},
                    action=self._parse_action(row.get('Action', 'multiply')),
                    value=float(row.get('Value', 1.0)),
                    priority=int(row.get('Priority', 0)),
                    active=bool(row.get('Active', True))
                )
                
                self.rules[rule_id] = rule
            
            logger.info(f"✅ Loaded {len([r for r in self.rules.values() if r.rule_type == RuleType.INDICATION])} indication rules")
        
        except Exception as e:
            logger.error(f"Error loading indication rules: {e}")
    
    # Helper methods
    
    def _map_category(self, proc_group: str) -> ProcedureCategory:
        """Map PROC_GROUP to ProcedureCategory enum"""
        group_lower = proc_group.lower()
        
        if 'questionnaire' in group_lower or 'scale' in group_lower or 'assessment' in group_lower:
            return ProcedureCategory.QUESTIONNAIRES
        elif 'evaluation' in group_lower or 'management' in group_lower:
            return ProcedureCategory.EVALUATION_MANAGEMENT
        elif 'laboratory' in group_lower or 'lab' in group_lower:
            return ProcedureCategory.LABORATORY
        elif 'radiology' in group_lower or 'imaging' in group_lower:
            return ProcedureCategory.RADIOLOGY
        elif 'medicine' in group_lower:
            return ProcedureCategory.MEDICINE
        elif 'pathology' in group_lower:
            return ProcedureCategory.PATHOLOGY
        elif 'surgery' in group_lower or 'surgical' in group_lower:
            return ProcedureCategory.SURGERY
        elif 'anesthesia' in group_lower:
            return ProcedureCategory.ANESTHESIA
        else:
            return ProcedureCategory.OTHER
    
    def _get_currency(self, country_code: str) -> str:
        """Get currency code from country code"""
        currency_map = {
            'USA': 'USD', 'US': 'USD',
            'GBR': 'GBP', 'UK': 'GBP',
            'EUR': 'EUR', 'DEU': 'EUR', 'FRA': 'EUR', 'ITA': 'EUR', 'ESP': 'EUR', 'NLD': 'EUR',
            'JPN': 'JPY', 'JP': 'JPY',
            'CHN': 'CNY', 'CN': 'CNY',
            'IND': 'INR', 'IN': 'INR',
            'AUS': 'AUD', 'AU': 'AUD',
            'CAN': 'CAD', 'CA': 'CAD',
            'BRA': 'BRL', 'BR': 'BRL',
            'MEX': 'MXN', 'MX': 'MXN',
            'KOR': 'KRW', 'KR': 'KRW',
        }
        return currency_map.get(country_code, 'USD')
    
    def _parse_action(self, action_str: str) -> RuleAction:
        """Parse action string to RuleAction enum"""
        action_lower = str(action_str).lower()
        
        if 'add_cost' in action_lower or 'add cost' in action_lower:
            return RuleAction.ADD_COST
        elif 'multiply' in action_lower or 'multiplier' in action_lower:
            return RuleAction.MULTIPLY
        elif 'percentage' in action_lower or 'percent' in action_lower:
            return RuleAction.ADD_PERCENTAGE
        elif 'set' in action_lower:
            return RuleAction.SET_VALUE
        else:
            return RuleAction.ADD_COST
    
    # Query methods
    
    def get_procedure(self, code: str) -> Optional[Procedure]:
        """Get procedure by code"""
        return self.clinical_procedures.get(code)
    
    def get_spu_price(self, code: str, country: str) -> Optional[SPUPrice]:
        """Get SPU price for procedure and country"""
        return self.spu_prices.get((code, country))
    
    def get_rules_for_context(self, context: Dict[str, any]) -> List[Rule]:
        """Get applicable rules for a given context"""
        applicable_rules = []
        
        for rule in self.rules.values():
            if not rule.active:
                continue
            
            # Golden rules always apply
            if rule.rule_type == RuleType.GOLDEN:
                applicable_rules.append(rule)
                continue
            
            # Check conditions
            if self._matches_conditions(rule.conditions, context):
                applicable_rules.append(rule)
        
        # Sort by priority
        applicable_rules.sort(key=lambda r: r.priority, reverse=True)
        
        return applicable_rules
    
    def _matches_conditions(self, conditions: Dict[str, any], context: Dict[str, any]) -> bool:
        """Check if conditions match context"""
        for key, value in conditions.items():
            context_value = context.get(key)
            if context_value is None:
                return False
            
            # Case-insensitive string comparison
            if isinstance(value, str) and isinstance(context_value, str):
                if value.lower() != context_value.lower():
                    return False
            elif context_value != value:
                return False
        
        return True


# Global singleton instance
_cpp_data_loader = None

def get_cpp_data_loader() -> CPPDataLoader:
    """Get or create global CPP data loader instance"""
    global _cpp_data_loader
    if _cpp_data_loader is None:
        _cpp_data_loader = CPPDataLoader()
        _cpp_data_loader.load_all()
    return _cpp_data_loader







