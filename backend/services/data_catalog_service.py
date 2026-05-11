"""
Data Catalog Service - Source registration, coverage analysis, usage tracking
Enhanced with auto-registration of data sources from OptimizedDataLoader
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
from utils.optimized_data_loader import OptimizedDataLoader
import logging

logger = logging.getLogger(__name__)


class DataCatalogService:
    """Service for managing data source catalog with auto-registration"""
    
    def __init__(self, data_loader: Optional[OptimizedDataLoader] = None):
        # In-memory storage
        self._data_sources: Dict[str, Dict[str, Any]] = {}
        self._source_usage: Dict[str, List[str]] = {}  # source_id -> list of asset_ids
        self.data_loader = data_loader
        self._initialized = False
    
    def initialize_from_data_loader(self, data_loader: OptimizedDataLoader):
        """Auto-register all data sources from OptimizedDataLoader"""
        if self._initialized:
            return
        
        self.data_loader = data_loader
        
        # Register static data sources
        static_sources = [
            {
                "name": "TrialTrove",
                "type": "clinical_trials",
                "coverage": {"markets": ["global"], "therapeutic_areas": ["all"]},
                "description": "Proprietary clinical trials database with drug, indication, and trial data"
            },
            {
                "name": "SiteTrove",
                "type": "site_performance",
                "coverage": {"markets": ["global"], "therapeutic_areas": ["all"]},
                "description": "Site location and performance data for trial site selection"
            },
            {
                "name": "FDA Structured Labels",
                "type": "regulatory",
                "coverage": {"markets": ["US"], "therapeutic_areas": ["all"]},
                "description": "FDA drug labels with structured data (MOA, indications, subpopulations)"
            },
            {
                "name": "Claims Data",
                "type": "claims",
                "coverage": {"markets": ["US"], "therapeutic_areas": ["all"]},
                "description": "Healthcare claims data for utilization and cost analysis"
            },
            {
                "name": "Payer Data",
                "type": "payer",
                "coverage": {"markets": ["US"], "therapeutic_areas": ["all"]},
                "description": "Payer formulary, sales, and rebate data"
            }
        ]
        
        for source_info in static_sources:
            self.register_source(
                name=source_info["name"],
                source_type=source_info["type"],
                owner="system",
                refresh_frequency="quarterly",
                coverage=source_info["coverage"]
            )
        
        # Register CPP data sources
        cpp_sources = [
            {
                "name": "SPU (Standard Pricing Units)",
                "type": "pricing",
                "coverage": {"markets": ["global"], "therapeutic_areas": ["all"]},
                "description": "Fair Market Value (FMV) pricing by country for international market analysis"
            },
            {
                "name": "CPP Drug Costs",
                "type": "pricing",
                "coverage": {"markets": ["global"], "therapeutic_areas": ["all"]},
                "description": "Historical drug costs for comparator pricing benchmarks"
            },
            {
                "name": "CPP Country Specifications",
                "type": "market_rules",
                "coverage": {"markets": ["global"], "therapeutic_areas": ["all"]},
                "description": "Country-specific rules and adjustments for market analysis"
            },
            {
                "name": "CPP Indications",
                "type": "therapeutic_area",
                "coverage": {"markets": ["global"], "therapeutic_areas": ["all"]},
                "description": "Indication-specific rules for therapeutic area analysis"
            }
        ]
        
        for source_info in cpp_sources:
            self.register_source(
                name=source_info["name"],
                source_type=source_info["type"],
                owner="system",
                refresh_frequency="quarterly",
                coverage=source_info["coverage"]
            )
        
        # Register key payer dimension tables
        payer_dim_sources = [
            {
                "name": "Formulary Tier Data",
                "type": "formulary",
                "coverage": {"markets": ["US"], "therapeutic_areas": ["all"]},
                "description": "US formulary tiering data for GTN calculations"
            },
            {
                "name": "Therapeutic Area Dimension",
                "type": "therapeutic_area",
                "coverage": {"markets": ["US"], "therapeutic_areas": ["all"]},
                "description": "Therapeutic area taxonomy for indication normalization"
            },
            {
                "name": "Product Brand Dimension",
                "type": "products",
                "coverage": {"markets": ["US"], "therapeutic_areas": ["all"]},
                "description": "Product brand catalog for comparator identification"
            },
            {
                "name": "Geography Dimension",
                "type": "geography",
                "coverage": {"markets": ["US"], "therapeutic_areas": ["all"]},
                "description": "Geographic dimension data for market analysis"
            }
        ]
        
        for source_info in payer_dim_sources:
            self.register_source(
                name=source_info["name"],
                source_type=source_info["type"],
                owner="system",
                refresh_frequency="monthly",
                coverage=source_info["coverage"]
            )
        
        # Register graph backend agents as data sources
        agent_sources = [
            {
                "name": "Google Search",
                "type": "web_search",
                "coverage": {"markets": ["global"], "therapeutic_areas": ["all"]},
                "description": "Real-time web search for pharma news, pricing, regulatory updates"
            },
            {
                "name": "GoodRx Price Search",
                "type": "pricing",
                "coverage": {"markets": ["US"], "therapeutic_areas": ["all"]},
                "description": "Real-time drug pricing from GoodRx.com"
            },
            {
                "name": "PubMed",
                "type": "publications",
                "coverage": {"markets": ["global"], "therapeutic_areas": ["all"]},
                "description": "Medical publications database for evidence synthesis"
            },
            {
                "name": "OpenFDA",
                "type": "regulatory",
                "coverage": {"markets": ["US"], "therapeutic_areas": ["all"]},
                "description": "FDA drug information and safety data"
            },
            {
                "name": "EMA / EU medicines",
                "type": "regulatory",
                "coverage": {"markets": ["EU", "EEA"], "therapeutic_areas": ["all"]},
                "description": "EMA public JSON (medicines, EPAR, non-EPAR, post-auth, guidance, DHPC, PSUSA, PIP, orphan, shortages, referrals) plus ePI FHIR (path probing) and optional PMS read",
            },
            {
                "name": "CDE / NMPA (China regulatory web)",
                "type": "regulatory",
                "coverage": {"markets": ["CN"], "therapeutic_areas": ["all"]},
                "description": "China national regulatory portals (CDE, NMPA, zwfw) via Google Custom Search scoped to official hosts and HTML text extraction; optional LLM snippet translation",
            },
        ]
        
        for source_info in agent_sources:
            self.register_source(
                name=source_info["name"],
                source_type=source_info["type"],
                owner="system",
                refresh_frequency="real-time",
                coverage=source_info["coverage"]
            )
        
        self._initialized = True
        logger.info(f"Auto-registered {len(static_sources) + len(agent_sources)} data sources")
    
    def register_source(
        self,
        name: str,
        source_type: str,
        owner: str,
        refresh_frequency: str = "monthly",
        coverage: Dict[str, Any] = None,
        quality_threshold: float = 0.9
    ) -> Dict[str, Any]:
        """Register a data source"""
        source_id = str(uuid.uuid4())
        
        source = {
            "id": source_id,
            "name": name,
            "type": source_type,
            "owner": owner,
            "refresh_frequency": refresh_frequency,
            "last_refresh": datetime.now().isoformat(),
            "coverage": coverage or {},
            "quality_score": 1.0,
            "quality_threshold": quality_threshold,
            "registered_at": datetime.now().isoformat()
        }
        
        self._data_sources[source_id] = source
        return source
    
    def list_sources(
        self,
        source_type: Optional[str] = None,
        market: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List data sources with optional filtering"""
        sources = list(self._data_sources.values())
        
        if source_type:
            sources = [s for s in sources if s["type"] == source_type]
        
        if market:
            sources = [s for s in sources if market in s.get("coverage", {}).get("markets", [])]
        
        return sources
    
    def get_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Get source by ID"""
        return self._data_sources.get(source_id)
    
    def update_quality_score(
        self,
        source_id: str,
        quality_score: float
    ) -> Optional[Dict[str, Any]]:
        """Update quality score for a source"""
        source = self._data_sources.get(source_id)
        if not source:
            return None
        
        source["quality_score"] = quality_score
        source["last_refresh"] = datetime.now().isoformat()
        self._data_sources[source_id] = source
        return source
    
    def track_usage(self, source_id: str, asset_id: str):
        """Track which assets use which sources"""
        if source_id not in self._source_usage:
            self._source_usage[source_id] = []
        if asset_id not in self._source_usage[source_id]:
            self._source_usage[source_id].append(asset_id)
    
    def get_usage(self, source_id: str) -> List[str]:
        """Get list of assets using a source"""
        return self._source_usage.get(source_id, [])


# Global instance
data_catalog_service = DataCatalogService()

