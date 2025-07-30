"""FastAPI application for Solana Token Backtesting System"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import os
from contextlib import asynccontextmanager
import asyncpg
import aioredis
import asyncio
import logging
from typing import Optional

from config import settings, get_database_url, get_redis_url
from config.logging import setup_logging
from src.api import HeliusClient, BirdeyeClient, APICache
from src.services import TokenAgeTracker, TokenMonitor
from src.strategies import StrategyManager
from src.engine import BacktestEngine

# Setup logging
logger = setup_logging()

# Import dependencies module to set up globals
from . import dependencies


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    
    # Startup
    
    logger.info("Starting Solana Backtest API")
    
    try:
        # Ensure database is initialized
        from src.utils.db_init import ensure_database_exists
        await ensure_database_exists()
        
        # Initialize database pool with retries
        logger.info("Connecting to PostgreSQL")
        for attempt in range(3):
            try:
                dependencies.db_pool = await asyncpg.create_pool(
                    get_database_url(),
                    min_size=10,
                    max_size=20,
                    command_timeout=60
                )
                break
            except Exception as db_error:
                logger.warning(f"Database connection attempt {attempt + 1} failed: {db_error}")
                if attempt == 2:
                    raise
                await asyncio.sleep(2)
        
        # Initialize Redis
        logger.info("Connecting to Redis")
        dependencies.redis_client = await aioredis.from_url(
            get_redis_url(),
            encoding="utf-8",
            decode_responses=True
        )
        
        # Initialize API clients
        logger.info("Initializing API clients")
        dependencies.helius_client = HeliusClient(settings.HELIUS_API_KEY)
        dependencies.birdeye_client = BirdeyeClient(settings.BIRDEYE_API_KEY)
        
        # Initialize cache
        dependencies.api_cache = APICache(get_redis_url())
        await dependencies.api_cache.connect()
        
        # Initialize services
        logger.info("Initializing services")
        dependencies.token_tracker = TokenAgeTracker(
            dependencies.helius_client,
            dependencies.birdeye_client,
            dependencies.db_pool,
            dependencies.redis_client
        )
        
        token_monitor = TokenMonitor(
            dependencies.birdeye_client,
            dependencies.token_tracker,
            dependencies.db_pool,
            dependencies.redis_client
        )
        
        dependencies.strategy_manager = StrategyManager(dependencies.db_pool)
        
        dependencies.backtest_engine = BacktestEngine(
            dependencies.helius_client,
            dependencies.birdeye_client,
            dependencies.db_pool,
            dependencies.redis_client
        )
        
        # Initialize job manager
        from src.engine.job_manager import JobManager
        dependencies.job_manager = JobManager(
            dependencies.redis_client,
            dependencies.db_pool
        )
        
        # Start token monitor
        dependencies.token_monitor = token_monitor
        asyncio.create_task(token_monitor.start())
        
        logger.info("Application startup complete")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        # Don't raise on startup failure - let the app run with degraded functionality
        logger.warning("Running in degraded mode - some services unavailable")
        
    yield
    
    # Cleanup
    logger.info("Shutting down Solana Backtest API")
    
    try:
        if token_monitor:
            await token_monitor.stop()
            
        if cache:
            await cache.disconnect()
            
        if dependencies.db_pool:
            await dependencies.db_pool.close()
            
        if dependencies.redis_client:
            await dependencies.redis_client.close()
            
    except Exception as e:
        logger.error(f"Cleanup error: {e}")


# Create FastAPI app
app = FastAPI(
    title="Solana Token Backtesting API",
    description="Production-ready backtesting system for Solana tokens with flexible strategies",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENVIRONMENT == "development" else settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )


@app.exception_handler(asyncpg.PostgresError)
async def database_error_handler(request, exc):
    logger.error(f"Database error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Database error occurred"}
    )


# Import routers after app is created to avoid circular imports
from .routes import router as general_router
from .strategy_routes import router as strategy_router
from .token_routes import router as token_router
from .sample_data_routes import router as sample_router
from .sync_routes import router as sync_router

# Include routers
app.include_router(general_router)
app.include_router(strategy_router, prefix="/strategies", tags=["strategies"])
app.include_router(token_router, prefix="/tokens", tags=["tokens"])
app.include_router(sample_router, prefix="/sample-data", tags=["sample-data"])
app.include_router(sync_router, prefix="/sync", tags=["data-sync"])


# Simple health check for Railway - MUST be before static files mount
@app.get("/health/simple")
async def simple_health_check():
    """Simple health check that responds immediately"""
    return {"status": "ok"}


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    
    health_status = {
        "status": "healthy",
        "database": "unknown",
        "redis": "unknown",
        "services": {
            "helius": "unknown",
            "birdeye": "unknown"
        }
    }
    
    # Check database
    if dependencies.db_pool:
        try:
            async with dependencies.db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            health_status["database"] = "connected"
        except:
            health_status["database"] = "disconnected"
            health_status["status"] = "degraded"
            
    # Check Redis
    if dependencies.redis_client:
        try:
            await dependencies.redis_client.ping()
            health_status["redis"] = "connected"
        except:
            health_status["redis"] = "disconnected"
            health_status["status"] = "degraded"
            
    # Check API clients
    if dependencies.helius_client:
        health_status["services"]["helius"] = "configured"
    if dependencies.birdeye_client:
        health_status["services"]["birdeye"] = "configured"
        
    return health_status


# Debug endpoint to check frontend status
@app.get("/debug/frontend")
async def debug_frontend():
    """Debug endpoint to check frontend build status"""
    frontend_build_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "build")
    frontend_exists = os.path.exists(frontend_build_path)
    
    files = []
    if frontend_exists:
        try:
            files = os.listdir(frontend_build_path)
        except Exception as e:
            files = [f"Error listing files: {str(e)}"]
    
    return {
        "frontend_build_path": frontend_build_path,
        "exists": frontend_exists,
        "files": files,
        "working_dir": os.getcwd()
    }


# API validation endpoint
@app.get("/api/validate")
async def validate_apis():
    """Validate API keys and connectivity"""
    
    validation_results = {
        "helius": {
            "configured": False,
            "valid": False,
            "error": None
        },
        "birdeye": {
            "configured": False,
            "valid": False,
            "error": None
        }
    }
    
    # Check Helius API
    if dependencies.helius_client and dependencies.helius_client.api_key:
        validation_results["helius"]["configured"] = True
        try:
            # Test with a simple request
            async with dependencies.helius_client:
                # Get recent Solana slot to test API
                test_result = await dependencies.helius_client.get_latest_blockhash()
                if test_result:
                    validation_results["helius"]["valid"] = True
        except Exception as e:
            validation_results["helius"]["error"] = str(e)
    
    # Check Birdeye API
    if dependencies.birdeye_client and dependencies.birdeye_client.api_key:
        validation_results["birdeye"]["configured"] = True
        try:
            # Test with a simple request for USDC token
            async with dependencies.birdeye_client:
                test_result = await dependencies.birdeye_client.get_token_overview(
                    "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC
                )
                if test_result:
                    validation_results["birdeye"]["valid"] = True
        except Exception as e:
            validation_results["birdeye"]["error"] = str(e)
    
    # Add summary
    all_valid = all(
        api["configured"] and api["valid"] 
        for api in validation_results.values()
    )
    
    return {
        "status": "ready" if all_valid else "incomplete",
        "apis": validation_results,
        "message": "All APIs are configured and working" if all_valid else "Some APIs are not configured or failing"
    }


# System status endpoint - shows real data availability
@app.get("/system/status")
async def system_status():
    """Get comprehensive system status including real data availability"""
    
    status = {
        "mode": "real_data" if dependencies.helius_client and dependencies.helius_client.api_key else "demo_data",
        "apis": {},
        "data_stats": {},
        "services": {}
    }
    
    # Check API status
    if dependencies.helius_client and dependencies.helius_client.api_key:
        status["apis"]["helius"] = {
            "configured": True,
            "api_key_length": len(dependencies.helius_client.api_key)
        }
    else:
        status["apis"]["helius"] = {"configured": False}
    
    if dependencies.birdeye_client and dependencies.birdeye_client.api_key:
        status["apis"]["birdeye"] = {
            "configured": True,
            "api_key_length": len(dependencies.birdeye_client.api_key)
        }
    else:
        status["apis"]["birdeye"] = {"configured": False}
    
    # Get data statistics
    if dependencies.db_pool:
        try:
            async with dependencies.db_pool.acquire() as conn:
                # Token count
                token_count = await conn.fetchval(
                    "SELECT COUNT(DISTINCT token_address) FROM token_metadata"
                )
                
                # Transaction stats
                tx_stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_transactions,
                        COUNT(DISTINCT token_address) as unique_tokens,
                        MIN(time) as oldest_transaction,
                        MAX(time) as newest_transaction
                    FROM transactions
                """)
                
                # Pool state stats
                pool_stats = await conn.fetchrow("""
                    SELECT 
                        COUNT(*) as total_states,
                        COUNT(DISTINCT token_address) as tokens_tracked
                    FROM pool_states
                """)
                
                status["data_stats"] = {
                    "tokens": {
                        "total": token_count,
                        "with_transactions": tx_stats["unique_tokens"] if tx_stats else 0
                    },
                    "transactions": dict(tx_stats) if tx_stats else {},
                    "pool_states": dict(pool_stats) if pool_stats else {}
                }
        except Exception as e:
            status["data_stats"]["error"] = str(e)
    
    # Check services
    status["services"]["token_monitor"] = {
        "enabled": dependencies.token_monitor is not None,
        "status": "running" if dependencies.token_monitor else "disabled"
    }
    
    status["services"]["job_manager"] = {
        "enabled": dependencies.job_manager is not None
    }
    
    # Add recommendations
    if status["mode"] == "demo_data":
        status["recommendations"] = [
            "Add HELIUS_API_KEY to environment for real Solana transaction data",
            "Add BIRDEYE_API_KEY to environment for real token price/liquidity data",
            "Use /sync/token/{address} endpoint to sync real data once APIs are configured"
        ]
    else:
        status["recommendations"] = [
            "Use /tokens/trending to discover real-time trending tokens",
            "Use /sync/token/{address} to sync historical data for any token",
            "Monitor /sync/active to track ongoing data synchronization"
        ]
    
    return status


# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus-compatible metrics endpoint"""
    
    metrics_data = []
    
    # Database metrics
    if dependencies.db_pool:
        pool_size = dependencies.db_pool.get_size()
        pool_free = dependencies.db_pool.get_idle_size()
        
        metrics_data.extend([
            f"# HELP db_pool_size Database connection pool size",
            f"# TYPE db_pool_size gauge",
            f"db_pool_size {pool_size}",
            f"# HELP db_pool_free Free connections in pool",
            f"# TYPE db_pool_free gauge", 
            f"db_pool_free {pool_free}"
        ])
        
    return "\n".join(metrics_data)


# Root endpoint - only for API calls, not browser requests
@app.get("/api")
async def api_root():
    """API root endpoint"""
    return {
        "message": "Solana Token Backtesting API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "redoc": "/redoc"
    }


# Serve frontend build if it exists - MUST be last to avoid catching API routes
frontend_build_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "build")
if os.path.exists(frontend_build_path):
    app.mount("/", StaticFiles(directory=frontend_build_path, html=True), name="frontend")
    logger.info(f"Serving frontend from {frontend_build_path}")
else:
    logger.warning(f"Frontend build not found at {frontend_build_path}")
    # If no frontend, add a root endpoint that returns JSON
    @app.get("/")
    async def root():
        """Root endpoint when no frontend is available"""
        return {
            "message": "Solana Token Backtesting API",
            "version": "1.0.0",
            "status": "operational",
            "docs": "/docs",
            "redoc": "/redoc",
            "note": "Frontend not available - use API endpoints directly"
        }


# Export for uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.web.app:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development"
    )