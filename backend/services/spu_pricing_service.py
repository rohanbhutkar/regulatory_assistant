"""
SPU Pricing Service
Fair Market Value pricing for procedures by country
"""

import logging
from typing import Optional, Dict, List
from decimal import Decimal

from models.cpp_models import SPUPrice
from services.cpp_data_loaders import get_cpp_data_loader

logger = logging.getLogger(__name__)


class SPUPricingService:
    """
    Service for SPU (Standard Pricing Unit) Fair Market Value pricing
    
    Provides country-specific pricing with intelligent fallbacks
    """
    
    # Default prices for common internal codes (USD)
    DEFAULT_INTERNAL_PRICING = {
        '*INCO': Decimal('150.00'),  # Patient Inconvenience Fee
        '*RNDO': Decimal('500.00'),  # Randomization
        '*IWR*': Decimal('300.00'),  # Interactive Web Response
        '*DAS2': Decimal('200.00'),  # Data Storage
        '*OQOL': Decimal('100.00'),  # Quality of Life Questionnaire
        '*MEAC': Decimal('250.00'),  # Medical Chart Access
        '*CNSV': Decimal('350.00'),  # Consent Visit
        '*SAEA': Decimal('400.00'),  # Serious Adverse Event Assessment
        '*RCM*': Decimal('200.00'),  # Reimbursement
        '*ISCE': Decimal('300.00'),  # Informed Consent
        '*DPMD': Decimal('150.00'),  # Dispensing Medicine
    }
    
    # Currency conversion rates (to USD)
    # In production, these should be fetched from a live API
    CURRENCY_RATES = {
        'USD': Decimal('1.00'),
        'EUR': Decimal('1.10'),
        'GBP': Decimal('1.25'),
        'JPY': Decimal('0.0067'),
        'CNY': Decimal('0.14'),
        'INR': Decimal('0.012'),
        'AUD': Decimal('0.65'),
        'CAD': Decimal('0.74'),
        'BRL': Decimal('0.20'),
        'MXN': Decimal('0.050'),
        'KRW': Decimal('0.00075'),
    }
    
    def __init__(self):
        self.data_loader = get_cpp_data_loader()
        self._price_cache = {}
    
    def get_procedure_price(
        self,
        procedure_code: str,
        country_code: str = 'USA',
        convert_to_usd: bool = False
    ) -> Optional[SPUPrice]:
        """
        Get procedure price for a specific country
        
        Fallback strategy:
        1. Try SPU pricing for specified country
        2. Try SPU pricing for USA
        3. Try internal code pricing
        4. Return None (needs manual pricing)
        
        Args:
            procedure_code: Procedure code
            country_code: Country code (e.g., 'USA', 'GBR')
            convert_to_usd: If True, convert to USD
            
        Returns:
            SPUPrice or None
        """
        cache_key = (procedure_code, country_code, convert_to_usd)
        if cache_key in self._price_cache:
            return self._price_cache[cache_key]
        
        # Try SPU pricing
        spu_price = self.data_loader.get_spu_price(procedure_code, country_code)
        
        if spu_price:
            if convert_to_usd and spu_price.currency != 'USD':
                converted_price = self._convert_to_usd(spu_price.local_price, spu_price.currency)
                spu_price = SPUPrice(
                    procedure_code=procedure_code,
                    country_code=country_code,
                    local_price=converted_price,
                    currency='USD',
                    source='SPU (converted)'
                )
            
            self._price_cache[cache_key] = spu_price
            return spu_price
        
        # Fallback to USA pricing
        if country_code != 'USA':
            usa_price = self.data_loader.get_spu_price(procedure_code, 'USA')
            if usa_price:
                logger.debug(f"Using USA price for {procedure_code} in {country_code}")
                fallback_price = SPUPrice(
                    procedure_code=procedure_code,
                    country_code=country_code,
                    local_price=usa_price.local_price,
                    currency='USD',
                    source='SPU (USA fallback)'
                )
                self._price_cache[cache_key] = fallback_price
                return fallback_price
        
        # Fallback to internal code pricing
        internal_price = self._get_internal_price(procedure_code)
        if internal_price:
            logger.debug(f"Using internal price for {procedure_code}")
            price_obj = SPUPrice(
                procedure_code=procedure_code,
                country_code=country_code,
                local_price=internal_price,
                currency='USD',
                source='Internal default'
            )
            self._price_cache[cache_key] = price_obj
            return price_obj
        
        # No price found
        logger.warning(f"No price found for {procedure_code} in {country_code}")
        return None
    
    def get_prices_batch(
        self,
        procedure_codes: List[str],
        country_code: str = 'USA'
    ) -> Dict[str, Optional[SPUPrice]]:
        """Get prices for multiple procedures"""
        return {
            code: self.get_procedure_price(code, country_code)
            for code in procedure_codes
        }
    
    def calculate_procedure_costs(
        self,
        procedures: List[Dict[str, any]],
        country_code: str = 'USA'
    ) -> Dict[str, any]:
        """
        Calculate total costs for a list of procedures
        
        Args:
            procedures: List of dicts with 'code' and 'quantity'
            country_code: Country code
            
        Returns:
            Dict with total cost and breakdown
        """
        total_cost = Decimal('0.00')
        procedure_costs = []
        missing_prices = []
        
        for proc in procedures:
            code = proc.get('code')
            quantity = Decimal(str(proc.get('quantity', 1)))
            
            if not code:
                continue
            
            price_obj = self.get_procedure_price(code, country_code)
            
            if price_obj:
                unit_price = price_obj.local_price
                proc_cost = unit_price * quantity
                total_cost += proc_cost
                
                procedure_costs.append({
                    'code': code,
                    'name': proc.get('name', code),
                    'quantity': float(quantity),
                    'unit_price': float(unit_price),
                    'total_cost': float(proc_cost),
                    'currency': price_obj.currency,
                    'source': price_obj.source
                })
            else:
                missing_prices.append(code)
                logger.warning(f"Skipping {code} - no pricing available")
        
        return {
            'total_cost': float(total_cost),
            'currency': 'USD',
            'procedure_costs': procedure_costs,
            'missing_prices': missing_prices,
            'count_priced': len(procedure_costs),
            'count_missing': len(missing_prices)
        }
    
    def _get_internal_price(self, procedure_code: str) -> Optional[Decimal]:
        """Get price for internal codes (wildcards)"""
        # Check exact match
        if procedure_code in self.DEFAULT_INTERNAL_PRICING:
            return self.DEFAULT_INTERNAL_PRICING[procedure_code]
        
        # Check wildcard patterns
        for pattern, price in self.DEFAULT_INTERNAL_PRICING.items():
            if '*' in pattern:
                # Simple wildcard matching
                pattern_parts = pattern.split('*')
                matches = all(
                    part in procedure_code
                    for part in pattern_parts if part
                )
                if matches:
                    return price
        
        return None
    
    def _convert_to_usd(self, amount: Decimal, from_currency: str) -> Decimal:
        """Convert currency amount to USD"""
        if from_currency == 'USD':
            return amount
        
        rate = self.CURRENCY_RATES.get(from_currency)
        if not rate:
            logger.warning(f"No conversion rate for {from_currency}, using 1:1")
            return amount
        
        return amount * rate


# Global singleton
_spu_pricing_service = None

def get_spu_pricing_service() -> SPUPricingService:
    """Get or create global SPU pricing service instance"""
    global _spu_pricing_service
    if _spu_pricing_service is None:
        _spu_pricing_service = SPUPricingService()
    return _spu_pricing_service







