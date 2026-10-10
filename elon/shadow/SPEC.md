# Shadow logger spec (paper trading only)

**Safety.** The code only issues public HTTP GETs (gamma, clob `/book`, xtracker). There are no keys, no signing and no order code, and none must be added. `grep -ri "private_key\|py_clob\|post_order\|create_order" .` must stay empty.

## Cadence
`shadow_logger.py` every 15 min; `settle.py` daily; `report.py` on demand. Everything is stored in `shadow.db` (SQLite) plus `rawbooks/books_YYYYMMDD.jsonl.gz` (one line per bucket book per run).

## Each 15-min run
1. **Discover** live events: `{GAMMA}/events?series_id=10000|10816&closed=false&limit=100` (weekly | 48h), browser User-Agent from `common.py`. Events whose window has ended are skipped (settle.py handles them).
2. **Window**: `{XT}/users/elonmusk` -> `data.trackings[]` matched by `marketLink` slug; `startDate`, `endDate` (rounded up to the minute, 15:59:59 -> 16:00:00; end exclusive). Fallback: parse "from <date> 12:00 PM ET to <date> 12:00 PM ET" in the event description.
3. **Tracker posts**: `{XT}/users/elonmusk/posts?platform=x&startDate&endDate` cached in table `posts(id,c,i)`. A full 29-day re-pull happens once a day (to see late imports); other runs pull from min(now-3d, earliest live window start). Recorded per event in `tracker`: raw count in window, as-known count (createdAt in [S, now) and importedAt <= now), newest createdAt / importedAt, user `lastSync`, `lastSyncError`.
4. **Books**: `{CLOB}/book?token_id=<YES token>` for every bucket. 404 = closed bucket (`status=closed`). Best ask = min ask price; best bid = max bid; `depth2c_usd` = sum(price*size) over asks with price <= best ask + 0.02. Compressed JSON in `books.book_gz`, raw line in the daily gz.
5. **Model** (identical to `backtest.py`): as-known count K; hour-of-week rate = posts of the trailing 28 days per (epoch hour mod 168) slot / 4, with the `(created < t-1d) | (imported <= t)` filter; mu = sum of rate over the remaining window; remaining posts ~ NB(k, k/(k+mu)); `p_model = P(lo <= K + R <= hi)`. k comes from `k_table.json` (family x nearest backtest lead grid -5..95 step 5, plus -10), exported by `export_k.py` from `backtest.py`'s `k_walk` (per-lead fit if >= 10 prior events, pooled if >= 4, else 15). Refresh monthly: `python3 export_k.py` (about 1 min).
6. **Would-trade** (logged in `preds`, `would_trade=1`, row copied to `paper_trades`): buy YES at the real best ask if all hold: book ok and market not closed; lead in [-10, 95]% (the backtest-validated grid); 0.001 <= ask <= 0.50; `p_model - ask >= 0.05`. Fixed $10 stake, shares = 10/ask, fee 0.05*ask*(1-ask) per share. Skips: same event+bucket already bought within 12 h (`dedupe_12h`); event total stake would exceed $100 (`event_cap_100`); candidates ranked by edge. `skip_reason` records why each non-trade was not taken. Fill realism is logged, not enforced: `depth2c_usd` < $10 means the paper fill is optimistic (reported).

## Tables
- `runs(run_id, ts, ts_iso, status ok|partial|error, n_events, n_books, n_trades, last_sync, last_sync_error, errors)`
- `posts(id, c, i)` / `meta(k, v)`: tracker cache
- `tracker(run_id, ts, event_slug, family, window_start, window_end, window_source, raw_count, asknown_count, newest_created, newest_imported, last_sync, last_sync_error)`
- `books(run_id, ts, event_slug, token_id, bucket_lo, bucket_hi, status, best_ask, best_bid, depth2c_usd, book_gz)`
- `preds(run_id, ts, event_slug, family, bucket_lo, bucket_hi, token_id, lead_pct, lead_grid, k, k_src, K_asknown, mu, p_model, ask, bid, depth2c_usd, edge, would_trade, skip_reason)`
- `paper_trades(trade_id, run_id, ts, event_slug, family, bucket_lo, bucket_hi, token_id, lead_pct, lead_grid, p_model, ask, bid, edge, stake, shares, fee_per_share, depth2c_usd, K_asknown, mu, k)`
- `settlements(trade_id, event_slug, outcome_yes, pnl, pnl_p05, settled_ts)`; `pnl_p05` = same trade at ask + 0.5c
- `event_results(event_slug, family, window_start, window_end, win_lo, win_hi, tracker_final, tracker_lo, tracker_hi, mismatch, note, settled_ts)`

## Settlement (`settle.py`, daily)
For each logged event with window end in the past and no `event_results` row: fetch `{GAMMA}/events?slug=`. Resolved only if every market is closed and exactly one `outcomePrices[0] >= 0.99` with all others <= 0.01; otherwise retry next day. Then re-pull tracker posts for [S, E), map the count to its bucket, and set `mismatch=1` if it differs from the resolved bucket. PnL per trade: `shares*win - 10 - shares*fee`, at the logged ask and at ask+0.5c. Idempotent.

## Go-live criteria (evaluated by `report.py`)
(i) >= 8 weeks of runs and >= 15 resolved weekly events; (ii) ROI at logged ask >= +15% and still > 0 after dropping the 2 best events; (iii) event-clustered bootstrap p (ROI <= 0) < 0.10; (iv) median ask-mid gap on traded buckets <= 0.5c; (v) share of posts imported > 1 h after creation < 10% during the shadow period, and zero resolution mismatches; (vi) median $ within 2c of the ask on would-trades >= $25. All six must PASS.

## Failure handling
Every network call is wrapped; errors are printed to stderr (-> `logs/cron.log`) and stored in `runs.errors`; the run row is always finalised and the process always exits 0. Post-fetch failure -> model uses the existing cache; fewer than 200 cached posts or no live events -> run ends `error` without trading. Book failures skip only that bucket (`book_error`). Missed cron runs just leave gaps (dedupe is time-based).

## AWS EC2 cron
```
*/15 * * * * cd /home/ubuntu/elon-poly-experiment/elon/shadow && /usr/bin/python3 shadow_logger.py >> logs/cron.log 2>&1
17 6 * * *   cd /home/ubuntu/elon-poly-experiment/elon/shadow && /usr/bin/python3 settle.py >> logs/settle.log 2>&1
```
(use `venv/bin/python` instead of `/usr/bin/python3` if a venv is used). Keep the instance clock on chrony/NTP. Rotate `logs/` with logrotate; `rawbooks/` grows about 10-20 MB/day.
