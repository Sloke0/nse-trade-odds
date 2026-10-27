# NSE Trade Odds

**Probability-based trade analysis for the Indian stock market (NSE / BSE, cash and F&O), built as Claude skills plus a standalone Python engine.**

> ⚠️ **Read [DISCLAIMER.md](DISCLAIMER.md) before using this.** The results are **not 100% accurate**. Treat them as a rough guide only; the author's working assumption is roughly **55% reliability**, which has **not yet been measured**. This is **not financial advice**, and any trade you take using it is **entirely at your own risk**.

You give it a trade idea (stock, entry, stop-loss, target, number of days). It answers in plain language:

- **What are the odds?** It measures how often the target was hit before the stop, using several independent methods on real past prices.
- **Is it worth it?** It compares those odds with the break-even win rate and works out the expected profit or loss after costs.
- **What could change it?** It scans news and events (results dates, regulator actions, market mood) and builds a **scenario tree**: every combination of market direction × company news × chart outcome.
- **Where should the levels be?** It tests 168 stop × target × holding-period combinations and only recommends ones that still work on recent data the search never saw.
- **Can I survive it?** It simulates 100-trade runs to show losing streaks, worst drawdowns and a safe position size.
- **Is it actually accurate?** Every prediction is logged, and the log is scored against real outcomes later.

---

## What's in the repo

```
nse-trade-odds/
├── README.md
├── DISCLAIMER.md                      ← read this first
├── LICENSE                            MIT
├── THIRD_PARTY_NOTICES.md             credits and licences of the work this builds on
├── THIRD_PARTY_nse-trading-skills_LICENSE.txt
├── requirements.txt
├── skills/
│   ├── nse-trading-frameworks/SKILL.md     chart-reading and risk rulebook
│   └── nse-trade-probability/
│       ├── SKILL.md                        odds + news + scenario tree + debate workflow
│       └── scripts/trade_odds.py           the engine (same file as engine/)
├── engine/trade_odds.py               standalone probability engine (command line)
├── examples/SAMPLE_synthetic.csv      made-up price data for trying it out
└── tests/test_engine.py               smoke tests
```

## The two skills

| Skill | What it does |
|---|---|
| **nse-trading-frameworks** | Technical analysis, weekly/daily/hourly view, RSI divergence, Fibonacci, position sizing (shares and F&O lots), stop-loss placement, trailing stops, risk-reward. Adapted from [nse-trading-skills](https://github.com/Bhala-Srinivash/nse-trading-skills) (MIT). |
| **nse-trade-probability** | The full odds workflow: price history → probability engine → news and event scan → scenario tree → bull-vs-bear debate (structure inspired by [TradingAgents](https://github.com/TauricResearch/TradingAgents)) → plain-language verdict: Take / Take smaller / Wait / Skip. |

### Installing the skills

**Claude (claude.ai / desktop):** zip each folder under `skills/` and upload it under Settings → Capabilities → Skills, or ask Claude to add it.

**Claude Code:** copy the folders into your project's `.claude/skills/` directory:
```bash
mkdir -p .claude/skills
cp -r skills/* .claude/skills/
```

Then just ask, for example:
```
odds on BHARTIARTL long, entry 1917, stop 1900, target 2000, 30 days
```
and attach the price history (see below).

## Getting price data

The engine needs **daily OHLC history, ideally 5+ years**. With only 1 year, some methods switch themselves off.

1. **NSE website (free):** stock page → *Historical Data* → download one file per year (NSE allows about 1 year per download). Pass all the files to the engine; it merges them.
2. **Groww MCP connector** (if connected): the skill pulls candles automatically.
3. **yfinance** (`--symbol RELIANCE`): works on most home machines but is often blocked in cloud sandboxes.

Also download **Nifty 50** history (NSE → Indices → Historical Data) so the engine can measure how much the stock moves with the market.

This repo does **not** include real exchange data. `examples/SAMPLE_synthetic.csv` is randomly generated, for testing only.

## Using the engine directly

```bash
pip install -r requirements.txt

# basic odds
python3 engine/trade_odds.py --csv examples/SAMPLE_synthetic.csv \
  --entry 820 --stop 790 --target 880 --days 10

# everything: several yearly files, Nifty, a results date in the window,
# level search, streak simulation, prediction log
python3 engine/trade_odds.py --csv data/BHARTIARTL_*.csv --market data/NIFTY_*.csv \
  --entry 1917 --stop 1855 --target 2000 --days 30 \
  --event-date 2026-11-03 --past-events 2024-10-28,2025-11-03 \
  --grid --streaks --risk-pct 1 --log journal.csv --name BHARTIARTL

# options: chance of finishing above or below a strike, and of touching it
python3 engine/trade_odds.py --csv data/BSE_*.csv --strike 3300 --expiry-days 7 --iv 32

# later: score past predictions against what actually happened
python3 engine/trade_odds.py --calibrate journal.csv --data-dir data
```

Add `--json` for machine-readable output. Run `python3 engine/trade_odds.py -h` for every option.

### The methods (why there are several)

| Method | What it does |
|---|---|
| **Historical replay** | Starts a trade on every past day and checks whether the target or the stop came first. If the price opened below the stop (a gap), the loss is counted at the opening price. |
| **Event split** | The same replay, split into windows with and without a big-news day (results etc.). |
| **Nearest analogs** | The 50 past days that looked most like today: trend distance, recent returns, RSI, volatility, volume. |
| **Bootstrap simulation** | 20,000 synthetic paths stitched together from real 5-day blocks. It is also run with the past trend removed, so a past rally or crash isn't assumed to repeat. |
| **Market regime** | Uses only past days when Nifty was in the same trend as today. |
| **Event injection** | Inserts real past results-day moves at the expected date. |
| **Textbook model** | Standard volatility maths, as a sanity check only. |

When the methods agree, the estimate is more trustworthy. When they disagree by more than 15 points, the output flags it as **unstable** and gives a range instead of a single number.

### Reading the result

- **Break-even win rate** = 1 ÷ (1 + reward/risk). If the measured odds are below this, the trade loses money over time however good the story sounds.
- **Stop inside one day's normal movement** (`stop_in_atr < 1`): ordinary daily noise will hit it. That was the most common problem in real tests.
- **Level search:** only trust rows marked `holds_up: true`. If none hold up, the honest answer is that there is no reliable edge.

## Measuring accuracy (the prediction log)

Every analysed trade can be saved to `journal.csv` with its predicted odds. After the holding period, run `--calibrate` with fresh price files. The engine fills in what really happened and reports:

- **Calibration table:** when it said 20–40%, how often did the target actually get hit?
- **Brier score** compared with always guessing the average. Lower is better; if it isn't better than that baseline, the odds aren't adding anything.

**This is the only real way to know how accurate the tool is.** Until about 30 predictions have been scored, any accuracy figure, including the ~55% working assumption in the disclaimer, is a guess.

## Known limitations

- Past prices don't contain the future. Regime changes, regulation, fraud, wars and policy shocks aren't in the data.
- The scenario tree and the news adjustments involve judgement and are capped at ±15 points per factor.
- Costs default to 0.1% round trip; F&O costs, slippage and taxes vary.
- Lot sizes, expiry days and margin rules change. Always check current values.
- With only 1 year of data, the analog and level-search methods are weak or switch off.

## Credits

- Trading-framework content adapted from **[nse-trading-skills](https://github.com/Bhala-Srinivash/nse-trading-skills)** by Bhala Srinivash (MIT). See `THIRD_PARTY_NOTICES.md`.
- Bull/bear/risk debate structure inspired by **[TradingAgents](https://github.com/TauricResearch/TradingAgents)** by Tauric Research (Apache-2.0). No code from that project is included.
- Probability engine, workflow and documentation: this repository.

## License

MIT. See [LICENSE](LICENSE). Using this software does not create any advisory relationship. See [DISCLAIMER.md](DISCLAIMER.md).
