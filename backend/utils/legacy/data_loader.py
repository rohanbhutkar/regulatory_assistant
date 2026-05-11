from pathlib import PurePosixPath
from typing import Any, Dict

import pandas as pd

from utils.json_utils import clean_dataframe_for_json
from utils.regulatory_data_io import (
    list_regulatory_dir,
    read_regulatory_csv,
    read_regulatory_excel,
)


class DataLoader:
    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.loaded = False

    async def load_all_data(self):
        """Load all CSV data at startup for fast access"""
        if self.loaded:
            return

        print("Loading TrialTrove data...")
        try:
            trial_df = read_regulatory_csv("combined_trial_trove.csv")
            self.cache["trialtrove"] = clean_dataframe_for_json(trial_df)
            print(f"Loaded {len(self.cache['trialtrove'])} trials")
        except Exception as e:
            print(f"Warning: Could not load TrialTrove data: {e}")
            self.cache["trialtrove"] = pd.DataFrame()

        print("Loading SiteTrove data...")
        try:
            site_df = read_regulatory_csv("combined_site_trove.csv")
            self.cache["sitetrove"] = clean_dataframe_for_json(site_df)
            print(f"Loaded {len(self.cache['sitetrove'])} sites")
        except Exception as e:
            print(f"Warning: Could not load SiteTrove data: {e}")
            self.cache["sitetrove"] = pd.DataFrame()

        print("Loading Claims data...")
        try:
            claims_df = read_regulatory_csv("claims/combined_claims.csv")
            self.cache["claims"] = clean_dataframe_for_json(claims_df)
            print(f"Loaded {len(self.cache['claims'])} claims")
        except Exception as e:
            print(f"Warning: Could not load Claims data: {e}")
            self.cache["claims"] = pd.DataFrame()

        print("Loading Payer data...")
        self.cache["payer_data"] = {}
        for rel in list_regulatory_dir("payer_data", ".csv"):
            name = PurePosixPath(rel).stem
            try:
                payer_df = read_regulatory_csv(rel)
                self.cache["payer_data"][name] = clean_dataframe_for_json(payer_df)
                print(f"Loaded {name}: {len(self.cache['payer_data'][name])} rows")
            except Exception as e:
                print(f"Warning: Could not load {name}: {e}")

        print("Loading FDA Labels...")
        try:
            fda_df = read_regulatory_excel("FDA_Structured_Labels.xlsx")
            self.cache["fda_labels"] = clean_dataframe_for_json(fda_df)
            print(f"Loaded {len(self.cache['fda_labels'])} FDA labels")
        except Exception as e:
            print(f"Warning: Could not load FDA Labels: {e}")
            self.cache["fda_labels"] = pd.DataFrame()

        self.loaded = True
        print(f"Data loading complete. Loaded {len(self.cache)} data sources")

    def get_data(self, source: str) -> pd.DataFrame:
        """Get cached data"""
        return self.cache.get(source, pd.DataFrame())

    def get_payer_data(self, table_name: str) -> pd.DataFrame:
        """Get specific payer data table"""
        return self.cache["payer_data"].get(table_name, pd.DataFrame())

    def search_trials(self, filters: Dict[str, Any]) -> pd.DataFrame:
        """Search trials with filters"""
        df = self.cache["trialtrove"]
        if df.empty:
            return df

        for key, value in filters.items():
            if key in df.columns and value:
                df = df[df[key].astype(str).str.contains(str(value), case=False, na=False)]
        return df

    def search_sites(self, filters: Dict[str, Any]) -> pd.DataFrame:
        """Search sites with filters"""
        df = self.cache["sitetrove"]
        if df.empty:
            return df

        for key, value in filters.items():
            if key in df.columns and value:
                df = df[df[key].astype(str).str.contains(str(value), case=False, na=False)]
        return df

    def get_claims_data(self, filters: Dict[str, Any] = None) -> pd.DataFrame:
        """Get claims data with optional filters"""
        df = self.cache["claims"]
        if df.empty or not filters:
            return df

        for key, value in filters.items():
            if key in df.columns and value:
                df = df[df[key].astype(str).str.contains(str(value), case=False, na=False)]
        return df
