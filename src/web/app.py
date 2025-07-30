"""FastAPI application for Solana Token Backtesting System"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncpg
import aioredis
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
        # Initialize database pool
        logger.info("Connecting to PostgreSQL")
        dependencies.db_pool = await asyncpg.create_pool(
            get_database_url(),
            min_size=10,
            max_size=20,
            command_timeout=60
        )
        
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
        
        # Start token monitor
        # asyncio.create_task(token_monitor.start())
        
        logger.info("Application startup complete")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise
        
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

# Include routers
app.include_router(general_router)
app.include_router(strategy_router, prefix="/strategies", tags=["strategies"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Solana Token Backtesting API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "redoc": "/redoc"
    }


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


# Export for uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.web.app:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development"
    )