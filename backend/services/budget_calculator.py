"""
Enhanced Budget Calculator Service
Integrates all study components to create comprehensive budget
"""

from typing import Dict, List, Any
from decimal import Decimal
import numpy as np
import logging
from services.budget_calculator_extended import BudgetCalculatorExtensions

logger = logging.getLogger(__name__)


class EnhancedBudgetCalculator:
    """
    Production-grade budget calculator integrating all study components
    """
    
    def __init__(
        self,
        study_context: Dict[str, Any],
        reference_trials: List[Dict],
        study_design: Dict[str, Any],
        ie_criteria: Dict[str, Any],
        endpoints: List[Dict],
        soa_data: Dict[str, Any],
        selected_sites: List[Dict],
        simulation_results: Dict[str, Any]
    ):
        self.study_context = study_context
        self.reference_trials = reference_trials
        self.study_design = study_design
        self.ie_criteria = ie_criteria
        self.endpoints = endpoints
        self.soa_data = soa_data
        self.sites = selected_sites
        self.simulation = simulation_results
        
        # Cost databases
        self.procedure_costs = self._load_procedure_costs()
        self.country_multipliers = self._load_country_multipliers()
        self.phase_overhead_rates = {
            'Phase I': 0.25,
            'Phase II': 0.30,
            'Phase III': 0.35,
            'Phase IV': 0.20
        }
        
        # Cache for visit breakdown
        self._visit_breakdown = []
    
    def calculate_complete_budget(self) -> Dict[str, Any]:
        """Main entry point - calculate complete budget"""
        
        logger.info("💰 Starting comprehensive budget calculation...")
        
        # 1. Calculate per-patient costs
        patient_costs = self._calculate_patient_costs()
        logger.info(f"   Patient costs: ${patient_costs['total_patient_costs']:,.0f}")
        
        # 2. Calculate site costs
        site_costs = self._calculate_site_costs()
        logger.info(f"   Site costs: ${site_costs['total_site_costs']:,.0f}")
        
        # 3. Calculate operational costs
        operational_costs = self._calculate_operational_costs()
        logger.info(f"   Operational costs: ${operational_costs['total_operational_costs']:,.0f}")
        
        # 4. Calculate overhead
        base_costs = Decimal(str(patient_costs['total_patient_costs'])) + \
                    Decimal(str(site_costs['total_site_costs'])) + \
                    Decimal(str(operational_costs['total_operational_costs']))
        overhead = self._calculate_overhead(base_costs)
        logger.info(f"   Overhead: ${overhead['amount']:,.0f}")
        
        # 5. Calculate risk contingency
        contingency = self._calculate_contingency()
        
        # 6. Aggregate totals
        total_budget = self._aggregate_budget(
            patient_costs,
            site_costs,
            operational_costs,
            overhead,
            contingency
        )
        logger.info(f"   Grand total: ${total_budget['grand_total']:,.0f}")
        
        # 7. Create detailed breakdown
        breakdown = {
            'patient_costs': patient_costs,
            'site_costs': site_costs,
            'operational_costs': operational_costs,
            'overhead': overhead,
            'contingency': contingency
        }
        
        # 8. Generate risk scenarios
        scenarios = self._generate_risk_scenarios(total_budget)
        
        # 9. Create cashflow projections
        cashflow = self._create_cashflow_projections(total_budget)
        
        # 10. Calculate summary metrics
        summary_metrics = self._calculate_summary_metrics(total_budget)
        
        # 11. Calculate additional cost categories (B&C features)
        total_patients = self.study_design.get('totalParticipants', 300)
        phase = self.study_context.get('phase', 'Phase III')
        therapeutic_area = self.study_context.get('therapeutic_area', 'General')
        duration_months = int(self.simulation.get('expected_duration_months', 24))
        num_sites = len(self.sites) if self.sites else 100
        num_arms = len(self.study_design.get('arms', [])) or 2
        
        # Additional CRF payments
        additional_crf = BudgetCalculatorExtensions.calculate_additional_crf_payments(
            total_patients, phase, therapeutic_area
        )
        logger.info(f"   Additional CRF payments: ${additional_crf['total']:,.0f}")
        
        # Invoice items
        invoice_items = BudgetCalculatorExtensions.calculate_invoice_items(
            total_patients, phase, duration_months
        )
        logger.info(f"   Invoice items: ${invoice_items['total']:,.0f}")
        
        # Study-level fees
        num_countries = len(set(site.get('country', 'USA') for site in self.sites)) if self.sites else 1
        study_level_fees = BudgetCalculatorExtensions.calculate_study_level_fees(
            num_sites, num_countries, phase, duration_months
        )
        logger.info(f"   Study-level fees: ${study_level_fees['total']:,.0f}")
        
        # Total additional costs
        total_additional_costs = (
            additional_crf['total'] + 
            invoice_items['total'] + 
            study_level_fees['total']
        )
        
        # 12. Drug supply chain costs
        drug_supply = BudgetCalculatorExtensions.calculate_drug_supply_chain(
            total_patients, duration_months, num_arms, phase
        )
        logger.info(f"   Drug supply chain: ${drug_supply['total']:,.0f}")
        
        # 13. Screening & dropout detailed
        screen_failure_rate = self.ie_criteria.get('populationAnalysis', {}).get('screening_impact', 0.30)
        dropout_rate = self.simulation.get('summary_statistics', {}).get('mean_dropout_rate', 0.15)
        base_cpp = patient_costs.get('base_cpp', 50000)
        
        screening_dropout = BudgetCalculatorExtensions.calculate_screening_and_dropout_detailed(
            total_patients, screen_failure_rate, dropout_rate, base_cpp
        )
        
        # 14. Country breakdown
        country_allocations = self.study_context.get('country_allocations', None)
        base_total_for_countries = total_budget['grand_total']
        country_budgets, globalized_total = BudgetCalculatorExtensions.calculate_country_breakdown(
            total_patients, num_sites, base_total_for_countries, country_allocations
        )
        logger.info(f"   Globalized total (with FX buffer): ${globalized_total:,.0f}")
        
        # 15. Enhanced overhead breakdown
        enhanced_overhead = BudgetCalculatorExtensions.calculate_enhanced_overhead_breakdown(
            float(base_costs), overhead['rate']
        )
        
        # Calculate updated grand total with additional costs
        updated_grand_total = (
            total_budget['grand_total'] + 
            total_additional_costs + 
            drug_supply['total']
        )
        
        logger.info(f"✅ Budget calculation complete - Updated total: ${updated_grand_total:,.0f}")
        
        return {
            'total_budget': total_budget,
            'breakdown': breakdown,
            'scenarios': scenarios,
            'cashflow': cashflow,
            'summary_metrics': summary_metrics,
            # B&C Additional features
            'additional_crf_payments': additional_crf,
            'invoice_items': invoice_items,
            'study_level_fees': study_level_fees,
            'total_additional_costs': total_additional_costs,
            'drug_supply_chain': drug_supply,
            'screening_and_dropout': screening_dropout,
            'country_budgets': country_budgets,
            'globalized_total_usd': globalized_total,
            'enhanced_overhead': enhanced_overhead,
            'updated_grand_total': updated_grand_total
        }
    
    # ========================================================================
    # PATIENT COSTS (Primary Component - from SoA)
    # ========================================================================
    
    def _calculate_patient_costs(self) -> Dict[str, Any]:
        """Calculate all per-patient costs from SoA and additional components"""
        
        # Get patient count from study design
        total_patients = self.study_design.get('totalParticipants', 0)
        
        if total_patients == 0:
            logger.warning("No patients specified in study design, using default 300")
            total_patients = 300
        
        # Calculate base cost per patient from SoA
        base_cpp = self._calculate_cpp_from_soa()
        
        # OPAL Overhead per patient
        opal_cpp = self._calculate_opal_per_patient()
        
        # PRDL (Patient Reimbursement for Direct Losses)
        prdl_cpp = self._calculate_prdl_per_patient()
        
        # Drug/Packaging costs
        drug_packaging_cpp = self._calculate_drug_packaging_per_patient()
        
        # Labs costs (beyond basic SoA)
        additional_labs_cpp = self._calculate_additional_labs_per_patient()
        
        # Total CPP
        total_cpp = base_cpp + opal_cpp + prdl_cpp + drug_packaging_cpp + additional_labs_cpp
        
        # Screen failure costs
        screen_failure_rate = float(self.ie_criteria.get('populationAnalysis', {}).get('screening_impact', 0.30))
        screening_patients = int(total_patients / (1 - screen_failure_rate)) - total_patients
        screening_costs = self._calculate_screening_costs(screening_patients)
        
        # Dropout replacement costs
        dropout_rate = self.simulation.get('summary_statistics', {}).get('mean_dropout_rate', 0.10)
        dropout_replacements = int(total_patients * dropout_rate)
        dropout_costs = float(dropout_replacements * total_cpp)
        
        # Total patient costs
        enrolled_costs = float(total_patients * total_cpp)
        total_patient_costs = enrolled_costs + screening_costs + dropout_costs
        
        return {
            'base_cpp': float(base_cpp),
            'opal_cpp': float(opal_cpp),
            'prdl_cpp': float(prdl_cpp),
            'drug_packaging_cpp': float(drug_packaging_cpp),
            'additional_labs_cpp': float(additional_labs_cpp),
            'total_cpp': float(total_cpp),
            'enrolled_patients': total_patients,
            'enrolled_costs': enrolled_costs,
            'screening_patients': screening_patients,
            'screening_costs': screening_costs,
            'dropout_replacements': dropout_replacements,
            'dropout_replacement_costs': dropout_costs,
            'total_patient_costs': total_patient_costs,
            'breakdown_by_category': self._get_cost_by_category(),
            'breakdown_by_visit': self._visit_breakdown,
            'cpp_breakdown': {
                'base_procedures': float(base_cpp),
                'opal_overhead': float(opal_cpp),
                'prdl_reimbursement': float(prdl_cpp),
                'drug_packaging': float(drug_packaging_cpp),
                'additional_labs': float(additional_labs_cpp),
                'total': float(total_cpp)
            }
        }
    
    def _calculate_cpp_from_soa(self) -> Decimal:
        """Calculate cost per patient from Schedule of Activities"""
        
        visits = self.soa_data.get('visits', [])
        activities = self.soa_data.get('activities', [])
        
        if not visits or not activities:
            logger.warning("No SoA data available, using default CPP")
            return Decimal('50000.00')  # Default $50k CPP
        
        total_cpp = Decimal('0.00')
        visit_costs = []
        
        for visit in visits:
            visit_id = visit['id']
            visit_cost = Decimal('0.00')
            
            # Get all activities for this visit
            for activity in activities:
                if activity['visits'].get(visit_id, False):
                    # Look up procedure cost
                    proc_cost = self._get_procedure_cost(
                        activity['category'],
                        activity['name']
                    )
                    
                    # Apply frequency multiplier if specified
                    frequency = activity.get('frequency', 1)
                    
                    # Apply probability multiplier if optional
                    probability = 1.0 if not activity.get('optional', False) else 0.7
                    
                    activity_cost = proc_cost * Decimal(str(frequency)) * Decimal(str(probability))
                    visit_cost += activity_cost
            
            visit_costs.append({
                'visit_name': visit['name'],
                'visit_week': visit['week'],
                'cost': float(visit_cost)
            })
            
            total_cpp += visit_cost
        
        # Apply complexity multipliers
        total_cpp = self._apply_complexity_multipliers(total_cpp)
        
        self._visit_breakdown = visit_costs  # Store for later use
        
        return total_cpp
    
    def _get_procedure_cost(self, category: str, name: str) -> Decimal:
        """Look up procedure cost from cost database"""
        
        # Default costs by category
        default_costs = {
            'Screening': {
                'Informed Consent': 50.00,
                'Medical History': 100.00,
                'Physical Examination': 150.00,
                'Demographics': 50.00
            },
            'Laboratory': {
                'Complete Blood Count': 75.00,
                'Chemistry Panel': 100.00,
                'Liver Function Tests': 150.00,
                'Urinalysis': 50.00,
                'Pregnancy Test': 30.00,
                'Tumor Markers': 500.00,
                'Genetic Testing': 2000.00
            },
            'Imaging': {
                'Chest X-Ray': 200.00,
                'CT Scan': 1500.00,
                'MRI': 2500.00,
                'PET Scan': 3000.00,
                'Ultrasound': 500.00,
                'DEXA Scan': 300.00
            },
            'Assessments': {
                'Vital Signs': 75.00,
                'ECG': 150.00,
                'Echocardiogram': 500.00,
                'ECOG Performance Status': 50.00,
                'Quality of Life Questionnaire': 100.00,
                'Cognitive Assessment': 200.00
            },
            'Treatment': {
                'Study Drug Administration': 250.00,
                'IV Infusion': 300.00,
                'Injection': 150.00,
                'Dose Preparation': 200.00
            },
            'Safety': {
                'Adverse Event Assessment': 100.00,
                'Concomitant Medication Review': 75.00
            },
            'Procedures': {
                'Tissue Biopsy': 1500.00,
                'Bone Marrow Biopsy': 2000.00,
                'Endoscopy': 1000.00,
                'Colonoscopy': 1200.00,
                'Lumbar Puncture': 800.00
            }
        }
        
        # Look up cost
        category_costs = default_costs.get(category, {})
        cost = category_costs.get(name, 100.00)  # Default $100 if not found
        
        # Adjust for therapeutic area
        ta_multiplier = self._get_ta_multiplier()
        
        return Decimal(str(cost * ta_multiplier))
    
    def _apply_complexity_multipliers(self, base_cpp: Decimal) -> Decimal:
        """Apply study complexity multipliers"""
        
        multiplier = Decimal('1.0')
        
        # Multiple arms increase complexity
        num_arms = self.study_design.get('numberOfArms', 1)
        if num_arms > 2:
            multiplier *= Decimal('1.10') ** (num_arms - 2)
        
        # Complex endpoints increase monitoring
        num_endpoints = len(self.endpoints)
        if num_endpoints > 3:
            multiplier *= Decimal('1.05')
        
        # Blinded studies increase costs
        study_type = self.study_design.get('studyType', '')
        if study_type and 'blind' in study_type.lower():
            multiplier *= Decimal('1.15')
        
        return base_cpp * multiplier
    
    def _calculate_opal_per_patient(self) -> Decimal:
        """
        Calculate OPAL (Overhead Per Active Lab) score per patient.
        OPAL represents the administrative and operational overhead for managing
        lab samples, results, and data coordination per patient.
        """
        
        # Count lab activities in SoA
        lab_count = 0
        for activity in self.soa_data.get('activities', []):
            if activity['category'] in ['Labs', 'Imaging', 'Biomarkers']:
                # Count visits where this activity occurs
                visit_count = sum(1 for v in activity['visits'].values() if v)
                lab_count += visit_count
        
        # OPAL score calculation
        # Base: $50 per lab activity for coordination, tracking, shipping
        base_opal = Decimal('50.00') * lab_count
        
        # Therapeutic area multipliers
        ta_multiplier = Decimal('1.0')
        indication = self.study_design.get('indication', '').lower()
        if 'oncology' in indication or 'cancer' in indication:
            ta_multiplier = Decimal('1.5')  # Higher due to complex biomarkers
        elif 'rare disease' in indication or 'orphan' in indication:
            ta_multiplier = Decimal('1.8')  # Highest due to specialized labs
        
        # Phase multipliers (more complex in later phases)
        phase = self.study_design.get('phase', '')
        phase_multiplier = {
            'Phase I': Decimal('1.0'),
            'Phase II': Decimal('1.2'),
            'Phase III': Decimal('1.3'),
            'Phase IV': Decimal('1.1')
        }.get(phase, Decimal('1.0'))
        
        opal_cpp = base_opal * ta_multiplier * phase_multiplier
        
        return opal_cpp
    
    def _calculate_prdl_per_patient(self) -> Decimal:
        """
        Calculate PRDL (Patient Reimbursement for Direct Losses) per patient.
        Includes travel, parking, meals, childcare, lost wages, etc.
        """
        
        # Count all on-site visits (excluding remote/phone visits)
        onsite_visits = 0
        for visit in self.soa_data.get('visits', []):
            visit_name = visit.get('name', '').lower()
            if not any(remote in visit_name for remote in ['phone', 'remote', 'telehealth']):
                onsite_visits += 1
        
        # Base reimbursement per visit
        per_visit_reimbursement = {
            'travel': Decimal('75.00'),      # Mileage/gas/public transport
            'parking': Decimal('20.00'),     # Parking fees
            'meals': Decimal('30.00'),       # Meal allowance
            'childcare': Decimal('50.00'),   # If applicable (~50% need it)
            'lost_wages': Decimal('100.00')  # Partial wage reimbursement (~30% need it)
        }
        
        # Calculate weighted average per visit
        per_visit_prdl = (
            per_visit_reimbursement['travel'] +
            per_visit_reimbursement['parking'] +
            per_visit_reimbursement['meals'] +
            (per_visit_reimbursement['childcare'] * Decimal('0.5')) +
            (per_visit_reimbursement['lost_wages'] * Decimal('0.3'))
        )
        
        # Total PRDL
        total_prdl = per_visit_prdl * onsite_visits
        
        # Geographic multiplier based on site locations
        geo_multiplier = Decimal('1.0')
        if self.sites:
            # Higher costs in US/EU
            countries = [site.get('country', 'US') for site in self.sites]
            if any(c in ['US', 'USA', 'United States'] for c in countries):
                geo_multiplier = Decimal('1.3')
            elif any(c in ['UK', 'Germany', 'France', 'Switzerland'] for c in countries):
                geo_multiplier = Decimal('1.2')
        
        return total_prdl * geo_multiplier
    
    def _calculate_drug_packaging_per_patient(self) -> Decimal:
        """
        Calculate drug supply and packaging costs per patient.
        Includes IMP/NIMP, comparators, placebo, storage, distribution.
        """
        
        # Get study duration and dosing frequency
        duration_months = self.study_design.get('treatmentDuration', 12)
        # Convert to Decimal to avoid type mixing errors
        duration_months_decimal = Decimal(str(duration_months))
        num_arms = self.study_design.get('numberOfArms', 1)
        
        # Base drug costs by indication (highly variable)
        indication = self.study_design.get('indication', '').lower()
        
        # Cost per patient per month
        base_drug_cost_pm = Decimal('500.00')  # Default
        
        if 'oncology' in indication or 'cancer' in indication:
            base_drug_cost_pm = Decimal('3000.00')  # High cost biologics
        elif 'rare disease' in indication:
            base_drug_cost_pm = Decimal('5000.00')  # Ultra-high cost
        elif 'cardiovascular' in indication:
            base_drug_cost_pm = Decimal('800.00')
        elif 'diabetes' in indication:
            base_drug_cost_pm = Decimal('600.00')
        elif 'respiratory' in indication:
            base_drug_cost_pm = Decimal('700.00')
        
        # Drug costs
        drug_costs = base_drug_cost_pm * duration_months_decimal
        
        # Packaging costs (15% of drug costs)
        packaging_costs = drug_costs * Decimal('0.15')
        
        # Comparator costs (if multiple arms, assume 1 is placebo/comparator)
        comparator_multiplier = Decimal('1.0')
        if num_arms > 1:
            comparator_multiplier = Decimal('1.3')  # 30% more for comparator arm
        
        # Storage and distribution (5% of drug costs)
        storage_costs = drug_costs * Decimal('0.05')
        
        # Wastage (10% overage)
        wastage_multiplier = Decimal('1.10')
        
        total_drug_packaging = (
            (drug_costs + packaging_costs + storage_costs) *
            comparator_multiplier *
            wastage_multiplier
        )
        
        return total_drug_packaging
    
    def _calculate_additional_labs_per_patient(self) -> Decimal:
        """
        Calculate additional lab costs beyond basic SoA procedures.
        Includes central lab fees, shipping, special handling, batch testing.
        """
        
        # Count lab samples from SoA
        lab_samples = 0
        for activity in self.soa_data.get('activities', []):
            if activity['category'] == 'Labs':
                # Count visits
                visit_count = sum(1 for v in activity['visits'].values() if v)
                lab_samples += visit_count
        
        # Central lab fees (per sample processing, QC, reporting)
        central_lab_fee = Decimal('150.00')  # Per sample
        
        # Shipping and handling (per sample)
        shipping_fee = Decimal('50.00')
        
        # Special handling (biomarkers, genetic testing - ~20% of samples)
        special_handling_rate = Decimal('0.20')
        special_handling_fee = Decimal('300.00')
        
        # Batch testing coordination
        batch_fee = Decimal('100.00') * Decimal(str(int(lab_samples / 10) + 1))  # Per 10 samples
        
        total_lab_costs = (
            (central_lab_fee + shipping_fee) * lab_samples +
            (special_handling_fee * lab_samples * special_handling_rate) +
            batch_fee
        )
        
        return total_lab_costs
    
    def _calculate_screening_costs(self, screening_patients: int) -> float:
        """Calculate costs for screen failure patients"""
        
        if screening_patients == 0:
            return 0.0
        
        # Get screening visit activities
        screening_visit_cost = Decimal('0.00')
        
        for visit in self.soa_data.get('visits', []):
            if 'screen' in visit['name'].lower():
                for activity in self.soa_data.get('activities', []):
                    if activity['visits'].get(visit['id'], False):
                        proc_cost = self._get_procedure_cost(
                            activity['category'],
                            activity['name']
                        )
                        screening_visit_cost += proc_cost
        
        # If no explicit screening visit, estimate as 15% of full CPP
        if screening_visit_cost == 0:
            base_cpp = self._calculate_cpp_from_soa()
            screening_visit_cost = base_cpp * Decimal('0.15')
        
        return float(screening_visit_cost * screening_patients)
    
    # ========================================================================
    # SITE COSTS
    # ========================================================================
    
    def _calculate_site_costs(self) -> Dict[str, Any]:
        """Calculate all site-related costs"""
        
        num_sites = len(self.sites)
        
        if num_sites == 0:
            logger.warning("No sites selected, using default 10 sites")
            num_sites = 10
        
        duration_months = self.simulation.get('expected_duration_months', 24)
        # Convert to Decimal to avoid type mixing errors with Decimal arithmetic
        duration_months_decimal = Decimal(str(duration_months))
        
        # Site initiation costs
        initiation_costs = []
        total_initiation = Decimal('0.00')
        
        for site in self.sites:
            base_init = Decimal('50000.00')  # Base $50k per site
            
            # Adjust by country
            country = site.get('country', site.get('Country', 'US'))
            country_mult = Decimal(str(self._get_country_multiplier(country)))
            
            # Adjust by organization type
            org_type = site.get('organization_type', '')
            org_mult = Decimal('1.2') if 'academic' in org_type.lower() else Decimal('1.0')
            
            site_init_cost = base_init * country_mult * org_mult
            
            initiation_costs.append({
                'site_id': site.get('site_id', site.get('id', '')),
                'site_name': site.get('site_name', site.get('name', 'Unknown Site')),
                'cost': float(site_init_cost)
            })
            
            total_initiation += site_init_cost
        
        # Monthly monitoring costs
        monthly_monitoring_per_site = Decimal('5000.00')
        total_monitoring = monthly_monitoring_per_site * num_sites * duration_months_decimal
        
        # Site closeout costs
        closeout_per_site = Decimal('20000.00')
        total_closeout = closeout_per_site * num_sites
        
        # Travel costs for site visits
        visits_per_site = max(1, int(duration_months / 3))  # Quarterly visits
        travel_per_visit = Decimal('2000.00')
        total_travel = travel_per_visit * num_sites * visits_per_site
        
        total_site_costs = total_initiation + total_monitoring + total_closeout + total_travel
        
        return {
            'num_sites': num_sites,
            'initiation_costs': float(total_initiation),
            'initiation_breakdown': initiation_costs,
            'monitoring_costs': float(total_monitoring),
            'closeout_costs': float(total_closeout),
            'travel_costs': float(total_travel),
            'total_site_costs': float(total_site_costs)
        }
    
    # ========================================================================
    # OPERATIONAL COSTS
    # ========================================================================
    
    def _calculate_operational_costs(self) -> Dict[str, Any]:
        """Calculate operational/staffing costs"""
        
        num_sites = len(self.sites) if self.sites else 10
        duration_months = self.simulation.get('expected_duration_months', 24)
        # Convert to Decimal to avoid type mixing errors
        duration_months_decimal = Decimal(str(duration_months))
        
        # CRA staffing
        sites_per_cra = 8
        num_cras = max(1, int(np.ceil(num_sites / sites_per_cra)))
        cra_monthly_cost = Decimal('15000.00')
        total_cra_costs = cra_monthly_cost * num_cras * duration_months_decimal
        
        # Data Management
        sites_per_dm = 15
        num_dms = max(1, int(np.ceil(num_sites / sites_per_dm)))
        dm_monthly_cost = Decimal('12000.00')
        total_dm_costs = dm_monthly_cost * num_dms * duration_months_decimal
        
        # Medical Monitoring
        medical_monitor_cost = Decimal('20000.00') * duration_months_decimal
        
        # Project Management
        pm_cost = Decimal('18000.00') * duration_months_decimal
        
        # Systems & Technology
        edc_setup = Decimal('50000.00')
        edc_monthly = Decimal('5000.00') * duration_months_decimal
        ivrs_cost = Decimal('30000.00')
        total_systems = edc_setup + edc_monthly + ivrs_cost
        
        total_operational = total_cra_costs + total_dm_costs + medical_monitor_cost + pm_cost + total_systems
        
        return {
            'cra_costs': {
                'num_cras': num_cras,
                'total': float(total_cra_costs)
            },
            'data_management': {
                'num_dms': num_dms,
                'total': float(total_dm_costs)
            },
            'medical_monitoring': float(medical_monitor_cost),
            'project_management': float(pm_cost),
            'systems_technology': float(total_systems),
            'total_operational_costs': float(total_operational)
        }
    
    # ========================================================================
    # OVERHEAD & CONTINGENCY
    # ========================================================================
    
    def _calculate_overhead(self, base_costs: Decimal) -> Dict[str, Any]:
        """Calculate overhead"""
        
        phase = self.study_context.get('phase', 'Phase II')
        overhead_rate = Decimal(str(self.phase_overhead_rates.get(phase, 0.30)))
        
        overhead_amount = base_costs * overhead_rate
        
        return {
            'rate': float(overhead_rate),
            'amount': float(overhead_amount),
            'base_costs': float(base_costs)
        }
    
    def _calculate_contingency(self) -> Dict[str, Any]:
        """Calculate risk contingency"""
        
        # Base contingency rate
        base_rate = Decimal('0.10')
        
        # Adjust based on risk factors
        risk_factors = self.simulation.get('risk_factors', [])
        high_risk_count = sum(1 for r in risk_factors if r.get('probability') == 'High')
        
        if high_risk_count >= 3:
            contingency_rate = Decimal('0.15')
        elif high_risk_count >= 1:
            contingency_rate = Decimal('0.12')
        else:
            contingency_rate = base_rate
        
        # Adjust based on timeline confidence
        prob_on_time = self.simulation.get('summary_statistics', {}).get('probability_on_time', 0.7)
        if prob_on_time < 0.5:
            contingency_rate += Decimal('0.05')
        
        reasoning = f"Based on {high_risk_count} high-risk factors and {prob_on_time:.1%} on-time probability"
        
        return {
            'rate': float(contingency_rate),
            'reasoning': reasoning
        }
    
    # ========================================================================
    # AGGREGATION & SCENARIOS
    # ========================================================================
    
    def _aggregate_budget(
        self,
        patient_costs: Dict,
        site_costs: Dict,
        operational_costs: Dict,
        overhead: Dict,
        contingency: Dict
    ) -> Dict[str, Any]:
        """Aggregate all cost components"""
        
        # Base costs (before overhead)
        base_total = (
            Decimal(str(patient_costs['total_patient_costs'])) +
            Decimal(str(site_costs['total_site_costs'])) +
            Decimal(str(operational_costs['total_operational_costs']))
        )
        
        # Add overhead
        subtotal_with_overhead = base_total + Decimal(str(overhead['amount']))
        
        # Add contingency
        contingency_amount = subtotal_with_overhead * Decimal(str(contingency['rate']))
        grand_total = subtotal_with_overhead + contingency_amount
        
        # Cost per patient (with overhead)
        total_patients = self.study_design.get('totalParticipants', 1)
        if total_patients == 0:
            total_patients = 300
        cpp_with_overhead = grand_total / total_patients
        
        return {
            'base_total': float(base_total),
            'overhead_amount': float(overhead['amount']),
            'subtotal_with_overhead': float(subtotal_with_overhead),
            'contingency_amount': float(contingency_amount),
            'grand_total': float(grand_total),
            'cost_per_patient_with_overhead': float(cpp_with_overhead),
            'component_totals': {
                'patient_costs': patient_costs['total_patient_costs'],
                'site_costs': site_costs['total_site_costs'],
                'operational_costs': operational_costs['total_operational_costs'],
                'overhead': overhead['amount'],
                'contingency': float(contingency_amount)
            },
            'detailed_cpp_breakdown': patient_costs.get('cpp_breakdown', {}),
            'prdl_details': {
                'per_patient': patient_costs.get('prdl_cpp', 0),
                'total': patient_costs.get('prdl_cpp', 0) * total_patients,
                'description': 'Patient travel, parking, meals, childcare, lost wages'
            },
            'drug_packaging_details': {
                'per_patient': patient_costs.get('drug_packaging_cpp', 0),
                'total': patient_costs.get('drug_packaging_cpp', 0) * total_patients,
                'description': 'Drug supply, packaging, storage, distribution, wastage'
            },
            'opal_details': {
                'per_patient': patient_costs.get('opal_cpp', 0),
                'total': patient_costs.get('opal_cpp', 0) * total_patients,
                'score': patient_costs.get('opal_cpp', 0),
                'description': 'Lab overhead: coordination, tracking, shipping, processing'
            },
            'additional_labs_details': {
                'per_patient': patient_costs.get('additional_labs_cpp', 0),
                'total': patient_costs.get('additional_labs_cpp', 0) * total_patients,
                'description': 'Central lab fees, shipping, special handling, batch testing'
            }
        }
    
    def _generate_risk_scenarios(self, base_budget: Dict) -> Dict[str, Any]:
        """Generate optimistic, expected, pessimistic scenarios"""
        
        grand_total = Decimal(str(base_budget['grand_total']))
        
        # Use simulation confidence intervals
        conf_interval = self.simulation.get('confidence_interval', {})
        p10_duration = conf_interval.get('completion_time_p10', 18)
        p90_duration = conf_interval.get('completion_time_p90', 32)
        
        expected_duration = self.simulation.get('expected_duration_months', 24)
        
        # Optimistic: Fast enrollment
        optimistic_mult = Decimal(str(p10_duration / expected_duration)) if expected_duration > 0 else Decimal('0.85')
        optimistic_total = grand_total * (Decimal('0.90') + optimistic_mult * Decimal('0.05'))
        
        # Expected: Base case
        expected_total = grand_total
        
        # Pessimistic: Delays
        pessimistic_mult = Decimal(str(p90_duration / expected_duration)) if expected_duration > 0 else Decimal('1.25')
        pessimistic_total = grand_total * (Decimal('1.05') + pessimistic_mult * Decimal('0.10'))
        
        return {
            'optimistic': {
                'total': float(optimistic_total),
                'duration_months': p10_duration,
                'description': 'Fast enrollment, minimal delays, efficient operations'
            },
            'expected': {
                'total': float(expected_total),
                'duration_months': expected_duration,
                'description': 'Base case from simulation'
            },
            'pessimistic': {
                'total': float(pessimistic_total),
                'duration_months': p90_duration,
                'description': 'Enrollment delays, site issues, additional monitoring'
            }
        }
    
    def _create_cashflow_projections(self, total_budget: Dict) -> List[Dict[str, Any]]:
        """Create monthly cashflow projections"""
        
        enrollment_curve = self.simulation.get('enrollment_curve', [])
        duration_months = int(self.simulation.get('expected_duration_months', 24))
        
        # Get component costs
        patient_costs = total_budget['component_totals']['patient_costs']
        site_costs = total_budget['component_totals']['site_costs']
        operational_costs = total_budget['component_totals']['operational_costs']
        
        monthly_cashflow = []
        cumulative_spend = 0
        
        for month in range(duration_months):
            # Patient costs (proportional to enrollment)
            if month < len(enrollment_curve) and enrollment_curve:
                month_enrollment = enrollment_curve[month].get('enrolled_mean', 0)
                total_enrollment = enrollment_curve[-1].get('cumulative_mean', 1) if enrollment_curve else 1
                patient_pct = month_enrollment / total_enrollment if total_enrollment > 0 else 0
            else:
                patient_pct = 1.0 / duration_months if duration_months > 0 else 0
            
            month_patient_cost = patient_costs * patient_pct
            
            # Site costs (amortized monthly)
            month_site_cost = site_costs / duration_months if duration_months > 0 else 0
            
            # Operational costs (monthly)
            month_operational_cost = operational_costs / duration_months if duration_months > 0 else 0
            
            # Total monthly spend
            month_total = month_patient_cost + month_site_cost + month_operational_cost
            cumulative_spend += month_total
            
            monthly_cashflow.append({
                'month': month + 1,
                'patient_costs': float(month_patient_cost),
                'site_costs': float(month_site_cost),
                'operational_costs': float(month_operational_cost),
                'total_monthly': float(month_total),
                'cumulative': float(cumulative_spend)
            })
        
        return monthly_cashflow
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _get_ta_multiplier(self) -> float:
        """Get therapeutic area complexity multiplier"""
        ta_multipliers = {
            'Oncology': 1.3,
            'Neurology': 1.2,
            'Cardiovascular': 1.1,
            'Infectious Disease': 1.15,
            'Metabolic': 1.0,
            'Dermatology': 0.9
        }
        ta = self.study_context.get('therapeuticArea', 'General')
        return ta_multipliers.get(ta, 1.0)
    
    def _get_country_multiplier(self, country: str) -> float:
        """Get country cost multiplier"""
        return self.country_multipliers.get(country, 1.0)
    
    def _load_procedure_costs(self) -> Dict:
        """Load procedure cost database"""
        return {}
    
    def _load_country_multipliers(self) -> Dict:
        """Load country cost multipliers"""
        return {
            'US': 1.0,
            'Canada': 1.05,
            'UK': 0.95,
            'Germany': 1.1,
            'France': 1.05,
            'Spain': 0.85,
            'Italy': 0.85,
            'China': 0.70,
            'Japan': 1.2,
            'Australia': 1.1,
            'Brazil': 0.65,
            'Argentina': 0.60,
            'Mexico': 0.55,
            'India': 0.50
        }
    
    def _get_cost_by_category(self) -> Dict[str, float]:
        """Aggregate costs by category"""
        category_costs = {}
        
        for activity in self.soa_data.get('activities', []):
            category = activity['category']
            cost = 0.0
            
            # Count how many visits include this activity
            visit_count = sum(1 for v in activity['visits'].values() if v)
            
            if visit_count > 0:
                proc_cost = float(self._get_procedure_cost(category, activity['name']))
                cost = proc_cost * visit_count
            
            if category in category_costs:
                category_costs[category] += cost
            else:
                category_costs[category] = cost
        
        return category_costs
    
    def _calculate_summary_metrics(self, total_budget: Dict) -> Dict[str, Any]:
        """Calculate key summary metrics"""
        
        total_patients = self.study_design.get('totalParticipants', 300)
        num_sites = len(self.sites) if self.sites else 10
        duration_months = self.simulation.get('expected_duration_months', 24)
        
        return {
            'grand_total': total_budget['grand_total'],
            'cost_per_patient': total_budget['cost_per_patient_with_overhead'],
            'cost_per_site': total_budget['grand_total'] / num_sites if num_sites > 0 else 0,
            'monthly_burn_rate': total_budget['grand_total'] / duration_months if duration_months > 0 else 0,
            'total_patients': total_patients,
            'num_sites': num_sites,
            'duration_months': duration_months,
            'efficiency_score': self._calculate_efficiency_score(total_budget),
            'risk_level': self._assess_risk_level()
        }
    
    def _calculate_efficiency_score(self, total_budget: Dict) -> float:
        """Calculate budget efficiency score (0-100)"""
        
        # Compare to reference trials if available
        if self.reference_trials:
            ref_cpps = [
                t.get('cost_per_patient', 0) 
                for t in self.reference_trials 
                if t.get('cost_per_patient', 0) > 0
            ]
            
            if ref_cpps:
                avg_cpp_reference = np.mean(ref_cpps)
            else:
                avg_cpp_reference = 50000
        else:
            avg_cpp_reference = 50000
        
        actual_cpp = total_budget['cost_per_patient_with_overhead']
        
        # Lower is better
        if actual_cpp > 0:
            efficiency = (avg_cpp_reference / actual_cpp) * 100
        else:
            efficiency = 50
        
        # Cap at 100
        return min(100.0, max(0.0, efficiency))
    
    def _assess_risk_level(self) -> str:
        """Assess overall budget risk level"""
        
        prob_on_time = self.simulation.get('summary_statistics', {}).get('probability_on_time', 0.7)
        
        if prob_on_time >= 0.7:
            return 'Low'
        elif prob_on_time >= 0.5:
            return 'Medium'
        else:
            return 'High'

