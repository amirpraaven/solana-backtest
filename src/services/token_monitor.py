import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Set, Optional, Callable
import logging
import asyncpg
import aioredis

from src.api import BirdeyeClient
from .token_tracker import TokenAgeTracker

logger = logging.getLogger(__name__)


class TokenMonitor:
    """Real-time monitoring service for new tokens"""
    
    def __init__(
        self,
        birdeye_client: BirdeyeClient,
        token_tracker: TokenAgeTracker,
        db_pool: asyncpg.Pool,
        redis_client: aioredis.Redis
    ):
        self.birdeye = birdeye_client
        self.tracker = token_tracker
        self.db = db_pool
        self.redis = redis_client
        
        self.monitored_tokens: Set[str] = set()
        self.callbacks: List[Callable] = []
        self.running = False
        self.poll_interval = 60  # seconds
        
    def register_callback(self, callback: Callable):
        """Register a callback for new token notifications"""
        self.callbacks.append(callback)
        
    async def start(self):
        """Start monitoring for new tokens"""
        self.running = True
        logger.info("Starting token monitor")
        
        # Load existing monitored tokens
        await self._load_monitored_tokens()
        
        while self.running:
            try:
                await self._check_new_tokens()
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Error in token monitor: {e}")
                await asyncio.sleep(self.poll_interval)
                
    async def stop(self):
        """Stop monitoring"""
        self.running = False
        logger.info("Stopping token monitor")
        
    async def _load_monitored_tokens(self):
        """Load already monitored tokens from database"""
        
        # Get tokens created in last 7 days
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT token_address
                FROM token_metadata
                WHERE created_at > $1
            """, cutoff)
            
        self.monitored_tokens = {row['token_address'] for row in rows}
        logger.info(f"Loaded {len(self.monitored_tokens)} monitored tokens")
        
    async def _check_new_tokens(self):
        """Check for new tokens"""
        
        try:
            # Get latest tokens from Birdeye
            new_tokens = await self.birdeye.get_token_list(
                sort_by="createdAt",
                sort_type="desc",
                limit=50
            )
            
            for token in new_tokens:
                address = token.get('address')
                if not address or address in self.monitored_tokens:
                    continue
                    
                # Check if token meets criteria
                if await self._should_monitor_token(token):
                    await self._process_new_token(token)
                    
        except Exception as e:
            logger.error(f"Error checking new tokens: {e}")
            
    async def _should_monitor_token(self, token: Dict) -> bool:
        """Determine if token should be monitored"""
        
        # Basic filters
        liquidity = token.get('liquidity', {}).get('usd', 0)
        volume_24h = token.get('v24hUSD', 0)
        
        # Skip tokens with very low liquidity
        if liquidity < 1000:
            return False
            
        # Skip tokens with no volume
        if volume_24h == 0:
            return False
            
        # Check token age
        address = token.get('address')
        age_hours = await self.tracker.get_token_age_hours(address)
        
        # Only monitor tokens less than 7 days old
        if age_hours is not None and age_hours > 168:
            return False
            
        return True
        
    async def _process_new_token(self, token: Dict):
        """Process a newly discovered token"""
        
        address = token['address']
        self.monitored_tokens.add(address)
        
        # Get full token metadata
        creation_time = await self.tracker.get_token_creation_time(address)
        
        # Store in database
        async with self.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO token_metadata (
                    token_address, name, symbol, decimals,
                    created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, NOW())
                ON CONFLICT (token_address) DO NOTHING
            """,
                address,
                token.get('name'),
                token.get('symbol'),
                token.get('decimals', 9),
                creation_time or datetime.now(timezone.utc)
            )
            
        # Notify callbacks
        for callback in self.callbacks:
            try:
                await callback({
                    'token_address': address,
                    'name': token.get('name'),
                    'symbol': token.get('symbol'),
                    'liquidity': token.get('liquidity', {}).get('usd', 0),
                    'volume_24h': token.get('v24hUSD', 0),
                    'created_at': creation_time,
                    'discovered_at': datetime.now(timezone.utc)
                })
            except Exception as e:
                logger.error(f"Error in callback: {e}")
                
    async def get_monitored_tokens(
        self,
        max_age_hours: Optional[float] = None
    ) -> List[str]:
        """Get list of currently monitored tokens"""
        
        if max_age_hours is None:
            return list(self.monitored_tokens)
            
        # Filter by age
        filtered_tokens = []
        for token in self.monitored_tokens:
            age = await self.tracker.get_token_age_hours(token)
            if age is not None and age <= max_age_hours:
                filtered_tokens.append(token)
                
        return filtered_tokens
        
    async def add_token_to_monitor(self, token_address: str):
        """Manually add a token to monitor"""
        
        if token_address in self.monitored_tokens:
            return
            
        self.monitored_tokens.add(token_address)
        
        # Fetch and store metadata
        creation_time = await self.tracker.get_token_creation_time(token_address)
        
        logger.info(f"Added token {token_address} to monitor list")
        
    async def remove_token_from_monitor(self, token_address: str):
        """Remove a token from monitoring"""
        
        self.monitored_tokens.discard(token_address)
        logger.info(f"Removed token {token_address} from monitor list")