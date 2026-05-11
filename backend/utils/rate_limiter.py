"""
Rate limiting utilities for API calls
"""
import asyncio
import time
from typing import Dict, Optional
from asyncio_throttle import Throttler
from config import settings
from utils.logger import log_error

class RateLimiter:
    def __init__(self):
        # Use unified rate limiting configuration
        rate_limit = settings.RATE_LIMIT_REQUESTS
        window = settings.RATE_LIMIT_WINDOW
        
        self.throttlers: Dict[str, Throttler] = {
            "clinical_trials": Throttler(rate_limit=rate_limit, period=window),
            "pubmed": Throttler(rate_limit=rate_limit, period=window),
            "bioontology": Throttler(rate_limit=rate_limit, period=window),
            "goodrx": Throttler(rate_limit=rate_limit, period=window),
            # EMA public APIs + bulk JSON refresh: stay conservative vs upstream
            "ema_eu": Throttler(rate_limit=min(20, rate_limit), period=window),
            # CDE / NMPA: Google CSE + page fetches — separate budget from general google_search
            "china_regulatory": Throttler(rate_limit=min(15, rate_limit), period=window),
            "china_regulatory_content": Throttler(rate_limit=min(20, rate_limit), period=window),
            # Public APIs — stay polite vs upstream guidelines
            "nih_reporter": Throttler(rate_limit=1, period=2),
            "npi_registry": Throttler(rate_limit=min(8, rate_limit), period=window),
            "openalex": Throttler(rate_limit=min(10, rate_limit), period=window),
            "crossref": Throttler(rate_limit=min(8, rate_limit), period=window),
            "ror": Throttler(rate_limit=min(10, rate_limit), period=window),
            "open_payments": Throttler(rate_limit=min(6, rate_limit), period=window),
            "eu_ctis": Throttler(rate_limit=min(6, rate_limit), period=window),
            "isrctn": Throttler(rate_limit=min(6, rate_limit), period=window),
            "cms_open_data": Throttler(rate_limit=min(8, rate_limit), period=window),
            "fda_datadashboard": Throttler(rate_limit=min(4, rate_limit), period=window),
        }
        self.request_timestamps: Dict[str, list] = {
            "clinical_trials": [],
            "pubmed": [],
            "bioontology": [],
            "goodrx": [],
            "ema_eu": [],
            "china_regulatory": [],
            "china_regulatory_content": [],
            "nih_reporter": [],
            "npi_registry": [],
            "openalex": [],
            "crossref": [],
            "ror": [],
            "open_payments": [],
            "eu_ctis": [],
            "isrctn": [],
            "cms_open_data": [],
            "fda_datadashboard": [],
        }
    
    async def acquire(self, api_name: str) -> bool:
        """Acquire permission to make API call"""
        if api_name not in self.throttlers:
            return True
        
        try:
            await self.throttlers[api_name].acquire()
            self.request_timestamps[api_name].append(time.time())
            
            # Clean old timestamps (older than rate limit window)
            current_time = time.time()
            window = settings.RATE_LIMIT_WINDOW
            self.request_timestamps[api_name] = [
                ts for ts in self.request_timestamps[api_name] 
                if current_time - ts < window
            ]
            
            return True
        except Exception as e:
            log_error(e, f"Rate limiter acquire for {api_name}")
            return False
    
    def get_wait_time(self, api_name: str) -> float:
        """Get estimated wait time for next request"""
        if api_name not in self.request_timestamps:
            return 0.0
        
        current_time = time.time()
        window = settings.RATE_LIMIT_WINDOW
        recent_requests = [
            ts for ts in self.request_timestamps[api_name] 
            if current_time - ts < window
        ]
        
        max_requests = settings.RATE_LIMIT_REQUESTS
        
        if len(recent_requests) >= max_requests:
            oldest_request = min(recent_requests)
            return window - (current_time - oldest_request)
        
        return 0.0
    
    def get_stats(self, api_name: str) -> Dict:
        """Get rate limiting statistics"""
        if api_name not in self.request_timestamps:
            return {"requests_last_minute": 0, "wait_time": 0.0}
        
        current_time = time.time()
        window = settings.RATE_LIMIT_WINDOW
        requests_last_window = len([
            ts for ts in self.request_timestamps[api_name] 
            if current_time - ts < window
        ])
        
        return {
            "requests_last_minute": requests_last_window,
            "wait_time": self.get_wait_time(api_name)
        }

# Global rate limiter instance
rate_limiter = RateLimiter() 