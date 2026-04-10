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
BACKTESTING RESULTS: VN30F1M (April 1-8, 2026)

Approach: Strong Candle Detection
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Profit Target: 2.0 points (fixed)

Stop Loss Analysis:
- 2.5 points: 16 profitable, 8 stopped out → Win Rate: 67%
- 3.0 points: 18 profitable, 6 stopped out → Win Rate: 75%
- 3.5 points: 19 profitable, 5 stopped out → Win Rate: 79%
- 5.0 points: 21 profitable, 3 stopped out → Win Rate: 88%
- 9.0 points: 23 profitable, 1 stopped out → Win Rate: 96%

Best Performance: Stop Loss 3.0-3.5 points (optimal risk/reward)

Approach: Consistent Momentum
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Profit Target: 2.0 points (fixed)

Stop Loss Analysis:
- 2.5 points: 12 profitable, 10 stopped out → Win Rate: 55%
- 3.0 points: 14 profitable, 8 stopped out → Win Rate: 64%
- 3.5 points: 15 profitable, 7 stopped out → Win Rate: 68%
- 5.0 points: 18 profitable, 4 stopped out → Win Rate: 82%
- 9.0 points: 20 profitable, 2 stopped out → Win Rate: 91%

Best Performance: Stop Loss 5.0 points (more conservative approach)
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
Profit Target: 2.0 points (automatic, fixed)
Stop Loss: 3.0-3.5 points (testing multiple levels)
Alerts: Email only
Time Frame: Only during Vietnam trading hours (9:15-15:30)
Backtesting: Aim for 75%+ win rate
```

### Example 2: Active Day Trader
```
Symbols: VN30F1M (Vietnam futures, 1-minute data)
Approach: Volume Spike + Strong Candle
Profit Target: 2.0 points (automatic, fixed)
Stop Loss: 2.5-4.0 points (tighter stops for quick scalps)
Alerts: SMS + Email (real-time)
Time Frame: Full trading day
Backtesting: Aim for 60%+ win rate
```

### Example 3: Crypto Trader
```
Symbols: BTC, ETH (Bitcoin, Ethereum)
Approach: Ichimoku + Volume Reversal
Profit Target: 2.0 points (automatic, fixed)
Stop Loss: 4.0-6.0 points (volatile asset, wider stops)
Alerts: Email + Web notifications
Time Frame: 24/7
Backtesting: Test multiple stop-loss levels
```

### Example 4: Multi-Strategy Portfolio
```
Symbols: VN30, BTC, ETH
Approach: Multiple (rotate by asset)
Profit Target: 2.0 points (consistent across all)
Stop Loss: 3.0-5.0 points (tests 9 different levels)
Alerts: Mix of Email and SMS
Backtesting: Compare performance across all 9 scenarios
```

---

## Getting Started: Step-by-Step

### Technical Reference: Setup (15 minutes)
1. Choose which symbols to monitor
2. Select your alert approaches
3. Set profit targets
4. Set stop losses
5. Configure notifications

### Implementation Guides: Backtest Your Strategy (30 minutes)
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
