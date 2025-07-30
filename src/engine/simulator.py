"""Trade execution simulator with realistic market conditions"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
import logging

logger = logging.getLogger(__name__)


class TradeSimulator:
    """Simulate realistic trade execution"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = {
            'base_slippage': 0.02,      # 2% base slippage
            'size_impact': 0.001,       # 0.1% per $1000 traded
            'volatility_multiplier': 2,  # Slippage multiplier during high volatility
            'min_fill_rate': 0.5,        # Minimum fill rate (50%)
            'max_fill_rate': 1.0,        # Maximum fill rate (100%)
            'network_delay_ms': 100,     # Network delay in milliseconds
            'block_time_ms': 400,        # Solana block time
        }
        if config:
            self.config.update(config)
            
    def simulate_entry(
        self,
        signal_price: float,
        size_usd: float,
        liquidity_usd: float,
        volatility: float = 0.02,
        is_market_order: bool = True
    ) -> Dict:
        """Simulate trade entry with realistic conditions"""
        
        # Calculate size impact
        size_impact = self._calculate_size_impact(size_usd, liquidity_usd)
        
        # Calculate volatility impact
        vol_impact = volatility * self.config['volatility_multiplier']
        
        # Total slippage
        total_slippage = self.config['base_slippage'] + size_impact + vol_impact
        
        # Apply slippage (worse price for buyer)
        executed_price = signal_price * (1 + total_slippage)
        
        # Calculate fill rate based on liquidity
        fill_rate = self._calculate_fill_rate(size_usd, liquidity_usd)
        
        # Actual executed size
        executed_size = size_usd * fill_rate
        
        return {
            'executed_price': executed_price,
            'executed_size': executed_size,
            'fill_rate': fill_rate,
            'total_slippage': total_slippage,
            'size_impact': size_impact,
            'volatility_impact': vol_impact,
            'execution_delay_ms': self._simulate_execution_delay()
        }
        
    def simulate_exit(
        self,
        current_price: float,
        size_usd: float,
        liquidity_usd: float,
        volatility: float = 0.02,
        urgency: str = 'normal'  # normal, urgent, patient
    ) -> Dict:
        """Simulate trade exit with realistic conditions"""
        
        # Adjust slippage based on urgency
        urgency_multipliers = {
            'patient': 0.5,
            'normal': 1.0,
            'urgent': 1.5
        }
        urgency_mult = urgency_multipliers.get(urgency, 1.0)
        
        # Calculate impacts
        size_impact = self._calculate_size_impact(size_usd, liquidity_usd)
        vol_impact = volatility * self.config['volatility_multiplier']
        
        # Total slippage (higher for exits)
        total_slippage = (self.config['base_slippage'] * 1.5 + size_impact + vol_impact) * urgency_mult
        
        # Apply slippage (worse price for seller)
        executed_price = current_price * (1 - total_slippage)
        
        # Fill rate (usually worse for exits)
        fill_rate = self._calculate_fill_rate(size_usd, liquidity_usd) * 0.9
        
        # Actual executed size
        executed_size = size_usd * fill_rate
        
        return {
            'executed_price': executed_price,
            'executed_size': executed_size,
            'fill_rate': fill_rate,
            'total_slippage': total_slippage,
            'size_impact': size_impact,
            'volatility_impact': vol_impact,
            'urgency': urgency,
            'execution_delay_ms': self._simulate_execution_delay()
        }
        
    def _calculate_size_impact(
        self,
        size_usd: float,
        liquidity_usd: float
    ) -> float:
        """Calculate price impact based on trade size relative to liquidity"""
        
        if liquidity_usd <= 0:
            return 0.5  # 50% impact if no liquidity
            
        # Size as percentage of liquidity
        size_percent = size_usd / liquidity_usd
        
        # Non-linear impact (gets worse as size increases)
        if size_percent < 0.01:  # Less than 1% of liquidity
            impact = size_percent * 0.1
        elif size_percent < 0.05:  # 1-5% of liquidity
            impact = 0.001 + (size_percent - 0.01) * 0.5
        elif size_percent < 0.10:  # 5-10% of liquidity
            impact = 0.021 + (size_percent - 0.05) * 1.0
        else:  # More than 10% of liquidity
            impact = 0.071 + (size_percent - 0.10) * 2.0
            
        return min(impact, 0.5)  # Cap at 50% impact
        
    def _calculate_fill_rate(
        self,
        size_usd: float,
        liquidity_usd: float
    ) -> float:
        """Calculate how much of the order can be filled"""
        
        if liquidity_usd <= 0:
            return self.config['min_fill_rate']
            
        # Size relative to liquidity
        size_ratio = size_usd / liquidity_usd
        
        if size_ratio < 0.05:  # Small order relative to liquidity
            fill_rate = self.config['max_fill_rate']
        elif size_ratio < 0.20:  # Medium order
            # Linear decrease from 100% to 70%
            fill_rate = 1.0 - (size_ratio - 0.05) * 2
        else:  # Large order
            # Asymptotic decrease towards minimum
            fill_rate = 0.7 * np.exp(-5 * (size_ratio - 0.20))
            
        return max(fill_rate, self.config['min_fill_rate'])
        
    def _simulate_execution_delay(self) -> int:
        """Simulate network and execution delays"""
        
        # Network delay (normally distributed)
        network_delay = max(0, np.random.normal(
            self.config['network_delay_ms'],
            self.config['network_delay_ms'] * 0.2
        ))
        
        # Block inclusion delay (0-2 blocks typically)
        blocks_to_include = np.random.poisson(0.5)
        block_delay = blocks_to_include * self.config['block_time_ms']
        
        return int(network_delay + block_delay)
        
    def simulate_partial_fills(
        self,
        total_size: float,
        avg_liquidity: float,
        num_fills: int = 1
    ) -> List[Dict]:
        """Simulate order filled in multiple parts"""
        
        if num_fills <= 1:
            return [{
                'size': total_size,
                'fill_percent': 100.0
            }]
            
        # Generate random fill percentages
        fill_percentages = np.random.dirichlet(np.ones(num_fills)) * 100
        
        fills = []
        remaining_size = total_size
        
        for i, pct in enumerate(fill_percentages):
            fill_size = total_size * (pct / 100)
            
            # Ensure we don't exceed remaining size
            fill_size = min(fill_size, remaining_size)
            remaining_size -= fill_size
            
            fills.append({
                'size': fill_size,
                'fill_percent': pct,
                'order': i + 1
            })
            
        return fills
        
    def estimate_trading_costs(
        self,
        entry_price: float,
        exit_price: float,
        size_usd: float,
        entry_liquidity: float,
        exit_liquidity: float,
        fee_rate: float = 0.0025
    ) -> Dict:
        """Estimate total trading costs"""
        
        # Entry costs
        entry_sim = self.simulate_entry(
            entry_price,
            size_usd,
            entry_liquidity
        )
        
        entry_cost = size_usd * (entry_sim['total_slippage'] + fee_rate)
        
        # Exit costs (on the exit value)
        exit_value = size_usd * (exit_price / entry_price)
        exit_sim = self.simulate_exit(
            exit_price,
            exit_value,
            exit_liquidity
        )
        
        exit_cost = exit_value * (exit_sim['total_slippage'] + fee_rate)
        
        # Total costs
        total_cost = entry_cost + exit_cost
        total_cost_percent = (total_cost / size_usd) * 100
        
        return {
            'entry_cost': entry_cost,
            'entry_cost_percent': (entry_cost / size_usd) * 100,
            'exit_cost': exit_cost,
            'exit_cost_percent': (exit_cost / exit_value) * 100,
            'total_cost': total_cost,
            'total_cost_percent': total_cost_percent,
            'breakeven_price_change': total_cost_percent
        }