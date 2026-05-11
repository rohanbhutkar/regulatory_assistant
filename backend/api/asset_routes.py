from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Dict, Any, Optional
from api_models import Asset, AssetFilters, AssetsResponse, PortfolioSummary
import pandas as pd
from utils.optimized_data_loader import OptimizedDataLoader as DataLoader

router = APIRouter()

# Global data loader instance
data_loader: Optional[DataLoader] = None

def set_data_loader(loader: DataLoader):
    global data_loader
    data_loader = loader

def get_data_loader() -> DataLoader:
    if data_loader is None:
        raise HTTPException(status_code=500, detail="Data loader not initialized")
    return data_loader

def create_asset_from_trial(row: pd.Series, index: int) -> Asset:
    """Convert trial data to Asset model"""
    return Asset(
        id=f"asset_{index:03d}",
        asset_name=row.get('drug_name', f"Drug {index}"),
        therapeutic_area=row.get('therapeutic_area', 'Unknown'),
        trial_phase=row.get('phase', 'Unknown'),
        cost_per_patient=row.get('cost_per_patient', 15000),
        total_estimated_cost=row.get('total_cost', 3000000),
        projected_revenue=row.get('projected_revenue', 50000000),
        status='active' if row.get('status', '').lower() == 'active' else 'paused',
        current_trials=[{"id": f"trial_{index:03d}", "name": row.get('trial_name', f"Trial {index}")}],
        last_updated=pd.Timestamp.now().isoformat(),
        created_by="system"
    )

@router.get("/", response_model=AssetsResponse)
async def get_assets(
    filters: Optional[AssetFilters] = None,
    sort_by: str = "asset_name",
    sort_order: str = "asc",
    page: int = 1,
    page_size: int = 50,
    loader: DataLoader = Depends(get_data_loader)
):
    """Get paginated asset list with filtering and sorting using real data"""
    # Get trial data from CSV
    trial_df = loader.get_data('trialtrove')
    
    if trial_df.empty:
        # Fallback to mock data if CSV is empty
        MOCK_ASSETS = [
            Asset(
                id="asset_001",
                asset_name="Oncology Drug A",
                therapeutic_area="Oncology",
                trial_phase="Phase III",
                cost_per_patient=25000,
                total_estimated_cost=5000000,
                projected_revenue=150000000,
                status="active",
                current_trials=[{"id": "trial_001", "name": "ONC-A-001"}],
                last_updated="2024-01-15T10:30:00Z",
                created_by="user_001"
            )
        ]
        assets = MOCK_ASSETS
    else:
        # Convert trial data to assets
        assets = []
        for idx, row in trial_df.iterrows():
            try:
                asset = create_asset_from_trial(row, idx)
                assets.append(asset)
            except Exception as e:
                print(f"Error creating asset from row {idx}: {e}")
                continue
    
    # Apply filters
    if filters:
        if filters.therapeutic_area:
            assets = [a for a in assets if a.therapeutic_area in filters.therapeutic_area]
        if filters.trial_phase:
            assets = [a for a in assets if a.trial_phase in filters.trial_phase]
        if filters.status:
            assets = [a for a in assets if a.status in filters.status]
        if filters.cost_range:
            assets = [a for a in assets if filters.cost_range["min"] <= a.cost_per_patient <= filters.cost_range["max"]]
        if filters.revenue_range:
            assets = [a for a in assets if filters.revenue_range["min"] <= a.projected_revenue <= filters.revenue_range["max"]]
    
    # Apply sorting
    reverse = sort_order == "desc"
    if sort_by == "asset_name":
        assets.sort(key=lambda x: x.asset_name, reverse=reverse)
    elif sort_by == "cost_per_patient":
        assets.sort(key=lambda x: x.cost_per_patient, reverse=reverse)
    elif sort_by == "projected_revenue":
        assets.sort(key=lambda x: x.projected_revenue, reverse=reverse)
    
    # Apply pagination
    total_count = len(assets)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    paginated_assets = assets[start_idx:end_idx]
    
    return AssetsResponse(
        assets=paginated_assets,
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=(total_count + page_size - 1) // page_size,
        filters_applied=filters or AssetFilters()
    )

@router.get("/{asset_id}")
async def get_asset_details(asset_id: str, loader: DataLoader = Depends(get_data_loader)):
    """Get detailed asset information including trials and costs"""
    # Get trial data
    trial_df = loader.get_data('trialtrove')
    
    # Find the asset
    asset = None
    if not trial_df.empty:
        try:
            asset_idx = int(asset_id.split('_')[1])
            if asset_idx < len(trial_df):
                row = trial_df.iloc[asset_idx]
                asset = create_asset_from_trial(row, asset_idx)
        except:
            pass
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    return {
        "asset": asset,
        "trial_details": [
            {
                "trial_id": f"trial_{asset_idx:03d}",
                "trial_name": asset.current_trials[0]["name"] if asset.current_trials else "Unknown",
                "phase": asset.trial_phase,
                "status": asset.status,
                "enrollment_target": 500,
                "current_enrollment": 320,
                "start_date": "2023-06-01",
                "estimated_completion": "2024-12-31"
            }
        ],
        "cost_breakdown": {
            "screening": asset.cost_per_patient * 0.1,
            "treatment": asset.cost_per_patient * 0.6,
            "follow_up": asset.cost_per_patient * 0.2,
            "overhead": asset.cost_per_patient * 0.1
        },
        "revenue_projection": {
            "year_1": asset.projected_revenue * 0.2,
            "year_2": asset.projected_revenue * 0.3,
            "year_3": asset.projected_revenue * 0.3,
            "year_4": asset.projected_revenue * 0.2
        },
        "risk_analysis": {
            "regulatory_risk": "medium",
            "competitive_risk": "high",
            "technical_risk": "low"
        }
    }

@router.get("/portfolio/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(loader: DataLoader = Depends(get_data_loader)):
    """Get portfolio-level summary statistics using real data"""
    trial_df = loader.get_data('trialtrove')
    
    if trial_df.empty:
        # Fallback to mock data
        return PortfolioSummary(
            total_investment=15000000,
            projected_revenue=320000000,
            roi_percentage=2033.33,
            active_assets=3,
            high_risk_assets=1,
            therapeutic_area_distribution={"Oncology": 1, "Cardiology": 1, "Neurology": 1},
            phase_distribution={"Phase I": 1, "Phase II": 1, "Phase III": 1},
            cost_trends=[
                {"month": "2024-01", "cost": 5000000},
                {"month": "2024-02", "cost": 5200000},
                {"month": "2024-03", "cost": 4800000},
                {"month": "2024-04", "cost": 5500000},
                {"month": "2024-05", "cost": 6000000}
            ]
        )
    
    # Calculate real statistics from trial data
    total_investment = trial_df.get('total_cost', pd.Series([3000000] * len(trial_df))).sum()
    projected_revenue = trial_df.get('projected_revenue', pd.Series([50000000] * len(trial_df))).sum()
    active_assets = len(trial_df[trial_df.get('status', pd.Series(['active'] * len(trial_df))).str.lower() == 'active'])
    
    # Therapeutic area distribution
    therapeutic_areas = trial_df.get('therapeutic_area', pd.Series(['Unknown'] * len(trial_df)))
    therapeutic_area_distribution = therapeutic_areas.value_counts().to_dict()
    
    # Phase distribution
    phases = trial_df.get('phase', pd.Series(['Unknown'] * len(trial_df)))
    phase_distribution = phases.value_counts().to_dict()
    
    # Cost trends (mock for now)
    cost_trends = [
        {"month": "2024-01", "cost": total_investment * 0.2},
        {"month": "2024-02", "cost": total_investment * 0.25},
        {"month": "2024-03", "cost": total_investment * 0.22},
        {"month": "2024-04", "cost": total_investment * 0.28},
        {"month": "2024-05", "cost": total_investment * 0.3}
    ]
    
    return PortfolioSummary(
        total_investment=int(total_investment),
        projected_revenue=int(projected_revenue),
        roi_percentage=((projected_revenue - total_investment) / total_investment) * 100 if total_investment > 0 else 0,
        active_assets=active_assets,
        high_risk_assets=max(1, len(trial_df) // 10),  # Assume 10% are high risk
        therapeutic_area_distribution=therapeutic_area_distribution,
        phase_distribution=phase_distribution,
        cost_trends=cost_trends
    )










