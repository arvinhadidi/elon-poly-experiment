# Polymarket API probe notes (Elon weekly + 48h trade tape)

All calls public, no keys. Script: `elon/pull_trades.py`.

## Trades: data-api `GET /trades`
- **`takerOnly` must be `false`.** Default (true) returns only taker fills: 697 rows vs 1785 for a test market with takerOnly=false.
- `market=<conditionId>` works. `conditionId` from gamma `GET /markets/<market_id>`.
- `limit`: 1000 used; 3000 and 5000 accepted in tests (returned all rows), 10000 accepted.
- `offset`: works through offset 3000 (page at offset 3000 returned 296 rows for a 3296-row market). Offset 4000+ returned 0 rows; offset 15000+ returned HTTP 400.
- `start` / `end` (unix seconds): **work, both inclusive**. Verified with trade timestamps at start=end=T and start=T-1,end=T.
- `before` / `after`: no effect observed (returned the same rows as unfiltered).
- Pipeline: pages at offset 0/1000/2000 and splits any window reaching 3000 rows into two inclusive halves by time. 17,429 splits across 3,714 markets. No failed markets or events.
- Full tape cross-checked for one market (3296 rows): unfiltered paging and 1-hour window walk returned the same rows.
- Exact duplicate rows (same tx hash, wallet, asset, side, size, price, timestamp) occur in the API's own unfiltered output too (about 1-3% of rows). Kept as-is.

## Completeness
- Full run: 208 events, 21,143,190 trades, 179,055 unique wallets, notional $760.8M.
- Notional / gamma `event_volume`: median 0.75, 10th pct 0.52, 90th pct 0.86, min 0.22.
- Six March-2026 events exceed 1.0 (up to 10.7x). Likely gamma `event_volume` in events.csv does not match the event's full volume, not a data-api overcount. Not resolved.
- Largest December-2026 market (23.9M gamma volume) returned only 3,296 trades (~$283k notional, ~1%). Its tape starts 24 Feb 2026 and ends 1 Mar 2026, with no earlier trades returned. Unresolved gap.

## Holders: data-api `GET /holders?market=<conditionId>&limit=100`
- Works. Returns a list of `{token, holders:[...]}`, one entry per YES/NO token. Holder rows include `proxyWallet`, `asset`, `pseudonym`, `amount`, plus bio/profile fields.
- Tested on all 26 bucket markets of the 10 most recent weekly events: 260/260 ok. Saved to `data/raw/holders_recent_weekly.json`.

## Leaderboards
- `GET {DATA}/leaderboard`: **404**.
- `GET https://lb-api.polymarket.com/profit?window=all&limit=50`: **200**. Rows: `proxyWallet`, `amount` (profit, USD), `pseudonym`, `name`.
- `GET {DATA}/v1/leaderboard?category=overall`: **200**. Rows: `rank`, `proxyWallet`, `userName`, `vol`, `pnl`, `verifiedBadge`, `profileImage`.

## Per-wallet PnL
- `GET {DATA}/value?user=<wallet>`: 200. Returns `{user, value}`.
- `GET {DATA}/positions?user=<wallet>&limit=500`: 200. Open positions. Fields include `asset, conditionId, size, avgPrice, initialValue, currentValue, cashPnl, realizedPnl, percentPnl, totalBought, curPrice, eventSlug, title, redeemable, mergeable, endDate`.
- `GET {DATA}/closed-positions?user=<wallet>`: 200. Returns 10 rows by default; `limit=500` returns 50 (max observed); offset paging returned the same rows, so no full history via paging. Fields include `realizedPnl, totalBought, avgPrice, curPrice, timestamp, eventSlug, title, outcome`.
- `GET {DATA}/activity?user=<wallet>&limit=`: 200. Trade/activity rows (`timestamp, conditionId, type, size, usdcSize, transactionHash, price`).
