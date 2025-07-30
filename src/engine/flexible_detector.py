from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta, timezone
import operator
from collections import deque
import numpy as np
import logging

from src.services import TokenAgeTracker

logger = logging.getLogger(__name__)


class FlexibleSignalDetector:
    """Signal detector with configurable conditions"""
    
    # Operator mapping
    OPERATORS = {
        'greater_than': operator.gt,
        'greater_than_equal': operator.ge,
        'less_than': operator.lt,
        'less_than_equal': operator.le,
        'equal': operator.eq,
        'not_equal': operator.ne
    }
    
    def __init__(self, strategy_config: Dict, token_tracker: TokenAgeTracker):
        self.conditions = strategy_config.get('conditions', {})
        self.token_tracker = token_tracker
        self.strategy_name = strategy_config.get('name', 'Unknown')
        self.strategy_id = strategy_config.get('id')
        
        # Validate conditions on initialization
        self._validate_conditions()
        
    def _validate_conditions(self):
        """Validate strategy conditions"""
        
        for condition_name, config in self.conditions.items():
            if not isinstance(config, dict):
                raise ValueError(f"Condition {condition_name} must be a dictionary")
                
            if config.get('enabled', False):
                # Check required fields based on condition type
                if 'operator' in config and config['operator'] not in self.OPERATORS:
                    raise ValueError(f"Invalid operator in {condition_name}: {config['operator']}")
                    
                if 'value' not in config and condition_name != 'large_buys':
                    raise ValueError(f"Missing value in {condition_name}")
                    
    async def detect_signals(
        self,
        transactions: List[Dict],
        pool_states: Dict[datetime, Dict],
        token_address: str
    ) -> List[Dict]:
        """Detect signals based on flexible conditions"""
        
        signals = []
        
        # Check token age first (if enabled)
        if not await self._check_token_age(token_address):
            logger.debug(f"Token {token_address} doesn't meet age criteria")
            return []
            
        # Group transactions by time for rolling window
        tx_by_time = self._group_by_time(transactions)
        
        # Get window size from conditions
        window_seconds = self._get_window_seconds()
        
        # Use deque for efficient rolling window
        window = deque()
        
        for timestamp in sorted(tx_by_time.keys()):
            # Add new transactions to window
            window.extend(tx_by_time[timestamp])
            
            # Remove old transactions
            cutoff_time = timestamp - timedelta(seconds=window_seconds)
            while window and window[0]['timestamp'] < cutoff_time:
                window.popleft()
                
            # Get pool state
            pool_state = self._get_closest_pool_state(timestamp, pool_states)
            if not pool_state:
                continue
                
            # Check all conditions
            if await self._check_all_conditions(list(window), pool_state, token_address):
                signal = {
                    'timestamp': timestamp,
                    'token_address': token_address,
                    'transactions': list(window),
                    'pool_state': pool_state,
                    'metrics': self._calculate_metrics(list(window), pool_state),
                    'strategy': self.strategy_name,
                    'strategy_id': self.strategy_id,
                    'conditions_met': self._get_met_conditions(list(window), pool_state)
                }
                signals.append(signal)
                
                # Avoid duplicate signals in close succession
                # Skip next few seconds to prevent multiple signals
                for _ in range(5):
                    if tx_by_time:
                        tx_by_time.pop(min(tx_by_time.keys()), None)
                
        return signals
        
    def _get_window_seconds(self) -> int:
        """Get window size from conditions"""
        # Check volume window first
        vol_window = self.conditions.get('volume_window', {})
        if vol_window.get('enabled') and vol_window.get('window_seconds'):
            return vol_window['window_seconds']
            
        # Check large buys window
        lb_window = self.conditions.get('large_buys', {})
        if lb_window.get('enabled') and lb_window.get('window_seconds'):
            return lb_window['window_seconds']
            
        # Default
        return 30
        
    def _group_by_time(self, transactions: List[Dict]) -> Dict[datetime, List[Dict]]:
        """Group transactions by timestamp"""
        grouped = {}
        for tx in transactions:
            timestamp = tx.get('timestamp') or tx.get('time')
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
                
            if timestamp not in grouped:
                grouped[timestamp] = []
            grouped[timestamp].append(tx)
        return grouped
        
    def _get_closest_pool_state(
        self,
        timestamp: datetime,
        pool_states: Dict[datetime, Dict]
    ) -> Optional[Dict]:
        """Get pool state closest to timestamp"""
        
        if not pool_states:
            return None
            
        # Find closest timestamp
        closest_time = min(pool_states.keys(), key=lambda t: abs((t - timestamp).total_seconds()))
        
        # Only use if within 5 minutes
        if abs((closest_time - timestamp).total_seconds()) <= 300:
            return pool_states[closest_time]
            
        return None
        
    async def _check_token_age(self, token_address: str) -> bool:
        """Check if token meets age criteria"""
        
        age_config = self.conditions.get('token_age', {})
        if not age_config.get('enabled', False):
            return True  # Skip if not enabled
            
        age_hours = await self.token_tracker.get_token_age_hours(token_address)
        if age_hours is None:
            logger.warning(f"Cannot determine age for token {token_address}")
            return False
            
        # Convert to specified unit
        unit = age_config.get('unit', 'hours')
        if unit == 'days':
            age_value = age_hours / 24
        elif unit == 'hours':
            age_value = age_hours
        elif unit == 'minutes':
            age_value = age_hours * 60
        else:
            age_value = age_hours
            
        # Apply operator
        op = self.OPERATORS.get(age_config['operator'], operator.lt)
        result = op(age_value, age_config['value'])
        
        if not result:
            logger.debug(f"Token age {age_value} {unit} doesn't meet condition")
            
        return result
        
    async def _check_all_conditions(
        self,
        window_txs: List[Dict],
        pool_state: Dict,
        token_address: str
    ) -> bool:
        """Check all enabled conditions"""
        
        # Check each condition type
        checks = [
            self._check_liquidity(pool_state),
            self._check_volume(window_txs),
            self._check_market_cap(pool_state),
            self._check_large_buys(window_txs),
            self._check_buy_pressure(window_txs),
            self._check_unique_wallets(window_txs),
            self._check_price_change(pool_state)
        ]
        
        # All enabled conditions must pass
        return all(checks)
        
    def _check_liquidity(self, pool_state: Dict) -> bool:
        """Check liquidity condition"""
        
        liq_config = self.conditions.get('liquidity', {})
        if not liq_config.get('enabled', False):
            return True
            
        liquidity = pool_state.get('liquidity_usd', 0)
        op = self.OPERATORS.get(liq_config['operator'], operator.gt)
        
        return op(liquidity, liq_config['value'])
        
    def _check_volume(self, window_txs: List[Dict]) -> bool:
        """Check volume in window"""
        
        vol_config = self.conditions.get('volume_window', {})
        if not vol_config.get('enabled', False):
            return True
            
        total_volume = sum(tx.get('amount_usd', 0) for tx in window_txs)
        op = self.OPERATORS.get(vol_config['operator'], operator.gte)
        
        return op(total_volume, vol_config['value'])
        
    def _check_market_cap(self, pool_state: Dict) -> bool:
        """Check market cap condition"""
        
        mc_config = self.conditions.get('market_cap', {})
        if not mc_config.get('enabled', False):
            return True
            
        market_cap = pool_state.get('market_cap', float('inf'))
        op = self.OPERATORS.get(mc_config['operator'], operator.lt)
        
        return op(market_cap, mc_config['value'])
        
    def _check_large_buys(self, window_txs: List[Dict]) -> bool:
        """Check large buy conditions"""
        
        lb_config = self.conditions.get('large_buys', {})
        if not lb_config.get('enabled', False):
            return True
            
        large_buys = [
            tx for tx in window_txs
            if tx.get('type') == 'buy' and 
            tx.get('amount_usd', 0) >= lb_config.get('min_amount', 1000)
        ]
        
        return len(large_buys) >= lb_config.get('min_count', 5)
        
    def _check_buy_pressure(self, window_txs: List[Dict]) -> bool:
        """Check buy/sell pressure ratio"""
        
        bp_config = self.conditions.get('buy_pressure', {})
        if not bp_config.get('enabled', False):
            return True
            
        buys = [tx for tx in window_txs if tx.get('type') == 'buy']
        sells = [tx for tx in window_txs if tx.get('type') == 'sell']
        
        if not sells:
            ratio = float('inf') if buys else 0
        else:
            ratio = len(buys) / len(sells)
            
        op = self.OPERATORS.get(bp_config['operator'], operator.gt)
        return op(ratio, bp_config['value'])
        
    def _check_unique_wallets(self, window_txs: List[Dict]) -> bool:
        """Check unique wallet count"""
        
        uw_config = self.conditions.get('unique_wallets', {})
        if not uw_config.get('enabled', False):
            return True
            
        unique_wallets = set(tx.get('wallet_address') for tx in window_txs if tx.get('wallet_address'))
        op = self.OPERATORS.get(uw_config['operator'], operator.gte)
        
        return op(len(unique_wallets), uw_config['value'])
        
    def _check_price_change(self, pool_state: Dict) -> bool:
        """Check price change condition"""
        
        pc_config = self.conditions.get('price_change', {})
        if not pc_config.get('enabled', False):
            return True
            
        # This would need historical price data
        # For now, return True if not available
        price_change = pool_state.get('price_change_percent', 0)
        op = self.OPERATORS.get(pc_config['operator'], operator.gt)
        
        return op(price_change, pc_config['value'])
        
    def _calculate_metrics(self, window_txs: List[Dict], pool_state: Dict) -> Dict:
        """Calculate metrics for signal"""
        
        buy_txs = [tx for tx in window_txs if tx.get('type') == 'buy']
        sell_txs = [tx for tx in window_txs if tx.get('type') == 'sell']
        
        buy_volumes = [tx.get('amount_usd', 0) for tx in buy_txs]
        sell_volumes = [tx.get('amount_usd', 0) for tx in sell_txs]
        
        unique_buyers = set(tx.get('wallet_address') for tx in buy_txs if tx.get('wallet_address'))
        unique_sellers = set(tx.get('wallet_address') for tx in sell_txs if tx.get('wallet_address'))
        
        return {
            'total_transactions': len(window_txs),
            'buy_transactions': len(buy_txs),
            'sell_transactions': len(sell_txs),
            'total_volume': sum(buy_volumes) + sum(sell_volumes),
            'buy_volume': sum(buy_volumes),
            'sell_volume': sum(sell_volumes),
            'buy_sell_ratio': len(buy_txs) / len(sell_txs) if sell_txs else float('inf'),
            'volume_ratio': sum(buy_volumes) / sum(sell_volumes) if sell_volumes else float('inf'),
            'average_buy_size': np.mean(buy_volumes) if buy_volumes else 0,
            'average_sell_size': np.mean(sell_volumes) if sell_volumes else 0,
            'largest_buy': max(buy_volumes) if buy_volumes else 0,
            'largest_sell': max(sell_volumes) if sell_volumes else 0,
            'unique_buyers': len(unique_buyers),
            'unique_sellers': len(unique_sellers),
            'unique_wallets': len(unique_buyers.union(unique_sellers)),
            'liquidity': pool_state.get('liquidity_usd', 0),
            'market_cap': pool_state.get('market_cap', 0),
            'price': pool_state.get('price', 0)
        }
        
    def _get_met_conditions(self, window_txs: List[Dict], pool_state: Dict) -> List[str]:
        """Get list of conditions that were met"""
        
        met_conditions = []
        
        if self._check_liquidity(pool_state):
            met_conditions.append('liquidity')
        if self._check_volume(window_txs):
            met_conditions.append('volume_window')
        if self._check_market_cap(pool_state):
            met_conditions.append('market_cap')
        if self._check_large_buys(window_txs):
            met_conditions.append('large_buys')
        if self._check_buy_pressure(window_txs):
            met_conditions.append('buy_pressure')
        if self._check_unique_wallets(window_txs):
            met_conditions.append('unique_wallets')
            
        return met_conditions