"""
Caching utilities for the Clinical Research Assistant
"""
import json
import hashlib
from typing import Any, Optional
import redis
from config import settings
from utils.logger import log_cache_hit, log_cache_miss, log_error

class CacheManager:
    def __init__(self):
        self.redis_client = None
        self._fallback_cache = {}  # In-memory fallback cache
        try:
            # Build Redis URL from individual settings
            redis_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
            if settings.REDIS_PASSWORD:
                redis_url = f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
            
            self.redis_client = redis.from_url(redis_url)
            self.redis_client.ping()  # Test connection
            print("✅ Redis cache connected successfully")
        except Exception as e:
            log_error(e, "Cache initialization")
            print("⚠️  Redis not available, using in-memory fallback cache")
            self.redis_client = None
    
    def _generate_key(self, prefix: str, data: Any) -> str:
        """Generate a cache key from data"""
        data_str = json.dumps(data, sort_keys=True)
        hash_obj = hashlib.md5(data_str.encode())
        return f"{prefix}:{hash_obj.hexdigest()}"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value:
                    log_cache_hit(key)
                    return json.loads(value)
                else:
                    log_cache_miss(key)
                    return None
            except Exception as e:
                log_error(e, f"Cache get for key: {key}")
                # Fall back to in-memory cache
                return self._fallback_cache.get(key)
        else:
            # Use in-memory cache
            return self._fallback_cache.get(key)
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache"""
        if self.redis_client:
            try:
                ttl = ttl or settings.REDIS_TTL
                # Convert Pydantic models to dict for JSON serialization
                serialized_value = self._serialize_value(value)
                return self.redis_client.setex(key, ttl, serialized_value)
            except Exception as e:
                log_error(e, f"Cache set for key: {key}")
                # Fall back to in-memory cache
                self._fallback_cache[key] = value
                return True
        else:
            # Use in-memory cache
            self._fallback_cache[key] = value
            return True
    
    def _serialize_value(self, value: Any) -> str:
        """Serialize value for JSON storage"""
        if isinstance(value, list):
            # Handle lists of objects
            serialized_list = []
            for item in value:
                if hasattr(item, 'model_dump'):
                    # Pydantic v2
                    serialized_list.append(item.model_dump())
                elif hasattr(item, 'dict'):
                    # Pydantic v1
                    serialized_list.append(item.dict())
                else:
                    serialized_list.append(item)
            return json.dumps(serialized_list)
        elif hasattr(value, 'model_dump'):
            # Pydantic v2
            return json.dumps(value.model_dump())
        elif hasattr(value, 'dict'):
            # Pydantic v1
            return json.dumps(value.dict())
        else:
            # Regular object
            return json.dumps(value)
    
    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        if self.redis_client:
            try:
                return bool(self.redis_client.delete(key))
            except Exception as e:
                log_error(e, f"Cache delete for key: {key}")
                # Fall back to in-memory cache
                return self._fallback_cache.pop(key, None) is not None
        else:
            # Use in-memory cache
            return self._fallback_cache.pop(key, None) is not None
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        if self.redis_client:
            try:
                keys = self.redis_client.keys(pattern)
                if keys:
                    return self.redis_client.delete(*keys)
                return 0
            except Exception as e:
                log_error(e, f"Cache clear pattern: {pattern}")
                # Fall back to in-memory cache
                return self._clear_fallback_pattern(pattern)
        else:
            # Use in-memory cache
            return self._clear_fallback_pattern(pattern)
    
    def _clear_fallback_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern in fallback cache"""
        import re
        pattern_re = re.compile(pattern.replace('*', '.*'))
        keys_to_delete = [key for key in self._fallback_cache.keys() if pattern_re.match(key)]
        for key in keys_to_delete:
            del self._fallback_cache[key]
        return len(keys_to_delete)
    
    def get_query_cache_key(self, query: str, sources: list) -> str:
        """Generate cache key for query results"""
        return self._generate_key("query", {"query": query, "sources": sources})
    
    def get_api_cache_key(self, api_name: str, endpoint: str, params: dict) -> str:
        """Generate cache key for API calls"""
        return self._generate_key(f"api:{api_name}", {"endpoint": endpoint, "params": params})

# Global cache instance
cache_manager = CacheManager() 