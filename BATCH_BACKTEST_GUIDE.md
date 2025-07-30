# Batch Backtest Guide - Test ALL New Tokens

## 🚀 What is Batch Backtesting?

Batch backtesting allows you to test your strategy against **ALL tokens created within a specific timeframe**. Instead of manually selecting tokens, the system automatically:

1. Finds all tokens created in the last X hours
2. Filters by liquidity requirements
3. Runs your strategy on each token
4. Shows you which tokens would have been profitable

## 📊 How to Use It

### Step 1: Create Your Strategy
Go to the "Strategies" tab and create a strategy with your conditions:
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
    "value": 40000
  }
}
```

### Step 2: Go to "Batch Test New Tokens" Tab
Configure your batch test:

- **Time Range**: How far back to look for new tokens (1 hour to 7 days)
- **Minimum Liquidity**: Only test tokens with at least this much liquidity
- **Max Tokens**: Limit to avoid long processing times (max 100)
- **Backtest Days**: How many days of history to test per token

### Step 3: Run the Batch Test
Click "Test All New Tokens" and the system will:
1. Fetch all tokens created in your timeframe
2. Sync real blockchain data for each token
3. Run your strategy on each one
4. Show progress in real-time

### Step 4: View Results
You'll see:
- **Summary**: Total tokens tested, profitable count, total P&L
- **Best/Worst**: Which tokens performed best and worst
- **Success Rate**: Percentage of profitable tokens
- **Detailed Table**: Every token with its signals, trades, and P&L

## 🎯 Example Use Cases

### 1. Find Profitable New Launches
```
Time Range: Last 24 hours
Min Liquidity: $10,000
Strategy: Your momentum strategy
Result: See which of today's launches would have been profitable
```

### 2. Test Different Time Windows
```
Run 1: Last 1 hour (very new tokens)
Run 2: Last 24 hours (day-old tokens)
Run 3: Last 7 days (week-old tokens)
Compare: Which age group performs best?
```

### 3. Optimize Liquidity Filters
```
Test 1: Min $5,000 liquidity
Test 2: Min $20,000 liquidity
Test 3: Min $50,000 liquidity
Find: Sweet spot for your strategy
```

## 📈 Understanding Results

### Summary Metrics
- **Tokens Tested**: How many tokens met your criteria
- **Profitable Tokens**: How many made money
- **Total P&L**: Combined profit/loss across all tokens
- **Success Rate**: Win percentage

### Individual Token Results
- **Age**: How old the token was when created
- **Liquidity**: Current liquidity in USD
- **Signals**: How many times your strategy triggered
- **Trades**: Actual trades executed
- **P&L**: Profit or loss for that token
- **Return %**: Percentage return

## 🔥 Pro Tips

1. **Start Small**: Test last 1-2 hours first to verify it works
2. **Adjust Liquidity**: Higher liquidity = safer but fewer opportunities
3. **Compare Strategies**: Run multiple strategies on same token set
4. **Time of Day**: Some launch times may be more profitable
5. **Save Winners**: Note which tokens performed well for manual analysis

## 📊 API Endpoints (Advanced)

### Run Batch Backtest
```bash
POST /batch/backtest/new-tokens
{
  "strategy_id": 1,
  "hours_back": 24,
  "min_liquidity": 10000,
  "max_tokens": 50,
  "backtest_days": 7
}
```

### Check Status
```bash
GET /batch/status/{job_id}
```

### Get Results
```bash
GET /batch/results/{job_id}
```

## ⚡ Performance Notes

- Testing 20 tokens takes ~2-5 minutes
- Testing 100 tokens takes ~10-20 minutes
- Results are cached for 24 hours
- Multiple batch tests can run simultaneously

## 🎯 Your Specific Use Case

For your 30-second momentum strategy:
1. Set time range to last 24-48 hours
2. Min liquidity $40,000 (your requirement)
3. The system will find ALL tokens matching your market cap limit
4. See which ones had the volume spikes you're looking for

This is perfect for finding tokens that "popped" shortly after launch!