# Trading Alert System — Trader's Guide

> Set up your alert strategy, validate it with backtesting, and go live with confidence.

**For:** Traders · End users · Anyone configuring their alert strategy
**Date:** May 29, 2026
**Read Time:** 15-20 minutes

> 💡 **Quick Start:** Ready to set up? Jump to [Getting Started: Step-by-Step](#getting-started-step-by-step)

---

## What This System Does For You

Two modes — one for live trading, one for strategy validation:

### 🟢 LIVE Mode — Real-Time Alerts (Production)
Monitor multiple stock symbols in real-time using live market data. When price movements match your configured alert criteria, you receive instant notifications.

### 🔵 REPLAY Mode — Historical Backtesting (Strategy Validation)
Test your alert strategies against historical market data to see how they would have performed. This helps you validate and optimize your approach before running it live.

---

## Everything You Get

✅ **Real-Time Price Monitoring**
- Monitor multiple symbols simultaneously
- Detect price movements 24/7
- Instant notifications when alerts trigger

✅ **8 Alert Approaches: TRADE (5 active) + ANNOUNCE (3)**

**TRADE Approaches** (precise entry signals, executor pattern):
- Strong Candle Detection
- Consistent Momentum
- VRA (Volume Reversal Analysis)
- Ichimoku Patterns
- Reversal Anchor Signal Candle

**ANNOUNCE Approaches** (broad market movement alerts):
- Large Candle
- Large Volume Candle
- Price Movement

✅ **Multi-Channel Notifications**
- Email ✅ (validated)
- Slack ✅ (validated)
- Ntfy ✅ (validated)
- SMS ⚠️ (not yet validated)

✅ **Backtesting & Analysis**
- Test strategies on historical data
- Simulate trades and see profitability
- Optimize profit/loss thresholds
- Identify key support/resistance levels

✅ **Performance Metrics**
- See how each alert approach performed
- Profitability analysis by approach and time period
- Visual reports and dashboards
- Data-driven recommendations

✅ **Configuration Flexibility**
- Choose which symbols to monitor
- Select which alert approaches to use
- Set your own profit targets and stop losses
- Customize notification preferences

---

## How It Works: End-to-End Flow

### Step 1: You Configure Your Strategy
You define:
- Which symbols to monitor (VN30F1M, BTCUSDT-PERP, etc.)
- Which alert approaches match your trading style
- Your profit targets (e.g., +2% gain)
- Your stop losses (e.g., -1% loss)
- How you want to be notified (Email, Slack, Ntfy)

**Example:**
```
Monitor: VN30F1M
Alert Types: Consistent Momentum + Strong Candle
Profit Target: +1.5%
Stop Loss: -0.8%
Notifications: Email + Slack
```

### Step 2: System Monitors in Real-Time
While your strategy runs:
- Fetches latest price data every minute (or your chosen interval)
- Analyzes prices using your selected approaches
- Detects when conditions match your alert criteria
- Triggers notifications immediately

### Step 3: You Receive Alerts
When an alert is triggered:
- Email notification (with details)
- Slack notification (instant)
- Ntfy web notification (if subscribed)
- Alert summary including price, time, approach used
- Each notification includes environment context (LIVE/REPLAY) and deployment mode footer

### Step 4: Trade Execution

This step differs by symbol:

**VN30F1M — Manual execution**
- You receive the alert and execute the trade yourself
- Vietstock is a data provider only — it does not support order placement via API
- The system's job ends at notification delivery

**BTCUSDT-PERP — Automated execution (optional)**
- When a TRADE alert is confirmed, the system can automatically place a **DCA bracket order** on Binance Futures:
  - 7-rung LIMIT entry ladder (dollar-cost averaging into the position)
  - Take-profit order (Binance algo conditional)
  - Stop-loss order (Binance algo conditional)
- The bracket self-manages: TP/SL recalculate automatically as more ladder entries fill
- Controlled by `TRADING_EXECUTION_EXPIRED_MINUTES` — stale alerts are skipped

### Step 5: System Tracks Performance
The system records:
- When alert triggered
- Actual trade result
- Whether target was hit
- Whether stop loss was hit
- Overall profitability

### Step 6: Analyze & Optimize
Using the performance data:
- See which approaches work best
- Identify best times of day for your strategy
- Find optimal profit/loss thresholds
- Get recommendations for improvements

---

## The 8 Alert Approaches Explained

The system has **8 alert approaches** split into two categories.

### 🟦 TRADE Approaches (5 active)
Precise entry signals — uses an executor pattern where each approach is independently evaluated. Alerts from these approaches are designed for actionable trade entries.

> **Note:** `VOLUME_SPIKE_CONFIRMATION` and `CONSISTENT_VOLUME_ANCHOR` exist in the codebase but are currently **archived** (not wired into execution) and are not counted here.

### 🔸 Strong Candle Detection
- Looks for dominant candles (large bodies, small wicks)
- Indicates strong buyer/seller commitment
- Best for: Trend confirmation

### 🔸 Consistent Momentum
- Detects repeated price movements in same direction
- Measures consistency of the trend
- Best for: Momentum plays

### 🔸 Volume Reversal Analysis (VRA)
- Detects trend reversals with volume confirmation
- When price goes one way but volume goes opposite
- Best for: Counter-trend entries

### 🔸 Ichimoku Patterns
- Japanese charting technique
- Multiple components (Kijun, Tenkan, Kumo)
- Best for: Trend and support/resistance

### 🔸 Reversal Anchor Signal Candle
- Detects trend reversals using a 3-candle logic:
   1. **Anchor Candle**: Largest body in lookback window
   2. **Signal Candle**: Highest volume at/after anchor
   3. **Alert Candle**: Final candle with extreme wick/price action
- Designed to catch sharp reversals with volume and price confirmation
- Best for: Early reversal entries after strong trends

---

### 🟧 ANNOUNCE Approaches (3)
Broad market movement alerts — uses `AnnouncementAlerterBase`. These are informational signals about notable candle or price activity, not necessarily direct trade entries.

### 🔹 Large Candle
- Detects unusually large candlestick bodies
- Indicates exceptional price movement in a single bar
- Best for: Awareness of volatility spikes

### 🔹 Large Volume Candle
- Detects candles with both large body **and** exceptional volume
- Confirms that institutional or large-player activity is driving the move
- Best for: Spotting high-conviction market moves

### 🔹 Price Movement
- Detects significant percentage price movement over a period
- Threshold-based: alerts when price moves beyond configured levels
- Best for: Trend initiation awareness and momentum context

---

## Backtesting — Validate Before Going Live

### What It Does

Tests how your alert strategy would have performed on historical data.

### How It Works

1. **You specify a date range**
   - Example: "Test on last 30 days of data"

2. **System simulates all alerts for that period**
   - Generates all alerts that would have triggered
   - Records when each alert occurred
   - Tracks what would have happened after each alert

3. **System tests profit/loss scenarios**
   - Profit Target: Fixed at 2.0 points (per alert magnitude)
   - Stop Loss Levels: Tests 9 different stop-loss thresholds:
     - 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0 points
   - Creates 9 separate scenarios (1 profit target × 9 stop-loss levels)
   - Each scenario shows different profitability metrics

4. **System generates performance reports**
   - Shows which approach works best
   - Shows best time periods
   - Shows optimal stop-loss thresholds
   - Provides specific recommendations for risk management

### Example Report Output

```
BACKTESTING RESULTS: VN30F1M (REPLAY mode)

Approach: Strong Candle Detection
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total alerts triggered: [N]
Alerts with follow-through: [X]
Alerts stopped out: [Y]

Best performing time windows: [reported per run]

Approach: Consistent Momentum
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total alerts triggered: [N]
Alerts with follow-through: [X]
Alerts stopped out: [Y]

Best performing time windows: [reported per run]
```

> **Note:** Specific win rates and trade counts depend entirely on the historical data period and configuration used in each REPLAY run. The system does not produce pre-set performance guarantees.

### Advanced Features (Optional)

**Support/Resistance Detection**
- Analyzes historical price data
- Identifies key support and resistance levels
- Suggests where to place stops and targets

**Price Optimization**
- Calculates optimal profit targets
- Calculates optimal stop losses
- Auto-updates your configuration with best values

**Performance Analysis**
- Statistical analysis of all approaches
- Time-of-day analysis (when best to trade)
- Volatility analysis
- Correlation analysis with market conditions

---

## Data Sources Supported

The system can fetch market data from:

- **Vietstock** - Vietnamese stocks and indices
- **Binance API** - Cryptocurrencies via Binance
- **Binance CCXT** - Cryptocurrencies via CCXT integration

You can mix and match data sources:
```
Monitor VN30F1M → via Vietstock
Monitor BTCUSDT-PERP → via Binance API
```

---

## Configuration Examples — 4 Trader Profiles

### Example 1: Conservative Trader
```
Symbols: VN30F1M (Vietnam futures)
Approach: Strong Candle + Consistent Momentum
Profit Target: 2.0 points (automatic, fixed)
Stop Loss: 3.0-3.5 points (testing multiple levels)
Alerts: Email only
Time Frame: Only during Vietnam trading hours (9:15-15:30)
Backtesting: Aim for 75%+ win rate
```

### Example 2: Active Day Trader
```
Symbols: VN30F1M (Vietnam futures, 1-minute data)
Approach: Reversal Anchor Signal Candle + Strong Candle
Profit Target: 2.0 points (automatic, fixed)
Stop Loss: 2.5-4.0 points (tighter stops for quick scalps)
Alerts: Email + Slack (real-time)
Time Frame: Full trading day
Backtesting: Aim for 60%+ win rate
```

### Example 3: Crypto Trader
```
Symbols: BTCUSDT-PERP (Bitcoin perpetual futures)
Approach: Ichimoku + VRA
Profit Target: 2.0 points (automatic, fixed)
Stop Loss: 4.0-6.0 points (volatile asset, wider stops)
Alerts: Email + Slack
Time Frame: 24/7
Backtesting: Test multiple stop-loss levels
```

### Example 4: Multi-Strategy Portfolio
```
Symbols: VN30F1M, BTCUSDT-PERP
Approach: Multiple (rotate by asset)
Profit Target: 2.0 points (consistent across all)
Stop Loss: 3.0-5.0 points (tests 9 different levels)
Alerts: Email + Slack + Ntfy
Backtesting: Compare performance across all 9 scenarios
```

---

## Getting Started: Step-by-Step

### Phase 1: Setup (15 minutes)
1. Choose which symbols to monitor
2. Select your alert approaches
3. Set profit targets
4. Set stop losses
5. Configure notifications

### Phase 2: Backtest Your Strategy (30 minutes)
1. Choose a date range (30-60 days recommended)
2. Run backtesting on historical data
3. Review the performance report
4. Check win rate and profit factor
5. Adjust if needed

### Phase 3: Validate with REPLAY Mode (1-2 weeks)
1. Run in REPLAY mode against recent historical data
2. See how alerts would have performed in real time
3. Adjust thresholds based on observations
4. Build confidence in your strategy before going live

### Phase 4: Go Live (Start small)
1. Start with minimum position sizes
2. Scale up gradually as confidence builds
3. Monitor daily for adjustments
4. Re-backtest monthly to stay optimized

---

## Key Metrics to Track

### Win Rate
Percentage of alerts that result in profitable trades.
- Healthy range: 50-70% (you don't need to be right every time)

### Profit Factor
Ratio of gross profit to gross loss.
- Healthy range: 1.5x to 3.0x (for every $1 lost, make $1.50-3.00)

### Risk/Reward Ratio
Average profit per win vs. average loss per loss.
- Healthy range: 1:1 to 3:1 (for every $1 at risk, win $1-3)

### Drawdown
Maximum loss from peak to trough.
- Acceptable: Less than 20% of account

### Monthly Returns
Percentage gain per month.
- Realistic range: 5-15% per month (anything higher is suspect)

---

## ⚠️ Important Disclaimers

⚠️ **Past Performance ≠ Future Results**
- Backtesting shows what *would* have happened
- Real markets can behave differently
- Always start with small position sizes

⚠️ **All Trading Involves Risk**
- You can lose money
- Use stop losses
- Never risk more than you can afford to lose
- Don't trade on borrowed money you can't repay

⚠️ **Strategy Optimization Risk**
- Over-optimizing on historical data leads to curve-fitting
- Test on data you haven't seen before
- Use conservative settings
- Re-test periodically

⚠️ **Black Swan Events**
- Market gaps, halts, and limit moves can happen
- Your stop loss might not fill at expected price
- Maintain additional reserves

---

## FAQ - Common Questions

**Q: How often do alerts trigger?**
A: Depends on market conditions and your settings. Typically 10-30 alerts per symbol per month.

**Q: Can I use multiple approaches at once?**
A: Yes! You can combine approaches for more confirmation.

**Q: What if I miss an alert?**
A: All alerts are logged in the system. You can review them later.

**Q: Can I run on multiple symbols?**
A: Yes! System monitors all configured symbols simultaneously.

**Q: How accurate is the backtesting?**
A: Very accurate. It uses actual historical OHLCV (Open, High, Low, Close, Volume) data and real spread/slippage assumptions.

**Q: Can I modify my strategy while running?**
A: Yes, but be careful. Changes apply to new alerts only.

**Q: What if the data connection fails?**
A: System automatically reconnects and resumes monitoring. No alerts are lost.

---

## Support & Resources

- **Technical Issues:** Contact support team
- **Strategy Questions:** Review backtesting results
- **Data Quality:** Validate against your broker's charts
- **Performance Analysis:** Run performance reports quarterly

---

## Next Steps

1. **Start with one symbol** - Build confidence
2. **Run extensive backtest** - Validate your approach
3. **Begin paper trading** - See real-time performance
4. **Scale gradually** - Increase position sizes slowly
5. **Monitor monthly** - Re-backtest and adjust

Your trading journey starts here. Good luck! 📈
