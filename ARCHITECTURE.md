# Solana Token Backtesting System Architecture

## Overview

This document describes the architecture of the Solana Token Backtesting System, a production-ready application for backtesting trading strategies on Solana tokens across multiple DEXes.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Layer (FastAPI)                      │
├─────────────────────────────────────────────────────────────────┤
│                      Business Logic Layer                        │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐           │
│  │  Strategy   │  │  Backtest   │  │   Signal     │           │
│  │  Manager    │  │   Engine    │  │  Detector    │           │
│  └─────────────┘  └─────────────┘  └──────────────┘           │
├─────────────────────────────────────────────────────────────────┤
│                        Service Layer                             │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐           │
│  │Token Tracker│  │ DEX Parsers │  │Data Ingestion│           │
│  └─────────────┘  └─────────────┘  └──────────────┘           │
├─────────────────────────────────────────────────────────────────┤
│                      External APIs                               │
│  ┌─────────────┐  ┌─────────────┐                              │
│  │   Helius    │  │   Birdeye   │                              │
│  └─────────────┘  └─────────────┘                              │
├─────────────────────────────────────────────────────────────────┤
│                      Data Layer                                  │
│  ┌─────────────┐  ┌─────────────┐                              │
│  │ PostgreSQL  │  │    Redis    │                              │
│  │(TimescaleDB)│  │   (Cache)   │                              │
│  └─────────────┘  └─────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. API Layer (FastAPI)

- **Purpose**: RESTful API interface for the system
- **Key Files**: 
  - `src/web/app.py`: Main FastAPI application
  - `src/web/routes.py`: General API endpoints
  - `src/web/strategy_routes.py`: Strategy management endpoints
- **Features**:
  - Automatic API documentation (OpenAPI)
  - Async request handling
  - CORS support
  - Health checks and metrics

### 2. Strategy Management

- **Purpose**: Flexible, database-backed strategy configuration
- **Key Files**:
  - `src/strategies/manager.py`: CRUD operations for strategies
  - `src/strategies/templates.py`: Pre-built strategy templates
- **Features**:
  - JSON-based condition storage
  - Strategy templates
  - Validation and versioning

### 3. Signal Detection Engine

- **Purpose**: Detect trading signals based on configurable conditions
- **Key Files**:
  - `src/engine/flexible_detector.py`: Configurable signal detection
  - `src/engine/detector.py`: Basic fixed-threshold detection
- **Features**:
  - Token age filtering
  - Rolling window analysis
  - Multiple condition types (liquidity, volume, market cap, etc.)
  - Operator-based comparisons

### 4. Backtesting Engine

- **Purpose**: Simulate trading with realistic execution
- **Key Files**:
  - `src/engine/backtest.py`: Main backtesting logic
  - `src/engine/simulator.py`: Trade execution simulation
  - `src/engine/metrics.py`: Performance calculations
- **Features**:
  - Realistic slippage modeling
  - Multiple exit strategies
  - Comprehensive metrics
  - Portfolio-level analysis

### 5. DEX Parsers

- **Purpose**: Parse transactions from different DEX protocols
- **Supported DEXes**:
  - pump.fun (Bonding curve model)
  - Raydium CLMM (Concentrated liquidity)
  - Raydium CPMM (Constant product)
  - Meteora DLMM (Bin-based liquidity)
  - Meteora Dynamic (Adaptive parameters)
- **Key Files**: `src/dex/*.py`
- **Features**:
  - Protocol-specific parsing
  - Unified output format
  - Transfer extraction

### 6. Data Layer

- **PostgreSQL with TimescaleDB**:
  - Time-series optimized storage
  - Hypertables for transactions and pool states
  - Efficient time-based queries
  
- **Redis Cache**:
  - API response caching
  - Token metadata caching
  - Session management

### 7. External Integrations

- **Helius API**:
  - Transaction fetching
  - Enhanced transaction data
  - Token creation times
  
- **Birdeye API**:
  - Price data (OHLCV)
  - Token metadata
  - Market statistics

## Data Flow

1. **Data Ingestion**:
   ```
   Helius/Birdeye → Validation → Database → Cache
   ```

2. **Signal Detection**:
   ```
   Transactions → Rolling Window → Condition Checks → Signals
   ```

3. **Backtesting**:
   ```
   Signals → Trade Simulation → Metrics Calculation → Results Storage
   ```

## Performance Optimizations

- **Caching**: Multi-level caching with Redis
- **Batch Processing**: Bulk database operations
- **Async I/O**: Non-blocking API calls
- **Connection Pooling**: Database and HTTP connection reuse
- **NumPy Optimizations**: Vectorized calculations
- **Time-based Indexing**: Efficient time-series queries

## Security Considerations

- Environment-based configuration
- API key protection
- Input validation
- Rate limiting
- SQL injection prevention
- CORS configuration

## Scalability

- Horizontal scaling via Docker Swarm/Kubernetes
- Database read replicas
- Redis clustering
- API load balancing
- Background task queuing

## Monitoring

- Health endpoints
- Prometheus metrics
- Structured logging
- Error tracking
- Performance profiling

## Development Workflow

1. **Local Development**:
   ```bash
   make dev-install
   make run-dev
   ```

2. **Testing**:
   ```bash
   make test-cov
   ```

3. **Production**:
   ```bash
   docker-compose up -d
   ```

## Future Enhancements

- WebSocket support for real-time signals
- Machine learning integration
- More DEX integrations
- Advanced portfolio optimization
- Rust performance extensions
- GraphQL API option