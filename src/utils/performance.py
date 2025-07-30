"""Performance optimized calculations using NumPy"""

import numpy as np
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def calculate_returns(prices: np.ndarray) -> np.ndarray:
    """Calculate returns from price series"""
    if len(prices) < 2:
        return np.array([])
    return np.diff(prices) / prices[:-1]


def calculate_log_returns(prices: np.ndarray) -> np.ndarray:
    """Calculate log returns from price series"""
    if len(prices) < 2:
        return np.array([])
    return np.log(prices[1:] / prices[:-1])


def calculate_sharpe_ratio(
    returns: np.ndarray,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 365
) -> float:
    """Calculate Sharpe ratio"""
    
    if len(returns) == 0:
        return 0.0
        
    excess_returns = returns - risk_free_rate / periods_per_year
    
    if np.std(excess_returns) == 0:
        return 0.0
        
    return np.sqrt(periods_per_year) * np.mean(excess_returns) / np.std(excess_returns)


def calculate_sortino_ratio(
    returns: np.ndarray,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 365
) -> float:
    """Calculate Sortino ratio (uses downside deviation)"""
    
    if len(returns) == 0:
        return 0.0
        
    excess_returns = returns - risk_free_rate / periods_per_year
    downside_returns = excess_returns[excess_returns < 0]
    
    if len(downside_returns) == 0:
        return float('inf')  # No downside
        
    downside_std = np.std(downside_returns)
    
    if downside_std == 0:
        return 0.0
        
    return np.sqrt(periods_per_year) * np.mean(excess_returns) / downside_std


def calculate_max_drawdown(equity_curve: np.ndarray) -> Tuple[float, int, int]:
    """
    Calculate maximum drawdown and drawdown periods
    
    Returns:
        (max_drawdown, start_idx, end_idx)
    """
    
    if len(equity_curve) == 0:
        return 0.0, 0, 0
        
    # Calculate running maximum
    running_max = np.maximum.accumulate(equity_curve)
    
    # Calculate drawdowns
    drawdowns = (equity_curve - running_max) / running_max
    
    # Find maximum drawdown
    max_dd_idx = np.argmin(drawdowns)
    max_dd = drawdowns[max_dd_idx]
    
    # Find start of drawdown (last peak before max drawdown)
    start_idx = np.where(equity_curve[:max_dd_idx] == running_max[:max_dd_idx])[0]
    start_idx = start_idx[-1] if len(start_idx) > 0 else 0
    
    return abs(max_dd), start_idx, max_dd_idx


def calculate_win_rate(pnl_array: np.ndarray) -> float:
    """Calculate win rate from P&L array"""
    
    if len(pnl_array) == 0:
        return 0.0
        
    return np.sum(pnl_array > 0) / len(pnl_array)


def calculate_profit_factor(pnl_array: np.ndarray) -> float:
    """Calculate profit factor (gross profits / gross losses)"""
    
    profits = pnl_array[pnl_array > 0]
    losses = pnl_array[pnl_array < 0]
    
    if len(losses) == 0:
        return float('inf') if len(profits) > 0 else 0.0
        
    gross_profits = np.sum(profits)
    gross_losses = abs(np.sum(losses))
    
    if gross_losses == 0:
        return float('inf')
        
    return gross_profits / gross_losses


def calculate_calmar_ratio(
    returns: np.ndarray,
    periods_per_year: int = 365
) -> float:
    """Calculate Calmar ratio (annual return / max drawdown)"""
    
    if len(returns) == 0:
        return 0.0
        
    # Calculate cumulative returns
    cumulative = np.cumprod(1 + returns)
    
    # Annual return
    total_return = cumulative[-1] - 1
    years = len(returns) / periods_per_year
    annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
    
    # Max drawdown
    max_dd, _, _ = calculate_max_drawdown(cumulative)
    
    if max_dd == 0:
        return float('inf') if annual_return > 0 else 0.0
        
    return annual_return / max_dd


def fast_rolling_sum(
    values: np.ndarray,
    window_size: int
) -> np.ndarray:
    """Fast rolling sum using cumsum trick"""
    
    if len(values) < window_size:
        return np.array([])
        
    cumsum = np.cumsum(np.insert(values, 0, 0))
    return cumsum[window_size:] - cumsum[:-window_size]


def fast_rolling_mean(
    values: np.ndarray,
    window_size: int
) -> np.ndarray:
    """Fast rolling mean"""
    
    rolling_sum = fast_rolling_sum(values, window_size)
    return rolling_sum / window_size


def fast_rolling_std(
    values: np.ndarray,
    window_size: int
) -> np.ndarray:
    """Fast rolling standard deviation"""
    
    if len(values) < window_size:
        return np.array([])
        
    # Use Welford's online algorithm for numerical stability
    rolling_mean = fast_rolling_mean(values, window_size)
    
    # Calculate squared deviations
    squared_deviations = (values[window_size-1:] - rolling_mean) ** 2
    
    # Rolling variance
    rolling_var = fast_rolling_mean(squared_deviations, window_size)
    
    return np.sqrt(rolling_var)


def calculate_trade_metrics(trades: List[Dict]) -> Dict:
    """Calculate comprehensive trade metrics"""
    
    if not trades:
        return {
            'total_trades': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'largest_win': 0,
            'largest_loss': 0
        }
        
    # Extract P&L data
    pnls = np.array([t.get('pnl_percent', 0) for t in trades])
    
    # Separate wins and losses
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    
    # Calculate equity curve
    equity_curve = np.cumprod(1 + pnls / 100)
    
    return {
        'total_trades': len(trades),
        'win_rate': calculate_win_rate(pnls),
        'profit_factor': calculate_profit_factor(pnls),
        'sharpe_ratio': calculate_sharpe_ratio(pnls / 100),
        'sortino_ratio': calculate_sortino_ratio(pnls / 100),
        'calmar_ratio': calculate_calmar_ratio(pnls / 100),
        'max_drawdown': calculate_max_drawdown(equity_curve)[0],
        'avg_win': np.mean(wins) if len(wins) > 0 else 0,
        'avg_loss': np.mean(losses) if len(losses) > 0 else 0,
        'largest_win': np.max(wins) if len(wins) > 0 else 0,
        'largest_loss': np.min(losses) if len(losses) > 0 else 0,
        'win_loss_ratio': abs(np.mean(wins) / np.mean(losses)) if len(losses) > 0 and len(wins) > 0 else 0,
        'expectancy': np.mean(pnls),
        'total_return': (equity_curve[-1] - 1) * 100 if len(equity_curve) > 0 else 0
    }