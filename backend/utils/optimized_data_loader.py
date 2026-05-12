import asyncio
from pathlib import PurePosixPath
from typing import Any, Dict, Optional

import pandas as pd

from utils.json_utils import clean_dataframe_for_json
from utils.regulatory_data_io import (
    list_regulatory_dir,
    read_regulatory_csv,
    read_regulatory_excel,
    regulatory_file_exists,
)


class OptimizedDataLoader:
    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.loaded = False
        self.essential_data_loaded = False

    def _load_essential_data_blocking(self) -> None:
        """CPU/IO-bound essential load; run via asyncio.to_thread so the event loop can serve probes."""
        if self.essential_data_loaded:
            return

        print("🚀 Loading essential data for fast startup...")

        print("Loading TrialTrove data...")
        try:
            trial_df = read_regulatory_csv("combined_trial_trove.csv", low_memory=False)
            self.cache["trialtrove"] = clean_dataframe_for_json(trial_df)
            print(f"✅ Loaded {len(self.cache['trialtrove'])} trials")
        except Exception as e:
            print(f"⚠️ Warning: Could not load TrialTrove data: {e}")
            self.cache["trialtrove"] = pd.DataFrame()

        print("Loading SiteTrove data...")
        try:
            site_df = read_regulatory_csv("combined_site_trove.csv", low_memory=False)
            self.cache["sitetrove"] = clean_dataframe_for_json(site_df)
            print(f"✅ Loaded {len(self.cache['sitetrove'])} sites")
        except Exception as e:
            print(f"⚠️ Warning: Could not load SiteTrove data: {e}")
            self.cache["sitetrove"] = pd.DataFrame()

        print("Loading sample Claims data...")
        try:
            claims_df = read_regulatory_csv(
                "claims/combined_claims.csv", nrows=10000, low_memory=False
            )
            self.cache["claims"] = clean_dataframe_for_json(claims_df)
            print(f"✅ Loaded {len(self.cache['claims'])} sample claims")
        except Exception as e:
            print(f"⚠️ Warning: Could not load Claims data: {e}")
            self.cache["claims"] = pd.DataFrame()

        print("Loading FDA Labels...")
        try:
            fda_df = read_regulatory_excel("FDA_Structured_Labels.xlsx")
            self.cache["fda_labels"] = clean_dataframe_for_json(fda_df)
            print(f"✅ Loaded {len(self.cache['fda_labels'])} FDA labels")
        except Exception as e:
            print(f"⚠️ Warning: Could not load FDA Labels: {e}")
            self.cache["fda_labels"] = pd.DataFrame()

        self.cache["payer_data"] = {}
        self.cache["cpp_data"] = {}

        self.essential_data_loaded = True
        print("🎉 Essential data loading complete! Ready for demo.")

    async def load_essential_data(self):
        """Load only essential data for demo - fast startup"""
        if self.essential_data_loaded:
            return
        await asyncio.to_thread(self._load_essential_data_blocking)

    def _load_all_data_blocking(self) -> None:
        if self.loaded:
            return

        print("📊 Loading complete dataset (this may take a while)...")

        self._load_essential_data_blocking()

        print("Loading full Claims data...")
        try:
            claims_df = read_regulatory_csv("claims/combined_claims.csv", low_memory=False)
            self.cache["claims"] = clean_dataframe_for_json(claims_df)
            print(f"✅ Loaded {len(self.cache['claims'])} total claims")
        except Exception as e:
            print(f"⚠️ Warning: Could not load full Claims data: {e}")

        print("Loading Payer data...")
        self.cache["payer_data"] = {}
        for rel in list_regulatory_dir("payer_data", ".csv"):
            name = PurePosixPath(rel).stem
            try:
                payer_df = read_regulatory_csv(rel, low_memory=False)
                self.cache["payer_data"][name] = clean_dataframe_for_json(payer_df)
                print(f"✅ Loaded {name}: {len(self.cache['payer_data'][name])} rows")
            except Exception as e:
                print(f"⚠️ Warning: Could not load {name}: {e}")

        print("Initializing CPP data cache...")
        self.cache["cpp_data"] = {}

        cpp_files = [
            ("spu", "cpp/spu/Reference_SPU_All_Countries_2025.csv"),
            ("drug_costs", "cpp/drugs/Reference_Drug_Costs_2024_Q1_Historical.csv"),
            ("country_specs", "cpp/rules/Reference_Country_Specifications.csv"),
            ("indications", "cpp/rules/Reference_Indications_2025_Q1.csv"),
        ]
        for label, rel in cpp_files:
            if not regulatory_file_exists(rel):
                continue
            try:
                df = read_regulatory_csv(rel, low_memory=False)
                self.cache["cpp_data"][label] = clean_dataframe_for_json(df)
                print(f"✅ Loaded {label}: {len(self.cache['cpp_data'][label])} rows")
            except Exception as e:
                print(f"⚠️ Warning: Could not load {label}: {e}")

        self.loaded = True
        print("🎉 Complete data loading finished!")

    async def load_all_data(self):
        """Load all CSV data - full dataset (slower startup)"""
        if self.loaded:
            return
        await asyncio.to_thread(self._load_all_data_blocking)

    def get_data(self, source: str) -> pd.DataFrame:
        """Get cached data"""
        data = self.cache.get(source)
        if data is None:
            return pd.DataFrame()
        if isinstance(data, dict):
            return pd.DataFrame()
        return data if isinstance(data, pd.DataFrame) else pd.DataFrame()

    def get_payer_data(self, table_name: str) -> pd.DataFrame:
        """Get specific payer data table (loads on demand if not cached)"""
        if "payer_data" not in self.cache:
            self.cache["payer_data"] = {}

        if table_name not in self.cache["payer_data"]:
            rel = f"payer_data/{table_name}.csv"
            if not regulatory_file_exists(rel):
                return pd.DataFrame()
            try:
                payer_df = read_regulatory_csv(rel, low_memory=False)
                self.cache["payer_data"][table_name] = clean_dataframe_for_json(payer_df)
                print(
                    f"📊 Loaded {table_name} on demand: {len(self.cache['payer_data'][table_name])} rows"
                )
            except Exception as e:
                print(f"⚠️ Warning: Could not load {table_name}: {e}")
                return pd.DataFrame()

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
        if data_type in self.cache.get("cpp_data", {}):
            return self.cache["cpp_data"][data_type]

        file_map = {
            "spu": "cpp/spu/Reference_SPU_All_Countries_2025.csv",
            "drug_costs": "cpp/drugs/Reference_Drug_Costs_2024_Q1_Historical.csv",
            "country_specs": "cpp/rules/Reference_Country_Specifications.csv",
            "indications": "cpp/rules/Reference_Indications_2025_Q1.csv",
            "clinical_procedures": "cpp/clinical_procedures/Reference_Clinical_Procedures_2025_Q2.csv",
            "odcs": "cpp/odcs/Reference_ODCs_2025_Q2.csv",
        }

        rel = file_map.get(data_type)
        if rel and regulatory_file_exists(rel):
            try:
                df = read_regulatory_csv(rel, low_memory=False)
                if "cpp_data" not in self.cache:
                    self.cache["cpp_data"] = {}
                self.cache["cpp_data"][data_type] = clean_dataframe_for_json(df)
                print(f"📊 Loaded CPP {data_type} on demand: {len(df)} rows")
                return self.cache["cpp_data"][data_type]
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
