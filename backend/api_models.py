"""
Models for the existing API routes (assets, trials, commercial)
Separate from the multi-agent models to avoid conflicts
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

# Asset Models
class Asset(BaseModel):
    id: str
    name: str
    indication: str
    phase: str
    status: str
    probability_of_success: float
    npv: float
    investment: float
    revenue_projection: float
    risk_level: str
    last_updated: str
    current_trials: List[Dict[str, Any]]

# Trial Models
class Trial(BaseModel):
    id: str
    title: str
    phase: str
    status: str
    indication: str
    sponsor: str
    enrollment: int
    sites: int
    start_date: Optional[str] = None
    completion_date: Optional[str] = None

# Commercial Models
class RevenueModel(BaseModel):
    id: str
    product: str
    indication: str
    market_size: float
    market_share: float
    revenue_projection: float
    peak_sales: float
    time_to_peak: int

# Data Query Models
class DataQuery(BaseModel):
    query_type: str
    filters: Dict[str, Any]
    limit: Optional[int] = 100

# Asset Models (extended)
class AssetFilters(BaseModel):
    phase: Optional[List[str]] = None
    status: Optional[List[str]] = None
    indication: Optional[List[str]] = None
    risk_level: Optional[List[str]] = None

class AssetsResponse(BaseModel):
    assets: List[Asset]
    total: int
    summary: Dict[str, Any]

class PortfolioSummary(BaseModel):
    total_assets: int
    total_investment: float
    total_npv: float
    total_revenue_projection: float
    by_phase: Dict[str, int]
    by_status: Dict[str, int]
    by_risk: Dict[str, int]

# Trial Models (extended)
class TrialFilters(BaseModel):
    phase: Optional[List[str]] = None
    status: Optional[List[str]] = None
    indication: Optional[List[str]] = None
    sponsor: Optional[List[str]] = None

class TrialsResponse(BaseModel):
    trials: List[Trial]
    total: int
    filters_applied: Dict[str, Any]

# Simulation Models
class SimulationParameters(BaseModel):
    indication: str
    phase: str
    number_of_sites: int
    patients_per_site: int
    enrollment_duration_months: int
    screening_success_rate: float = 0.8
    dropout_rate: float = 0.15
    startup_time_months: int = 6

class RevenueSimulationResponse(BaseModel):
    success: bool
    indication: str
    market_size: float
    peak_sales: float
    time_to_peak_years: int
    yearly_revenue: List[Dict[str, float]]
    assumptions: Dict[str, Any]
    confidence_interval: Dict[str, Any]

# Data Filters
class TrialTroveFilters(BaseModel):
    query: Optional[str] = None
    phase: Optional[List[str]] = None
    status: Optional[List[str]] = None
    therapeutic_area: Optional[List[str]] = None
    sponsor: Optional[List[str]] = None
    country: Optional[List[str]] = None
    start_year_min: Optional[int] = None
    start_year_max: Optional[int] = None

class SiteTroveFilters(BaseModel):
    query: Optional[str] = None
    country: Optional[List[str]] = None
    state: Optional[List[str]] = None
    city: Optional[List[str]] = None
    specialty: Optional[List[str]] = None
    enrollment_min: Optional[int] = None

class ClaimsFilters(BaseModel):
    query: Optional[str] = None
    diagnosis_code: Optional[List[str]] = None
    procedure_code: Optional[List[str]] = None
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    gender: Optional[str] = None
    year: Optional[List[int]] = None

# Response Models
class ApiResponse(BaseModel):
    success: bool
    data: Any
    message: Optional[str] = None
    error: Optional[str] = None












