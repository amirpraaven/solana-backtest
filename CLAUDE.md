# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development
- **Run backend server**: `make run-dev` or `uvicorn src.web.app:app --reload --host 0.0.0.0 --port 8000`
- **Run frontend**: `cd frontend && npm start`
- **Install dependencies**: `make install` (production) or `make dev-install` (includes dev dependencies)

### Testing
- **Run tests**: `make test` or `pytest tests/`
- **Run tests with coverage**: `make test-cov` or `pytest tests/ --cov=src --cov-report=term-missing --cov-report=html`
- **Run specific test**: `pytest tests/test_specific.py::test_function`
- **Skip slow tests**: `pytest -m "not slow"`
- **Coverage requirement**: 80% minimum

### Code Quality
- **Lint code**: `make lint` (runs flake8, mypy, isort, black checks)
- **Format code**: `make format` (runs isort and black)
- **Type checking**: `mypy src/`

### Docker & Database
- **Start services**: `docker-compose up -d`
- **Initialize database**: `make db-init`
- **Database shell**: `make db-shell`
- **Redis CLI**: `make redis-cli`

### Frontend Build
- **Build frontend**: `cd frontend && npm run build`
- **Frontend deployment script**: `./scripts/build_frontend.sh`

## Architecture Overview

This is a production-ready Solana token backtesting system with the following key components:

### Core Architecture
- **API Layer**: FastAPI-based REST API (`src/web/`) with automatic OpenAPI documentation at `/docs`
- **Strategy System**: Database-backed flexible strategy configurations using JSON conditions (`src/strategies/`)
- **Signal Detection**: Configurable detector supporting token age filtering and rolling window analysis (`src/engine/flexible_detector.py`)
- **Backtesting Engine**: Realistic trade simulation with slippage modeling (`src/engine/backtest.py`)
- **DEX Support**: Parsers for pump.fun, Raydium (CLMM/CPMM), and Meteora (DLMM/Dynamic) in `src/dex/`

### Data Flow
1. **External APIs** → Helius (transactions) and Birdeye (prices/metadata)
2. **Data Layer** → PostgreSQL with TimescaleDB for time-series, Redis for caching
3. **Processing** → DEX-specific parsers → Signal detection → Backtesting → Metrics

### Key Design Patterns
- **Flexible Conditions**: Strategies use JSON-based conditions stored in database, supporting operators like `greater_than`, `less_than`, etc.
- **Rolling Windows**: Time-based analysis for volume, unique wallets, large buys
- **Caching Strategy**: Multi-level caching with Redis for API responses
- **Async Operations**: Non-blocking I/O throughout the application

### Important Files
- **Strategy Templates**: `src/strategies/templates.py` - Pre-built strategy configurations
- **API Cache**: `src/api/api_cache.py` - Redis-based caching decorator
- **Token Tracking**: `src/services/token_tracker.py` - Token monitoring by age
- **Performance Utils**: `src/utils/performance.py` - NumPy-optimized calculations

### Environment Requirements
- Python 3.9+
- PostgreSQL with TimescaleDB extension
- Redis
- Helius API key (Business plan)
- Birdeye API key (Business plan)

### Database Schema
- `transactions`: Time-series transaction data with hypertable
- `pool_states`: DEX pool liquidity and pricing
- `token_metadata`: Token creation times and info
- `strategy_configs`: Flexible strategy storage
- `backtest_results`: Performance metrics

### Testing Strategy
- Unit tests for individual components
- Integration tests for API endpoints
- Async test support with pytest-asyncio
- Mock external API calls in tests