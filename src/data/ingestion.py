"""Data ingestion and storage pipeline"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
import asyncio
import asyncpg
import logging
from collections import defaultdict

from src.api import HeliusClient, BirdeyeClient
from src.dex import get_dex_parser, SUPPORTED_DEXES
from .validation import DataValidator

logger = logging.getLogger(__name__)


class DataIngestionPipeline:
    """Pipeline for ingesting and storing blockchain data"""
    
    def __init__(
        self,
        helius_client: HeliusClient,
        birdeye_client: BirdeyeClient,
        db_pool: asyncpg.Pool,
        batch_size: int = 1000
    ):
        self.helius = helius_client
        self.birdeye = birdeye_client
        self.db = db_pool
        self.batch_size = batch_size
        self.validator = DataValidator()
        
    async def ingest_token_data(
        self,
        token_address: str,
        start_date: datetime,
        end_date: datetime,
        fetch_transactions: bool = True,
        fetch_pool_states: bool = True,
        fetch_metadata: bool = True
    ) -> Dict[str, Any]:
        """Ingest all data for a token"""
        
        logger.info(f"Starting data ingestion for {token_address}")
        
        results = {
            'token_address': token_address,
            'start_date': start_date,
            'end_date': end_date,
            'transactions': {'fetched': 0, 'stored': 0, 'errors': 0},
            'pool_states': {'fetched': 0, 'stored': 0, 'errors': 0},
            'metadata': {'fetched': False, 'stored': False}
        }
        
        try:
            # Fetch and store token metadata
            if fetch_metadata:
                metadata_result = await self._ingest_token_metadata(token_address)
                results['metadata'] = metadata_result
                
            # Fetch and store transactions
            if fetch_transactions:
                tx_result = await self._ingest_transactions(
                    token_address,
                    start_date,
                    end_date
                )
                results['transactions'] = tx_result
                
            # Fetch and store pool states
            if fetch_pool_states:
                pool_result = await self._ingest_pool_states(
                    token_address,
                    start_date,
                    end_date
                )
                results['pool_states'] = pool_result
                
        except Exception as e:
            logger.error(f"Error in data ingestion: {e}")
            results['error'] = str(e)
            
        return results
        
    async def _ingest_token_metadata(self, token_address: str) -> Dict:
        """Ingest token metadata"""
        
        result = {'fetched': False, 'stored': False, 'errors': []}
        
        try:
            # Fetch from Birdeye
            async with self.birdeye:
                token_data = await self.birdeye.get_token_overview(token_address)
                creation_info = await self.birdeye.get_token_creation_info(token_address)
                
            if not token_data:
                result['errors'].append("No token data found")
                return result
                
            # Prepare metadata
            metadata = {
                'token_address': token_address,
                'name': token_data.get('name'),
                'symbol': token_data.get('symbol'),
                'decimals': token_data.get('decimals', 9),
                'total_supply': token_data.get('supply'),
                'created_at': datetime.fromtimestamp(
                    creation_info.get('createdAt', 0),
                    tz=timezone.utc
                ) if creation_info else None
            }
            
            # Validate
            errors = self.validator.validate_token_metadata(metadata)
            if errors:
                result['errors'].extend(errors)
                return result
                
            result['fetched'] = True
            
            # Store in database
            async with self.db.acquire() as conn:
                await conn.execute("""
                    INSERT INTO token_metadata (
                        token_address, name, symbol, decimals,
                        created_at, total_supply, updated_at
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, NOW())
                    ON CONFLICT (token_address)
                    DO UPDATE SET
                        name = EXCLUDED.name,
                        symbol = EXCLUDED.symbol,
                        decimals = EXCLUDED.decimals,
                        total_supply = EXCLUDED.total_supply,
                        updated_at = NOW()
                """,
                    metadata['token_address'],
                    metadata['name'],
                    metadata['symbol'],
                    metadata['decimals'],
                    metadata['created_at'],
                    metadata['total_supply']
                )
                
            result['stored'] = True
            
        except Exception as e:
            logger.error(f"Error ingesting metadata: {e}")
            result['errors'].append(str(e))
            
        return result
        
    async def _ingest_transactions(
        self,
        token_address: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """Ingest transactions for a token"""
        
        result = {'fetched': 0, 'stored': 0, 'errors': 0, 'validation_errors': []}
        
        try:
            # Fetch transactions from Helius
            async with self.helius:
                raw_transactions = await self.helius.get_token_transactions(
                    token_address,
                    start_date,
                    end_date,
                    tx_type="SWAP"
                )
                
            result['fetched'] = len(raw_transactions)
            logger.info(f"Fetched {len(raw_transactions)} transactions")
            
            # Process in batches
            for i in range(0, len(raw_transactions), self.batch_size):
                batch = raw_transactions[i:i + self.batch_size]
                
                # Parse transactions
                parsed_txs = await self._parse_transaction_batch(batch, token_address)
                
                # Validate
                valid_txs = []
                for tx in parsed_txs:
                    errors = self.validator.validate_transaction(tx)
                    if errors:
                        result['validation_errors'].append({
                            'signature': tx.get('signature'),
                            'errors': errors
                        })
                        result['errors'] += 1
                    else:
                        valid_txs.append(self.validator.sanitize_transaction(tx))
                        
                # Store valid transactions
                if valid_txs:
                    stored = await self._store_transactions(valid_txs)
                    result['stored'] += stored
                    
        except Exception as e:
            logger.error(f"Error ingesting transactions: {e}")
            result['error'] = str(e)
            
        return result
        
    async def _parse_transaction_batch(
        self,
        raw_transactions: List[Dict],
        token_address: str
    ) -> List[Dict]:
        """Parse a batch of raw transactions"""
        
        parsed_txs = []
        
        # Get enhanced transaction data
        signatures = [tx['signature'] for tx in raw_transactions]
        enhanced_txs = await self.helius.get_enhanced_transactions(signatures)
        
        # Create lookup map
        enhanced_map = {tx['signature']: tx for tx in enhanced_txs}
        
        for raw_tx in raw_transactions:
            signature = raw_tx['signature']
            enhanced = enhanced_map.get(signature, raw_tx)
            
            # Determine DEX
            dex_parser = None
            dex_name = None
            
            for dex, program_id in SUPPORTED_DEXES.items():
                if any(ix.get('programId') == program_id 
                      for ix in enhanced.get('instructions', [])):
                    dex_parser = get_dex_parser(program_id)
                    dex_name = dex
                    break
                    
            if not dex_parser:
                continue
                
            # Parse transaction
            try:
                parsed = dex_parser.parse_swap(enhanced)
                if parsed and parsed.get('token_address') == token_address:
                    parsed['dex'] = dex_name
                    parsed_txs.append(parsed)
            except Exception as e:
                logger.error(f"Error parsing transaction {signature}: {e}")
                
        return parsed_txs
        
    async def _store_transactions(self, transactions: List[Dict]) -> int:
        """Store transactions in database"""
        
        stored = 0
        
        async with self.db.acquire() as conn:
            # Use COPY for bulk insert
            columns = [
                'time', 'signature', 'token_address', 'dex', 'type',
                'amount_token', 'amount_usd', 'wallet_address',
                'block_slot', 'success'
            ]
            
            # Prepare data
            records = []
            for tx in transactions:
                record = (
                    tx.get('timestamp', tx.get('time')),
                    tx.get('signature'),
                    tx.get('token_address'),
                    tx.get('dex'),
                    tx.get('type', 'swap'),
                    tx.get('amount_token') or tx.get('token_amount'),
                    tx.get('amount_usd'),
                    tx.get('wallet_address'),
                    tx.get('block_slot') or tx.get('slot'),
                    tx.get('success', True)
                )
                records.append(record)
                
            # Bulk insert
            try:
                result = await conn.copy_records_to_table(
                    'transactions',
                    records=records,
                    columns=columns
                )
                stored = len(records)
            except asyncpg.UniqueViolationError:
                # Fall back to individual inserts for duplicates
                for record in records:
                    try:
                        await conn.execute(f"""
                            INSERT INTO transactions ({', '.join(columns)})
                            VALUES ({', '.join(f'${i+1}' for i in range(len(columns)))})
                            ON CONFLICT (signature) DO NOTHING
                        """, *record)
                        stored += 1
                    except Exception as e:
                        logger.error(f"Error storing transaction: {e}")
                        
        return stored
        
    async def _ingest_pool_states(
        self,
        token_address: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """Ingest pool state data"""
        
        result = {'fetched': 0, 'stored': 0, 'errors': 0}
        
        try:
            # Fetch OHLCV data from Birdeye
            async with self.birdeye:
                ohlcv_data = await self.birdeye.get_ohlcv(
                    token_address,
                    int(start_date.timestamp()),
                    int(end_date.timestamp()),
                    interval="5m"  # 5-minute intervals
                )
                
            result['fetched'] = len(ohlcv_data)
            
            # Get pool information for each DEX
            # This is simplified - in production you'd fetch actual pool data
            pool_states = []
            
            for candle in ohlcv_data:
                timestamp = datetime.fromtimestamp(
                    candle['unixTime'],
                    tz=timezone.utc
                )
                
                # Create pool state record
                # In production, you'd fetch actual liquidity data per DEX
                state = {
                    'time': timestamp,
                    'token_address': token_address,
                    'dex': 'aggregate',  # Simplified - would be per DEX
                    'liquidity_usd': candle.get('l', 0) * candle.get('c', 0),
                    'market_cap': candle.get('mc', 0),
                    'price': candle.get('c', 0)
                }
                
                # Validate
                errors = self.validator.validate_pool_state(state)
                if not errors:
                    pool_states.append(state)
                else:
                    result['errors'] += 1
                    
            # Store pool states
            if pool_states:
                stored = await self._store_pool_states(pool_states)
                result['stored'] = stored
                
        except Exception as e:
            logger.error(f"Error ingesting pool states: {e}")
            result['error'] = str(e)
            
        return result
        
    async def _store_pool_states(self, pool_states: List[Dict]) -> int:
        """Store pool states in database"""
        
        stored = 0
        
        async with self.db.acquire() as conn:
            for state in pool_states:
                try:
                    await conn.execute("""
                        INSERT INTO pool_states (
                            time, token_address, dex,
                            liquidity_usd, market_cap, price
                        )
                        VALUES ($1, $2, $3, $4, $5, $6)
                        ON CONFLICT (token_address, dex, time) DO UPDATE SET
                            liquidity_usd = EXCLUDED.liquidity_usd,
                            market_cap = EXCLUDED.market_cap,
                            price = EXCLUDED.price
                    """,
                        state['time'],
                        state['token_address'],
                        state['dex'],
                        state.get('liquidity_usd'),
                        state.get('market_cap'),
                        state.get('price')
                    )
                    stored += 1
                except Exception as e:
                    logger.error(f"Error storing pool state: {e}")
                    
        return stored
        
    async def ingest_multiple_tokens(
        self,
        token_addresses: List[str],
        start_date: datetime,
        end_date: datetime,
        max_concurrent: int = 5
    ) -> Dict[str, Any]:
        """Ingest data for multiple tokens concurrently"""
        
        results = {
            'total_tokens': len(token_addresses),
            'successful': 0,
            'failed': 0,
            'token_results': {}
        }
        
        # Process in batches to avoid overwhelming APIs
        for i in range(0, len(token_addresses), max_concurrent):
            batch = token_addresses[i:i + max_concurrent]
            
            tasks = [
                self.ingest_token_data(token, start_date, end_date)
                for token in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for token, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    results['failed'] += 1
                    results['token_results'][token] = {'error': str(result)}
                else:
                    results['successful'] += 1
                    results['token_results'][token] = result
                    
        return results