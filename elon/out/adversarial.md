# Adversarial review: weekly Elon tweet-bucket edge

Reproduce with `python3 adversarial.py` (about 4 min; full numeric dump in `out/adversarial_raw.txt`). Offline only, no orders. Replication: primary weekly slip-0 gives n=384, ROI +68.3%, PnL $2624, which matches `bt_trades.csv` exactly. At 0.5c ROI is +41%, at 1c it is +16%.

## 1. Lottery skew (null strategies)
Argument: dropping the top-k winners kills any longshot strategy, so the "fragility" proves nothing, and the +68% is just a longshot buyer's mid-price artifact.
Test: 3 no-information nulls with the same fee, and 600-2000 reps each. (a) Random buckets at the same lead with entry within [0.7x, 1.43x] of each real trade. (b) Model shuffled across buckets within each event x lead, then the same rule applied. (c) Random eligible buckets, same count per event x lead.

| slip | null | null ROI mean (95% range) | % of null >= ours | null ROI after dropping top-5 events | % of null >= ours after top-5 |
|---|---|---|---|---|---|
| 0 | matched price | +21% (-47%..+130%) | 14% | -51% | 0.2% |
| 0 | shuffled model | +30% (-49%..+123%) | 20% | -72% | 0.1% |
| 0 | same count | +69% (-50%..+257%) | 44% | -60% | 0.3% |
| 0.5c | matched price | -3% | 10% | -56% | 1.7% |
| 0.5c | shuffled model | -59% | 0.0% | -89% | 0.0% |
| 0.5c | same count | -35% | 2.2% | -85% | 0.0% |

- The null itself earns +20% to +70% at zero slippage. Reasons: buying at the mid or last-trade price, and the market underpricing 0.5-1% buckets (hit rate 1.6% vs 0.7c price). Model-free "buy every bucket at 0.5-5c" gets +54% at 0 slip (p=0.04) and -56% at 0.5c.
- So the slip-0 headline of +68% is inside the null's range. It is not evidence of skill.
- The fragility is NOT special in the way the objection claims. After dropping the top 5 events our ROI is +3.5%, while the null is -51% to -72% (we beat 99.7%+ of null draws). At 0.5c we beat 90-100% of the null on the full sample, and 98-100% of it after dropping the top 5.
- Verdict: **partially holds.** The 0-slip number is meaningless. The 0.5c result is better than lottery noise, though the nulls are wide.

## 2. Forking paths
Grid: 9 lead sets x 4 edge thresholds (2/5/8/12pp) x 3 price caps (15/30/50c) x 2 entry floors = 216 specs per slip level.

| slip | specs (n>=15) | % ROI>0 | median ROI | specs with block p<.05 | White reality check p (studentised max) |
|---|---|---|---|---|---|
| 0 | 195 | 87% | +51% | 47 | 0.16 |
| 0.5c | 192 | 75% | +21% | 13 | 0.45 |
| 1c | 187 | 64% | +8% | 5 | 0.58 |

- Holm over 216 specs needs p<2.3e-4, and no spec reaches it. The primary spec sits at the 33rd-45th percentile of its own grid, so it is unremarkable and was not cherry-picked from the top.
- Positivity depends on the lead set. At 0.5c the lead 25, 50 and primary sets are 100% positive. Early leads 0-45 are only 37% positive. The 21 single leads are 9/20 positive at 0.5c (binomial p=0.75).
- Per-lead hot spots (lead 50-55) were found after looking. The project also forked on family, k method, lookahead, rate window and slip, which is roughly 30-100 effective specs.
- Verdict: **holds.** After the search, the best spec's reality-check p is 0.16 at slip 0 and 0.45 at 0.5c. The sign is mostly positive, but significance is not established.

## 3. Mid vs executable ask
- Live books: ask minus mid is 0.1c (22% of price) at <=2c, 0.2c (5%) at 2-5c, 0.5c (4%) at 5-15c and 3c (7%) at 15-50c. 17 of 90 books have no bid.
- Raw trades exist only for Jul-Oct 2026 (69 events). Actual BUY-YES prints within ±10 min are on average at or below the snapshot price (median ratio 0.89-0.98). Last print was a sell in 47-52% of rows, so the snapshot is not systematically a bid.
- 101 strategy trades in that coverage: ROI +54% at the actual median BUY print vs +58% at the snapshot (mean print/snap 1.04).
- The real problem is fill availability. Only 45% of <=2c rows had any BUY print in ±10 min (68-71% in the higher bands), and 14 of 101 trades had none. Touch depth at <=2c is about $2.
- Verdict: **partially holds.** Price bias is small (about 4% worse) in Jul-Oct, but this says nothing about Dec-Jun, where no trade data exists. The <2c fills are the weak spot.

## 4. Stale prices
- Minutes since last price change at the trades: median 4, p75 17, p90 67. Snapshot dt_sec median is 11 s.
- Fresh (<=30 min, n=313) ROI +70%, p=0.029. Stale (>30 min, n=71) ROI +63%. Age >120 min (n=17) ROI -36%. At 0.5c, fresh n=269 ROI +44% (p=0.09).
- Verdict: **rebutted.** The edge is not driven by stale quotes.

## 5. Regime
- Slip 0: Dec-Feb ROI +44% (23% of PnL, p=0.31). Mar-Oct ROI +82% (77% of PnL, p=0.010). At 0.5c: Dec-Feb +18%, Mar-Oct +55% (p=0.035).
- Dec 2025 is -55%. The best single event is Feb 3-10 at $921 (35% of PnL).
- Mar-Oct leave-k-out ROI for k=0, 1, 2, 3, 5: +82%, +59%, +44%, +31%, +8%.
- Verdict: **rebutted.** PnL is not concentrated in the high-rate regime. It is positive in the 27-35 posts/day regime, but only 3 events carry it.
- Caveat: Sep-Oct 2026 are negative (-28%, -105% on one event).

## 6. Data integrity
- All 88 weekly events: tracker final_count falls inside Polymarket's resolved bucket (0 mismatches). The 122 "disagreements" in `ops_resolution.md` come from pre-Nov-2025 events that have no posts in the tracker and do not apply to our sample.
- 17 of 88 events contain at least one post imported >1h late. Their trades net +$127. Late-import share is rising live: 3.7% in Aug and Sep, then 26% in Oct 2026, with a 112-post late batch in the Oct 2-9 event (-$73).
- The Nov 2025 backfill (648 posts imported 2025-11-24) pollutes the trailing rate for Dec 2025.
- Deleted posts cannot be audited, since the CSV has no flag.
- Verdict: **rebutted for the backtest, partially holds for live use.** A growing tracker outage rate hits the as-known model directly.

## 7. Is the edge real? (monotonicity)
- Over all priced rows (price 0.1-50c, n=6094), excess return (hit minus price) by edge bin is: -15.5pp for edge < -5pp, and about 0 for edge in -2pp to +2pp. It then rises to +3.2pp (5-8pp), +4.8pp (8-12pp) and +6.7pp (12-20pp). Beyond that it falls to -4.6pp (n=13, >20pp). Spearman(edge, outcome-price) = 0.40.
- Regression of outcome on price and p_model: p_model coefficient 0.93 [0.80, 1.06], price coefficient 0.10 [0.05, 0.15] (event-cluster bootstrap). The result holds after dropping the top-5 events (0.93) and in Mar-Oct only (1.01). In Dec-Feb only it is 0.32 [-0.08, 0.77]. In this cheap region the model dominates the price, which is inconsistent with "pure luck".
- Trade ROI by edge bin is NOT monotone: +103%, +12%, +58%, -60% (n=13) at slip 0.
- Calibration is similar overall (Brier equal weekly, worse at 48h), because the information sits in the 0.1-50c tail rows only.
- Model-free entries at 5-15c lose (-12% to -20%). Our model-selected entries at >=5c earn +69% at 0.5c (n=160, p=0.017). So selection by model adds value beyond cheapness.
- Verdict: **partially holds.** There is a signal, but the large-edge tail is unreliable and the claimed monotone payoff is not there.

## 8. Capacity and competition
- $10 flat: $61/week at slip 0, $31/week at 0.5c, $10/week at 1c (about 7-9 trades/week). Leave-top-5 PnL is $128 at 0, -$369 at 0.5c and -$542 at 1c.
- Book depth within 2c is about $28 for <=2c buckets, $41 for 2-5c, $155 for 5-15c and $45 for 15-50c. The $100/trade realistic-fill ROI of +30% has p=0.12.
- Bursts are repriced about 8-12 minutes before the tracker sees them (repricing.md). That is not a problem for the pre-window weekly bet, but it kills any intra-window burst alpha and implies informed competitors.
- Verdict: **holds** as to dollars. The edge is real at best a few tens of dollars a week and cannot scale.

## Overall
Probability that a live weekly strategy makes >0 after costs over the next 6 months: **about 40%.**
- For: robust p_model coefficient, ≥5c entries positive at 0.5c, no stale-price or resolution artifact, and an unremarkable but not noise-like grid position.
- Against: only 44 independent windows, 3-5 events carry the PnL, the reality check fails after the search, 1c slip is +16% (p=0.24), <2c fills are unreliable, tracker outages are rising, and the last 2 months are negative.
- Six months is about 26 windows. Even at a true +20% ROI the chance of a positive realised PnL is only about 60% with this skew.

The single piece of evidence that would change this most: 10-12 weeks of live-shadow paper fills against actual ask books (≥5c entries, true bid/ask, timestamped), showing ROI >20% at the touch.
