"""Real-time data synchronization routes"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
import json

from src.data.ingestion import DataIngestionPipeline
from src.engine.job_manager import JobManager
from .dependencies import get_db, get_redis_client, get_helius_client, get_birdeye_client, get_job_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/sync/token/{token_address}")
async def sync_token_data(
    token_address: str,
    days_back: int = 7,
    background_tasks: BackgroundTasks = None,
    db_pool = Depends(get_db),
    redis = Depends(get_redis_client),
    helius = Depends(get_helius_client),
    birdeye = Depends(get_birdeye_client),
    job_manager: JobManager = Depends(get_job_manager)
):
    """Sync real-time data for a specific token"""
    
    try:
        # Create job
        job_id = await job_manager.create_job(
            job_type="token_sync",
            params={
                "token_address": token_address,
                "days_back": days_back
            }
        )
        
        # Define sync task
        async def sync_task():
            try:
                await job_manager.update_job_progress(job_id, 10, "Starting token data sync...")
                
                # Create ingestion pipeline
                pipeline = DataIngestionPipeline(
                    helius_client=helius,
                    birdeye_client=birdeye,
                    db_pool=db_pool
                )
                
                # Set date range
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=days_back)
                
                # Sync metadata
                await job_manager.update_job_progress(job_id, 20, "Fetching token metadata...")
                
                # Sync transactions
                await job_manager.update_job_progress(job_id, 40, "Fetching transactions...")
                
                # Ingest all data
                result = await pipeline.ingest_token_data(
                    token_address=token_address,
                    start_date=start_date,
                    end_date=end_date,
                    fetch_transactions=True,
                    fetch_pool_states=True,
                    fetch_metadata=True
                )
                
                await job_manager.update_job_progress(job_id, 90, "Finalizing sync...")
                
                # Mark job as completed
                await job_manager.complete_job(job_id, result)
                
                # Cache sync status
                await redis.setex(
                    f"sync:status:{token_address}",
                    3600,  # 1 hour TTL
                    json.dumps({
                        "last_sync": datetime.utcnow().isoformat(),
                        "status": "completed",
                        "result": result
                    })
                )
                
            except Exception as e:
                logger.error(f"Error in sync task: {e}")
                await job_manager.fail_job(job_id, str(e))
                
                # Cache error status
                await redis.setex(
                    f"sync:status:{token_address}",
                    300,  # 5 min TTL for errors
                    json.dumps({
                        "last_sync": datetime.utcnow().isoformat(),
                        "status": "failed",
                        "error": str(e)
                    })
                )
        
        # Run sync in background
        background_tasks.add_task(sync_task)
        
        return {
            "message": "Token sync started",
            "job_id": job_id,
            "token_address": token_address,
            "status_endpoint": f"/sync/status/{token_address}"
        }
        
    except Exception as e:
        logger.error(f"Error starting token sync: {e}")
        raise HTTPException(500, detail=f"Failed to start sync: {str(e)}")


@router.get("/sync/status/{token_address}")
async def get_sync_status(
    token_address: str,
    redis = Depends(get_redis_client),
    db_conn = Depends(get_db)
):
    """Get sync status for a token"""
    
    try:
        # Check cache first
        cached_status = await redis.get(f"sync:status:{token_address}")
        if cached_status:
            status = json.loads(cached_status)
        else:
            status = {
                "status": "no_sync",
                "message": "No recent sync found for this token"
            }
        
        # Get data stats from database
        stats = await db_conn.fetchrow("""
            SELECT 
                COUNT(DISTINCT time) as transaction_count,
                MIN(time) as oldest_transaction,
                MAX(time) as newest_transaction,
                COUNT(DISTINCT dex) as dex_count
            FROM transactions
            WHERE token_address = $1
        """, token_address)
        
        pool_stats = await db_conn.fetchrow("""
            SELECT 
                COUNT(*) as pool_state_count,
                MIN(time) as oldest_state,
                MAX(time) as newest_state
            FROM pool_states
            WHERE token_address = $1
        """, token_address)
        
        return {
            "sync_status": status,
            "data_stats": {
                "transactions": dict(stats) if stats else None,
                "pool_states": dict(pool_stats) if pool_stats else None
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        raise HTTPException(500, detail=f"Failed to get sync status: {str(e)}")


@router.post("/sync/batch")
async def sync_multiple_tokens(
    token_addresses: List[str],
    days_back: int = 7,
    background_tasks: BackgroundTasks = None,
    db_pool = Depends(get_db),
    redis = Depends(get_redis_client),
    helius = Depends(get_helius_client),
    birdeye = Depends(get_birdeye_client),
    job_manager: JobManager = Depends(get_job_manager)
):
    """Sync data for multiple tokens"""
    
    if len(token_addresses) > 10:
        raise HTTPException(400, detail="Maximum 10 tokens per batch")
    
    jobs = []
    
    for token_address in token_addresses:
        try:
            # Create job for each token
            job_id = await job_manager.create_job(
                job_type="token_sync",
                params={
                    "token_address": token_address,
                    "days_back": days_back
                }
            )
            
            jobs.append({
                "token_address": token_address,
                "job_id": job_id
            })
            
            # Sync task (similar to single token sync)
            async def sync_task(addr=token_address, jid=job_id):
                try:
                    await job_manager.update_job_progress(jid, 10, f"Starting sync for {addr}")
                    
                    pipeline = DataIngestionPipeline(
                        helius_client=helius,
                        birdeye_client=birdeye,
                        db_pool=db_pool
                    )
                    
                    end_date = datetime.utcnow()
                    start_date = end_date - timedelta(days=days_back)
                    
                    result = await pipeline.ingest_token_data(
                        token_address=addr,
                        start_date=start_date,
                        end_date=end_date,
                        fetch_transactions=True,
                        fetch_pool_states=True,
                        fetch_metadata=True
                    )
                    
                    await job_manager.complete_job(jid, result)
                    
                except Exception as e:
                    logger.error(f"Error syncing {addr}: {e}")
                    await job_manager.fail_job(jid, str(e))
            
            background_tasks.add_task(sync_task)
            
        except Exception as e:
            logger.error(f"Error creating sync job for {token_address}: {e}")
            jobs.append({
                "token_address": token_address,
                "error": str(e)
            })
    
    return {
        "message": f"Started sync for {len(jobs)} tokens",
        "jobs": jobs
    }


@router.get("/sync/active")
async def get_active_syncs(
    job_manager: JobManager = Depends(get_job_manager)
):
    """Get all active sync jobs"""
    
    try:
        # Get running jobs of type token_sync
        running_jobs = await job_manager.list_jobs(status="running", limit=50)
        
        sync_jobs = [
            job for job in running_jobs.get("jobs", [])
            if job.get("type") == "token_sync"
        ]
        
        return {
            "active_syncs": len(sync_jobs),
            "jobs": sync_jobs
        }
        
    except Exception as e:
        logger.error(f"Error getting active syncs: {e}")
        raise HTTPException(500, detail=f"Failed to get active syncs: {str(e)}")


@router.delete("/sync/cache")
async def clear_sync_cache(
    redis = Depends(get_redis_client)
):
    """Clear all sync status cache"""
    
    try:
        # Find all sync status keys
        keys = []
        cursor = 0
        
        while True:
            cursor, partial_keys = await redis.scan(
                cursor, match="sync:status:*", count=100
            )
            keys.extend(partial_keys)
            
            if cursor == 0:
                break
        
        # Delete all keys
        if keys:
            await redis.delete(*keys)
        
        return {
            "message": f"Cleared {len(keys)} sync status entries",
            "cleared_keys": len(keys)
        }
        
    except Exception as e:
        logger.error(f"Error clearing sync cache: {e}")
        raise HTTPException(500, detail=f"Failed to clear cache: {str(e)}")