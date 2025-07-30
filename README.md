# Solana Token Backtesting System

A production-ready backtesting system for Solana tokens with flexible, configurable strategy conditions and comprehensive DEX coverage.

## Features

- **Multi-DEX Support**: pump.fun, Raydium CLMM/CPMM, Meteora DLMM/Dynamic
- **Flexible Strategies**: Configurable conditions stored in database
- **Token Age Filtering**: Monitor tokens based on creation time
- **Real-time Detection**: Rolling window analysis with customizable thresholds
- **High Performance**: Rust extensions for critical paths, Redis caching
- **Production Ready**: Docker support, comprehensive logging, monitoring

## Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL with TimescaleDB extension
- Redis
- Helius API key (Business plan)
- Birdeye API key (Business plan)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/your-org/solana-backtest.git
cd solana-backtest
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

5. Initialize database:
```bash
docker-compose up -d postgres
psql -h localhost -U postgres -f init.sql
```

### Running the Application

Start the API server:
```bash
uvicorn src.web.app:app --reload
```

Access the API documentation at: http://localhost:8000/docs

## Architecture

### Components

- **API Layer**: FastAPI for REST endpoints
- **Data Layer**: PostgreSQL with TimescaleDB for time-series data
- **Cache Layer**: Redis for API response caching
- **Processing**: Python with NumPy optimizations
- **DEX Parsers**: Specialized parsers for each DEX

### Database Schema

- `transactions`: Time-series transaction data
- `pool_states`: Pool liquidity and pricing data
- `token_metadata`: Token information including creation time
- `strategy_configs`: Flexible strategy configurations
- `backtest_results`: Backtest performance metrics

## Strategy Configuration

Strategies use flexible JSON conditions:

```json
{
  "name": "Early Token Momentum",
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
    "volume_window": {
      "enabled": true,
      "window_seconds": 30,
      "operator": "greater_than_equal",
      "value": 5000
    }
  }
}
```

### Available Conditions

- **token_age**: Filter by token creation time
- **liquidity**: Pool liquidity in USD
- **market_cap**: Token market capitalization
- **volume_window**: Volume within time window
- **large_buys**: Count of large buy transactions
- **buy_pressure**: Buy/sell ratio
- **unique_wallets**: Unique wallet count

### Operators

- `greater_than`, `greater_than_equal`
- `less_than`, `less_than_equal`
- `equal`, `not_equal`

## API Endpoints

### Strategy Management

- `POST /strategies/create` - Create new strategy
- `GET /strategies/list` - List all strategies
- `GET /strategies/templates` - Get pre-built templates

### Backtesting

- `POST /strategies/backtest` - Run backtest
- `GET /strategies/backtest/{id}` - Get results
- `POST /strategies/compare` - Compare multiple strategies

### Token Analysis

- `POST /analyze/token/{address}` - Quick token analysis
- `GET /health` - System health check

## DEX Coverage

### pump.fun
- Bonding curve model
- 6 decimal tokens
- 1% fixed fee
- Auto-graduation at ~$69k

### Raydium CLMM
- Concentrated liquidity
- Variable fees
- Tick-based pricing

### Raydium CPMM
- Constant product (x*y=k)
- 0.25% fixed fee

### Meteora DLMM
- Bin-based liquidity
- Dynamic fees
- Optimized for volatility

### Meteora Dynamic
- Adaptive parameters
- Market phase optimization

## Performance Optimization

- Batch API requests
- Redis caching with TTL
- NumPy for calculations
- Database indexing
- Connection pooling

## Testing

Run tests:
```bash
pytest tests/
```

Coverage report:
```bash
pytest --cov=src tests/
```

## Deployment

### Docker

```bash
docker-compose up -d
```

### Production Considerations

1. Use environment-specific configs
2. Enable SSL/TLS
3. Set up monitoring (Prometheus/Grafana)
4. Configure rate limiting
5. Implement API authentication

## Monitoring

- Health endpoint: `/health`
- Prometheus metrics: `/metrics`
- Structured logging with correlation IDs

## Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## License

MIT License - see LICENSE file