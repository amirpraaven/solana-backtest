import asyncio
import aiohttp
from typing import List, Dict, Optional, Any
from datetime import datetime
import backoff
from ratelimit import limits, sleep_and_retry
import logging

from config import settings

logger = logging.getLogger(__name__)


class BirdeyeClient:
    """Birdeye API client with rate limiting and retry logic"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.BIRDEYE_API_KEY
        self.base_url = "https://public-api.birdeye.so"
        self.headers = {
            'X-API-KEY': self.api_key,
            'x-chain': 'solana'
        }
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limit = settings.BIRDEYE_RATE_LIMIT
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    @sleep_and_retry
    @limits(calls=50, period=1)  # Business plan limit
    @backoff.on_exception(backoff.expo, aiohttp.ClientError, max_tries=3)
    async def get_ohlcv(
        self,
        token_address: str,
        start_time: int,
        end_time: int,
        interval: str = "1m"
    ) -> List[Dict]:
        """Get OHLCV data with volume"""
        
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
            
        params = {
            'address': token_address,
            'type': interval,
            'time_from': start_time,
            'time_to': end_time
        }
        
        try:
            async with self.session.get(
                f"{self.base_url}/defi/ohlcv",
                params=params
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get('data', {}).get('items', [])
                
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching OHLCV data: {e}")
            raise
            
    @sleep_and_retry
    @limits(calls=50, period=1)
    @backoff.on_exception(backoff.expo, aiohttp.ClientError, max_tries=3)
    async def get_token_overview(self, token_address: str) -> Dict:
        """Get current market cap and liquidity"""
        
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
            
        try:
            async with self.session.get(
                f"{self.base_url}/defi/token_overview",
                params={'address': token_address}
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get('data', {})
                
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching token overview: {e}")
            raise
            
    @sleep_and_retry
    @limits(calls=50, period=1)
    async def get_token_security(self, token_address: str) -> Dict:
        """Get token security information"""
        
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
            
        try:
            async with self.session.get(
                f"{self.base_url}/defi/token_security",
                params={'address': token_address}
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get('data', {})
                
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching token security: {e}")
            return {}
            
    @sleep_and_retry
    @limits(calls=50, period=1)
    async def get_token_creation_info(self, token_address: str) -> Optional[Dict]:
        """Get token creation information including timestamp"""
        
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
            
        try:
            async with self.session.get(
                f"{self.base_url}/defi/token_creation_info",
                params={'address': token_address}
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get('data', {})
                
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching token creation info: {e}")
            return None
            
    @sleep_and_retry
    @limits(calls=50, period=1)
    async def get_price_history(
        self,
        token_address: str,
        address_type: str = "token",
        interval: str = "1m",
        time_from: Optional[int] = None,
        time_to: Optional[int] = None
    ) -> List[Dict]:
        """Get historical price data"""
        
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
            
        params = {
            'address': token_address,
            'address_type': address_type,
            'type': interval
        }
        
        if time_from:
            params['time_from'] = time_from
        if time_to:
            params['time_to'] = time_to
            
        try:
            async with self.session.get(
                f"{self.base_url}/defi/history_price",
                params=params
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get('data', {}).get('items', [])
                
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching price history: {e}")
            raise
            
    @sleep_and_retry
    @limits(calls=50, period=1)
    async def get_trades(
        self,
        token_address: str,
        offset: int = 0,
        limit: int = 50,
        tx_type: str = "swap"
    ) -> Dict:
        """Get recent trades for a token"""
        
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
            
        params = {
            'address': token_address,
            'offset': offset,
            'limit': limit,
            'tx_type': tx_type
        }
        
        try:
            async with self.session.get(
                f"{self.base_url}/defi/txs/token",
                params=params
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get('data', {})
                
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching trades: {e}")
            raise
            
    @sleep_and_retry
    @limits(calls=50, period=1)
    async def get_token_list(
        self,
        sort_by: str = "v24hUSD",
        sort_type: str = "desc",
        offset: int = 0,
        limit: int = 50
    ) -> List[Dict]:
        """Get list of tokens sorted by various metrics"""
        
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
            
        params = {
            'sort_by': sort_by,
            'sort_type': sort_type,
            'offset': offset,
            'limit': limit
        }
        
        try:
            async with self.session.get(
                f"{self.base_url}/defi/tokenlist",
                params=params
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get('data', {}).get('tokens', [])
                
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching token list: {e}")
            raise
            
    async def get_multiple_token_overviews(
        self,
        token_addresses: List[str]
    ) -> Dict[str, Dict]:
        """Get overview for multiple tokens efficiently"""
        
        if not token_addresses:
            return {}
            
        # Birdeye supports bulk requests
        results = {}
        batch_size = 30  # Birdeye's batch limit
        
        for i in range(0, len(token_addresses), batch_size):
            batch = token_addresses[i:i + batch_size]
            
            # Process batch in parallel
            tasks = [
                self.get_token_overview(address)
                for address in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for address, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Error fetching overview for {address}: {result}")
                    results[address] = {}
                else:
                    results[address] = result
                    
            # Respect rate limit between batches
            if i + batch_size < len(token_addresses):
                await asyncio.sleep(1)
                
        return results
        
    async def get_pool_info(
        self,
        pool_address: str
    ) -> Dict:
        """Get pool information"""
        
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
            
        try:
            async with self.session.get(
                f"{self.base_url}/defi/pool_info",
                params={'address': pool_address}
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get('data', {})
                
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching pool info: {e}")
            return {}
    
    @sleep_and_retry
    @limits(calls=50, period=1)
    async def get_trending_tokens(
        self,
        time_frame: str = "24h",
        sort_by: str = "volume",
        limit: int = 50
    ) -> Dict:
        """Get trending tokens based on various metrics"""
        
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        # Map sort_by to Birdeye API parameters
        sort_map = {
            'volume': 'v24hUSD',
            'price_change': 'v24hChangePercent', 
            'trades': 'trade24h',
            'liquidity': 'liquidity'
        }
        
        try:
            async with self.session.get(
                f"{self.base_url}/defi/tokenlist",
                params={
                    'sort_by': sort_map.get(sort_by, 'v24hUSD'),
                    'sort_type': 'desc',
                    'limit': limit,
                    'min_liquidity': 1000  # Filter out very low liquidity tokens
                }
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                # Enhance token data
                tokens = []
                for token in data.get('data', {}).get('tokens', []):
                    tokens.append({
                        'address': token.get('address'),
                        'symbol': token.get('symbol'),
                        'name': token.get('name'),
                        'price': token.get('price', 0),
                        'priceChange24h': token.get('priceChange24hPercent', 0),
                        'volume24h': token.get('v24hUSD', 0),
                        'liquidity': token.get('liquidity', 0),
                        'mc': token.get('mc', 0),
                        'holder': token.get('holder', 0),
                        'trade24h': token.get('trade24h', 0),
                        'createdAt': token.get('createdAt')
                    })
                
                return {'data': tokens}
                
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching trending tokens: {e}")
            raise
    
    @sleep_and_retry
    @limits(calls=50, period=1)
    async def get_new_tokens(
        self,
        from_time: datetime,
        limit: int = 100
    ) -> Dict:
        """Get newly created tokens from a specific time"""
        
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        try:
            # Get new tokens by sorting by creation time
            async with self.session.get(
                f"{self.base_url}/defi/tokenlist",
                params={
                    'sort_by': 'createdAt',
                    'sort_type': 'desc',
                    'limit': limit,
                    'min_liquidity': 100  # Basic liquidity filter
                }
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                # Filter by creation time
                tokens = []
                for token in data.get('data', {}).get('tokens', []):
                    if token.get('createdAt'):
                        created_at = datetime.fromisoformat(token['createdAt'].replace('Z', '+00:00'))
                        if created_at >= from_time:
                            tokens.append({
                                'address': token.get('address'),
                                'symbol': token.get('symbol'),
                                'name': token.get('name'),
                                'createdAt': token.get('createdAt'),
                                'price': token.get('price', 0),
                                'volume24h': token.get('v24hUSD', 0),
                                'liquidity': token.get('liquidity', 0),
                                'mc': token.get('mc', 0),
                                'holder': token.get('holder', 0),
                                'dex': token.get('dex', 'unknown'),
                                'poolAddress': token.get('poolAddress')
                            })
                
                return {'data': tokens}
                
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching new tokens: {e}")
            raise
    
    @sleep_and_retry
    @limits(calls=50, period=1)
    async def search_tokens(
        self,
        query: str,
        limit: int = 20
    ) -> Dict:
        """Search tokens by symbol or address"""
        
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        try:
            # If query looks like an address (44 chars), search by address
            if len(query) == 44:
                token_data = await self.get_token_overview(query)
                if token_data:
                    return {'data': [token_data]}
                else:
                    return {'data': []}
            
            # Otherwise search by symbol - get token list and filter
            async with self.session.get(
                f"{self.base_url}/defi/tokenlist",
                params={
                    'sort_by': 'v24hUSD',
                    'sort_type': 'desc',
                    'limit': 200  # Get more to filter
                }
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                # Filter by symbol match
                tokens = []
                query_upper = query.upper()
                for token in data.get('data', {}).get('tokens', []):
                    if (token.get('symbol', '').upper().startswith(query_upper) or 
                        query_upper in token.get('symbol', '').upper()):
                        tokens.append({
                            'address': token.get('address'),
                            'symbol': token.get('symbol'),
                            'name': token.get('name'),
                            'price': token.get('price', 0),
                            'volume24h': token.get('v24hUSD', 0),
                            'liquidity': token.get('liquidity', 0),
                            'mc': token.get('mc', 0),
                            'decimals': token.get('decimals', 9),
                            'logoURI': token.get('logoURI')
                        })
                        
                        if len(tokens) >= limit:
                            break
                
                return {'data': tokens}
                
        except aiohttp.ClientError as e:
            logger.error(f"Error searching tokens: {e}")
            raise