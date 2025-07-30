"""FastAPI application for Solana Token Backtesting System"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncpg
import aioredis
import logging
from typing import Optional

from config import settings
from config.logging import setup_logging
from src.api import HeliusClient, BirdeyeClient, APICache
from src.services import TokenAgeTracker, TokenMonitor
from src.strategies import StrategyManager
from src.engine import BacktestEngine

from .routes import router as general_router
from .strategy_routes import router as strategy_router

# Setup logging
logger = setup_logging()

# Global connections
db_pool: Optional[asyncpg.Pool] = None
redis_client: Optional[aioredis.Redis] = None
helius_client: Optional[HeliusClient] = None
birdeye_client: Optional[BirdeyeClient] = None
cache: Optional[APICache] = None
token_tracker: Optional[TokenAgeTracker] = None
token_monitor: Optional[TokenMonitor] = None
strategy_manager: Optional[StrategyManager] = None
backtest_engine: Optional[BacktestEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    
    # Startup
    global db_pool, redis_client, helius_client, birdeye_client, cache
    global token_tracker, token_monitor, strategy_manager, backtest_engine
    
    logger.info("Starting Solana Backtest API")
    
    try:
        # Initialize database pool
        logger.info("Connecting to PostgreSQL")
        db_pool = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=10,
            max_size=20,
            command_timeout=60
        )
        
        # Initialize Redis
        logger.info("Connecting to Redis")
        redis_client = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
        
        # Initialize API clients
        logger.info("Initializing API clients")
        helius_client = HeliusClient(settings.HELIUS_API_KEY)
        birdeye_client = BirdeyeClient(settings.BIRDEYE_API_KEY)
        
        # Initialize cache
        cache = APICache(settings.REDIS_URL)
        await cache.connect()
        
        # Initialize services
        logger.info("Initializing services")
        token_tracker = TokenAgeTracker(
            helius_client,
            birdeye_client,
            db_pool,
            redis_client
        )
        
        token_monitor = TokenMonitor(
            birdeye_client,
            token_tracker,
            db_pool,
            redis_client
        )
        
        strategy_manager = StrategyManager(db_pool)
        
        backtest_engine = BacktestEngine(
            helius_client,
            birdeye_client,
            db_pool,
            redis_client
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
            
        if db_pool:
            await db_pool.close()
            
        if redis_client:
            await redis_client.close()
            
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
    if db_pool:
        try:
            async with db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            health_status["database"] = "connected"
        except:
            health_status["database"] = "disconnected"
            health_status["status"] = "degraded"
            
    # Check Redis
    if redis_client:
        try:
            await redis_client.ping()
            health_status["redis"] = "connected"
        except:
            health_status["redis"] = "disconnected"
            health_status["status"] = "degraded"
            
    # Check API clients
    if helius_client:
        health_status["services"]["helius"] = "configured"
    if birdeye_client:
        health_status["services"]["birdeye"] = "configured"
        
    return health_status


# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus-compatible metrics endpoint"""
    
    metrics_data = []
    
    # Database metrics
    if db_pool:
        pool_size = db_pool.get_size()
        pool_free = db_pool.get_idle_size()
        
        metrics_data.extend([
            f"# HELP db_pool_size Database connection pool size",
            f"# TYPE db_pool_size gauge",
            f"db_pool_size {pool_size}",
            f"# HELP db_pool_free Free connections in pool",
            f"# TYPE db_pool_free gauge", 
            f"db_pool_free {pool_free}"
        ])
        
    return "\n".join(metrics_data)


# Dependency injection
async def get_db():
    """Get database connection"""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")
    async with db_pool.acquire() as conn:
        yield conn


async def get_redis():
    """Get Redis connection"""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not available")
    return redis_client


async def get_helius():
    """Get Helius client"""
    if not helius_client:
        raise HTTPException(status_code=503, detail="Helius client not available")
    return helius_client


async def get_birdeye():
    """Get Birdeye client"""
    if not birdeye_client:
        raise HTTPException(status_code=503, detail="Birdeye client not available")
    return birdeye_client


async def get_token_tracker():
    """Get token tracker"""
    if not token_tracker:
        raise HTTPException(status_code=503, detail="Token tracker not available")
    return token_tracker


async def get_strategy_manager():
    """Get strategy manager"""
    if not strategy_manager:
        raise HTTPException(status_code=503, detail="Strategy manager not available")
    return strategy_manager


async def get_backtest_engine():
    """Get backtest engine"""
    if not backtest_engine:
        raise HTTPException(status_code=503, detail="Backtest engine not available")
    return backtest_engine


# Export for uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.web.app:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development"
    )