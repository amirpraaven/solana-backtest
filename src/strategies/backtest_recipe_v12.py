"""Backtest Recipe v1.2 - MC band-based strategy with 5-minute slices"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd

class BacktestRecipeV12:
    """
    Implements v1.2 backtest recipe with:
    - 5-minute time slices
    - MC band-based big buy thresholds
    - Tokens <= 30 days old
    - Entry: 1 SOL buy when conditions met
    - Exit ladder: 2x (take partial), 7x (take 50% of remainder)
    """
    
    # MC band definitions (upper limit, big buy threshold, min total)
    MC_BANDS = [
        (100_000, 300, 1_500),      # <= $100k
        (400_000, 1_000, 5_000),    # <= $400k (need 5 buys min)
        (1_000_000, 2_000, 10_000), # <= $1m
        (2_000_000, 4_000, 20_000), # <= $2m
    ]
    
    def __init__(self):
        self.entry_price = 1.0  # 1 SOL worth
        self.exit_targets = [(2.0, 0.3), (7.0, 0.5)]  # (multiplier, sell_fraction)
        self.max_token_age_days = 30
        self.slice_duration_seconds = 300  # 5 minutes
        
    def get_mc_band_config(self, market_cap: float) -> Optional[Tuple[float, float, int]]:
        """Get big buy threshold and min total for given market cap"""
        for mc_limit, buy_threshold, min_total in self.MC_BANDS:
            if market_cap <= mc_limit:
                # Special case for $400k band - need at least 5 buys
                min_count = 5 if mc_limit == 400_000 else 0
                return buy_threshold, min_total, min_count
        return None
        
    def check_big_buy_conditions(self, 
                                transactions: List[Dict], 
                                market_cap: float) -> bool:
        """
        Check if big buy conditions are met for the given MC band
        
        Args:
            transactions: List of transactions in the 5-minute slice
            market_cap: Market cap at slice start
            
        Returns:
            bool: True if conditions met
        """
        # Validate inputs
        if not transactions or market_cap <= 0:
            return False
            
        config = self.get_mc_band_config(market_cap)
        if not config:
            return False
            
        buy_threshold, min_total, min_count = config
        
        # Handle different MC bands
        if market_cap <= 100_000:
            # For <= $100k: buys >= $300 each
            big_buys = [
                tx for tx in transactions 
                if tx.get('type') == 'buy' and tx.get('amount_usd', 0) >= buy_threshold
            ]
            
        elif market_cap <= 400_000:
            # For <= $400k: buys >= $1000 each, need at least 5
            big_buys = [
                tx for tx in transactions 
                if tx.get('type') == 'buy' and tx.get('amount_usd', 0) >= buy_threshold
            ]
            
            if len(big_buys) < min_count:
                return False
                
        elif market_cap <= 1_000_000:
            # For <= $1m: $2k - $4k range
            big_buys = [
                tx for tx in transactions 
                if (tx.get('type') == 'buy' and 
                    2_000 <= tx.get('amount_usd', 0) <= 4_000)
            ]
            
        elif market_cap <= 2_000_000:
            # For <= $2m: $4k - $12k range
            big_buys = [
                tx for tx in transactions 
                if (tx.get('type') == 'buy' and 
                    4_000 <= tx.get('amount_usd', 0) <= 12_000)
            ]
        else:
            return False
            
        # Check total amount
        total = sum(tx.get('amount_usd', 0) for tx in big_buys)
        return total >= min_total
            
    def should_enter_position(self, 
                            token_data: Dict,
                            slice_transactions: List[Dict],
                            current_time: datetime) -> bool:
        """
        Check if entry conditions are met
        
        Args:
            token_data: Token metadata including age, market cap
            slice_transactions: Transactions in current 5-minute slice
            current_time: Current timestamp
            
        Returns:
            bool: True if should enter position
        """
        # Validate inputs
        if not token_data or not isinstance(token_data, dict):
            return False
            
        # Check token age
        created_at = token_data.get('created_at')
        if not created_at:
            return False
            
        # Handle both datetime and string formats
        if isinstance(created_at, str):
            # Remove 'Z' suffix if present, handle already formatted strings
            if created_at.endswith('Z'):
                created_at = created_at[:-1] + '+00:00'
            try:
                created_at = datetime.fromisoformat(created_at)
            except ValueError:
                # Try parsing without timezone
                created_at = datetime.fromisoformat(created_at.split('+')[0])
        
        # Ensure timezone aware
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if current_time.tzinfo is None:
            current_time = current_time.replace(tzinfo=timezone.utc)
            
        token_age_days = (current_time - created_at).days
        if token_age_days > self.max_token_age_days:
            return False
            
        # Get market cap at slice start
        market_cap = token_data.get('market_cap', 0)
        if market_cap <= 0:
            return False
            
        # Check big buy conditions
        return self.check_big_buy_conditions(slice_transactions, market_cap)
        
    def calculate_exit_amounts(self, 
                             entry_price: float,
                             current_price: float,
                             position_value: float) -> Optional[float]:
        """
        Calculate amount to sell based on exit ladder
        
        Args:
            entry_price: Price at entry
            current_price: Current price
            position_value: Current position value in SOL
            
        Returns:
            Optional[float]: Amount to sell in SOL, or None if no exit
        """
        # Validate inputs
        if entry_price <= 0 or current_price <= 0 or position_value <= 0:
            return None
            
        price_multiple = current_price / entry_price
        
        # Check 2x target
        if 1.9 <= price_multiple < 2.1:  # Small tolerance
            # At 2x: sell just enough to leave 1.7x initial SOL value
            # If position is worth 2 SOL (2x), we want to keep 1.7 SOL
            # So sell 0.3 SOL worth = 15% of current position
            return position_value * 0.15
            
        # Check 7x target
        elif 6.9 <= price_multiple < 7.1:  # Small tolerance
            # Sell 50% of whatever is left
            return position_value * 0.5
            
        return None
        
    def to_strategy_config(self) -> Dict:
        """Convert to flexible strategy config format"""
        return {
            "name": "Backtest Recipe v1.2",
            "description": "MC band-based strategy with 5-minute slices",
            "conditions": {
                "token_age": {
                    "enabled": True,
                    "operator": "less_than_equal",
                    "value": self.max_token_age_days,
                    "unit": "days"
                },
                "custom": {
                    "enabled": True,
                    "type": "mc_band_big_buys",
                    "slice_duration": self.slice_duration_seconds,
                    "mc_bands": self.MC_BANDS
                }
            },
            "entry": {
                "type": "fixed_sol",
                "amount": self.entry_price
            },
            "exit": {
                "type": "ladder",
                "targets": self.exit_targets
            }
        }