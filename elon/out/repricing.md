# Repricing speed of Elon tweet-count markets after bursts (offline analysis, no orders)

Scope: 208 closed weekly/48h events from Dec 2025 (price data per bucket, forward-filled at most 30 min). Valid-M minutes: 78% (a minute needs >=80% of buckets priced and a raw price sum within 0.8-1.25).

## Definitions

- M(t): market-implied mean final count (normalised bucket prices x bucket mids; open top bucket mid = lo + typical width).
- F(t) = K(t) + mu(t): K = posts in window with importedAt <= t; mu = trailing-4-week hour-of-week rate (same function as backtest.py, re-implemented because importing it runs the full backtest).
- Burst: rolling 60-min import count >= max(8, 3 x expected hourly rate); first crossing, de-clustered by 240 min. Trigger time t0 = the minute the counter sees the burst.
- Quiet spell: >= 240 min with no imported post while the expected 4h count >= 4. t0 = minute the 4h mark is reached.
- Should-move: dF = F(t0) - F(t0-60) (the surprise the burst adds relative to the expected flow). Only events with |dF| >= 3 posts are used for fractions. Response fraction c(rel) = (M(t0+rel) - M(t0-60)) / dF, so 0 = nothing repriced, 1 = fully repriced; rel is measured from the counter-trigger time t0 (negative rel = before the counter saw it).
- Half-life = first rel minute at which c >= 0.5 (negative = the market got there before the counter trigger).

## Q8: counts

- Bursts detected: **603** (580 with |dF|>=3); quiet spells: **725** (103 used); placebo times: 8020 (784 with |dF|>=3).

### Fraction of the should-move already in the price (median across bursts)

| rel min from t0 | burst | quiet spell | placebo (|dF|>=3) |
|---|---|---|---|
| 0 | 0.88 | 0.33 | 0.50 |
| 5 | 0.99 | 0.39 | 0.50 |
| 15 | 1.08 | 0.46 | 0.55 |
| 30 | 1.17 | 0.55 | 0.61 |
| 60 | 1.32 | 0.66 | 0.74 |
| 120 | 1.36 | 0.68 | 0.90 |
| 240 | 1.35 | 0.98 | 1.38 |

Half-life (median per-event first crossing of 0.5, rel to t0): burst **-12 min**, quiet **-2 min**, placebo -14 min. Half-life of the median curve: burst -8, quiet 22.

### Literal spec: median of dM(tau)/dF(tau) with both measured from t0

(dF(tau) = F(t0+tau)-F(t0) is small and noisy because the burst is already in K at t0, so this ratio is unstable; pairs with |dF(tau)|<1 post dropped. Signs normalised so the burst direction is positive.)

| tau | median dM/dF burst | mean signed dM burst | mean signed dF burst | median dM/dF quiet | mean signed dM quiet |
|---|---|---|---|---|---|
| 5 | 1.00 | 1.09 | 0.77 | -0.35 | 0.14 |
| 15 | 1.13 | 2.18 | 1.65 | 0.21 | 0.39 |
| 30 | 1.10 | 3.31 | 2.53 | 0.34 | 0.67 |
| 60 | 1.09 | 4.42 | 3.17 | 0.45 | 0.87 |
| 120 | 0.98 | 5.02 | 3.50 | 0.52 | 0.98 |
| 240 | 0.97 | 6.21 | 3.32 | 0.73 | 1.57 |

Raw |dM| sanity (mean absolute change in M, posts) bursts vs placebo: tau 15: 2.85 vs 0.79; tau 60: 5.82 vs 1.86; tau 240: 9.46 vs 4.14

### Is there a profitable lag?

Rule: at t0+5 buy every bucket above the pre-burst (t0-60) market median bucket at raw mid + 0.5c, mark at mid at t0+60, equal shares, no fees, no exit spread. Quiet spells: mirror (buy buckets below the median). Returns are on cost.

| set | n | aggregate return | mean per-trade | median | win rate |
|---|---|---|---|---|---|
| burst_up_all | 569 | -4.2% | -4.2% | -7.6% | 29% |
| burst_up_p>=0.02 | 569 | 2.3% | 3.4% | -1.8% | 43% |
| placebo_up_all | 64 | -12.2% | -13.7% | -13.0% | 9% |
| placebo_up_p>=0.02 | 64 | -5.8% | -7.1% | -6.9% | 14% |
| quiet_down_all | 96 | -7.3% | -7.5% | -6.9% | 26% |
| quiet_down_p>=0.02 | 94 | -2.7% | -2.7% | -2.4% | 34% |

## Q9: does the lag shrink?

Bursts and quiet spells pooled (power), plus bursts only. Full table: out/repricing_by_month.csv. 'frac' = median response fraction from the baseline; 'lit' = literal dM/dF from t0.

| group | src | n | frac@t0 | frac@15 | frac@60 | lit15 | lit60 | half-life (per-event, min) | xcorr peak lag (importedAt) |
|---|---|---|---|---|---|---|---|---|---|
| 2025-12 | burst+quiet | 45 | 0.81 | 1.24 | 1.51 | 0.96 | 1.05 | -10 | 1 |
| 2025-12 | burst | 42 | 0.83 | 1.25 | 1.53 | 0.98 | 1.22 | -9 | 1 |
| 2026-01 | burst+quiet | 93 | 0.37 | 0.53 | 0.59 | 0.60 | 0.45 | -2 | -2 |
| 2026-01 | burst | 80 | 0.37 | 0.55 | 0.59 | 0.60 | 0.41 | -2 | -2 |
| 2026-02 | burst+quiet | 100 | 0.57 | 0.74 | 1.14 | 0.70 | 0.95 | -10 | -1 |
| 2026-02 | burst | 73 | 0.64 | 0.91 | 1.29 | 0.96 | 1.24 | -10 | -1 |
| 2026-03 | burst+quiet | 82 | 0.97 | 1.10 | 1.41 | 1.02 | 1.20 | -26 | -3 |
| 2026-03 | burst | 78 | 1.04 | 1.22 | 1.43 | 1.09 | 1.23 | -27 | -3 |
| 2026-04 | burst+quiet | 50 | 0.68 | 0.97 | 1.10 | 0.71 | 0.67 | -4 | -2 |
| 2026-04 | burst | 41 | 0.86 | 1.00 | 1.15 | 0.84 | 0.73 | -4 | -2 |
| 2026-05 | burst+quiet | 57 | 0.93 | 1.08 | 1.11 | 1.38 | 0.74 | -11 | -1 |
| 2026-05 | burst | 47 | 1.05 | 1.17 | 1.32 | 1.38 | 1.09 | -12 | -1 |
| 2026-06 | burst+quiet | 62 | 0.76 | 1.14 | 1.38 | 1.56 | 1.21 | -7 | -2 |
| 2026-06 | burst | 58 | 0.81 | 1.20 | 1.40 | 1.56 | 1.27 | -7 | -2 |
| 2026-07 | burst+quiet | 59 | 1.11 | 1.32 | 1.51 | 1.38 | 1.21 | -18 | -2 |
| 2026-07 | burst | 50 | 1.20 | 1.40 | 1.63 | 1.44 | 1.33 | -21 | -2 |
| 2026-08 | burst+quiet | 65 | 1.00 | 1.16 | 1.53 | 1.12 | 1.04 | -22 | -1 |
| 2026-08 | burst | 51 | 1.06 | 1.23 | 1.60 | 1.51 | 1.37 | -24 | -1 |
| 2026-09 | burst+quiet | 56 | 0.92 | 0.94 | 0.95 | 1.31 | 0.96 | -18 | -3 |
| 2026-09 | burst | 50 | 0.93 | 0.97 | 0.95 | 1.33 | 1.02 | -18 | -3 |
| 2026-10 | burst+quiet | 14 | 0.79 | 0.96 | 0.86 | 1.67 | 0.76 | -20 | -3 |
| 2026-10 | burst | 10 | 0.86 | 1.05 | 0.96 | 1.67 | 1.07 | -25 | -3 |
| T1 | burst+quiet | 281 | 0.60 | 0.77 | 1.14 | 0.75 | 0.81 | -10 |  |
| T1 | burst | 236 | 0.66 | 0.90 | 1.24 | 0.91 | 1.00 | -10 |  |
| T2 | burst+quiet | 195 | 0.80 | 1.01 | 1.14 | 1.17 | 0.91 | -10 |  |
| T2 | burst | 170 | 0.89 | 1.09 | 1.28 | 1.18 | 1.07 | -10 |  |
| T3 | burst+quiet | 207 | 0.93 | 1.13 | 1.35 | 1.34 | 1.11 | -18 |  |
| T3 | burst | 174 | 1.03 | 1.23 | 1.50 | 1.49 | 1.27 | -19 |  |

### Price-count cross-correlation (minute changes of M vs minute changes of K; lag>0 = M moves after K)

| month | n events | peak lag, K by importedAt (min) | corr | peak lag, K by createdAt (min) | corr |
|---|---|---|---|---|---|
| ALL | 208 | -2 | 0.137 | 0 | 0.380 |
| 2025-12 | 9 | 1 | 0.111 | 2 | 0.162 |
| 2026-01 | 23 | -2 | 0.073 | 1 | 0.132 |
| 2026-02 | 20 | -1 | 0.120 | 0 | 0.271 |
| 2026-03 | 22 | -3 | 0.138 | 0 | 0.323 |
| 2026-04 | 21 | -2 | 0.149 | 0 | 0.374 |
| 2026-05 | 21 | -1 | 0.140 | 0 | 0.395 |
| 2026-06 | 22 | -2 | 0.168 | 0 | 0.460 |
| 2026-07 | 22 | -2 | 0.187 | 0 | 0.513 |
| 2026-08 | 23 | -1 | 0.191 | 0 | 0.483 |
| 2026-09 | 21 | -3 | 0.161 | 0 | 0.550 |
| 2026-10 | 4 | -3 | 0.192 | 0 | 0.610 |

Caveats: minute-level M changes are dominated by thin-book noise and stale ticks (hence small correlations); few events per month in some months; bursts are clustered in time and overlap across events of the same period (weekly and 48h windows cover the same posts), so the effective sample is smaller than n; the placebo is conditioned on a like-sized fundamental surprise so it is a like-for-like noise reference.
