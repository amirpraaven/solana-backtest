import asyncio
import aiohttp
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import backoff
from ratelimit import limits, sleep_and_retry
import logging
from base64 import b64decode

from config import settings

logger = logging.getLogger(__name__)


class HeliusClient:
    """Helius API client with rate limiting and retry logic"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.HELIUS_API_KEY
        self.base_url = "https://api.helius.xyz/v0"
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limit = settings.HELIUS_RATE_LIMIT
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
            
    @sleep_and_retry
    @limits(calls=10, period=1)  # Adjust based on your plan
    @backoff.on_exception(backoff.expo, aiohttp.ClientError, max_tries=3)
    async def get_token_transactions(
        self, 
        token_address: str, 
        start_time: datetime,
        end_time: datetime,
        tx_type: str = "SWAP"
    ) -> List[Dict]:
        """Fetch all transactions for a token in a time range"""
        
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
        
        transactions = []
        before_signature = None
        
        while True:
            params = {
                "api-key": self.api_key,
                "type": tx_type,
                "source": "RAYDIUM,METEORA,PUMP_FUN"
            }
            
            if before_signature:
                params["before"] = before_signature
                
            try:
                async with self.session.get(
                    f"{self.base_url}/addresses/{token_address}/transactions",
                    params=params
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    if not data:
                        break
                        
                    # Filter by time range
                    for tx in data:
                        tx_time = datetime.fromtimestamp(tx['timestamp'])
                        if tx_time < start_time:
                            return transactions
                        if tx_time <= end_time:
                            transactions.append(tx)
                            
                    before_signature = data[-1]['signature']
                    
                    # Rate limit handling
                    await asyncio.sleep(1 / self.rate_limit)
                    
            except aiohttp.ClientError as e:
                logger.error(f"Error fetching transactions: {e}")
                raise
                
        return transactions

    async def get_token_creation_time(self, token_address: str) -> Optional[datetime]:
        """Get token creation time from first mint transaction"""
        
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
            
        try:
            transactions = await self.get_address_transactions(
                token_address,
                transaction_type="TOKEN_MINT",
                limit=100
            )
            
            if not transactions:
                return None
                
            # Find the earliest transaction (token creation)
            earliest_tx = min(transactions, key=lambda x: x['timestamp'])
            
            return datetime.fromtimestamp(earliest_tx['timestamp'])
            
        except Exception as e:
            logger.error(f"Error getting token creation time: {e}")
            return None

    @sleep_and_retry
    @limits(calls=10, period=1)
    async def get_address_transactions(
        self,
        address: str,
        transaction_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get transactions for any address"""
        
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
            
        params = {
            "api-key": self.api_key,
            "limit": limit
        }
        
        if transaction_type:
            params["type"] = transaction_type
            
        try:
            async with self.session.get(
                f"{self.base_url}/addresses/{address}/transactions",
                params=params
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"Error fetching address transactions: {e}")
            raise

    async def parse_transaction_details(self, tx: Dict) -> Optional[Dict]:
        """Parse swap details from enhanced transaction data"""
        try:
            # Parse based on DEX type
            if self._is_pump_fun_tx(tx):
                return self._parse_pump_fun_swap(tx)
            elif self._is_raydium_clmm_tx(tx):
                return self._parse_raydium_clmm_swap(tx)
            elif self._is_raydium_cpmm_tx(tx):
                return self._parse_raydium_cpmm_swap(tx)
            elif self._is_meteora_dlmm_tx(tx):
                return self._parse_meteora_dlmm_swap(tx)
            elif self._is_meteora_dyn_tx(tx):
                return self._parse_meteora_dyn_swap(tx)
        except Exception as e:
            logger.error(f"Error parsing transaction {tx.get('signature', 'unknown')}: {e}")
            return None
            
    def _is_pump_fun_tx(self, tx: Dict) -> bool:
        return any(
            ix.get('programId') == '6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P'
            for ix in tx.get('instructions', [])
        )
        
    def _is_raydium_clmm_tx(self, tx: Dict) -> bool:
        return any(
            ix.get('programId') == 'CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK'
            for ix in tx.get('instructions', [])
        )
        
    def _is_raydium_cpmm_tx(self, tx: Dict) -> bool:
        return any(
            ix.get('programId') == 'CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C'
            for ix in tx.get('instructions', [])
        )
        
    def _is_meteora_dlmm_tx(self, tx: Dict) -> bool:
        return any(
            ix.get('programId') == 'LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo'
            for ix in tx.get('instructions', [])
        )
        
    def _is_meteora_dyn_tx(self, tx: Dict) -> bool:
        return any(
            ix.get('programId') == 'Eo7WjKq67rjJQSZxS6z3YkapzY3eMj6Xy8X5EQVn5UaB'
            for ix in tx.get('instructions', [])
        )
        
    def _parse_pump_fun_swap(self, tx: Dict) -> Optional[Dict]:
        """Parse pump.fun swap - simplified for now"""
        return {
            'dex': 'pump.fun',
            'signature': tx['signature'],
            'timestamp': datetime.fromtimestamp(tx['timestamp']),
            'type': 'swap',
            'success': tx.get('err') is None
        }
        
    def _parse_raydium_clmm_swap(self, tx: Dict) -> Optional[Dict]:
        """Parse Raydium CLMM swap - simplified for now"""
        return {
            'dex': 'raydium_clmm',
            'signature': tx['signature'],
            'timestamp': datetime.fromtimestamp(tx['timestamp']),
            'type': 'swap',
            'success': tx.get('err') is None
        }
        
    def _parse_raydium_cpmm_swap(self, tx: Dict) -> Optional[Dict]:
        """Parse Raydium CPMM swap - simplified for now"""
        return {
            'dex': 'raydium_cpmm',
            'signature': tx['signature'],
            'timestamp': datetime.fromtimestamp(tx['timestamp']),
            'type': 'swap',
            'success': tx.get('err') is None
        }
        
    def _parse_meteora_dlmm_swap(self, tx: Dict) -> Optional[Dict]:
        """Parse Meteora DLMM swap - simplified for now"""
        return {
            'dex': 'meteora_dlmm',
            'signature': tx['signature'],
            'timestamp': datetime.fromtimestamp(tx['timestamp']),
            'type': 'swap',
            'success': tx.get('err') is None
        }
        
    def _parse_meteora_dyn_swap(self, tx: Dict) -> Optional[Dict]:
        """Parse Meteora Dynamic swap - simplified for now"""
        return {
            'dex': 'meteora_dyn',
            'signature': tx['signature'],
            'timestamp': datetime.fromtimestamp(tx['timestamp']),
            'type': 'swap',
            'success': tx.get('err') is None
        }

    @sleep_and_retry
    @limits(calls=10, period=1)
    async def get_enhanced_transactions(
        self,
        signatures: List[str]
    ) -> List[Dict]:
        """Get enhanced transaction data for multiple signatures"""
        
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")
            
        if not signatures:
            return []
            
        # Helius supports batch requests
        batch_size = 100
        all_transactions = []
        
        for i in range(0, len(signatures), batch_size):
            batch = signatures[i:i + batch_size]
            
            try:
                async with self.session.post(
                    f"{self.base_url}/transactions",
                    params={"api-key": self.api_key},
                    json={"transactions": batch}
                ) as response:
                    response.raise_for_status()
                    transactions = await response.json()
                    all_transactions.extend(transactions)
                    
                await asyncio.sleep(1 / self.rate_limit)
                
            except aiohttp.ClientError as e:
                logger.error(f"Error fetching enhanced transactions: {e}")
                raise
                
        return all_transactions