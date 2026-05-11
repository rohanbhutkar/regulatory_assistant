import pandas as pd
import os
from typing import Dict, Any, Optional
import asyncio
from pathlib import Path
import numpy as np
from utils.json_utils import clean_dataframe_for_json

class OptimizedDataLoader:
    def __init__(self):
        self.data_path = Path("data")  # Data is in backend/data
        self.cache = {}
        self.loaded = False
        self.essential_data_loaded = False
    
    async def load_essential_data(self):
        """Load only essential data for demo - fast startup"""
        if self.essential_data_loaded:
            return
        
        print("🚀 Loading essential data for fast startup...")
        
        # Load TrialTrove data (essential for research agent)
        print("Loading TrialTrove data...")
        try:
            trial_df = pd.read_csv(self.data_path / "combined_trial_trove.csv", low_memory=False)
            self.cache['trialtrove'] = clean_dataframe_for_json(trial_df)
            print(f"✅ Loaded {len(self.cache['trialtrove'])} trials")
        except Exception as e:
            print(f"⚠️ Warning: Could not load TrialTrove data: {e}")
            self.cache['trialtrove'] = pd.DataFrame()
        
        # Load SiteTrove data (essential for site selection)
        print("Loading SiteTrove data...")
        try:
            site_df = pd.read_csv(self.data_path / "combined_site_trove.csv", low_memory=False)
            self.cache['sitetrove'] = clean_dataframe_for_json(site_df)
            print(f"✅ Loaded {len(self.cache['sitetrove'])} sites")
        except Exception as e:
            print(f"⚠️ Warning: Could not load SiteTrove data: {e}")
            self.cache['sitetrove'] = pd.DataFrame()
        
        # Load sample Claims data (not all 2.9M records)
        print("Loading sample Claims data...")
        try:
            claims_df = pd.read_csv(self.data_path / "claims" / "combined_claims.csv", nrows=10000, low_memory=False)
            self.cache['claims'] = clean_dataframe_for_json(claims_df)
            print(f"✅ Loaded {len(self.cache['claims'])} sample claims")
        except Exception as e:
            print(f"⚠️ Warning: Could not load Claims data: {e}")
            self.cache['claims'] = pd.DataFrame()
        
        # Load FDA Labels (usually smaller file)
        print("Loading FDA Labels...")
        try:
            fda_df = pd.read_excel(self.data_path / "FDA_Structured_Labels.xlsx")
            self.cache['fda_labels'] = clean_dataframe_for_json(fda_df)
            print(f"✅ Loaded {len(self.cache['fda_labels'])} FDA labels")
        except Exception as e:
            print(f"⚠️ Warning: Could not load FDA Labels: {e}")
            self.cache['fda_labels'] = pd.DataFrame()
        
        # Initialize empty payer data cache (load on demand)
        self.cache['payer_data'] = {}
        
        # Initialize empty CPP data cache (load on demand)
        self.cache['cpp_data'] = {}
        
        self.essential_data_loaded = True
        print(f"🎉 Essential data loading complete! Ready for demo.")
    
    async def load_all_data(self):
        """Load all CSV data - full dataset (slower startup)"""
        if self.loaded:
            return
        
        print("📊 Loading complete dataset (this may take a while)...")
        
        # Load essential data first
        await self.load_essential_data()
        
        # Load full Claims data
        print("Loading full Claims data...")
        try:
            claims_df = pd.read_csv(self.data_path / "claims" / "combined_claims.csv", low_memory=False)
            self.cache['claims'] = clean_dataframe_for_json(claims_df)
            print(f"✅ Loaded {len(self.cache['claims'])} total claims")
        except Exception as e:
            print(f"⚠️ Warning: Could not load full Claims data: {e}")
        
        # Load Payer data (all files)
        print("Loading Payer data...")
        payer_path = self.data_path / "payer_data"
        if payer_path.exists():
            for csv_file in payer_path.glob("*.csv"):
                name = csv_file.stem
                try:
                    payer_df = pd.read_csv(csv_file, low_memory=False)
                    self.cache['payer_data'][name] = clean_dataframe_for_json(payer_df)
                    print(f"✅ Loaded {name}: {len(self.cache['payer_data'][name])} rows")
                except Exception as e:
                    print(f"⚠️ Warning: Could not load {name}: {e}")
        
        # Load CPP data (on demand, but initialize cache)
        print("Initializing CPP data cache...")
        self.cache['cpp_data'] = {}
        
        # Load key CPP files that are useful for asset strategy
        cpp_path = self.data_path / "cpp"
        if cpp_path.exists():
            # Load SPU (Standard Pricing Units) - useful for international pricing
            spu_file = cpp_path / "spu" / "Reference_SPU_All_Countries_2025.csv"
            if spu_file.exists():
                try:
                    spu_df = pd.read_csv(spu_file, low_memory=False)
                    self.cache['cpp_data']['spu'] = clean_dataframe_for_json(spu_df)
                    print(f"✅ Loaded SPU pricing: {len(self.cache['cpp_data']['spu'])} rows")
                except Exception as e:
                    print(f"⚠️ Warning: Could not load SPU data: {e}")
            
            # Load Drug Costs - useful for comparator pricing
            drug_file = cpp_path / "drugs" / "Reference_Drug_Costs_2024_Q1_Historical.csv"
            if drug_file.exists():
                try:
                    drug_df = pd.read_csv(drug_file, low_memory=False)
                    self.cache['cpp_data']['drug_costs'] = clean_dataframe_for_json(drug_df)
                    print(f"✅ Loaded Drug Costs: {len(self.cache['cpp_data']['drug_costs'])} rows")
                except Exception as e:
                    print(f"⚠️ Warning: Could not load Drug Costs: {e}")
            
            # Load Country Specifications - useful for market-specific analysis
            country_file = cpp_path / "rules" / "Reference_Country_Specifications.csv"
            if country_file.exists():
                try:
                    country_df = pd.read_csv(country_file, low_memory=False)
                    self.cache['cpp_data']['country_specs'] = clean_dataframe_for_json(country_df)
                    print(f"✅ Loaded Country Specifications: {len(self.cache['cpp_data']['country_specs'])} rows")
                except Exception as e:
                    print(f"⚠️ Warning: Could not load Country Specifications: {e}")
            
            # Load Indications - useful for therapeutic area analysis
            indication_file = cpp_path / "rules" / "Reference_Indications_2025_Q1.csv"
            if indication_file.exists():
                try:
                    indication_df = pd.read_csv(indication_file, low_memory=False)
                    self.cache['cpp_data']['indications'] = clean_dataframe_for_json(indication_df)
                    print(f"✅ Loaded Indications: {len(self.cache['cpp_data']['indications'])} rows")
                except Exception as e:
                    print(f"⚠️ Warning: Could not load Indications: {e}")
        
        self.loaded = True
        print(f"🎉 Complete data loading finished!")
    
    def get_data(self, source: str) -> pd.DataFrame:
        """Get cached data"""
        data = self.cache.get(source)
        if data is None:
            return pd.DataFrame()
        # If it's a dictionary (like payer_data or cpp_data), return empty DataFrame
        # Use specific getter methods instead
        if isinstance(data, dict):
            return pd.DataFrame()
        return data if isinstance(data, pd.DataFrame) else pd.DataFrame()
    
    def get_payer_data(self, table_name: str) -> pd.DataFrame:
        """Get specific payer data table (loads on demand if not cached)"""
        # Initialize payer_data cache if it doesn't exist
        if 'payer_data' not in self.cache:
            self.cache['payer_data'] = {}
        
        if table_name not in self.cache['payer_data']:
            # Load on demand
            payer_path = self.data_path / "payer_data" / f"{table_name}.csv"
            if payer_path.exists():
                try:
                    payer_df = pd.read_csv(payer_path, low_memory=False)
                    self.cache['payer_data'][table_name] = clean_dataframe_for_json(payer_df)
                    print(f"📊 Loaded {table_name} on demand: {len(self.cache['payer_data'][table_name])} rows")
                except Exception as e:
                    print(f"⚠️ Warning: Could not load {table_name}: {e}")
                    return pd.DataFrame()
            else:
                return pd.DataFrame()
        
        return self.cache['payer_data'].get(table_name, pd.DataFrame())
    
    def search_trials(self, filters: Dict[str, Any]) -> pd.DataFrame:
        """Search trials with filters"""
        df = self.cache['trialtrove']
        if df.empty:
            return df
            
        for key, value in filters.items():
            if key in df.columns and value:
                df = df[df[key].astype(str).str.contains(str(value), case=False, na=False)]
        return df
    
    def search_sites(self, filters: Dict[str, Any]) -> pd.DataFrame:
        """Search sites with filters"""
        df = self.cache['sitetrove']
        if df.empty:
            return df
            
        for key, value in filters.items():
            if key in df.columns and value:
                df = df[df[key].astype(str).str.contains(str(value), case=False, na=False)]
        return df
    
    def get_claims_data(self, filters: Dict[str, Any] = None) -> pd.DataFrame:
        """Get claims data with optional filters"""
        df = self.cache['claims']
        if df.empty or not filters:
            return df
            
        for key, value in filters.items():
            if key in df.columns and value:
                df = df[df[key].astype(str).str.contains(str(value), case=False, na=False)]
        return df
    
    def get_cpp_data(self, data_type: str) -> pd.DataFrame:
        """
        Get CPP (Comprehensive Patient Protocol) data
        
        Available types:
        - 'spu': Standard Pricing Units (FMV pricing by country)
        - 'drug_costs': Historical drug costs
        - 'country_specs': Country-specific specifications
        - 'indications': Indication-specific rules
        - 'clinical_procedures': Clinical procedure codes
        - 'odcs': Other Direct Costs
        """
        if data_type in self.cache.get('cpp_data', {}):
            return self.cache['cpp_data'][data_type]
        
        # Load on demand if not cached
        cpp_path = self.data_path / "cpp"
        file_map = {
            'spu': cpp_path / "spu" / "Reference_SPU_All_Countries_2025.csv",
            'drug_costs': cpp_path / "drugs" / "Reference_Drug_Costs_2024_Q1_Historical.csv",
            'country_specs': cpp_path / "rules" / "Reference_Country_Specifications.csv",
            'indications': cpp_path / "rules" / "Reference_Indications_2025_Q1.csv",
            'clinical_procedures': cpp_path / "clinical_procedures" / "Reference_Clinical_Procedures_2025_Q2.csv",
            'odcs': cpp_path / "odcs" / "Reference_ODCs_2025_Q2.csv"
        }
        
        if data_type in file_map and file_map[data_type].exists():
            try:
                df = pd.read_csv(file_map[data_type], low_memory=False)
                if 'cpp_data' not in self.cache:
                    self.cache['cpp_data'] = {}
                self.cache['cpp_data'][data_type] = clean_dataframe_for_json(df)
                print(f"📊 Loaded CPP {data_type} on demand: {len(df)} rows")
                return self.cache['cpp_data'][data_type]
            except Exception as e:
                print(f"⚠️ Warning: Could not load CPP {data_type}: {e}")
                return pd.DataFrame()
        
        return pd.DataFrame()
    
    def get_formulary_tier_data(self) -> pd.DataFrame:
        """Get US formulary tier data (useful for US GTN calculations)"""
        return self.get_payer_data("Formulary_Tier_Dim")
    
    def get_therapeutic_area_data(self) -> pd.DataFrame:
        """Get therapeutic area dimension data (useful for indication normalization)"""
        return self.get_payer_data("Therapeuticarea_Dim")
    
    def get_product_brand_data(self) -> pd.DataFrame:
        """Get product brand data (useful for comparator identification)"""
        return self.get_payer_data("Productbrand_Dim")
    
    def get_geography_data(self) -> pd.DataFrame:
        """Get geography dimension data (useful for market analysis)"""
        return self.get_payer_data("Geography_Dim")
from typing import Dict, Any, Optional
import asyncio
from pathlib import Path
import numpy as np
from utils.json_utils import clean_dataframe_for_json











