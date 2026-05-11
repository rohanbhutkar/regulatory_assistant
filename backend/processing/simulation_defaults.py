"""
Default configurations for advanced Monte Carlo simulation
==========================================================

Provides industry-standard defaults for countries, regulatory events,
operational parameters, and financial parameters.
"""

from typing import Dict, List
import numpy as np
from processing.advanced_monte_carlo import (
    CountryConfiguration,
    FinancialParameters,
    OperationalParameters,
    RegulatoryEvent
)


def get_default_country_configs() -> Dict[str, CountryConfiguration]:
    """Get default country configurations for major regions"""
    return {
        'US': CountryConfiguration(
            country_code='US',
            country_name='United States',
            regulatory_approval_weeks_mean=20,  # FDA ~5 months
            regulatory_approval_weeks_std=6,
            regulatory_success_probability=0.96,
            cost_multiplier=1.5,  # Higher cost in US
            healthcare_infrastructure_score=9.0,
            competing_trials_count=15,  # High competition
            patient_acceptance_multiplier=1.0,
        ),
        'GB': CountryConfiguration(
            country_code='GB',
            country_name='United Kingdom',
            regulatory_approval_weeks_mean=24,  # MHRA ~6 months
            regulatory_approval_weeks_std=8,
            regulatory_success_probability=0.95,
            cost_multiplier=1.2,
            healthcare_infrastructure_score=9.0,
            competing_trials_count=10,
            patient_acceptance_multiplier=1.0,
        ),
        'DE': CountryConfiguration(
            country_code='DE',
            country_name='Germany',
            regulatory_approval_weeks_mean=26,  # BfArM ~6.5 months
            regulatory_approval_weeks_std=8,
            regulatory_success_probability=0.94,
            cost_multiplier=1.1,
            healthcare_infrastructure_score=9.0,
            competing_trials_count=8,
            patient_acceptance_multiplier=0.95,
        ),
        'FR': CountryConfiguration(
            country_code='FR',
            country_name='France',
            regulatory_approval_weeks_mean=28,  # ANSM ~7 months
            regulatory_approval_weeks_std=10,
            regulatory_success_probability=0.93,
            cost_multiplier=1.1,
            healthcare_infrastructure_score=8.5,
            competing_trials_count=7,
            patient_acceptance_multiplier=0.9,
        ),
        'CA': CountryConfiguration(
            country_code='CA',
            country_name='Canada',
            regulatory_approval_weeks_mean=22,  # Health Canada ~5.5 months
            regulatory_approval_weeks_std=7,
            regulatory_success_probability=0.95,
            cost_multiplier=1.3,
            healthcare_infrastructure_score=9.0,
            competing_trials_count=8,
            patient_acceptance_multiplier=1.0,
        ),
        'AU': CountryConfiguration(
            country_code='AU',
            country_name='Australia',
            regulatory_approval_weeks_mean=20,  # TGA ~5 months
            regulatory_approval_weeks_std=6,
            regulatory_success_probability=0.96,
            cost_multiplier=1.2,
            healthcare_infrastructure_score=8.5,
            competing_trials_count=5,
            patient_acceptance_multiplier=1.0,
        ),
        'JP': CountryConfiguration(
            country_code='JP',
            country_name='Japan',
            regulatory_approval_weeks_mean=32,  # PMDA ~8 months
            regulatory_approval_weeks_std=12,
            regulatory_success_probability=0.90,
            cost_multiplier=1.6,  # Higher cost
            healthcare_infrastructure_score=9.0,
            competing_trials_count=6,
            patient_acceptance_multiplier=0.85,  # Cultural factors
        ),
        'CN': CountryConfiguration(
            country_code='CN',
            country_name='China',
            regulatory_approval_weeks_mean=36,  # NMPA ~9 months
            regulatory_approval_weeks_std=14,
            regulatory_success_probability=0.88,
            cost_multiplier=0.7,  # Lower cost
            healthcare_infrastructure_score=7.0,
            competing_trials_count=10,
            patient_acceptance_multiplier=0.9,
        ),
        'IN': CountryConfiguration(
            country_code='IN',
            country_name='India',
            regulatory_approval_weeks_mean=28,  # CDSCO ~7 months
            regulatory_approval_weeks_std=10,
            regulatory_success_probability=0.91,
            cost_multiplier=0.4,  # Much lower cost
            healthcare_infrastructure_score=6.5,
            competing_trials_count=8,
            patient_acceptance_multiplier=1.1,  # Good acceptance
        ),
        'BR': CountryConfiguration(
            country_code='BR',
            country_name='Brazil',
            regulatory_approval_weeks_mean=30,  # ANVISA ~7.5 months
            regulatory_approval_weeks_std=12,
            regulatory_success_probability=0.89,
            cost_multiplier=0.6,
            healthcare_infrastructure_score=6.0,
            competing_trials_count=6,
            patient_acceptance_multiplier=1.0,
        ),
        'MX': CountryConfiguration(
            country_code='MX',
            country_name='Mexico',
            regulatory_approval_weeks_mean=24,  # COFEPRIS ~6 months
            regulatory_approval_weeks_std=8,
            regulatory_success_probability=0.92,
            cost_multiplier=0.5,
            healthcare_infrastructure_score=6.5,
            competing_trials_count=5,
            patient_acceptance_multiplier=1.0,
        ),
        'PL': CountryConfiguration(
            country_code='PL',
            country_name='Poland',
            regulatory_approval_weeks_mean=26,  # ~6.5 months
            regulatory_approval_weeks_std=8,
            regulatory_success_probability=0.94,
            cost_multiplier=0.7,
            healthcare_infrastructure_score=7.5,
            competing_trials_count=6,
            patient_acceptance_multiplier=1.0,
        ),
        'ES': CountryConfiguration(
            country_code='ES',
            country_name='Spain',
            regulatory_approval_weeks_mean=28,  # AEMPS ~7 months
            regulatory_approval_weeks_std=10,
            regulatory_success_probability=0.93,
            cost_multiplier=1.0,
            healthcare_infrastructure_score=8.0,
            competing_trials_count=7,
            patient_acceptance_multiplier=0.95,
        ),
        'IT': CountryConfiguration(
            country_code='IT',
            country_name='Italy',
            regulatory_approval_weeks_mean=30,  # AIFA ~7.5 months
            regulatory_approval_weeks_std=12,
            regulatory_success_probability=0.92,
            cost_multiplier=1.0,
            healthcare_infrastructure_score=8.0,
            competing_trials_count=6,
            patient_acceptance_multiplier=0.9,
        ),
        'KR': CountryConfiguration(
            country_code='KR',
            country_name='South Korea',
            regulatory_approval_weeks_mean=28,  # MFDS ~7 months
            regulatory_approval_weeks_std=10,
            regulatory_success_probability=0.93,
            cost_multiplier=1.1,
            healthcare_infrastructure_score=8.5,
            competing_trials_count=7,
            patient_acceptance_multiplier=0.95,
        ),
    }


def get_default_regulatory_events(phase: str) -> List[RegulatoryEvent]:
    """Get default regulatory events based on trial phase"""
    
    # Base events for all phases
    events = [
        RegulatoryEvent(
            event_type='routine_audit',
            probability_per_year=0.15,  # 15% chance per year
            duration_weeks=2,
            impact_on_enrollment=0.7  # Slows to 70% during audit
        ),
        RegulatoryEvent(
            event_type='protocol_amendment',
            probability_per_year=0.25,  # 25% chance per year
            duration_weeks=6,
            impact_on_enrollment=0.5  # Slows to 50% during amendment
        ),
    ]
    
    # Phase-specific events
    if phase in ['Phase I', 'Phase II']:
        events.append(RegulatoryEvent(
            event_type='safety_signal',
            probability_per_year=0.15,  # Higher in early phases
            duration_weeks=8,
            impact_on_enrollment=0.3  # Significant slowdown
        ))
    
    if phase in ['Phase II', 'Phase III']:
        events.append(RegulatoryEvent(
            event_type='clinical_hold',
            probability_per_year=0.05,  # 5% chance
            duration_weeks=12,
            impact_on_enrollment=0.0  # Complete halt
        ))
    
    if phase == 'Phase III':
        events.append(RegulatoryEvent(
            event_type='dsmb_review',
            probability_per_year=0.5,  # Scheduled reviews
            duration_weeks=3,
            impact_on_enrollment=0.8  # Minor slowdown
        ))
    
    return events


def get_default_financial_params(
    phase: str,
    target_enrollment: int,
    trial_duration_months: int,
    number_of_sites: int
) -> FinancialParameters:
    """Get default financial parameters based on phase and scale"""
    
    # Phase-specific costs per patient
    costs_by_phase = {
        'Phase I': {
            'screening': 1000,
            'enrollment': 2000,
            'treatment': 5000,
            'followup': 500,
        },
        'Phase II': {
            'screening': 750,
            'enrollment': 1500,
            'treatment': 3500,
            'followup': 400,
        },
        'Phase III': {
            'screening': 500,
            'enrollment': 1000,
            'treatment': 2500,
            'followup': 300,
        },
        'Phase IV': {
            'screening': 400,
            'enrollment': 800,
            'treatment': 2000,
            'followup': 250,
        },
    }
    
    costs = costs_by_phase.get(phase, costs_by_phase['Phase II'])
    
    # Estimate total budget
    patient_costs = target_enrollment * sum(costs.values())
    site_costs = number_of_sites * (5000 + 1000 * trial_duration_months + 2000)
    overhead = (patient_costs + site_costs) * 0.20  # 20% overhead
    
    total_budget = patient_costs + site_costs + overhead
    
    return FinancialParameters(
        total_budget=total_budget * 1.2,  # 20% buffer
        monthly_burn_rate_target=total_budget / trial_duration_months,
        cost_per_patient_screening=costs['screening'],
        cost_per_patient_enrollment=costs['enrollment'],
        cost_per_patient_treatment=costs['treatment'],
        cost_per_patient_followup=costs['followup'],
        cost_per_site_initiation=5000,
        cost_per_site_monthly=1000,
        cost_per_site_closeout=2000,
        budget_constrained=False  # Default: don't constrain by budget
    )


def get_default_operational_params(number_of_sites: int) -> OperationalParameters:
    """Get default operational parameters based on site count"""
    
    # Scale CRA count based on sites
    cra_count = max(1, int(np.ceil(number_of_sites / 8)))
    
    return OperationalParameters(
        cra_count=cra_count,
        sites_per_cra=8.0,
        max_sites_activated_per_month=max(2, int(number_of_sites / 4)),  # Activate over ~4 months
        data_manager_capacity_hours_per_month=160 * max(1, int(number_of_sites / 15)),
        hours_per_query=0.5,
        ae_review_time_hours=0.5,
        expected_ae_rate_per_patient=0.2,
    )

