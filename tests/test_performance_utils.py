"""Tests for performance calculation utilities"""

import pytest
import numpy as np

from src.utils.performance import (
    calculate_returns,
    calculate_log_returns,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_max_drawdown,
    calculate_win_rate,
    calculate_profit_factor,
    calculate_calmar_ratio,
    calculate_trade_metrics,
    fast_rolling_sum,
    fast_rolling_mean,
    fast_rolling_std
)


class TestPerformanceUtils:
    """Test performance calculation functions"""
    
    def test_calculate_returns(self):
        """Test returns calculation"""
        prices = np.array([100, 110, 105, 115, 120])
        returns = calculate_returns(prices)
        
        expected = np.array([0.1, -0.0454545, 0.095238, 0.043478])
        np.testing.assert_array_almost_equal(returns, expected, decimal=5)
        
        # Test with single price
        assert len(calculate_returns(np.array([100]))) == 0
        
    def test_calculate_log_returns(self):
        """Test log returns calculation"""
        prices = np.array([100, 110, 105, 115])
        log_returns = calculate_log_returns(prices)
        
        assert len(log_returns) == 3
        assert log_returns[0] == pytest.approx(np.log(110/100), rel=0.0001)
        
    def test_calculate_sharpe_ratio(self):
        """Test Sharpe ratio calculation"""
        returns = np.array([0.01, 0.02, -0.01, 0.03, 0.01, -0.02, 0.02])
        
        sharpe = calculate_sharpe_ratio(returns, risk_free_rate=0.02)
        assert isinstance(sharpe, float)
        
        # Test with zero returns
        zero_returns = np.zeros(10)
        assert calculate_sharpe_ratio(zero_returns) == 0.0
        
        # Test with no variance
        constant_returns = np.ones(10) * 0.01
        assert calculate_sharpe_ratio(constant_returns) == 0.0
        
    def test_calculate_sortino_ratio(self):
        """Test Sortino ratio calculation"""
        returns = np.array([0.01, 0.02, -0.01, 0.03, 0.01, -0.02, 0.02])
        
        sortino = calculate_sortino_ratio(returns)
        assert isinstance(sortino, float)
        
        # Test with no downside
        positive_returns = np.array([0.01, 0.02, 0.03, 0.01])
        sortino_no_downside = calculate_sortino_ratio(positive_returns)
        assert sortino_no_downside == float('inf')
        
    def test_calculate_max_drawdown(self):
        """Test maximum drawdown calculation"""
        equity_curve = np.array([100, 110, 105, 95, 100, 90, 95, 100, 105])
        
        max_dd, start_idx, end_idx = calculate_max_drawdown(equity_curve)
        
        assert max_dd == pytest.approx(0.1818, rel=0.01)  # ~18.18% drawdown
        assert start_idx == 1  # Peak at index 1 (110)
        assert end_idx == 5   # Trough at index 5 (90)
        
        # Test with no drawdown
        increasing_curve = np.array([100, 110, 120, 130])
        max_dd, _, _ = calculate_max_drawdown(increasing_curve)
        assert max_dd == 0.0
        
    def test_calculate_win_rate(self):
        """Test win rate calculation"""
        pnl_array = np.array([10, -5, 20, -10, 15, 0, -5, 25])
        
        win_rate = calculate_win_rate(pnl_array)
        assert win_rate == 0.5  # 4 wins out of 8 trades
        
        # Test with all wins
        all_wins = np.array([10, 20, 30])
        assert calculate_win_rate(all_wins) == 1.0
        
        # Test with empty array
        assert calculate_win_rate(np.array([])) == 0.0
        
    def test_calculate_profit_factor(self):
        """Test profit factor calculation"""
        pnl_array = np.array([10, -5, 20, -10, 15])
        
        profit_factor = calculate_profit_factor(pnl_array)
        assert profit_factor == pytest.approx(2.33, rel=0.01)  # 45/15 ≈ 3
        
        # Test with no losses
        no_losses = np.array([10, 20, 30])
        assert calculate_profit_factor(no_losses) == float('inf')
        
        # Test with no profits
        no_profits = np.array([-10, -20, -30])
        assert calculate_profit_factor(no_profits) == 0.0
        
    def test_calculate_calmar_ratio(self):
        """Test Calmar ratio calculation"""
        returns = np.array([0.01, 0.02, -0.01, 0.01, -0.005, 0.015])
        
        calmar = calculate_calmar_ratio(returns, periods_per_year=252)
        assert isinstance(calmar, float)
        
        # Test with no drawdown
        positive_returns = np.array([0.01, 0.01, 0.01])
        calmar_no_dd = calculate_calmar_ratio(positive_returns)
        assert calmar_no_dd == float('inf')
        
    def test_fast_rolling_sum(self):
        """Test fast rolling sum"""
        values = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        window_size = 3
        
        rolling_sum = fast_rolling_sum(values, window_size)
        expected = np.array([6, 9, 12, 15, 18, 21, 24, 27])
        
        np.testing.assert_array_equal(rolling_sum, expected)
        
        # Test with window larger than array
        small_array = np.array([1, 2])
        assert len(fast_rolling_sum(small_array, 5)) == 0
        
    def test_fast_rolling_mean(self):
        """Test fast rolling mean"""
        values = np.array([1, 2, 3, 4, 5])
        window_size = 3
        
        rolling_mean = fast_rolling_mean(values, window_size)
        expected = np.array([2, 3, 4])
        
        np.testing.assert_array_almost_equal(rolling_mean, expected)
        
    def test_calculate_trade_metrics(self):
        """Test comprehensive trade metrics calculation"""
        trades = [
            {'net_pnl_percent': 5.0},
            {'net_pnl_percent': -2.0},
            {'net_pnl_percent': 10.0},
            {'net_pnl_percent': -3.0},
            {'net_pnl_percent': 7.0},
            {'net_pnl_percent': 0.0},
            {'net_pnl_percent': -5.0},
            {'net_pnl_percent': 15.0}
        ]
        
        metrics = calculate_trade_metrics(trades)
        
        assert metrics['total_trades'] == 8
        assert metrics['winning_trades'] == 4
        assert metrics['losing_trades'] == 3
        assert metrics['breakeven_trades'] == 1
        assert metrics['win_rate'] == 50.0
        assert metrics['avg_pnl'] == pytest.approx(3.375, rel=0.01)
        assert metrics['avg_win'] == pytest.approx(9.25, rel=0.01)
        assert metrics['avg_loss'] == pytest.approx(-3.33, rel=0.01)
        assert metrics['largest_win'] == 15.0
        assert metrics['largest_loss'] == -5.0
        assert metrics['profit_factor'] > 1.0
        
        # Test with empty trades
        empty_metrics = calculate_trade_metrics([])
        assert empty_metrics['total_trades'] == 0
        assert empty_metrics['win_rate'] == 0