# Elon tweet-count markets: does the weather edge carry over?

*Built 2026-10-10. All numbers are from a from-scratch rebuild (`backtest.py`) on public data. No orders were placed.*

## Verdict: **GO-to-shadow, not to live money** (it sits on the MAYBE side of GO)

The model does carry some real information. But the edge is small, and it is fragile once real-world friction is added:

- With realistic fills at $10 a trade, ROI is about +60% (p≈0.04).
- At 1c of slippage it is +16% (p=0.24).
- Once we correct for having tried many strategy variants, the p-value is 0.45 at 0.5c slippage.
- It does not replicate on related markets.
- Its realistic capacity is tens of dollars a week, maybe a couple of hundred at best.

Running the shadow logger is free and it's already built, so run it for 8–12 weeks. Only trade live if it passes the checklist at the bottom.

## Headline numbers (weekly, as-known counts, leads 0/25/50/75, buy YES if model − price ≥ 5pp and price ≤ 50c, $10 flat, fee 0.05·p·(1−p))

| Fill assumption | Trades / events | ROI | Event-clustered p | 14-day block p |
|---|---|---|---|---|
| Mid price, 0 slippage | 384 / 86 | **+68%** | 0.018 | 0.018 |
| +0.5c | 327 / 82 | +41% | 0.078 | 0.091 |
| +1c | 282 / 77 | +16% | 0.24 | 0.28 |
| Realistic: mid + half the live spread, $10 | 346 / 82 | +61% | 0.042 | 0.038 |
| Realistic, $50 a trade (walks the book) | 346 / 82 | +46% | 0.063 | 0.067 |
| Realistic, $100 a trade | 346 / 82 | +30% | 0.12 | 0.12 |
| 48h family, mid price | 586 / 119 | +84% | 0.09 | 0.08 |
| 48h family, +1c | 520 / 118 | +20% | 0.22 | 0.20 |

**How this compares with the earlier scan** (+115%, p=0.001; +66% at 1c):
- My rebuild gives about half the ROI and a p-value about 20× weaker.
- Using the as-known count instead of the final count is **not** the cause: it changes PnL by only $10–20.
- The likely causes are the earlier scan's sample of 65 events (versus 86 here), the matching of entry prices, and how its 298 trades were counted. I can't check these exactly without its code.
- The one hot spot that holds is **50% elapsed**: +156% (p=0.03), against the scan's +224%.
- The scan's "+90% at window start" does **not** hold: I get +15% (p=0.45). At the start the bucket prices add up to about $1.30, so the 30% overround eats the edge.

## Answers to Q1–Q16

| # | Question | Answer |
|---|---|---|
| 1 | Driven by a few weeks? | **Yes.** The top 5 of 86 events make about 95% of the PnL. Dropping them leaves +4% at 0 slippage and −12% at 0.5c. Only 28 of 86 events are net positive. The chronological halves give +53% (p=0.19) and +82% (p=0.02), and at 1c the first half is −5%. Monthly ROI with realistic fills: Dec −53%, Jan +21%, Feb +309%, Mar +172%, Apr +100%, May +11%, Jun +206%, Jul +69%, Aug +89%, **Sep −44%, Oct −105%** (Oct is one event). This is normal for buying long shots: a random "no-information" strategy collapses even harder (−51% to −72% after dropping its top 5). So the lumpiness is expected, but it does mean we can't measure the edge's size precisely. |
| 2 | Realistic fills? | **Partly.** Live spreads are about 0.15c (≤2c buckets), 0.3c (2–5c), 1c (5–15c) and 6c (15–50c). Mid plus half the spread gives +61% at $10. Actual buy fills on Jul–Oct strategy trades were about 4% worse than the snapshot price (+54% versus +58%). Only 45% of ≤2c buckets had *any* buy fill within ±10 minutes, and touch depth there is about $2, so the <2c band is effectively untradable. A $10 order fits within 2c of the ask every time. $50 or more needs to walk the book on about 66% of trades. |
| 3 | Is "too narrow" stable? | **Only for weekly, and only early.** At window start the weekly market's spread is too narrow: the outcome is 1.25 SDs from the market mean on average (1.0 is well calibrated), and 35% of outcomes land in the outer 20% of the market's distribution. Pooled over the main leads it is 1.03 and 25%. From the 85% mark onward the market is *too wide*. The narrow months were Dec, Feb and May; others were not. The 48h market is **not** too narrow (0.86, 13%), and neither are the related families (pooled 0.80, 19%). There is no stable direction: Dec finished above the market mean 72% of the time, Apr only 17%. |
| 4 | Where does it sit? | Mostly in **upper-tail buckets** (wholly above the market mean): +151% (p=0.02) versus +23% for lower-tail buckets, falling to +23% at 1c. By price band, 5–15c is best (+81%, p=0.03) and <2c dies at slippage. By timing, leads 50–55% are best and 90–95% lose. Tue–Tue windows give +76% and Fri–Fri +59%. |
| 5 | As-known count used? | **Yes. I rebuilt with counts as they were known at the time** (importedAt ≤ t). The look-ahead version differs by only $10–20. Late imports were rare from Dec to Jul, so the original's choice didn't matter historically. |
| 6 | Independent bets? | 86 events, but only **44 non-overlapping weekly windows**. Fri–Fri windows alone give +59% (p=0.10); Tue–Tue alone give +76% (p=0.05). 14-day block bootstrap p is 0.018 / 0.09 / 0.28 at 0 / 0.5c / 1c. About 23 two-week blocks in total. |
| 7 | Who trades? | Full tape: all 208 events, 21.1M fills, 179k wallets. Volume is less concentrated than the 58-event sample suggested: the top 10 wallets hold 16% of notional and the top 50 hold 35%. About 1,100 market-maker-like wallets carry 36% of notional. The "sharp" class is mostly noise: 7.1k wallets are labelled sharp but about 1.1k of those are expected by chance, and only 247 made over $1k. Retail one-offs lose 3.7%. **Cheap YES in general:** buyers made +19% on $19M when held to resolution, but this is lottery-shaped and driven by a few hits. **Cheap upper-tail YES:** crowd buyers lost 95% on $9M, and the sellers (68% of them profitable overall) took it. The model trades this slice selectively, and in the backtest its above-the-market-mode trades made +81% (382 trades). So the edge is about picking, not blanket tail-buying, and the counterparties are pros. Source: `out/wallets.md`. |
| 8 | Repricing speed? | **Fast. No latency edge.** The market has priced in about 88% of a burst *before* xtracker imports it, so traders watch X directly. Buying after a burst returns −4%. Quiet spells reprice more slowly (0.33 priced in at the start, 0.66 after 60 minutes), but the mirror trade after quiet spells still loses 7%. |
| 9 | Is the lag shrinking? | **Yes, bots are here.** The share of a burst already priced in when it's imported rose from 0.60 to 0.80 to 0.93 across the three thirds of the sample. The price-to-count correlation rose from 0.13 to about 0.5, peaking at 0 minutes of lag. |
| 10 | Related markets | See the table below. The only other free, tracker-settled families are about 8 weekly post-count markets (Trump on Truth Social, White House, Zelenskyy, Khamenei, NYC Mayor, CZ, Ted Cruz), each with roughly $10–60k a week and $20–500 within 2c. View-count markets (MrBeast, GTA VI, Netflix) have no free settlement data. |
| 11 | Does it replicate on related markets? | **No.** On 7 families (388 events) with the model unchanged: +76% at 0 slippage (p=0.08), **+1% at 0.5c, −18% at 1c**. The model's Brier score is worse than the market's in 5 of 7 families. Only Khamenei (small counts) and CZ are positive after slippage. Trump on Truth Social looks narrow but has 26% tracker mismatches. |
| 12 | Same market on other venues? | **No live cross-check.** Kalshi's KXELONTWEETS has been dormant since April 2025, and Manifold has no live equivalent. Kalshi KXTRUTHSOCIAL (Trump Truth Social, weekly, 2.8M contracts) is live and could cross-check the Trump family. |
| 13 | Tracker reliability | Normal import lag is 2–3 minutes (p50 about 150s). Late imports: under 1% of posts Dec–Jul, 3.7% in Aug and Sep, **26% in Oct 2026** (one batch on Oct 8 brought in 115 posts up to 51 hours late). The longest real outages were 57.7h (Aug 26–28) and 23.5h (Sep 10). 12 of 89 weekly windows had posts arrive after the window closed (up to 12.5% of the count). **Yes, treat the live count as a lower bound.** The shadow logger records the gap. The Dec–Oct backtest wasn't affected (as-known and final counts are about the same). |
| 14 | Maker or taker? | **Unknown, because** fills of resting orders can't be backtested without order-book history (we only have trades). Facts: maker fee 0 with a 25% rebate; median liquidity reward **$15/day** per market (range $2–85) for 36 live Elon markets, minimum 20–50 shares, maximum spread 4.5–5.5c. The cheap-tail sellers who profit are mostly makers, which means passive *bids* on cheap tails get filled mostly when the tail is dying (adverse selection). The shadow logger stores full books so a queue simulation can be run later. |
| 15 | Capacity at 1c | About 8 trades a week across weekly events. At $10 a trade that's about $10/week PnL at 1c (about $30/week at 0.5c). With realistic fills at $50 a trade, about $180/week in the backtest, and roughly half that after an overfitting haircut. **Realistically $50–150/week.** |
| 16 | Resolution risk | 6,125 of 6,132 closed markets resolved cleanly (7 still "proposed" on one old 2024 event). 12 markets had a dispute entry and none changed the outcome. Tracker versus winning bucket matched 210 of 212 events since Dec 2025, and both misses were archived duplicate twins. Rule edge cases: deleted posts count only if the tracker caught them (about 5 minutes); X itself is the fallback source. The main risk is the rising late-import share. |

## Related recurring count markets (Q10)

| Family | Series | Window | Events/mo | Median vol (90d) | Free data | 2c depth (cheap buckets) |
|---|---|---|---|---|---|---|
| Elon posts, weekly | 10000 | 7d | 8.7 (overlapping) | $3.0M | xtracker, from Nov 2025 | about $2.0k |
| Elon posts, 48h | 10816 | 2d | 13 | $672k | xtracker | about $1.1k |
| Elon posts, daily or monthly | 10181 | 1d / 1mo | about 1 | $727k | xtracker | about $600 |
| Trump Truth Social posts | 11108 | 7d | 8.7 | $61k | xtracker, from Jan 2026 | about $520 |
| White House posts | 11335 | 7d | 8.7 | $36k | xtracker | about $50 |
| Khamenei / Zelenskyy / NYC Mayor / CZ / Ted Cruz | 11340/11349/11348/11347/11334 | 7d | 8.7 each | $9–20k | xtracker, from Mar 2026 | $20–220 |
| MrBeast views (several series) | 10061, 10321… | 1–19d | 2–14 | $36–282k | no | $150–230 |
| Trump X posts, Trump mentions | 11341, 11277 | 7d | 4.3 | $12–21k | no | about $20 |

## Adversarial review: objections and my ruling

| Objection | Reviewer | My ruling |
|---|---|---|
| Lottery skew: dropping winners kills anything | Partly holds | **Agree.** Fragility is generic, but we beat a no-information null at 0.5c (90–100th percentile). There is real information, but the size is very uncertain. |
| Forking paths / many specs tried | **Holds** | **Agree. This is the main reason not to go live.** White's reality check gives p=0.45 at 0.5c. Our main spec was fixed in advance by the earlier scan and sits at only the 35th percentile of the grid, so there was no cherry-picking here. But the scan itself was a search. |
| Mid vs executable ask | Partly holds | **Agree.** Drop <2c entries live. Actual fills are about 4% worse. |
| Stale prices | Rebutted | Agree (+70% on freshly updated prices). |
| Regime (post rate halved) | Rebutted | Mostly agree: Mar–Oct carries 77% of PnL. **But Sep and Oct are negative**, the first losing streak since Dec. Watch it. |
| Data integrity | Rebutted for the backtest | Agree, and **live risk is rising** (26% late imports in Oct). |
| Model no better calibrated than the market | Partly holds | Partly. Regressing outcome on both, the model gets weight 0.93 [0.80–1.06] and the price 0.10, which is real information. ROI by edge size isn't monotone, though. Model-picked entries at ≥5c make +69% at 0.5c (p=0.017), while model-free 5–15c entries lose. |
| Capacity and competition | **Holds** | **Agree.** At most tens to low hundreds of dollars a week. Pros and makers are present, and repricing has sped up. |
| *Mine:* no replication on related markets | — | A big strike. Weather was confirmed on a second venue; this isn't confirmed on sibling markets. |

The reviewer puts the chance that a live weekly strategy makes more than $0 after costs over 6 months at about **40%**. I'd put it at **35–45%**. The expected profit is small even if the edge is real.

## Weather green flags this lacks

| Weather had | Elon market | Fixable? |
|---|---|---|
| A physics forecast from outside the market | Only one person's past behaviour | **No.** Partial proxies: news and event calendars (launches, earnings, political news). Untested. |
| Many independent markets every day | About 44 independent weeks in 10 months | **Partly.** Add the 48h family and sibling families, but those didn't replicate. |
| A stable process with published research | One person, regime shifts (69 → 29 posts a day) | **No.** Walk-forward refits help at the margin. |
| Two venues agreeing | Polymarket only. Kalshi's Elon market has been dormant since Apr 2025 | **No** for Elon. Possible for Trump via Kalshi KXTRUTHSOCIAL. |
| Settlement independent of the venue | Polymarket's own xtracker, late imports rising | **Partly.** Count from X directly as a cross-check and treat the tracker as a lower bound. |
| Thin, retail-heavy books | $2–10M a week; makers and pros hold most volume | **No.** That's the market. |

## Shadow test: what it must show before any live money
(Implemented in `shadow/report.py`. The rule is frozen: the same spec as the backtest. The secondary arm is entries ≥5c only, decided in advance here.)
1. At least 8 weeks and at least 15 resolved weekly events logged.
2. Paper ROI at the **logged ask** of at least +15%, and still above 0 after dropping the top 2 events.
3. Event-clustered p below 0.10, or below 0.20 if the ≥5c arm agrees in sign and size.
4. Median ask-minus-mid gap on traded buckets of at most 0.5c, and median $ within 2c of the ask of at least $25.
5. Tracker late-import share (more than 1 hour late) under 10%, and zero resolution mismatches.
If it passes, start live at $10 a trade, a $100 cap per event, taker only, and buckets of 5c or more.

## How fast can the shadow test give an answer?
The shadow logger already trades the weekly and 48h markets together. Daily markets are too thin to add: about 36 events in total and about $600 of book.
Together the two families resolve about 4.6 events a week. That is about 1.5× faster than weekly-only, not 7×.
The edge pays out like a lottery: only about 27–32% of events make money, and the median event loses its whole stake.
The table below comes from a simulation that resamples backtest events at +0.5c slippage:

| Shadow length | Real edge: chance the record shows a loss | Real edge: chance ROI > +15% | No edge: chance ROI > +15% (fluke) |
|---|---|---|---|
| 4 weeks | 36% | 54% | 32% |
| 8 weeks | 27% | 62% | 34% |
| 12 weeks | 20% | 67% | 33% |
| 26 weeks | 10% | 77% | 31% |

**What this means:**
- Shadow results under about 12 weeks can't tell a real edge from luck.
- Shadow mostly checks the mechanics: fills, spread, depth and tracker reliability. Those answers come within 2–4 weeks.
- A clearly negative ROI after 12 weeks or more is a fair reason to stop.

## Next steps
1. Deploy `shadow/` on the EC2 box: run `shadow_logger.py` every 15 minutes, `settle.py` daily and `report.py` weekly. See `README.md`.
2. Add an X-side post counter (a second source) to the shadow logger so tracker undercounts can be measured live.
3. After about 4 weeks of stored books, simulate resting cheap-tail bids against the logged books to answer Q14 (maker fills plus rewards).
4. Optional: cross-check the Trump Truth Social family against Kalshi KXTRUTHSOCIAL as the one possible two-venue replication.
