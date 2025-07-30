"""Dependency injection for FastAPI"""

from typing import AsyncGenerator, Optional
import asyncpg
import aioredis

# Global connections (will be initialized by app lifespan)
db_pool: Optional[asyncpg.Pool] = None
redis_client: Optional[aioredis.Redis] = None
helius_client = None
birdeye_client = None
token_tracker = None
api_cache = None
strategy_manager = None
backtest_engine = None

async def get_db() -> asyncpg.Pool:
    """Get database connection pool"""
    if not db_pool:
        raise RuntimeError("Database not initialized")
    return db_pool

async def get_redis() -> aioredis.Redis:
    """Get Redis client"""
    if not redis_client:
        raise RuntimeError("Redis not initialized")
    return redis_client

async def get_helius():
    """Get Helius client"""
    if not helius_client:
        raise RuntimeError("Helius client not initialized")
    return helius_client

async def get_birdeye():
    """Get Birdeye client"""
    if not birdeye_client:
        raise RuntimeError("Birdeye client not initialized")
    return birdeye_client

async def get_token_tracker():
    """Get token tracker"""
    if not token_tracker:
        raise RuntimeError("Token tracker not initialized")
    return token_tracker

async def get_api_cache():
    """Get API cache"""
    if not api_cache:
        raise RuntimeError("API cache not initialized")
    return api_cache

async def get_strategy_manager():
    """Get strategy manager"""
    if not strategy_manager:
        raise RuntimeError("Strategy manager not initialized")
    return strategy_manager

async def get_backtest_engine():
    """Get backtest engine"""
    if not backtest_engine:
        raise RuntimeError("Backtest engine not initialized")
    return backtest_engine

def get_redis_client():
    """Get Redis client (sync wrapper)"""
    return redis_client

def get_helius_client():
    """Get Helius client (sync wrapper)"""
    return helius_client

def get_birdeye_client():
    """Get Birdeye client (sync wrapper)"""
    return birdeye_client

async def get_job_executor():
    """Get job executor"""
    from src.engine.job_manager import BacktestJobExecutor
    return BacktestJobExecutor(
        backtest_engine=backtest_engine,
        strategy_manager=strategy_manager,
        db_pool=db_pool
    )