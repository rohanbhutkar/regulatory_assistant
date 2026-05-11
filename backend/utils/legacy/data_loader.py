import pandas as pd
import os
from typing import Dict, Any, Optional
import asyncio
from pathlib import Path
import numpy as np
from utils.json_utils import clean_dataframe_for_json

class DataLoader:
    def __init__(self):
        self.data_path = Path("data")  # Data is in backend/data
        self.cache = {}
        self.loaded = False
    
    async def load_all_data(self):
        """Load all CSV data at startup for fast access"""
        if self.loaded:
            return
        
        print("Loading TrialTrove data...")
        try:
            trial_df = pd.read_csv(self.data_path / "combined_trial_trove.csv")
            self.cache['trialtrove'] = clean_dataframe_for_json(trial_df)
            print(f"Loaded {len(self.cache['trialtrove'])} trials")
        except Exception as e:
            print(f"Warning: Could not load TrialTrove data: {e}")
            self.cache['trialtrove'] = pd.DataFrame()
        
        print("Loading SiteTrove data...")
        try:
            site_df = pd.read_csv(self.data_path / "combined_site_trove.csv")
            self.cache['sitetrove'] = clean_dataframe_for_json(site_df)
            print(f"Loaded {len(self.cache['sitetrove'])} sites")
        except Exception as e:
            print(f"Warning: Could not load SiteTrove data: {e}")
            self.cache['sitetrove'] = pd.DataFrame()
        
        print("Loading Claims data...")
        try:
            claims_df = pd.read_csv(self.data_path / "claims" / "combined_claims.csv")
            self.cache['claims'] = clean_dataframe_for_json(claims_df)
            print(f"Loaded {len(self.cache['claims'])} claims")
        except Exception as e:
            print(f"Warning: Could not load Claims data: {e}")
            self.cache['claims'] = pd.DataFrame()
        
        print("Loading Payer data...")
        self.cache['payer_data'] = {}
        payer_path = self.data_path / "payer_data"
        if payer_path.exists():
            for csv_file in payer_path.glob("*.csv"):
                name = csv_file.stem
                try:
                    payer_df = pd.read_csv(csv_file)
                    self.cache['payer_data'][name] = clean_dataframe_for_json(payer_df)
                    print(f"Loaded {name}: {len(self.cache['payer_data'][name])} rows")
                except Exception as e:
                    print(f"Warning: Could not load {name}: {e}")
        
        print("Loading FDA Labels...")
        try:
            fda_df = pd.read_excel(self.data_path / "FDA_Structured_Labels.xlsx")
            self.cache['fda_labels'] = clean_dataframe_for_json(fda_df)
            print(f"Loaded {len(self.cache['fda_labels'])} FDA labels")
        except Exception as e:
            print(f"Warning: Could not load FDA Labels: {e}")
            self.cache['fda_labels'] = pd.DataFrame()
        
        self.loaded = True
        print(f"Data loading complete. Loaded {len(self.cache)} data sources")
    
    def get_data(self, source: str) -> pd.DataFrame:
        """Get cached data"""
        return self.cache.get(source, pd.DataFrame())
    
    def get_payer_data(self, table_name: str) -> pd.DataFrame:
        """Get specific payer data table"""
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

from typing import Dict, Any, Optional
import asyncio
from pathlib import Path
import numpy as np
from utils.json_utils import clean_dataframe_for_json

class DataLoader:
    def __init__(self):
        self.data_path = Path("data")  # Data is in backend/data
        self.cache = {}
        self.loaded = False
    
    async def load_all_data(self):
        """Load all CSV data at startup for fast access"""
        if self.loaded:
            return
        
        print("Loading TrialTrove data...")
        try:
            trial_df = pd.read_csv(self.data_path / "combined_trial_trove.csv")
            self.cache['trialtrove'] = clean_dataframe_for_json(trial_df)
            print(f"Loaded {len(self.cache['trialtrove'])} trials")
        except Exception as e:
            print(f"Warning: Could not load TrialTrove data: {e}")
            self.cache['trialtrove'] = pd.DataFrame()
        
        print("Loading SiteTrove data...")
        try:
            site_df = pd.read_csv(self.data_path / "combined_site_trove.csv")
            self.cache['sitetrove'] = clean_dataframe_for_json(site_df)
            print(f"Loaded {len(self.cache['sitetrove'])} sites")
        except Exception as e:
            print(f"Warning: Could not load SiteTrove data: {e}")
            self.cache['sitetrove'] = pd.DataFrame()
        
        print("Loading Claims data...")
        try:
            claims_df = pd.read_csv(self.data_path / "claims" / "combined_claims.csv")
            self.cache['claims'] = clean_dataframe_for_json(claims_df)
            print(f"Loaded {len(self.cache['claims'])} claims")
        except Exception as e:
            print(f"Warning: Could not load Claims data: {e}")
            self.cache['claims'] = pd.DataFrame()
        
        print("Loading Payer data...")
        self.cache['payer_data'] = {}
        payer_path = self.data_path / "payer_data"
        if payer_path.exists():
            for csv_file in payer_path.glob("*.csv"):
                name = csv_file.stem
                try:
                    payer_df = pd.read_csv(csv_file)
                    self.cache['payer_data'][name] = clean_dataframe_for_json(payer_df)
                    print(f"Loaded {name}: {len(self.cache['payer_data'][name])} rows")
                except Exception as e:
                    print(f"Warning: Could not load {name}: {e}")
        
        print("Loading FDA Labels...")
        try:
            fda_df = pd.read_excel(self.data_path / "FDA_Structured_Labels.xlsx")
            self.cache['fda_labels'] = clean_dataframe_for_json(fda_df)
            print(f"Loaded {len(self.cache['fda_labels'])} FDA labels")
        except Exception as e:
            print(f"Warning: Could not load FDA Labels: {e}")
            self.cache['fda_labels'] = pd.DataFrame()
        
        self.loaded = True
        print(f"Data loading complete. Loaded {len(self.cache)} data sources")
    
    def get_data(self, source: str) -> pd.DataFrame:
        """Get cached data"""
        return self.cache.get(source, pd.DataFrame())
    
    def get_payer_data(self, table_name: str) -> pd.DataFrame:
        """Get specific payer data table"""
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
