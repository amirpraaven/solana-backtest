"""Pytest configuration and fixtures"""

import pytest
import asyncio
import asyncpg
import aioredis
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from config import settings
from src.api import HeliusClient, BirdeyeClient, APICache
from src.services import TokenAgeTracker
from src.strategies import StrategyManager
from src.engine import BacktestEngine


# Test database URL (use separate test database)
TEST_DATABASE_URL = settings.DATABASE_URL.replace('/solana_backtest', '/solana_backtest_test')


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def db_pool():
    """Create test database connection pool"""
    pool = await asyncpg.create_pool(
        TEST_DATABASE_URL,
        min_size=2,
        max_size=5
    )
    
    # Create test schema
    async with pool.acquire() as conn:
        # Drop and recreate tables for clean test environment
        await conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
        await conn.execute("CREATE SCHEMA public")
        
        # Execute init.sql to create tables
        with open('init.sql', 'r') as f:
            sql = f.read()
            # Remove database creation commands
            sql = sql.replace('CREATE DATABASE solana_backtest;', '')
            sql = sql.replace('\\c solana_backtest;', '')
            await conn.execute(sql)
    
    yield pool
    
    await pool.close()


@pytest.fixture(scope="session")
async def redis_client():
    """Create test Redis client"""
    client = await aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        db=1  # Use different database for tests
    )
    
    # Clear test database
    await client.flushdb()
    
    yield client
    
    await client.close()


@pytest.fixture
async def mock_helius_client(mocker):
    """Mock Helius client"""
    client = mocker.Mock(spec=HeliusClient)
    
    # Mock common methods
    client.get_token_transactions = mocker.AsyncMock(return_value=[])
    client.get_token_creation_time = mocker.AsyncMock(
        return_value=datetime.now(timezone.utc) - timedelta(days=2)
    )
    client.get_enhanced_transactions = mocker.AsyncMock(return_value=[])
    
    return client


@pytest.fixture
async def mock_birdeye_client(mocker):
    """Mock Birdeye client"""
    client = mocker.Mock(spec=BirdeyeClient)
    
    # Mock common methods
    client.get_token_overview = mocker.AsyncMock(return_value={
        'price': 0.001,
        'mc': 100000,
        'liquidity': {'usd': 50000},
        'v24hUSD': 10000,
        'holder': 100,
        'name': 'Test Token',
        'symbol': 'TEST',
        'decimals': 9
    })
    
    client.get_ohlcv = mocker.AsyncMock(return_value=[])
    client.get_token_creation_info = mocker.AsyncMock(return_value={
        'createdAt': int((datetime.now(timezone.utc) - timedelta(days=2)).timestamp())
    })
    
    return client


@pytest.fixture
async def token_tracker(mock_helius_client, mock_birdeye_client, db_pool, redis_client):
    """Create token tracker with mocked clients"""
    return TokenAgeTracker(
        mock_helius_client,
        mock_birdeye_client,
        db_pool,
        redis_client
    )


@pytest.fixture
async def strategy_manager(db_pool):
    """Create strategy manager"""
    return StrategyManager(db_pool)


@pytest.fixture
async def sample_strategy(strategy_manager):
    """Create a sample strategy for testing"""
    strategy_id = await strategy_manager.create_strategy(
        name="Test Strategy",
        description="Strategy for testing",
        conditions={
            "token_age": {
                "enabled": True,
                "operator": "less_than",
                "value": 3,
                "unit": "days"
            },
            "liquidity": {
                "enabled": True,
                "operator": "greater_than",
                "value": 10000
            }
        }
    )
    
    return await strategy_manager.get_strategy(strategy_id)


@pytest.fixture
def sample_transactions():
    """Sample transaction data for testing"""
    base_time = datetime.now(timezone.utc)
    
    return [
        {
            'timestamp': base_time - timedelta(seconds=30),
            'signature': 'sig1',
            'token_address': 'token123',
            'dex': 'pump.fun',
            'type': 'buy',
            'amount_token': 1000,
            'amount_usd': 1500,
            'wallet_address': 'wallet1',
            'success': True
        },
        {
            'timestamp': base_time - timedelta(seconds=25),
            'signature': 'sig2',
            'token_address': 'token123',
            'dex': 'pump.fun',
            'type': 'buy',
            'amount_token': 2000,
            'amount_usd': 3000,
            'wallet_address': 'wallet2',
            'success': True
        },
        {
            'timestamp': base_time - timedelta(seconds=20),
            'signature': 'sig3',
            'token_address': 'token123',
            'dex': 'pump.fun',
            'type': 'sell',
            'amount_token': 500,
            'amount_usd': 700,
            'wallet_address': 'wallet3',
            'success': True
        },
        {
            'timestamp': base_time - timedelta(seconds=15),
            'signature': 'sig4',
            'token_address': 'token123',
            'dex': 'pump.fun',
            'type': 'buy',
            'amount_token': 1500,
            'amount_usd': 2200,
            'wallet_address': 'wallet4',
            'success': True
        },
        {
            'timestamp': base_time - timedelta(seconds=10),
            'signature': 'sig5',
            'token_address': 'token123',
            'dex': 'pump.fun',
            'type': 'buy',
            'amount_token': 800,
            'amount_usd': 1200,
            'wallet_address': 'wallet5',
            'success': True
        }
    ]


@pytest.fixture
def sample_pool_states():
    """Sample pool state data for testing"""
    base_time = datetime.now(timezone.utc)
    
    states = {}
    for i in range(5):
        timestamp = base_time - timedelta(seconds=30-i*5)
        states[timestamp] = {
            'liquidity_usd': 50000 + i * 1000,
            'market_cap': 200000 + i * 5000,
            'price': 0.001 * (1 + i * 0.01)
        }
        
    return states


@pytest.fixture
def pump_fun_transaction():
    """Sample pump.fun transaction for parser testing"""
    return {
        'signature': 'test_sig_pump',
        'timestamp': int(datetime.now(timezone.utc).timestamp()),
        'slot': 12345678,
        'err': None,
        'instructions': [
            {
                'programId': '6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P',
                'data': 'base64_encoded_data_here',
                'accounts': [
                    'token_mint_address',
                    'bonding_curve_address',
                    'bonding_curve_token_account',
                    'user_wallet_address',
                    'user_token_account',
                    'system_program',
                    'token_program',
                    'rent',
                    'event_authority'
                ]
            }
        ],
        'meta': {
            'logMessages': [
                'Program log: Instruction: Buy',
                'Program log: remaining_tokens: 1000000'
            ]
        }
    }