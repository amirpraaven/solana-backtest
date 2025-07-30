from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import deque
import numpy as np
import logging

logger = logging.getLogger(__name__)


class SignalDetector:
    """Basic signal detector with fixed thresholds"""
    
    def __init__(
        self,
        window_seconds: int = 30,
        min_large_buys: int = 5,
        large_buy_threshold: float = 1000,
        min_volume: float = 5000,
        min_liquidity: float = 40000,
        max_market_cap: float = 400000
    ):
        self.window_seconds = window_seconds
        self.min_large_buys = min_large_buys
        self.large_buy_threshold = large_buy_threshold
        self.min_volume = min_volume
        self.min_liquidity = min_liquidity
        self.max_market_cap = max_market_cap
        
    def detect_signals(
        self,
        transactions: List[Dict],
        pool_states: Dict[datetime, Dict],
        token_address: str
    ) -> List[Dict]:
        """Detect signals based on fixed criteria"""
        
        signals = []
        
        # Sort transactions by time
        sorted_txs = sorted(transactions, key=lambda x: x.get('timestamp', x.get('time')))
        
        # Use sliding window
        window = deque()
        
        for tx in sorted_txs:
            tx_time = tx.get('timestamp', tx.get('time'))
            if isinstance(tx_time, str):
                tx_time = datetime.fromisoformat(tx_time)
                
            # Add to window
            window.append(tx)
            
            # Remove old transactions
            cutoff = tx_time - timedelta(seconds=self.window_seconds)
            while window and window[0].get('timestamp', window[0].get('time')) < cutoff:
                window.popleft()
                
            # Get current pool state
            pool_state = self._get_pool_state_at_time(tx_time, pool_states)
            if not pool_state:
                continue
                
            # Check signal conditions
            if self._check_signal_conditions(list(window), pool_state):
                signal = {
                    'timestamp': tx_time,
                    'token_address': token_address,
                    'pool_state': pool_state,
                    'window_transactions': len(window),
                    'metrics': self._calculate_window_metrics(list(window))
                }
                signals.append(signal)
                
                # Clear window to avoid duplicate signals
                window.clear()
                
        return signals
        
    def _get_pool_state_at_time(
        self,
        timestamp: datetime,
        pool_states: Dict[datetime, Dict]
    ) -> Optional[Dict]:
        """Get pool state at or near timestamp"""
        
        if not pool_states:
            return None
            
        # Find closest timestamp
        closest = min(pool_states.keys(), key=lambda t: abs((t - timestamp).total_seconds()))
        
        # Only use if within 5 minutes
        if abs((closest - timestamp).total_seconds()) <= 300:
            return pool_states[closest]
            
        return None
        
    def _check_signal_conditions(
        self,
        window_txs: List[Dict],
        pool_state: Dict
    ) -> bool:
        """Check if window meets signal conditions"""
        
        # Check liquidity
        if pool_state.get('liquidity_usd', 0) < self.min_liquidity:
            return False
            
        # Check market cap
        if pool_state.get('market_cap', float('inf')) > self.max_market_cap:
            return False
            
        # Calculate window metrics
        metrics = self._calculate_window_metrics(window_txs)
        
        # Check volume
        if metrics['total_volume'] < self.min_volume:
            return False
            
        # Check large buys
        if metrics['large_buy_count'] < self.min_large_buys:
            return False
            
        return True
        
    def _calculate_window_metrics(self, window_txs: List[Dict]) -> Dict:
        """Calculate metrics for transaction window"""
        
        buy_txs = [tx for tx in window_txs if tx.get('type') == 'buy']
        sell_txs = [tx for tx in window_txs if tx.get('type') == 'sell']
        
        large_buys = [
            tx for tx in buy_txs
            if tx.get('amount_usd', 0) >= self.large_buy_threshold
        ]
        
        total_volume = sum(tx.get('amount_usd', 0) for tx in window_txs)
        buy_volume = sum(tx.get('amount_usd', 0) for tx in buy_txs)
        sell_volume = sum(tx.get('amount_usd', 0) for tx in sell_txs)
        
        return {
            'total_volume': total_volume,
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'buy_count': len(buy_txs),
            'sell_count': len(sell_txs),
            'large_buy_count': len(large_buys),
            'large_buy_volume': sum(tx.get('amount_usd', 0) for tx in large_buys),
            'buy_sell_ratio': len(buy_txs) / len(sell_txs) if sell_txs else float('inf'),
            'volume_ratio': buy_volume / sell_volume if sell_volume > 0 else float('inf')
        }