"""Main backtesting engine with realistic trade simulation"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, timezone
import asyncio
import asyncpg
import logging
import numpy as np
import json
import operator
from collections import defaultdict

from src.api import HeliusClient, BirdeyeClient, APICache
from src.services import TokenAgeTracker
from src.strategies import StrategyManager
from src.dex import get_dex_parser, SUPPORTED_DEXES
from src.utils import calculate_trade_metrics, decimal_handler
from .flexible_detector import FlexibleSignalDetector

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Production backtesting engine with realistic execution simulation"""
    
    def __init__(
        self,
        helius_client: HeliusClient,
        birdeye_client: BirdeyeClient,
        db_pool: asyncpg.Pool,
        redis_client: Any,
        config: Optional[Dict] = None
    ):
        self.helius = helius_client
        self.birdeye = birdeye_client
        self.db = db_pool
        self.redis = redis_client
        
        # Default configuration
        self.config = {
            'entry_slippage': 0.02,  # 2%
            'exit_slippage': 0.03,   # 3% (usually higher on exit)
            'trading_fee': 0.0025,    # 0.25% per trade
            'min_liquidity': 5000,    # Minimum pool liquidity to trade
            'max_position_size': 0.10, # Max 10% of pool liquidity
            'stop_loss': 0.10,        # 10% stop loss
            'take_profit': 0.50,      # 50% take profit
            'hold_duration': 300,     # 5 minutes default hold
            'exit_strategy': 'time_based',  # time_based, stop_loss_take_profit, trailing_stop
            'execution_delay': 2,     # 2 seconds execution delay
            'max_concurrent_positions': 10
        }
        
        if config:
            self.config.update(config)
            
        # Initialize services
        self.token_tracker = TokenAgeTracker(helius_client, birdeye_client, db_pool, redis_client)
        self.strategy_manager = StrategyManager(db_pool)
        self.cache = APICache()
        
    async def run_backtest(
        self,
        strategy_id: int,
        token_addresses: List[str],
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 10000
    ) -> Dict[str, Any]:
        """Run comprehensive backtest for a strategy"""
        
        logger.info(f"Starting backtest for strategy {strategy_id}")
        
        # Load strategy
        strategy = await self.strategy_manager.get_strategy(strategy_id)
        if not strategy:
            raise ValueError(f"Strategy {strategy_id} not found")
            
        # Create backtest record
        backtest_id = await self._create_backtest_record(
            strategy_id,
            start_date,
            end_date
        )
        
        try:
            # Update status
            await self._update_backtest_status(backtest_id, 'running')
            
            # Initialize detector
            detector = FlexibleSignalDetector(strategy, self.token_tracker)
            
            # Process each token
            all_signals = []
            all_trades = []
            
            for i, token_address in enumerate(token_addresses):
                logger.info(f"Processing token {i+1}/{len(token_addresses)}: {token_address}")
                
                # Check token age first
                if not await self._is_token_eligible(token_address, start_date, strategy):
                    logger.info(f"Token {token_address} not eligible, skipping")
                    continue
                    
                # Fetch data
                token_data = await self._fetch_token_data(
                    token_address,
                    start_date,
                    end_date
                )
                
                if not token_data['transactions']:
                    logger.warning(f"No transactions found for {token_address}")
                    continue
                    
                # Detect signals
                signals = await detector.detect_signals(
                    token_data['transactions'],
                    token_data['pool_states'],
                    token_address
                )
                
                all_signals.extend(signals)
                
                # Simulate trades
                trades = await self._simulate_trades(
                    signals,
                    token_address,
                    token_data['price_data']
                )
                
                all_trades.extend(trades)
                
            # Calculate portfolio metrics
            portfolio_metrics = self._calculate_portfolio_metrics(
                all_trades,
                initial_capital
            )
            
            # Store results
            await self._store_backtest_results(
                backtest_id,
                all_signals,
                all_trades,
                portfolio_metrics
            )
            
            # Update status
            await self._update_backtest_status(backtest_id, 'completed')
            
            logger.info(f"Backtest {backtest_id} completed successfully")
            
            return {
                'backtest_id': backtest_id,
                'strategy': strategy,
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                },
                'tokens_analyzed': len(token_addresses),
                'total_signals': len(all_signals),
                'total_trades': len(all_trades),
                'metrics': portfolio_metrics,
                'summary': self._generate_summary(all_trades, portfolio_metrics)
            }
            
        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            await self._update_backtest_status(backtest_id, 'failed', str(e))
            raise
            
    async def _fetch_token_data(
        self,
        token_address: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Fetch all required data for a token"""
        
        # Fetch transactions from database first
        transactions = await self._fetch_transactions_from_db(
            token_address,
            start_date,
            end_date
        )
        
        # If not enough data, fetch from API
        if len(transactions) < 100:  # Arbitrary threshold
            logger.info(f"Fetching additional data from API for {token_address}")
            api_transactions = await self.helius.get_token_transactions(
                token_address,
                start_date,
                end_date
            )
            
            # Parse and store transactions
            parsed_txs = await self._parse_and_store_transactions(
                api_transactions,
                token_address
            )
            transactions.extend(parsed_txs)
            
        # Fetch pool states
        pool_states = await self._fetch_pool_states(
            token_address,
            start_date,
            end_date
        )
        
        # Fetch price data for exit simulation
        price_data = await self._fetch_price_data(
            token_address,
            start_date,
            end_date
        )
        
        return {
            'transactions': transactions,
            'pool_states': pool_states,
            'price_data': price_data
        }
        
    async def _fetch_transactions_from_db(
        self,
        token_address: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """Fetch transactions from database"""
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    time as timestamp,
                    signature,
                    type,
                    amount_token,
                    amount_usd,
                    wallet_address,
                    dex,
                    success
                FROM transactions
                WHERE token_address = $1
                AND time BETWEEN $2 AND $3
                AND success = true
                ORDER BY time
            """, token_address, start_date, end_date)
            
        return [dict(row) for row in rows]
        
    async def _parse_and_store_transactions(
        self,
        raw_transactions: List[Dict],
        token_address: str
    ) -> List[Dict]:
        """Parse and store transactions from API"""
        
        parsed_txs = []
        
        for tx in raw_transactions:
            # Determine DEX
            dex_parser = None
            for program_id in SUPPORTED_DEXES.values():
                if any(ix.get('programId') == program_id for ix in tx.get('instructions', [])):
                    dex_parser = get_dex_parser(program_id)
                    break
                    
            if not dex_parser:
                continue
                
            # Parse transaction
            parsed = await self.helius.parse_transaction_details(tx)
            if parsed and parsed.get('token_address') == token_address:
                parsed_txs.append(parsed)
                
                # Store in database
                await self._store_transaction(parsed)
                
        return parsed_txs
        
    async def _fetch_pool_states(
        self,
        token_address: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[datetime, Dict]:
        """Fetch pool states from database"""
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT 
                    time,
                    dex,
                    liquidity_usd,
                    market_cap,
                    price
                FROM pool_states
                WHERE token_address = $1
                AND time BETWEEN $2 AND $3
                ORDER BY time
            """, token_address, start_date, end_date)
            
        # Group by time
        pool_states = {}
        for row in rows:
            pool_states[row['time']] = dict(row)
            
        return pool_states
        
    async def _fetch_price_data(
        self,
        token_address: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[datetime, float]:
        """Fetch minute-level price data"""
        
        # Try cache first
        cache_key = f"price_data:{token_address}:{start_date.date()}:{end_date.date()}"
        cached = await self.redis.get(cache_key)
        if cached:
            return {datetime.fromisoformat(k): v for k, v in cached.items()}
            
        # Fetch from Birdeye
        ohlcv_data = await self.birdeye.get_ohlcv(
            token_address,
            int(start_date.timestamp()),
            int(end_date.timestamp()),
            interval="1m"
        )
        
        # Convert to price dict
        price_data = {}
        for candle in ohlcv_data:
            timestamp = datetime.fromtimestamp(candle['unixTime'], tz=timezone.utc)
            price_data[timestamp] = candle['c']  # Close price
            
        # Cache for future use
        await self.redis.setex(
            cache_key,
            3600,  # 1 hour cache
            {k.isoformat(): v for k, v in price_data.items()}
        )
        
        return price_data
        
    async def _simulate_trades(
        self,
        signals: List[Dict],
        token_address: str,
        price_data: Dict[datetime, float]
    ) -> List[Dict]:
        """Simulate trade execution with realistic conditions"""
        
        trades = []
        
        for signal in signals:
            trade = await self._simulate_single_trade(
                signal,
                token_address,
                price_data
            )
            
            if trade:
                trades.append(trade)
                
        return trades
        
    async def _simulate_single_trade(
        self,
        signal: Dict,
        token_address: str,
        price_data: Dict[datetime, float]
    ) -> Optional[Dict]:
        """Simulate a single trade with slippage and fees"""
        
        entry_time = signal['timestamp'] + timedelta(seconds=self.config['execution_delay'])
        
        # Get entry price with slippage
        base_price = signal['pool_state'].get('price', 0)
        if base_price == 0:
            return None
            
        entry_price = base_price * (1 + self.config['entry_slippage'])
        
        # Check liquidity constraints
        liquidity = signal['pool_state'].get('liquidity_usd', 0)
        if liquidity < self.config['min_liquidity']:
            return None
            
        # Calculate position size (respecting max % of pool)
        position_size = min(
            1000,  # Default $1000 position
            liquidity * self.config['max_position_size']
        )
        
        # Determine exit
        exit_time, exit_price, exit_reason = await self._determine_exit(
            entry_time,
            entry_price,
            price_data
        )
        
        if not exit_price:
            return None
            
        # Apply exit slippage
        exit_price = exit_price * (1 - self.config['exit_slippage'])
        
        # Calculate P&L including fees
        gross_pnl_percent = ((exit_price - entry_price) / entry_price) * 100
        total_fees = (self.config['trading_fee'] * 2) * 100  # Entry + exit fees
        net_pnl_percent = gross_pnl_percent - total_fees
        
        return {
            'signal_time': signal['timestamp'],
            'entry_time': entry_time,
            'entry_price': entry_price,
            'exit_time': exit_time,
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'gross_pnl_percent': gross_pnl_percent,
            'net_pnl_percent': net_pnl_percent,
            'pnl_usd': position_size * net_pnl_percent / 100,
            'position_size': position_size,
            'hold_duration': exit_time - entry_time,
            'token_address': token_address,
            'strategy': signal.get('strategy'),
            'signal_metrics': signal.get('metrics', {}),
            'entry_liquidity': liquidity,
            'entry_market_cap': signal['pool_state'].get('market_cap', 0)
        }
        
    async def _determine_exit(
        self,
        entry_time: datetime,
        entry_price: float,
        price_data: Dict[datetime, float]
    ) -> Tuple[datetime, float, str]:
        """Determine exit time and price based on strategy"""
        
        exit_strategy = self.config['exit_strategy']
        
        if exit_strategy == 'time_based':
            return await self._time_based_exit(entry_time, price_data)
        elif exit_strategy == 'stop_loss_take_profit':
            return await self._stop_loss_take_profit_exit(entry_time, entry_price, price_data)
        elif exit_strategy == 'trailing_stop':
            return await self._trailing_stop_exit(entry_time, entry_price, price_data)
        else:
            # Default to time-based
            return await self._time_based_exit(entry_time, price_data)
            
    async def _time_based_exit(
        self,
        entry_time: datetime,
        price_data: Dict[datetime, float]
    ) -> Tuple[datetime, float, str]:
        """Simple time-based exit"""
        
        exit_time = entry_time + timedelta(seconds=self.config['hold_duration'])
        
        # Find closest price
        if not price_data:
            return exit_time, None, 'no_price_data'
            
        closest_time = min(
            price_data.keys(),
            key=lambda t: abs((t - exit_time).total_seconds())
        )
        
        # Only use if within 5 minutes
        if abs((closest_time - exit_time).total_seconds()) <= 300:
            return exit_time, price_data[closest_time], 'time_based'
            
        return exit_time, None, 'no_price_data'
        
    async def _stop_loss_take_profit_exit(
        self,
        entry_time: datetime,
        entry_price: float,
        price_data: Dict[datetime, float]
    ) -> Tuple[datetime, float, str]:
        """Exit on stop loss or take profit"""
        
        stop_loss_price = entry_price * (1 - self.config['stop_loss'])
        take_profit_price = entry_price * (1 + self.config['take_profit'])
        max_hold_time = entry_time + timedelta(seconds=self.config['hold_duration'] * 2)
        
        # Check each minute
        current_time = entry_time
        while current_time < max_hold_time:
            if current_time in price_data:
                current_price = price_data[current_time]
                
                if current_price <= stop_loss_price:
                    return current_time, stop_loss_price, 'stop_loss'
                elif current_price >= take_profit_price:
                    return current_time, take_profit_price, 'take_profit'
                    
            current_time += timedelta(minutes=1)
            
        # Time-based exit if no stop/target hit
        return await self._time_based_exit(entry_time, price_data)
        
    async def _trailing_stop_exit(
        self,
        entry_time: datetime,
        entry_price: float,
        price_data: Dict[datetime, float]
    ) -> Tuple[datetime, float, str]:
        """Exit with trailing stop loss"""
        
        trailing_stop_percent = self.config.get('trailing_stop_percent', 0.05)  # 5%
        max_hold_time = entry_time + timedelta(seconds=self.config['hold_duration'] * 2)
        
        highest_price = entry_price
        current_time = entry_time
        
        while current_time < max_hold_time:
            if current_time in price_data:
                current_price = price_data[current_time]
                
                # Update highest price
                if current_price > highest_price:
                    highest_price = current_price
                    
                # Check trailing stop
                stop_price = highest_price * (1 - trailing_stop_percent)
                if current_price <= stop_price:
                    return current_time, current_price, 'trailing_stop'
                    
            current_time += timedelta(minutes=1)
            
        # Time-based exit if stop not hit
        return await self._time_based_exit(entry_time, price_data)
        
    def _calculate_portfolio_metrics(
        self,
        trades: List[Dict],
        initial_capital: float
    ) -> Dict[str, Any]:
        """Calculate comprehensive portfolio metrics"""
        
        if not trades:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_return': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'profit_factor': 0
            }
            
        # Sort trades by entry time
        trades.sort(key=lambda x: x['entry_time'])
        
        # Calculate trade metrics
        trade_metrics = calculate_trade_metrics(trades)
        
        # Calculate portfolio equity curve
        equity = [initial_capital]
        current_capital = initial_capital
        
        for trade in trades:
            pnl_usd = trade.get('pnl_usd', 0)
            current_capital += pnl_usd
            equity.append(current_capital)
            
        equity_array = np.array(equity)
        
        # Additional portfolio metrics
        trade_metrics['initial_capital'] = initial_capital
        trade_metrics['final_capital'] = current_capital
        trade_metrics['total_return_usd'] = current_capital - initial_capital
        trade_metrics['total_return_percent'] = ((current_capital - initial_capital) / initial_capital) * 100
        trade_metrics['max_equity'] = np.max(equity_array)
        trade_metrics['min_equity'] = np.min(equity_array)
        
        # Win/loss streaks
        trade_metrics['max_win_streak'] = self._calculate_max_streak(trades, True)
        trade_metrics['max_loss_streak'] = self._calculate_max_streak(trades, False)
        
        # Time-based metrics
        if trades:
            total_duration = (trades[-1]['exit_time'] - trades[0]['entry_time']).total_seconds() / 3600
            trade_metrics['avg_trades_per_day'] = len(trades) / (total_duration / 24) if total_duration > 0 else 0
            
        return trade_metrics
        
    def _calculate_max_streak(self, trades: List[Dict], wins: bool) -> int:
        """Calculate maximum winning or losing streak"""
        
        max_streak = 0
        current_streak = 0
        
        for trade in trades:
            is_win = trade.get('net_pnl_percent', 0) > 0
            
            if (wins and is_win) or (not wins and not is_win):
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
                
        return max_streak
        
    async def _is_token_eligible(
        self,
        token_address: str,
        backtest_start: datetime,
        strategy: Dict
    ) -> bool:
        """Check if token meets strategy eligibility criteria"""
        
        # Get token creation time
        creation_time = await self.token_tracker.get_token_creation_time(token_address)
        if not creation_time:
            return False
            
        # Check if token existed before backtest start
        if creation_time > backtest_start:
            return False
            
        # Check age requirements from strategy
        age_condition = strategy.get('conditions', {}).get('token_age', {})
        if age_condition.get('enabled'):
            age_at_start = (backtest_start - creation_time).total_seconds() / 3600
            
            # Convert to required unit
            unit = age_condition.get('unit', 'hours')
            if unit == 'days':
                age_value = age_at_start / 24
            elif unit == 'minutes':
                age_value = age_at_start * 60
            else:
                age_value = age_at_start
                
            # Check operator
            from .flexible_detector import FlexibleSignalDetector
            op = FlexibleSignalDetector.OPERATORS.get(
                age_condition.get('operator', 'less_than'),
                operator.lt
            )
            
            if not op(age_value, age_condition.get('value', 0)):
                return False
                
        return True
        
    async def _create_backtest_record(
        self,
        strategy_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> int:
        """Create backtest record in database"""
        
        async with self.db.acquire() as conn:
            backtest_id = await conn.fetchval("""
                INSERT INTO backtest_results (
                    strategy_id,
                    date_range,
                    status,
                    created_at
                )
                VALUES ($1, $2, 'pending', NOW())
                RETURNING id
            """, strategy_id, (start_date, end_date))
            
        return backtest_id
        
    async def _update_backtest_status(
        self,
        backtest_id: int,
        status: str,
        error_message: Optional[str] = None
    ):
        """Update backtest status"""
        
        async with self.db.acquire() as conn:
            if status == 'completed':
                await conn.execute("""
                    UPDATE backtest_results
                    SET status = $2, completed_at = NOW()
                    WHERE id = $1
                """, backtest_id, status)
            elif status == 'failed':
                await conn.execute("""
                    UPDATE backtest_results
                    SET status = $2, error_message = $3, completed_at = NOW()
                    WHERE id = $1
                """, backtest_id, status, error_message)
            else:
                await conn.execute("""
                    UPDATE backtest_results
                    SET status = $2
                    WHERE id = $1
                """, backtest_id, status)
                
    async def _store_transaction(self, parsed_tx: Dict):
        """Store parsed transaction in database"""
        
        async with self.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO transactions (
                    time, signature, token_address, dex, type,
                    amount_token, amount_usd, wallet_address,
                    block_slot, success
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ON CONFLICT (signature) DO NOTHING
            """,
                parsed_tx['timestamp'],
                parsed_tx['signature'],
                parsed_tx['token_address'],
                parsed_tx['dex'],
                parsed_tx.get('type', 'swap'),
                parsed_tx.get('token_amount'),
                parsed_tx.get('amount_usd'),
                parsed_tx.get('wallet_address'),
                parsed_tx.get('slot'),
                parsed_tx.get('success', True)
            )
            
    async def _store_backtest_results(
        self,
        backtest_id: int,
        signals: List[Dict],
        trades: List[Dict],
        metrics: Dict
    ):
        """Store backtest results in database"""
        
        async with self.db.acquire() as conn:
            # Update backtest summary
            await conn.execute("""
                UPDATE backtest_results
                SET 
                    total_signals = $2,
                    trades_executed = $3,
                    win_rate = $4,
                    total_pnl = $5,
                    sharpe_ratio = $6,
                    max_drawdown = $7
                WHERE id = $1
            """,
                backtest_id,
                len(signals),
                len(trades),
                metrics.get('win_rate', 0),
                metrics.get('total_return_percent', 0),
                metrics.get('sharpe_ratio', 0),
                metrics.get('max_drawdown', 0)
            )
            
            # Store individual trades
            for trade in trades:
                await conn.execute("""
                    INSERT INTO backtest_trades (
                        backtest_id, token_address, signal_time,
                        entry_time, entry_price, exit_time, exit_price,
                        pnl_percent, pnl_usd, hold_duration,
                        exit_reason, signal_metrics
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                    backtest_id,
                    trade['token_address'],
                    trade['signal_time'],
                    trade['entry_time'],
                    trade['entry_price'],
                    trade['exit_time'],
                    trade['exit_price'],
                    trade['net_pnl_percent'],
                    trade['pnl_usd'],
                    trade['hold_duration'],
                    trade['exit_reason'],
                    json.dumps(trade.get('signal_metrics', {}))
                )
                
    def _generate_summary(self, trades: List[Dict], metrics: Dict) -> str:
        """Generate human-readable summary"""
        
        if not trades:
            return "No trades executed"
            
        summary_parts = [
            f"Executed {len(trades)} trades",
            f"Win rate: {metrics['win_rate']:.1f}%",
            f"Total return: {metrics['total_return_percent']:.2f}%",
            f"Sharpe ratio: {metrics['sharpe_ratio']:.2f}",
            f"Max drawdown: {metrics['max_drawdown']:.1f}%",
            f"Profit factor: {metrics['profit_factor']:.2f}"
        ]
        
        return " | ".join(summary_parts)