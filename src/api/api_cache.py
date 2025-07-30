import json
import hashlib
from typing import Any, Optional, Union, List, Dict
import aioredis
from datetime import datetime, timedelta
import logging

from config import settings, get_redis_url

logger = logging.getLogger(__name__)


class APICache:
    """Redis-based caching layer for API responses"""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or get_redis_url()
        self.redis: Optional[aioredis.Redis] = None
        self.default_ttl = settings.CACHE_TTL
        
    async def connect(self):
        """Connect to Redis"""
        self.redis = await aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
            
    def _generate_key(self, prefix: str, params: dict) -> str:
        """Generate cache key from prefix and parameters"""
        # Sort params for consistent keys
        sorted_params = json.dumps(params, sort_keys=True)
        param_hash = hashlib.md5(sorted_params.encode()).hexdigest()
        return f"{prefix}:{param_hash}"
        
    async def get(
        self,
        key_prefix: str,
        params: dict
    ) -> Optional[Any]:
        """Get cached value"""
        
        if not self.redis:
            return None
            
        key = self._generate_key(key_prefix, params)
        
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            
        return None
        
    async def set(
        self,
        key_prefix: str,
        params: dict,
        value: Any,
        ttl: Optional[int] = None
    ):
        """Set cached value"""
        
        if not self.redis:
            return
            
        key = self._generate_key(key_prefix, params)
        ttl = ttl or self.default_ttl
        
        try:
            await self.redis.setex(
                key,
                ttl,
                json.dumps(value)
            )
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            
    async def delete(self, key_prefix: str, params: dict):
        """Delete cached value"""
        
        if not self.redis:
            return
            
        key = self._generate_key(key_prefix, params)
        
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            
    async def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern"""
        
        if not self.redis:
            return
            
        try:
            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(
                    cursor,
                    match=pattern,
                    count=100
                )
                
                if keys:
                    await self.redis.delete(*keys)
                    
                if cursor == 0:
                    break
                    
        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")
            
    async def get_or_fetch(
        self,
        key_prefix: str,
        params: dict,
        fetch_func,
        ttl: Optional[int] = None
    ) -> Any:
        """Get from cache or fetch and cache"""
        
        # Try cache first
        cached = await self.get(key_prefix, params)
        if cached is not None:
            return cached
            
        # Fetch from source
        result = await fetch_func(**params)
        
        # Cache result
        if result is not None:
            await self.set(key_prefix, params, result, ttl)
            
        return result


class CachedHeliusClient:
    """Helius client with caching"""
    
    def __init__(self, helius_client, cache: APICache):
        self.client = helius_client
        self.cache = cache
        
    async def get_token_transactions(
        self,
        token_address: str,
        start_time: datetime,
        end_time: datetime,
        tx_type: str = "SWAP"
    ) -> List[Dict]:
        """Get token transactions with caching"""
        
        params = {
            "token_address": token_address,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "tx_type": tx_type
        }
        
        return await self.cache.get_or_fetch(
            "helius:token_txs",
            params,
            lambda **p: self.client.get_token_transactions(
                p["token_address"],
                datetime.fromisoformat(p["start_time"]),
                datetime.fromisoformat(p["end_time"]),
                p["tx_type"]
            ),
            ttl=300  # 5 minutes
        )
        
    async def get_token_creation_time(self, token_address: str) -> Optional[datetime]:
        """Get token creation time with caching"""
        
        params = {"token_address": token_address}
        
        return await self.cache.get_or_fetch(
            "helius:token_creation",
            params,
            lambda **p: self.client.get_token_creation_time(p["token_address"]),
            ttl=86400  # 24 hours
        )


class CachedBirdeyeClient:
    """Birdeye client with caching"""
    
    def __init__(self, birdeye_client, cache: APICache):
        self.client = birdeye_client
        self.cache = cache
        
    async def get_token_overview(self, token_address: str) -> Dict:
        """Get token overview with caching"""
        
        params = {"token_address": token_address}
        
        return await self.cache.get_or_fetch(
            "birdeye:token_overview",
            params,
            lambda **p: self.client.get_token_overview(p["token_address"]),
            ttl=60  # 1 minute for real-time data
        )
        
    async def get_ohlcv(
        self,
        token_address: str,
        start_time: int,
        end_time: int,
        interval: str = "1m"
    ) -> List[Dict]:
        """Get OHLCV data with caching"""
        
        params = {
            "token_address": token_address,
            "start_time": start_time,
            "end_time": end_time,
            "interval": interval
        }
        
        # Longer cache for historical data
        ttl = 3600 if end_time < int(datetime.now().timestamp()) else 60
        
        return await self.cache.get_or_fetch(
            "birdeye:ohlcv",
            params,
            lambda **p: self.client.get_ohlcv(**p),
            ttl=ttl
        )