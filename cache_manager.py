"""
Cache Manager Module
Redis-based caching for improved performance
"""

import redis
import json
import os
from typing import Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CacheManager:
    """Manages caching operations using Redis"""
    
    def __init__(self):
        """Initialize Redis connection"""
        self.host = os.getenv('REDIS_HOST', 'localhost')
        self.port = int(os.getenv('REDIS_PORT', 6379))
        self.db = int(os.getenv('REDIS_DB', 0))
        self.password = os.getenv('REDIS_PASSWORD', None)
        
        try:
            self.redis_client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True,
                socket_connect_timeout=5
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info(f"Redis connected: {self.host}:{self.port}")
            self.cache_enabled = True
            
        except redis.ConnectionError:
            logger.warning("Redis not available, caching disabled")
            self.redis_client = None
            self.cache_enabled = False
        
        # Statistics
        self.hits = 0
        self.misses = 0
    
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        if not self.cache_enabled:
            return None
        
        try:
            value = self.redis_client.get(key)
            
            if value:
                self.hits += 1
                return json.loads(value)
            else:
                self.misses += 1
                return None
                
        except Exception as e:
            logger.error(f"Cache get error: {str(e)}")
            return None
    
    
    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: 1 hour)
            
        Returns:
            True if successful
        """
        if not self.cache_enabled:
            return False
        
        try:
            serialized = json.dumps(value)
            self.redis_client.setex(key, ttl, serialized)
            return True
            
        except Exception as e:
            logger.error(f"Cache set error: {str(e)}")
            return False
    
    
    def delete(self, key: str) -> bool:
        """
        Delete key from cache
        
        Args:
            key: Cache key
            
        Returns:
            True if successful
        """
        if not self.cache_enabled:
            return False
        
        try:
            self.redis_client.delete(key)
            return True
            
        except Exception as e:
            logger.error(f"Cache delete error: {str(e)}")
            return False
    
    
    def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching pattern
        
        Args:
            pattern: Key pattern (e.g., "sentiment:*")
            
        Returns:
            Number of keys deleted
        """
        if not self.cache_enabled:
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
            
        except Exception as e:
            logger.error(f"Cache clear pattern error: {str(e)}")
            return 0
    
    
    def get_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return round((self.hits / total) * 100, 2)
    
    
    def check_connection(self) -> bool:
        """Check Redis connection health"""
        if not self.cache_enabled:
            return False
        
        try:
            self.redis_client.ping()
            return True
        except:
            return False
    
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        if not self.cache_enabled:
            return {'enabled': False}
        
        try:
            info = self.redis_client.info()
            return {
                'enabled': True,
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': self.get_hit_rate(),
                'total_keys': self.redis_client.dbsize(),
                'used_memory': info.get('used_memory_human', 'N/A'),
                'connected_clients': info.get('connected_clients', 0)
            }
        except Exception as e:
            logger.error(f"Error getting stats: {str(e)}")
            return {'enabled': True, 'error': str(e)}


# Example usage
if __name__ == "__main__":
    cache = CacheManager()
    
    print("=== Cache Operations ===")
    
    # Set value
    cache.set('test_key', {'data': 'test_value'}, ttl=60)
    print("Value set in cache")
    
    # Get value
    value = cache.get('test_key')
    print(f"Retrieved value: {value}")
    
    # Get stats
    stats = cache.get_stats()
    print(f"\n=== Cache Stats ===")
    print(f"Hit rate: {stats.get('hit_rate')}%")
    print(f"Total keys: {stats.get('total_keys')}")