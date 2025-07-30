from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    # API Keys
    HELIUS_API_KEY: str = Field(alias="HELIUS_KEY")
    BIRDEYE_API_KEY: str
    
    # Database - Railway provides these automatically
    DATABASE_URL: Optional[str] = None
    REDIS_URL: Optional[str] = None
    
    # API Rate Limits
    HELIUS_RATE_LIMIT: int = 10  # requests per second
    BIRDEYE_RATE_LIMIT: int = 50  # requests per second
    
    # Backtesting defaults
    DEFAULT_SLIPPAGE: float = 0.02
    DEFAULT_HOLD_DURATION: int = 300  # 5 minutes
    DEFAULT_STOP_LOSS: float = 0.10  # 10%
    DEFAULT_TAKE_PROFIT: float = 0.50  # 50%
    
    # Performance
    MAX_WORKERS: int = 4
    BATCH_SIZE: int = 1000
    CACHE_TTL: int = 300  # 5 minutes
    
    # Application
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    ALLOWED_ORIGINS: list = ["http://localhost:3000", "http://localhost:8000"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        populate_by_name = True

settings = Settings()

# Helper functions for database URLs
def get_database_url() -> str:
    """Get database URL with fallback"""
    if settings.DATABASE_URL:
        return settings.DATABASE_URL
    # Fallback for local development
    return "postgresql://postgres:password@localhost:5432/solana_backtest"

def get_redis_url() -> str:
    """Get Redis URL with fallback"""
    if settings.REDIS_URL:
        return settings.REDIS_URL
    # Fallback for local development
    return "redis://localhost:6379"