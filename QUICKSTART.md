# Quick Start Guide

This guide will help you get the Solana Token Backtesting System up and running quickly.

## Prerequisites

- Python 3.9+
- Docker & Docker Compose
- Helius API key (Business plan)
- Birdeye API key (Business plan)

## 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/your-org/solana-backtest.git
cd solana-backtest

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
make install
```

## 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env
```

Required environment variables:
- `HELIUS_API_KEY`: Your Helius API key
- `BIRDEYE_API_KEY`: Your Birdeye API key
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string

## 3. Start Services

### Using Docker (Recommended)

```bash
# Start all services
docker-compose up -d

# Initialize database
make db-init

# Check service status
docker-compose ps
```

### Manual Setup

```bash
# Start PostgreSQL with TimescaleDB
# Start Redis

# Run database migrations
psql -U postgres -f init.sql

# Start API server
make run-dev
```

## 4. Your First Backtest

### Step 1: Create a Strategy

```bash
# Using curl
curl -X POST http://localhost:8000/strategies/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My First Strategy",
    "description": "Testing early token momentum",
    "conditions": {
      "token_age": {
        "enabled": true,
        "operator": "less_than",
        "value": 3,
        "unit": "days"
      },
      "liquidity": {
        "enabled": true,
        "operator": "greater_than",
        "value": 10000
      },
      "large_buys": {
        "enabled": true,
        "min_count": 5,
        "min_amount": 1000,
        "window_seconds": 30
      }
    }
  }'
```

### Step 2: Run a Backtest

```bash
# Get your strategy ID from the previous response
STRATEGY_ID=1

# Run backtest
curl -X POST http://localhost:8000/strategies/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": '$STRATEGY_ID',
    "token_addresses": [
      "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
      "So11111111111111111111111111111111111111112"
    ],
    "start_date": "2024-01-01T00:00:00Z",
    "end_date": "2024-01-07T00:00:00Z",
    "initial_capital": 10000
  }'
```

### Step 3: Check Results

```bash
# Get backtest results
BACKTEST_ID=1  # From previous response
curl http://localhost:8000/strategies/backtest/$BACKTEST_ID?include_trades=true
```

## 5. Using Pre-built Templates

### List Available Templates

```bash
curl http://localhost:8000/strategies/templates
```

### Create Strategy from Template

```bash
curl -X POST http://localhost:8000/strategies/create-from-template \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "early_momentum",
    "custom_name": "My Early Momentum Strategy",
    "modifications": {
      "liquidity": {"value": 20000}
    }
  }'
```

## 6. Analyze a Token

```bash
# Quick token analysis
TOKEN_ADDRESS="YourTokenAddressHere"
curl -X POST "http://localhost:8000/analyze/token/$TOKEN_ADDRESS?include_price_data=true"
```

## 7. Query Historical Data

```bash
# Query transactions
curl -X POST http://localhost:8000/transactions/query \
  -H "Content-Type: application/json" \
  -d '{
    "token_address": "TokenAddress",
    "start_time": "2024-01-01T00:00:00Z",
    "end_time": "2024-01-02T00:00:00Z",
    "dex": "pump.fun",
    "type": "buy",
    "min_amount_usd": 1000
  }'
```

## 8. API Documentation

Visit http://localhost:8000/docs for interactive API documentation.

## Common Commands

```bash
# Check system health
curl http://localhost:8000/health

# List supported DEXes
curl http://localhost:8000/supported-dexes

# Get new tokens (last 72 hours)
curl "http://localhost:8000/tokens/new?max_age_hours=72&min_liquidity=5000"

# View logs
docker-compose logs -f app

# Run tests
make test

# Format code
make format
```

## Troubleshooting

### Database Connection Issues
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Test connection
docker-compose exec postgres psql -U postgres -d solana_backtest -c "SELECT 1"
```

### Redis Connection Issues
```bash
# Check Redis is running
docker-compose ps redis

# Test connection
docker-compose exec redis redis-cli ping
```

### API Key Issues
- Ensure API keys are correctly set in `.env`
- Check rate limits on your API plan
- Verify keys with:
  ```bash
  make check-env
  ```

## Next Steps

1. Read the [Architecture Documentation](ARCHITECTURE.md)
2. Explore strategy templates in `src/strategies/templates.py`
3. Customize backtest parameters in `config/settings.py`
4. Set up monitoring with Prometheus/Grafana
5. Deploy to production using Docker Swarm or Kubernetes

## Support

- GitHub Issues: https://github.com/your-org/solana-backtest/issues
- Documentation: See `/docs` directory
- API Reference: http://localhost:8000/docs