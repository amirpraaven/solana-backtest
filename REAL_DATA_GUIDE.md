# Real Data Integration Guide

## Overview
The Solana Backtest system is now fully configured to work with real-world blockchain data from Solana. The system can fetch and analyze actual transaction data, token prices, liquidity, and market metrics.

## Current Status
- ✅ Token discovery with real-time trending data
- ✅ Transaction syncing from Helius API
- ✅ Price and liquidity data from Birdeye API
- ✅ Async job processing for non-blocking operations
- ✅ Real-time progress tracking
- ✅ Automatic data ingestion pipeline

## API Configuration
The system uses your API keys configured in Railway:
- **HELIUS_API_KEY**: For transaction data
- **BIRDEYE_API_KEY**: For token prices and market data

## Key Endpoints

### 1. System Status
Check if real data is enabled:
```
GET /system/status
```
This shows:
- Current mode (real_data vs demo_data)
- API configuration status
- Data statistics
- Service status

### 2. API Validation
Verify API keys are working:
```
GET /api/validate
```

### 3. Token Discovery (Real Data)
Find real tokens on Solana:
```
GET /tokens/trending?time_frame=1h&sort_by=volume
GET /tokens/new-listings?max_age_hours=24
GET /tokens/search?query=BONK
```

### 4. Data Synchronization
Sync historical data for any token:
```
POST /sync/token/{token_address}?days_back=7
```

Check sync status:
```
GET /sync/status/{token_address}
GET /sync/active
```

### 5. Run Backtests with Real Data
1. Use the Token Selector to find real tokens
2. Select your strategy
3. Run backtest - it will use real historical data

## How It Works

### Real-Time Data Flow
1. **Token Discovery**: Fetches current trending tokens from Birdeye
2. **Data Sync**: When you select a token, it syncs:
   - All transactions from Helius
   - Price/volume data from Birdeye
   - Pool states and liquidity metrics
3. **Backtesting**: Uses the synced real data to simulate trades

### Your Specific Algorithm Support
The system fully supports your requirements:
- **30-second windows**: Real transaction data with second-level precision
- **Large buy detection**: Actual USD amounts from on-chain data
- **Liquidity filtering**: Real-time liquidity from DEX pools
- **Market cap limits**: Current market cap from Birdeye

## Usage Example

### 1. Find a Token
```javascript
// Frontend automatically uses real data
const response = await fetch('/tokens/trending?time_frame=30m');
const { tokens } = await response.json();
```

### 2. Sync Its Data
```javascript
const syncResponse = await fetch(`/sync/token/${token.address}?days_back=7`, {
  method: 'POST'
});
const { job_id } = await syncResponse.json();
```

### 3. Run Backtest
Configure your strategy with exact conditions:
```json
{
  "volume_window": {
    "enabled": true,
    "window_seconds": 30,
    "value": 5000
  },
  "large_buys": {
    "enabled": true,
    "min_amount": 1000,
    "min_count": 1,
    "window_seconds": 30
  },
  "liquidity": {
    "enabled": true,
    "operator": "greater_than",
    "value": 40000
  }
}
```

## Performance Notes
- Initial token sync takes 10-60 seconds depending on activity
- Subsequent backtests use cached data (instant)
- Real-time monitoring updates every 5 seconds
- API rate limits are automatically handled

## Troubleshooting
1. If token discovery shows no results:
   - Check `/api/validate` endpoint
   - Verify API keys in Railway dashboard

2. If sync fails:
   - Check `/sync/status/{token_address}` for errors
   - Some new tokens may have limited historical data

3. If backtests are slow:
   - First run syncs data (normal)
   - Subsequent runs should be fast (cached)

## Data Accuracy
- Transaction data: Direct from Solana blockchain
- Prices: Real-time from DEX pools
- Volume: Actual traded amounts in USD
- Liquidity: Current pool reserves

The system is now 100% functional with real Solana data!