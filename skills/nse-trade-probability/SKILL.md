---
name: nse-trade-probability
description: Estimate where an Indian-market trade (NSE stock, futures or options) is likely to go - probability of target vs stop from past price data, scenario trees across market/news/technical outcomes, news and event check, bull-vs-bear debate, and expected value. Use when asked the odds, probability or likely outcome of a trade.
---

# NSE Trade Probability (v2)

Answers "where might this trade go, and is it worth it?" with numbers instead of gut feel:
1. **Past price data** -> measured odds of target vs stop (several independent methods, gap-aware exits)
2. **News and events** -> what could shift those odds, with event days modelled separately
3. **Permutations** -> scenario tree (market × stock catalyst × technical outcome) and a stop × target × holding-period search
4. **Bull vs bear debate** -> strongest case each way, then a judgement (structure from TauricResearch/TradingAgents)
5. **Survival maths** -> losing streaks, drawdowns and safe size if this setup is traded repeatedly
6. **Track record** -> every prediction is logged and later scored, so accuracy is measured, not assumed

Use with the `nse-trading-frameworks` skill for levels, stops and sizing. The user trades NSE swing and F&O through Groww and explains odds best in plain language ("long" = buy expecting a rise).

## Step 1 - Pin down the trade
Need: symbol · side (long/short) · instrument (cash, future, CE/PE strike + expiry) · entry · stop · target · holding window in trading days · capital or quantity/lots.
- If levels are missing, derive them with `nse-trading-frameworks` and label them proposed. "Analyse X" -> propose a setup, then run odds.
- **Sanity-check the symbol and price** against a quick web search before anything else: tickers change (e.g. TATAMOTORS split into TMPV and TMCV in 2025) and an entry far from the live price can't fill. Flag it and ask.
- Ask only for what can't be derived.

## Step 2 - Get price history (never fabricate)
**Aim for 5+ years of daily OHLCV.** One year is the minimum and makes the feature-matched analogs (m2) and the walk-forward grid unreliable - say so when that's all there is.
1. **Groww MCP** `fetch_historical_candle_data` (1d) -> save as `data/<SYMBOL>.csv` (Date,Open,High,Low,Close,Volume).
2. **yfinance** via `--symbol` (adds `.NS`; `^NSEI` Nifty, `^NSEBANK` Bank Nifty). Usually blocked in cloud sandboxes.
3. **User CSVs**: NSE website -> stock -> Historical Data allows ~1 year per download, so ask for **one file per year for 5 years** (and the same for Nifty 50 from NSE -> Indices -> Historical Data). Pass all files to `--csv`; the script merges, de-duplicates, handles DD-Mon-YYYY dates and comma numbers, and warns if a year is missing. Name files `data/<SYMBOL>_<year>.csv` so calibration can find them.
Also get Nifty 50 (or the sector index) history whenever possible -> `--market`.

## Step 3 - Run the engine
If this skill folder contains `scripts/trade_odds.py`, copy that file; otherwise write the script below to `scripts/trade_odds.py` (the two are identical). Do this once per workspace (needs `pandas numpy`; `yfinance` only for `--symbol`). Run with `python3 -I`.

```
python3 -I scripts/trade_odds.py --csv data/BSE_*.csv --market data/NIFTY_*.csv \
  --entry 3230 --stop 3200 --target 3300 --side long --days 10 --qty 50 \
  --event-date 2026-11-05 --past-events 2025-11-11,2026-02-03 \
  --grid --streaks --risk-pct 1 --log journal.csv --name BSE
# options: --strike 3300 --expiry-days 7 --iv 32      --json for machine-readable output
```

| Output | What it is | How to use it |
|---|---|---|
| `m1_historical` | Every past day replayed: target or stop first within N days; gap through stop exits at the open | Real path behaviour |
| `m1_windows_with/without_event` | Same, split by whether a big-move day (results etc.) fell in the window | Shows how much events change the odds |
| `m2_nearest_analogs` | The 50 past days most similar to today on 7 features (distance from 50/200 DMA, 5d/20d return, RSI, volatility regime, volume surge) | Most relevant estimate; needs ~1.5y+ data |
| `m3_bootstrap` / `_zero_drift` | 20,000 paths from real days in 5-day blocks, with and without the sample's trend | Zero-drift stops a past crash/rally from being assumed to repeat |
| `m3_bootstrap_market_regime` | Bootstrap using only days when the market was in today's regime (needs `--market`) | Also gives beta and correlation to Nifty |
| `m3_bootstrap_with_event` | Injects real past event days at the event's position in the window (`--event-date`) | Use whenever results/RBI/SEBI decision falls inside the window |
| `m4_gbm` | Textbook touch probabilities | Sanity check only |
| `blend` | Average of the valid methods; P(target/stop/neither), EV % and Rs, edge vs breakeven, range, `unstable` flag | Headline numbers |
| `grid` | Every stop (0.5-3 × ATR) × target (1-4 R) × hold (5/10/15/20 d) on the first 70% of history, re-checked on the last 30% | Where levels *should* be; `holds_up` = positive out-of-sample with positive neighbours |
| `streaks` | This setup's real payoffs resampled into 10,000 runs of 100 trades at `--risk-pct` | Chance of 5/8-loss streaks, drawdown p50/p90/p99, ending capital, half-Kelly size |
| `options` | P(expire beyond strike), P(touch), empirical frequency | Say which probability it is |

**Reading rules**
- Report each probability with method and n. Use the range, not a point, when `unstable` is true (methods differ by >15 pts).
- If the sample had a strong trend (`m3_note`), lead with zero-drift and say why.
- `stop_in_atr` < 1 -> the stop sits inside normal daily noise; say so plainly with the rupee ATR.
- Edge = P(target) − breakeven win rate. EV after costs ≤ 0 -> no edge as structured, whatever the story.
- Event in window -> lead with `m3_bootstrap_with_event` and the with-event historical split; widen the range; use option IV if available.
- Grid: never recommend a setup whose `holds_up` is false. If none holds up, say there is no reliable edge on this side in this stock's history - that is a valid answer. Grid winners on 1 year of data are weak evidence.
- Streaks: translate into plain terms ("trading this 100 times at 1% risk, half the time you'd be down 22% at some point"). If half-Kelly is 0, the setup should not be traded repeatedly.

## Step 4 - Log and score predictions (accuracy is measured, not assumed)
- Run every analysed trade with `--log journal.csv --name SYMBOL`. The workspace may be wiped between sessions, so **send `journal.csv` to the user after logging** (SendUserFile) and ask them to attach it next time.
- When the user returns with the journal and fresh price files: `python3 -I scripts/trade_odds.py --calibrate journal.csv --data-dir data`. It fills in outcome and P&L for every prediction whose window has passed, and reports Brier score vs a naive baseline plus a calibration table (predicted 20-40% -> actual hit rate).
- Under 30 resolved predictions: report the numbers but say they're not yet meaningful. If calibration shows the model over- or under-predicts by >10 pts in a bucket, say so and shade future blends in that direction.

## Step 5 - News and event scan
WebSearch (send searches together, last 14 days) plus Groww quotes if connected:
- Company: news, results date (SEBI deadline is 45 days after quarter end), board meetings, order wins, block/bulk deals, promoter pledges, corporate actions, F&O ban list, regulatory or enforcement actions.
- Sector and market: peers, regulation, Nifty/Bank Nifty trend, India VIX, FII/DII flows, RBI/Fed dates, crude, USD/INR.
- F&O: OI build-up, PCR, max pain, IV percentile.
Event table: | Event | Date | In window? | Direction | Impact | Source |. Separate priced-in from pending. Feed known dates into `--event-date` (upcoming) and `--past-events` (last 4-8 results dates, so they're treated as event days even if the auto-detector missed them). Cite sources.

## Step 6 - Scenario tree (permutations and combinations)
Enumerate Market (Nifty up / flat / down) × Catalyst (positive / none / negative) = 9 branches, each split target / stop / neither = 27 paths. Build it in code so the arithmetic is exact.
- Market base rates from Nifty's N-day distribution (run the script on Nifty alone); tilt by VIX/macro. Use measured beta to size how much market branches shift the stock's odds.
- Catalyst default "none" 65-80%; widen when an event is in the window, guided by the with-event split.
- Start technical odds from the blend; shift at most ±15 pts per factor, justify each shift, re-normalise each branch.
- Payoffs: target +reward; stop −risk with extra slippage on negative-catalyst branches (gap through stop); neither = branch median drift.
- The probability-weighted total should sit near the blend unless news justifies moving it.
Output the 9-branch table, totals (P target/stop/neither, EV % and Rs), and the worst plausible path.

## Step 7 - Bull vs bear, then judge
Short debate: bull case answering the bear; bear case answering the bull; risk view (aggressive / conservative / neutral on size and structure); judge in 3-4 lines. Measured odds outrank narrative.

## Step 8 - Verdict (plain language)
```
# [SYMBOL] [side] [instrument] - odds report (data as of [date], [years] of history)
Verdict: TAKE / TAKE SMALLER / WAIT FOR [trigger] / SKIP
Odds (N days): target X% · stop Y% · neither Z%  [range a-b%, methods, n]
R:R r:1 · breakeven b% · edge (X−b) pts · EV ±e% (Rs ...)
Expected range: 1σ Rs L-H · 5-95% Rs ..-..
Events in window: ...
Better levels (grid, only if holds_up): stop .. / target .. / days ..
If traded repeatedly at 1% risk: losing-streak and drawdown odds, half-Kelly size
Scenario tree: [9 branches + totals]
Bull vs bear: [debate + judge]
Plan: trigger · stop · target(s) · size (shares/lots, risk Rs and %) · trailing plan
What would change this view: [specific conditions]
Track record so far: [calibration summary if a journal exists]
```
End with this disclaimer, in one or two lines: these odds are statistical estimates from past prices plus judgement on news, not 100% accurate - treat them as a rough guide (the author's working assumption is roughly 55% reliability; this has not been measured yet - see the prediction log). Not financial advice; any trade taken on this is at the user's own risk.

## Guardrails
- Never place, modify or cancel Groww orders unless the user explicitly asks in that message; confirm the full order first.
- No fabricated prices, IVs, lot sizes, OI, dates or news. If something is missing, say what changes without it.
- Options: say what the probability is OF (expire ITM vs touch vs premium doubling). Buyers: time decay, P(profit) < P(touch). Sellers: gap risk and margin.
- Flag over-sizing (risk > 2% of capital, > 1% with leverage) in rupees.
- Lot sizes, expiry days, margin rules change - verify current values.
- Nothing gives 100% certainty; if asked, explain that odds describe how often similar setups worked, and the stop is what protects the times they don't.

## Engine source - write to scripts/trade_odds.py

```python
#!/usr/bin/env python3
"""trade_odds.py v2 - probability engine for Indian-market trades (NSE cash / F&O underlying).

DATA   --csv f1.csv [f2.csv ...]   NSE/Groww/TradingView daily OHLC; several yearly files are merged
       --symbol RELIANCE           yfinance fallback (adds .NS)
       --market nifty.csv [...]    optional Nifty/sector history -> beta and market-regime filter

MODES (combine freely)
  odds     --entry --stop --target --days [--side long|short] [--qty] [--cost-pct]
  events   --event-date YYYY-MM-DD (known results/policy date)  --past-events d1,d2  (known past results dates)
  grid     --grid            search stop(ATR) x target(R) x days with walk-forward check
  streaks  --streaks [--risk-pct 1] [--n-trades 100]   losing streaks / drawdown from this setup's real payoffs
  options  --strike --expiry-days [--iv]
  log      --log journal.csv --name SYMBOL     append this prediction
  calib    --calibrate journal.csv --data-dir data   score past predictions (needs price files covering them)

Exits are gap-aware: an open beyond the stop exits at the open, not the stop. Same-day stop+target -> stop.
"""
import argparse, csv, glob, json, math, os, sys
from datetime import datetime
import numpy as np
import pandas as pd

ATR_STOPS = [0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0]
R_TARGETS = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
DAYS_GRID = [5, 10, 15, 20]


# ---------------------------------------------------------------- data
def read_one(path, dayfirst):
    df = pd.read_csv(path)
    df.columns = [c.strip().title() for c in df.columns]
    dcol = next(c for c in df.columns if c.lower() in ("date", "datetime", "timestamp", "time"))
    df[dcol] = pd.to_datetime(df[dcol].astype(str).str.strip(), dayfirst=dayfirst, format="mixed")
    df = df.rename(columns={dcol: "Date"}).set_index("Date")
    keep = [c for c in ("Open", "High", "Low", "Close", "Volume") if c in df.columns]
    df = df[keep].copy()
    for c in keep:
        df[c] = pd.to_numeric(df[c].astype(str).str.replace(",", "").str.strip(), errors="coerce")
    return df


def load(paths=None, symbol=None, period="10y", dayfirst=True):
    if paths:
        df = pd.concat([read_one(p, dayfirst) for p in paths])
        df = df[~df.index.duplicated(keep="last")].sort_index()
    else:
        import yfinance as yf
        sym = symbol if "." in symbol or symbol.startswith("^") else symbol + ".NS"
        df = yf.download(sym, period=period, interval="1d", auto_adjust=True, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if df.empty:
            sys.exit(f"No data for {sym} (network blocked or bad symbol) - use --csv instead.")
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    gaps = df.index.to_series().diff().dt.days
    if (gaps > 10).any():
        print(f"WARNING: {int((gaps > 10).sum())} gap(s) >10 calendar days in data - a yearly file may be missing.", file=sys.stderr)
    return df


def indicators(df):
    c = df["Close"]; d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    df["RSI"] = 100 - 100 / (1 + up / dn.replace(0, np.nan))
    tr = pd.concat([df.High - df.Low, (df.High - c.shift()).abs(), (df.Low - c.shift()).abs()], axis=1).max(axis=1)
    df["ATR"] = tr.ewm(alpha=1 / 14, adjust=False).mean()
    for n in (20, 50, 200):
        df[f"SMA{n}"] = c.rolling(n).mean()
    df["Ret"] = np.log(c / c.shift())
    df["Vol20"] = df.Ret.rolling(20).std()
    df["Trend"] = np.select([(c > df.SMA50) & (df.SMA50 > df.SMA200), (c < df.SMA50) & (df.SMA50 < df.SMA200)], ["up", "down"], "mixed")
    # features for nearest-neighbour analogs
    df["f_d50"] = c / df.SMA50 - 1
    df["f_d200"] = c / df.SMA200 - 1
    df["f_r5"] = c / c.shift(5) - 1
    df["f_r20"] = c / c.shift(20) - 1
    df["f_rsi"] = df.RSI / 100
    df["f_vol"] = df.Vol20 / df.Ret.rolling(120).std()
    if "Volume" in df:
        df["f_volu"] = np.log(df.Volume / df.Volume.rolling(20).median())
    return df


def mark_events(df, past_events=()):
    """Event day = |return| > 2.5x prior 60d sd AND volume > 2x 20d median, or a user-given past results date."""
    sd = df.Ret.rolling(60, min_periods=20).std().shift()
    big = df.Ret.abs() > 2.5 * sd
    if "Volume" in df:
        big &= df.Volume > 2.0 * df.Volume.rolling(20, min_periods=10).median().shift()
    ev = big.fillna(False)
    for d in past_events:
        d = pd.Timestamp(d)
        nxt = df.index[df.index >= d]
        if len(nxt): ev.loc[nxt[0]] = True
    df["Event"] = ev
    return df


# ---------------------------------------------------------------- core path evaluation
def forward_rel(df, D):
    """rows i -> next D days of O/H/L/C divided by close[i]; only rows with D full days ahead."""
    O, H, L, C = (df[k].values for k in ("Open", "High", "Low", "Close"))
    n = len(C) - D
    if n <= 0: return None
    idx = np.arange(n)[:, None] + np.arange(1, D + 1)
    base = C[:n, None]
    return O[idx] / base, H[idx] / base, L[idx] / base, C[idx] / base


def evaluate(rel, up, dn, D, side):
    """rel=(O,H,L,C) arrays (n, >=D). Returns outcome (+1 tgt, -1 stop, 0 neither) and pnl fraction per path."""
    O, H, L, C = (a[:, :D] for a in rel)
    if side == "long":
        t, s = 1 + up, 1 - dn
        s_hit, t_hit, gap = L <= s, H >= t, O <= s
    else:
        t, s = 1 - up, 1 + dn
        s_hit, t_hit, gap = H >= s, L <= t, O >= s
    big = D + 1
    fs = np.where(s_hit.any(1), s_hit.argmax(1), big)
    ft = np.where(t_hit.any(1), t_hit.argmax(1), big)
    stop_first = (fs <= ft) & (fs < big)
    tgt_first = (ft < fs)
    rows = np.arange(len(O))
    fs_c = np.minimum(fs, D - 1)
    exit_stop = np.where(gap[rows, fs_c], O[rows, fs_c], s)
    sign = 1 if side == "long" else -1
    pnl = np.where(stop_first, sign * (exit_stop - 1),
          np.where(tgt_first, sign * (t - 1), sign * (C[:, D - 1] - 1)))
    out = np.where(stop_first, -1, np.where(tgt_first, 1, 0))
    return out, pnl


def stats(out, pnl, cost):
    if len(out) == 0: return None
    return {"n": int(len(out)), "p_target": round(float((out == 1).mean()), 3), "p_stop": round(float((out == -1).mean()), 3),
            "p_neither": round(float((out == 0).mean()), 3), "ev_pct": round(float(pnl.mean() - cost) * 100, 3),
            "loss_windows_pct": round(float((pnl - cost < 0).mean()) * 100, 1)}


def bootstrap_rel(df, D, sims=20000, block=5, seed=7, drift=0.0, event_day=None, mask=None):
    """Synthetic forward (O,H,L,C)/C0 paths from real days in blocks. event_day: inject one real event day at that index
    (or random if -1). mask: restrict source days (e.g. market-regime matched)."""
    O, H, L, C = (df[k].values for k in ("Open", "High", "Low", "Close"))
    pc = C[:-1]
    g, h, l, r = np.log(O[1:] / pc), np.log(H[1:] / pc), np.log(L[1:] / pc), np.log(C[1:] / pc)
    g, h, l, r = g - drift, h - drift, l - drift, r - drift
    src = np.arange(len(r) - block)
    if mask is not None:
        m = mask[1:][: len(src)]
        if m.sum() >= 50: src = src[m]
    rng = np.random.default_rng(seed)
    nb = -(-D // block)
    starts = rng.choice(src, size=(sims, nb))
    idx = (starts[:, :, None] + np.arange(block)).reshape(sims, -1)[:, :D]
    G, Hh, Ll, R = g[idx], h[idx], l[idx], r[idx]
    if event_day is not None:
        ev_idx = np.where(df.Event.values[1:])[0]
        if len(ev_idx):
            pick = rng.choice(ev_idx, size=sims)
            pos = rng.integers(0, D, size=sims) if event_day < 0 else np.full(sims, min(event_day, D - 1))
            rows = np.arange(sims)
            G[rows, pos], Hh[rows, pos], Ll[rows, pos], R[rows, pos] = g[pick], h[pick], l[pick], r[pick]
    cum = np.cumsum(R, 1); prev = np.hstack([np.zeros((sims, 1)), cum[:, :-1]])
    return np.exp(prev + G), np.exp(prev + Hh), np.exp(prev + Ll), np.exp(cum)


def gbm_touch(S, B, sig, days):
    if sig <= 0: return float("nan")
    z = abs(math.log(B / S)) / (sig * math.sqrt(days))
    return min(1.0, 2 * (1 - 0.5 * (1 + math.erf(z / math.sqrt(2)))))


def nn_analogs(df, k=50):
    feats = [c for c in df.columns if c.startswith("f_")]
    X = df[feats].replace([np.inf, -np.inf], np.nan)
    valid = X.dropna().index
    if len(valid) < k + 20: return None
    Z = (X.loc[valid] - X.loc[valid].mean()) / X.loc[valid].std()
    today = Z.iloc[-1].values
    dist = np.sqrt(((Z.iloc[:-1].values - today) ** 2).sum(1))
    order = np.argsort(dist)[:k]
    return [df.index.get_loc(valid[i]) for i in order]


# ---------------------------------------------------------------- modes
def run_odds(df, a, mkt=None):
    last = df.iloc[-1]; S = float(last.Close); entry = a.entry or S
    sig = float(df.Ret.iloc[-60:].std())
    up = abs(a.target - entry) / entry; dn = abs(entry - a.stop) / entry; rr = up / dn
    cost = a.cost_pct / 100; D = a.days
    o = {"trade": {"side": a.side, "entry": entry, "stop": a.stop, "target": a.target, "days": D,
                   "reward_pct": round(up * 100, 2), "risk_pct": round(dn * 100, 2), "rr": round(rr, 2),
                   "stop_in_atr": round(abs(entry - a.stop) / float(last.ATR), 2), "breakeven_winrate": round(1 / (1 + rr), 3)}}
    if a.qty: o["trade"]["max_loss_rupees_at_stop"] = round(dn * entry * a.qty)
    rel = forward_rel(df, D)
    out, pnl = evaluate(rel, up, dn, D, a.side)
    o["m1_historical"] = stats(out, pnl, cost)
    # event split
    if df.Event.any():
        ev_win = np.array([df.Event.values[i + 1:i + 1 + D].any() for i in range(len(out))])
        o["m1_windows_with_event"] = stats(out[ev_win], pnl[ev_win], cost)
        o["m1_windows_without_event"] = stats(out[~ev_win], pnl[~ev_win], cost)
    # nearest-neighbour analogs
    nn = nn_analogs(df)
    if nn:
        nn = [i for i in nn if i < len(out)]
        o["m2_nearest_analogs"] = stats(out[nn], pnl[nn], cost) if len(nn) >= 30 else {"note": f"only {len(nn)} usable analogs"}
        if len(nn) >= 30: o["m2_nearest_analogs"]["dates"] = [str(df.index[i].date()) for i in nn[:5]] + ["..."]
    else:
        o["m2_nearest_analogs"] = {"note": "not enough history for feature matching (need ~1.5y+)"}
    # bootstrap: as-is, zero-drift, market-regime matched, event-injected
    drift = float(df.Ret.mean())
    b_raw = evaluate(bootstrap_rel(df, D), up, dn, D, a.side)
    b_zero = evaluate(bootstrap_rel(df, D, drift=drift), up, dn, D, a.side)
    o["m3_bootstrap"] = stats(*b_raw, cost)
    o["m3_bootstrap_zero_drift"] = stats(*b_zero, cost)
    o["m3_note"] = f"past-sample drift {drift*100:.3f}%/day ({(math.exp(drift*252)-1)*100:.0f}%/yr) - zero-drift removes it"
    if mkt is not None:
        o["market"] = mkt["summary"]
        b_mkt = evaluate(bootstrap_rel(df, D, mask=mkt["mask"]), up, dn, D, a.side)
        o["m3_bootstrap_market_regime"] = stats(*b_mkt, cost)
    event_in = a.event_date and pd.Timestamp(a.event_date) <= df.index[-1] + pd.tseries.offsets.BDay(D)
    if event_in or a.force_event:
        pos = -1
        if a.event_date:
            pos = max(0, len(pd.bdate_range(df.index[-1] + pd.Timedelta(days=1), a.event_date)) - 1)
        b_ev = evaluate(bootstrap_rel(df, D, event_day=pos), up, dn, D, a.side)
        o["m3_bootstrap_with_event"] = stats(*b_ev, cost)
        o["event_note"] = f"event inside window (day {pos+1 if pos>=0 else 'random'}); {int(df.Event.sum())} past event days sampled"
    o["m4_gbm"] = {"p_touch_target": round(gbm_touch(entry, a.target, sig, D), 3), "p_touch_stop": round(gbm_touch(entry, a.stop, sig, D), 3)}
    # blend
    keys = ["m1_historical", "m3_bootstrap", "m3_bootstrap_zero_drift"]
    if isinstance(o.get("m2_nearest_analogs"), dict) and "n" in o["m2_nearest_analogs"]: keys.append("m2_nearest_analogs")
    if "m3_bootstrap_market_regime" in o: keys.append("m3_bootstrap_market_regime")
    if "m3_bootstrap_with_event" in o:
        we = o.get("m1_windows_with_event")
        keys = ["m3_bootstrap_with_event"] + (["m1_windows_with_event"] if we and we["n"] >= 30 else [])
    E = [o[k] for k in keys if o.get(k)]
    o["blend"] = {"methods": keys, "p_target": round(np.mean([e["p_target"] for e in E]), 3), "p_stop": round(np.mean([e["p_stop"] for e in E]), 3),
                  "ev_pct": round(np.mean([e["ev_pct"] for e in E]), 3),
                  "p_target_range": [min(e["p_target"] for e in E), max(e["p_target"] for e in E)],
                  "edge_pts": round((np.mean([e["p_target"] for e in E]) - 1 / (1 + rr)) * 100, 1)}
    o["blend"]["p_neither"] = round(1 - o["blend"]["p_target"] - o["blend"]["p_stop"], 3)
    if a.qty: o["blend"]["ev_rupees"] = round(o["blend"]["ev_pct"] / 100 * entry * a.qty)
    o["blend"]["unstable"] = (o["blend"]["p_target_range"][1] - o["blend"]["p_target_range"][0]) > 0.15
    final = bootstrap_rel(df, D, drift=drift)[3][:, -1]
    o["price_range_at_horizon_zero_drift"] = dict(zip(["p5", "p25", "p50", "p75", "p95"], [round(S * x, 2) for x in np.percentile(final, [5, 25, 50, 75, 95])]))
    return o, pnl


def run_grid(df, a):
    last = df.iloc[-1]; atrp = float(last.ATR / last.Close); cost = a.cost_pct / 100
    Dmax = max(DAYS_GRID); rel = forward_rel(df, Dmax)
    if rel is None or len(rel[0]) < 120: return {"note": "need ~1y+ of data for grid"}
    n = len(rel[0]); split = int(n * 0.7)
    res = {}
    for D in DAYS_GRID:
        for ks in ATR_STOPS:
            for R in R_TARGETS:
                dn = ks * atrp; up = R * dn
                if dn >= 0.5: continue
                out, pnl = evaluate(rel, up, dn, D, a.side)
                res[(D, ks, R)] = (pnl[:split].mean() - cost, pnl[split:].mean() - cost, (out[:split] == 1).mean(), (out[split:] == 1).mean())
    def neigh(D, ks, R):
        i, j = ATR_STOPS.index(ks), R_TARGETS.index(R); vals = []
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if 0 <= i + di < len(ATR_STOPS) and 0 <= j + dj < len(R_TARGETS):
                    k = (D, ATR_STOPS[i + di], R_TARGETS[j + dj])
                    if k in res: vals.append(res[k][0])
        return float(np.mean(vals))
    ranked, seen = [], set()
    for kv in sorted(res.items(), key=lambda kv: (-kv[1][0], kv[0][0])):
        sig = (kv[0][1], kv[0][2], round(kv[1][0], 5), round(kv[1][1], 5))
        if sig in seen: continue
        seen.add(sig); ranked.append(kv)
        if len(ranked) == 8: break
    E = a.entry or float(last.Close)
    rows = []
    for (D, ks, R), (tr, te, wtr, wte) in ranked:
        dn = ks * atrp
        rows.append({"days": D, "stop_atr": ks, "target_R": R,
                     "stop_price": round(E * (1 - dn) if a.side == "long" else E * (1 + dn), 2),
                     "target_price": round(E * (1 + R * dn) if a.side == "long" else E * (1 - R * dn), 2),
                     "train_ev_pct": round(tr * 100, 2), "test_ev_pct": round(te * 100, 2),
                     "train_win": round(wtr, 3), "test_win": round(wte, 3), "neighbour_ev_pct": round(neigh(D, ks, R) * 100, 2),
                     "holds_up": bool(te > 0 and neigh(D, ks, R) > 0)})
    any_ok = any(r["holds_up"] for r in rows)
    return {"atr_pct_now": round(atrp * 100, 2), "train_period": f"{df.index[0].date()}..{df.index[split].date()}",
            "test_period": f"{df.index[split].date()}..{df.index[n-1].date()}", "top_by_train_ev": rows,
            "verdict": "at least one setup positive out-of-sample with stable neighbours" if any_ok else
                       "NO setup holds up out-of-sample - no reliable edge in this stock's recent history for this side"}


def run_streaks(pnl, dn, a):
    """Resample this setup's real per-trade payoffs (in R units) into many 100-trade sequences."""
    Rr = pnl / dn  # payoff in R multiples (stop ~ -1R, gaps worse)
    rng = np.random.default_rng(11); sims, N = 10000, a.n_trades
    seq = rng.choice(Rr, size=(sims, N))
    eq = np.cumprod(1 + seq * a.risk_pct / 100, axis=1)
    peak = np.maximum.accumulate(eq, axis=1); dd = 1 - eq / peak; maxdd = dd.max(1)
    losses = seq < 0
    def longest(row):
        best = cur = 0
        for x in row:
            cur = cur + 1 if x else 0; best = max(best, cur)
        return best
    ls = np.array([longest(r) for r in losses[:2000]])
    return {"risk_per_trade_pct": a.risk_pct, "trades": N, "avg_R_per_trade": round(float(Rr.mean()), 3),
            "worst_single_trade_R": round(float(Rr.min()), 2),
            "p_losing_streak_ge_5": round(float((ls >= 5).mean()), 3), "p_losing_streak_ge_8": round(float((ls >= 8).mean()), 3),
            "median_longest_losing_streak": int(np.median(ls)),
            "max_drawdown_pct": {"median": round(float(np.median(maxdd)) * 100, 1), "p90": round(float(np.percentile(maxdd, 90)) * 100, 1),
                                 "p99": round(float(np.percentile(maxdd, 99)) * 100, 1)},
            "p_drawdown_ge_20pct": round(float((maxdd >= 0.2).mean()), 3), "p_drawdown_ge_30pct": round(float((maxdd >= 0.3).mean()), 3),
            "ending_capital_x": {"p10": round(float(np.percentile(eq[:, -1], 10)), 3), "median": round(float(np.median(eq[:, -1])), 3),
                                 "p90": round(float(np.percentile(eq[:, -1], 90)), 3)},
            "half_kelly_risk_pct": kelly(Rr)}


def kelly(Rr):
    w = Rr[Rr > 0]; l = Rr[Rr < 0]
    if len(w) == 0 or len(l) == 0: return 0.0
    p = len(w) / len(Rr); b = w.mean() / -l.mean()
    k = p - (1 - p) / b
    return round(max(0.0, k / 2) * 100, 2)


def market_regime(paths, dayfirst, df):
    m = indicators(load(paths, dayfirst=dayfirst))
    m = m.reindex(df.index).ffill()
    j = pd.concat([df.Ret, m.Ret], axis=1, keys=["s", "m"]).dropna()
    beta = float(np.cov(j.s, j.m)[0, 1] / j.m.var()) if len(j) > 60 else float("nan")
    corr = float(j.s.corr(j.m)) if len(j) > 60 else float("nan")
    regime_now = m.Trend.iloc[-1]
    mask = (m.Trend == regime_now).values
    return {"summary": {"market_trend_now": regime_now, "beta": round(beta, 2), "corr": round(corr, 2),
                        "market_20d_ret_pct": round(float(m.Close.iloc[-1] / m.Close.iloc[-21] - 1) * 100, 2),
                        "days_in_same_regime": int(mask.sum())}, "mask": mask}


def run_options(df, a):
    S = float(df.Close.iloc[-1]); sig = (a.iv / 100 / math.sqrt(252)) if a.iv else float(df.Ret.iloc[-60:].std())
    T = a.expiry_days; z = math.log(a.strike / S) / (sig * math.sqrt(T))
    p_above = 1 - 0.5 * (1 + math.erf(z / math.sqrt(2)))
    fwd = np.log(df.Close.shift(-T) / df.Close).dropna().values; need = math.log(a.strike / S)
    return {"strike": a.strike, "trading_days": T, "vol_used_annual_pct": round(sig * math.sqrt(252) * 100, 1),
            "vol_source": "IV given" if a.iv else "realised 60d", "p_close_above_at_expiry": round(p_above, 3),
            "p_close_below_at_expiry": round(1 - p_above, 3), "p_touch_before_expiry": round(gbm_touch(S, a.strike, sig, T), 3),
            "empirical_p_move_that_far": round(float((fwd >= need).mean() if need > 0 else (fwd <= need).mean()), 3)}


# ---------------------------------------------------------------- journal
FIELDS = ["logged_at", "as_of", "symbol", "side", "entry", "stop", "target", "days", "p_target", "p_stop", "p_neither", "ev_pct", "outcome", "pnl_pct"]


def log_prediction(path, name, as_of, a, blend):
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new: w.writeheader()
        w.writerow({"logged_at": datetime.now().strftime("%Y-%m-%d %H:%M"), "as_of": as_of, "symbol": name.upper(), "side": a.side,
                    "entry": a.entry, "stop": a.stop, "target": a.target, "days": a.days, "p_target": blend["p_target"],
                    "p_stop": blend["p_stop"], "p_neither": blend["p_neither"], "ev_pct": blend["ev_pct"], "outcome": "", "pnl_pct": ""})


def calibrate(path, data_dir, dayfirst):
    rows = list(csv.DictReader(open(path)))
    resolved, cache = [], {}
    for r in rows:
        if not r["outcome"]:
            sym = r["symbol"]
            if sym not in cache:
                files = sorted(glob.glob(os.path.join(data_dir, f"{sym}*.csv")))
                cache[sym] = load(files, dayfirst=dayfirst) if files else None
            df = cache[sym]
            if df is None: continue
            after = df[df.index > pd.Timestamp(r["as_of"])]
            D = int(r["days"])
            if len(after) < D: continue
            e, s, t = float(r["entry"]), float(r["stop"]), float(r["target"])
            rel = tuple((after[k].values[:D] / e)[None, :] for k in ("Open", "High", "Low", "Close"))
            up, dn = abs(t - e) / e, abs(e - s) / e
            out, pnl = evaluate(rel, up, dn, D, r["side"])
            r["outcome"] = {1: "target", -1: "stop", 0: "neither"}[int(out[0])]; r["pnl_pct"] = round(float(pnl[0]) * 100, 2)
        if r["outcome"]: resolved.append(r)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    if not resolved: return {"logged": len(rows), "resolved": 0, "note": "no predictions have completed their window yet"}
    p = np.array([float(r["p_target"]) for r in resolved]); y = np.array([r["outcome"] == "target" for r in resolved], float)
    bins = [(0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.01)]
    table = []
    for lo, hi in bins:
        m = (p >= lo) & (p < hi)
        if m.any(): table.append({"predicted": f"{int(lo*100)}-{int(min(hi,1)*100)}%", "n": int(m.sum()), "avg_predicted": round(float(p[m].mean()), 3),
                                  "actual_hit_rate": round(float(y[m].mean()), 3)})
    brier = float(((p - y) ** 2).mean()); base = float(((y.mean() - y) ** 2).mean())
    return {"logged": len(rows), "resolved": len(resolved), "brier": round(brier, 4), "brier_if_always_avg": round(base, 4),
            "skill_vs_naive": "better than naive" if brier < base else "NOT better than naive - treat odds with caution",
            "avg_predicted_ev_pct": round(float(np.mean([float(r['ev_pct']) for r in resolved])), 3),
            "avg_actual_pnl_pct": round(float(np.mean([float(r['pnl_pct']) for r in resolved])), 3),
            "calibration": table, "note": "need 30+ resolved predictions before trusting this"}


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", nargs="+"); ap.add_argument("--symbol"); ap.add_argument("--period", default="10y")
    ap.add_argument("--dayfirst", action="store_true", default=True); ap.add_argument("--market", nargs="+")
    ap.add_argument("--entry", type=float); ap.add_argument("--stop", type=float); ap.add_argument("--target", type=float)
    ap.add_argument("--side", default="long", choices=["long", "short"]); ap.add_argument("--days", type=int, default=10)
    ap.add_argument("--qty", type=float, default=0); ap.add_argument("--cost-pct", type=float, default=0.1)
    ap.add_argument("--event-date"); ap.add_argument("--past-events", default=""); ap.add_argument("--force-event", action="store_true")
    ap.add_argument("--grid", action="store_true")
    ap.add_argument("--streaks", action="store_true"); ap.add_argument("--risk-pct", type=float, default=1.0); ap.add_argument("--n-trades", type=int, default=100)
    ap.add_argument("--strike", type=float); ap.add_argument("--expiry-days", type=int); ap.add_argument("--iv", type=float)
    ap.add_argument("--log"); ap.add_argument("--name"); ap.add_argument("--calibrate"); ap.add_argument("--data-dir", default="data")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.calibrate:
        print(json.dumps(calibrate(a.calibrate, a.data_dir, a.dayfirst), indent=2)); return
    if not (a.csv or a.symbol): sys.exit("give --csv or --symbol")

    df = load(a.csv, a.symbol, a.period, a.dayfirst)
    df = mark_events(indicators(df), [d for d in a.past_events.split(",") if d])
    last = df.iloc[-1]; S = float(last.Close); sig = float(df.Ret.iloc[-60:].std())
    o = {"as_of": str(df.index[-1].date()), "history": f"{df.index[0].date()} -> {df.index[-1].date()} ({len(df)} bars, {len(df)/248:.1f}y)",
         "last_close": round(S, 2), "trend": str(last.Trend), "rsi14": round(float(last.RSI), 1), "atr14": round(float(last.ATR), 2),
         "atr_pct": round(float(last.ATR) / S * 100, 2), "vol_annual_pct_60d": round(sig * math.sqrt(252) * 100, 1),
         "sma20": round(float(last.SMA20), 2), "sma50": round(float(last.SMA50), 2),
         "sma200": None if pd.isna(last.SMA200) else round(float(last.SMA200), 2), "past_event_days": int(df.Event.sum()),
         "expected_move_1sd": {f"{d}d": [round(S * math.exp(-sig * math.sqrt(d)), 2), round(S * math.exp(sig * math.sqrt(d)), 2)] for d in (1, 5, 10, 20)}}
    mkt = market_regime(a.market, a.dayfirst, df) if a.market else None
    pnl = None
    if a.stop and a.target:
        odds, pnl = run_odds(df, a, mkt); o.update(odds)
        if a.log:
            log_prediction(a.log, a.name or (a.symbol or os.path.basename(a.csv[0]).split(".")[0]), o["as_of"], a, o["blend"])
            o["logged_to"] = a.log
    elif mkt: o["market"] = mkt["summary"]
    if a.grid: o["grid"] = run_grid(df, a)
    if a.streaks:
        if pnl is None: sys.exit("--streaks needs --entry/--stop/--target")
        o["streaks"] = run_streaks(pnl, abs((a.entry or S) - a.stop) / (a.entry or S), a)
    if a.strike and a.expiry_days: o["options"] = run_options(df, a)

    if a.json:
        print(json.dumps(o, indent=2, default=str)); return
    for k, v in o.items():
        if k == "grid" and isinstance(v, dict) and "top_by_train_ev" in v:
            print(f"grid: ATR now {v['atr_pct_now']}% | train {v['train_period']} | test {v['test_period']}")
            for r in v["top_by_train_ev"]: print("   ", json.dumps(r))
            print("   verdict:", v["verdict"])
        else:
            print(f"{k}: {json.dumps(v, default=str) if isinstance(v, (dict, list)) else v}")


if __name__ == "__main__":
    main()
```
