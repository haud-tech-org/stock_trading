# Architecture Guide for Trading Clients

**Date:** April 8, 2026  
**Target Audience:** End users, traders, business stakeholders, potential clients  
**Purpose:** Understand the system from a trading and business perspective  
**Reading Time:** 15-20 minutes

---

## What This System Does

This is a **real-time trading alert system** that automatically detects trading opportunities and notifies you through your preferred channel (Email, SMS, Telegram).

The system works in two ways:

### 🟢 LIVE Mode: Real-Time Monitoring (Production)
Monitor multiple stock symbols in real-time using live market data. When price movements match your configured alert criteria, you receive instant notifications.

### 🔵 REPLAY Mode: Historical Testing (Backtesting)
Test your alert strategies against historical market data to see how they would have performed. This helps you validate and optimize your approach before running it live.

---

## Key Capabilities at a Glance

✅ **Real-Time Price Monitoring**
- Monitor multiple symbols simultaneously
- Detect price movements 24/7
- Instant notifications when alerts trigger

✅ **5+ Different Alert Approaches**
- Strong Candle Detection
- Consistent Momentum
- Volume Spike Confirmation
- VRA (Volume Reversal Analysis)
- Ichimoku Patterns
- And more...

✅ **Multi-Channel Notifications**
- Email alerts
- SMS text messages
- Web notifications
- Mix and match as desired

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

## How It Works: The Complete Flow

### Step 1: You Configure Your Strategy
You define:
- Which symbols to monitor (VN30, VN30F1M, BTC, ETH, etc.)
- Which alert approaches match your trading style
- Your profit targets (e.g., +2% gain)
- Your stop losses (e.g., -1% loss)
- How you want to be notified (email, SMS, etc.)

**Example:**
```
Monitor: VN30F1M
Alert Types: Consistent Momentum + Strong Candle
Profit Target: +1.5%
Stop Loss: -0.8%
Notifications: Email + SMS
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
- SMS notification (instant)
- Web notification (if subscribed)
- Alert summary including price, time, approach used

### Step 4: You Execute Your Trade
Based on the alert, you can:
- Enter a long position
- Enter a short position
- Set stop loss at your defined level
- Set profit target at your configured level

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

## Understanding Alert Approaches

Each approach looks for different signals:

### 🔸 Strong Candle Detection
- Looks for dominant candles (large bodies, small wicks)
- Indicates strong buyer/seller commitment
- Best for: Trend confirmation

### 🔸 Consistent Momentum
- Detects repeated price movements in same direction
- Measures consistency of the trend
- Best for: Momentum plays

### 🔸 Volume Spike Confirmation
- Confirms price movements with unusual volume
- High volume = stronger signal
- Best for: Breakout trades

### 🔸 Volume Reversal Analysis (VRA)
- Detects trend reversals with volume confirmation
- When price goes one way but volume goes opposite
- Best for: Counter-trend entries

### 🔸 Consistent Volume Anchor
- Uses volume as anchor for price analysis
- Identifies support/resistance from volume
- Best for: Level-based trading

### 🔸 Ichimoku Patterns
- Japanese charting technique
- Multiple components (Kijun, Tenkan, Kumo)
- Best for: Trend and support/resistance

---

## The Performance Metrics (Backtesting) Feature

### What It Does

Tests how your alert strategy would have performed on historical data.

### How It Works

1. **You specify a date range**
   - Example: "Test on last 30 days of data"

2. **System simulates all alerts for that period**
   - Generates all alerts that would have triggered
   - Records when each alert occurred
   - Tracks what would have happened

3. **System tests profit/loss scenarios**
   - Tests multiple profit targets (1%, 2%, 3%, etc.)
   - Tests multiple stop losses (0.5%, 1%, 2%, etc.)
   - Creates combination scenarios (20-30 different combinations)

4. **System generates performance reports**
   - Shows which approach works best
   - Shows best time periods
   - Shows optimal profit/loss thresholds
   - Provides specific recommendations

### Example Report Output

```
BACKTESTING RESULTS: VN30F1M (Jan 1-31, 2026)

Approach: Strong Candle Detection
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Alerts Generated: 24
Winning Trades: 18 (75%)
Losing Trades: 6 (25%)
Profit Factor: 2.1x
Best Profit Target: 2.0%
Best Stop Loss: 1.0%
Recommended: Use with 2.0% profit target, 1.0% stop loss

Approach: Consistent Momentum
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Alerts Generated: 31
Winning Trades: 20 (65%)
Losing Trades: 11 (35%)
Profit Factor: 1.8x
Best Profit Target: 1.5%
Best Stop Loss: 0.8%
Recommended: Good for consistent income, slightly higher risk
```

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
Monitor VN30 → via Vietstock
Monitor BTC → via Binance
Monitor ETH → via Binance
```

---

## Configuration Examples

### Example 1: Conservative Trader
```
Symbols: VN30 (Vietnam's main index)
Approach: Strong Candle + Consistent Momentum
Profit Target: 2.0% (wait for solid gains)
Stop Loss: 1.5% (tight stops for safety)
Alerts: Email only
Time Frame: Only during Vietnam trading hours (9:15-15:30)
```

### Example 2: Active Day Trader
```
Symbols: VN30F1M (Vietnam futures, 1-minute data)
Approach: Volume Spike + Strong Candle
Profit Target: 0.5% (many small wins)
Stop Loss: 0.3% (quick exit on loss)
Alerts: SMS + Email (real-time)
Time Frame: Full trading day
```

### Example 3: Crypto Trader
```
Symbols: BTC, ETH (Bitcoin, Ethereum)
Approach: Ichimoku + Volume Reversal
Profit Target: 3.0% (larger moves)
Stop Loss: 2.0% (allow room for volatility)
Alerts: Email + Web notifications
Time Frame: 24/7 (crypto markets never sleep)
```

### Example 4: Multi-Strategy Portfolio
```
Symbols: VN30, BTC, ETH, AAPL
Approach 1: Consistent Momentum (VN30)
Approach 2: Ichimoku (BTC/ETH)
Approach 3: Volume Spike (AAPL)
Profit Targets: 1.5-2.5% depending on asset
Stop Losses: 1.0-1.5% depending on volatility
Alerts: Mix of Email and SMS
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

### Phase 3: Paper Trade (1-2 weeks)
1. Run in LIVE mode on a paper trading account (no real money)
2. See how alerts perform in real time
3. Adjust based on real-time observations
4. Build confidence in your strategy

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

## Important Disclaimers & Warnings

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
