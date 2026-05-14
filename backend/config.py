"""
Configuration settings for the Clinical Research Assistant
Uses environment variables for sensitive data in production
"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Dict, List, Literal
import os

class Settings(BaseSettings):
    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8001
    API_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # LLM Configuration — single entry point: agents/llm_agent.py (all app LLM calls route here)
    LLM_PROVIDER: Literal["anthropic", "azure_openai", "openai"] = "anthropic"
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    # OpenAI API (set LLM_PROVIDER=openai). Model id must match your account (e.g. gpt-5.4, gpt-5-mini).
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-5-mini"
    # Optional: proxies, Azure OpenAI-compatible gateways, or OpenAI enterprise base URL.
    OPENAI_BASE_URL: str = ""
    MAX_TOKENS: int = 4000
    # Graph synthesis final answer: high ceiling for detailed, citation-heavy responses (APIs still enforce a max).
    SYNTHESIS_MAX_TOKENS: int = int(os.getenv("SYNTHESIS_MAX_TOKENS", "16384"))
    # Graph planning JSON can be large when many search/analyze nodes are needed; separate cap avoids truncated plans.
    GRAPH_PLAN_MAX_TOKENS: int = int(os.getenv("GRAPH_PLAN_MAX_TOKENS", "16000"))
    GRAPH_PLAN_MAX_NODES: int = int(os.getenv("GRAPH_PLAN_MAX_NODES", "40"))
    # When deep_research is off for a request: hard caps on planner output (before sanitize trim).
    GRAPH_PLAN_COMPACT_MAX_NODES: int = int(os.getenv("GRAPH_PLAN_COMPACT_MAX_NODES", "5"))
    GRAPH_PLAN_COMPACT_MAX_SEARCH_NODES: int = int(os.getenv("GRAPH_PLAN_COMPACT_MAX_SEARCH_NODES", "3"))
    # LangGraph default recursion_limit is 25; linear plans use ~1 step per node—raise for larger plans.
    GRAPH_RECURSION_LIMIT: int = int(os.getenv("GRAPH_RECURSION_LIMIT", "80"))
    TEMPERATURE: float = 0.1

    # Deep research (brief/outline, verifier + replan, optional parallel sub-runs)
    DEEP_RESEARCH_ENABLED: bool = os.getenv("DEEP_RESEARCH_ENABLED", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    DEEP_RESEARCH_MAX_REPLANS: int = int(os.getenv("DEEP_RESEARCH_MAX_REPLANS", "3"))
    # Per-step source assessment + running answer draft (2 LLM calls per evidence node when enabled).
    DEEP_RESEARCH_INCREMENTAL: bool = os.getenv(
        "DEEP_RESEARCH_INCREMENTAL", "true"
    ).lower() in ("1", "true", "yes")
    DEEP_RESEARCH_MAX_NEW_NODES_PER_ROUND: int = int(
        os.getenv("DEEP_RESEARCH_MAX_NEW_NODES_PER_ROUND", "4")
    )
    DEEP_RESEARCH_PARALLEL_SUBRUNS: bool = os.getenv(
        "DEEP_RESEARCH_PARALLEL_SUBRUNS", "true"
    ).lower() in ("1", "true", "yes")
    DEEP_RESEARCH_MIN_OUTLINE_SECTIONS_FOR_PARALLEL: int = int(
        os.getenv("DEEP_RESEARCH_MIN_OUTLINE_SECTIONS_FOR_PARALLEL", "4")
    )
    # Split outline into N parallel sub-plans (merged before main graph). Clamped at runtime to [2, 8] and to outline length.
    DEEP_RESEARCH_PARALLEL_BRANCH_COUNT: int = int(
        os.getenv("DEEP_RESEARCH_PARALLEL_BRANCH_COUNT", "4")
    )
    # Incremental reflection / draft refinement — larger payloads so multi-attempt CSE + big JSON nodes still get assessed.
    REFLECTION_PAYLOAD_MAX_CHARS: int = int(os.getenv("REFLECTION_PAYLOAD_MAX_CHARS", "48000"))
    REFLECTION_EVIDENCE_SNIPPET_CHARS: int = int(
        os.getenv("REFLECTION_EVIDENCE_SNIPPET_CHARS", "32000")
    )
    # Use a short LLM pass to propose entity-aware CSE query variants (per request; not hardcoded topic rules).
    GOOGLE_CSE_LLM_QUERY_PLANNING: bool = os.getenv(
        "GOOGLE_CSE_LLM_QUERY_PLANNING", "true"
    ).lower() in ("1", "true", "yes")

    # Azure OpenAI (set LLM_PROVIDER=azure_openai). Deployment name is the resource name you chose in Azure (not always "gpt-4o").
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_VERSION: str = "2024-08-01-preview"
    AZURE_OPENAI_DEPLOYMENT_NAME: str = ""
    # Alias some templates use for deployment name:
    AZURE_OPENAI_API_INSTANCE_NAME: str = ""

    @field_validator("AZURE_OPENAI_ENDPOINT", mode="before")
    @classmethod
    def strip_azure_endpoint(cls, v: object) -> object:
        if v is None or v == "":
            return ""
        s = str(v).strip().strip('"').strip("'")
        return s.rstrip("/")

    @field_validator("OPENAI_BASE_URL", mode="before")
    @classmethod
    def strip_openai_base_url(cls, v: object) -> object:
        if v is None or v == "":
            return ""
        s = str(v).strip().strip('"').strip("'")
        return s.rstrip("/")

    @property
    def azure_openai_deployment(self) -> str:
        return (self.AZURE_OPENAI_DEPLOYMENT_NAME or self.AZURE_OPENAI_API_INSTANCE_NAME or "").strip()
    
    # ClinicalTrials.gov API v2 (public). Override with CLINICAL_TRIALS_API_BASE if needed.
    CLINICAL_TRIALS_API_BASE: str = "https://clinicaltrials.gov/api/v2"
    # Optional; include contact URL if your org requires it. Default UA is set in clinical_trials_agent.
    CLINICAL_TRIALS_USER_AGENT: str = os.getenv("CLINICAL_TRIALS_USER_AGENT", "").strip()

    # PubMed Central API
    PUBMED_BASE_URL: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    PUBMED_OAI_URL: str = "https://www.ncbi.nlm.nih.gov/pmc/oai/oai.cgi"
    
    # BioOntology API (replacing BioMCP)
    BIOONTOLOGY_BASE_URL: str = "https://data.bioontology.org"
    BIOONTOLOGY_API_KEY: str = os.getenv("BIOONTOLOGY_API_KEY", "")
    
    # OpenFDA API
    OPENFDA_BASE_URL: str = "https://api.fda.gov"
    OPENFDA_API_KEY: str = os.getenv("OPENFDA_API_KEY", "")

    # EMA / EU medicines — public JSON feeds (twice daily CET) + optional ePI FHIR API
    # JSON base: https://www.ema.europa.eu/en/about-us/about-website/download-website-data-json-data-format
    EMA_JSON_BASE_URL: str = "https://www.ema.europa.eu/en/documents/report"
    EMA_JSON_CACHE_DIR: str = os.getenv("EMA_JSON_CACHE_DIR", "")  # default: backend/.cache/ema_json
    EMA_JSON_CACHE_TTL_SECONDS: int = int(os.getenv("EMA_JSON_CACHE_TTL_SECONDS", "21600"))  # 6h
    # Stricter row scoring (anchor entities vs generic regulatory words), aligned with Google CSE query discipline.
    EMA_JSON_STRICT_ANCHOR_SCORING: bool = os.getenv(
        "EMA_JSON_STRICT_ANCHOR_SCORING", "true"
    ).lower() in ("1", "true", "yes")
    # If any search term is at least this length (likely INN / invented name), it must hit identity text (or INN match).
    EMA_JSON_LONG_ANCHOR_MIN_LEN: int = int(os.getenv("EMA_JSON_LONG_ANCHOR_MIN_LEN", "9"))
    # ePI consuming API (EMA.EPI.Consuming): GET {EMA_EPI_BASE_URL}{EMA_EPI_FHIR_ROOT}/List, /Bundle, etc.
    # Official: https://epi.ema.europa.eu/consuming/api/fhir/ — ListBySearchParameter, BundleById, …
    # If the primary FHIR root 404s, the client tries EMA_EPI_*_PATH_CANDIDATES (comma-separated legacy gateways).
    EMA_EPI_ENABLED: bool = os.getenv("EMA_EPI_ENABLED", "true").lower() in ("1", "true", "yes")
    EMA_EPI_BASE_URL: str = os.getenv("EMA_EPI_BASE_URL", "https://epi.ema.europa.eu")
    EMA_EPI_FHIR_ROOT: str = os.getenv("EMA_EPI_FHIR_ROOT", "/consuming/api/fhir")
    EMA_EPI_SUBSCRIPTION_KEY: str = os.getenv("EMA_EPI_SUBSCRIPTION_KEY", "").strip()
    # Comma-separated legacy fallbacks (trim each); use {id} for path or query templates
    EMA_EPI_LIST_PATH_CANDIDATES: str = os.getenv(
        "EMA_EPI_LIST_PATH_CANDIDATES",
        "/api/retrieval/ListBySearchParameter,/api/retrieval/listbysearchparameter,"
        "/consumption/api/retrieval/ListBySearchParameter,/ema-epi-consuming/api/retrieval/ListBySearchParameter,"
        "/api/v1/retrieval/ListBySearchParameter",
    )
    EMA_EPI_BUNDLE_BY_ID_PATH_CANDIDATES: str = os.getenv(
        "EMA_EPI_BUNDLE_BY_ID_PATH_CANDIDATES",
        "/api/retrieval/BundleById?id={id},/api/retrieval/bundlebyid?id={id},"
        "/consumption/api/retrieval/BundleById?id={id},/ema-epi-consuming/api/retrieval/BundleById?id={id}",
    )
    EMA_EPI_BUNDLE_BY_SEARCH_PATH_CANDIDATES: str = os.getenv(
        "EMA_EPI_BUNDLE_BY_SEARCH_PATH_CANDIDATES",
        "/api/retrieval/BundleBySearchParameter,/consumption/api/retrieval/BundleBySearchParameter,"
        "/ema-epi-consuming/api/retrieval/BundleBySearchParameter",
    )
    EMA_EPI_LIST_BY_ID_PATH_CANDIDATES: str = os.getenv(
        "EMA_EPI_LIST_BY_ID_PATH_CANDIDATES",
        "/api/retrieval/ListById?id={id},/api/retrieval/listbyid?id={id},"
        "/consumption/api/retrieval/ListById?id={id},/ema-epi-consuming/api/retrieval/ListById?id={id}",
    )
    EMA_EPI_TIMEOUT_SECONDS: float = float(os.getenv("EMA_EPI_TIMEOUT_SECONDS", "25"))
    EMA_EPI_MAX_BUNDLE_CHARS: int = int(os.getenv("EMA_EPI_MAX_BUNDLE_CHARS", "12000"))
    # Optional Phase 2+: authenticated PMS FHIR read (Write PMS IG)
    EMA_PMS_BASE_URL: str = os.getenv("EMA_PMS_BASE_URL", "")
    EMA_PMS_READ_ENABLED: bool = os.getenv("EMA_PMS_READ_ENABLED", "false").lower() in ("1", "true", "yes")
    
    # Google Custom Search API
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GOOGLE_SEARCH_ENGINE_ID: str = os.getenv("GOOGLE_SEARCH_ENGINE_ID", "")
    # Optional second CSE restricted to CDE/NMPA/zwfw hosts (omit redundant site: in query when set)
    GOOGLE_CSE_CHINA_ENGINE_ID: str = os.getenv("GOOGLE_CSE_CHINA_ENGINE_ID", "").strip()
    GOOGLE_CSE_BASE_URL: str = "https://www.googleapis.com/customsearch/v1"
    # Brave Web Search API (used when Google CSE returns HTTP 429). Header: X-Subscription-Token
    BRAVE_API_KEY: str = os.getenv("BRAVE_API_KEY", "").strip()
    BRAVE_WEB_SEARCH_URL: str = (
        os.getenv("BRAVE_WEB_SEARCH_URL", "https://api.search.brave.com/res/v1/web/search")
        .strip()
        .rstrip("/")
    )

    # China regulatory agent (CDE / NMPA web discovery)
    CHINA_REGULATORY_TRANSLATE_SNIPPETS: bool = os.getenv(
        "CHINA_REGULATORY_TRANSLATE_SNIPPETS", "false"
    ).lower() in ("1", "true", "yes")
    CHINA_REGULATORY_TRANSLATE_MAX_CHARS: int = int(
        os.getenv("CHINA_REGULATORY_TRANSLATE_MAX_CHARS", "4000")
    )
    # Multi-query CSE coverage (parallel angles, like EMA multi-collection search)
    CHINA_REGULATORY_QUERY_VARIATIONS_MAX: int = int(
        os.getenv("CHINA_REGULATORY_QUERY_VARIATIONS_MAX", "5")
    )
    CHINA_REGULATORY_CSE_CONCURRENCY: int = int(
        os.getenv("CHINA_REGULATORY_CSE_CONCURRENCY", "2")
    )
    CHINA_REGULATORY_CSE_NUM_PER_VARIATION: int = int(
        os.getenv("CHINA_REGULATORY_CSE_NUM_PER_VARIATION", "6")
    )
    # Per-query-stem retries when Google returns 429 / transient 5xx (each attempt re-acquires throttle).
    CHINA_REGULATORY_CSE_MAX_RETRIES: int = int(os.getenv("CHINA_REGULATORY_CSE_MAX_RETRIES", "10"))
    # Max characters of fetched page text kept per China regulatory result (synthesis context).
    CHINA_REGULATORY_PAGE_MAX_CHARS: int = int(os.getenv("CHINA_REGULATORY_PAGE_MAX_CHARS", "20000"))
    # Max characters of fetched page text kept per google_search / FiercePharma-style web result.
    GOOGLE_SEARCH_CONTENT_MAX_CHARS: int = int(os.getenv("GOOGLE_SEARCH_CONTENT_MAX_CHARS", "18000"))
    CHINA_REGULATORY_FETCH_CONCURRENCY: int = int(
        os.getenv("CHINA_REGULATORY_FETCH_CONCURRENCY", "4")
    )

    # Live API agents (no site database) — NIH, NPI, OpenAlex, Crossref, ROR, Open Payments, CTIS, ISRCTN, CMS, FDA DDAPI
    NIH_REPORTER_BASE_URL: str = os.getenv("NIH_REPORTER_BASE_URL", "https://api.reporter.nih.gov")
    NPI_REGISTRY_BASE_URL: str = os.getenv("NPI_REGISTRY_BASE_URL", "https://npiregistry.cms.hhs.gov/api")
    OPENALEX_BASE_URL: str = os.getenv("OPENALEX_BASE_URL", "https://api.openalex.org")
    OPENALEX_API_KEY: str = os.getenv("OPENALEX_API_KEY", "").strip()
    CROSSREF_BASE_URL: str = os.getenv("CROSSREF_BASE_URL", "https://api.crossref.org")
    CROSSREF_MAILTO: str = os.getenv("CROSSREF_MAILTO", "study-designer@localhost").strip()
    ROR_API_BASE_URL: str = os.getenv("ROR_API_BASE_URL", "https://api.ror.org")
    OPEN_PAYMENTS_BASE_URL: str = os.getenv(
        "OPEN_PAYMENTS_BASE_URL", "https://openpaymentsdata.cms.gov"
    )
    OPEN_PAYMENTS_DATASTORE_RESOURCE_IDS: str = os.getenv(
        "OPEN_PAYMENTS_DATASTORE_RESOURCE_IDS", ""
    ).strip()
    EU_CTIS_SEARCH_URL: str = os.getenv(
        "EU_CTIS_SEARCH_URL", "https://euclinicaltrials.eu/ctis-public-api/search"
    )
    EU_CTIS_RETRIEVE_PREFIX: str = os.getenv(
        "EU_CTIS_RETRIEVE_PREFIX", "https://euclinicaltrials.eu/ctis-public-api/retrieve"
    )
    ISRCTN_API_BASE_URL: str = os.getenv(
        "ISRCTN_API_BASE_URL", "https://www.isrctn.com"
    )
    CMS_DATA_API_BASE_URL: str = os.getenv(
        "CMS_DATA_API_BASE_URL", "https://data.cms.gov"
    )
    FDA_DATADASHBOARD_BASE_URL: str = os.getenv(
        "FDA_DATADASHBOARD_BASE_URL", "https://api-datadashboard.fda.gov/v1"
    )
    FDA_DATADASHBOARD_USER: str = os.getenv("FDA_DATADASHBOARD_USER", "").strip()
    FDA_DATADASHBOARD_KEY: str = os.getenv("FDA_DATADASHBOARD_KEY", "").strip()

    # AACT Database Configuration (CTTI cloud Postgres — SSL recommended)
    AACT_DB_USERNAME: str = os.getenv("AACT_DB_USERNAME", "").strip()
    AACT_DB_PASSWORD: str = os.getenv("AACT_DB_PASSWORD", "")
    AACT_DB_HOST: str = os.getenv("AACT_DB_HOST", "aact-db.ctti-clinicaltrials.org").strip()
    AACT_DB_NAME: str = os.getenv("AACT_DB_NAME", "aact").strip()
    AACT_DB_PORT: int = int(os.getenv("AACT_DB_PORT", "5432"))
    AACT_DB_SSL: bool = os.getenv("AACT_DB_SSL", "true").lower() in ("1", "true", "yes")
    # Optional PEM path for TLS verify (corp proxy / custom CA). Empty = use certifi / defaults.
    AACT_DB_SSL_CAFILE: str = os.getenv("AACT_DB_SSL_CAFILE", "").strip()

    # Redis Configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    REDIS_TTL: int = 3600  # 1 hour
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # Processing
    MAX_RESULTS_PER_SOURCE: int = 50
    MAX_CONCURRENT_REQUESTS: int = 10
    REQUEST_TIMEOUT: int = 30
    
    # WebSocket Configuration
    WEBSOCKET_TIMEOUT: int = 600  # 10 minutes (600 seconds) - allow longer for SoA extraction
    WEBSOCKET_CONNECTION_TIMEOUT: int = 180  # 3 minutes (180 seconds) - shorter than client keepalive
    WEBSOCKET_KEEPALIVE_INTERVAL: int = 30   # 30 seconds - more frequent pings to prevent timeout
    WEBSOCKET_HEALTH_CHECK_INTERVAL: int = 60  # 1 minute (60 seconds)
    WEBSOCKET_SEND_TIMEOUT: int = 10  # 10 seconds for sending messages
    
    # SoA Extraction Timeout (longer than regular WebSocket timeout)
    SOA_EXTRACTION_TIMEOUT: int = 1800  # 30 minutes (1800 seconds) - SoA extraction can be very slow
    
    # File Upload Configuration
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB for protocol uploads
    ALLOWED_FILE_TYPES: List[str] = [".pdf"]  # Only PDF files for protocols
    UPLOAD_CHUNK_SIZE: int = 1024 * 1024  # 1MB chunks for large file processing
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"

    # Dynamic graph synthesis — context formatting and optional node compression
    # Higher default so regulatory/web excerpts (titles + long content fields) survive per-layer budgeting.
    CONTEXT_LAYER_CHAR_BUDGET: int = int(os.getenv("CONTEXT_LAYER_CHAR_BUDGET", "96000"))
    SYNTHESIS_COMPACT_SEARCH_TRIALS: bool = os.getenv(
        "SYNTHESIS_COMPACT_SEARCH_TRIALS", "true"
    ).lower() in ("1", "true", "yes")
    ENABLE_NODE_OUTPUT_COMPRESSION: bool = os.getenv(
        "ENABLE_NODE_OUTPUT_COMPRESSION", "false"
    ).lower() in ("1", "true", "yes")
    NODE_COMPRESSION_MIN_RAW_ITEMS: int = int(os.getenv("NODE_COMPRESSION_MIN_RAW_ITEMS", "25"))

    # Token counting for truncation budgets (tiktoken; encoding chosen per provider/model when "auto")
    TOKEN_COUNT_METHOD: str = os.getenv("TOKEN_COUNT_METHOD", "tiktoken").strip().lower()
    # tiktoken encoding: auto | o200k_base | cl100k_base (auto maps OpenAI GPT-4/5 family → o200k_base when available)
    TIKTOKEN_ENCODING: str = os.getenv("TIKTOKEN_ENCODING", "auto").strip().lower()

    # Model context — used to size synthesis/truncation budgets (0 = infer from LLM_PROVIDER + model id)
    LLM_CONTEXT_WINDOW_TOKENS: int = int(os.getenv("LLM_CONTEXT_WINDOW_TOKENS", "0"))
    # Extra tokens reserved beyond SYNTHESIS_MAX_TOKENS (tool framing, separators, API slack)
    SYNTHESIS_INPUT_OVERHEAD_TOKENS: int = int(os.getenv("SYNTHESIS_INPUT_OVERHEAD_TOKENS", "8192"))

    # Anthropic prompt caching (beta prompt_caching API) — static system prompt must exceed min tokens
    ENABLE_ANTHROPIC_PROMPT_CACHE: bool = os.getenv(
        "ENABLE_ANTHROPIC_PROMPT_CACHE", "true"
    ).lower() in ("1", "true", "yes")
    ANTHROPIC_CACHE_MIN_SYSTEM_TOKENS: int = int(os.getenv("ANTHROPIC_CACHE_MIN_SYSTEM_TOKENS", "1024"))
    # Cache the large static graph-planner document (Anthropic); variable query stays in user message.
    ENABLE_GRAPH_PLANNER_PROMPT_CACHE: bool = os.getenv(
        "ENABLE_GRAPH_PLANNER_PROMPT_CACHE", "true"
    ).lower() in ("1", "true", "yes")
    # One LLM call for incremental reflection + working-answer update (vs two).
    DEEP_RESEARCH_INCREMENTAL_COMBINED_LLM: bool = os.getenv(
        "DEEP_RESEARCH_INCREMENTAL_COMBINED_LLM", "true"
    ).lower() in ("1", "true", "yes")
    # Replan: small JSON mapping each gap → one targeted search (not a full replanner).
    DEEP_RESEARCH_REPLAN_TARGETED: bool = os.getenv(
        "DEEP_RESEARCH_REPLAN_TARGETED", "true"
    ).lower() in ("1", "true", "yes")
    # TTL for auxiliary LLM caches (brief/outline, EMA router, Google CSE expansion).
    LLM_AUX_CACHE_TTL_SECONDS: int = int(os.getenv("LLM_AUX_CACHE_TTL_SECONDS", "3600"))

    # Map–reduce digests of large meaningful_data before synthesis (extra LLM calls per shard).
    # Leave MAP_REDUCE_TRIM_JSON_AFTER_SUMMARY off for regulatory work—trim drops raw shards the model may need.
    MAP_REDUCE_SYNTHESIS: bool = os.getenv("MAP_REDUCE_SYNTHESIS", "false").lower() in ("1", "true", "yes")
    MAP_REDUCE_MIN_DATA_TOKENS: int = int(os.getenv("MAP_REDUCE_MIN_DATA_TOKENS", "28000"))
    MAP_REDUCE_MAX_SHARDS: int = int(os.getenv("MAP_REDUCE_MAX_SHARDS", "12"))
    MAP_REDUCE_SHARD_INPUT_CHARS: int = int(os.getenv("MAP_REDUCE_SHARD_INPUT_CHARS", "18000"))
    MAP_REDUCE_TRIM_JSON_AFTER_SUMMARY: bool = os.getenv(
        "MAP_REDUCE_TRIM_JSON_AFTER_SUMMARY", "false"
    ).lower() in ("1", "true", "yes")
    MAP_REDUCE_TRIM_TOKEN_THRESHOLD: int = int(os.getenv("MAP_REDUCE_TRIM_TOKEN_THRESHOLD", "8000"))

    # Context attention: keyword | bm25 | hybrid; pool_factor widens BM25 candidate pool before top-k by attention
    CONTEXT_ATTENTION_METHOD: str = os.getenv("CONTEXT_ATTENTION_METHOD", "hybrid").strip().lower()
    CONTEXT_HYBRID_KEYWORD_WEIGHT: float = float(os.getenv("CONTEXT_HYBRID_KEYWORD_WEIGHT", "0.35"))
    CONTEXT_BM25_POOL_FACTOR: int = int(os.getenv("CONTEXT_BM25_POOL_FACTOR", "2"))

    # Long conversation threads — summarize middle segment (extra LLM call when triggered)
    ENABLE_CONVERSATION_SUMMARIZATION: bool = os.getenv(
        "ENABLE_CONVERSATION_SUMMARIZATION", "false"
    ).lower() in ("1", "true", "yes")
    CONVERSATION_SUMMARY_MAX_MESSAGES: int = int(os.getenv("CONVERSATION_SUMMARY_MAX_MESSAGES", "24"))
    CONVERSATION_SUMMARY_MAX_CHARS: int = int(os.getenv("CONVERSATION_SUMMARY_MAX_CHARS", "24000"))
    CONVERSATION_SUMMARY_HEAD_MESSAGES: int = int(os.getenv("CONVERSATION_SUMMARY_HEAD_MESSAGES", "3"))
    CONVERSATION_SUMMARY_TAIL_MESSAGES: int = int(os.getenv("CONVERSATION_SUMMARY_TAIL_MESSAGES", "6"))

    # Regulatory CSV / Excel under repo ``data/`` (local) or S3 mirror (EKS: sync in deploy workflow).
    REGULATORY_DATA_DIR: str = os.getenv("REGULATORY_DATA_DIR", "").strip()
    DATA_S3_BUCKET: str = os.getenv("DATA_S3_BUCKET", "").strip()
    DATA_S3_PREFIX: str = os.getenv("DATA_S3_PREFIX", "regulatory-app-data").strip().strip("/")
    AWS_REGION: str = os.getenv("AWS_REGION", "").strip()
    AWS_ENDPOINT_URL_S3: str = os.getenv("AWS_ENDPOINT_URL_S3", "").strip()

    def effective_llm_context_window_tokens(self) -> int:
        """Total context window (combined input + output limit) for the active provider/model."""
        override = int(self.LLM_CONTEXT_WINDOW_TOKENS or 0)
        if override > 0:
            return override
        prov = self.LLM_PROVIDER
        if prov == "anthropic":
            return 200_000
        if prov in ("openai", "azure_openai"):
            mid = (
                (self.OPENAI_MODEL or "").lower()
                if prov == "openai"
                else (self.azure_openai_deployment or "").lower()
            )
            if any(k in mid for k in ("gpt-5", "gpt-4.1")):
                return 400_000
            if any(
                k in mid
                for k in (
                    "gpt-4o",
                    "gpt-4-turbo",
                    "gpt-4-0125",
                    "gpt-4-1106",
                    "gpt-4-vision",
                    "o1",
                    "o3",
                    "o4-mini",
                )
            ):
                return 128_000
            if "gpt-3.5" in mid:
                return 16_385
            return 128_000
        return 128_000

    def effective_synthesis_input_token_budget(self) -> int:
        """Max estimated tokens for system + user before completion (SYNTHESIS_MAX_TOKENS)."""
        ctx = self.effective_llm_context_window_tokens()
        reserve = int(self.SYNTHESIS_MAX_TOKENS) + int(self.SYNTHESIS_INPUT_OVERHEAD_TOKENS)
        return max(32_000, ctx - reserve)

    def synthesis_combined_prompt_soft_limit(self) -> int:
        """Start progressive truncation when system+user estimates exceed this."""
        return max(24_000, int(self.effective_synthesis_input_token_budget() * 0.92))

    def synthesis_user_progressive_target_tokens(self, system_prompt_tokens: int) -> int:
        """Target token budget for user-only synthesis payload after accounting for system size."""
        base = self.effective_synthesis_input_token_budget()
        return max(24_000, base - int(system_prompt_tokens) - 4096)

    def synthesis_user_emergency_target_tokens(self, system_prompt_tokens: int) -> int:
        t = self.synthesis_user_progressive_target_tokens(system_prompt_tokens)
        return max(16_000, int(t * 0.82))

    def meaningful_data_truncation_token_budget(self) -> int:
        """Token budget for pre-assembly structured pools (trials, SoA, simulation JSON)."""
        cap = int(self.effective_synthesis_input_token_budget() * 0.88)
        return min(500_000, max(50_000, cap))

    def effective_context_layer_char_budget(self) -> int:
        """Per-layer character cap for ContextManager (bounded by CONTEXT_LAYER_CHAR_BUDGET)."""
        tb = self.effective_synthesis_input_token_budget()
        derived = int(tb * 0.18 * 3.2)
        return max(16_000, min(int(self.CONTEXT_LAYER_CHAR_BUDGET), max(24_000, derived)))

    def working_answer_max_chars(self) -> int:
        """Clamp incremental working-answer paste so it cannot dominate the synthesis window."""
        return int(min(200_000, max(48_000, self.effective_synthesis_input_token_budget() * 2.8)))

    class Config:
        # backend/.env first; repo-root .env when the server is started from backend/
        env_file = (".env", "../.env")
        env_file_encoding = "utf-8"

# Global settings instance
settings = Settings()

# API Endpoints
CLINICAL_TRIALS_ENDPOINTS = {
    "studies": "/studies",
    "conditions": "/studies",
    "interventions": "/studies",
    "sponsors": "/studies",
    "locations": "/studies"
}

PUBMED_ENDPOINTS = {
    "search": "/search",
    "fetch": "/fetch",
    "list": "/list"
}

BIOONTOLOGY_ENDPOINTS = {
    "search": "/search",
    "annotator": "/annotator",
    "recommender": "/recommender",
    "ontologies": "/ontologies",
    "classes": "/classes"
}

OPENFDA_ENDPOINTS = {
    "drugs": "/drug/drugsfda.json",
    "drug_events": "/drug/event.json",
    "drug_enforcement": "/drug/enforcement.json",
    "device": "/device/device.json",
    "food": "/food/enforcement.json"
}

# Medical terminology patterns for NER
MEDICAL_TERMS = [
    "clinical trial", "randomized", "placebo", "intervention", "outcome",
    "adverse event", "efficacy", "safety", "protocol", "inclusion criteria",
    "exclusion criteria", "primary endpoint", "secondary endpoint",
    "statistical significance", "p-value", "confidence interval"
]

# Error messages
ERROR_MESSAGES = {
    "api_timeout": "API request timed out",
    "rate_limit": "Rate limit exceeded",
    "invalid_query": "Invalid query format",
    "service_unavailable": "Service temporarily unavailable",
    "data_processing_error": "Error processing data"
} 
