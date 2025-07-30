-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Create database
CREATE DATABASE solana_backtest;

-- Connect to database
\c solana_backtest;

-- Enable TimescaleDB in our database
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- TimescaleDB hypertable for transactions
CREATE TABLE transactions (
    time TIMESTAMPTZ NOT NULL,
    signature TEXT PRIMARY KEY,
    token_address TEXT NOT NULL,
    dex TEXT NOT NULL CHECK (dex IN ('pump.fun', 'raydium_clmm', 'raydium_cpmm', 'meteora_dlmm', 'meteora_dyn')),
    type TEXT CHECK (type IN ('buy', 'sell')),
    amount_token NUMERIC,
    amount_usd NUMERIC,
    wallet_address TEXT,
    block_slot BIGINT,
    success BOOLEAN DEFAULT true
);

SELECT create_hypertable('transactions', 'time');
CREATE INDEX idx_token_time ON transactions (token_address, time DESC);
CREATE INDEX idx_wallet_time ON transactions (wallet_address, time DESC);
CREATE INDEX idx_dex_time ON transactions (dex, time DESC);

-- Pool state tracking
CREATE TABLE pool_states (
    time TIMESTAMPTZ NOT NULL,
    token_address TEXT NOT NULL,
    dex TEXT NOT NULL CHECK (dex IN ('pump.fun', 'raydium_clmm', 'raydium_cpmm', 'meteora_dlmm', 'meteora_dyn')),
    liquidity_usd NUMERIC,
    market_cap NUMERIC,
    price NUMERIC,
    holders INTEGER,
    -- DEX-specific fields
    active_bin_id INTEGER, -- For Meteora DLMM
    current_tick INTEGER,  -- For Raydium CLMM
    fee_rate NUMERIC,      -- Dynamic fees
    PRIMARY KEY (token_address, dex, time)
);

SELECT create_hypertable('pool_states', 'time');

-- Token metadata including creation time
CREATE TABLE token_metadata (
    token_address TEXT PRIMARY KEY,
    name TEXT,
    symbol TEXT,
    decimals INTEGER,
    created_at TIMESTAMPTZ NOT NULL,  -- Token creation time
    first_pool_created_at TIMESTAMPTZ, -- First liquidity pool creation
    creator_address TEXT,
    total_supply NUMERIC,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_token_age ON token_metadata (created_at);
CREATE INDEX idx_token_creator ON token_metadata (creator_address);

-- Strategy configurations
CREATE TABLE strategy_configs (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    conditions JSONB NOT NULL,  -- Flexible condition storage
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

-- Backtesting results
CREATE TABLE backtest_results (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER REFERENCES strategy_configs(id),
    strategy_params JSONB,
    date_range TSTZRANGE,
    total_signals INTEGER,
    trades_executed INTEGER,
    win_rate NUMERIC,
    total_pnl NUMERIC,
    sharpe_ratio NUMERIC,
    max_drawdown NUMERIC,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_backtest_strategy ON backtest_results (strategy_id);
CREATE INDEX idx_backtest_status ON backtest_results (status);

-- Individual trades for analysis
CREATE TABLE backtest_trades (
    id SERIAL PRIMARY KEY,
    backtest_id INTEGER REFERENCES backtest_results(id),
    token_address TEXT NOT NULL,
    signal_time TIMESTAMPTZ,
    entry_time TIMESTAMPTZ,
    entry_price NUMERIC,
    exit_time TIMESTAMPTZ,
    exit_price NUMERIC,
    pnl_percent NUMERIC,
    pnl_usd NUMERIC,
    hold_duration INTERVAL,
    exit_reason TEXT,
    signal_metrics JSONB
);

CREATE INDEX idx_trades_backtest ON backtest_trades (backtest_id);
CREATE INDEX idx_trades_token ON backtest_trades (token_address);

-- Insert default strategies
INSERT INTO strategy_configs (name, description, conditions) VALUES 
(
    'Early Token Momentum',
    'Detect momentum in tokens less than 3 days old',
    '{
        "token_age": {
            "enabled": true,
            "operator": "less_than",
            "value": 3,
            "unit": "days"
        },
        "liquidity": {
            "enabled": true,
            "operator": "greater_than",
            "value": 10000,
            "unit": "USD"
        },
        "volume_window": {
            "enabled": true,
            "window_seconds": 30,
            "operator": "greater_than_equal",
            "value": 5000,
            "unit": "USD"
        },
        "market_cap": {
            "enabled": true,
            "operator": "less_than",
            "value": 300000,
            "unit": "USD"
        },
        "large_buys": {
            "enabled": true,
            "min_count": 5,
            "min_amount": 1000,
            "window_seconds": 30
        }
    }'::jsonb
),
(
    'Micro Cap Surge',
    'Detect surges in very small cap tokens',
    '{
        "market_cap": {
            "enabled": true,
            "operator": "less_than",
            "value": 100000,
            "unit": "USD"
        },
        "liquidity": {
            "enabled": true,
            "operator": "greater_than",
            "value": 5000,
            "unit": "USD"
        },
        "volume_window": {
            "enabled": true,
            "window_seconds": 10,
            "operator": "greater_than",
            "value": 2000,
            "unit": "USD"
        },
        "large_buys": {
            "enabled": true,
            "min_count": 3,
            "min_amount": 500,
            "window_seconds": 10
        }
    }'::jsonb
),
(
    'Fresh Launch Detection',
    'Catch tokens in first hour of trading',
    '{
        "token_age": {
            "enabled": true,
            "operator": "less_than",
            "value": 1,
            "unit": "hours"
        },
        "liquidity": {
            "enabled": true,
            "operator": "greater_than",
            "value": 5000,
            "unit": "USD"
        },
        "volume_window": {
            "enabled": true,
            "window_seconds": 30,
            "operator": "greater_than",
            "value": 1000,
            "unit": "USD"
        },
        "large_buys": {
            "enabled": true,
            "min_count": 3,
            "min_amount": 500,
            "window_seconds": 30
        }
    }'::jsonb
);