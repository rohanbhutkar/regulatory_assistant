"""
Payer Data Agent
Provides access to pharmaceutical sales, payer, and market data
"""
import asyncio
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from config import settings
from utils.regulatory_data_io import read_regulatory_csv
from utils.logger import log_error
from models.schemas import PayerResult, SalesResult, ProductResult
import logging

logger = logging.getLogger(__name__)

class PayerDataAgent:
    def __init__(self):
        self.cache = {}
        self._load_data()

    @staticmethod
    def _payer_csv(name: str) -> pd.DataFrame:
        return read_regulatory_csv(f"payer_data/{name}", low_memory=False)
    
    def _load_data(self):
        """Load payer data into memory for fast access"""
        try:
            # Load core datasets
            self.product_brand_df = self._payer_csv( "Productbrand_Dim.csv")
            self.product_group_df = self._payer_csv( "Productgroup_Dim.csv")
            self.product_ndc_df = self._payer_csv( "Productndc_Dim.csv")
            self.therapeutic_area_df = self._payer_csv( "Therapeuticarea_Dim.csv")
            self.therapeutic_class_df = self._payer_csv( "Therapeuticclass_Dim.csv")
            self.customer_df = self._payer_csv( "Customer_Dim.csv")
            self.payer_plan_df = self._payer_csv( "Payer_Plan_Dim.csv")
            self.formulary_tier_df = self._payer_csv( "Formulary_Tier_Dim.csv")
            
            # Load additional datasets
            try:
                self.sales_forecast_df = self._payer_csv( "Sales_Forecast_Fact.csv")
            except:
                self.sales_forecast_df = None
                logger.warning("Sales forecast data not available")
            
            try:
                self.payer_plans_claims_df = self._payer_csv( "Payer_Plans_Claims_Fact.csv")
            except:
                self.payer_plans_claims_df = None
                logger.warning("Payer plans claims data not available")
            
            try:
                self.product_group_df = self._payer_csv( "Productgroup_Dim.csv")
            except:
                self.product_group_df = None
                logger.warning("Product group data not available")
            
            # Load sales data if available (use the correct sales file with real data)
            try:
                self.sales_df = self._payer_csv( "Sales_Fact.csv")
                logger.info(f"Loaded Sales_Fact data: {len(self.sales_df)} records")
            except Exception as e:
                self.sales_df = None
                logger.warning(f"Sales data not available: {e}")
            
            # Load relationship data
            try:
                self.product_brand_group_rel_df = self._payer_csv( "Productbrand_Productgroup_Relationship_Dim.csv")
                logger.info(f"Loaded product brand-group relationship data: {len(self.product_brand_group_rel_df)} records")
            except Exception as e:
                self.product_brand_group_rel_df = None
                logger.warning(f"Product brand-group relationship data not available: {e}")
            
            try:
                self.product_brand_therapeutic_rel_df = self._payer_csv( "Productbrand_Therapeuticarea_Relationship_Dim.csv")
                logger.info(f"Loaded product brand-therapeutic area relationship data: {len(self.product_brand_therapeutic_rel_df)} records")
            except Exception as e:
                self.product_brand_therapeutic_rel_df = None
                logger.warning(f"Product brand-therapeutic area relationship data not available: {e}")
            
            # Load enhanced relationship data (NDC relationships - more complete)
            try:
                self.product_brand_ndc_rel_df = self._payer_csv( "Productbrand_Productndc_Relationship_Dim.csv")
                logger.info(f"Loaded product brand-NDC relationship data: {len(self.product_brand_ndc_rel_df)} records")
            except Exception as e:
                self.product_brand_ndc_rel_df = None
                logger.warning(f"Product brand-NDC relationship data not available: {e}")
            
            # Load additional data sources for enhanced analysis
            try:
                self.market_basket_df = self._payer_csv( "Market_Basket_Dim.csv")
                logger.info(f"Loaded market basket data: {len(self.market_basket_df)} records")
            except Exception as e:
                self.market_basket_df = None
                logger.warning(f"Market basket data not available: {e}")
            
            try:
                self.formulary_tier_df = self._payer_csv( "Formulary_Tier_Dim.csv")
                logger.info(f"Loaded formulary tier data: {len(self.formulary_tier_df)} records")
            except Exception as e:
                self.formulary_tier_df = None
                logger.warning(f"Formulary tier data not available: {e}")
            
            # Create indexes for faster lookups
            self._create_indexes()
            
            # Load relationship tables
            try:
                self.product_brand_ndc_df = self._payer_csv( "Productbrand_Productndc_Relationship_Dim.csv")
                self.product_brand_therapeutic_df = self._payer_csv( "Productbrand_Therapeuticarea_Relationship_Dim.csv")
                self.product_brand_class_df = self._payer_csv( "Product_Brand_Therapeutic_Class_Relation_Dim.csv")
            except:
                logger.warning("Some relationship tables not available")
            
            logger.info("Payer data loaded successfully")
            
        except Exception as e:
            log_error(e, "Failed to load payer data")
            raise
    
    def _create_indexes(self):
        """Create indexes for faster lookups"""
        try:
            # Create indexes for common lookups
            if self.product_brand_df is not None:
                self.product_brand_index = self.product_brand_df.set_index('ProductbrandID')
            if self.therapeutic_area_df is not None:
                self.therapeutic_area_index = self.therapeutic_area_df.set_index('TherapeuticareaID')
            if self.customer_df is not None:
                self.customer_index = self.customer_df.set_index('CustomerID')
            if self.payer_plan_df is not None:
                self.payer_plan_index = self.payer_plan_df.set_index('PayerplanID')
            
            logger.info("Payer data indexes created successfully")
        except Exception as e:
            log_error(e, "Failed to create payer data indexes")
    
    async def analyze_sales_trends_enhanced(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Enhanced sales trends analysis using NDC relationships and market basket data"""
        try:
            query_lower = query.lower()
            results = []
            
            # Extract search terms
            search_terms = self._extract_pharmaceutical_terms(query)
            
            # Method 1: Use NDC relationships (more complete data)
            if self.product_brand_ndc_rel_df is not None and self.product_ndc_df is not None:
                # Get diabetes products from therapeutic area relationships
                diabetes_brand_rel_df = self._payer_csv( "Productbrand_Therapeuticarea_Relationship_Dim.csv")
                diabetes_brands = diabetes_brand_rel_df[diabetes_brand_rel_df['TherapeuticareaID'] == 2]
                diabetes_brand_ids = diabetes_brands['ProductbrandID'].tolist()
                
                # Get NDC relationships for diabetes products
                diabetes_ndc_rels = self.product_brand_ndc_rel_df[
                    self.product_brand_ndc_rel_df['productbrandid'].isin(diabetes_brand_ids)
                ]
                
                if len(diabetes_ndc_rels) > 0:
                    # Get NDC details
                    ndc_ids = diabetes_ndc_rels['productndcid'].tolist()
                    diabetes_ndcs = self.product_ndc_df[self.product_ndc_df['ProductndcID'].isin(ndc_ids)]
                    
                    # Filter by search terms
                    if search_terms:
                        diabetes_ndcs = diabetes_ndcs[
                            diabetes_ndcs['Ndcname'].str.lower().str.contains('|'.join(search_terms), na=False)
                        ]
                    
                    if len(diabetes_ndcs) > 0:
                        # Prioritize recent NDC data
                        date_columns = ['NDC_Start_Date', 'Inserttimestamp', 'Updatetimestamp']
                        recent_ndcs = self._prioritize_recent_data(diabetes_ndcs, date_columns, max_age_years=3)
                        
                        # Add recency scores and sort by recency
                        if not recent_ndcs.empty:
                            recent_ndcs = recent_ndcs.copy()
                            recent_ndcs['recency_score'] = recent_ndcs.apply(
                                lambda row: self._get_recency_score(row, date_columns), axis=1
                            )
                            recent_ndcs = recent_ndcs.sort_values('recency_score', ascending=False)
                        
                        # Create results based on recent NDC data
                        for _, ndc_row in recent_ndcs.head(max_results).iterrows():
                            results.append({
                                'product_id': str(ndc_row['ProductndcID']),
                                'product_name': ndc_row['Ndcname'],
                                'drug_generic_name': ndc_row.get('Drug_Generic_Name', 'Unknown'),
                                'drug_class': ndc_row.get('Drug_Class', 'Unknown'),
                                'manufacturer': ndc_row.get('Manufacturer', 'Unknown'),
                                'ndc_start_date': ndc_row.get('NDC_Start_Date', 'Unknown'),
                                'recency_score': ndc_row.get('recency_score', 0.5),
                                'total_wac_dollars': 0,  # NDC data doesn't have sales data
                                'average_wac_dollars': 0,
                                'total_volume_units': 0,
                                'total_rx_count': 0,
                                'data_points': 1,
                                'metadata': {
                                    'source': 'payer_data',
                                    'analysis_type': 'sales_trends_ndc',
                                    'data_source': 'NDC relationships',
                                    'recency_prioritized': True
                                }
                            })
            
            # Method 2: Use market basket data (fallback)
            if len(results) < max_results and self.market_basket_df is not None:
                market_basket_diabetes = self.market_basket_df[
                    self.market_basket_df['ProductGroupName'].str.contains('|'.join(search_terms), case=False, na=False)
                ]
                
                if len(market_basket_diabetes) > 0:
                    for _, mb_row in market_basket_diabetes.head(max_results - len(results)).iterrows():
                        results.append({
                            'product_id': str(mb_row['ProductGroupNo']),
                            'product_name': mb_row['ProductGroupName'],
                            'drug_generic_name': 'Unknown',
                            'drug_class': 'Unknown',
                            'manufacturer': 'Unknown',
                            'total_wac_dollars': 0,
                            'average_wac_dollars': 0,
                            'total_volume_units': 0,
                            'total_rx_count': 0,
                            'data_points': 1,
                            'metadata': {
                                'source': 'payer_data',
                                'analysis_type': 'sales_trends_market_basket',
                                'data_source': 'Market basket'
                            }
                        })
            
            return results
            
        except Exception as e:
            log_error(e, f"Enhanced sales trends analysis failed for query: {query}")
            return []

    async def analyze_sales_trends(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Analyze sales trends with flexible search terms and time-based analysis"""
        try:
            # First try the enhanced method
            enhanced_results = await self.analyze_sales_trends_enhanced(query, max_results)
            if enhanced_results:
                return enhanced_results
            
            # Fallback to original method
            query_lower = query.lower()
            results = []
            
            # Extract search terms
            search_terms = self._extract_pharmaceutical_terms(query)
            
            # Search in therapeutic areas first
            matching_therapeutic = self.therapeutic_area_df[
                self.therapeutic_area_df['Therapeuticareavalue'].str.lower().str.contains('|'.join(search_terms), na=False)
            ]
            
            if not matching_therapeutic.empty and self.sales_df is not None and self.product_brand_group_rel_df is not None:
                # Get therapeutic area IDs
                therapeutic_ids = matching_therapeutic['TherapeuticareaID'].tolist()
                
                # Get product brands in these therapeutic areas
                product_brand_rels = self.product_brand_therapeutic_rel_df[
                    self.product_brand_therapeutic_rel_df['TherapeuticareaID'].isin(therapeutic_ids)
                ]
                
                if not product_brand_rels.empty:
                    product_brand_ids = product_brand_rels['ProductbrandID'].tolist()
                    
                    # Get product group IDs from relationship
                    product_group_rels = self.product_brand_group_rel_df[
                        self.product_brand_group_rel_df['ProductbrandID'].isin(product_brand_ids)
                    ]
                    
                    if not product_group_rels.empty:
                        product_group_ids = product_group_rels['ProductgroupID'].tolist()
                        
                        # Get sales data for matching product groups
                        sales_data = self.sales_df[self.sales_df['productgroupid'].isin(product_group_ids)]
                        
                        # Merge with product information through relationship
                        merged = sales_data.merge(
                            product_group_rels[['ProductbrandID', 'ProductgroupID']], 
                            left_on='productgroupid', 
                            right_on='ProductgroupID', 
                            how='left'
                        ).merge(
                            self.product_brand_df[['ProductbrandID', 'Productbrandname']], 
                            on='ProductbrandID', 
                            how='left'
                        )
                        
                        # Group by product and calculate trend statistics
                        grouped = merged.groupby('ProductbrandID').agg({
                            'wac_dollars': ['sum', 'mean', 'std', 'min', 'max'],
                            'volume_units': ['sum', 'mean', 'std'],
                            'totalrxcount': ['sum', 'mean'],
                            'weekendingdateid': ['min', 'max', 'count']
                        }).reset_index()
                    
                        # Flatten column names
                        grouped.columns = ['ProductbrandID', 'total_wac', 'avg_wac', 'std_wac', 
                                         'min_wac', 'max_wac', 'total_volume', 'avg_volume', 
                                         'std_volume', 'total_rx', 'avg_rx', 'earliest_date', 
                                         'latest_date', 'data_points']
                        
                        # Add product information
                        grouped = grouped.merge(
                            self.product_brand_df[['ProductbrandID', 'Productbrandname']], 
                            on='ProductbrandID', 
                            how='left'
                        )
                
                        for _, row in grouped.head(max_results).iterrows():
                            results.append({
                                'product_id': str(row['ProductbrandID']),
                                'product_name': row['Productbrandname'],
                                'total_wac_dollars': row['total_wac'],
                                'average_wac_dollars': row['avg_wac'],
                                'wac_standard_deviation': row['std_wac'],
                                'min_wac_dollars': row['min_wac'],
                                'max_wac_dollars': row['max_wac'],
                                'total_volume_units': row['total_volume'],
                                'average_volume_units': row['avg_volume'],
                                'total_rx_count': row['total_rx'],
                                'average_rx_count': row['avg_rx'],
                                'earliest_sale_date': row['earliest_date'],
                                'latest_sale_date': row['latest_date'],
                                'data_points': row['data_points'],
                                'metadata': {'source': 'payer_data', 'analysis_type': 'sales_trends'}
                            })
            
            return results
            
        except Exception as e:
            log_error(e, f"Sales trends analysis failed for query: {query}")
            return []
    
    async def analyze_market_penetration_enhanced(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Enhanced market penetration analysis using customer and HCP data"""
        try:
            query_lower = query.lower()
            results = []
            
            # Extract search terms
            search_terms = self._extract_pharmaceutical_terms(query)
            
            # Method 1: Use customer data for diabetes market analysis
            try:
                customer_df = self._payer_csv( "Customer_Dim.csv")
                diabetes_customers = customer_df[
                    customer_df['SourceID'].str.contains('|'.join(search_terms), case=False, na=False)
                ]
                
                if len(diabetes_customers) > 0:
                    # Analyze customer types
                    customer_types = diabetes_customers['Customertype'].value_counts()
                    
                    for customer_type, count in customer_types.head(max_results).items():
                        results.append({
                            'customer_type': customer_type,
                            'customer_count': count,
                            'market_penetration': count / len(customer_df) * 100,
                            'therapeutic_area': 'Diabetes',
                            'metadata': {
                                'source': 'payer_data',
                                'analysis_type': 'market_penetration_customers',
                                'data_source': 'Customer data'
                            }
                        })
            except Exception as e:
                log_error(e, "Failed to analyze customer data for market penetration")
            
            # Method 2: Use HCP data for diabetes market analysis
            if len(results) < max_results:
                try:
                    hcp_df = self._payer_csv( "HCP_Dim.csv")
                    diabetes_hcps = hcp_df[
                        hcp_df['organization_name'].str.contains('|'.join(search_terms), case=False, na=False)
                    ]
                    
                    if len(diabetes_hcps) > 0:
                        # Analyze HCP tiers
                        hcp_tiers = diabetes_hcps['hcp_tier'].value_counts()
                        
                        for tier, count in hcp_tiers.head(max_results - len(results)).items():
                            results.append({
                                'hcp_tier': tier,
                                'hcp_count': count,
                                'market_penetration': count / len(hcp_df) * 100,
                                'therapeutic_area': 'Diabetes',
                                'metadata': {
                                    'source': 'payer_data',
                                    'analysis_type': 'market_penetration_hcps',
                                    'data_source': 'HCP data'
                                }
                            })
                except Exception as e:
                    log_error(e, "Failed to analyze HCP data for market penetration")
            
            return results
            
        except Exception as e:
            log_error(e, f"Enhanced market penetration analysis failed for query: {query}")
            return []

    async def analyze_market_penetration(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Analyze market penetration by payer plans and therapeutic areas"""
        try:
            # First try the enhanced method
            enhanced_results = await self.analyze_market_penetration_enhanced(query, max_results)
            if enhanced_results:
                return enhanced_results
            
            # Fallback to original method
            query_lower = query.lower()
            results = []
            
            # Extract search terms
            search_terms = self._extract_pharmaceutical_terms(query)
            
            # Search in therapeutic areas
            matching_therapeutic = self.therapeutic_area_df[
                self.therapeutic_area_df['Therapeuticareavalue'].str.lower().str.contains('|'.join(search_terms), na=False)
            ]
            
            if not matching_therapeutic.empty and self.sales_df is not None:
                # Get therapeutic area IDs
                therapeutic_ids = matching_therapeutic['TherapeuticareaID'].tolist()
                
                # Get products in these therapeutic areas
                if self.product_brand_therapeutic_df is not None:
                    therapeutic_products = self.product_brand_therapeutic_df[
                        self.product_brand_therapeutic_df['TherapeuticareaID'].isin(therapeutic_ids)
                    ]
                    
                    product_ids = therapeutic_products['ProductbrandID'].tolist()
                    sales_data = self.sales_df[self.sales_df['productgroupid'].isin(product_ids)]
                    
                    # Merge with therapeutic area information
                    merged = sales_data.merge(
                        therapeutic_products[['ProductbrandID', 'TherapeuticareaID']], 
                        left_on='productgroupid', 
                        right_on='ProductbrandID', 
                        how='left'
                    )
                    
                    merged = merged.merge(
                        matching_therapeutic[['TherapeuticareaID', 'Therapeuticareavalue']], 
                        on='TherapeuticareaID', 
                        how='left'
                    )
                    
                    # Group by therapeutic area and payer plan
                    grouped = merged.groupby(['TherapeuticareaID', 'payerplanid']).agg({
                        'wac_dollars': ['sum', 'mean'],
                        'volume_units': ['sum', 'mean'],
                        'totalrxcount': ['sum', 'mean']
                    }).reset_index()
                    
                    # Flatten column names
                    grouped.columns = ['TherapeuticareaID', 'payerplanid', 'total_wac', 'avg_wac', 
                                     'total_volume', 'avg_volume', 'total_rx', 'avg_rx']
                    
                    # Add therapeutic area information
                    grouped = grouped.merge(
                        matching_therapeutic[['TherapeuticareaID', 'Therapeuticareavalue']], 
                        on='TherapeuticareaID', 
                        how='left'
                    )
                    
                    # Add payer plan information if available
                    if self.payer_plan_df is not None:
                        grouped = grouped.merge(
                            self.payer_plan_df[['PayerplanID', 'Payername', 'Planname']], 
                            left_on='payerplanid', 
                            right_on='PayerplanID', 
                            how='left'
                        )
                    
                    for _, row in grouped.head(max_results).iterrows():
                        results.append({
                            'therapeutic_area_id': str(row['TherapeuticareaID']),
                            'therapeutic_area_name': row['Therapeuticareavalue'],
                            'payer_plan_id': str(row['payerplanid']) if pd.notna(row['payerplanid']) else 'Unknown',
                            'payer_plan_name': row.get('Payername', 'Unknown'),
                            'total_wac_dollars': row['total_wac'],
                            'average_wac_dollars': row['avg_wac'],
                            'total_volume_units': row['total_volume'],
                            'average_volume_units': row['avg_volume'],
                            'total_rx_count': row['total_rx'],
                            'average_rx_count': row['avg_rx'],
                            'metadata': {'source': 'payer_data', 'analysis_type': 'market_penetration'}
                        })
            
            return results
            
        except Exception as e:
            log_error(e, f"Market penetration analysis failed for query: {query}")
            return []
    
    async def analyze_payer_rebates(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Analyze payer rebates and formulary coverage"""
        try:
            query_lower = query.lower()
            results = []
            
            if self.payer_plans_claims_df is None:
                return results
            
            # Extract search terms
            search_terms = self._extract_pharmaceutical_terms(query)
            
            # Search in payer plans
            matching_payers = self.payer_plan_df[
                self.payer_plan_df['Payername'].str.lower().str.contains('|'.join(search_terms), na=False) |
                self.payer_plan_df['Planname'].str.lower().str.contains('|'.join(search_terms), na=False)
            ]
            
            if not matching_payers.empty:
                payer_ids = matching_payers['PayerplanID'].tolist()
                rebate_data = self.payer_plans_claims_df[
                    self.payer_plans_claims_df['PAYERPLANID'].isin(payer_ids)
                ]
                
                # Merge with payer plan information
                merged = rebate_data.merge(
                    matching_payers[['PayerplanID', 'Payername', 'Planname']], 
                    left_on='PAYERPLANID', 
                    right_on='PayerplanID', 
                    how='left'
                )
                
                # Group by payer plan and calculate rebate statistics
                # Convert numeric columns to proper types first
                numeric_cols = ['TOTAL_REBATES_PAID', 'TOTAL_PRESCRIPTION_COUNT', 'COMMERCIAL_LIVES', 'MEDICARE_LIVES']
                for col in numeric_cols:
                    if col in merged.columns:
                        merged[col] = pd.to_numeric(merged[col], errors='coerce')
                
                grouped = merged.groupby('PayerplanID').agg({
                    'TOTAL_REBATES_PAID': ['sum', 'mean', 'std'],
                    'TOTAL_PRESCRIPTION_COUNT': ['sum', 'mean'],
                    'COMMERCIAL_LIVES': ['sum', 'mean'],
                    'MEDICARE_LIVES': ['sum', 'mean']
                }).reset_index()
                
                # Flatten column names
                grouped.columns = ['PayerplanID', 'total_rebates', 'avg_rebates', 'std_rebates', 
                                 'total_rx_count', 'avg_rx_count', 'total_commercial_lives', 
                                 'avg_commercial_lives', 'total_medicare_lives', 'avg_medicare_lives']
                
                # Add payer plan information
                grouped = grouped.merge(
                    matching_payers[['PayerplanID', 'Payername', 'Planname']], 
                    on='PayerplanID', 
                    how='left'
                )
                
                for _, row in grouped.head(max_results).iterrows():
                    results.append({
                        'payer_plan_id': str(row['PayerplanID']),
                        'payer_name': row['Payername'],
                        'plan_name': row['Planname'],
                        'total_rebates_paid': row['total_rebates'],
                        'average_rebates_paid': row['avg_rebates'],
                        'rebates_standard_deviation': row['std_rebates'],
                        'total_prescription_count': row['total_rx_count'],
                        'average_prescription_count': row['avg_rx_count'],
                        'total_commercial_lives': row['total_commercial_lives'],
                        'average_commercial_lives': row['avg_commercial_lives'],
                        'total_medicare_lives': row['total_medicare_lives'],
                        'average_medicare_lives': row['avg_medicare_lives'],
                        'metadata': {'source': 'payer_data', 'analysis_type': 'payer_rebates'}
                    })
            
            return results
            
        except Exception as e:
            log_error(e, f"Payer rebates analysis failed for query: {query}")
            return []
    
    async def analyze_formulary_coverage(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Analyze formulary coverage using unified PayerDataService.
        LLM-accessible method for formulary coverage queries.
        """
        try:
            from services.payer_data_service import payer_data_service
            from utils.optimized_data_loader import OptimizedDataLoader
            
            # Initialize service with data loader
            if not payer_data_service.data_loader:
                payer_data_service.data_loader = OptimizedDataLoader()
            
            # Search for products matching query
            products = payer_data_service.search_products(query, max_results=max_results)
            
            # Get coverage for each product
            results = []
            for product in products:
                drug_name = product.get("Productbrandname", "")
                coverage = payer_data_service.get_formulary_coverage(drug_name)
                
                if coverage:
                    results.append({
                        "product": product,
                        "coverage": coverage,
                        "query": query
                    })
            
            return results[:max_results]
        except Exception as e:
            logger.warning(f"Error in analyze_formulary_coverage: {e}")
            # Fallback to original implementation
            return await self._analyze_formulary_coverage_legacy(query, max_results)
    
    async def _analyze_formulary_coverage_legacy(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Analyze formulary coverage and tier placement"""
        try:
            query_lower = query.lower()
            results = []
            
            # Extract search terms
            search_terms = self._extract_pharmaceutical_terms(query)
            
            # Search in product brands - use bracket pattern search
            matching_products = pd.DataFrame()
            for term in search_terms:
                # Strategy 1: Search for brand name in brackets [brandname]
                bracket_pattern = f"[{term}]"
                bracket_matches = self.product_brand_df[
                    self.product_brand_df['Productbrandname'].astype(str).str.contains(bracket_pattern, case=False, na=False, regex=False)
                ]
                if not bracket_matches.empty:
                    matching_products = pd.concat([matching_products, bracket_matches]).drop_duplicates(subset=['ProductbrandID'])
                    continue
                
                # Strategy 2: Search for term anywhere in product name
                term_matches = self.product_brand_df[
                    self.product_brand_df['Productbrandname'].astype(str).str.contains(term, case=False, na=False, regex=False)
                ]
                if not term_matches.empty:
                    matching_products = pd.concat([matching_products, term_matches]).drop_duplicates(subset=['ProductbrandID'])
            
            if not matching_products.empty and self.formulary_tier_df is not None:
                # Get formulary coverage for matching products
                # Handle case variations for ProductbrandID
                product_id_col = None
                for col in self.formulary_tier_df.columns:
                    if col.lower() == 'productbrandid':
                        product_id_col = col
                        break
                
                if not product_id_col:
                    return results
                
                product_ids = matching_products['ProductbrandID'].tolist()
                formulary_data = self.formulary_tier_df[
                    self.formulary_tier_df[product_id_col].isin(product_ids)
                ]
                
                if formulary_data.empty:
                    return results
                
                # Merge with product information
                merged = formulary_data.merge(
                    matching_products[['ProductbrandID', 'Productbrandname']], 
                    left_on=product_id_col,
                    right_on='ProductbrandID', 
                    how='left'
                )
                
                # Merge with payer plan information if PayerPlanID exists
                if self.payer_plan_df is not None and 'PayerPlanID' in merged.columns:
                    payer_plan_id_col = None
                    for col in self.payer_plan_df.columns:
                        if col.lower() == 'payerplanid':
                            payer_plan_id_col = col
                            break
                    
                    if payer_plan_id_col:
                        merged = merged.merge(
                            self.payer_plan_df[[payer_plan_id_col, 'PayerPlanName']], 
                            left_on='PayerPlanID',
                            right_on=payer_plan_id_col,
                            how='left'
                        )
                
                # Group by product and calculate coverage statistics using actual column names
                # Use universalstatusrollup for tier, universalstatus for coverage
                agg_dict = {}
                
                if 'universalstatusrollup' in merged.columns:
                    agg_dict['universalstatusrollup'] = ['count', lambda x: x.value_counts().to_dict()]
                if 'universalstatus' in merged.columns:
                    agg_dict['universalstatus'] = ['count', lambda x: x.value_counts().to_dict()]
                if 'PayerPlanID' in merged.columns:
                    agg_dict['PayerPlanID'] = 'nunique'
                
                if not agg_dict:
                    return results
                
                grouped = merged.groupby('ProductbrandID').agg(agg_dict).reset_index()
                
                # Flatten column names
                new_cols = ['ProductbrandID']
                for col, funcs in agg_dict.items():
                    if isinstance(funcs, list):
                        for func in funcs:
                            if callable(func):
                                new_cols.append(f'{col}_distribution')
                            else:
                                new_cols.append(f'{col}_count')
                    else:
                        new_cols.append(f'{col}_{funcs}')
                
                grouped.columns = new_cols[:len(grouped.columns)]
                
                # Add product information
                grouped = grouped.merge(
                    matching_products[['ProductbrandID', 'Productbrandname']], 
                    on='ProductbrandID', 
                    how='left'
                )
                
                for _, row in grouped.head(max_results).iterrows():
                    # Calculate coverage rate from universalstatus
                    coverage_count = 0
                    total_count = 0
                    if 'universalstatus_count' in row.index:
                        total_count = row['universalstatus_count']
                    if 'universalstatus_distribution' in row.index and row['universalstatus_distribution']:
                        status_dist = row['universalstatus_distribution']
                        if isinstance(status_dist, dict):
                            for status, count in status_dist.items():
                                status_str = str(status).lower()
                                if 'preferred' in status_str or ('covered' in status_str and 'not' not in status_str):
                                    coverage_count += count
                    
                    coverage_rate = (coverage_count / total_count * 100) if total_count > 0 else 0
                    
                    results.append({
                        'product_id': str(row['ProductbrandID']),
                        'brand_name': row.get('Productbrandname', 'Unknown'),
                        'total_coverage_records': total_count,
                        'covered_count': coverage_count,
                        'coverage_rate_percent': coverage_rate,
                        'unique_payer_plans': row.get('PayerPlanID_nunique', 0),
                        'tier_distribution': row.get('universalstatusrollup_distribution', {}),
                        'status_distribution': row.get('universalstatus_distribution', {}),
                        'metadata': {'source': 'payer_data', 'analysis_type': 'formulary_coverage'}
                    })
            
            return results
            
        except Exception as e:
            log_error(e, f"Formulary coverage analysis failed for query: {query}")
            return []
    
    async def analyze_competitive_landscape(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Analyze competitive landscape by therapeutic area"""
        try:
            query_lower = query.lower()
            results = []
            
            # Extract search terms
            search_terms = self._extract_pharmaceutical_terms(query)
            
            # Search in therapeutic areas
            matching_therapeutic = self.therapeutic_area_df[
                self.therapeutic_area_df['Therapeuticareavalue'].str.lower().str.contains('|'.join(search_terms), na=False)
            ]
            
            if not matching_therapeutic.empty:
                therapeutic_ids = matching_therapeutic['TherapeuticareaID'].tolist()
                
                # Get products in these therapeutic areas
                if self.product_brand_therapeutic_df is not None:
                    therapeutic_products = self.product_brand_therapeutic_df[
                        self.product_brand_therapeutic_df['TherapeuticareaID'].isin(therapeutic_ids)
                    ]
                    
                    product_ids = therapeutic_products['ProductbrandID'].tolist()
                    
                    # Get product information
                    products_in_area = self.product_brand_df[
                        self.product_brand_df['ProductbrandID'].isin(product_ids)
                    ]
                    
                    # Prioritize recent products
                    if not products_in_area.empty:
                        date_columns = ['Inserttimestamp', 'Updatetimestamp']
                        recent_products = self._prioritize_recent_data(products_in_area, date_columns, max_age_years=5)
                        
                        # Add recency scores
                        if not recent_products.empty:
                            recent_products = recent_products.copy()
                            recent_products['recency_score'] = recent_products.apply(
                                lambda row: self._get_recency_score(row, date_columns), axis=1
                            )
                            recent_products = recent_products.sort_values('recency_score', ascending=False)
                    else:
                        recent_products = products_in_area
                    
                    # Merge with therapeutic area information
                    merged = recent_products.merge(
                        therapeutic_products[['ProductbrandID', 'TherapeuticareaID']], 
                        on='ProductbrandID', 
                        how='left'
                    )
                    
                    merged = merged.merge(
                        matching_therapeutic[['TherapeuticareaID', 'Therapeuticareavalue']], 
                        on='TherapeuticareaID', 
                        how='left'
                    )
                    
                    # Group by therapeutic area and calculate competitive metrics with recency
                    grouped = merged.groupby('TherapeuticareaID').agg({
                        'ProductbrandID': 'count',
                        'Productbrandname': 'nunique',
                        'recency_score': ['mean', 'max', 'min']
                    }).reset_index()
                    
                    # Flatten column names
                    grouped.columns = ['TherapeuticareaID', 'total_products', 'unique_product_names', 
                                     'avg_recency_score', 'max_recency_score', 'min_recency_score']
                    
                    # Add therapeutic area information
                    grouped = grouped.merge(
                        matching_therapeutic[['TherapeuticareaID', 'Therapeuticareavalue']], 
                        on='TherapeuticareaID', 
                        how='left'
                    )
                    
                    for _, row in grouped.head(max_results).iterrows():
                        results.append({
                            'therapeutic_area_id': str(row['TherapeuticareaID']),
                            'therapeutic_area_name': row['Therapeuticareavalue'],
                            'total_products': row['total_products'],
                            'unique_product_names': row['unique_product_names'],
                            'avg_recency_score': round(row['avg_recency_score'], 3) if pd.notna(row['avg_recency_score']) else 0.5,
                            'max_recency_score': round(row['max_recency_score'], 3) if pd.notna(row['max_recency_score']) else 0.5,
                            'min_recency_score': round(row['min_recency_score'], 3) if pd.notna(row['min_recency_score']) else 0.5,
                            'metadata': {
                                'source': 'payer_data', 
                                'analysis_type': 'competitive_landscape',
                                'recency_prioritized': True
                            }
                        })
            
            return results
            
        except Exception as e:
            log_error(e, f"Competitive landscape analysis failed for query: {query}")
            return []
    
    async def analyze_customer_segments(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Analyze customer segments and purchasing patterns"""
        try:
            query_lower = query.lower()
            results = []
            
            # Extract search terms
            search_terms = self._extract_pharmaceutical_terms(query)
            
            # Search in customers
            matching_customers = self.customer_df[
                self.customer_df['Customertype'].str.lower().str.contains('|'.join(search_terms), na=False)
            ]
            
            if not matching_customers.empty and self.sales_df is not None:
                customer_ids = matching_customers['CustomerID'].tolist()
                sales_data = self.sales_df[self.sales_df['customerid'].isin(customer_ids)]
                
                # Merge with customer information
                merged = sales_data.merge(
                    matching_customers[['CustomerID', 'Customertype']], 
                    on='CustomerID', 
                    how='left'
                )
                
                # Group by customer and calculate purchasing patterns
                grouped = merged.groupby('CustomerID').agg({
                    'wac_dollars': ['sum', 'mean', 'std'],
                    'volume_units': ['sum', 'mean'],
                    'totalrxcount': ['sum', 'mean'],
                    'productgroupid': 'nunique',
                    'weekendingdateid': ['min', 'max', 'count']
                }).reset_index()
                
                # Flatten column names
                grouped.columns = ['CustomerID', 'total_wac', 'avg_wac', 'std_wac', 
                                 'total_volume', 'avg_volume', 'total_rx', 'avg_rx', 
                                 'unique_products', 'earliest_purchase', 'latest_purchase', 'purchase_weeks']
                
                # Add customer information
                grouped = grouped.merge(
                    matching_customers[['CustomerID', 'Customertype']], 
                    on='CustomerID', 
                    how='left'
                )
                
                for _, row in grouped.head(max_results).iterrows():
                    results.append({
                        'customer_id': str(row['CustomerID']),
                        'customer_type': row['Customertype'],
                        'total_wac_dollars': row['total_wac'],
                        'average_wac_dollars': row['avg_wac'],
                        'wac_standard_deviation': row['std_wac'],
                        'total_volume_units': row['total_volume'],
                        'average_volume_units': row['avg_volume'],
                        'total_rx_count': row['total_rx'],
                        'average_rx_count': row['avg_rx'],
                        'unique_products_purchased': row['unique_products'],
                        'earliest_purchase_date': row['earliest_purchase'],
                        'latest_purchase_date': row['latest_purchase'],
                        'purchase_weeks': row['purchase_weeks'],
                        'metadata': {'source': 'payer_data', 'analysis_type': 'customer_segments'}
                    })
            
            return results
            
        except Exception as e:
            log_error(e, f"Customer segments analysis failed for query: {query}")
            return []
    
    def _prioritize_recent_data(self, df: pd.DataFrame, date_columns: List[str], max_age_years: int = 5) -> pd.DataFrame:
        """Prioritize recent data by filtering and sorting based on date columns"""
        try:
            if df.empty:
                return df
            
            # Find the best date column to use for recency
            best_date_col = None
            for col in date_columns:
                if col in df.columns:
                    # Check if column has valid dates
                    non_null_dates = df[col].dropna()
                    if len(non_null_dates) > 0:
                        best_date_col = col
                        break
            
            if best_date_col is None:
                return df
            
            # Convert date column to datetime
            df_copy = df.copy()
            df_copy[best_date_col] = pd.to_datetime(df_copy[best_date_col], errors='coerce')
            
            # Filter out very old data (older than max_age_years)
            cutoff_date = pd.Timestamp.now() - pd.DateOffset(years=max_age_years)
            recent_df = df_copy[df_copy[best_date_col] >= cutoff_date]
            
            # If we filtered out too much, use original data but sort by recency
            if len(recent_df) < len(df) * 0.1:  # If less than 10% remains, use original
                recent_df = df_copy.dropna(subset=[best_date_col])
            
            # Sort by date (most recent first)
            if not recent_df.empty:
                recent_df = recent_df.sort_values(best_date_col, ascending=False)
            
            return recent_df
            
        except Exception as e:
            log_error(e, f"Error prioritizing recent data: {e}")
            return df
    
    def _get_recency_score(self, row: pd.Series, date_columns: List[str]) -> float:
        """Calculate a recency score for a row based on available date columns"""
        try:
            scores = []
            current_date = pd.Timestamp.now()
            
            for col in date_columns:
                if col in row.index and pd.notna(row[col]):
                    try:
                        date_val = pd.to_datetime(row[col])
                        if pd.notna(date_val):
                            # Calculate days since date (more recent = higher score)
                            days_diff = (current_date - date_val).days
                            # Convert to score (0-1, where 1 is most recent)
                            score = max(0, 1 - (days_diff / (365 * 5)))  # 5 year decay
                            scores.append(score)
                    except:
                        continue
            
            return max(scores) if scores else 0.5  # Default score if no valid dates
            
        except Exception as e:
            return 0.5  # Default score on error

    def _extract_pharmaceutical_terms(self, query: str) -> List[str]:
        """Extract pharmaceutical terms from query for flexible searching"""
        query_lower = query.lower()
        
        # Common pharmaceutical terms
        pharma_terms = [
            'diabetes', 'hypertension', 'cancer', 'oncology', 'cardiology', 'neurology',
            'respiratory', 'asthma', 'copd', 'pneumonia', 'infection', 'antibiotic',
            'pain', 'analgesic', 'anti-inflammatory', 'steroid', 'hormone', 'thyroid',
            'depression', 'anxiety', 'mental', 'psychiatric', 'neurological',
            'orthopedic', 'dermatology', 'gastroenterology', 'urology', 'gynecology',
            'pediatric', 'geriatric', 'vaccine', 'immunization', 'biologic',
            'generic', 'brand', 'patent', 'formulary', 'tier', 'coverage', 'rebate',
            'payer', 'insurance', 'medicare', 'medicaid', 'commercial'
        ]
        
        # Extract terms that appear in the query
        found_terms = [term for term in pharma_terms if term in query_lower]
        
        # Also extract capitalized words that might be drug names
        words = query.split()
        capitalized_words = [word.strip('.,!?') for word in words if word[0].isupper() and len(word) > 2]
        
        # Extract drug codes (NDC patterns)
        import re
        code_patterns = [
            r'\b\d{5}-\d{4}-\d{2}\b',  # NDC codes like 12345-6789-01
            r'\b\d{11}\b',             # 11-digit NDC codes
            r'\b[A-Z]\d{2,3}\b',       # Drug codes like A12, B34
        ]
        
        codes = []
        for pattern in code_patterns:
            codes.extend(re.findall(pattern, query))
        
        # Combine all terms
        all_terms = found_terms + capitalized_words[:5] + codes[:5]  # Limit to avoid too many terms
        
        return list(set(all_terms))  # Remove duplicates
    
    async def search_products(self, query: str, max_results: int = 50) -> List[ProductResult]:
        """Search pharmaceutical products by name, therapeutic area, or class"""
        try:
            query_lower = query.lower()
            results = []
            
            # Search by product name (default for drug names)
            drug_terms = self._extract_drug_terms(query)
            
            if drug_terms:
                # Find matching products using bracket pattern search
                matching_products = pd.DataFrame()
                for term in drug_terms:
                    # Strategy 1: Search for brand name in brackets [brandname]
                    bracket_pattern = f"[{term}]"
                    bracket_matches = self.product_brand_df[
                        self.product_brand_df['Productbrandname'].astype(str).str.contains(bracket_pattern, case=False, na=False, regex=False)
                    ]
                    if not bracket_matches.empty:
                        matching_products = pd.concat([matching_products, bracket_matches]).drop_duplicates(subset=['ProductbrandID'])
                        continue
                    
                    # Strategy 2: Search for term anywhere in product name
                    term_matches = self.product_brand_df[
                        self.product_brand_df['Productbrandname'].astype(str).str.contains(term, case=False, na=False, regex=False)
                    ]
                    if not term_matches.empty:
                        matching_products = pd.concat([matching_products, term_matches]).drop_duplicates(subset=['ProductbrandID'])
                
                for _, row in matching_products.head(max_results).iterrows():
                    results.append(ProductResult(
                        product_id=str(row['ProductbrandID']),
                        brand_name=row['Productbrandname'],
                        market_id=str(row['MarketID']) if pd.notna(row['MarketID']) else '9999',
                        competitor_flag=row['Competitorflag'],
                        category=str(row['Category']) if pd.notna(row['Category']) else 'Unknown',
                        metadata={'source': 'payer_data'}
                    ))
            
            # If no drug terms found, search by therapeutic area
            elif any(term in query_lower for term in ['therapeutic', 'indication', 'condition']):
                # Find matching therapeutic areas
                matching_areas = self.therapeutic_area_df[
                    self.therapeutic_area_df['Therapeuticareavalue'].str.lower().str.contains(query_lower, na=False)
                ]
                
                if not matching_areas.empty:
                    # Get products in these therapeutic areas
                    area_ids = matching_areas['TherapeuticareaID'].tolist()
                    
                    # Use relationship table if available
                    if hasattr(self, 'product_brand_therapeutic_df'):
                        product_relationships = self.product_brand_therapeutic_df[
                            self.product_brand_therapeutic_df['TherapeuticareaID'].isin(area_ids)
                        ]
                        product_ids = product_relationships['ProductbrandID'].tolist()
                        
                        matching_products = self.product_brand_df[
                            self.product_brand_df['ProductbrandID'].isin(product_ids)
                        ]
                        
                        for _, row in matching_products.head(max_results).iterrows():
                            results.append(ProductResult(
                                product_id=str(row['ProductbrandID']),
                                brand_name=row['Productbrandname'],
                                market_id=str(row['MarketID']) if pd.notna(row['MarketID']) else '9999',
                                competitor_flag=row['Competitorflag'],
                                category=str(row['Category']) if pd.notna(row['Category']) else 'Unknown',
                                metadata={'source': 'payer_data', 'therapeutic_area': 'matched'}
                            ))
            
            return results
            
        except Exception as e:
            log_error(e, f"Product search failed for query: {query}")
            return []
    
    async def search_sales_data(self, query: str, max_results: int = 50) -> List[SalesResult]:
        """Search sales data by product, customer, or time period"""
        try:
            if self.sales_df is None:
                return []
            
            query_lower = query.lower()
            results = []
            
            # Search by product
            if any(term in query_lower for term in ['sales', 'prescription', 'volume', 'revenue']):
                # Extract product terms
                drug_terms = self._extract_drug_terms(query)
                
                if drug_terms:
                    # Find matching products
                    matching_products = self.product_brand_df[
                        self.product_brand_df['Productbrandname'].str.lower().str.contains('|'.join(drug_terms), na=False)
                    ]
                    
                    if not matching_products.empty:
                        product_ids = matching_products['ProductbrandID'].tolist()
                        
                        # Get sales data for these products
                        sales_matches = self.sales_df[
                            self.sales_df['productgroupid'].isin(product_ids)
                        ]
                        
                        # Group by product and calculate totals
                        grouped = sales_matches.groupby('productgroupid').agg({
                            'newrxcount': 'sum',
                            'refillrxcount': 'sum',
                            'totalrxcount': 'sum',
                            'wac_dollars': 'sum',
                            'volume_units': 'sum'
                        }).reset_index()
                        
                        for _, row in grouped.head(max_results).iterrows():
                            results.append(SalesResult(
                                product_id=row['productgroupid'],
                                new_rx_count=row['newrxcount'],
                                refill_rx_count=row['refillrxcount'],
                                total_rx_count=row['totalrxcount'],
                                wac_dollars=row['wac_dollars'],
                                volume_units=row['volume_units'],
                                metadata={'source': 'payer_data'}
                            ))
            
            return results
            
        except Exception as e:
            log_error(e, f"Sales data search failed for query: {query}")
            return []
    
    async def search_payer_plans(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Search payer plan data by plan name, type, or formulary tier"""
        try:
            query_lower = query.lower()
            results = []
            
            # Search by plan name
            if any(term in query_lower for term in ['plan', 'payer', 'insurance', 'formulary']):
                # Find matching plans
                matching_plans = self.payer_plan_df[
                    self.payer_plan_df['PayerPlanName'].str.lower().str.contains(query_lower, na=False)
                ]
                
                for _, row in matching_plans.head(max_results).iterrows():
                    results.append({
                        'payer_plan_id': row['PayerPlanID'],
                        'payer_plan_name': row['PayerPlanName'],
                        'payer_id': row['PayerID'],
                        'plan_type': row.get('PlanType', ''),
                        'metadata': {'source': 'payer_data'}
                    })
            
            # Search by formulary tier
            elif 'tier' in query_lower:
                # Find matching formulary tiers
                matching_tiers = self.formulary_tier_df[
                    self.formulary_tier_df['TierName'].str.lower().str.contains(query_lower, na=False)
                ]
                
                for _, row in matching_tiers.head(max_results).iterrows():
                    results.append({
                        'tier_id': row['TierID'],
                        'tier_name': row['TierName'],
                        'tier_description': row.get('TierDescription', ''),
                        'metadata': {'source': 'payer_data'}
                    })
            
            return results
            
        except Exception as e:
            log_error(e, f"Payer plan search failed for query: {query}")
            return []
    
    async def get_market_analysis(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Analyze market data by therapeutic area, product group, or customer segment"""
        try:
            query_lower = query.lower()
            results = []
            
            # Analyze by therapeutic area
            if 'therapeutic' in query_lower or 'market' in query_lower:
                # Group products by therapeutic area
                if hasattr(self, 'product_brand_therapeutic_df'):
                    grouped = self.product_brand_therapeutic_df.groupby('TherapeuticareaID').size().reset_index(name='product_count')
                    
                    # Merge with therapeutic area names
                    merged = grouped.merge(
                        self.therapeutic_area_df[['TherapeuticareaID', 'Therapeuticareavalue']], 
                        on='TherapeuticareaID', 
                        how='left'
                    )
                    
                    for _, row in merged.head(max_results).iterrows():
                        results.append({
                            'therapeutic_area_id': row['TherapeuticareaID'],
                            'therapeutic_area_name': row['Therapeuticareavalue'],
                            'product_count': row['product_count'],
                            'metadata': {'source': 'payer_data'}
                        })
            
            # Analyze by product group
            elif 'product group' in query_lower:
                grouped = self.product_group_df.groupby('ProductGroupName').size().reset_index(name='count')
                
                for _, row in grouped.head(max_results).iterrows():
                    results.append({
                        'product_group_name': row['ProductGroupName'],
                        'count': row['count'],
                        'metadata': {'source': 'payer_data'}
                    })
            
            # Analyze by customer type
            elif 'customer' in query_lower or 'provider' in query_lower:
                grouped = self.customer_df.groupby('Customertype').size().reset_index(name='count')
                
                for _, row in grouped.head(max_results).iterrows():
                    results.append({
                        'customer_type': row['Customertype'],
                        'count': row['count'],
                        'metadata': {'source': 'payer_data'}
                    })
            
            return results
            
        except Exception as e:
            log_error(e, f"Market analysis failed for query: {query}")
            return []
    
    async def get_competitive_analysis(self, query: str, max_results: int = 50) -> List[Dict[str, Any]]:
        """Analyze competitive landscape by therapeutic area or product class"""
        try:
            query_lower = query.lower()
            results = []
            
            # Analyze competitors by therapeutic area
            if 'competitor' in query_lower or 'competitive' in query_lower:
                # Get products marked as competitors
                competitor_products = self.product_brand_df[
                    self.product_brand_df['Competitorflag'] == 'Y'
                ]
                
                # Group by therapeutic area if relationship available
                if hasattr(self, 'product_brand_therapeutic_df'):
                    competitor_relationships = self.product_brand_therapeutic_df[
                        self.product_brand_therapeutic_df['ProductbrandID'].isin(competitor_products['ProductbrandID'])
                    ]
                    
                    grouped = competitor_relationships.groupby('TherapeuticareaID').size().reset_index(name='competitor_count')
                    
                    # Merge with therapeutic area names
                    merged = grouped.merge(
                        self.therapeutic_area_df[['TherapeuticareaID', 'Therapeuticareavalue']], 
                        on='TherapeuticareaID', 
                        how='left'
                    )
                    
                    for _, row in merged.head(max_results).iterrows():
                        results.append({
                            'therapeutic_area_id': row['TherapeuticareaID'],
                            'therapeutic_area_name': row['Therapeuticareavalue'],
                            'competitor_count': row['competitor_count'],
                            'metadata': {'source': 'payer_data'}
                        })
                else:
                    # Simple competitor count
                    competitor_count = len(competitor_products)
                    results.append({
                        'total_competitors': competitor_count,
                        'metadata': {'source': 'payer_data'}
                    })
            
            return results
            
        except Exception as e:
            log_error(e, f"Competitive analysis failed for query: {query}")
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

# Create global instance
payer_data_agent = PayerDataAgent()
