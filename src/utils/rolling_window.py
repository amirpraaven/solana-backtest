"""Efficient rolling window implementation for time-series data"""

from typing import List, Dict, Any, Callable, Optional
from collections import deque
from datetime import datetime, timedelta
import bisect


class RollingWindow:
    """Efficient rolling window for time-series data"""
    
    def __init__(self, window_seconds: int):
        self.window_seconds = window_seconds
        self.data = deque()
        self.timestamps = deque()
        
    def add(self, timestamp: datetime, item: Any):
        """Add item to window"""
        self.data.append(item)
        self.timestamps.append(timestamp)
        self._cleanup(timestamp)
        
    def _cleanup(self, current_time: datetime):
        """Remove old items outside window"""
        cutoff = current_time - timedelta(seconds=self.window_seconds)
        
        while self.timestamps and self.timestamps[0] < cutoff:
            self.timestamps.popleft()
            self.data.popleft()
            
    def get_items(self) -> List[Any]:
        """Get all items in current window"""
        return list(self.data)
        
    def get_items_with_time(self) -> List[tuple]:
        """Get items with their timestamps"""
        return list(zip(self.timestamps, self.data))
        
    def apply(self, func: Callable) -> Any:
        """Apply function to window items"""
        return func(list(self.data))
        
    def count(self) -> int:
        """Count items in window"""
        return len(self.data)
        
    def clear(self):
        """Clear the window"""
        self.data.clear()
        self.timestamps.clear()


class TimeIndexedWindow:
    """Window with efficient time-based lookups"""
    
    def __init__(self, window_seconds: int):
        self.window_seconds = window_seconds
        self.items = []  # List of (timestamp, item) tuples
        
    def add(self, timestamp: datetime, item: Any):
        """Add item maintaining time order"""
        # Use bisect for efficient insertion
        bisect.insort(self.items, (timestamp, item))
        self._cleanup(timestamp)
        
    def _cleanup(self, current_time: datetime):
        """Remove old items"""
        cutoff = current_time - timedelta(seconds=self.window_seconds)
        
        # Find cutoff index
        cutoff_idx = bisect.bisect_left(
            self.items,
            (cutoff, None)
        )
        
        # Remove old items
        if cutoff_idx > 0:
            self.items = self.items[cutoff_idx:]
            
    def get_range(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Any]:
        """Get items in time range"""
        
        start_idx = bisect.bisect_left(
            self.items,
            (start_time, None)
        )
        end_idx = bisect.bisect_right(
            self.items,
            (end_time, None)
        )
        
        return [item for _, item in self.items[start_idx:end_idx]]
        
    def get_latest(self, n: int = 1) -> List[Any]:
        """Get n most recent items"""
        if n >= len(self.items):
            return [item for _, item in self.items]
        return [item for _, item in self.items[-n:]]
        
    def aggregate_by_interval(
        self,
        interval_seconds: int,
        aggregator: Callable
    ) -> List[tuple]:
        """Aggregate items by time intervals"""
        
        if not self.items:
            return []
            
        results = []
        current_interval_start = self.items[0][0]
        current_interval_items = []
        
        for timestamp, item in self.items:
            # Check if we've moved to a new interval
            if timestamp >= current_interval_start + timedelta(seconds=interval_seconds):
                # Process current interval
                if current_interval_items:
                    results.append((
                        current_interval_start,
                        aggregator(current_interval_items)
                    ))
                    
                # Start new interval
                current_interval_start = timestamp
                current_interval_items = [item]
            else:
                current_interval_items.append(item)
                
        # Process last interval
        if current_interval_items:
            results.append((
                current_interval_start,
                aggregator(current_interval_items)
            ))
            
        return results