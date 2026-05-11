"""
Payer Data Service - Unified service for payer data matching, search, retrieval, and coordination
Provides LLM-accessible interfaces for comprehensive payer data operations
"""
from typing import Dict, Any, Optional, List, Union
import pandas as pd
import numpy as np
from utils.optimized_data_loader import OptimizedDataLoader


class PayerDataService:
    """
    Unified service for payer data operations across the entire system.
    Implements comprehensive matching strategies and provides LLM-accessible interfaces.
    """
    
    def __init__(self, data_loader: Optional[OptimizedDataLoader] = None):
        self.data_loader = data_loader or OptimizedDataLoader()
        self._cache = {}
    
    # ============================================================================
    # CORE DATA RETRIEVAL METHODS
    # ============================================================================
    
    def get_formulary_data(self) -> pd.DataFrame:
        """Get formulary tier data"""
        return self.data_loader.get_formulary_tier_data()
    
    def get_product_brand_data(self) -> pd.DataFrame:
        """Get product brand dimension data"""
        return self.data_loader.get_product_brand_data()
    
    def get_product_ndc_data(self) -> pd.DataFrame:
        """Get product NDC dimension data"""
        return self.data_loader.get_payer_data("Productndc_Dim")
    
    def get_therapeutic_area_data(self) -> pd.DataFrame:
        """Get therapeutic area dimension data"""
        return self.data_loader.get_therapeutic_area_data()
    
    def get_payer_plan_data(self) -> pd.DataFrame:
        """Get payer plan dimension data"""
        return self.data_loader.get_payer_data("Payer_Plan_Dim")
    
    def get_payer_plans_claims_data(self) -> pd.DataFrame:
        """Get payer plans claims fact data"""
        return self.data_loader.get_payer_data("Payer_Plans_Claims_Fact")
    
    def get_relationship_table(self, table_name: str) -> pd.DataFrame:
        """Get relationship table by name"""
        return self.data_loader.get_payer_data(table_name)
    
    # ============================================================================
    # DRUG MATCHING METHODS - Core matching logic
    # ============================================================================
    
    def find_product_by_name(
        self, 
        drug_name: str, 
        search_generic: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Find product in Productbrand_Dim by name.
        Returns product info with ProductbrandID.
        
        Args:
            drug_name: Drug name (e.g., "Zolgensma (onasemnogene abeparvovec)")
            search_generic: Whether to also search by generic name
        
        Returns:
            Dict with ProductbrandID, Productbrandname, and other product info
        """
        product_df = self.get_product_brand_data()
        if product_df.empty:
            return None
        
        # Extract drug name parts
        drug_name_clean = drug_name.split('(')[0].strip().lower()
        generic_name = None
        if '(' in drug_name and ')' in drug_name:
            generic_match = drug_name.split('(')[1].split(')')[0].strip().lower()
            if generic_match:
                generic_name = generic_match
        
        # Search strategies
        product_matches = pd.DataFrame()
        
        # Strategy 1: Bracket pattern [drugname]
        if 'Productbrandname' in product_df.columns:
            bracket_pattern = f"[{drug_name_clean}]"
            product_matches = product_df[
                product_df['Productbrandname'].astype(str).str.contains(
                    bracket_pattern, case=False, na=False, regex=False
                )
            ]
        
        # Strategy 2: Generic name
        if product_matches.empty and generic_name and search_generic:
            product_matches = product_df[
                product_df['Productbrandname'].astype(str).str.contains(
                    generic_name, case=False, na=False, regex=False
                )
            ]
        
        # Strategy 3: Brand name anywhere
        if product_matches.empty:
            product_matches = product_df[
                product_df['Productbrandname'].astype(str).str.contains(
                    drug_name_clean, case=False, na=False, regex=False
                )
            ]
        
        if product_matches.empty:
            return None
        
        # Get ProductbrandID
        product_id_col = None
        for col in product_matches.columns:
            if col.lower() == 'productbrandid':
                product_id_col = col
                break
        
        if not product_id_col:
            return None
        
        product = product_matches.iloc[0]
        product_id = product.get(product_id_col)
        
        if not product_id or pd.isna(product_id):
            return None
        
        return {
            "ProductbrandID": product_id,
            "Productbrandname": product.get('Productbrandname', drug_name),
            "drug_name": drug_name,
            "matched_name": product.get('Productbrandname', ''),
            "match_method": "bracket" if bracket_pattern in str(product.get('Productbrandname', '')).lower() else "name"
        }
    
    def get_ndc_ids_for_product(self, product_id: Union[int, str]) -> List[int]:
        """
        Get NDC IDs for a ProductbrandID via Productbrand_Productndc_Relationship_Dim
        
        Args:
            product_id: ProductbrandID
        
        Returns:
            List of ProductndcID values
        """
        try:
            ndc_rel = self.get_relationship_table("Productbrand_Productndc_Relationship_Dim")
            if ndc_rel.empty:
                return []
            
            # Find columns - check actual column names
            pb_col = None
            ndc_col = None
            for col in ndc_rel.columns:
                col_lower = col.lower()
                if 'productbrandid' in col_lower:
                    pb_col = col
                elif 'productndcid' in col_lower or ('productndc' in col_lower and 'id' in col_lower):
                    ndc_col = col
            
            if not pb_col or not ndc_col:
                return []
            
            # Get NDC IDs
            matches = ndc_rel[ndc_rel[pb_col] == product_id]
            if matches.empty:
                return []
            
            ndc_ids = matches[ndc_col].dropna().unique().tolist()
            result = [int(ndc_id) for ndc_id in ndc_ids if pd.notna(ndc_id)]
            import logging
            logger = logging.getLogger(__name__)
            if result:
                print(f"✅ Found {len(result)} NDC IDs for ProductbrandID {product_id}: {result[:5]}...")
            else:
                print(f"⚠️ No NDC IDs found for ProductbrandID {product_id}")
            return result
        except Exception as e:
            print(f"❌ Error getting NDC IDs for ProductbrandID {product_id}: {e}")
            return []
    
    def get_therapeutic_area_for_product(self, product_id: Union[int, str]) -> Optional[Dict[str, Any]]:
        """
        Get therapeutic area for a ProductbrandID via relationship tables
        
        Args:
            product_id: ProductbrandID
        
        Returns:
            Dict with TherapeuticareaID and Therapeuticareavalue
        """
        try:
            ta_rel = self.get_relationship_table("Productbrand_Therapeuticarea_Relationship_Dim")
            if ta_rel.empty:
                return None
            
            # Find columns
            pb_col = None
            ta_id_col_rel = None
            for col in ta_rel.columns:
                if col.lower() == 'productbrandid':
                    pb_col = col
                elif 'therapeuticarea' in col.lower() and 'id' in col.lower():
                    ta_id_col_rel = col
            
            if not pb_col or not ta_id_col_rel:
                return None
            
            # Get therapeutic area ID
            matches = ta_rel[ta_rel[pb_col] == product_id]
            if matches.empty:
                return None
            
            ta_id = matches.iloc[0][ta_id_col_rel]
            
            # Get therapeutic area name
            ta_dim = self.get_therapeutic_area_data()
            if ta_dim.empty:
                return None
            
            ta_id_col = None
            ta_value_col = None
            for col in ta_dim.columns:
                if 'therapeuticarea' in col.lower() and 'id' in col.lower():
                    ta_id_col = col
                elif 'therapeuticarea' in col.lower() and ('value' in col.lower() or 'name' in col.lower()):
                    ta_value_col = col
            
            if not ta_id_col or not ta_value_col:
                return None
            
            ta_info = ta_dim[ta_dim[ta_id_col] == ta_id]
            if ta_info.empty:
                return None
            
            return {
                "TherapeuticareaID": ta_id,
                "Therapeuticareavalue": ta_info.iloc[0][ta_value_col]
            }
        except Exception:
            return None
    
    # ============================================================================
    # FORMULARY MATCHING METHODS - Single strategy
    # ============================================================================
    
    def match_formulary_by_sourcemedid(
        self,
        ndc_ids: List[int],
        formulary_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Match formulary records by sourcemedid (links to ProductndcID)
        
        This is the key matching strategy when ProductbrandID is -1
        
        Args:
            ndc_ids: List of ProductndcID values
            formulary_df: Optional pre-loaded formulary data
        
        Returns:
            DataFrame of matching formulary records
        """
        if not ndc_ids:
            return pd.DataFrame()
        
        if formulary_df is None:
            formulary_df = self.get_formulary_data()
        
        if formulary_df.empty:
            return pd.DataFrame()
        
        # Find sourcemedid column (handle case variations)
        sourcemedid_col = None
        for col in formulary_df.columns:
            if col.lower() == 'sourcemedid':
                sourcemedid_col = col
                break
        
        if not sourcemedid_col:
            return pd.DataFrame()
        
        # Match sourcemedid to NDC IDs - try both numeric and string comparison
        try:
            formulary_medids = pd.to_numeric(formulary_df[sourcemedid_col], errors='coerce')
            # Convert ndc_ids to same numeric type
            ndc_ids_numeric = [int(ndc_id) for ndc_id in ndc_ids]
            matches = formulary_df[formulary_medids.isin(ndc_ids_numeric)]
        except Exception:
            # Fallback to string comparison
            matches = formulary_df[
                formulary_df[sourcemedid_col].astype(str).isin([str(ndc_id) for ndc_id in ndc_ids])
            ]
        
        return matches
    
    def get_formulary_coverage(
        self,
        drug_name: str,
        indication: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get formulary coverage for a drug using sourcemedid matching strategy.
        This is the primary strategy since ProductbrandID is -1 in formulary data.
        
        Args:
            drug_name: Drug name (e.g., "Zolgensma (onasemnogene abeparvovec)")
            indication: Optional indication (not used in matching, kept for API compatibility)
        
        Returns:
            Dict with coverage_level, tier, restrictions, coverage_distribution
        """
        # Step 1: Find product in Productbrand_Dim
        product_info = self.find_product_by_name(drug_name)
        if not product_info:
            print(f"❌ Product not found in Productbrand_Dim: {drug_name}")
            return None
        
        product_id = product_info["ProductbrandID"]
        print(f"✅ Found product: {drug_name} -> ProductbrandID: {product_id}")
        
        formulary_df = self.get_formulary_data()
        if formulary_df.empty:
            print(f"❌ Formulary data is empty")
            return None
        
        # Step 2: Use sourcemedid matching strategy (ProductbrandID -> ProductndcID -> sourcemedid)
        ndc_ids = self.get_ndc_ids_for_product(product_id)
        if not ndc_ids:
            print(f"⚠️ No NDC IDs found for ProductbrandID {product_id} ({drug_name})")
            # No NDC relationship found, return default
            return {
                "coverage_level": "Not Listed/Unknown",
                "tier": "Unknown",
                "restrictions": [],
                "coverage_distribution": {
                    "Unrestricted": 0.0,
                    "Restricted": 0.0,
                    "Not Covered": 0.0,
                    "Not Listed/Unknown": 100.0
                },
                "product_info": product_info
            }
        
        print(f"✅ Found {len(ndc_ids)} NDC IDs for {drug_name}: {ndc_ids[:5]}...")
        
        # Match formulary by sourcemedid
        formulary_matches = self.match_formulary_by_sourcemedid(ndc_ids, formulary_df)
        
        # Step 3: If no match, return default
        if formulary_matches.empty:
            print(f"⚠️ No formulary matches found for {drug_name} (NDC IDs: {ndc_ids[:5]}...)")
            return {
                "coverage_level": "Not Listed/Unknown",
                "tier": "Unknown",
                "restrictions": [],
                "coverage_distribution": {
                    "Unrestricted": 0.0,
                    "Restricted": 0.0,
                    "Not Covered": 0.0,
                    "Not Listed/Unknown": 100.0
                },
                "product_info": product_info
            }
        
        # Step 4: Calculate coverage statistics
        return self._calculate_coverage_stats(formulary_matches, product_info)
    
    def _calculate_coverage_stats(
        self,
        formulary_matches: pd.DataFrame,
        product_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate coverage statistics from formulary matches"""
        if formulary_matches.empty:
            return None
        
        coverage_level = "Not Listed/Unknown"
        tier = "Unknown"
        restrictions = []
        
        # Get tier
        if 'universalstatusrollup' in formulary_matches.columns:
            tier_counts = formulary_matches['universalstatusrollup'].value_counts()
            if not tier_counts.empty:
                tier = str(tier_counts.index[0])
        
        # Get coverage level
        if 'universalstatus' in formulary_matches.columns:
            status_counts = formulary_matches['universalstatus'].value_counts()
            if not status_counts.empty:
                most_common_status = str(status_counts.index[0]).lower()
                if 'preferred' in most_common_status or 'covered' in most_common_status:
                    coverage_level = "Unrestricted"
                elif 'restricted' in most_common_status or 'prior' in most_common_status:
                    coverage_level = "Restricted"
                elif 'not covered' in most_common_status or 'excluded' in most_common_status:
                    coverage_level = "Not Covered"
        
        # Get restrictions
        if 'pa' in formulary_matches.columns:
            pa_values = formulary_matches['pa'].dropna()
            if not pa_values.empty:
                if pa_values.astype(str).str.strip().isin(['1', 'yes', 'true', 'Y']).any():
                    restrictions.append('PA')
        
        if 'st' in formulary_matches.columns:
            st_values = formulary_matches['st'].dropna()
            if not st_values.empty:
                if st_values.astype(str).str.strip().isin(['1', 'yes', 'true', 'Y']).any():
                    restrictions.append('ST')
        
        if 'restrictioncode' in formulary_matches.columns:
            restriction_codes = formulary_matches['restrictioncode'].dropna()
            if not restriction_codes.empty:
                for code in restriction_codes.astype(str):
                    if 'ql' in code.lower():
                        if "QL" not in restrictions:
                            restrictions.append("QL")
                    break
        
        # Calculate distribution
        total = len(formulary_matches)
        unrestricted = len(formulary_matches[
            formulary_matches['universalstatus'].astype(str).str.contains('preferred|covered', case=False, na=False)
        ]) if 'universalstatus' in formulary_matches.columns else 0
        
        restricted = len(formulary_matches[
            (formulary_matches.get('pa', pd.Series([0])).astype(str).str.contains('1|yes|true', case=False, na=False)) |
            (formulary_matches.get('st', pd.Series([0])).astype(str).str.contains('1|yes|true', case=False, na=False))
        ]) if 'pa' in formulary_matches.columns or 'st' in formulary_matches.columns else 0
        
        not_covered = len(formulary_matches[
            formulary_matches['universalstatus'].astype(str).str.contains('not covered|excluded', case=False, na=False)
        ]) if 'universalstatus' in formulary_matches.columns else 0
        
        coverage_distribution = {
            "Unrestricted": round(unrestricted / total * 100, 1) if total > 0 else 0.0,
            "Restricted": round(restricted / total * 100, 1) if total > 0 else 0.0,
            "Not Covered": round(not_covered / total * 100, 1) if total > 0 else 0.0,
            "Not Listed/Unknown": round((total - unrestricted - restricted - not_covered) / total * 100, 1) if total > 0 else 100.0
        }
        
        return {
            "coverage_level": coverage_level,
            "tier": tier,
            "restrictions": list(set(restrictions)),
            "coverage_distribution": coverage_distribution,
            "match_count": total,
            "product_info": product_info
        }
    
    # ============================================================================
    # SEARCH METHODS - LLM-accessible search interfaces
    # ============================================================================
    
    def search_products(
        self,
        query: str,
        therapeutic_area: Optional[str] = None,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search for products by name, generic name, or therapeutic area.
        LLM-accessible search method.
        
        Args:
            query: Search query (drug name, generic name, or keywords)
            therapeutic_area: Optional therapeutic area filter
            max_results: Maximum number of results
        
        Returns:
            List of product dictionaries
        """
        product_df = self.get_product_brand_data()
        if product_df.empty:
            return []
        
        query_lower = query.lower()
        results = []
        
        # Search in Productbrandname
        if 'Productbrandname' in product_df.columns:
            matches = product_df[
                product_df['Productbrandname'].astype(str).str.contains(
                    query_lower, case=False, na=False, regex=False
                )
            ]
            
            for _, row in matches.head(max_results).iterrows():
                product_id = row.get('ProductbrandID')
                if product_id:
                    results.append({
                        "ProductbrandID": product_id,
                        "Productbrandname": row.get('Productbrandname', ''),
                        "match_score": 1.0
                    })
        
        return results
    
    def search_formulary_coverage(
        self,
        drug_names: List[str],
        indication: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search formulary coverage for multiple drugs.
        LLM-accessible batch search method.
        
        Args:
            drug_names: List of drug names to search
            indication: Optional indication for context
        
        Returns:
            Dict mapping drug names to coverage info
        """
        results = {}
        for drug_name in drug_names:
            coverage = self.get_formulary_coverage(drug_name, indication)
            if coverage:
                results[drug_name] = coverage
        
        return results
    
    def get_comparator_coverage(
        self,
        comparators: List[Dict[str, Any]],
        indication: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get coverage information for a list of comparators.
        Enhances comparator list with coverage data.
        
        Args:
            comparators: List of comparator dicts with 'drug' or 'name' field
            indication: Optional indication for context
        
        Returns:
            List of comparators with added coverage_info
        """
        enhanced = []
        for comp in comparators:
            drug_name = comp.get("drug") or comp.get("name", "Unknown")
            coverage = self.get_formulary_coverage(drug_name, indication)
            
            comp_copy = comp.copy()
            if coverage:
                comp_copy["coverage_info"] = coverage
            else:
                comp_copy["coverage_info"] = {
                    "coverage_level": "Not Listed/Unknown",
                    "tier": "Unknown",
                    "restrictions": [],
                    "coverage_distribution": {
                        "Unrestricted": 0.0,
                        "Restricted": 0.0,
                        "Not Covered": 0.0,
                        "Not Listed/Unknown": 100.0
                    }
                }
            
            enhanced.append(comp_copy)
        
        return enhanced
    
    # ============================================================================
    # COORDINATION METHODS - For use across services
    # ============================================================================
    
    def get_gtn_data_for_asset(
        self,
        asset_data: Dict[str, Any],
        comparators: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Get GTN-related data for an asset.
        Coordinates data retrieval for GTN calculations.
        
        Args:
            asset_data: Asset information (indication, therapeutic_area, etc.)
            comparators: Optional list of comparators
        
        Returns:
            Dict with formulary data, coverage distributions, etc.
        """
        indication = asset_data.get("indication", "")
        therapeutic_area = asset_data.get("therapeutic_area", "")
        
        formulary_df = self.get_formulary_data()
        
        # Filter by therapeutic area if available
        if therapeutic_area and 'therapeuticclass' in formulary_df.columns:
            filtered_formulary = formulary_df[
                formulary_df['therapeuticclass'].astype(str).str.contains(
                    therapeutic_area, case=False, na=False, regex=False
                )
            ]
        else:
            filtered_formulary = formulary_df
        
        # Get comparator coverage if provided
        comparator_coverage = {}
        if comparators:
            for comp in comparators:
                drug_name = comp.get("drug") or comp.get("name", "")
                if drug_name:
                    coverage = self.get_formulary_coverage(drug_name, indication)
                    if coverage:
                        comparator_coverage[drug_name] = coverage
        
        return {
            "formulary_data": filtered_formulary,
            "formulary_count": len(filtered_formulary),
            "comparator_coverage": comparator_coverage,
            "therapeutic_area": therapeutic_area,
            "indication": indication
        }
    
    def get_payer_plan_coverage(
        self,
        payer_plan_id: Optional[Union[int, str]] = None,
        product_id: Optional[Union[int, str]] = None
    ) -> Dict[str, Any]:
        """
        Get payer plan coverage information.
        
        Args:
            payer_plan_id: Optional PayerPlanID to filter
            product_id: Optional ProductbrandID to filter
        
        Returns:
            Dict with payer plan coverage data
        """
        payer_plan_df = self.get_payer_plan_data()
        formulary_df = self.get_formulary_data()
        
        if payer_plan_df.empty or formulary_df.empty:
            return {}
        
        # Join formulary with payer plans if possible
        # This would require identifying the join key
        # For now, return basic structure
        
        return {
            "payer_plans": len(payer_plan_df),
            "formulary_records": len(formulary_df),
            "data_available": True
        }
    
    # ============================================================================
    # LLM INTERFACE METHODS - Structured data for LLM consumption
    # ============================================================================
    
    def get_llm_context_for_drug(
        self,
        drug_name: str,
        indication: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive context about a drug for LLM consumption.
        Returns structured data that LLMs can use for analysis.
        
        Args:
            drug_name: Drug name
            indication: Optional indication
        
        Returns:
            Dict with product info, coverage, therapeutic area, etc.
        """
        product_info = self.find_product_by_name(drug_name)
        if not product_info:
            return {
                "drug_name": drug_name,
                "found": False,
                "message": "Product not found in Productbrand_Dim"
            }
        
        product_id = product_info["ProductbrandID"]
        
        # Get coverage
        coverage = self.get_formulary_coverage(drug_name, indication)
        
        # Get therapeutic area
        ta_info = self.get_therapeutic_area_for_product(product_id)
        
        # Get NDC IDs
        ndc_ids = self.get_ndc_ids_for_product(product_id)
        
        return {
            "drug_name": drug_name,
            "found": True,
            "product_info": product_info,
            "coverage": coverage,
            "therapeutic_area": ta_info,
            "ndc_ids": ndc_ids,
            "ndc_count": len(ndc_ids),
            "formulary_match_method": coverage.get("match_method", "unknown") if coverage else "none"
        }
    
    def get_llm_context_for_comparators(
        self,
        comparators: List[Dict[str, Any]],
        indication: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive context for a list of comparators.
        LLM-accessible batch method.
        
        Args:
            comparators: List of comparator dicts
            indication: Optional indication
        
        Returns:
            Dict with comparator coverage analysis
        """
        enhanced_comparators = self.get_comparator_coverage(comparators, indication)
        
        # Aggregate statistics
        coverage_levels = {}
        for comp in enhanced_comparators:
            coverage = comp.get("coverage_info", {})
            level = coverage.get("coverage_level", "Unknown")
            coverage_levels[level] = coverage_levels.get(level, 0) + 1
        
        return {
            "comparators": enhanced_comparators,
            "total_comparators": len(enhanced_comparators),
            "coverage_summary": coverage_levels,
            "indication": indication
        }


# Singleton instance
payer_data_service = PayerDataService()
