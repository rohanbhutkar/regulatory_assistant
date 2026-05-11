from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from api_models import Trial, TrialFilters, TrialsResponse, SimulationParameters, RevenueSimulationResponse
import pandas as pd
import uuid
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

def create_trial_from_data(row: pd.Series, index: int) -> Trial:
    """Convert trial data to Trial model"""
    return Trial(
        id=f"trial_{index:03d}",
        title=row.get('trial_name', f"Trial {index}"),
        status='active' if row.get('status', '').lower() == 'active' else 'design',
        therapeutic_area=row.get('therapeutic_area', 'Unknown'),
        phase=row.get('phase', 'Phase I'),
        last_modified=pd.Timestamp.now().isoformat(),
        last_modified_by="system",
        recent_activity="Trial loaded from data",
        assigned_to=["system"]
    )

@router.get("/", response_model=TrialsResponse)
async def get_trials(
    filters: Optional[TrialFilters] = None,
    sort_by: str = "last_modified",
    sort_order: str = "desc",
    loader: DataLoader = Depends(get_data_loader)
):
    """Get trials for study designer file explorer using real data"""
    # Get trial data from CSV
    trial_df = loader.get_data('trialtrove')
    
    if trial_df.empty:
        # Fallback to mock data if CSV is empty
        MOCK_TRIALS = [
            Trial(
                id="trial_001",
                title="ONC-A-001 Phase III Study",
                status="design",
                therapeutic_area="Oncology",
                phase="Phase III",
                last_modified="2024-01-15T11:00:00Z",
                last_modified_by="Dr. Smith",
                recent_activity="Protocol section updated",
                assigned_to=["Dr. Smith", "Dr. Johnson"]
            )
        ]
        trials = MOCK_TRIALS
    else:
        # Convert trial data to trials
        trials = []
        for idx, row in trial_df.iterrows():
            try:
                trial = create_trial_from_data(row, idx)
                trials.append(trial)
            except Exception as e:
                print(f"Error creating trial from row {idx}: {e}")
                continue
    
    # Apply filters
    if filters:
        if filters.status:
            trials = [t for t in trials if t.status in filters.status]
        if filters.therapeutic_area:
            trials = [t for t in trials if t.therapeutic_area in filters.therapeutic_area]
        if filters.phase:
            trials = [t for t in trials if t.phase in filters.phase]
        if filters.assigned_to:
            trials = [t for t in trials if any(assignee in t.assigned_to for assignee in filters.assigned_to)]
    
    # Apply sorting
    reverse = sort_order == "desc"
    if sort_by == "last_modified":
        trials.sort(key=lambda x: x.last_modified, reverse=reverse)
    elif sort_by == "title":
        trials.sort(key=lambda x: x.title, reverse=reverse)
    elif sort_by == "status":
        trials.sort(key=lambda x: x.status, reverse=reverse)
    
    return TrialsResponse(
        trials=trials,
        total_count=len(trials),
        filters_applied=filters or TrialFilters()
    )

@router.get("/{trial_id}")
async def get_trial_details(trial_id: str, loader: DataLoader = Depends(get_data_loader)):
    """Get detailed trial information for design workspace"""
    # Get trial data
    trial_df = loader.get_data('trialtrove')
    
    # Find the trial
    trial = None
    if not trial_df.empty:
        try:
            trial_idx = int(trial_id.split('_')[1])
            if trial_idx < len(trial_df):
                row = trial_df.iloc[trial_idx]
                trial = create_trial_from_data(row, trial_idx)
        except:
            pass
    
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")
    
    return {
        "trial": trial,
        "protocol_sections": [
            {
                "id": "title",
                "title": "Protocol Title",
                "content": f"A {trial.phase} Study of {trial.title} in {trial.therapeutic_area}",
                "last_modified": trial.last_modified
            },
            {
                "id": "rationale",
                "title": "Rationale",
                "content": f"Based on promising results in {trial.therapeutic_area}...",
                "last_modified": trial.last_modified
            }
        ],
        "reference_trials": [
            {
                "id": "ref_001",
                "title": f"Similar {trial.therapeutic_area} Trial",
                "phase": trial.phase,
                "sponsor": "Pharma Corp",
                "primary_endpoint": "Overall Survival"
            }
        ],
        "ie_criteria": {
            "inclusion_criteria": [
                "Age ≥ 18 years",
                f"Histologically confirmed {trial.therapeutic_area} diagnosis",
                "ECOG performance status 0-1"
            ],
            "exclusion_criteria": [
                "Prior treatment with similar drugs",
                "Active infection",
                "Pregnancy or lactation"
            ]
        },
        "site_selection": {
            "selected_sites": 15,
            "target_sites": 20,
            "geographic_distribution": {
                "North America": 8,
                "Europe": 5,
                "Asia": 2
            }
        },
        "budget_calculation": {
            "cost_per_patient": 25000,
            "total_cost": 5000000,
            "cost_breakdown": {
                "screening": 2000,
                "treatment": 15000,
                "follow_up": 5000,
                "overhead": 3000
            }
        },
        "simulation_results": {
            "enrollment_time": 18,
            "success_probability": 0.78,
            "risk_factors": ["Regulatory delays", "Site activation"]
        }
    }

@router.post("/")
async def create_trial(trial_data: Dict[str, Any], loader: DataLoader = Depends(get_data_loader)):
    """Create new trial design"""
    trial_df = loader.get_data('trialtrove')
    new_id = f"trial_{len(trial_df) + 1:03d}"
    
    new_trial = Trial(
        id=new_id,
        title=trial_data.get("title", "New Trial"),
        status="design",
        therapeutic_area=trial_data.get("therapeutic_area", "Unknown"),
        phase=trial_data.get("phase", "Phase I"),
        last_modified=pd.Timestamp.now().isoformat(),
        last_modified_by="Current User",
        recent_activity="Trial created",
        assigned_to=["Current User"]
    )
    
    return new_trial

@router.post("/{trial_id}/startup-simulation")
async def run_startup_simulation(trial_id: str, simulation_params: Dict[str, Any]):
    """Run study startup simulation"""
    return {
        "simulation_id": str(uuid.uuid4()),
        "enrollment_curves": [
            {"month": 1, "enrollment": 5},
            {"month": 2, "enrollment": 12},
            {"month": 3, "enrollment": 18},
            {"month": 4, "enrollment": 25}
        ],
        "key_timepoints": [
            {"milestone": "First Patient In", "estimated_date": "2024-02-15"},
            {"milestone": "Last Patient In", "estimated_date": "2024-08-15"},
            {"milestone": "Study Completion", "estimated_date": "2025-06-15"}
        ],
        "sensitivity_analysis": {
            "screen_failure_rate": {"baseline": 0.2, "impact": "±2 months"},
            "site_activation": {"baseline": 0.8, "impact": "±1 month"}
        }
    }

@router.post("/{trial_id}/budget-calculation")
async def update_budget_calculation(trial_id: str, budget_data: Dict[str, Any]):
    """Update budget calculation"""
    return {
        "cost_per_patient": budget_data.get("cost_per_patient", 25000),
        "total_cost": budget_data.get("total_cost", 5000000),
        "cost_breakdown": budget_data.get("cost_breakdown", {
            "screening": 2000,
            "treatment": 15000,
            "follow_up": 5000,
            "overhead": 3000
        }),
        "burden_analysis": {
            "patient_burden_score": 7.5,
            "caregiver_burden_score": 6.2
        }
    }










