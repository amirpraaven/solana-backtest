"""Tests for flexible signal detector"""

import pytest
from datetime import datetime, timedelta, timezone

from src.engine.flexible_detector import FlexibleSignalDetector


class TestFlexibleSignalDetector:
    """Test flexible signal detection"""
    
    @pytest.mark.asyncio
    async def test_token_age_filtering(self, token_tracker):
        """Test token age condition"""
        
        strategy = {
            "name": "Test Strategy",
            "conditions": {
                "token_age": {
                    "enabled": True,
                    "operator": "less_than",
                    "value": 3,
                    "unit": "days"
                }
            }
        }
        
        detector = FlexibleSignalDetector(strategy, token_tracker)
        
        # Test with token that passes age check (2 days old from fixture)
        result = await detector._check_token_age("test_token")
        assert result is True
        
        # Test with old token
        token_tracker.get_token_age_hours.return_value = 96  # 4 days
        result = await detector._check_token_age("old_token")
        assert result is False
        
    def test_liquidity_check(self):
        """Test liquidity condition checking"""
        
        strategy = {
            "name": "Test Strategy",
            "conditions": {
                "liquidity": {
                    "enabled": True,
                    "operator": "greater_than",
                    "value": 10000
                }
            }
        }
        
        detector = FlexibleSignalDetector(strategy, None)
        
        # Test passing liquidity
        pool_state = {"liquidity_usd": 15000}
        assert detector._check_liquidity(pool_state) is True
        
        # Test failing liquidity
        pool_state = {"liquidity_usd": 5000}
        assert detector._check_liquidity(pool_state) is False
        
    def test_volume_window_check(self):
        """Test volume window condition"""
        
        strategy = {
            "name": "Test Strategy",
            "conditions": {
                "volume_window": {
                    "enabled": True,
                    "window_seconds": 30,
                    "operator": "greater_than_equal",
                    "value": 5000
                }
            }
        }
        
        detector = FlexibleSignalDetector(strategy, None)
        
        # Test with sufficient volume
        transactions = [
            {"amount_usd": 1000},
            {"amount_usd": 2000},
            {"amount_usd": 2500}
        ]
        assert detector._check_volume(transactions) is True
        
        # Test with insufficient volume
        transactions = [
            {"amount_usd": 1000},
            {"amount_usd": 1000}
        ]
        assert detector._check_volume(transactions) is False
        
    def test_large_buys_check(self):
        """Test large buy detection"""
        
        strategy = {
            "name": "Test Strategy",
            "conditions": {
                "large_buys": {
                    "enabled": True,
                    "min_count": 3,
                    "min_amount": 1000,
                    "window_seconds": 30
                }
            }
        }
        
        detector = FlexibleSignalDetector(strategy, None)
        
        # Test with enough large buys
        transactions = [
            {"type": "buy", "amount_usd": 1500},
            {"type": "buy", "amount_usd": 2000},
            {"type": "buy", "amount_usd": 1200},
            {"type": "sell", "amount_usd": 1500}
        ]
        assert detector._check_large_buys(transactions) is True
        
        # Test with insufficient large buys
        transactions = [
            {"type": "buy", "amount_usd": 500},
            {"type": "buy", "amount_usd": 1500},
            {"type": "sell", "amount_usd": 2000}
        ]
        assert detector._check_large_buys(transactions) is False
        
    def test_calculate_metrics(self):
        """Test metrics calculation"""
        
        detector = FlexibleSignalDetector({"name": "Test", "conditions": {}}, None)
        
        transactions = [
            {"type": "buy", "amount_usd": 1000, "wallet_address": "wallet1"},
            {"type": "buy", "amount_usd": 2000, "wallet_address": "wallet2"},
            {"type": "sell", "amount_usd": 500, "wallet_address": "wallet3"},
            {"type": "buy", "amount_usd": 1500, "wallet_address": "wallet1"}
        ]
        
        pool_state = {
            "liquidity_usd": 50000,
            "market_cap": 200000,
            "price": 0.001
        }
        
        metrics = detector._calculate_metrics(transactions, pool_state)
        
        assert metrics['total_transactions'] == 4
        assert metrics['buy_transactions'] == 3
        assert metrics['sell_transactions'] == 1
        assert metrics['total_volume'] == 5000
        assert metrics['buy_volume'] == 4500
        assert metrics['sell_volume'] == 500
        assert metrics['buy_sell_ratio'] == 3.0
        assert metrics['unique_wallets'] == 3
        assert metrics['liquidity'] == 50000
        assert metrics['market_cap'] == 200000
        
    @pytest.mark.asyncio
    async def test_signal_detection(
        self,
        token_tracker,
        sample_transactions,
        sample_pool_states
    ):
        """Test full signal detection"""
        
        strategy = {
            "name": "Test Strategy",
            "conditions": {
                "liquidity": {
                    "enabled": True,
                    "operator": "greater_than",
                    "value": 40000
                },
                "volume_window": {
                    "enabled": True,
                    "window_seconds": 30,
                    "operator": "greater_than",
                    "value": 5000
                },
                "large_buys": {
                    "enabled": True,
                    "min_count": 3,
                    "min_amount": 1000,
                    "window_seconds": 30
                }
            }
        }
        
        detector = FlexibleSignalDetector(strategy, token_tracker)
        
        signals = await detector.detect_signals(
            sample_transactions,
            sample_pool_states,
            "token123"
        )
        
        # Should detect at least one signal
        assert len(signals) > 0
        
        # Check signal structure
        signal = signals[0]
        assert 'timestamp' in signal
        assert 'token_address' in signal
        assert 'transactions' in signal
        assert 'pool_state' in signal
        assert 'metrics' in signal
        assert signal['token_address'] == "token123"
        
    def test_window_size_detection(self):
        """Test window size extraction from conditions"""
        
        # Test with volume window
        strategy = {
            "conditions": {
                "volume_window": {
                    "enabled": True,
                    "window_seconds": 60
                }
            }
        }
        detector = FlexibleSignalDetector(strategy, None)
        assert detector._get_window_seconds() == 60
        
        # Test with large buys window
        strategy = {
            "conditions": {
                "large_buys": {
                    "enabled": True,
                    "window_seconds": 45
                }
            }
        }
        detector = FlexibleSignalDetector(strategy, None)
        assert detector._get_window_seconds() == 45
        
        # Test default
        strategy = {"conditions": {}}
        detector = FlexibleSignalDetector(strategy, None)
        assert detector._get_window_seconds() == 30