"""Token discovery and management routes"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
import asyncio

from src.api import BirdeyeClient, HeliusClient
from src.services import TokenAgeTracker
from .dependencies import get_birdeye_client, get_helius_client, get_token_tracker, get_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/trending")
async def get_trending_tokens(
    time_frame: str = Query("24h", regex="^(5m|15m|30m|1h|2h|4h|12h|24h)$"),
    sort_by: str = Query("volume", regex="^(volume|price_change|trades|liquidity)$"),
    limit: int = Query(20, ge=1, le=100),
    birdeye: BirdeyeClient = Depends(get_birdeye_client)
):
    """Get trending tokens from Birdeye"""
    
    try:
        # Fetch trending tokens
        trending = await birdeye.get_trending_tokens(
            time_frame=time_frame,
            sort_by=sort_by,
            limit=limit
        )
        
        # Enhance with additional data
        enhanced_tokens = []
        for token in trending.get('data', []):
            enhanced_tokens.append({
                'address': token['address'],
                'symbol': token.get('symbol', 'Unknown'),
                'name': token.get('name', 'Unknown Token'),
                'price': token.get('price', 0),
                'price_change_24h': token.get('priceChange24h', 0),
                'volume_24h': token.get('volume24h', 0),
                'liquidity': token.get('liquidity', 0),
                'market_cap': token.get('mc', 0),
                'created_at': token.get('createdAt'),
                'age_hours': (
                    (datetime.utcnow() - datetime.fromisoformat(token['createdAt'].replace('Z', '+00:00'))).total_seconds() / 3600
                    if token.get('createdAt') else None
                ),
                'holder_count': token.get('holder', 0),
                'trade_count_24h': token.get('trade24h', 0)
            })
            
        return {
            'tokens': enhanced_tokens,
            'count': len(enhanced_tokens),
            'time_frame': time_frame,
            'sort_by': sort_by
        }
        
    except Exception as e:
        logger.error(f"Error fetching trending tokens: {e}")
        raise HTTPException(500, detail=f"Failed to fetch trending tokens: {str(e)}")


@router.get("/new-listings")
async def get_new_listings(
    max_age_hours: int = Query(24, ge=1, le=168),
    min_liquidity: float = Query(1000, ge=0),
    min_volume_24h: float = Query(500, ge=0),
    limit: int = Query(50, ge=1, le=200),
    birdeye: BirdeyeClient = Depends(get_birdeye_client)
):
    """Get newly listed tokens"""
    
    try:
        # Calculate time range
        from_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        # Fetch new tokens
        new_tokens = await birdeye.get_new_tokens(
            from_time=from_time,
            limit=limit * 2  # Fetch more to filter
        )
        
        # Filter and enhance
        filtered_tokens = []
        for token in new_tokens.get('data', []):
            # Apply filters
            if token.get('liquidity', 0) < min_liquidity:
                continue
            if token.get('volume24h', 0) < min_volume_24h:
                continue
                
            # Calculate age
            created_at = datetime.fromisoformat(token['createdAt'].replace('Z', '+00:00'))
            age_hours = (datetime.utcnow() - created_at).total_seconds() / 3600
            
            filtered_tokens.append({
                'address': token['address'],
                'symbol': token.get('symbol', 'Unknown'),
                'name': token.get('name', 'Unknown Token'),
                'created_at': token['createdAt'],
                'age_hours': age_hours,
                'age_display': _format_age(age_hours),
                'price': token.get('price', 0),
                'liquidity': token.get('liquidity', 0),
                'volume_24h': token.get('volume24h', 0),
                'market_cap': token.get('mc', 0),
                'holder_count': token.get('holder', 0),
                'dex': token.get('dex', 'Unknown'),
                'pool_address': token.get('poolAddress')
            })
            
            if len(filtered_tokens) >= limit:
                break
                
        # Sort by age (newest first)
        filtered_tokens.sort(key=lambda x: x['age_hours'])
        
        return {
            'tokens': filtered_tokens,
            'count': len(filtered_tokens),
            'filters': {
                'max_age_hours': max_age_hours,
                'min_liquidity': min_liquidity,
                'min_volume_24h': min_volume_24h
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching new listings: {e}")
        raise HTTPException(500, detail=f"Failed to fetch new listings: {str(e)}")


@router.get("/search")
async def search_tokens(
    query: str = Query(..., min_length=1, max_length=50),
    limit: int = Query(10, ge=1, le=50),
    birdeye: BirdeyeClient = Depends(get_birdeye_client)
):
    """Search for tokens by symbol or address"""
    
    try:
        # Search by symbol or address
        results = await birdeye.search_tokens(
            query=query,
            limit=limit
        )
        
        tokens = []
        for token in results.get('data', []):
            tokens.append({
                'address': token['address'],
                'symbol': token.get('symbol', 'Unknown'),
                'name': token.get('name', 'Unknown Token'),
                'decimals': token.get('decimals', 9),
                'price': token.get('price', 0),
                'liquidity': token.get('liquidity', 0),
                'volume_24h': token.get('volume24h', 0),
                'market_cap': token.get('mc', 0),
                'logo': token.get('logoURI')
            })
            
        return {
            'tokens': tokens,
            'count': len(tokens),
            'query': query
        }
        
    except Exception as e:
        logger.error(f"Error searching tokens: {e}")
        raise HTTPException(500, detail=f"Failed to search tokens: {str(e)}")


@router.get("/{token_address}/info")
async def get_token_info(
    token_address: str,
    birdeye: BirdeyeClient = Depends(get_birdeye_client),
    helius: HeliusClient = Depends(get_helius_client),
    db_conn = Depends(get_db)
):
    """Get detailed token information"""
    
    try:
        # Fetch from Birdeye
        token_data = await birdeye.get_token_overview(token_address)
        if not token_data:
            raise HTTPException(404, detail="Token not found")
            
        # Get creation info
        creation_info = await birdeye.get_token_creation_info(token_address)
        
        # Get historical metrics from DB if available
        db_metrics = await db_conn.fetchrow("""
            SELECT 
                MIN(time) as first_seen,
                MAX(time) as last_seen,
                COUNT(DISTINCT wallet_address) as unique_traders,
                COUNT(*) as total_transactions,
                SUM(CASE WHEN type = 'buy' THEN amount_usd ELSE 0 END) as total_buy_volume,
                SUM(CASE WHEN type = 'sell' THEN amount_usd ELSE 0 END) as total_sell_volume
            FROM transactions
            WHERE token_address = $1
        """, token_address)
        
        return {
            'token': {
                'address': token_address,
                'symbol': token_data.get('symbol', 'Unknown'),
                'name': token_data.get('name', 'Unknown Token'),
                'decimals': token_data.get('decimals', 9),
                'total_supply': token_data.get('supply', 0),
                'created_at': creation_info.get('createdAt') if creation_info else None,
                'creator': creation_info.get('creator') if creation_info else None
            },
            'market': {
                'price': token_data.get('price', 0),
                'price_change_24h': token_data.get('priceChange24h', 0),
                'volume_24h': token_data.get('volume24h', 0),
                'liquidity': token_data.get('liquidity', 0),
                'market_cap': token_data.get('mc', 0),
                'holder_count': token_data.get('holder', 0),
                'trade_count_24h': token_data.get('trade24h', 0)
            },
            'database_metrics': dict(db_metrics) if db_metrics else None,
            'pools': token_data.get('pools', [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching token info: {e}")
        raise HTTPException(500, detail=f"Failed to fetch token info: {str(e)}")


@router.post("/{token_address}/populate")
async def populate_token_data(
    token_address: str,
    days_back: int = Query(7, ge=1, le=30),
    helius: HeliusClient = Depends(get_helius_client),
    birdeye: BirdeyeClient = Depends(get_birdeye_client),
    db_conn = Depends(get_db)
):
    """Populate historical data for a token (for testing/demo)"""
    
    try:
        from src.data.ingestion import DataIngestionPipeline
        
        # Create ingestion pipeline
        pipeline = DataIngestionPipeline(
            helius_client=helius,
            birdeye_client=birdeye,
            db_pool=db_conn.pool  # Assuming pool is accessible
        )
        
        # Set date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)
        
        # Ingest data
        result = await pipeline.ingest_token_data(
            token_address=token_address,
            start_date=start_date,
            end_date=end_date,
            fetch_transactions=True,
            fetch_pool_states=True,
            fetch_metadata=True
        )
        
        return {
            'message': 'Data population completed',
            'token_address': token_address,
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'results': result
        }
        
    except Exception as e:
        logger.error(f"Error populating token data: {e}")
        raise HTTPException(500, detail=f"Failed to populate data: {str(e)}")


def _format_age(hours: float) -> str:
    """Format age in human-readable format"""
    if hours < 1:
        return f"{int(hours * 60)} minutes"
    elif hours < 24:
        return f"{int(hours)} hours"
    elif hours < 168:
        return f"{int(hours / 24)} days"
    else:
        return f"{int(hours / 168)} weeks"