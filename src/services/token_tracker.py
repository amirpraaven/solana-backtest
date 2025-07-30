from datetime import datetime, timezone, timedelta
import asyncio
from typing import Optional, Dict, List, Any
import asyncpg
import aioredis
import logging

from src.api import HeliusClient, BirdeyeClient

logger = logging.getLogger(__name__)


class TokenAgeTracker:
    """Service for tracking token creation times and ages"""
    
    def __init__(
        self,
        helius_client: HeliusClient,
        birdeye_client: BirdeyeClient,
        db_pool: asyncpg.Pool,
        redis_client: aioredis.Redis
    ):
        self.helius = helius_client
        self.birdeye = birdeye_client
        self.db = db_pool
        self.redis = redis_client
        self.cache_ttl = 86400  # 24 hours
        
    async def get_token_creation_time(self, token_address: str) -> Optional[datetime]:
        """Get token creation time from first mint transaction"""
        
        # Check cache first
        cache_key = f"token_creation:{token_address}"
        cached = await self.redis.get(cache_key)
        if cached:
            return datetime.fromisoformat(cached)
            
        # Check database
        async with self.db.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT created_at FROM token_metadata WHERE token_address = $1",
                token_address
            )
            
        if result:
            creation_time = result['created_at']
            # Update cache
            await self.redis.setex(
                cache_key,
                self.cache_ttl,
                creation_time.isoformat()
            )
            return creation_time
            
        # Try to fetch from APIs
        creation_time = await self._fetch_creation_time(token_address)
        
        if creation_time:
            # Store in database
            await self._store_token_metadata(token_address, creation_time)
            
            # Cache result
            await self.redis.setex(
                cache_key,
                self.cache_ttl,
                creation_time.isoformat()
            )
            
        return creation_time
        
    async def _fetch_creation_time(self, token_address: str) -> Optional[datetime]:
        """Fetch token creation time from APIs"""
        
        # Try Birdeye first (usually faster)
        try:
            creation_info = await self.birdeye.get_token_creation_info(token_address)
            if creation_info and 'createdAt' in creation_info:
                return datetime.fromtimestamp(creation_info['createdAt'], tz=timezone.utc)
        except Exception as e:
            logger.error(f"Error fetching from Birdeye: {e}")
            
        # Fallback to Helius
        try:
            creation_time = await self.helius.get_token_creation_time(token_address)
            if creation_time:
                return creation_time.replace(tzinfo=timezone.utc)
        except Exception as e:
            logger.error(f"Error fetching from Helius: {e}")
            
        return None
        
    async def _store_token_metadata(
        self,
        token_address: str,
        creation_time: datetime,
        metadata: Optional[Dict] = None
    ):
        """Store token metadata in database"""
        
        async with self.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO token_metadata (
                    token_address, created_at, name, symbol, decimals,
                    creator_address, total_supply, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                ON CONFLICT (token_address) 
                DO UPDATE SET 
                    created_at = EXCLUDED.created_at,
                    updated_at = NOW()
            """,
                token_address,
                creation_time,
                metadata.get('name') if metadata else None,
                metadata.get('symbol') if metadata else None,
                metadata.get('decimals') if metadata else None,
                metadata.get('creator') if metadata else None,
                metadata.get('totalSupply') if metadata else None
            )
            
    async def get_token_age_hours(self, token_address: str) -> Optional[float]:
        """Get token age in hours"""
        
        creation_time = await self.get_token_creation_time(token_address)
        if not creation_time:
            return None
            
        # Ensure timezone aware
        if creation_time.tzinfo is None:
            creation_time = creation_time.replace(tzinfo=timezone.utc)
            
        age = datetime.now(timezone.utc) - creation_time
        return age.total_seconds() / 3600
        
    async def get_token_age_days(self, token_address: str) -> Optional[float]:
        """Get token age in days"""
        
        hours = await self.get_token_age_hours(token_address)
        return hours / 24 if hours is not None else None
        
    async def batch_update_token_metadata(self, token_addresses: List[str]):
        """Batch update token metadata for efficiency"""
        
        # Filter out already cached tokens
        uncached_tokens = []
        for address in token_addresses:
            cache_key = f"token_creation:{address}"
            if not await self.redis.exists(cache_key):
                uncached_tokens.append(address)
                
        if not uncached_tokens:
            return
            
        logger.info(f"Batch updating metadata for {len(uncached_tokens)} tokens")
        
        # Create tasks for parallel fetching
        tasks = []
        for address in uncached_tokens:
            task = self.get_token_creation_time(address)
            tasks.append(task)
            
        # Execute with rate limiting
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log errors
        for address, result in zip(uncached_tokens, results):
            if isinstance(result, Exception):
                logger.error(f"Error updating metadata for {address}: {result}")
                
    async def get_tokens_by_age(
        self,
        max_age_hours: float,
        min_age_hours: float = 0,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get tokens within a specific age range"""
        
        min_created_at = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        max_created_at = datetime.now(timezone.utc) - timedelta(hours=min_age_hours)
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    token_address,
                    name,
                    symbol,
                    created_at,
                    EXTRACT(EPOCH FROM (NOW() - created_at)) / 3600 as age_hours
                FROM token_metadata
                WHERE created_at BETWEEN $1 AND $2
                ORDER BY created_at DESC
                LIMIT $3
            """, min_created_at, max_created_at, limit)
            
        return [dict(row) for row in rows]
        
    async def get_first_pool_creation_time(
        self,
        token_address: str
    ) -> Optional[datetime]:
        """Get time when first liquidity pool was created for token"""
        
        # Check cache
        cache_key = f"first_pool:{token_address}"
        cached = await self.redis.get(cache_key)
        if cached:
            return datetime.fromisoformat(cached)
            
        # Check database
        async with self.db.acquire() as conn:
            result = await conn.fetchrow(
                "SELECT first_pool_created_at FROM token_metadata WHERE token_address = $1",
                token_address
            )
            
        if result and result['first_pool_created_at']:
            pool_time = result['first_pool_created_at']
            await self.redis.setex(cache_key, self.cache_ttl, pool_time.isoformat())
            return pool_time
            
        # Query pool states to find first pool
        async with self.db.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT MIN(time) as first_pool_time
                FROM pool_states
                WHERE token_address = $1
            """, token_address)
            
        if result and result['first_pool_time']:
            pool_time = result['first_pool_time']
            
            # Update token metadata
            await conn.execute("""
                UPDATE token_metadata
                SET first_pool_created_at = $1
                WHERE token_address = $2
            """, pool_time, token_address)
            
            await self.redis.setex(cache_key, self.cache_ttl, pool_time.isoformat())
            return pool_time
            
        return None
        
    async def is_token_within_age(
        self,
        token_address: str,
        max_age_hours: float
    ) -> bool:
        """Check if token is within specified age limit"""
        
        age_hours = await self.get_token_age_hours(token_address)
        if age_hours is None:
            return False
            
        return age_hours <= max_age_hours