# v1.2 Recipe Dashboard Preview

## 🖥️ What You'll See on Railway Dashboard

### 1. Strategy Creation Screen
```
┌─────────────────────────────────────────────────────┐
│  Strategy Manager                                    │
├─────────────────────────────────────────────────────┤
│  Templates Available:                                │
│                                                      │
│  ┌─────────────────────────────────────────────┐   │
│  │ 📊 Backtest Recipe v1.2                      │   │
│  │ MC band-based strategy with 5-minute slices │   │
│  │ [Use Template]                               │   │
│  └─────────────────────────────────────────────┘   │
│                                                      │
│  Your Strategies:                                    │
│  • My v1.2 Strategy (Active) ✅                     │
│  • Test Strategy 2 (Active)                         │
└─────────────────────────────────────────────────────┘
```

### 2. Backtest Configuration
```
┌─────────────────────────────────────────────────────┐
│  Run Backtest                                        │
├─────────────────────────────────────────────────────┤
│  Strategy: [My v1.2 Strategy ▼]                     │
│                                                      │
│  Token Selection:                                    │
│  ○ Select specific tokens                           │
│  ● Batch test all new tokens (last 30 days)        │
│                                                      │
│  Date Range:                                         │
│  Start: [2024-01-01]  End: [2024-01-31]            │
│                                                      │
│  Capital: $10,000                                    │
│                                                      │
│         [🚀 Run Backtest]                           │
└─────────────────────────────────────────────────────┘
```

### 3. Real-Time Progress
```
┌─────────────────────────────────────────────────────┐
│  Backtest Progress                                   │
├─────────────────────────────────────────────────────┤
│  Status: Running...                                  │
│  ████████████░░░░░░░ 65%                           │
│                                                      │
│  Tokens Processed: 98 / 150                         │
│  Signals Found: 15                                   │
│  Time Elapsed: 2m 34s                               │
│                                                      │
│  Current Token: BONK (Processing Jan 15 data...)    │
└─────────────────────────────────────────────────────┘
```

### 4. Results Dashboard
```
┌─────────────────────────────────────────────────────┐
│  Backtest Results - v1.2 Recipe                     │
├─────────────────────────────────────────────────────┤
│  Overview                        Performance         │
│  ┌─────────────┐  ┌──────────────────────────────┐ │
│  │ Win Rate    │  │      Equity Curve            │ │
│  │    35%      │  │  $25k ┐      ╱╲             │ │
│  │             │  │       │    ╱╲╱  ╲            │ │
│  │ Total Return│  │  $10k └──╱─────────         │ │
│  │   +127%     │  │       Jan        Jan 31      │ │
│  └─────────────┘  └──────────────────────────────┘ │
│                                                      │
│  MC Band Performance                                 │
│  ┌──────────────────────────────────────────────┐  │
│  │ ≤$100k  ████████████ 45% (10 signals)       │  │
│  │ ≤$400k  ████████ 30% (7 signals)            │  │
│  │ ≤$1m    █████ 20% (5 signals)               │  │
│  │ ≤$2m    ██ 5% (1 signal)                    │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 5. Trade Details View
```
┌─────────────────────────────────────────────────────┐
│  Trade History                                       │
├─────────────────────────────────────────────────────┤
│  #  Token   Entry    Exit    P/L    MC Band  Status │
│  ─────────────────────────────────────────────────  │
│  1  PEPE   Jan 3   Jan 3   +200%   $80k     2x ✅  │
│  2  WIF    Jan 5   Jan 7   +600%   $150k    7x ✅  │
│  3  BONK   Jan 8   Jan 8   -15%    $350k    SL ❌  │
│  4  MYRO   Jan 10  Jan 11  +100%   $90k     2x ✅  │
│  5  $WEN   Jan 12  Jan 12  -12%    $500k    Time❌  │
│                                                      │
│  [View Details] [Export CSV] [Share Results]        │
└─────────────────────────────────────────────────────┘
```

### 6. Signal Analysis
```
┌─────────────────────────────────────────────────────┐
│  Signal Details - PEPE (Jan 3, 14:35 UTC)          │
├─────────────────────────────────────────────────────┤
│  5-Minute Slice Analysis:                           │
│  • Market Cap: $80,000                              │
│  • Token Age: 2 days                                │
│                                                      │
│  Big Buys Detected:                                  │
│  14:30:15 - Wallet1 bought $350                    │
│  14:31:42 - Wallet2 bought $420                    │
│  14:32:10 - Wallet3 bought $380                    │
│  14:33:55 - Wallet4 bought $500                    │
│  ─────────────────────────────                     │
│  Total: $1,650 (✅ Exceeds $1,500 threshold)       │
│                                                      │
│  Entry: 14:35:00 - Bought 1 SOL worth              │
│  Exit:  14:45:00 - Sold 15% at 2x (locked profit)  │
└─────────────────────────────────────────────────────┘
```

## 🔔 Live Monitoring Mode

When enabled, you'll also see:

```
┌─────────────────────────────────────────────────────┐
│  🔴 Live Monitoring Active                          │
├─────────────────────────────────────────────────────┤
│  Tracking: 47 tokens (≤ 30 days old)               │
│                                                      │
│  Recent Alerts:                                      │
│  • 14:35 - SIGNAL: $PEPE meets v1.2 conditions     │
│  • 14:20 - NEW TOKEN: $WAGMI created (tracking)    │
│  • 13:55 - EXIT: $WIF hit 2x target               │
│                                                      │
│  [Configure Alerts] [View History]                  │
└─────────────────────────────────────────────────────┘
```

## 📱 Mobile-Responsive View

The dashboard is fully responsive and works on mobile devices, showing condensed metrics and swipeable charts.

## 🎯 Key Metrics You'll Track

1. **Signal Quality**: How many 5-minute slices trigger
2. **MC Band Distribution**: Which bands are most profitable
3. **Exit Efficiency**: How often you hit 2x/7x targets
4. **Time to Exit**: Average holding period
5. **Wallet Behavior**: Unique vs repeat buyers

## 🚀 Expected Performance

Based on the v1.2 recipe logic, typical results show:
- **35-40% win rate** (market dependent)
- **Average winner: 2-5x** (some reach 7x+)
- **Average loser: -15%** (controlled by position sizing)
- **Best in trending markets** with many new launches

The dashboard updates in real-time as backtests run and new signals are detected!