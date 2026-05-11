"""
Fair Market Value (FMV) Analysis Engine
Compares budgeted prices against market benchmarks
"""

from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class FMVAnalysisEngine:
    """
    Fair Market Value Analysis Engine
    Validates budgeted prices against industry benchmarks
    """
    
    def __init__(self):
        # Load benchmark data (in production, this would come from a database)
        self.benchmarks = self._load_benchmark_data()
    
    def _load_benchmark_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Load procedure cost benchmarks
        In production: SELECT * FROM procedure_benchmarks
        """
        return {
            # Clinical procedures
            'ECG': {'median': 115.0, 'q1': 95.0, 'q3': 135.0, 'category': 'Cardiac'},
            'Echocardiogram': {'median': 850.0, 'q1': 700.0, 'q3': 1000.0, 'category': 'Cardiac'},
            'Holter Monitor': {'median': 425.0, 'q1': 350.0, 'q3': 500.0, 'category': 'Cardiac'},
            
            # Laboratory
            'Complete Blood Count': {'median': 45.0, 'q1': 35.0, 'q3': 55.0, 'category': 'Laboratory'},
            'Comprehensive Metabolic Panel': {'median': 85.0, 'q1': 70.0, 'q3': 100.0, 'category': 'Laboratory'},
            'Lipid Panel': {'median': 65.0, 'q1': 50.0, 'q3': 80.0, 'category': 'Laboratory'},
            'HbA1c': {'median': 50.0, 'q1': 40.0, 'q3': 60.0, 'category': 'Laboratory'},
            'Urinalysis': {'median': 25.0, 'q1': 20.0, 'q3': 30.0, 'category': 'Laboratory'},
            'Blood Draw': {'median': 25.0, 'q1': 20.0, 'q3': 30.0, 'category': 'Laboratory'},
            
            # Imaging
            'X-Ray Chest': {'median': 250.0, 'q1': 200.0, 'q3': 300.0, 'category': 'Imaging'},
            'CT Scan': {'median': 1500.0, 'q1': 1200.0, 'q3': 1800.0, 'category': 'Imaging'},
            'MRI Brain': {'median': 1800.0, 'q1': 1500.0, 'q3': 2100.0, 'category': 'Imaging'},
            'MRI Spine': {'median': 2000.0, 'q1': 1700.0, 'q3': 2300.0, 'category': 'Imaging'},
            'Ultrasound': {'median': 350.0, 'q1': 280.0, 'q3': 420.0, 'category': 'Imaging'},
            'PET Scan': {'median': 3500.0, 'q1': 3000.0, 'q3': 4000.0, 'category': 'Imaging'},
            
            # Procedures
            'Bone Marrow Biopsy': {'median': 1200.0, 'q1': 1000.0, 'q3': 1400.0, 'category': 'Procedures'},
            'Endoscopy': {'median': 2500.0, 'q1': 2000.0, 'q3': 3000.0, 'category': 'Procedures'},
            'Colonoscopy': {'median': 2800.0, 'q1': 2300.0, 'q3': 3300.0, 'category': 'Procedures'},
            'Bronchoscopy': {'median': 3200.0, 'q1': 2700.0, 'q3': 3700.0, 'category': 'Procedures'},
            
            # Specialty
            'Pulmonary Function Test': {'median': 350.0, 'q1': 280.0, 'q3': 420.0, 'category': 'Pulmonary'},
            'Sleep Study': {'median': 1500.0, 'q1': 1200.0, 'q3': 1800.0, 'category': 'Pulmonary'},
            'Stress Test': {'median': 650.0, 'q1': 550.0, 'q3': 750.0, 'category': 'Cardiac'},
            'Skin Biopsy': {'median': 450.0, 'q1': 350.0, 'q3': 550.0, 'category': 'Dermatology'},
            
            # Visit types
            'Screening Visit': {'median': 1500.0, 'q1': 1200.0, 'q3': 1800.0, 'category': 'Visit'},
            'Baseline Visit': {'median': 2000.0, 'q1': 1600.0, 'q3': 2400.0, 'category': 'Visit'},
            'Follow-up Visit': {'median': 800.0, 'q1': 600.0, 'q3': 1000.0, 'category': 'Visit'},
            'End of Study Visit': {'median': 1800.0, 'q1': 1500.0, 'q3': 2100.0, 'category': 'Visit'},
            'Unscheduled Visit': {'median': 1200.0, 'q1': 900.0, 'q3': 1500.0, 'category': 'Visit'},
        }
    
    def analyze_procedure_costs(
        self,
        budgeted_costs: List[Dict[str, Any]],
        tolerance: float = 0.25
    ) -> Dict[str, Any]:
        """
        Analyze budgeted costs against FMV benchmarks
        
        Args:
            budgeted_costs: List of {procedure_name, budgeted_amount, quantity}
            tolerance: Acceptable variance from median (default 25%)
        
        Returns:
            Analysis results with risk classifications
        """
        logger.info(f"🔍 Starting FMV analysis with {tolerance*100:.0f}% tolerance...")
        
        results = []
        summary = {
            'total_procedures': 0,
            'within_range': 0,
            'above_range': 0,
            'below_range': 0,
            'no_benchmark': 0,
            'total_budgeted': 0.0,
            'total_benchmark': 0.0,
            'total_variance': 0.0
        }
        
        for item in budgeted_costs:
            procedure_name = item.get('procedure_name', item.get('name', 'Unknown'))
            budgeted_amount = float(item.get('budgeted_amount', item.get('cost', 0)))
            quantity = item.get('quantity', 1)
            
            summary['total_procedures'] += 1
            summary['total_budgeted'] += budgeted_amount * quantity
            
            # Find benchmark
            benchmark = self.benchmarks.get(procedure_name)
            
            if not benchmark:
                # Try fuzzy matching
                benchmark = self._fuzzy_match_benchmark(procedure_name)
            
            if not benchmark:
                summary['no_benchmark'] += 1
                results.append({
                    'procedure_name': procedure_name,
                    'budgeted_amount': budgeted_amount,
                    'benchmark_median': None,
                    'benchmark_q1': None,
                    'benchmark_q3': None,
                    'difference_amount': None,
                    'difference_percentage': None,
                    'status': 'no_benchmark',
                    'risk_level': None,
                    'category': 'Unknown',
                    'quantity': quantity,
                    'total_budgeted': budgeted_amount * quantity,
                    'total_benchmark': None
                })
                continue
            
            # Calculate variance
            median = benchmark['median']
            q1 = benchmark['q1']
            q3 = benchmark['q3']
            
            difference_amount = budgeted_amount - median
            difference_percentage = (difference_amount / median) * 100 if median > 0 else 0
            
            # Determine status based on tolerance
            lower_bound = median * (1 - tolerance)
            upper_bound = median * (1 + tolerance)
            
            if lower_bound <= budgeted_amount <= upper_bound:
                status = 'within_range'
                summary['within_range'] += 1
                risk_level = 'low'
            elif budgeted_amount > upper_bound:
                status = 'above_range'
                summary['above_range'] += 1
                # Determine risk level based on how far above
                if budgeted_amount > median * (1 + tolerance * 2):
                    risk_level = 'high'
                else:
                    risk_level = 'medium'
            else:
                status = 'below_range'
                summary['below_range'] += 1
                # Below range might indicate quality concerns
                if budgeted_amount < median * (1 - tolerance * 1.5):
                    risk_level = 'high'
                else:
                    risk_level = 'medium'
            
            total_benchmark = median * quantity
            summary['total_benchmark'] += total_benchmark
            summary['total_variance'] += difference_amount * quantity
            
            results.append({
                'procedure_name': procedure_name,
                'budgeted_amount': budgeted_amount,
                'benchmark_median': median,
                'benchmark_q1': q1,
                'benchmark_q3': q3,
                'difference_amount': difference_amount,
                'difference_percentage': difference_percentage,
                'status': status,
                'risk_level': risk_level,
                'category': benchmark['category'],
                'quantity': quantity,
                'total_budgeted': budgeted_amount * quantity,
                'total_benchmark': total_benchmark,
                'total_difference': difference_amount * quantity
            })
        
        # Calculate summary percentages
        if summary['total_procedures'] > 0:
            summary['within_range_pct'] = (summary['within_range'] / summary['total_procedures']) * 100
            summary['above_range_pct'] = (summary['above_range'] / summary['total_procedures']) * 100
            summary['below_range_pct'] = (summary['below_range'] / summary['total_procedures']) * 100
            summary['no_benchmark_pct'] = (summary['no_benchmark'] / summary['total_procedures']) * 100
        
        if summary['total_benchmark'] > 0:
            summary['total_variance_pct'] = (summary['total_variance'] / summary['total_benchmark']) * 100
        else:
            summary['total_variance_pct'] = 0.0
        
        logger.info(f"✅ FMV analysis complete: {summary['within_range']}/{summary['total_procedures']} within range")
        
        return {
            'summary': summary,
            'items': results,
            'tolerance': tolerance,
            'analysis_date': 'current',
            'benchmark_source': 'Internal Database 2025 Q2'
        }
    
    def _fuzzy_match_benchmark(self, procedure_name: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to fuzzy match procedure name to benchmark
        """
        procedure_lower = procedure_name.lower()
        
        # Simple keyword matching
        for bench_name, bench_data in self.benchmarks.items():
            if bench_name.lower() in procedure_lower or procedure_lower in bench_name.lower():
                return bench_data
        
        # Check for common abbreviations
        abbreviations = {
            'ekg': 'ECG',
            'cbc': 'Complete Blood Count',
            'cmp': 'Comprehensive Metabolic Panel',
            'ua': 'Urinalysis',
            'cxr': 'X-Ray Chest'
        }
        
        for abbrev, full_name in abbreviations.items():
            if abbrev in procedure_lower:
                return self.benchmarks.get(full_name)
        
        return None
    
    def get_high_risk_procedures(
        self,
        analysis_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract high-risk procedures from analysis
        """
        items = analysis_results.get('items', [])
        return [
            item for item in items
            if item.get('risk_level') == 'high'
        ]
    
    def get_recommendations(
        self,
        analysis_results: Dict[str, Any]
    ) -> List[str]:
        """
        Generate recommendations based on FMV analysis
        """
        recommendations = []
        summary = analysis_results.get('summary', {})
        
        # Check overall compliance
        within_range_pct = summary.get('within_range_pct', 0)
        if within_range_pct < 70:
            recommendations.append(
                f"⚠️ Only {within_range_pct:.0f}% of procedures are within market range. "
                "Review pricing strategy with procurement team."
            )
        elif within_range_pct >= 90:
            recommendations.append(
                f"✅ Excellent FMV compliance: {within_range_pct:.0f}% of procedures within market range."
            )
        
        # Check for above-range items
        above_pct = summary.get('above_range_pct', 0)
        if above_pct > 20:
            recommendations.append(
                f"💰 {above_pct:.0f}% of procedures are priced above market. "
                "Potential cost savings through vendor negotiation."
            )
        
        # Check for below-range items
        below_pct = summary.get('below_range_pct', 0)
        if below_pct > 15:
            recommendations.append(
                f"🔍 {below_pct:.0f}% of procedures are priced below market. "
                "Verify vendor quality and service level agreements."
            )
        
        # Check for missing benchmarks
        no_benchmark_pct = summary.get('no_benchmark_pct', 0)
        if no_benchmark_pct > 10:
            recommendations.append(
                f"📊 {no_benchmark_pct:.0f}% of procedures lack benchmarks. "
                "Consider expanding benchmark database for better coverage."
            )
        
        # High risk items
        high_risk = self.get_high_risk_procedures(analysis_results)
        if len(high_risk) > 0:
            recommendations.append(
                f"⚠️ {len(high_risk)} high-risk procedures identified. "
                "Prioritize review and potential renegotiation."
            )
        
        return recommendations

