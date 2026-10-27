---
name: nse-trading-frameworks
description: Trading frameworks for Indian NSE/BSE stocks and F&O - technical analysis, multi-timeframe, RSI divergence, Fibonacci, position sizing, stop-loss, trailing stops and risk-reward. Use when analysing a stock, setup, entry/exit or position size.
---

# NSE Trading Frameworks

A rulebook for reading Indian equity charts and managing risk, adapted from the open-source nse-trading-skills pack (Bhala-Srinivash, MIT). The user trades NSE swing and F&O through Groww. Read the chart systematically - never cherry-pick indicators that confirm a bias.

For probability, scenario and news analysis of a specific trade, also use the `nse-trade-probability` skill; this skill supplies the levels, stops and sizing it feeds on.

## Data (all optional - never invent prices)

In priority order:
1. **Groww MCP** if connected: `search_stock_and_others_symbol` (resolve symbol first) -> `get_quotes_and_depth` / `get_ltp` -> `get_historical_technical_indicators` (RSI, MACD, SMA/EMA, Bollinger, ADX, ATR) -> `fetch_historical_candle_data` (1d for 200+ days; 1w for weekly; 1h ~30 days) -> `get_equity_portfolio_holdings` for existing positions. Groww MCP can also place orders: never place, modify or cancel an order unless the user explicitly asks in that message, and confirm the full order first.
2. **yfinance** (`pip install yfinance`): `yf.download("RELIANCE.NS", period="2y", interval="1d")`; `.NS` = NSE, `.BO` = BSE, `^NSEI` = Nifty 50, `^NSEBANK` = Bank Nifty. Often blocked in cloud sandboxes - if it fails, say so and move on.
3. **User-provided**: prices they type or a CSV export (Groww / NSE website / TradingView).
If no data is available, ask for current price, recent swing high/low and ATR rather than guessing. State the as-of date of every price used.

## Master workflow (skip steps the question doesn't need)

1. CONTEXT - what they hold, capital, cash vs futures vs options, horizon
2. DATA - quotes, candles, indicators
3. STRUCTURE - multi-timeframe (weekly -> daily -> hourly)
4. TECHNICALS - trend, S/R, volume, indicators, RSI divergence, Fibonacci
5. DECISION - buy / sell / hold / wait, with triggers
6. SIZING - shares or lots at fixed risk
7. STOPS - initial stop, then trailing plan
8. TARGETS - R:R check, Fib extensions
9. PLAN - concrete prices and triggers

| Question | Sections |
|---|---|
| "Analyse X" / "Should I buy X" | All, as needed |
| Position size | Sizing, Stops, R:R |
| Where to put stop | Stops, Technicals (S/R) |
| Divergence / Fib | Divergence or Fib + Technicals |
| Trail my stop | Trailing |
| Is this trade worth it | R:R, Sizing |
| Weekly vs daily | Multi-timeframe |

---

## 1. Technical analysis

**Trend.** Weekly HH/HL = uptrend, LH/LL = downtrend. MA alignment: Price > SMA20 > SMA50 > SMA200 = strong up; reverse = strong down; mixed = choppy. Golden cross (SMA50 > SMA200) bullish, death cross bearish.

**Support/resistance.** Swing highs/lows with 2+ touches; round numbers (Rs.1,000, 1,500, 2,000); volume clusters; dynamic S/R at SMA20/50/200; unfilled gaps.

**Volume** (vs 20-day average; >1.5x = significant):
| Price | Volume | Read |
|---|---|---|
| Up | Up | Healthy trend |
| Up | Down | Weak rally, suspect |
| Down | Up | Selling accelerating |
| Down | Down | Selling exhaustion, bounce possible |
| Spike at support | - | Capitulation / reversal |
| Spike at resistance | - | Breakout attempt or distribution |

**Indicator dashboard** - count bullish vs bearish:
| Indicator | Bullish | Bearish | Neutral |
|---|---|---|---|
| RSI(14) | >50, rising from <30 | <50, falling from >70 | 40-60 flat |
| MACD | Line > signal, histogram growing | Line < signal, shrinking | Near zero |
| Bollinger | Bounce off lower band | Rejected at upper | Walking band |
| ADX | >25, +DI > -DI | >25, -DI > +DI | <20 no trend |
| Stochastic | %K crosses up below 20 | %K crosses down above 80 | Mid-range |

**Scenarios.** Always give 2-3 (bullish / bearish / sideways) with trigger, target, invalidation and rough probability summing to ~100%. If `nse-trade-probability` has been run, use its measured probabilities instead of eyeballed ones.

## 2. Multi-timeframe (3-screen)

| Screen | TF | Purpose |
|---|---|---|
| 1 | Weekly | Direction: trend, 20W/50W SMA, weekly RSI vs 50, major S/R |
| 2 | Daily | Setup: pullback to support in uptrend / rally to resistance in downtrend; patterns; indicators; volume |
| 3 | 4H/1H | Timing: reversal candle, RSI bounce, MACD cross; tight stop |

Weekly decides direction; trade against it only with very strong reasons. If timeframes disagree, the answer is "no trade".

**Confluence score** (+1 each): weekly trend agrees; daily valid setup; daily RSI supports; daily MACD supports; clear S/R for stop/target; volume confirms.
5-6 strong -> full size; 4 good -> full size; 3 marginal -> half size; 2 weak -> skip/paper; 0-1 no trade.

## 3. RSI divergence

| Type | Price | RSI | Meaning |
|---|---|---|---|
| Regular bullish | Lower low | Higher low | Selling fading - possible bottom |
| Regular bearish | Higher high | Lower high | Buying fading - possible top |
| Hidden bullish | Higher low | Lower low | Uptrend continues |
| Hidden bearish | Lower high | Higher high | Downtrend continues |

Mark the last 2-3 swing points and RSI at the same candles (90-120 daily bars). Strength: 2-point standard < 3-point strong < plus RSI <30/>70 < plus falling volume. Signals inside RSI 40-60 are weak. Weekly > daily > hourly.
**Never enter on divergence alone** - wait for trendline break, RSI back above 30 (or below 70), or an engulfing candle; enter on the confirmation close. Stop beyond the divergence swing + 1% buffer. Targets: prior swing, then Fib 127.2% / 161.8%. Divergences can repeat in strong trends.

## 4. Fibonacci

Swing must be completed and at least ~5%. Uptrend: anchor low -> high. Downtrend: high -> low.
```
diff = high - low
retracements: high - diff*[0.236, 0.382, 0.5, 0.618, 0.786]
extensions from pullback low C: C + diff*[1.0, 1.272, 1.618, 2.0, 2.618]
```
23.6% shallow (strong trend) · 38.2% normal entry · 50% deep, caution · 61.8% last stand · 78.6% trend likely failed - if it breaks, exit.
Targets: 127.2% conservative, 161.8% standard, 200% strong trend.
Treat levels as zones (±1-2%). Confluence ranks: Fib alone moderate; + S/R or MA or trendline strong; Fib + S/R + MA or multi-timeframe Fibs very strong. Wait for a reversal candle at the level.

## 5. Position sizing

**Fixed fractional (default):**
```
Risk Rs = Capital × Risk%
Shares  = Risk Rs ÷ |Entry − Stop|
```
Risk%: 1-2% normal · 0.5% new/uncertain setup · up to 3% rare high conviction · with leverage divide by leverage (2% ÷ 3.74x ≈ 0.5%).

**ATR-based:** stop distance = ATR(14) × 1.5 (ADX<20) / 2.0 normal / 2.5 (ADX>30); shares = Risk Rs ÷ stop distance.

**Kelly** (only with 30+ trade history): Kelly% = W − (1−W)/R; use half-Kelly.

**F&O:** size in lots. Risk per lot = |Entry − Stop| × lot size (premium points × lot size for options). Lots = floor(Risk Rs ÷ risk per lot). If even 1 lot exceeds the risk budget, say so - suggest a smaller lot instrument, a spread, or cash. Lot sizes change - look up the current lot size, don't assume. For bought options, max loss is the premium paid; for sold options or futures, risk is open-ended without a stop - flag margin and gap risk.

**Hard portfolio limits:** single stock ≤20% · single sector ≤35% · total open risk ≤6% · max 3 positions in one sector. Reduce size to fit.

Output: Position (shares/lots) · Capital or margin required · Risk Rs (x% of capital) · Stop (x% from entry) · Allocation %.

## 6. Stop-loss

| Method | Use | Rule |
|---|---|---|
| Structure (preferred) | Swing trades | Below last swing low (long) / above swing high (short) − buffer |
| ATR | Volatile, no structure | Entry ∓ ATR × 1.5 / 2.0 / 2.5 |
| S/R | Ranges | Support × (1 − buffer); level needs 2+ touches |
| MA | Trend-following | Below SMA20 (aggressive) / SMA50 / SMA200 |

Buffer: 0.5% large-cap, 1% mid/small-cap, 1.5-2% if avg volume < 50K/day or known wick-hunting. Round to Rs.5/10. Trigger on closing price unless intraday.
**Hard rules:** max loss 2% of capital per trade (1% with leverage) · never widen a stop · if hit, exit at next open · decide before entry · use real SL orders or alerts, not mental stops.
**Validate:** ≥1× ATR from entry; size keeps risk within limits; R:R still acceptable; stop sits beyond a real level, not just a round number.

## 7. Trailing stops

**Hybrid (default):** 0-1R keep initial stop · at 1R move to breakeven · at 2R trail highest close − 1.5×ATR · 3R+ trail below most recent higher low.
Other methods: ATR trail (1.5/2.0/3.0×); structure trail; MA trail (SMA20 / EMA50 / SMA200, on daily close); Chandelier = highest high since entry − 3×ATR.
| Behaviour | Trail |
|---|---|
| Clean stair-step uptrend | Structure |
| Trending but volatile | ATR 2.0× or Chandelier |
| Low-vol grinder | EMA50 |
| Explosive runner | Chandelier 3× |
| Long-term hold | SMA200 |
Ratchet only (never down); update at daily close; exit next open when hit; don't over-tighten relative to ATR.

## 8. Risk-reward

```
R:R = |Target − Entry| ÷ |Entry − Stop|
Breakeven win rate = 1 ÷ (1 + R:R)
EV = Win% × Avg win − Loss% × Avg loss − costs
Multi-target R:R = Σ (fraction × R at that target)
```
| Win rate | Breakeven R:R | Recommended min |
|---|---|---|
| 30% | 2.33 | 3:1 |
| 40% | 1.5 | 2:1 |
| 50% | 1.0 | 1.5:1 |
| 60% | 0.67 | 1:1 |
Unknown win rate -> assume 40-50%, need ≥2:1. <1:1 skip · 1-1.5 only if win rate >55% and high conviction · 2-3 good · 3+ excellent.
Checklist: specific target? stop at a meaningful level? R:R ≥1.5 (ideally 2)? risk ≤1-2%? can I live with the stop being hit?

## Output format (full analysis)

```
# [STOCK] - [date, data as of]
## Quick take      1-2 lines: bias + key level
## Position        holdings, avg, P&L (if held)
## Technical setup trend, levels, indicators, confluence score
## Scenarios       bull / bear / sideways with trigger, target, invalidation, probability
## Action plan     | Action | Trigger | Price | Size | Stop | Target | R:R |
## Risk            max loss Rs and %, stop, trailing plan
```

## Indian market notes
- NSE hours 9:15-15:30 IST; pre-open 9:00-9:15. T+1 settlement.
- Circuit limits 2/5/10/20% by stock; F&O stocks have no fixed circuit but have dynamic price bands.
- Delivery costs ≈ 0.1% round trip (STT, brokerage, GST, stamp); F&O costs differ - include them in EV.
- Expiry days, lot sizes and margin rules change with SEBI/NSE circulars - verify current values before using them.
- Use the BSE symbol if not listed on NSE.

These are analysis frameworks, not financial advice, and not 100% accurate. Any trade taken on them is at the user's own risk.
