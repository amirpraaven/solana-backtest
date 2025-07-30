"""Tests for ladder exit functionality in backtest engine"""

import pytest
from datetime import datetime, timedelta, timezone
from src.engine.backtest import BacktestEngine
import asyncio


class TestLadderExit:
    """Test ladder exit strategy"""
    
    @pytest.mark.asyncio
    async def test_ladder_exit_2x_target(self):
        """Test ladder exit at 2x target"""
        # Mock backtest engine with minimal config
        engine = BacktestEngine(None, None, None, None)
        
        entry_time = datetime.now(timezone.utc)
        entry_price = 100.0
        
        # Create price data that hits 2x
        price_data = {}
        for i in range(60):  # 60 minutes
            time = entry_time + timedelta(minutes=i)
            if i < 30:
                price = entry_price * (1 + i * 0.03)  # Gradual increase
            else:
                price = entry_price * 2.0  # Hit 2x at 30 minutes
            price_data[time] = price
            
        targets = [(2.0, 0.3), (7.0, 0.5)]
        
        exit_time, exit_price, exit_reason = await engine._ladder_exit(
            entry_time, entry_price, price_data, targets
        )
        
        assert exit_time is not None
        assert abs(exit_price - 200.0) < 1.0  # Should exit around 2x
        assert "2.0x_target" in exit_reason
        
    @pytest.mark.asyncio
    async def test_ladder_exit_multiple_targets(self):
        """Test ladder exit hitting multiple targets"""
        engine = BacktestEngine(None, None, None, None)
        
        entry_time = datetime.now(timezone.utc)
        entry_price = 100.0
        
        # Create price data that hits both 2x and 7x
        price_data = {}
        for i in range(120):  # 120 minutes
            time = entry_time + timedelta(minutes=i)
            if i < 30:
                price = entry_price * (1 + i * 0.03)
            elif i < 60:
                price = entry_price * 2.0  # Hit 2x
            elif i < 90:
                price = entry_price * (2 + (i - 60) * 0.15)
            else:
                price = entry_price * 7.0  # Hit 7x
            price_data[time] = price
            
        targets = [(2.0, 0.3), (7.0, 0.5)]
        
        exit_time, exit_price, exit_reason = await engine._ladder_exit(
            entry_time, entry_price, price_data, targets
        )
        
        assert exit_time is not None
        # Weighted average exit price should be between 2x and 7x
        assert 200.0 < exit_price < 700.0
        assert "2.0x_target" in exit_reason
        assert "7.0x_target" in exit_reason
        
    @pytest.mark.asyncio
    async def test_ladder_exit_no_targets_hit(self):
        """Test ladder exit when no targets are hit"""
        engine = BacktestEngine(None, None, None, None)
        
        entry_time = datetime.now(timezone.utc)
        entry_price = 100.0
        
        # Create price data that doesn't hit targets
        price_data = {}
        for i in range(1440):  # 24 hours
            time = entry_time + timedelta(minutes=i)
            price = entry_price * 1.5  # Stay at 1.5x
            price_data[time] = price
            
        targets = [(2.0, 0.3), (7.0, 0.5)]
        
        exit_time, exit_price, exit_reason = await engine._ladder_exit(
            entry_time, entry_price, price_data, targets
        )
        
        assert exit_time is not None
        assert abs(exit_price - 150.0) < 1.0  # Should exit at market price
        assert "max_hold_time" in exit_reason
        
    @pytest.mark.asyncio
    async def test_ladder_exit_special_2x_calculation(self):
        """Test special 2x calculation (sell 15% to leave 1.7x value)"""
        engine = BacktestEngine(None, None, None, None)
        
        entry_time = datetime.now(timezone.utc)
        entry_price = 100.0
        
        # Simple price data at exactly 2x
        price_data = {
            entry_time: entry_price,
            entry_time + timedelta(minutes=30): entry_price * 2.0
        }
        
        targets = [(2.0, 0.3)]  # Original says 0.3, but code uses 0.15
        
        exit_time, exit_price, exit_reason = await engine._ladder_exit(
            entry_time, entry_price, price_data, targets
        )
        
        # With 15% sold at 2x, weighted average should be 200
        assert abs(exit_price - 200.0) < 1.0
        
    @pytest.mark.asyncio 
    async def test_ladder_exit_empty_targets(self):
        """Test ladder exit with no targets falls back to time-based"""
        engine = BacktestEngine(None, None, None, None)
        engine.config['hold_duration'] = 300  # 5 minutes
        
        entry_time = datetime.now(timezone.utc)
        entry_price = 100.0
        
        price_data = {
            entry_time + timedelta(seconds=300): 150.0
        }
        
        exit_time, exit_price, exit_reason = await engine._ladder_exit(
            entry_time, entry_price, price_data, []
        )
        
        # Should fall back to time-based exit
        assert exit_time == entry_time + timedelta(seconds=300)
        assert exit_price == 150.0