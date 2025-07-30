"""Database initialization utility for production environments"""

import asyncio
import asyncpg
import logging
from config import get_database_url

logger = logging.getLogger(__name__)


async def ensure_database_exists():
    """Ensure database and tables exist"""
    
    # Parse database URL
    db_url = get_database_url()
    
    # Extract database name
    parts = db_url.split('/')
    db_name = parts[-1].split('?')[0] if '?' in parts[-1] else parts[-1]
    base_url = '/'.join(parts[:-1])
    
    try:
        # First, check if tables exist
        conn = await asyncpg.connect(db_url)
        
        # Check if strategy_configs table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'strategy_configs'
            );
        """)
        
        if not table_exists:
            logger.warning("Database tables not found. Creating tables...")
            
            # Create tables
            await conn.execute("""
                -- Strategy configurations
                CREATE TABLE IF NOT EXISTS strategy_configs (
                    id SERIAL PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    conditions JSONB NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW(),
                    is_active BOOLEAN DEFAULT true
                );
                
                -- Insert default strategies if table is empty
                INSERT INTO strategy_configs (name, description, conditions)
                SELECT * FROM (VALUES
                    (
                        'Quick Start Template',
                        'Basic template for testing',
                        '{"volume_window": {"enabled": true, "window_seconds": 60, "operator": "greater_than", "value": 1000}}'::jsonb
                    )
                ) AS t(name, description, conditions)
                WHERE NOT EXISTS (SELECT 1 FROM strategy_configs LIMIT 1);
            """)
            
            logger.info("Database tables created successfully")
        else:
            logger.info("Database tables already exist")
            
        await conn.close()
        
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        # Don't fail the app startup
        logger.warning("Continuing with limited functionality")


if __name__ == "__main__":
    asyncio.run(ensure_database_exists())