"""Performance metrics calculation for backtesting"""

from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Calculate comprehensive performance metrics"""
    
    @staticmethod
    def calculate_trade_metrics(trades: List[Dict]) -> Dict:
        """Calculate metrics from list of trades"""
        
        if not trades:
            return MetricsCalculator._empty_metrics()
            
        # Extract data
        pnls = np.array([t.get('net_pnl_percent', 0) for t in trades])
        returns = pnls / 100  # Convert to decimal
        
        # Basic metrics
        metrics = {
            'total_trades': len(trades),
            'winning_trades': np.sum(pnls > 0),
            'losing_trades': np.sum(pnls < 0),
            'breakeven_trades': np.sum(pnls == 0),
            'win_rate': np.mean(pnls > 0) * 100,
            'avg_pnl': np.mean(pnls),
            'median_pnl': np.median(pnls),
            'std_pnl': np.std(pnls),
            'skewness': MetricsCalculator._calculate_skewness(pnls),
            'kurtosis': MetricsCalculator._calculate_kurtosis(pnls)
        }
        
        # Win/Loss analysis
        winning_pnls = pnls[pnls > 0]
        losing_pnls = pnls[pnls < 0]
        
        metrics.update({
            'avg_win': np.mean(winning_pnls) if len(winning_pnls) > 0 else 0,
            'avg_loss': np.mean(losing_pnls) if len(losing_pnls) > 0 else 0,
            'median_win': np.median(winning_pnls) if len(winning_pnls) > 0 else 0,
            'median_loss': np.median(losing_pnls) if len(losing_pnls) > 0 else 0,
            'largest_win': np.max(winning_pnls) if len(winning_pnls) > 0 else 0,
            'largest_loss': np.min(losing_pnls) if len(losing_pnls) > 0 else 0,
            'win_loss_ratio': abs(np.mean(winning_pnls) / np.mean(losing_pnls)) if len(losing_pnls) > 0 and len(winning_pnls) > 0 else 0
        })
        
        # Risk metrics
        metrics.update({
            'profit_factor': MetricsCalculator._calculate_profit_factor(pnls),
            'sharpe_ratio': MetricsCalculator._calculate_sharpe_ratio(returns),
            'sortino_ratio': MetricsCalculator._calculate_sortino_ratio(returns),
            'calmar_ratio': MetricsCalculator._calculate_calmar_ratio(returns),
            'omega_ratio': MetricsCalculator._calculate_omega_ratio(returns),
            'max_drawdown': MetricsCalculator._calculate_max_drawdown_from_returns(returns),
            'max_drawdown_duration': MetricsCalculator._calculate_max_drawdown_duration(trades, returns),
            'recovery_factor': MetricsCalculator._calculate_recovery_factor(returns),
            'var_95': np.percentile(pnls, 5),  # Value at Risk 95%
            'cvar_95': np.mean(pnls[pnls <= np.percentile(pnls, 5)])  # Conditional VaR
        })
        
        # Trade analysis
        hold_durations = [(t['exit_time'] - t['entry_time']).total_seconds() / 60 for t in trades]
        
        metrics.update({
            'avg_hold_duration_minutes': np.mean(hold_durations),
            'median_hold_duration_minutes': np.median(hold_durations),
            'min_hold_duration_minutes': np.min(hold_durations),
            'max_hold_duration_minutes': np.max(hold_durations)
        })
        
        # Streaks
        metrics.update({
            'max_consecutive_wins': MetricsCalculator._calculate_max_consecutive(pnls > 0),
            'max_consecutive_losses': MetricsCalculator._calculate_max_consecutive(pnls < 0),
            'current_streak': MetricsCalculator._calculate_current_streak(pnls)
        })
        
        # By time period
        metrics['by_hour'] = MetricsCalculator._calculate_metrics_by_hour(trades)
        metrics['by_day_of_week'] = MetricsCalculator._calculate_metrics_by_day_of_week(trades)
        
        return metrics
        
    @staticmethod
    def calculate_portfolio_metrics(
        trades: List[Dict],
        initial_capital: float
    ) -> Dict:
        """Calculate portfolio-level metrics"""
        
        if not trades:
            return MetricsCalculator._empty_portfolio_metrics(initial_capital)
            
        # Build equity curve
        equity_curve = [initial_capital]
        timestamps = [trades[0]['entry_time']]
        
        current_capital = initial_capital
        
        for trade in sorted(trades, key=lambda x: x['exit_time']):
            pnl_usd = trade.get('pnl_usd', 0)
            current_capital += pnl_usd
            equity_curve.append(current_capital)
            timestamps.append(trade['exit_time'])
            
        equity_array = np.array(equity_curve)
        
        # Portfolio returns
        portfolio_returns = np.diff(equity_array) / equity_array[:-1]
        
        # Calculate metrics
        total_return = (current_capital - initial_capital) / initial_capital
        
        # Annualized metrics
        days = (timestamps[-1] - timestamps[0]).days
        years = days / 365.25
        
        if years > 0:
            annual_return = (1 + total_return) ** (1 / years) - 1
            annual_sharpe = MetricsCalculator._calculate_sharpe_ratio(portfolio_returns) * np.sqrt(365)
        else:
            annual_return = 0
            annual_sharpe = 0
            
        metrics = {
            'initial_capital': initial_capital,
            'final_capital': current_capital,
            'total_return': total_return * 100,
            'total_return_usd': current_capital - initial_capital,
            'annual_return': annual_return * 100,
            'annual_sharpe': annual_sharpe,
            'max_equity': np.max(equity_array),
            'min_equity': np.min(equity_array),
            'equity_peak_time': timestamps[np.argmax(equity_array)],
            'equity_trough_time': timestamps[np.argmin(equity_array)],
            'time_in_market_days': days,
            'avg_capital_deployed': np.mean(equity_array),
            'capital_efficiency': total_return / (np.mean(equity_array) / initial_capital)
        }
        
        # Risk metrics
        max_dd, dd_start, dd_end = MetricsCalculator._calculate_max_drawdown_details(equity_array)
        
        metrics.update({
            'max_drawdown': max_dd * 100,
            'max_drawdown_start': timestamps[dd_start] if dd_start < len(timestamps) else None,
            'max_drawdown_end': timestamps[dd_end] if dd_end < len(timestamps) else None,
            'max_drawdown_recovery': MetricsCalculator._calculate_recovery_time(equity_array, dd_end, timestamps),
            'ulcer_index': MetricsCalculator._calculate_ulcer_index(equity_array),
            'stability': MetricsCalculator._calculate_stability(equity_array)
        })
        
        return metrics
        
    @staticmethod
    def _empty_metrics() -> Dict:
        """Return empty metrics structure"""
        return {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'breakeven_trades': 0,
            'win_rate': 0,
            'avg_pnl': 0,
            'median_pnl': 0,
            'std_pnl': 0,
            'profit_factor': 0,
            'sharpe_ratio': 0,
            'sortino_ratio': 0,
            'max_drawdown': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'largest_win': 0,
            'largest_loss': 0
        }
        
    @staticmethod
    def _empty_portfolio_metrics(initial_capital: float) -> Dict:
        """Return empty portfolio metrics"""
        return {
            'initial_capital': initial_capital,
            'final_capital': initial_capital,
            'total_return': 0,
            'total_return_usd': 0,
            'annual_return': 0,
            'max_drawdown': 0,
            'sharpe_ratio': 0
        }
        
    @staticmethod
    def _calculate_profit_factor(pnls: np.ndarray) -> float:
        """Calculate profit factor"""
        gross_profits = np.sum(pnls[pnls > 0])
        gross_losses = abs(np.sum(pnls[pnls < 0]))
        
        if gross_losses == 0:
            return float('inf') if gross_profits > 0 else 0
            
        return gross_profits / gross_losses
        
    @staticmethod
    def _calculate_sharpe_ratio(returns: np.ndarray, risk_free_rate: float = 0) -> float:
        """Calculate Sharpe ratio"""
        if len(returns) == 0 or np.std(returns) == 0:
            return 0
            
        excess_returns = returns - risk_free_rate
        return np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(252)
        
    @staticmethod
    def _calculate_sortino_ratio(returns: np.ndarray, risk_free_rate: float = 0) -> float:
        """Calculate Sortino ratio"""
        if len(returns) == 0:
            return 0
            
        excess_returns = returns - risk_free_rate
        downside_returns = excess_returns[excess_returns < 0]
        
        if len(downside_returns) == 0:
            return float('inf') if np.mean(excess_returns) > 0 else 0
            
        downside_std = np.std(downside_returns)
        if downside_std == 0:
            return 0
            
        return np.mean(excess_returns) / downside_std * np.sqrt(252)
        
    @staticmethod
    def _calculate_calmar_ratio(returns: np.ndarray) -> float:
        """Calculate Calmar ratio"""
        if len(returns) == 0:
            return 0
            
        cumulative = np.cumprod(1 + returns)
        total_return = cumulative[-1] - 1
        annual_return = (1 + total_return) ** (252 / len(returns)) - 1
        
        max_dd = MetricsCalculator._calculate_max_drawdown_from_returns(returns)
        
        if max_dd == 0:
            return float('inf') if annual_return > 0 else 0
            
        return annual_return / max_dd
        
    @staticmethod
    def _calculate_omega_ratio(returns: np.ndarray, threshold: float = 0) -> float:
        """Calculate Omega ratio"""
        if len(returns) == 0:
            return 0
            
        gains = returns[returns > threshold] - threshold
        losses = threshold - returns[returns <= threshold]
        
        if np.sum(losses) == 0:
            return float('inf') if np.sum(gains) > 0 else 0
            
        return np.sum(gains) / np.sum(losses)
        
    @staticmethod
    def _calculate_max_drawdown_from_returns(returns: np.ndarray) -> float:
        """Calculate maximum drawdown from returns"""
        if len(returns) == 0:
            return 0
            
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (cumulative - running_max) / running_max
        
        return abs(np.min(drawdowns))
        
    @staticmethod
    def _calculate_max_drawdown_details(equity: np.ndarray) -> Tuple[float, int, int]:
        """Calculate max drawdown with start and end indices"""
        if len(equity) == 0:
            return 0, 0, 0
            
        running_max = np.maximum.accumulate(equity)
        drawdowns = (equity - running_max) / running_max
        
        max_dd_idx = np.argmin(drawdowns)
        max_dd = abs(drawdowns[max_dd_idx])
        
        # Find start (last peak before max drawdown)
        start_idx = np.where(equity[:max_dd_idx] == running_max[:max_dd_idx])[0]
        start_idx = start_idx[-1] if len(start_idx) > 0 else 0
        
        return max_dd, start_idx, max_dd_idx
        
    @staticmethod
    def _calculate_max_consecutive(condition: np.ndarray) -> int:
        """Calculate maximum consecutive True values"""
        if len(condition) == 0:
            return 0
            
        max_streak = 0
        current_streak = 0
        
        for value in condition:
            if value:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
                
        return max_streak
        
    @staticmethod
    def _calculate_current_streak(pnls: np.ndarray) -> Dict:
        """Calculate current winning/losing streak"""
        if len(pnls) == 0:
            return {'type': 'none', 'count': 0}
            
        streak_count = 1
        streak_type = 'win' if pnls[-1] > 0 else 'loss'
        
        for i in range(len(pnls) - 2, -1, -1):
            if (pnls[i] > 0 and streak_type == 'win') or (pnls[i] < 0 and streak_type == 'loss'):
                streak_count += 1
            else:
                break
                
        return {'type': streak_type, 'count': streak_count}
        
    @staticmethod
    def _calculate_skewness(data: np.ndarray) -> float:
        """Calculate skewness"""
        if len(data) < 3:
            return 0
            
        mean = np.mean(data)
        std = np.std(data)
        
        if std == 0:
            return 0
            
        return np.mean(((data - mean) / std) ** 3)
        
    @staticmethod
    def _calculate_kurtosis(data: np.ndarray) -> float:
        """Calculate excess kurtosis"""
        if len(data) < 4:
            return 0
            
        mean = np.mean(data)
        std = np.std(data)
        
        if std == 0:
            return 0
            
        return np.mean(((data - mean) / std) ** 4) - 3
        
    @staticmethod
    def _calculate_ulcer_index(equity: np.ndarray) -> float:
        """Calculate Ulcer Index (measures downside volatility)"""
        if len(equity) < 2:
            return 0
            
        running_max = np.maximum.accumulate(equity)
        drawdowns = ((equity - running_max) / running_max) * 100
        
        return np.sqrt(np.mean(drawdowns ** 2))
        
    @staticmethod
    def _calculate_stability(equity: np.ndarray) -> float:
        """Calculate stability (R-squared of equity curve)"""
        if len(equity) < 2:
            return 0
            
        x = np.arange(len(equity))
        
        # Linear regression
        slope, intercept = np.polyfit(x, equity, 1)
        predicted = slope * x + intercept
        
        # R-squared
        ss_res = np.sum((equity - predicted) ** 2)
        ss_tot = np.sum((equity - np.mean(equity)) ** 2)
        
        if ss_tot == 0:
            return 1 if ss_res == 0 else 0
            
        return 1 - (ss_res / ss_tot)
        
    @staticmethod
    def _calculate_recovery_factor(returns: np.ndarray) -> float:
        """Calculate recovery factor (total return / max drawdown)"""
        if len(returns) == 0:
            return 0
            
        total_return = np.prod(1 + returns) - 1
        max_dd = MetricsCalculator._calculate_max_drawdown_from_returns(returns)
        
        if max_dd == 0:
            return float('inf') if total_return > 0 else 0
            
        return total_return / max_dd
        
    @staticmethod
    def _calculate_max_drawdown_duration(trades: List[Dict], returns: np.ndarray) -> int:
        """Calculate maximum drawdown duration in days"""
        if not trades or len(returns) == 0:
            return 0
            
        # Build equity curve with timestamps
        timestamps = [t['exit_time'] for t in sorted(trades, key=lambda x: x['exit_time'])]
        cumulative = np.cumprod(1 + returns)
        
        # Find drawdown periods
        running_max = np.maximum.accumulate(cumulative)
        in_drawdown = cumulative < running_max
        
        max_duration = 0
        current_duration = 0
        dd_start = None
        
        for i, in_dd in enumerate(in_drawdown):
            if in_dd:
                if dd_start is None:
                    dd_start = timestamps[i]
                current_duration = (timestamps[i] - dd_start).days
                max_duration = max(max_duration, current_duration)
            else:
                dd_start = None
                current_duration = 0
                
        return max_duration
        
    @staticmethod
    def _calculate_recovery_time(
        equity: np.ndarray,
        dd_end_idx: int,
        timestamps: List[datetime]
    ) -> Optional[int]:
        """Calculate time to recover from drawdown"""
        if dd_end_idx >= len(equity) - 1:
            return None  # Still in drawdown
            
        # Find recovery point
        dd_value = equity[dd_end_idx]
        peak_value = np.max(equity[:dd_end_idx + 1])
        
        for i in range(dd_end_idx + 1, len(equity)):
            if equity[i] >= peak_value:
                # Recovered
                return (timestamps[i] - timestamps[dd_end_idx]).days
                
        return None  # Not recovered yet
        
    @staticmethod
    def _calculate_metrics_by_hour(trades: List[Dict]) -> Dict:
        """Calculate metrics by hour of day"""
        hourly_pnls = defaultdict(list)
        
        for trade in trades:
            hour = trade['entry_time'].hour
            hourly_pnls[hour].append(trade.get('net_pnl_percent', 0))
            
        return {
            hour: {
                'trades': len(pnls),
                'avg_pnl': np.mean(pnls),
                'win_rate': np.mean(np.array(pnls) > 0) * 100
            }
            for hour, pnls in hourly_pnls.items()
        }
        
    @staticmethod
    def _calculate_metrics_by_day_of_week(trades: List[Dict]) -> Dict:
        """Calculate metrics by day of week"""
        daily_pnls = defaultdict(list)
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for trade in trades:
            dow = trade['entry_time'].weekday()
            daily_pnls[days[dow]].append(trade.get('net_pnl_percent', 0))
            
        return {
            day: {
                'trades': len(pnls),
                'avg_pnl': np.mean(pnls),
                'win_rate': np.mean(np.array(pnls) > 0) * 100
            }
            for day, pnls in daily_pnls.items()
        }