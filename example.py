"""
Example usage of the Solana Token Backtesting System
"""

import asyncio
from datetime import datetime, timedelta, timezone
from src.api import HeliusClient, BirdeyeClient, APICache
from src.services import TokenAgeTracker
from src.engine.flexible_detector import FlexibleSignalDetector
import asyncpg
import aioredis


async def main():
    # Initialize connections
    db_pool = await asyncpg.create_pool(
        "postgresql://postgres:password@localhost:5432/solana_backtest"
    )
    redis = await aioredis.from_url("redis://localhost:6379")
    
    # Initialize API clients
    helius = HeliusClient("your_helius_api_key")
    birdeye = BirdeyeClient("your_birdeye_api_key")
    
    # Initialize services
    cache = APICache()
    await cache.connect()
    
    token_tracker = TokenAgeTracker(helius, birdeye, db_pool, redis)
    
    # Example strategy configuration
    strategy_config = {
        "name": "Early Token Momentum",
        "conditions": {
            "token_age": {
                "enabled": True,
                "operator": "less_than",
                "value": 3,
                "unit": "days"
            },
            "liquidity": {
                "enabled": True,
                "operator": "greater_than",
                "value": 10000,
                "unit": "USD"
            },
            "volume_window": {
                "enabled": True,
                "window_seconds": 30,
                "operator": "greater_than_equal",
                "value": 5000,
                "unit": "USD"
            },
            "large_buys": {
                "enabled": True,
                "min_count": 5,
                "min_amount": 1000,
                "window_seconds": 30
            }
        }
    }
    
    # Create detector
    detector = FlexibleSignalDetector(strategy_config, token_tracker)
    
    # Example token to analyze
    token_address = "YourTokenAddressHere"
    
    # Get token age
    age_hours = await token_tracker.get_token_age_hours(token_address)
    print(f"Token age: {age_hours:.2f} hours")
    
    # Fetch transactions for the last hour
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=1)
    
    async with helius:
        transactions = await helius.get_token_transactions(
            token_address,
            start_time,
            end_time
        )
    
    print(f"Found {len(transactions)} transactions")
    
    # Mock pool states (in production, fetch from database)
    pool_states = {
        end_time: {
            "liquidity_usd": 50000,
            "market_cap": 250000,
            "price": 0.001
        }
    }
    
    # Detect signals
    signals = await detector.detect_signals(
        transactions,
        pool_states,
        token_address
    )
    
    print(f"Detected {len(signals)} signals")
    
    for signal in signals:
        print(f"\nSignal at {signal['timestamp']}:")
        print(f"  Metrics: {signal['metrics']}")
        print(f"  Conditions met: {signal.get('conditions_met', [])}")
    
    # Cleanup
    await cache.disconnect()
    await redis.close()
    await db_pool.close()


if __name__ == "__main__":
    asyncio.run(main())