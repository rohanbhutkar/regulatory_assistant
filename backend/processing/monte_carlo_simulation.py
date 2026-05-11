"""
Monte Carlo Simulation Engine for Clinical Trial Enrollment and Startup
Uses historical trial data to predict enrollment patterns and risks
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class SimulationParameters:
    """Parameters for Monte Carlo simulation"""
    target_enrollment: int
    number_of_sites: int
    trial_duration_months: int
    phase: str
    therapeutic_area: str
    indication: str
    screen_failure_rate: float = 0.30  # 30% default
    dropout_rate: float = 0.10  # 10% default
    site_activation_delay_weeks: int = 8
    iterations: int = 10000  # Number of Monte Carlo iterations


@dataclass
class EnrollmentCurve:
    """Enrollment data point"""
    month: int
    enrolled_mean: float
    enrolled_p10: float  # 10th percentile
    enrolled_p50: float  # 50th percentile (median)
    enrolled_p90: float  # 90th percentile
    cumulative_mean: float
    cumulative_p10: float
    cumulative_p50: float
    cumulative_p90: float


@dataclass
class Milestone:
    """Trial milestone"""
    name: str
    date_mean: str
    date_p10: str
    date_p50: str
    date_p90: str
    probability: float
    status: str = "pending"


@dataclass
class RiskFactor:
    """Risk assessment"""
    factor: str
    probability: float
    impact: str
    mitigation: str
    severity: str


@dataclass
class SimulationResult:
    """Complete simulation result"""
    simulation_id: str
    parameters: Dict[str, Any]
    enrollment_curves: List[Dict[str, Any]]
    milestones: List[Dict[str, Any]]
    risk_factors: List[Dict[str, Any]]
    success_probability: float
    expected_completion_date: str
    expected_duration_months: float
    budget_projection: Dict[str, Any]
    confidence_interval: Dict[str, float]
    summary_statistics: Dict[str, Any]


class MonteCarloSimulationEngine:
    """
    Monte Carlo simulation engine for trial enrollment prediction
    
    Uses historical trial data to model:
    - Enrollment patterns and velocity
    - Site activation timelines
    - Screen failure and dropout rates
    - Risk factors and their impact
    """
    
    def __init__(self, historical_trials: pd.DataFrame):
        """Initialize with historical trial data"""
        self.historical_trials = historical_trials
        self._analyze_historical_data()
    
    def _analyze_historical_data(self):
        """Analyze historical data to extract parameters"""
        if self.historical_trials.empty:
            logger.warning("No historical data available for simulation")
            self._use_default_parameters()
            return
        
        logger.info(f"Analyzing {len(self.historical_trials)} historical trials")
        
        # Extract enrollment patterns
        self._extract_enrollment_patterns()
        
        # Extract duration patterns
        self._extract_duration_patterns()
        
        # Extract site performance
        self._extract_site_performance()
    
    def _use_default_parameters(self):
        """Use literature-based default parameters"""
        self.enrollment_rate_mean = 0.5  # patients per site per month
        self.enrollment_rate_std = 0.3
        self.site_activation_mean = 8  # weeks
        self.site_activation_std = 4
        self.screen_failure_mean = 0.30
        self.screen_failure_std = 0.15
        self.dropout_rate_mean = 0.10
        self.dropout_rate_std = 0.05
    
    def _extract_enrollment_patterns(self):
        """Extract enrollment patterns from historical data"""
        # Check for enrollment-related columns
        enrollment_col = None
        for col in ['Actual Accrual (No. of patients)', 'Target Accrual', 'Enrollment']:
            if col in self.historical_trials.columns:
                enrollment_col = col
                break
        
        if enrollment_col:
            enrollments = self.historical_trials[enrollment_col].dropna()
            if len(enrollments) > 0:
                # Estimate enrollment rate per site per month
                # This is simplified - would need more detailed data for accuracy
                avg_enrollment = enrollments.mean()
                self.enrollment_rate_mean = avg_enrollment / 20 / 18  # Assume 20 sites, 18 months
                self.enrollment_rate_std = enrollments.std() / 20 / 18
                logger.info(f"Enrollment rate from historical data: {self.enrollment_rate_mean:.2f} ± {self.enrollment_rate_std:.2f}")
            else:
                self._use_default_parameters()
        else:
            self._use_default_parameters()
    
    def _extract_duration_patterns(self):
        """Extract trial duration patterns"""
        # Check for duration columns
        if 'Enrollment Duration (Mos.)' in self.historical_trials.columns:
            durations = self.historical_trials['Enrollment Duration (Mos.)'].dropna()
            if len(durations) > 0:
                self.duration_mean = durations.mean()
                self.duration_std = durations.std()
                logger.info(f"Duration from historical data: {self.duration_mean:.1f} ± {self.duration_std:.1f} months")
            else:
                self.duration_mean = 18
                self.duration_std = 6
        else:
            self.duration_mean = 18
            self.duration_std = 6
    
    def _extract_site_performance(self):
        """Extract site performance metrics"""
        # Use defaults for now - would need site-level data
        self.site_activation_mean = 8  # weeks
        self.site_activation_std = 4
        self.screen_failure_mean = 0.30
        self.screen_failure_std = 0.15
        self.dropout_rate_mean = 0.10
        self.dropout_rate_std = 0.05
    
    def run_simulation(self, params: SimulationParameters) -> SimulationResult:
        """
        Run Monte Carlo simulation
        
        Args:
            params: Simulation parameters
            
        Returns:
            Complete simulation result with enrollment curves, milestones, and risks
        """
        logger.info(f"Running Monte Carlo simulation with {params.iterations} iterations")
        
        # Run Monte Carlo iterations
        simulation_results = []
        for i in range(params.iterations):
            result = self._simulate_single_trial(params)
            simulation_results.append(result)
        
        # Aggregate results
        enrollment_curves = self._aggregate_enrollment_curves(simulation_results, params)
        milestones = self._calculate_milestones(simulation_results, params)
        risk_factors = self._assess_risks(simulation_results, params)
        
        # Calculate summary statistics
        completion_times = [r['completion_month'] for r in simulation_results]
        success_count = sum(1 for r in simulation_results if r['success'])
        
        success_probability = success_count / params.iterations
        expected_completion_months = np.mean(completion_times)
        
        # Budget projection
        budget_projection = self._project_budget(params, expected_completion_months)
        
        # Confidence intervals
        confidence_interval = {
            'completion_time_p10': np.percentile(completion_times, 10),
            'completion_time_p50': np.percentile(completion_times, 50),
            'completion_time_p90': np.percentile(completion_times, 90),
        }
        
        # Summary statistics
        summary_statistics = {
            'mean_enrollment_rate': np.mean([r['enrollment_rate'] for r in simulation_results]),
            'mean_screen_failure_rate': np.mean([r['screen_failure_rate'] for r in simulation_results]),
            'mean_dropout_rate': np.mean([r['dropout_rate'] for r in simulation_results]),
            'mean_site_activation_weeks': np.mean([r['site_activation_weeks'] for r in simulation_results]),
            'probability_on_time': sum(1 for r in simulation_results if r['completion_month'] <= params.trial_duration_months) / params.iterations,
            'probability_delayed': sum(1 for r in simulation_results if r['completion_month'] > params.trial_duration_months) / params.iterations,
        }
        
        return SimulationResult(
            simulation_id=f"sim-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            parameters=asdict(params),
            enrollment_curves=[asdict(curve) for curve in enrollment_curves],
            milestones=[asdict(milestone) for milestone in milestones],
            risk_factors=[asdict(risk) for risk in risk_factors],
            success_probability=success_probability,
            expected_completion_date=(datetime.now() + timedelta(days=expected_completion_months*30)).strftime('%Y-%m-%d'),
            expected_duration_months=expected_completion_months,
            budget_projection=budget_projection,
            confidence_interval=confidence_interval,
            summary_statistics=summary_statistics
        )
    
    def _simulate_single_trial(self, params: SimulationParameters) -> Dict[str, Any]:
        """Simulate a single trial iteration"""
        # Sample parameters from distributions
        enrollment_rate = max(0.1, np.random.normal(self.enrollment_rate_mean, self.enrollment_rate_std))
        screen_failure_rate = np.clip(np.random.normal(params.screen_failure_rate, self.screen_failure_std), 0, 0.8)
        dropout_rate = np.clip(np.random.normal(params.dropout_rate, self.dropout_rate_std), 0, 0.3)
        site_activation_weeks = max(1, np.random.normal(self.site_activation_mean, self.site_activation_std))
        
        # Simulate enrollment month by month
        enrolled = []
        cumulative = 0
        active_sites = 0
        
        for month in range(params.trial_duration_months + 24):  # Allow for delays
            # Activate sites gradually
            if month <= site_activation_weeks / 4:
                active_sites = int(params.number_of_sites * (month / (site_activation_weeks / 4)))
            else:
                active_sites = params.number_of_sites
            
            # Enroll patients
            screened = int(active_sites * enrollment_rate * np.random.uniform(0.7, 1.3))
            passed_screening = int(screened * (1 - screen_failure_rate))
            enrolled_this_month = passed_screening
            
            # Account for dropouts from previous enrollments
            dropout_this_month = int(cumulative * dropout_rate / 12)  # Monthly dropout rate
            
            cumulative = cumulative + enrolled_this_month - dropout_this_month
            enrolled.append(enrolled_this_month)
            
            # Check if target reached
            if cumulative >= params.target_enrollment:
                return {
                    'success': True,
                    'completion_month': month + 1,
                    'enrollment_by_month': enrolled,
                    'enrollment_rate': enrollment_rate,
                    'screen_failure_rate': screen_failure_rate,
                    'dropout_rate': dropout_rate,
                    'site_activation_weeks': site_activation_weeks,
                    'final_enrollment': cumulative
                }
        
        # Failed to reach target
        return {
            'success': False,
            'completion_month': params.trial_duration_months + 24,
            'enrollment_by_month': enrolled,
            'enrollment_rate': enrollment_rate,
            'screen_failure_rate': screen_failure_rate,
            'dropout_rate': dropout_rate,
            'site_activation_weeks': site_activation_weeks,
            'final_enrollment': cumulative
        }
    
    def _aggregate_enrollment_curves(self, results: List[Dict], params: SimulationParameters) -> List[EnrollmentCurve]:
        """Aggregate enrollment curves across all simulations"""
        max_months = max(len(r['enrollment_by_month']) for r in results)
        curves = []
        
        for month in range(min(max_months, params.trial_duration_months + 12)):
            monthly_enrollments = []
            cumulative_enrollments = []
            
            for result in results:
                if month < len(result['enrollment_by_month']):
                    monthly_enrollments.append(result['enrollment_by_month'][month])
                    cumulative_enrollments.append(sum(result['enrollment_by_month'][:month+1]))
            
            if monthly_enrollments:
                curves.append(EnrollmentCurve(
                    month=month + 1,
                    enrolled_mean=np.mean(monthly_enrollments),
                    enrolled_p10=np.percentile(monthly_enrollments, 10),
                    enrolled_p50=np.percentile(monthly_enrollments, 50),
                    enrolled_p90=np.percentile(monthly_enrollments, 90),
                    cumulative_mean=np.mean(cumulative_enrollments),
                    cumulative_p10=np.percentile(cumulative_enrollments, 10),
                    cumulative_p50=np.percentile(cumulative_enrollments, 50),
                    cumulative_p90=np.percentile(cumulative_enrollments, 90),
                ))
        
        return curves
    
    def _calculate_milestones(self, results: List[Dict], params: SimulationParameters) -> List[Milestone]:
        """Calculate key trial milestones with uncertainty"""
        completion_times = [r['completion_month'] for r in results]
        
        # First Patient In
        first_patient_months = [max(1, int(r['site_activation_weeks'] / 4)) for r in results]
        
        # 50% Enrollment
        half_enrollment_months = []
        for r in results:
            cumulative = 0
            for month, enrolled in enumerate(r['enrollment_by_month']):
                cumulative += enrolled
                if cumulative >= params.target_enrollment / 2:
                    half_enrollment_months.append(month + 1)
                    break
        
        # Last Patient In
        completion_months = completion_times
        
        # Database Lock (assume 3 months after LPI)
        db_lock_months = [c + 3 for c in completion_months]
        
        def format_milestone(months_list, base_date=datetime.now()):
            p10 = base_date + timedelta(days=np.percentile(months_list, 10) * 30)
            p50 = base_date + timedelta(days=np.percentile(months_list, 50) * 30)
            p90 = base_date + timedelta(days=np.percentile(months_list, 90) * 30)
            mean = base_date + timedelta(days=np.mean(months_list) * 30)
            
            return {
                'mean': mean.strftime('%Y-%m-%d'),
                'p10': p10.strftime('%Y-%m-%d'),
                'p50': p50.strftime('%Y-%m-%d'),
                'p90': p90.strftime('%Y-%m-%d'),
            }
        
        fpi = format_milestone(first_patient_months)
        half_enroll = format_milestone(half_enrollment_months)
        lpi = format_milestone(completion_months)
        db_lock = format_milestone(db_lock_months)
        
        milestones = [
            Milestone(
                name="First Patient In",
                date_mean=fpi['mean'],
                date_p10=fpi['p10'],
                date_p50=fpi['p50'],
                date_p90=fpi['p90'],
                probability=1.0,
                status="pending"
            ),
            Milestone(
                name="50% Enrollment",
                date_mean=half_enroll['mean'],
                date_p10=half_enroll['p10'],
                date_p50=half_enroll['p50'],
                date_p90=half_enroll['p90'],
                probability=0.95,
                status="pending"
            ),
            Milestone(
                name="Last Patient In",
                date_mean=lpi['mean'],
                date_p10=lpi['p10'],
                date_p50=lpi['p50'],
                date_p90=lpi['p90'],
                probability=0.85,
                status="pending"
            ),
            Milestone(
                name="Database Lock",
                date_mean=db_lock['mean'],
                date_p10=db_lock['p10'],
                date_p50=db_lock['p50'],
                date_p90=db_lock['p90'],
                probability=0.85,
                status="pending"
            ),
        ]
        
        return milestones
    
    def _assess_risks(self, results: List[Dict], params: SimulationParameters) -> List[RiskFactor]:
        """Assess risk factors based on simulation results"""
        risks = []
        
        # Enrollment risk
        success_rate = sum(1 for r in results if r['success']) / len(results)
        if success_rate < 0.7:
            risks.append(RiskFactor(
                factor="Enrollment Risk",
                probability=1 - success_rate,
                impact="High - May not reach target enrollment",
                mitigation="Add backup sites, increase recruitment budget, expand eligibility criteria",
                severity="High" if success_rate < 0.5 else "Medium"
            ))
        
        # Site activation risk
        avg_activation = np.mean([r['site_activation_weeks'] for r in results])
        if avg_activation > 12:
            risks.append(RiskFactor(
                factor="Site Activation Delays",
                probability=0.6,
                impact="Medium - Delayed study start",
                mitigation="Start IRB submissions early, pre-qualify sites, expedite contracts",
                severity="Medium"
            ))
        
        # Screen failure risk
        avg_screen_failure = np.mean([r['screen_failure_rate'] for r in results])
        if avg_screen_failure > 0.4:
            risks.append(RiskFactor(
                factor="High Screen Failure Rate",
                probability=0.5,
                impact="Medium - Increased screening costs and timeline",
                mitigation="Review eligibility criteria, improve patient prescreening",
                severity="Medium"
            ))
        
        # Dropout risk
        avg_dropout = np.mean([r['dropout_rate'] for r in results])
        if avg_dropout > 0.15:
            risks.append(RiskFactor(
                factor="Patient Dropout",
                probability=0.4,
                impact="Medium - May need to over-enroll",
                mitigation="Improve patient engagement, reduce visit burden, provide compensation",
                severity="Medium"
            ))
        
        # Timeline risk
        completion_times = [r['completion_month'] for r in results]
        delay_probability = sum(1 for t in completion_times if t > params.trial_duration_months) / len(completion_times)
        if delay_probability > 0.3:
            risks.append(RiskFactor(
                factor="Timeline Delays",
                probability=delay_probability,
                impact="High - Study completion beyond planned timeline",
                mitigation="Build timeline buffer, accelerate site activation, increase sites",
                severity="High" if delay_probability > 0.5 else "Medium"
            ))
        
        return risks
    
    def _project_budget(self, params: SimulationParameters, expected_months: float) -> Dict[str, Any]:
        """Project budget based on simulation results"""
        # Industry-standard cost estimates
        cost_per_patient = {
            'Phase I': 40000,
            'Phase II': 30000,
            'Phase III': 25000,
            'Phase IV': 20000,
        }.get(params.phase, 25000)
        
        site_initiation_cost = 50000
        site_maintenance_monthly = 5000
        monitoring_cost_per_patient = 2000
        
        # Calculate costs
        patient_costs = params.target_enrollment * cost_per_patient
        site_costs = (params.number_of_sites * site_initiation_cost) + \
                     (params.number_of_sites * site_maintenance_monthly * expected_months)
        monitoring_costs = params.target_enrollment * monitoring_cost_per_patient
        overhead = (patient_costs + site_costs + monitoring_costs) * 0.15
        
        total_cost = patient_costs + site_costs + monitoring_costs + overhead
        
        return {
            'total_cost': int(total_cost),
            'cost_per_patient': cost_per_patient,
            'breakdown': {
                'patient_costs': int(patient_costs),
                'site_costs': int(site_costs),
                'monitoring_costs': int(monitoring_costs),
                'overhead': int(overhead),
            },
            'monthly_burn_rate': int(total_cost / expected_months),
        }









