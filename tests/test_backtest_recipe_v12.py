"""Tests for Backtest Recipe v1.2 implementation"""

import pytest
from datetime import datetime, timedelta, timezone
from src.strategies.backtest_recipe_v12 import BacktestRecipeV12


class TestBacktestRecipeV12:
    """Test the v1.2 recipe implementation"""
    
    def setup_method(self):
        """Set up test instance"""
        self.recipe = BacktestRecipeV12()
        
    def test_mc_band_config(self):
        """Test MC band configuration retrieval"""
        # Test $100k band
        threshold, min_total, min_count = self.recipe.get_mc_band_config(50_000)
        assert threshold == 300
        assert min_total == 1_500
        assert min_count == 0
        
        # Test $400k band (special case)
        threshold, min_total, min_count = self.recipe.get_mc_band_config(300_000)
        assert threshold == 1_000
        assert min_total == 5_000
        assert min_count == 5
        
        # Test $1m band
        threshold, min_total, min_count = self.recipe.get_mc_band_config(800_000)
        assert threshold == 2_000
        assert min_total == 10_000
        assert min_count == 0
        
        # Test $2m band
        threshold, min_total, min_count = self.recipe.get_mc_band_config(1_500_000)
        assert threshold == 4_000
        assert min_total == 20_000
        assert min_count == 0
        
        # Test above all bands
        result = self.recipe.get_mc_band_config(3_000_000)
        assert result is None
        
    def test_check_big_buy_conditions_100k_band(self):
        """Test big buy conditions for $100k MC band"""
        transactions = [
            {'type': 'buy', 'amount_usd': 350},
            {'type': 'buy', 'amount_usd': 400},
            {'type': 'buy', 'amount_usd': 300},
            {'type': 'buy', 'amount_usd': 500},
            {'type': 'sell', 'amount_usd': 200},  # Should be ignored
        ]
        
        # Should pass - total is $1,550
        assert self.recipe.check_big_buy_conditions(transactions, 80_000) is True
        
        # Should fail - not enough total
        transactions_fail = [
            {'type': 'buy', 'amount_usd': 300},
            {'type': 'buy', 'amount_usd': 400},
        ]
        assert self.recipe.check_big_buy_conditions(transactions_fail, 80_000) is False
        
    def test_check_big_buy_conditions_400k_band(self):
        """Test big buy conditions for $400k MC band (special rules)"""
        # Should pass - 5 buys >= $1k with total >= $5k
        transactions = [
            {'type': 'buy', 'amount_usd': 1_100},
            {'type': 'buy', 'amount_usd': 1_000},
            {'type': 'buy', 'amount_usd': 1_200},
            {'type': 'buy', 'amount_usd': 1_000},
            {'type': 'buy', 'amount_usd': 1_500},
        ]
        assert self.recipe.check_big_buy_conditions(transactions, 350_000) is True
        
        # Should fail - only 4 buys
        transactions_fail = [
            {'type': 'buy', 'amount_usd': 1_500},
            {'type': 'buy', 'amount_usd': 1_500},
            {'type': 'buy', 'amount_usd': 1_500},
            {'type': 'buy', 'amount_usd': 1_500},
        ]
        assert self.recipe.check_big_buy_conditions(transactions_fail, 350_000) is False
        
    def test_check_big_buy_conditions_1m_band(self):
        """Test big buy conditions for $1m MC band"""
        # Should pass - buys in $2k-$4k range totaling >= $10k
        transactions = [
            {'type': 'buy', 'amount_usd': 2_500},
            {'type': 'buy', 'amount_usd': 3_000},
            {'type': 'buy', 'amount_usd': 2_000},
            {'type': 'buy', 'amount_usd': 3_500},
            {'type': 'buy', 'amount_usd': 1_000},  # Outside range, ignored
            {'type': 'buy', 'amount_usd': 5_000},  # Outside range, ignored
        ]
        assert self.recipe.check_big_buy_conditions(transactions, 700_000) is True
        
        # Should fail - not enough in range
        transactions_fail = [
            {'type': 'buy', 'amount_usd': 2_000},
            {'type': 'buy', 'amount_usd': 2_500},
        ]
        assert self.recipe.check_big_buy_conditions(transactions_fail, 700_000) is False
        
    def test_check_big_buy_conditions_2m_band(self):
        """Test big buy conditions for $2m MC band"""
        # Should pass - buys in $4k-$12k range totaling >= $20k
        transactions = [
            {'type': 'buy', 'amount_usd': 5_000},
            {'type': 'buy', 'amount_usd': 8_000},
            {'type': 'buy', 'amount_usd': 4_500},
            {'type': 'buy', 'amount_usd': 6_000},
        ]
        assert self.recipe.check_big_buy_conditions(transactions, 1_800_000) is True
        
    def test_should_enter_position(self):
        """Test entry position logic"""
        now = datetime.now(timezone.utc)
        
        # Valid token (15 days old)
        token_data = {
            'created_at': now - timedelta(days=15),
            'market_cap': 80_000
        }
        
        # Valid transactions
        transactions = [
            {'type': 'buy', 'amount_usd': 500},
            {'type': 'buy', 'amount_usd': 600},
            {'type': 'buy', 'amount_usd': 450},
        ]
        
        assert self.recipe.should_enter_position(token_data, transactions, now) is True
        
        # Test token too old
        old_token = {
            'created_at': now - timedelta(days=31),
            'market_cap': 80_000
        }
        assert self.recipe.should_enter_position(old_token, transactions, now) is False
        
        # Test no market cap
        no_mc_token = {
            'created_at': now - timedelta(days=5),
            'market_cap': 0
        }
        assert self.recipe.should_enter_position(no_mc_token, transactions, now) is False
        
    def test_calculate_exit_amounts(self):
        """Test exit amount calculations"""
        # Test 2x exit
        amount = self.recipe.calculate_exit_amounts(100, 200, 2.0)
        assert amount is not None
        assert abs(amount - 0.3) < 0.01  # Should sell ~15% to lock 30% profit
        
        # Test 7x exit
        amount = self.recipe.calculate_exit_amounts(100, 700, 2.0)
        assert amount is not None
        assert amount == 1.0  # Should sell 50% of position
        
        # Test no exit (price not at target)
        amount = self.recipe.calculate_exit_amounts(100, 150, 2.0)
        assert amount is None
        
    def test_to_strategy_config(self):
        """Test conversion to strategy config format"""
        config = self.recipe.to_strategy_config()
        
        assert config['name'] == "Backtest Recipe v1.2"
        assert config['conditions']['token_age']['value'] == 30
        assert config['conditions']['custom']['type'] == "mc_band_big_buys"
        assert config['entry']['type'] == "fixed_sol"
        assert config['entry']['amount'] == 1.0
        assert config['exit']['type'] == "ladder"
        assert len(config['exit']['targets']) == 2