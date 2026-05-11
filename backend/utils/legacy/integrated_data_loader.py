#!/usr/bin/env python3
"""
Integrated Data Loader for Clinical Knowledge Agent Platform
Integrates with all clinical knowledge agent components
"""
import pandas as pd
import os
import sys
from typing import Dict, Any, List
import asyncio
from pathlib import Path
import logging

# Add the clinical_knowledge_agent to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'clinical_knowledge_agent'))

from utils.json_utils import clean_dataframe_for_json, dataframe_to_dict_safe

logger = logging.getLogger(__name__)

class IntegratedDataLoader:
    def __init__(self):
        self.data_path = Path("../data")
        self.cache = {}
        self.loaded_flags = {
            'trialtrove': False,
            'sitetrove': False,
            'claims': False,
            'payer_data': False,
            'fda_labels': False
        }
        self.min_year = 2021  # For filtering trials

    async def load_essential_data(self):
        """Load essential data (trials, sites) at startup for fast access."""
        logger.info("⚡ Integrated data loading - loading essential data only...")
        await self._load_trialtrove_data()
        await self._load_sitetrove_data()
        logger.info("✅ Essential data loaded successfully!")

    async def load_all_data(self):
        """Load all data sources for comprehensive access."""
        logger.info("📊 Loading all data sources...")
        await self._load_trialtrove_data()
        await self._load_sitetrove_data()
        await self._load_claims_data()
        await self._load_payer_data()
        await self._load_fda_labels()
        logger.info("✅ All data loaded successfully!")

    async def _load_trialtrove_data(self):
        if self.loaded_flags['trialtrove']:
            return
        try:
            logger.info("📊 Loading TrialTrove data (filtered)...")
            df = pd.read_csv(self.data_path / "combined_trial_trove.csv", low_memory=False)
            df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
            df = df[df['Start Date'].dt.year >= self.min_year]
            df = clean_dataframe_for_json(df)
            self.cache['trialtrove'] = df.to_dict('records')
            self.loaded_flags['trialtrove'] = True
            logger.info(f"✅ Loaded {len(self.cache['trialtrove'])} recent trials")
        except Exception as e:
            logger.error(f"❌ Error loading TrialTrove data: {e}")
            self.cache['trialtrove'] = []

    async def _load_sitetrove_data(self):
        if self.loaded_flags['sitetrove']:
            return
        try:
            logger.info("🏥 Loading SiteTrove data...")
            df = pd.read_csv(self.data_path / "combined_site_trove.csv", low_memory=False)
            df = clean_dataframe_for_json(df)
            self.cache['sitetrove'] = df.to_dict('records')
            self.loaded_flags['sitetrove'] = True
            logger.info(f"✅ Loaded {len(self.cache['sitetrove'])} sites")
        except Exception as e:
            logger.error(f"❌ Error loading SiteTrove data: {e}")
            self.cache['sitetrove'] = []

    async def _load_claims_data(self):
        if self.loaded_flags['claims']:
            return
        try:
            logger.info("💰 Loading Claims data (lazy)...")
            df = pd.read_csv(self.data_path / "claims" / "combined_claims.csv", low_memory=False)
            df = clean_dataframe_for_json(df)
            self.cache['claims'] = df.to_dict('records')
            self.loaded_flags['claims'] = True
            logger.info(f"✅ Loaded {len(self.cache['claims'])} claims records")
        except Exception as e:
            logger.error(f"❌ Error loading Claims data: {e}")
            self.cache['claims'] = []

    async def _load_payer_data(self):
        if self.loaded_flags['payer_data']:
            return
        try:
            logger.info("💵 Loading Payer data (lazy)...")
            payer_path = self.data_path / "payer_data"
            self.cache['payer_data'] = {}
            for csv_file in payer_path.glob("*.csv"):
                name = csv_file.stem
                df = pd.read_csv(csv_file, low_memory=False)
                df = clean_dataframe_for_json(df)
                self.cache['payer_data'][name] = df.to_dict('records')
            self.loaded_flags['payer_data'] = True
            logger.info(f"✅ Loaded {len(self.cache['payer_data'])} payer data tables")
        except Exception as e:
            logger.error(f"❌ Error loading Payer data: {e}")
            self.cache['payer_data'] = {}

    async def _load_fda_labels(self):
        if self.loaded_flags['fda_labels']:
            return
        try:
            logger.info("📄 Loading FDA Labels (lazy)...")
            df = pd.read_excel(self.data_path / "FDA_Structured_Labels.xlsx")
            df = clean_dataframe_for_json(df)
            self.cache['fda_labels'] = df.to_dict('records')
            self.loaded_flags['fda_labels'] = True
            logger.info(f"✅ Loaded {len(self.cache['fda_labels'])} FDA labels")
        except Exception as e:
            logger.error(f"❌ Error loading FDA Labels: {e}")
            self.cache['fda_labels'] = []

    async def get_data(self, source: str) -> List[Dict[str, Any]]:
        """Get cached data, loading if not already loaded."""
        if source == 'trialtrove' and not self.loaded_flags['trialtrove']:
            await self._load_trialtrove_data()
        elif source == 'sitetrove' and not self.loaded_flags['sitetrove']:
            await self._load_sitetrove_data()
        elif source == 'claims' and not self.loaded_flags['claims']:
            await self._load_claims_data()
        elif source == 'payer_data' and not self.loaded_flags['payer_data']:
            await self._load_payer_data()
        elif source == 'fda_labels' and not self.loaded_flags['fda_labels']:
            await self._load_fda_labels()
        return self.cache.get(source, [])

    async def search_trials(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search trials with filters, ensuring data is loaded."""
        trials = await self.get_data('trialtrove')
        df = pd.DataFrame(trials)
        if df.empty:
            return []

        for key, value in filters.items():
            if key == 'search_term' and value:
                search_term = str(value).lower()
                df = df[df.astype(str).apply(lambda x: x.str.lower().str.contains(search_term, na=False)).any(axis=1)]
            elif key in df.columns and value:
                df = df[df[key].astype(str).str.contains(str(value), case=False, na=False)]
        return df.to_dict('records')

    async def search_sites(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search sites with filters, ensuring data is loaded."""
        sites = await self.get_data('sitetrove')
        df = pd.DataFrame(sites)
        if df.empty:
            return []

        for key, value in filters.items():
            if key == 'search_term' and value:
                search_term = str(value).lower()
                df = df[df.astype(str).apply(lambda x: x.str.lower().str.contains(search_term, na=False)).any(axis=1)]
            elif key in df.columns and value:
                df = df[df[key].astype(str).str.contains(str(value), case=False, na=False)]
        return df.to_dict('records')

    async def get_claims_data(self) -> List[Dict[str, Any]]:
        """Get claims data, ensuring it's loaded."""
        return await self.get_data('claims')

    async def get_payer_data(self, table_name: str) -> List[Dict[str, Any]]:
        """Get specific payer data table, ensuring it's loaded."""
        payer_data = await self.get_data('payer_data')
        return payer_data.get(table_name, [])

    def get_data_summary(self) -> Dict[str, Any]:
        """Get summary of loaded data."""
        return {
            'loaded_sources': [k for k, v in self.loaded_flags.items() if v],
            'cache_sizes': {k: len(v) if isinstance(v, list) else len(v) if isinstance(v, dict) else 0 
                          for k, v in self.cache.items()},
            'total_records': sum(len(v) if isinstance(v, list) else len(v) if isinstance(v, dict) else 0 
                               for v in self.cache.values())
        }


"""
Integrated Data Loader for Clinical Knowledge Agent Platform
Integrates with all clinical knowledge agent components
"""
import pandas as pd
import os
import sys
from typing import Dict, Any, List
import asyncio
from pathlib import Path
import logging

# Add the clinical_knowledge_agent to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'clinical_knowledge_agent'))

from utils.json_utils import clean_dataframe_for_json, dataframe_to_dict_safe

logger = logging.getLogger(__name__)

class IntegratedDataLoader:
    def __init__(self):
        self.data_path = Path("../data")
        self.cache = {}
        self.loaded_flags = {
            'trialtrove': False,
            'sitetrove': False,
            'claims': False,
            'payer_data': False,
            'fda_labels': False
        }
        self.min_year = 2021  # For filtering trials

    async def load_essential_data(self):
        """Load essential data (trials, sites) at startup for fast access."""
        logger.info("⚡ Integrated data loading - loading essential data only...")
        await self._load_trialtrove_data()
        await self._load_sitetrove_data()
        logger.info("✅ Essential data loaded successfully!")

    async def load_all_data(self):
        """Load all data sources for comprehensive access."""
        logger.info("📊 Loading all data sources...")
        await self._load_trialtrove_data()
        await self._load_sitetrove_data()
        await self._load_claims_data()
        await self._load_payer_data()
        await self._load_fda_labels()
        logger.info("✅ All data loaded successfully!")

    async def _load_trialtrove_data(self):
        if self.loaded_flags['trialtrove']:
            return
        try:
            logger.info("📊 Loading TrialTrove data (filtered)...")
            df = pd.read_csv(self.data_path / "combined_trial_trove.csv", low_memory=False)
            df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
            df = df[df['Start Date'].dt.year >= self.min_year]
            df = clean_dataframe_for_json(df)
            self.cache['trialtrove'] = df.to_dict('records')
            self.loaded_flags['trialtrove'] = True
            logger.info(f"✅ Loaded {len(self.cache['trialtrove'])} recent trials")
        except Exception as e:
            logger.error(f"❌ Error loading TrialTrove data: {e}")
            self.cache['trialtrove'] = []

    async def _load_sitetrove_data(self):
        if self.loaded_flags['sitetrove']:
            return
        try:
            logger.info("🏥 Loading SiteTrove data...")
            df = pd.read_csv(self.data_path / "combined_site_trove.csv", low_memory=False)
            df = clean_dataframe_for_json(df)
            self.cache['sitetrove'] = df.to_dict('records')
            self.loaded_flags['sitetrove'] = True
            logger.info(f"✅ Loaded {len(self.cache['sitetrove'])} sites")
        except Exception as e:
            logger.error(f"❌ Error loading SiteTrove data: {e}")
            self.cache['sitetrove'] = []

    async def _load_claims_data(self):
        if self.loaded_flags['claims']:
            return
        try:
            logger.info("💰 Loading Claims data (lazy)...")
            df = pd.read_csv(self.data_path / "claims" / "combined_claims.csv", low_memory=False)
            df = clean_dataframe_for_json(df)
            self.cache['claims'] = df.to_dict('records')
            self.loaded_flags['claims'] = True
            logger.info(f"✅ Loaded {len(self.cache['claims'])} claims records")
        except Exception as e:
            logger.error(f"❌ Error loading Claims data: {e}")
            self.cache['claims'] = []

    async def _load_payer_data(self):
        if self.loaded_flags['payer_data']:
            return
        try:
            logger.info("💵 Loading Payer data (lazy)...")
            payer_path = self.data_path / "payer_data"
            self.cache['payer_data'] = {}
            for csv_file in payer_path.glob("*.csv"):
                name = csv_file.stem
                df = pd.read_csv(csv_file, low_memory=False)
                df = clean_dataframe_for_json(df)
                self.cache['payer_data'][name] = df.to_dict('records')
            self.loaded_flags['payer_data'] = True
            logger.info(f"✅ Loaded {len(self.cache['payer_data'])} payer data tables")
        except Exception as e:
            logger.error(f"❌ Error loading Payer data: {e}")
            self.cache['payer_data'] = {}

    async def _load_fda_labels(self):
        if self.loaded_flags['fda_labels']:
            return
        try:
            logger.info("📄 Loading FDA Labels (lazy)...")
            df = pd.read_excel(self.data_path / "FDA_Structured_Labels.xlsx")
            df = clean_dataframe_for_json(df)
            self.cache['fda_labels'] = df.to_dict('records')
            self.loaded_flags['fda_labels'] = True
            logger.info(f"✅ Loaded {len(self.cache['fda_labels'])} FDA labels")
        except Exception as e:
            logger.error(f"❌ Error loading FDA Labels: {e}")
            self.cache['fda_labels'] = []

    async def get_data(self, source: str) -> List[Dict[str, Any]]:
        """Get cached data, loading if not already loaded."""
        if source == 'trialtrove' and not self.loaded_flags['trialtrove']:
            await self._load_trialtrove_data()
        elif source == 'sitetrove' and not self.loaded_flags['sitetrove']:
            await self._load_sitetrove_data()
        elif source == 'claims' and not self.loaded_flags['claims']:
            await self._load_claims_data()
        elif source == 'payer_data' and not self.loaded_flags['payer_data']:
            await self._load_payer_data()
        elif source == 'fda_labels' and not self.loaded_flags['fda_labels']:
            await self._load_fda_labels()
        return self.cache.get(source, [])

    async def search_trials(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search trials with filters, ensuring data is loaded."""
        trials = await self.get_data('trialtrove')
        df = pd.DataFrame(trials)
        if df.empty:
            return []

        for key, value in filters.items():
            if key == 'search_term' and value:
                search_term = str(value).lower()
                df = df[df.astype(str).apply(lambda x: x.str.lower().str.contains(search_term, na=False)).any(axis=1)]
            elif key in df.columns and value:
                df = df[df[key].astype(str).str.contains(str(value), case=False, na=False)]
        return df.to_dict('records')

    async def search_sites(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search sites with filters, ensuring data is loaded."""
        sites = await self.get_data('sitetrove')
        df = pd.DataFrame(sites)
        if df.empty:
            return []

        for key, value in filters.items():
            if key == 'search_term' and value:
                search_term = str(value).lower()
                df = df[df.astype(str).apply(lambda x: x.str.lower().str.contains(search_term, na=False)).any(axis=1)]
            elif key in df.columns and value:
                df = df[df[key].astype(str).str.contains(str(value), case=False, na=False)]
        return df.to_dict('records')

    async def get_claims_data(self) -> List[Dict[str, Any]]:
        """Get claims data, ensuring it's loaded."""
        return await self.get_data('claims')

    async def get_payer_data(self, table_name: str) -> List[Dict[str, Any]]:
        """Get specific payer data table, ensuring it's loaded."""
        payer_data = await self.get_data('payer_data')
        return payer_data.get(table_name, [])

    def get_data_summary(self) -> Dict[str, Any]:
        """Get summary of loaded data."""
        return {
            'loaded_sources': [k for k, v in self.loaded_flags.items() if v],
            'cache_sizes': {k: len(v) if isinstance(v, list) else len(v) if isinstance(v, dict) else 0 
                          for k, v in self.cache.items()},
            'total_records': sum(len(v) if isinstance(v, list) else len(v) if isinstance(v, dict) else 0 
                               for v in self.cache.values())
        }

