# elon/: Polymarket Elon tweet-count edge study

Read `FINDINGS.md` for the verdict, and open `elon_edge.html` for the visual report.
Every script calls only public GET endpoints, and none of them can place an order. No API keys are needed.

## Setup
```
python3 -m venv .venv && . .venv/bin/activate
pip install requests pandas numpy scipy pyarrow
cd elon
```
Every request goes through `common.py`, which sends a browser User-Agent (Gamma returns 403 without one) and retries on errors.

## Rerun order
| Step | Script | Output | Time |
|---|---|---|---|
| 1 | `pull_events.py` | `data/events.csv`, `data/events_summary.csv` (every Elon event and bucket, weekly/48h/daily/monthly) | ~7 min |
| 1 | `pull_posts.py` | `data/posts_elonmusk.csv` (xtracker posts with createdAt/importedAt), `posts_lag_monthly.csv` | ~1 min |
| 1 | `pull_related.py` | `data/related_inventory.csv`, `related_events.csv`, `related_notes.md` (Q10, Q12) | ~30 min |
| 2 | `pull_prices.py` | `data/raw/prices/*.parquet` (minute history), `data/price_snapshots.csv` (±10-min matched) | ~10 min |
| 2 | `pull_trades.py` | `data/raw/trades/*.parquet` (data-api trade tape) | hours |
| 3 | `backtest.py` | `out/bt_summary.md`, `bt_trades.csv`, `bt_preds.parquet` | ~1 min |
| 4 | `robustness.py` | `out/robustness.md` + `chart_*.csv` (Q1–Q6) | ~3 min |
| 5 | `repricing.py` | `out/repricing.md` (Q8–Q9) | ~5 min |
| 5 | `wallets.py` | `out/wallets.md` (Q7) | ~3 min |
| 6 | `pull_related_data.py`, `related_backtest.py` | `out/related_bt.md` (Q11) | ~10 min |
| 7 | `ops_checks.py {tracker,books,rewards,lag,resolution}` | `data/ops_*.{csv,md}` (Q13–Q16) | ~40 min |
| 8 | `adversarial.py` | `out/adversarial.md` | ~4 min |
| 9 | `build_html.py` | `elon_edge.html` | seconds |

`data/raw/` and `*.parquet` are gitignored (about 200 MB), so rerun steps 2–3 to rebuild them.

## Key gotchas
- Gamma `tag_slug=tweet-markets` now returns nothing. Pull by series id instead: 10000 (weekly), 10816 (48h), 10181 (daily and monthly). `limit` caps at 100.
- `prices-history` needs `startTs`/`endTs` and rejects ranges over ~14 days. `fidelity=1` gives minute data. Match the entry price only to a point within ±10 min of the target time.
- xtracker posts start on 2025-11-01, and November is a backfill. Use windows from 2025-12-01 onward. `endDate` is exclusive (UTC days).
- data-api `/trades` returns both sides of each fill (same transactionHash). Per-wallet PnL is correct, but summed notional double-counts.

## Shadow logger
See `shadow/README.md` and `shadow/SPEC.md`. It is paper only and cron-able on EC2 every 15 min.
