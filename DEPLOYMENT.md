# Complete Deployment Guide

## Table of Contents
1. [Local Development Setup](#local-development-setup)
2. [GitHub Repository Setup](#github-repository-setup)
3. [Railway Deployment](#railway-deployment)
4. [Environment Configuration](#environment-configuration)
5. [Database Setup](#database-setup)
6. [Monitoring & Maintenance](#monitoring--maintenance)
7. [Troubleshooting](#troubleshooting)

## Local Development Setup

### Prerequisites
- Python 3.9+
- Git
- Docker Desktop (optional but recommended)
- PostgreSQL 14+ with TimescaleDB
- Redis 7+

### Step 1: Clone and Initial Setup

```bash
# Clone the repository (after you push to GitHub)
git clone https://github.com/YOUR_USERNAME/solana-backtest.git
cd solana-backtest

# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your actual values
# REQUIRED: Add your API keys
nano .env  # or use any text editor
```

**Required Environment Variables:**
```env
# API Keys (REQUIRED - Get these from providers)
HELIUS_API_KEY=your_helius_api_key_here
BIRDEYE_API_KEY=your_birdeye_api_key_here

# Database (for local development)
DATABASE_URL=postgresql://postgres:password@localhost:5432/solana_backtest
REDIS_URL=redis://localhost:6379

# Application Settings
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### Step 3: Database Setup

#### Option A: Using Docker (Recommended)
```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Wait for services to start
sleep 10

# Initialize database
docker-compose exec -T postgres psql -U postgres < init.sql
```

#### Option B: Manual PostgreSQL Setup
```bash
# Install PostgreSQL with TimescaleDB extension
# On macOS:
brew install postgresql
brew install timescaledb

# Start PostgreSQL
brew services start postgresql

# Create database and user
createdb solana_backtest
psql solana_backtest < init.sql
```

### Step 4: Run the Application

```bash
# Run database migrations (first time only)
psql postgresql://postgres:password@localhost:5432/solana_backtest < init.sql

# Start the development server
uvicorn src.web.app:app --reload --host 0.0.0.0 --port 8000

# Or use the Makefile
make run-dev
```

### Step 5: Verify Installation

```bash
# Check API health
curl http://localhost:8000/health

# View API documentation
open http://localhost:8000/docs

# Run tests
pytest tests/
```

## GitHub Repository Setup

### Step 1: Initialize Git Repository

```bash
# Initialize git (if not already done)
cd solana-backtest
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: Solana Token Backtesting System"
```

### Step 2: Create GitHub Repository

```bash
# Using GitHub CLI (gh)
gh repo create solana-backtest --public --source=. --remote=origin --push

# Or manually:
# 1. Go to https://github.com/new
# 2. Create repository named "solana-backtest"
# 3. Don't initialize with README (we already have one)
# 4. Push existing repository:

git remote add origin https://github.com/YOUR_USERNAME/solana-backtest.git
git branch -M main
git push -u origin main
```

### Step 3: Set Up GitHub Secrets

```bash
# Add secrets for CI/CD
gh secret set HELIUS_API_KEY --body="your_helius_api_key"
gh secret set BIRDEYE_API_KEY --body="your_birdeye_api_key"
```

## Railway Deployment

### Prerequisites
- Railway account (https://railway.app)
- Railway CLI installed
- GitHub repository set up

### Step 1: Install Railway CLI

```bash
# Install Railway CLI
# On macOS:
brew install railwayapp/railway/railway

# On Linux/WSL:
curl -fsSL https://railway.app/install.sh | sh

# Verify installation
railway --version
```

### Step 2: Create Railway Configuration

First, create Railway-specific configuration files:

```bash
# Create railway.json
cat > railway.json << 'EOF'
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "pip install -r requirements.txt"
  },
  "deploy": {
    "startCommand": "uvicorn src.web.app:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 30,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
EOF

# Create Procfile for Railway
cat > Procfile << 'EOF'
web: uvicorn src.web.app:app --host 0.0.0.0 --port $PORT --workers 2
release: python scripts/migrate.py && cd frontend && npm install && npm run build
EOF
```

### Step 3: Create Migration Script

```bash
# Create scripts directory
mkdir -p scripts

# Create migration script
cat > scripts/migrate.py << 'EOF'
#!/usr/bin/env python3
"""Database migration script for Railway"""

import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def run_migrations():
    """Run database migrations"""
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("DATABASE_URL not set, skipping migrations")
        return
        
    # Railway provides DATABASE_URL in the format:
    # postgresql://user:pass@host:port/dbname
    
    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Read and execute init.sql
        with open('init.sql', 'r') as f:
            sql = f.read()
            # Remove database creation commands
            sql = sql.replace('CREATE DATABASE solana_backtest;', '')
            sql = sql.replace('\\c solana_backtest;', '')
            
            # Execute SQL
            cur.execute(sql)
            
        print("Database migrations completed successfully")
        
    except Exception as e:
        print(f"Migration error: {e}")
        # Don't fail the deployment
        
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    run_migrations()
EOF

chmod +x scripts/migrate.py
```

### Step 4: Create Railway Services

```bash
# Login to Railway
railway login

# Create new project
railway init

# Link to your GitHub repo
railway link

# Create services
railway up
```

### Step 5: Configure Railway Services

#### Via Railway Dashboard:

1. **PostgreSQL Database**:
   ```bash
   # Add PostgreSQL plugin in Railway dashboard
   # Or via CLI:
   railway add postgresql
   ```

2. **Redis**:
   ```bash
   # Add Redis plugin
   railway add redis
   ```

3. **Environment Variables**:
   ```bash
   # Set environment variables
   railway variables set HELIUS_API_KEY=your_key_here
   railway variables set BIRDEYE_API_KEY=your_key_here
   railway variables set ENVIRONMENT=production
   railway variables set LOG_LEVEL=INFO
   railway variables set ALLOWED_ORIGINS=https://yourdomain.com
   
   # Railway automatically provides:
   # - DATABASE_URL (from PostgreSQL plugin)
   # - REDIS_URL (from Redis plugin)
   # - PORT (for web service)
   ```

### Step 6: Deploy to Railway

```bash
# Deploy manually
railway up

# Or set up automatic deploys from GitHub:
# 1. Go to Railway dashboard
# 2. Connect GitHub repo
# 3. Enable automatic deploys from main branch
```

### Step 7: Custom Domain (Optional)

```bash
# Generate domain
railway domain

# Or add custom domain in Railway dashboard
```

## Environment Configuration

### Development vs Production

Create different environment files:

```bash
# .env.development
ENVIRONMENT=development
LOG_LEVEL=DEBUG
DATABASE_URL=postgresql://postgres:password@localhost:5432/solana_backtest
REDIS_URL=redis://localhost:6379

# .env.production
ENVIRONMENT=production
LOG_LEVEL=INFO
# DATABASE_URL and REDIS_URL provided by Railway
```

### API Key Management

```bash
# Never commit API keys!
# For Railway, set via dashboard or CLI:
railway variables set HELIUS_API_KEY=xxx BIRDEYE_API_KEY=yyy

# For local development, use .env file
# Make sure .env is in .gitignore
```

## Database Setup

### TimescaleDB Extension

Railway's PostgreSQL doesn't include TimescaleDB by default. Create a modified init script:

```bash
# Create railway-init.sql
cat > railway-init.sql << 'EOF'
-- Create tables without TimescaleDB hypertables
-- (Modified version of init.sql for Railway)

-- ... (copy init.sql content but comment out TimescaleDB-specific commands)
-- Comment out: CREATE EXTENSION IF NOT EXISTS timescaledb;
-- Comment out: SELECT create_hypertable(...);
EOF
```

### Database Backups

```bash
# Create backup script
cat > scripts/backup.sh << 'EOF'
#!/bin/bash
# Backup database
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
EOF

chmod +x scripts/backup.sh
```

## Monitoring & Maintenance

### Health Checks

```bash
# Check application health
curl https://your-app.railway.app/health

# Monitor logs
railway logs -f

# Check metrics
curl https://your-app.railway.app/metrics
```

### Performance Monitoring

1. **Railway Metrics**: Built-in CPU, Memory, Network monitoring
2. **Application Metrics**: Prometheus endpoint at `/metrics`
3. **Custom Alerts**: Set up in Railway dashboard

### Scaling

```bash
# Scale horizontally (add more instances)
# In Railway dashboard: Settings > Scaling > Instances

# Scale vertically (more resources)
# In Railway dashboard: Settings > Resources
```

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   ```bash
   # Check DATABASE_URL
   railway variables
   
   # Test connection
   railway run python -c "import psycopg2; psycopg2.connect('$DATABASE_URL')"
   ```

2. **Redis Connection Errors**
   ```bash
   # Check REDIS_URL
   railway variables get REDIS_URL
   
   # Test Redis
   railway run python -c "import redis; r=redis.from_url('$REDIS_URL'); print(r.ping())"
   ```

3. **Import Errors**
   ```bash
   # Ensure all dependencies are in requirements.txt
   pip freeze > requirements.txt
   
   # Check Python version
   echo "python-3.9" > runtime.txt
   ```

4. **Memory Issues**
   ```bash
   # Add memory limits to Procfile
   web: uvicorn src.web.app:app --host 0.0.0.0 --port $PORT --workers 1 --limit-max-requests 1000
   ```

### Debug Mode

```bash
# Enable debug logging
railway variables set LOG_LEVEL=DEBUG ENVIRONMENT=development

# View detailed logs
railway logs -f

# SSH into container (if enabled)
railway shell
```

### Rollback Deployment

```bash
# List deployments
railway deployments

# Rollback to previous version
railway deployments rollback
```

## Quick Start Commands

```bash
# Complete setup from scratch
git clone https://github.com/YOUR_USERNAME/solana-backtest.git
cd solana-backtest
railway login
railway init
railway add postgresql
railway add redis
railway variables set HELIUS_API_KEY=xxx BIRDEYE_API_KEY=yyy
railway up

# Check deployment
railway open
railway logs -f
```

## Production Checklist

- [ ] API keys configured in Railway
- [ ] Database migrations run successfully
- [ ] Health endpoint responding
- [ ] Custom domain configured (optional)
- [ ] Monitoring alerts set up
- [ ] Backup strategy in place
- [ ] Rate limiting configured
- [ ] CORS settings updated for production
- [ ] SSL certificate active (Railway provides)
- [ ] Environment set to "production"

## Support Resources

- Railway Documentation: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- Project Issues: https://github.com/YOUR_USERNAME/solana-backtest/issues
- API Documentation: https://your-app.railway.app/docs