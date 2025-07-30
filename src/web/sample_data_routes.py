"""Sample data endpoints for testing and demo purposes"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List
from datetime import datetime, timedelta
import random
import logging

from .dependencies import get_db, get_redis_client

logger = logging.getLogger(__name__)
router = APIRouter()


# Popular Solana tokens for demo
SAMPLE_TOKENS = [
    {
        'address': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
        'symbol': 'USDC',
        'name': 'USD Coin',
        'decimals': 6,
        'is_stable': True
    },
    {
        'address': 'So11111111111111111111111111111111111111112',
        'symbol': 'WSOL',
        'name': 'Wrapped SOL',
        'decimals': 9,
        'is_native': True
    },
    {
        'address': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',
        'symbol': 'BONK',
        'name': 'Bonk',
        'decimals': 5,
        'is_meme': True
    },
    {
        'address': 'JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN',
        'symbol': 'JUP',
        'name': 'Jupiter',
        'decimals': 6,
        'is_defi': True
    },
    {
        'address': 'WENWENvqqNya429ubCdR81ZmD69brwQaaBYY6p3LCpk',
        'symbol': 'WEN',
        'name': 'Wen',
        'decimals': 5,
        'is_meme': True
    }
]


@router.get("/tokens")
async def get_sample_tokens():
    """Get list of sample tokens for testing"""
    
    return {
        "tokens": SAMPLE_TOKENS,
        "count": len(SAMPLE_TOKENS),
        "note": "These are popular Solana tokens for testing purposes"
    }


@router.post("/populate-demo")
async def populate_demo_data(
    db_conn = Depends(get_db)
):
    """Populate database with demo data for testing"""
    
    try:
        results = {
            'tokens_added': 0,
            'transactions_added': 0,
            'pool_states_added': 0
        }
        
        # Add token metadata
        for token in SAMPLE_TOKENS:
            # Check if token already exists
            existing = await db_conn.fetchval(
                "SELECT token_address FROM token_metadata WHERE token_address = $1",
                token['address']
            )
            
            if not existing:
                await db_conn.execute("""
                    INSERT INTO token_metadata (
                        token_address, name, symbol, decimals, 
                        created_at, first_pool_created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6)
                """, 
                    token['address'],
                    token['name'],
                    token['symbol'],
                    token['decimals'],
                    datetime.utcnow() - timedelta(days=random.randint(7, 365)),
                    datetime.utcnow() - timedelta(days=random.randint(7, 365))
                )
                results['tokens_added'] += 1
        
        # Generate sample transactions for each token
        for token in SAMPLE_TOKENS[:3]:  # Only first 3 to avoid too much data
            # Generate transactions for last 7 days
            current_time = datetime.utcnow()
            start_time = current_time - timedelta(days=7)
            
            # Generate 100-500 transactions per token
            num_transactions = random.randint(100, 500)
            
            for i in range(num_transactions):
                # Random time within the period
                tx_time = start_time + timedelta(
                    seconds=random.randint(0, int((current_time - start_time).total_seconds()))
                )
                
                # Random transaction type
                tx_type = random.choice(['buy', 'sell'])
                
                # Random amounts
                amount_token = random.uniform(10, 10000)
                price = random.uniform(0.001, 100) if not token.get('is_stable') else 1.0
                amount_usd = amount_token * price
                
                # Random wallet
                wallet = f"Demo{random.randint(1000, 9999)}...{random.randint(1000, 9999)}"
                
                # Random DEX
                dex = random.choice(['pump.fun', 'raydium_clmm', 'raydium_cpmm'])
                
                # Insert transaction
                await db_conn.execute("""
                    INSERT INTO transactions (
                        time, signature, token_address, dex, type,
                        amount_token, amount_usd, wallet_address, block_slot, success
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT (signature) DO NOTHING
                """,
                    tx_time,
                    f"demo_sig_{token['symbol']}_{i}",
                    token['address'],
                    dex,
                    tx_type,
                    amount_token,
                    amount_usd,
                    wallet,
                    random.randint(100000000, 200000000),
                    True
                )
                results['transactions_added'] += 1
            
            # Generate pool states
            for day in range(7):
                for hour in range(0, 24, 6):  # Every 6 hours
                    pool_time = current_time - timedelta(days=day, hours=hour)
                    
                    # Random but realistic pool metrics
                    base_liquidity = random.uniform(10000, 1000000)
                    liquidity = base_liquidity * random.uniform(0.8, 1.2)
                    
                    await db_conn.execute("""
                        INSERT INTO pool_states (
                            time, token_address, dex, liquidity_usd,
                            market_cap, price, holders
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                        ON CONFLICT (token_address, dex, time) DO NOTHING
                    """,
                        pool_time,
                        token['address'],
                        'raydium_cpmm',
                        liquidity,
                        liquidity * random.uniform(1.5, 5.0),  # Market cap
                        random.uniform(0.001, 100) if not token.get('is_stable') else 1.0,
                        random.randint(100, 10000)  # Holders
                    )
                    results['pool_states_added'] += 1
        
        return {
            "message": "Demo data populated successfully",
            "results": results,
            "tokens": [t['symbol'] for t in SAMPLE_TOKENS[:3]],
            "note": "You can now run backtests with these tokens"
        }
        
    except Exception as e:
        logger.error(f"Error populating demo data: {e}")
        raise HTTPException(500, detail=f"Failed to populate demo data: {str(e)}")


@router.post("/create-demo-strategy")
async def create_demo_strategy(
    db_conn = Depends(get_db)
):
    """Create a demo strategy for testing"""
    
    try:
        # Check if demo strategy exists
        existing = await db_conn.fetchval(
            "SELECT id FROM strategy_configs WHERE name = $1",
            "Demo Momentum Strategy"
        )
        
        if existing:
            return {
                "message": "Demo strategy already exists",
                "strategy_id": existing
            }
        
        # Create demo strategy
        strategy_id = await db_conn.fetchval("""
            INSERT INTO strategy_configs (name, description, conditions)
            VALUES ($1, $2, $3)
            RETURNING id
        """,
            "Demo Momentum Strategy",
            "A demo strategy for testing the backtest system",
            {
                "volume_window": {
                    "enabled": True,
                    "window_seconds": 300,
                    "operator": "greater_than",
                    "value": 5000
                },
                "liquidity": {
                    "enabled": True,
                    "operator": "greater_than",
                    "value": 10000
                },
                "large_buys": {
                    "enabled": True,
                    "min_count": 3,
                    "min_amount": 1000,
                    "window_seconds": 300
                }
            }
        )
        
        return {
            "message": "Demo strategy created successfully",
            "strategy_id": strategy_id,
            "strategy_name": "Demo Momentum Strategy"
        }
        
    except Exception as e:
        logger.error(f"Error creating demo strategy: {e}")
        raise HTTPException(500, detail=f"Failed to create demo strategy: {str(e)}")


@router.get("/quick-start")
async def get_quick_start_guide():
    """Get quick start guide for testing the system"""
    
    return {
        "steps": [
            {
                "step": 1,
                "action": "Populate demo data",
                "endpoint": "POST /sample-data/populate-demo",
                "description": "Creates sample tokens and transaction data"
            },
            {
                "step": 2,
                "action": "Create demo strategy",
                "endpoint": "POST /sample-data/create-demo-strategy",
                "description": "Creates a pre-configured strategy"
            },
            {
                "step": 3,
                "action": "Run backtest",
                "description": "Use the UI to run a backtest with the demo strategy and tokens",
                "tokens": ["BONK", "JUP", "WEN"],
                "date_range": "Last 7 days"
            }
        ],
        "tips": [
            "The demo data includes realistic transaction patterns",
            "Try different date ranges and parameters",
            "Check the job progress endpoint for real-time updates"
        ]
    }