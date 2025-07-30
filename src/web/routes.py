"""General API routes"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone
import logging

from src.services import TokenAgeTracker
from src.api import BirdeyeClient, HeliusClient
from src.data.models import Transaction, PoolState
from .dependencies import (
    get_db, get_redis, get_token_tracker, 
    get_birdeye, get_helius
)

logger = logging.getLogger(__name__)

router = APIRouter()


# Pydantic models
class TokenAnalysisRequest(BaseModel):
    token_address: str
    include_price_data: bool = True
    include_security_info: bool = False


class TokenListRequest(BaseModel):
    max_age_hours: float = Field(default=72, gt=0, le=168)
    min_liquidity: float = Field(default=1000, gt=0)
    limit: int = Field(default=50, ge=1, le=200)


class TransactionQueryRequest(BaseModel):
    token_address: str
    start_time: datetime
    end_time: datetime
    dex: Optional[str] = None
    type: Optional[str] = None
    min_amount_usd: Optional[float] = None


# Routes
@router.post("/analyze/token/{token_address}")
async def analyze_token(
    token_address: str,
    include_price_data: bool = Query(True),
    include_security_info: bool = Query(False),
    tracker: TokenAgeTracker = Depends(get_token_tracker),
    birdeye: BirdeyeClient = Depends(get_birdeye),
    db_conn = Depends(get_db)
):
    """Quick analysis of a token"""
    
    try:
        # Get token age
        age_hours = await tracker.get_token_age_hours(token_address)
        
        # Get current stats from Birdeye
        async with birdeye:
            token_data = await birdeye.get_token_overview(token_address)
            
            # Get security info if requested
            security_data = None
            if include_security_info:
                security_data = await birdeye.get_token_security(token_address)
                
        # Get recent transaction stats from database
        tx_stats = await db_conn.fetchrow("""
            SELECT 
                COUNT(*) as total_txs,
                COUNT(DISTINCT wallet_address) as unique_wallets,
                SUM(CASE WHEN type = 'buy' THEN 1 ELSE 0 END) as buy_count,
                SUM(CASE WHEN type = 'sell' THEN 1 ELSE 0 END) as sell_count,
                SUM(amount_usd) as total_volume,
                MAX(time) as last_tx_time
            FROM transactions
            WHERE token_address = $1
            AND time > NOW() - INTERVAL '24 hours'
        """, token_address)
        
        # Get pool information
        pool_info = await db_conn.fetch("""
            SELECT DISTINCT 
                dex,
                MAX(liquidity_usd) as max_liquidity,
                MAX(time) as last_update
            FROM pool_states
            WHERE token_address = $1
            AND time > NOW() - INTERVAL '1 hour'
            GROUP BY dex
        """, token_address)
        
        response = {
            "token_address": token_address,
            "age": {
                "hours": age_hours,
                "days": age_hours / 24 if age_hours else None,
                "category": _categorize_age(age_hours)
            },
            "current_stats": {
                "price": token_data.get('price'),
                "price_change_24h": token_data.get('priceChange24h'),
                "market_cap": token_data.get('mc'),
                "liquidity": token_data.get('liquidity', {}).get('usd'),
                "volume_24h": token_data.get('v24hUSD'),
                "holders": token_data.get('holder')
            },
            "transaction_stats_24h": dict(tx_stats) if tx_stats else None,
            "pools": [dict(p) for p in pool_info],
            "metadata": {
                "name": token_data.get('name'),
                "symbol": token_data.get('symbol'),
                "decimals": token_data.get('decimals')
            }
        }
        
        if include_security_info and security_data:
            response["security"] = security_data
            
        return response
        
    except Exception as e:
        logger.error(f"Error analyzing token {token_address}: {e}")
        raise HTTPException(500, detail="Error analyzing token")


@router.get("/tokens/new")
async def get_new_tokens(
    max_age_hours: float = Query(72, gt=0, le=168),
    min_liquidity: float = Query(1000, gt=0),
    limit: int = Query(50, ge=1, le=200),
    tracker: TokenAgeTracker = Depends(get_token_tracker),
    db_conn = Depends(get_db)
):
    """Get recently created tokens"""
    
    tokens = await tracker.get_tokens_by_age(
        max_age_hours=max_age_hours,
        limit=limit
    )
    
    # Filter by liquidity if needed
    if min_liquidity > 0:
        filtered_tokens = []
        for token in tokens:
            # Get latest liquidity
            liquidity = await db_conn.fetchval("""
                SELECT MAX(liquidity_usd)
                FROM pool_states
                WHERE token_address = $1
                AND time > NOW() - INTERVAL '1 hour'
            """, token['token_address'])
            
            if liquidity and liquidity >= min_liquidity:
                token['current_liquidity'] = float(liquidity)
                filtered_tokens.append(token)
                
        tokens = filtered_tokens
        
    return {
        "tokens": tokens,
        "count": len(tokens),
        "filters": {
            "max_age_hours": max_age_hours,
            "min_liquidity": min_liquidity
        }
    }


@router.post("/transactions/query")
async def query_transactions(
    request: TransactionQueryRequest,
    limit: int = Query(1000, ge=1, le=10000),
    db_conn = Depends(get_db)
):
    """Query historical transactions"""
    
    # Build query
    query = """
        SELECT 
            time, signature, dex, type,
            amount_token, amount_usd,
            wallet_address, success
        FROM transactions
        WHERE token_address = $1
        AND time BETWEEN $2 AND $3
    """
    
    params = [request.token_address, request.start_time, request.end_time]
    param_count = 3
    
    if request.dex:
        param_count += 1
        query += f" AND dex = ${param_count}"
        params.append(request.dex)
        
    if request.type:
        param_count += 1
        query += f" AND type = ${param_count}"
        params.append(request.type)
        
    if request.min_amount_usd:
        param_count += 1
        query += f" AND amount_usd >= ${param_count}"
        params.append(request.min_amount_usd)
        
    query += f" ORDER BY time DESC LIMIT {limit}"
    
    rows = await db_conn.fetch(query, *params)
    
    return {
        "transactions": [dict(row) for row in rows],
        "count": len(rows),
        "query": {
            "token_address": request.token_address,
            "time_range": {
                "start": request.start_time.isoformat(),
                "end": request.end_time.isoformat()
            },
            "filters": {
                "dex": request.dex,
                "type": request.type,
                "min_amount_usd": request.min_amount_usd
            }
        }
    }


@router.get("/pool-states/{token_address}")
async def get_pool_states(
    token_address: str,
    hours: int = Query(24, ge=1, le=168),
    interval: str = Query("1h", regex="^(1m|5m|15m|1h|4h|1d)$"),
    db_conn = Depends(get_db)
):
    """Get historical pool states"""
    
    # Map interval to PostgreSQL interval
    interval_map = {
        "1m": "1 minute",
        "5m": "5 minutes",
        "15m": "15 minutes",
        "1h": "1 hour",
        "4h": "4 hours",
        "1d": "1 day"
    }
    
    pg_interval = interval_map[interval]
    
    rows = await db_conn.fetch("""
        SELECT 
            time_bucket($1, time) as bucket,
            dex,
            AVG(liquidity_usd) as avg_liquidity,
            AVG(market_cap) as avg_market_cap,
            AVG(price) as avg_price,
            MAX(liquidity_usd) as max_liquidity,
            MIN(liquidity_usd) as min_liquidity
        FROM pool_states
        WHERE token_address = $2
        AND time > NOW() - INTERVAL '%s hours'
        GROUP BY bucket, dex
        ORDER BY bucket DESC
    """ % hours, pg_interval, token_address)
    
    # Group by time bucket
    data_by_time = {}
    for row in rows:
        bucket = row['bucket'].isoformat()
        if bucket not in data_by_time:
            data_by_time[bucket] = {}
        data_by_time[bucket][row['dex']] = {
            'avg_liquidity': float(row['avg_liquidity']) if row['avg_liquidity'] else 0,
            'avg_market_cap': float(row['avg_market_cap']) if row['avg_market_cap'] else 0,
            'avg_price': float(row['avg_price']) if row['avg_price'] else 0,
            'liquidity_range': {
                'min': float(row['min_liquidity']) if row['min_liquidity'] else 0,
                'max': float(row['max_liquidity']) if row['max_liquidity'] else 0
            }
        }
        
    return {
        "token_address": token_address,
        "time_range": {
            "hours": hours,
            "interval": interval
        },
        "data": data_by_time
    }


@router.get("/dex/stats")
async def get_dex_stats(
    hours: int = Query(24, ge=1, le=168),
    db_conn = Depends(get_db)
):
    """Get DEX statistics"""
    
    stats = await db_conn.fetch("""
        SELECT 
            dex,
            COUNT(DISTINCT token_address) as unique_tokens,
            COUNT(*) as total_transactions,
            SUM(amount_usd) as total_volume,
            COUNT(DISTINCT wallet_address) as unique_wallets,
            AVG(amount_usd) as avg_trade_size
        FROM transactions
        WHERE time > NOW() - INTERVAL '%s hours'
        GROUP BY dex
        ORDER BY total_volume DESC
    """ % hours)
    
    return {
        "period_hours": hours,
        "dex_stats": [
            {
                "dex": row['dex'],
                "unique_tokens": row['unique_tokens'],
                "total_transactions": row['total_transactions'],
                "total_volume": float(row['total_volume']) if row['total_volume'] else 0,
                "unique_wallets": row['unique_wallets'],
                "avg_trade_size": float(row['avg_trade_size']) if row['avg_trade_size'] else 0
            }
            for row in stats
        ]
    }


@router.post("/data/refresh/{token_address}")
async def refresh_token_data(
    token_address: str,
    background_tasks: BackgroundTasks,
    helius: HeliusClient = Depends(get_helius),
    birdeye: BirdeyeClient = Depends(get_birdeye),
    tracker: TokenAgeTracker = Depends(get_token_tracker)
):
    """Refresh data for a specific token"""
    
    # Update token metadata
    background_tasks.add_task(
        tracker.get_token_creation_time,
        token_address
    )
    
    # You would implement the actual data refresh here
    # This is a placeholder
    
    return {
        "message": f"Data refresh initiated for {token_address}",
        "status": "processing"
    }


@router.get("/supported-dexes")
async def get_supported_dexes():
    """Get list of supported DEXes"""
    
    from src.dex import SUPPORTED_DEXES
    
    dex_info = []
    for name, program_id in SUPPORTED_DEXES.items():
        info = {
            "name": name,
            "program_id": program_id,
            "display_name": name.replace('_', ' ').title()
        }
        
        # Add specific characteristics
        if name == "pump.fun":
            info["characteristics"] = [
                "Bonding curve model",
                "6 decimal tokens",
                "1% fixed fee",
                "Auto-graduation at ~$69k"
            ]
        elif name == "raydium_clmm":
            info["characteristics"] = [
                "Concentrated liquidity",
                "Variable fees",
                "Tick-based pricing"
            ]
        elif name == "raydium_cpmm":
            info["characteristics"] = [
                "Constant product (x*y=k)",
                "0.25% fixed fee",
                "Traditional AMM"
            ]
        elif name == "meteora_dlmm":
            info["characteristics"] = [
                "Bin-based liquidity",
                "Dynamic fees",
                "Optimized for volatility"
            ]
        elif name == "meteora_dyn":
            info["characteristics"] = [
                "Adaptive parameters",
                "Market phase optimization",
                "Complex fee structure"
            ]
            
        dex_info.append(info)
        
    return {"supported_dexes": dex_info}


# Helper functions
def _categorize_age(age_hours: Optional[float]) -> str:
    """Categorize token age"""
    if age_hours is None:
        return "unknown"
    elif age_hours < 1:
        return "brand_new"
    elif age_hours < 24:
        return "very_new"
    elif age_hours < 72:
        return "new"
    elif age_hours < 168:  # 1 week
        return "recent"
    else:
        return "established"