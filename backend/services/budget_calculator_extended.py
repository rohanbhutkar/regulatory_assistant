"""
Extended Budget Calculator - B&C Missing Features
Adds: Additional costs, Country breakdown, Drug supply chain, FMV analysis
"""

from typing import Dict, List, Any, Tuple
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class BudgetCalculatorExtensions:
    """
    Extension methods for EnhancedBudgetCalculator
    Implements all missing B&C features
    """
    
    @staticmethod
    def calculate_additional_crf_payments(
        total_patients: int,
        phase: str,
        therapeutic_area: str
    ) -> Dict[str, Any]:
        """
        Calculate additional CRF-based payments
        These are per-CRF or per-event payments beyond the base CPP
        """
        
        items = []
        
        # Early termination payments
        early_term_rate = 0.10  # 10% of patients
        early_term_patients = int(total_patients * early_term_rate)
        early_term_payment = 500.00  # $500 per early termination
        items.append({
            'category': 'Early Termination',
            'description': f'{early_term_patients} patients × ${early_term_payment}',
            'per_patient': early_term_payment,
            'quantity': early_term_patients,
            'amount': early_term_patients * early_term_payment
        })
        
        # Protocol deviation payments
        deviation_rate = 0.15  # 15% of patients
        deviation_patients = int(total_patients * deviation_rate)
        deviation_payment = 300.00  # $300 per deviation
        items.append({
            'category': 'Protocol Deviations',
            'description': f'{deviation_patients} deviations × ${deviation_payment}',
            'per_patient': deviation_payment,
            'quantity': deviation_patients,
            'amount': deviation_patients * deviation_payment
        })
        
        # SAE reporting fees (phase-dependent)
        sae_rates = {
            'Phase I': 0.25,
            'Phase II': 0.20,
            'Phase III': 0.15,
            'Phase IV': 0.10
        }
        sae_rate = sae_rates.get(phase, 0.15)
        sae_patients = int(total_patients * sae_rate)
        sae_payment = 750.00  # $750 per SAE report
        items.append({
            'category': 'SAE Reporting',
            'description': f'{sae_patients} SAE reports × ${sae_payment}',
            'per_patient': sae_payment,
            'quantity': sae_patients,
            'amount': sae_patients * sae_payment
        })
        
        # Additional assessments (unscheduled visits)
        additional_visits_rate = 0.20
        additional_visits = int(total_patients * additional_visits_rate)
        additional_visit_cost = 1200.00  # $1,200 per unscheduled visit
        items.append({
            'category': 'Additional Assessments',
            'description': f'{additional_visits} unscheduled visits × ${additional_visit_cost}',
            'per_patient': additional_visit_cost,
            'quantity': additional_visits,
            'amount': additional_visits * additional_visit_cost
        })
        
        total = sum(item['amount'] for item in items)
        
        return {
            'total': total,
            'items': items,
            'description': 'Additional CRF-based payments for protocol deviations, SAEs, and unscheduled events'
        }
    
    @staticmethod
    def calculate_invoice_items(
        total_patients: int,
        phase: str,
        duration_months: int
    ) -> Dict[str, Any]:
        """
        Calculate items paid by invoice (vendor services)
        """
        
        items = []
        
        # Central laboratory services
        lab_cost_per_patient = 1500.00
        items.append({
            'category': 'Central Laboratory',
            'description': f'{total_patients} patients × ${lab_cost_per_patient}',
            'amount': total_patients * lab_cost_per_patient
        })
        
        # ECG reading services
        ecg_cost_per_patient = 250.00
        items.append({
            'category': 'ECG Reading Services',
            'description': f'{total_patients} patients × ${ecg_cost_per_patient}',
            'amount': total_patients * ecg_cost_per_patient
        })
        
        # Imaging core lab (if applicable for phase)
        if phase in ['Phase II', 'Phase III']:
            imaging_cost_per_patient = 3500.00
            items.append({
                'category': 'Imaging Core Lab',
                'description': f'{total_patients} patients × ${imaging_cost_per_patient}',
                'amount': total_patients * imaging_cost_per_patient
            })
        
        # IWRS/IVRS system
        iwrs_monthly_cost = 5000.00
        items.append({
            'category': 'IWRS/IVRS System',
            'description': f'{duration_months} months × ${iwrs_monthly_cost}/month',
            'amount': duration_months * iwrs_monthly_cost
        })
        
        # EDC system
        edc_monthly_cost = 8000.00
        items.append({
            'category': 'EDC System',
            'description': f'{duration_months} months × ${edc_monthly_cost}/month',
            'amount': duration_months * edc_monthly_cost
        })
        
        # Pathology services (if oncology or similar)
        pathology_cost_per_patient = 800.00
        pathology_rate = 0.70  # 70% of patients
        pathology_patients = int(total_patients * pathology_rate)
        items.append({
            'category': 'Pathology Services',
            'description': f'{pathology_patients} patients × ${pathology_cost_per_patient}',
            'amount': pathology_patients * pathology_cost_per_patient
        })
        
        total = sum(item['amount'] for item in items)
        
        return {
            'total': total,
            'items': items,
            'description': 'Vendor services and systems paid by invoice'
        }
    
    @staticmethod
    def calculate_study_level_fees(
        num_sites: int,
        num_countries: int,
        phase: str,
        duration_months: int
    ) -> Dict[str, Any]:
        """
        Calculate study-level fees (one-time and recurring)
        """
        
        items = []
        
        # IRB/Ethics committee fees
        irb_cost_per_site = 5000.00
        items.append({
            'category': 'IRB/Ethics Committee Fees',
            'description': f'{num_sites} sites × ${irb_cost_per_site}',
            'amount': num_sites * irb_cost_per_site
        })
        
        # Regulatory submission fees
        reg_cost_per_country = 25000.00
        items.append({
            'category': 'Regulatory Submissions',
            'description': f'{num_countries} countries × ${reg_cost_per_country}',
            'amount': num_countries * reg_cost_per_country
        })
        
        # Data Safety Monitoring Board (DSMB)
        if phase in ['Phase II', 'Phase III']:
            dsmb_meetings = duration_months // 6  # Meeting every 6 months
            dsmb_cost_per_meeting = 50000.00
            items.append({
                'category': 'DSMB Costs',
                'description': f'{dsmb_meetings} meetings × ${dsmb_cost_per_meeting}',
                'amount': dsmb_meetings * dsmb_cost_per_meeting
            })
        
        # Clinical Endpoint Committee (CEC)
        if phase == 'Phase III':
            cec_cost = 150000.00
            items.append({
                'category': 'Clinical Endpoint Committee',
                'description': 'CEC charter, meetings, and adjudication',
                'amount': cec_cost
            })
        
        # Document archiving
        archiving_cost = 35000.00
        items.append({
            'category': 'Document Archiving',
            'description': 'Long-term document storage and retrieval',
            'amount': archiving_cost
        })
        
        # Insurance
        insurance_cost = 75000.00
        items.append({
            'category': 'Clinical Trial Insurance',
            'description': 'Study-level liability insurance',
            'amount': insurance_cost
        })
        
        total = sum(item['amount'] for item in items)
        
        return {
            'total': total,
            'items': items,
            'description': 'Study-level fees and one-time costs'
        }
    
    @staticmethod
    def calculate_drug_supply_chain(
        total_patients: int,
        duration_months: int,
        num_arms: int,
        phase: str
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive drug supply chain costs
        """
        
        # Base drug manufacturing cost per patient
        base_drug_cost = 15000.00 if phase == 'Phase III' else 10000.00
        manufacturing_total = total_patients * base_drug_cost * num_arms
        
        # Packaging (10% of manufacturing)
        packaging_total = manufacturing_total * 0.10
        
        # Labeling (5% of manufacturing)
        labeling_total = manufacturing_total * 0.05
        
        # Storage (monthly cost)
        storage_monthly = 3000.00
        storage_total = storage_monthly * duration_months
        
        # Distribution (8% of manufacturing)
        distribution_total = manufacturing_total * 0.08
        
        # Wastage (15% of total drug costs)
        subtotal = manufacturing_total + packaging_total + labeling_total + storage_total + distribution_total
        wastage_total = subtotal * 0.15
        
        # Comparator drug (if applicable)
        comparator_cost_per_patient = 8000.00
        comparator_rate = 0.50  # 50% of patients on comparator
        comparator_patients = int(total_patients * comparator_rate)
        comparator_total = comparator_patients * comparator_cost_per_patient
        
        breakdown = {
            'manufacturing': manufacturing_total,
            'packaging': packaging_total,
            'labeling': labeling_total,
            'storage': storage_total,
            'distribution': distribution_total,
            'wastage': wastage_total,
            'comparator_drug': comparator_total
        }
        
        total = sum(breakdown.values())
        
        return {
            'total': total,
            'breakdown': breakdown,
            'per_patient': total / total_patients if total_patients > 0 else 0,
            'description': 'Complete drug supply chain from manufacturing to patient'
        }
    
    @staticmethod
    def calculate_screening_and_dropout_detailed(
        enrolled_patients: int,
        screen_failure_rate: float,
        dropout_rate: float,
        base_cpp: float,
        screening_cpp_multiplier: float = 0.30
    ) -> Dict[str, Any]:
        """
        Calculate detailed screening and dropout costs
        """
        
        # Screen failures
        total_screened = int(enrolled_patients / (1 - screen_failure_rate))
        num_screen_failures = total_screened - enrolled_patients
        cost_per_screen_failure = base_cpp * screening_cpp_multiplier
        screening_costs = num_screen_failures * cost_per_screen_failure
        
        # Dropouts and replacements
        num_dropouts = int(enrolled_patients * dropout_rate)
        cost_per_dropout = base_cpp * 0.60  # Partial cost for dropouts
        dropout_costs = num_dropouts * cost_per_dropout
        
        # Replacement costs
        num_replacements = num_dropouts  # Assume 1:1 replacement
        replacement_costs = num_replacements * base_cpp
        
        return {
            'screening': {
                'total_screened': total_screened,
                'screen_failures': num_screen_failures,
                'screen_failure_rate': screen_failure_rate,
                'cost_per_screen_failure': cost_per_screen_failure,
                'total_screening_costs': screening_costs
            },
            'dropout': {
                'num_dropouts': num_dropouts,
                'dropout_rate': dropout_rate,
                'cost_per_dropout': cost_per_dropout,
                'dropout_costs': dropout_costs,
                'num_replacements': num_replacements,
                'replacement_costs': replacement_costs,
                'total_dropout_costs': dropout_costs + replacement_costs
            },
            'total_attrition_costs': screening_costs + dropout_costs + replacement_costs
        }
    
    @staticmethod
    def calculate_country_breakdown(
        total_patients: int,
        num_sites: int,
        base_total_usd: float,
        country_allocations: List[Dict[str, Any]] = None
    ) -> Tuple[List[Dict[str, Any]], float]:
        """
        Calculate country-specific breakdown with exchange rates
        """
        
        if not country_allocations:
            # Default: 100% USA
            country_allocations = [
                {'country_code': 'USA', 'country_name': 'United States', 'patient_percentage': 1.0}
            ]
        
        # Exchange rates and multipliers (as of 2025)
        country_data = {
            'USA': {'currency': 'USD', 'exchange_rate': 1.0, 'cost_multiplier': 1.0},
            'GBR': {'currency': 'GBP', 'exchange_rate': 0.79, 'cost_multiplier': 1.15},
            'DEU': {'currency': 'EUR', 'exchange_rate': 0.92, 'cost_multiplier': 1.10},
            'FRA': {'currency': 'EUR', 'exchange_rate': 0.92, 'cost_multiplier': 1.12},
            'CAN': {'currency': 'CAD', 'exchange_rate': 1.36, 'cost_multiplier': 0.95},
            'JPN': {'currency': 'JPY', 'exchange_rate': 149.5, 'cost_multiplier': 1.25},
            'CHN': {'currency': 'CNY', 'exchange_rate': 7.24, 'cost_multiplier': 0.65},
            'IND': {'currency': 'INR', 'exchange_rate': 83.2, 'cost_multiplier': 0.45},
            'AUS': {'currency': 'AUD', 'exchange_rate': 1.53, 'cost_multiplier': 1.05},
            'BRA': {'currency': 'BRL', 'exchange_rate': 4.97, 'cost_multiplier': 0.70},
        }
        
        country_budgets = []
        weighted_cost_multiplier = 0
        
        for allocation in country_allocations:
            country_code = allocation.get('country_code', 'USA')
            patient_pct = allocation.get('patient_percentage', 1.0)
            
            country_info = country_data.get(country_code, country_data['USA'])
            
            num_country_patients = int(total_patients * patient_pct)
            num_country_sites = int(num_sites * patient_pct)
            
            # Apply country cost multiplier
            cost_multiplier = country_info['cost_multiplier']
            country_total_usd = base_total_usd * patient_pct * cost_multiplier
            
            # Convert to local currency
            exchange_rate = country_info['exchange_rate']
            country_total_local = country_total_usd * exchange_rate
            
            country_budgets.append({
                'country_code': country_code,
                'country_name': allocation.get('country_name', country_code),
                'currency': country_info['currency'],
                'exchange_rate': exchange_rate,
                'cost_multiplier': cost_multiplier,
                'num_patients': num_country_patients,
                'num_sites': num_country_sites,
                'total_local': country_total_local,
                'total_usd': country_total_usd
            })
            
            weighted_cost_multiplier += cost_multiplier * patient_pct
        
        # Calculate globalized total with exchange rate buffer
        exchange_rate_buffer = 0.12  # 12% buffer for FX risk
        globalized_total_usd = base_total_usd * weighted_cost_multiplier * (1 + exchange_rate_buffer)
        
        return country_budgets, globalized_total_usd
    
    @staticmethod
    def calculate_enhanced_overhead_breakdown(
        base_costs: float,
        overhead_rate: float
    ) -> Dict[str, Any]:
        """
        Calculate detailed overhead breakdown by type and category
        """
        
        total_overhead = base_costs * overhead_rate
        
        # Breakdown by type
        by_type = {
            'direct_overhead': total_overhead * 0.40,
            'indirect_overhead': total_overhead * 0.30,
            'administrative': total_overhead * 0.20,
            'management_fee': total_overhead * 0.10
        }
        
        # Breakdown by category
        by_category = {
            'personnel': total_overhead * 0.50,  # CRA, DM, PM salaries
            'systems_and_it': total_overhead * 0.20,  # Software, infrastructure
            'quality_and_compliance': total_overhead * 0.15,  # QA, audits
            'facilities': total_overhead * 0.10,  # Office space, utilities
            'corporate_allocation': total_overhead * 0.05  # Corporate overhead
        }
        
        return {
            'total': total_overhead,
            'rate': overhead_rate,
            'by_type': by_type,
            'by_category': by_category
        }







