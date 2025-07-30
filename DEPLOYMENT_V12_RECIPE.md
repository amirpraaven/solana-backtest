# Deploying and Running v1.2 Recipe on Railway Dashboard

## 🚀 Quick Start

### 1. Deploy to Railway

1. **Connect GitHub Repo to Railway**
   ```bash
   # First, merge the v1.2 branch to main
   git checkout main
   git merge feature/backtest-recipe-v1.2
   git push origin main
   ```

2. **In Railway Dashboard:**
   - Create new project
   - Connect GitHub repo
   - Railway will auto-detect the configuration and build

3. **Set Environment Variables in Railway:**
   ```env
   # Required API Keys
   HELIUS_API_KEY=your_helius_business_key
   BIRDEYE_API_KEY=your_birdeye_key
   
   # Database (Railway provides PostgreSQL)
   DATABASE_URL=postgresql://user:pass@host:5432/dbname
   
   # Redis (Add Redis service in Railway)
   REDIS_URL=redis://host:6379
   
   # Optional
   ENVIRONMENT=production
   LOG_LEVEL=INFO
   ```

### 2. Access Your Dashboard

Once deployed, Railway provides a URL like: `https://your-app.railway.app`

## 📊 Using the v1.2 Recipe

### Method 1: Via Web Dashboard

1. **Navigate to Strategy Manager Tab**
   - Go to `https://your-app.railway.app`
   - Click "Strategy Manager" tab

2. **Create v1.2 Strategy from Template**
   - Look for "Backtest Recipe v1.2" in templates
   - Click "Use Template"
   - Strategy will be created with all v1.2 settings

3. **Run Backtest**
   - Go to "Backtest Runner" tab
   - Select your v1.2 strategy
   - Choose tokens to test (or use batch mode)
   - Set date range and click "Run Backtest"

4. **View Results**
   - Go to "Results" tab
   - See performance metrics, charts, and trade details

### Method 2: Via API

1. **Create Strategy from Template**
   ```bash
   curl -X POST https://your-app.railway.app/strategies/create-from-template \
     -H "Content-Type: application/json" \
     -d '{
       "template_name": "backtest_recipe_v12",
       "custom_name": "My v1.2 Strategy"
     }'
   ```

2. **Run Backtest**
   ```bash
   curl -X POST https://your-app.railway.app/strategies/backtest \
     -H "Content-Type: application/json" \
     -d '{
       "strategy_id": 1,
       "token_addresses": ["TokenAddress1", "TokenAddress2"],
       "start_date": "2024-01-01",
       "end_date": "2024-01-31",
       "initial_capital": 10000
     }'
   ```

3. **Check Results**
   ```bash
   curl https://your-app.railway.app/strategies/backtest/{backtest_id}
   ```

## 🎯 What the Dashboard Shows

### Real-Time Metrics
- **Win Rate**: Percentage of profitable trades
- **Total Return**: Overall profit/loss
- **Sharpe Ratio**: Risk-adjusted returns
- **Max Drawdown**: Largest peak-to-trough decline

### Visual Charts
- **Equity Curve**: Portfolio value over time
- **Trade Distribution**: Winners vs losers
- **Entry/Exit Points**: When trades occurred
- **MC Band Analysis**: Which bands triggered most

### Trade Details
- **Entry Signals**: Which 5-minute slice triggered entry
- **Big Buy Activity**: Exact transactions that met criteria
- **Exit Execution**: When 2x/7x targets were hit
- **Position Sizes**: 1 SOL entries as configured

## 🔧 Advanced Features

### Batch Testing All New Tokens
```bash
# Test all tokens created in last 30 days
curl -X POST https://your-app.railway.app/batch/backtest/new-tokens \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": 1,
    "hours_back": 720,
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  }'
```

### Live Monitoring
The system can also monitor tokens in real-time:
1. Enable token monitoring in settings
2. System will track all new tokens ≤ 30 days old
3. Alerts when v1.2 conditions are met

## 📈 Expected Results Dashboard

### Performance Overview
```
Strategy: Backtest Recipe v1.2
Period: Jan 1-31, 2024
Tokens Analyzed: 156
Signals Generated: 23
Trades Executed: 23

Win Rate: 35%
Average Win: +245%
Average Loss: -15%
Profit Factor: 2.8
Total Return: +127%
```

### Signal Breakdown
```
MC Band Distribution:
≤ $100k:  45% of signals
≤ $400k:  30% of signals  
≤ $1m:    20% of signals
≤ $2m:     5% of signals

Exit Performance:
2x Target Hit: 8 trades (35%)
7x Target Hit: 3 trades (13%)
Stop/Time Exit: 12 trades (52%)
```

## 🚨 Monitoring & Alerts

Railway provides:
- **Health Checks**: Auto-restarts if app crashes
- **Metrics**: CPU, memory, request counts
- **Logs**: Real-time log streaming
- **Alerts**: Set up notifications for errors

## 💡 Tips for Best Results

1. **Data Quality**: Ensure Helius/Birdeye APIs are working
2. **Time Range**: Test different market conditions
3. **Token Selection**: Focus on high-activity tokens
4. **Performance**: Use batch mode for large-scale tests

## 🛠️ Troubleshooting

### If no results appear:
1. Check API keys are valid
2. Verify database has transaction data
3. Ensure tokens match age criteria (≤ 30 days)
4. Check Railway logs for errors

### Common Issues:
- **"No signals found"**: Market conditions may not match
- **"API rate limit"**: Upgrade API plans or reduce batch size
- **"Database timeout"**: Scale up Railway resources

## 📞 Support

- Railway Dashboard: Check deployment logs
- Application Logs: `/logs` endpoint
- Health Check: `/health/simple`
- API Docs: `https://your-app.railway.app/docs`