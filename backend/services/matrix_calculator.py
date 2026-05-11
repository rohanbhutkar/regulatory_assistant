"""
Matrix Calculator
Calculates costs using matrix multiplication: (Procedures × Visits) × FMV Rates
"""

import logging
from typing import List, Dict, Optional
from decimal import Decimal
import numpy as np

from models.cpp_models import CostMatrix, VisitProcedure
from services.spu_pricing_service import get_spu_pricing_service

logger = logging.getLogger(__name__)


class MatrixCalculator:
    """
    Calculates budget costs using matrix operations
    
    Process:
    1. Build frequency matrix (Procedures × Visits)
    2. Get FMV cost vector for each procedure
    3. Multiply element-wise: Cost_Matrix = Frequency_Matrix × Cost_Vector
    4. Apply multipliers (cycles, optional visits, etc.)
    5. Aggregate totals
    """
    
    def __init__(self):
        self.pricing_service = get_spu_pricing_service()
    
    def calculate_cost_matrix(
        self,
        visit_procedures: List[VisitProcedure],
        country_code: str = 'USA',
        cycles: Optional[Dict[str, int]] = None,
        visit_probabilities: Optional[Dict[str, float]] = None
    ) -> CostMatrix:
        """
        Calculate cost matrix from visit procedures
        
        Args:
            visit_procedures: List of procedures by visit
            country_code: Country for pricing
            cycles: Optional dict of visit_name -> number of cycles
            visit_probabilities: Optional dict of visit_name -> probability (0-1)
            
        Returns:
            CostMatrix with all calculations
        """
        if not visit_procedures:
            return self._empty_matrix()
        
        # Build unique lists
        unique_procedures = self._get_unique_procedures(visit_procedures)
        unique_visits = self._get_unique_visits(visit_procedures)
        
        # Build frequency matrix
        frequency_matrix = self._build_frequency_matrix(
            visit_procedures,
            unique_procedures,
            unique_visits
        )
        
        # Get cost vector
        cost_vector = self._get_cost_vector(unique_procedures, country_code)
        
        # Calculate cost matrix
        cost_matrix = self._multiply_matrix_by_vector(
            frequency_matrix,
            cost_vector
        )
        
        # Apply cycles
        if cycles:
            cost_matrix = self._apply_cycles(cost_matrix, unique_visits, cycles)
        
        # Apply visit probabilities
        if visit_probabilities:
            cost_matrix = self._apply_probabilities(
                cost_matrix,
                unique_visits,
                visit_probabilities
            )
        
        # Calculate totals
        per_visit_totals = self._sum_by_visit(cost_matrix)
        per_procedure_totals = self._sum_by_procedure(cost_matrix)
        grand_total = sum(per_procedure_totals)
        
        return CostMatrix(
            procedures=unique_procedures,
            visits=unique_visits,
            frequency_matrix=frequency_matrix,
            cost_vector=cost_vector,
            cost_matrix=cost_matrix,
            per_visit_totals=per_visit_totals,
            per_procedure_totals=per_procedure_totals,
            grand_total=grand_total
        )
    
    def _get_unique_procedures(self, visit_procedures: List[VisitProcedure]) -> List[str]:
        """Get unique procedure codes in order"""
        seen = set()
        unique = []
        for vp in visit_procedures:
            if vp.procedure_code not in seen:
                unique.append(vp.procedure_code)
                seen.add(vp.procedure_code)
        return unique
    
    def _get_unique_visits(self, visit_procedures: List[VisitProcedure]) -> List[str]:
        """Get unique visit names in order"""
        seen = set()
        unique = []
        for vp in visit_procedures:
            if vp.visit_name not in seen:
                unique.append(vp.visit_name)
                seen.add(vp.visit_name)
        return unique
    
    def _build_frequency_matrix(
        self,
        visit_procedures: List[VisitProcedure],
        procedures: List[str],
        visits: List[str]
    ) -> List[List[float]]:
        """
        Build frequency matrix (Procedures × Visits)
        
        Returns list of lists: matrix[proc_idx][visit_idx] = frequency
        """
        # Initialize matrix with zeros
        matrix = [[0.0 for _ in visits] for _ in procedures]
        
        # Fill in frequencies
        proc_idx_map = {proc: i for i, proc in enumerate(procedures)}
        visit_idx_map = {visit: i for i, visit in enumerate(visits)}
        
        for vp in visit_procedures:
            proc_idx = proc_idx_map[vp.procedure_code]
            visit_idx = visit_idx_map[vp.visit_name]
            
            # Multiply frequency by probability if optional
            freq = vp.frequency
            if vp.is_optional:
                freq *= vp.probability
            
            matrix[proc_idx][visit_idx] = freq
        
        return matrix
    
    def _get_cost_vector(
        self,
        procedures: List[str],
        country_code: str
    ) -> List[Decimal]:
        """Get cost for each procedure"""
        cost_vector = []
        
        for proc_code in procedures:
            price_obj = self.pricing_service.get_procedure_price(proc_code, country_code)
            
            if price_obj:
                cost_vector.append(price_obj.local_price)
            else:
                # Default to 0 if no price found
                logger.warning(f"No price for {proc_code}, using $0")
                cost_vector.append(Decimal('0.00'))
        
        return cost_vector
    
    def _multiply_matrix_by_vector(
        self,
        frequency_matrix: List[List[float]],
        cost_vector: List[Decimal]
    ) -> List[List[Decimal]]:
        """
        Multiply frequency matrix by cost vector element-wise
        
        cost_matrix[i][j] = frequency_matrix[i][j] * cost_vector[i]
        """
        cost_matrix = []
        
        for i, row in enumerate(frequency_matrix):
            cost_row = []
            for j, freq in enumerate(row):
                cost = Decimal(str(freq)) * cost_vector[i]
                cost_row.append(cost)
            cost_matrix.append(cost_row)
        
        return cost_matrix
    
    def _apply_cycles(
        self,
        cost_matrix: List[List[Decimal]],
        visits: List[str],
        cycles: Dict[str, int]
    ) -> List[List[Decimal]]:
        """Apply cycle multipliers to specific visits"""
        visit_idx_map = {visit: i for i, visit in enumerate(visits)}
        
        for visit_name, num_cycles in cycles.items():
            if visit_name in visit_idx_map:
                visit_idx = visit_idx_map[visit_name]
                # Multiply all procedures in this visit by num_cycles
                for proc_idx in range(len(cost_matrix)):
                    cost_matrix[proc_idx][visit_idx] *= num_cycles
        
        return cost_matrix
    
    def _apply_probabilities(
        self,
        cost_matrix: List[List[Decimal]],
        visits: List[str],
        visit_probabilities: Dict[str, float]
    ) -> List[List[Decimal]]:
        """Apply probability multipliers to visits"""
        visit_idx_map = {visit: i for i, visit in enumerate(visits)}
        
        for visit_name, probability in visit_probabilities.items():
            if visit_name in visit_idx_map:
                visit_idx = visit_idx_map[visit_name]
                # Multiply all procedures in this visit by probability
                for proc_idx in range(len(cost_matrix)):
                    cost_matrix[proc_idx][visit_idx] *= Decimal(str(probability))
        
        return cost_matrix
    
    def _sum_by_visit(self, cost_matrix: List[List[Decimal]]) -> List[Decimal]:
        """Sum costs by visit (column sums)"""
        if not cost_matrix or not cost_matrix[0]:
            return []
        
        num_visits = len(cost_matrix[0])
        totals = [Decimal('0.00') for _ in range(num_visits)]
        
        for proc_row in cost_matrix:
            for visit_idx, cost in enumerate(proc_row):
                totals[visit_idx] += cost
        
        return totals
    
    def _sum_by_procedure(self, cost_matrix: List[List[Decimal]]) -> List[Decimal]:
        """Sum costs by procedure (row sums)"""
        return [sum(row) for row in cost_matrix]
    
    def _empty_matrix(self) -> CostMatrix:
        """Return empty cost matrix"""
        return CostMatrix(
            procedures=[],
            visits=[],
            frequency_matrix=[],
            cost_vector=[],
            cost_matrix=[],
            per_visit_totals=[],
            per_procedure_totals=[],
            grand_total=Decimal('0.00')
        )


# Global singleton
_matrix_calculator = None

def get_matrix_calculator() -> MatrixCalculator:
    """Get or create global matrix calculator instance"""
    global _matrix_calculator
    if _matrix_calculator is None:
        _matrix_calculator = MatrixCalculator()
    return _matrix_calculator







