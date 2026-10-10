# Robustness analysis: Elon tweet-count bucket backtest

Primary spec: weekly family, as-known model, leads {0,25,50,75}, rule buy YES if p_model - entry >= 0.05, entry <= 0.50, entry >= 0.001, flat stake, fee 0.05 e (1-e) per share. Bootstrap: 10000 reps, seed fixed, p = P(bootstrap ROI <= 0). No orders are placed by this script.

## Takeaways (one line per question)

- Q1: Edge is concentrated: dropping the top 5 events takes slip0 ROI from +68% to +4% (0.5c: -12%); top-5 events = +95% of slip0 PnL; only 28/86 events net positive; 8/11 months positive.
- Q2: Realistic fill (mid + half spread, $10) keeps ROI +61% (p=0.042); $50 +46% (p=0.063); $100 +30% (p=0.120). $10 exceeds median touch depth on 209/346 trades, never the 2c depth; $50/$100 exceed 2c depth on 230.
- Q3: Weekly market is borderline too narrow at primary leads (SD(z) ~1.03, outer-20% share ~25% vs 20%), driven by leads 0-70 and Dec/Feb/May months; late leads (85+) are too wide. 48h market is not too narrow (SD(z) ~0.86, outer ~13%). Model is not too narrow (outer 11-14%). Directional: no clear upper/lower asymmetry overall; Dec 2025 realised was well above, Apr 2026 below.
- Q4: Profit comes from upper-tail buckets (bucket entirely above market mean), mid prices 2-15c, and lead 50-55; <2c and lead 0 vanish at 1c slippage; leads 90-95 lose. Fri and Tue windows are both positive at slip0.
- Q5: As-known vs lookahead differ by only ~$10-20 PnL; late-import K gaps are tiny (mean dK <0.35 posts) except Oct 2026 (one event).
- Q6: 384 trades from 86 overlapping events collapse to ~44 independent weekly windows; independent Tue-only/Fri-only subsets give ROI +76%/+59% (p 0.051/0.103) at slip0, and p 0.15-0.5 at 0.5c-1c.

## Live book medians (data/ops_books.csv, by best_ask band) versus the spec values used
| band | n books | median spread (data) | spread used | touch $ (data) | touch used | 2c depth $ (data) | 2c used |
|---|---|---|---|---|---|---|---|
| <=2c | 35 | 0.0015 | 0.0015 | 1.9 | 2 | 27.7 | 28 |
| 2-5c | 20 | 0.0030 | 0.0030 | 3.3 | 3 | 41.2 | 41 |
| 5-15c | 25 | 0.0100 | 0.0100 | 22.4 | 22 | 154.8 | 155 |
| 15-50c | 10 | 0.0600 | 0.0600 | 22.2 | 22 | 44.6 | 45 |

Sanity: rebuilt slippage trades vs bt_trades.csv (weekly primary): slip0: n 384/384, pnl 2624.16/2624.16; slip0.5c: n 327/327, pnl 1350.37/1350.37; slip1c: n 282/282, pnl 441.66/441.66

## Headline by fill assumption
Fills: slip0/0.5c/1c = mid + flat slippage at $10. real10 = entry mid + half live median spread of mid's band, stake min($10, median 2c depth) = $10. real10_touchcap = same but stake capped at min($10, median touch depth) (extra, stricter). real50/real100 = $50/$100 per trade: first part up to the band's median 2c depth at entry, remainder at entry + 2c. ROI = PnL / total stake. 2-event-clust = bootstrap over blocks of 2 chronologically adjacent events.

### Weekly primary (as-known, leads 0/25/50/75)
| fill | n trades | n events | stake $ | PnL $ | ROI | p event-clust | p 2-event-clust | p 14d-block |
|---|---|---|---|---|---|---|---|---|
| slip0 | 384 | 86 | 3840 | 2624 | +68% | 0.018 | 0.017 | 0.018 |
| slip0.5c | 327 | 82 | 3270 | 1350 | +41% | 0.078 | 0.085 | 0.091 |
| slip1c | 282 | 77 | 2820 | 442 | +16% | 0.239 | 0.254 | 0.280 |
| real10 | 346 | 82 | 3460 | 2113 | +61% | 0.042 | 0.040 | 0.038 |
| real10_touchcap | 346 | 82 | 1895 | 1224 | +65% | 0.009 | 0.009 | 0.006 |
| real50 | 346 | 82 | 17300 | 7962 | +46% | 0.063 | 0.061 | 0.067 |
| real100 | 346 | 82 | 34600 | 10456 | +30% | 0.120 | 0.115 | 0.125 |

### 48h (as-known, leads 0/25/50/75)
| fill | n trades | n events | stake $ | PnL $ | ROI | p event-clust | p 2-event-clust | p 14d-block |
|---|---|---|---|---|---|---|---|---|
| slip0 | 586 | 119 | 5860 | 4903 | +84% | 0.091 | 0.093 | 0.076 |
| slip0.5c | 556 | 118 | 5560 | 2424 | +44% | 0.130 | 0.134 | 0.109 |
| slip1c | 520 | 118 | 5200 | 1043 | +20% | 0.219 | 0.230 | 0.197 |
| real10 | 540 | 118 | 5400 | 3708 | +69% | 0.143 | 0.145 | 0.118 |
| real10_touchcap | 540 | 118 | 3663 | 1426 | +39% | 0.077 | 0.083 | 0.068 |
| real50 | 540 | 118 | 27000 | 11564 | +43% | 0.182 | 0.183 | 0.150 |
| real100 | 540 | 118 | 54000 | 12545 | +23% | 0.258 | 0.271 | 0.226 |

## Q1 Concentration (weekly primary)

### Leave-k-events-out ROI (drop the top-k events by PnL)
| k | slip0 | slip0.5c | slip1c | real10 | real10_touchcap | real50 | real100 |
|---|---|---|---|---|---|---|---|
| 0 | +68% | +41% | +16% | +61% | +65% | +46% | +30% |
| 1 | +45% | +23% | +6% | +37% | +56% | +29% | +17% |
| 2 | +30% | +13% | -2% | +21% | +47% | +17% | +8% |
| 3 | +20% | +4% | -10% | +10% | +39% | +7% | +0% |
| 4 | +11% | -4% | -15% | +1% | +31% | -1% | -7% |
| 5 | +4% | -12% | -21% | -7% | +24% | -9% | -14% |
| 6 | -4% | -20% | -26% | -16% | +16% | -17% | -21% |
| 7 | -12% | -25% | -30% | -25% | +8% | -25% | -27% |
| 8 | -18% | -31% | -35% | -30% | +1% | -31% | -32% |
| 9 | -24% | -35% | -40% | -35% | -6% | -36% | -37% |
| 10 | -29% | -40% | -45% | -41% | -12% | -41% | -42% |
| 11 | -34% | -45% | -48% | -45% | -19% | -46% | -47% |
| 12 | -39% | -48% | -54% | -50% | -25% | -51% | -52% |
| 13 | -44% | -53% | -58% | -56% | -31% | -56% | -55% |
| 14 | -49% | -56% | -62% | -60% | -37% | -60% | -60% |
| 15 | -54% | -62% | -66% | -64% | -43% | -64% | -63% |

### Split-half (chronological halves by window_start, and odd/even events)
| fill | subset | n | events | ROI | p event-clust |
|---|---|---|---|---|---|
| slip0 | chron first half | 181 | 42 | +53% | 0.186 |
| slip0 | chron second half | 203 | 44 | +82% | 0.018 |
| slip0 | even events | 203 | 43 | +76% | 0.050 |
| slip0 | odd events | 181 | 43 | +59% | 0.101 |
| slip0.5c | chron first half | 147 | 38 | +43% | 0.220 |
| slip0.5c | chron second half | 180 | 44 | +40% | 0.111 |
| slip0.5c | even events | 181 | 40 | +41% | 0.162 |
| slip0.5c | odd events | 146 | 42 | +41% | 0.169 |
| slip1c | chron first half | 125 | 34 | -5% | 0.578 |
| slip1c | chron second half | 157 | 43 | +32% | 0.137 |
| slip1c | even events | 159 | 38 | +3% | 0.480 |
| slip1c | odd events | 123 | 39 | +32% | 0.208 |
| real10 | chron first half | 162 | 38 | +61% | 0.162 |
| real10 | chron second half | 184 | 44 | +62% | 0.078 |
| real10 | even events | 185 | 40 | +56% | 0.147 |
| real10 | odd events | 161 | 42 | +67% | 0.093 |
| real10_touchcap | chron first half | 162 | 38 | +74% | 0.053 |
| real10_touchcap | chron second half | 184 | 44 | +58% | 0.051 |
| real10_touchcap | even events | 185 | 40 | +55% | 0.064 |
| real10_touchcap | odd events | 161 | 42 | +77% | 0.045 |
| real50 | chron first half | 162 | 38 | +41% | 0.209 |
| real50 | chron second half | 184 | 44 | +50% | 0.095 |
| real50 | even events | 185 | 40 | +40% | 0.170 |
| real50 | odd events | 161 | 42 | +53% | 0.115 |
| real100 | chron first half | 162 | 38 | +23% | 0.299 |
| real100 | chron second half | 184 | 44 | +36% | 0.142 |
| real100 | even events | 185 | 40 | +23% | 0.260 |
| real100 | odd events | 161 | 42 | +38% | 0.160 |

### Top-5 events share of PnL and events net positive
| fill | total PnL $ | top-5 PnL $ | top-5 share | events net positive / traded |
|---|---|---|---|---|
| slip0 | 2624 | 2496 | +95% | 28/86 |
| slip0.5c | 1350 | 1720 | +127% | 26/82 |
| slip1c | 442 | 984 | +223% | 24/77 |
| real10 | 2113 | 2356 | +111% | 25/82 |
| real10_touchcap | 1224 | 801 | +65% | 26/82 |
| real50 | 7962 | 9474 | +119% | 25/82 |
| real100 | 10456 | 15041 | +144% | 25/82 |

Top-5 events at slip0: elon-musk-of-tweets-february-3-february-10 (+921$), elon-musk-of-tweets-june-19-june-26 (+583$), elon-musk-of-tweets-june-30-july-7 (+392$), elon-musk-of-tweets-august-28-september-4-2026 (+312$), elon-musk-of-tweets-march-20-march-27 (+288$)

### Month-by-month PnL ($) and n trades (window_start month)
| month | slip0 | slip0.5c | slip1c | real10 | real10_touchcap | real50 | real100 |
|---|---|---|---|---|---|---|---|
| 2025-12 | -323 (n=59) | -428 (n=48) | -388 (n=44) | -285 (n=54) | -197 (n=54) | -1484 (n=54) | -3246 (n=54) |
| 2026-01 | 145 (n=53) | 108 (n=49) | 129 (n=41) | 110 (n=52) | 221 (n=52) | 433 (n=52) | 334 (n=52) |
| 2026-02 | 789 (n=26) | 529 (n=21) | -59 (n=15) | 741 (n=24) | 193 (n=24) | 2453 (n=24) | 3314 (n=24) |
| 2026-03 | 331 (n=22) | 298 (n=19) | 269 (n=17) | 326 (n=19) | 193 (n=19) | 1508 (n=19) | 2450 (n=19) |
| 2026-04 | 42 (n=19) | 142 (n=8) | 6 (n=6) | 110 (n=11) | 165 (n=11) | 550 (n=11) | 1101 (n=11) |
| 2026-05 | 402 (n=64) | 97 (n=58) | 116 (n=52) | 63 (n=57) | 170 (n=57) | 258 (n=57) | 252 (n=57) |
| 2026-06 | 877 (n=40) | 215 (n=35) | 214 (n=29) | 784 (n=38) | 191 (n=38) | 3034 (n=38) | 4383 (n=38) |
| 2026-07 | 217 (n=37) | 223 (n=32) | 121 (n=28) | 228 (n=33) | 191 (n=33) | 1081 (n=33) | 1894 (n=33) |
| 2026-08 | 298 (n=28) | 306 (n=24) | 142 (n=21) | 223 (n=25) | 143 (n=25) | 1061 (n=25) | 1840 (n=25) |
| 2026-09 | -82 (n=29) | -66 (n=26) | -36 (n=22) | -113 (n=26) | -21 (n=26) | -566 (n=26) | -1132 (n=26) |
| 2026-10 | -73 (n=7) | -73 (n=7) | -73 (n=7) | -73 (n=7) | -25 (n=7) | -367 (n=7) | -734 (n=7) |

## Q2 Fills and depth (weekly primary, realistic entries)

| stake | vs median | trades exceeding | of trades | share |
|---|---|---|---|---|
| $10 | touch | 209 | 346 | 60% |
| $10 | 2c depth | 0 | 346 | 0% |
| $50 | touch | 346 | 346 | 100% |
| $50 | 2c depth | 230 | 346 | 66% |
| $100 | touch | 346 | 346 | 100% |
| $100 | 2c depth | 230 | 346 | 66% |

Trades by band of mid (real10):
| band | n | ROI | PnL $ | touch $ | 2c depth $ |
|---|---|---|---|---|---|
| <=2c | 102 | +41% | 415 | 2 | 28 |
| 2-5c | 107 | +74% | 796 | 3 | 41 |
| 5-15c | 116 | +72% | 839 | 22 | 155 |
| 15-50c | 21 | +30% | 63 | 22 | 45 |

## Q3 Narrowness stability
Market distribution = bucket prices (missing price = 0) normalised to sum 1, event x lead rows with raw price sum in [0.9, 1.15]; bucket mids (lo+hi)/2, open top = lo + bucket width; SD uses mids only (no within-bucket variance). z = (final_count - mean)/SD, clipped to +/-5 in the SD(z) and mean-z columns (raw SD in JSON; the model SD collapses to ~0 at late leads in 48h, giving absurd raw z). PIT = CDF below realised bucket + half its mass. Outer-20% share = PIT<0.1 or >0.9 (calibrated: 20%); SD(z)>1 or outer>20% = too narrow. 'Model' uses p_model on the same rows. Leads 0..95 only (lead -10 excluded).

Coverage: 48h: 2433/2520 event-lead rows usable; weekly: 1796/1848 event-lead rows usable.

### weekly: pooled

| group | n | mkt SD(z) | mkt mean z | mkt outer20 | mkt PIT<.1/>.9 | mkt final>mean | mod SD(z) | mod mean z | mod outer20 | mod PIT<.1/>.9 | mod final>mean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| primary leads 0/25/50/75 | 307 | 1.03 | 0.01 | 25% | 11%/14% | 43% | 1.04 | 0.09 | 14% | 6%/8% | 47% |
| all leads 0..95 | 1710 | 0.98 | -0.03 | 21% | 10%/11% | 44% | 1.05 | 0.09 | 14% | 5%/9% | 47% |

### weekly: per lead
| group | n | mkt SD(z) | mkt mean z | mkt outer20 | mkt PIT<.1/>.9 | mkt final>mean | mod SD(z) | mod mean z | mod outer20 | mod PIT<.1/>.9 | mod final>mean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 43 | 1.25 | 0.13 | 35% | 16%/19% | 44% | 1.01 | 0.13 | 5% | 0%/5% | 44% |
| 5 | 87 | 1.07 | -0.00 | 25% | 10%/15% | 46% | 0.96 | 0.04 | 11% | 3%/8% | 41% |
| 10 | 87 | 1.06 | 0.01 | 24% | 10%/14% | 45% | 0.97 | 0.05 | 11% | 3%/8% | 46% |
| 15 | 87 | 1.04 | -0.04 | 25% | 14%/11% | 46% | 0.96 | 0.04 | 16% | 7%/9% | 47% |
| 20 | 88 | 1.02 | 0.01 | 20% | 9%/11% | 51% | 0.96 | 0.06 | 14% | 6%/8% | 50% |
| 25 | 88 | 1.02 | -0.01 | 23% | 11%/11% | 47% | 0.98 | 0.07 | 14% | 6%/8% | 53% |
| 30 | 88 | 0.97 | -0.02 | 19% | 9%/10% | 45% | 0.97 | 0.08 | 15% | 7%/8% | 50% |
| 35 | 87 | 1.01 | -0.06 | 18% | 11%/7% | 46% | 0.97 | 0.06 | 11% | 5%/7% | 48% |
| 40 | 88 | 1.03 | -0.02 | 23% | 12%/10% | 48% | 1.01 | 0.09 | 11% | 3%/8% | 49% |
| 45 | 88 | 1.00 | -0.07 | 23% | 12%/10% | 41% | 1.03 | 0.07 | 14% | 6%/8% | 48% |
| 50 | 88 | 1.06 | -0.07 | 25% | 11%/14% | 41% | 1.07 | 0.08 | 14% | 7%/7% | 44% |
| 55 | 88 | 1.06 | -0.06 | 27% | 12%/15% | 44% | 1.08 | 0.10 | 17% | 8%/9% | 45% |
| 60 | 88 | 1.07 | -0.04 | 25% | 12%/12% | 41% | 1.10 | 0.10 | 18% | 7%/11% | 49% |
| 65 | 88 | 1.09 | 0.05 | 26% | 9%/17% | 44% | 1.11 | 0.10 | 20% | 8%/12% | 47% |
| 70 | 88 | 1.05 | -0.01 | 23% | 10%/12% | 42% | 1.14 | 0.11 | 19% | 7%/12% | 48% |
| 75 | 88 | 0.89 | 0.04 | 24% | 9%/15% | 42% | 1.10 | 0.11 | 19% | 9%/10% | 44% |
| 80 | 88 | 0.87 | -0.00 | 18% | 7%/11% | 40% | 1.09 | 0.13 | 11% | 3%/8% | 45% |
| 85 | 87 | 0.66 | -0.09 | 14% | 6%/8% | 44% | 1.06 | 0.13 | 17% | 6%/11% | 46% |
| 90 | 88 | 0.59 | -0.14 | 7% | 2%/5% | 39% | 1.01 | 0.08 | 8% | 2%/6% | 43% |
| 95 | 88 | 0.51 | -0.06 | 7% | 2%/5% | 39% | 1.36 | 0.15 | 11% | 3%/8% | 44% |

### weekly: per month (primary leads)
| group | n | mkt SD(z) | mkt mean z | mkt outer20 | mkt PIT<.1/>.9 | mkt final>mean | mod SD(z) | mod mean z | mod outer20 | mod PIT<.1/>.9 | mod final>mean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2025-12 | 36 | 1.27 | 0.73 | 36% | 3%/33% | 72% | 1.40 | 0.99 | 31% | 0%/31% | 81% |
| 2026-01 | 36 | 0.95 | -0.15 | 25% | 17%/8% | 36% | 0.93 | 0.01 | 8% | 6%/3% | 42% |
| 2026-02 | 32 | 1.05 | -0.25 | 31% | 22%/9% | 38% | 0.74 | -0.42 | 19% | 16%/3% | 19% |
| 2026-03 | 36 | 0.91 | 0.05 | 22% | 8%/14% | 44% | 0.62 | 0.05 | 0% | 0%/0% | 50% |
| 2026-04 | 30 | 0.69 | -0.54 | 20% | 20%/0% | 17% | 0.51 | -0.55 | 7% | 7%/0% | 17% |
| 2026-05 | 28 | 1.02 | 0.04 | 36% | 18%/18% | 46% | 1.20 | 0.23 | 25% | 11%/14% | 50% |
| 2026-06 | 27 | 0.83 | -0.02 | 19% | 11%/7% | 48% | 0.69 | -0.03 | 11% | 11%/0% | 56% |
| 2026-07 | 28 | 0.76 | -0.09 | 18% | 4%/14% | 32% | 0.75 | -0.01 | 7% | 4%/4% | 43% |
| 2026-08 | 24 | 0.98 | -0.07 | 21% | 8%/12% | 46% | 0.87 | 0.14 | 17% | 8%/8% | 54% |
| 2026-09 | 27 | 0.54 | -0.10 | 15% | 4%/11% | 44% | 0.62 | 0.04 | 7% | 4%/4% | 52% |

### weekly: chronological halves (primary leads)
| group | n | mkt SD(z) | mkt mean z | mkt outer20 | mkt PIT<.1/>.9 | mkt final>mean | mod SD(z) | mod mean z | mod outer20 | mod PIT<.1/>.9 | mod final>mean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| first half | 173 | 1.08 | -0.02 | 27% | 13%/13% | 42% | 1.06 | 0.03 | 13% | 5%/8% | 42% |
| second half | 134 | 0.97 | 0.04 | 24% | 9%/15% | 46% | 1.02 | 0.18 | 16% | 7%/8% | 53% |

### 48h: pooled

| group | n | mkt SD(z) | mkt mean z | mkt outer20 | mkt PIT<.1/>.9 | mkt final>mean | mod SD(z) | mod mean z | mod outer20 | mod PIT<.1/>.9 | mod final>mean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| primary leads 0/25/50/75 | 415 | 0.86 | -0.02 | 13% | 7%/7% | 44% | 1.07 | 0.11 | 11% | 5%/7% | 46% |
| all leads 0..95 | 2315 | 0.84 | 0.01 | 12% | 5%/6% | 44% | 1.18 | 0.10 | 11% | 4%/7% | 47% |

### 48h: per lead
| group | n | mkt SD(z) | mkt mean z | mkt outer20 | mkt PIT<.1/>.9 | mkt final>mean | mod SD(z) | mod mean z | mod outer20 | mod PIT<.1/>.9 | mod final>mean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 59 | 0.90 | -0.12 | 24% | 19%/5% | 44% | 1.02 | 0.13 | 12% | 5%/7% | 51% |
| 5 | 119 | 0.83 | -0.01 | 15% | 8%/7% | 47% | 0.89 | 0.03 | 13% | 7%/7% | 45% |
| 10 | 119 | 0.85 | -0.02 | 15% | 8%/7% | 45% | 0.90 | 0.03 | 14% | 7%/8% | 44% |
| 15 | 118 | 0.85 | -0.01 | 14% | 8%/6% | 44% | 0.91 | 0.02 | 14% | 7%/8% | 46% |
| 20 | 119 | 0.88 | -0.00 | 14% | 8%/7% | 42% | 0.94 | 0.05 | 15% | 8%/8% | 45% |
| 25 | 118 | 0.90 | 0.01 | 15% | 8%/8% | 46% | 0.94 | 0.05 | 12% | 5%/7% | 47% |
| 30 | 119 | 0.92 | 0.07 | 12% | 4%/8% | 49% | 0.99 | 0.09 | 13% | 5%/8% | 50% |
| 35 | 119 | 0.95 | 0.13 | 13% | 6%/8% | 50% | 0.94 | 0.10 | 13% | 6%/8% | 52% |
| 40 | 119 | 0.89 | 0.08 | 13% | 6%/8% | 47% | 0.93 | 0.09 | 12% | 6%/6% | 52% |
| 45 | 118 | 0.87 | 0.02 | 12% | 6%/6% | 41% | 0.95 | 0.07 | 11% | 6%/5% | 48% |
| 50 | 119 | 0.84 | 0.01 | 11% | 6%/5% | 45% | 1.07 | 0.13 | 13% | 7%/7% | 45% |
| 55 | 119 | 0.80 | 0.01 | 11% | 6%/5% | 48% | 1.09 | 0.15 | 13% | 7%/6% | 43% |
| 60 | 119 | 0.82 | 0.01 | 12% | 3%/8% | 39% | 1.16 | 0.17 | 13% | 4%/9% | 44% |
| 65 | 118 | 0.81 | -0.01 | 8% | 3%/5% | 39% | 1.21 | 0.18 | 10% | 1%/9% | 45% |
| 70 | 119 | 0.80 | -0.00 | 10% | 3%/8% | 36% | 1.20 | 0.17 | 9% | 2%/8% | 45% |
| 75 | 119 | 0.82 | -0.02 | 9% | 2%/8% | 40% | 1.22 | 0.15 | 8% | 2%/7% | 44% |
| 80 | 119 | 0.78 | -0.00 | 7% | 3%/4% | 37% | 1.18 | 0.12 | 8% | 1%/8% | 42% |
| 85 | 119 | 0.85 | 0.07 | 9% | 2%/8% | 42% | 1.54 | 0.12 | 9% | 1%/8% | 50% |
| 90 | 119 | 0.73 | -0.02 | 9% | 2%/8% | 41% | 1.67 | 0.19 | 8% | 1%/7% | 53% |
| 95 | 118 | 0.70 | -0.06 | 5% | 3%/3% | 51% | 2.00 | 0.01 | 6% | 0%/6% | 54% |

### 48h: per month (primary leads)
| group | n | mkt SD(z) | mkt mean z | mkt outer20 | mkt PIT<.1/>.9 | mkt final>mean | mod SD(z) | mod mean z | mod outer20 | mod PIT<.1/>.9 | mod final>mean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-01 | 55 | 1.00 | -0.11 | 18% | 16%/2% | 45% | 1.65 | 0.45 | 9% | 0%/9% | 51% |
| 2026-02 | 48 | 0.99 | -0.13 | 25% | 12%/12% | 40% | 0.88 | -0.30 | 15% | 8%/6% | 27% |
| 2026-03 | 52 | 0.85 | 0.04 | 13% | 6%/8% | 58% | 0.84 | 0.22 | 13% | 6%/8% | 62% |
| 2026-04 | 47 | 0.94 | -0.09 | 11% | 2%/9% | 30% | 0.92 | -0.23 | 11% | 4%/6% | 23% |
| 2026-05 | 35 | 0.61 | -0.09 | 11% | 9%/3% | 26% | 0.87 | -0.09 | 17% | 11%/6% | 37% |
| 2026-06 | 42 | 0.84 | 0.00 | 12% | 5%/7% | 48% | 0.87 | 0.20 | 14% | 5%/10% | 60% |
| 2026-07 | 41 | 0.83 | 0.23 | 15% | 5%/10% | 56% | 0.87 | 0.26 | 10% | 5%/5% | 54% |
| 2026-08 | 47 | 0.86 | -0.03 | 11% | 4%/6% | 36% | 0.82 | -0.00 | 13% | 4%/9% | 47% |
| 2026-09 | 38 | 0.52 | -0.03 | 3% | 3%/0% | 45% | 1.03 | 0.30 | 0% | 0%/0% | 53% |
| 2026-10 | 10 | 0.83 | 0.37 | 10% | 0%/10% | 70% | 1.54 | 0.85 | 10% | 0%/10% | 60% |

### 48h: chronological halves (primary leads)
| group | n | mkt SD(z) | mkt mean z | mkt outer20 | mkt PIT<.1/>.9 | mkt final>mean | mod SD(z) | mod mean z | mod outer20 | mod PIT<.1/>.9 | mod final>mean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| first half | 224 | 0.93 | -0.06 | 17% | 9%/7% | 42% | 1.17 | 0.04 | 13% | 6%/8% | 41% |
| second half | 191 | 0.78 | 0.04 | 10% | 4%/6% | 45% | 0.94 | 0.20 | 9% | 3%/6% | 53% |

### Calibration by predicted-probability band (primary leads, rows with a price)
| family | source | band | mean pred | realised freq | n |
|---|---|---|---|---|---|
| weekly | market | <2c | 0.0034 | 0.0050 | 4972 |
| weekly | market | 2-5c | 0.0327 | 0.0421 | 784 |
| weekly | market | 5-15c | 0.0932 | 0.0849 | 1566 |
| weekly | market | 15-50c | 0.2736 | 0.1545 | 1010 |
| weekly | market | >50c | 0.5121 | 0.0400 | 75 |
| weekly | model | <2c | 0.0036 | 0.0037 | 4622 |
| weekly | model | 2-5c | 0.0342 | 0.0287 | 1326 |
| weekly | model | 5-15c | 0.0896 | 0.0940 | 1925 |
| weekly | model | 15-50c | 0.2161 | 0.2139 | 533 |
| weekly | model | >50c | 0.5520 | 0.0000 | 1 |
| 48h | market | <2c | 0.0031 | 0.0024 | 2526 |
| 48h | market | 2-5c | 0.0334 | 0.0241 | 373 |
| 48h | market | 5-15c | 0.0920 | 0.1012 | 504 |
| 48h | market | 15-50c | 0.3048 | 0.2505 | 918 |
| 48h | market | >50c | 0.6412 | 0.5894 | 302 |
| 48h | model | <2c | 0.0023 | 0.0028 | 2505 |
| 48h | model | 2-5c | 0.0334 | 0.0146 | 342 |
| 48h | model | 5-15c | 0.0963 | 0.0874 | 641 |
| 48h | model | 15-50c | 0.2922 | 0.3098 | 965 |
| 48h | model | >50c | 0.6651 | 0.6294 | 170 |

## Q4 Breakdowns (weekly, as-known)

### tail side vs market mean (slip0, primary leads)
| group | n | events | PnL $ | ROI | p event-clust |
|---|---|---|---|---|---|
| lower | 230 | 58 | 525 | +23% | 0.238 |
| straddles mean | 1 | 1 | 23 | +226% |  |
| unknown | 17 | 13 | 22 | +13% | 0.402 |
| upper | 136 | 50 | 2055 | +151% | 0.022 |

### entry price band (slip0, primary leads)
| group | n | events | PnL $ | ROI | p event-clust |
|---|---|---|---|---|---|
| <2c | 108 | 54 | 444 | +41% | 0.415 |
| 2-5c | 109 | 61 | 982 | +90% | 0.099 |
| 5-15c | 129 | 69 | 1044 | +81% | 0.029 |
| 15-50c | 38 | 31 | 155 | +41% | 0.163 |

### lead (slip0, primary leads)
| group | n | events | PnL $ | ROI | p event-clust |
|---|---|---|---|---|---|
| 0 | 43 | 34 | 67 | +15% | 0.434 |
| 25 | 75 | 35 | 476 | +63% | 0.207 |
| 50 | 119 | 54 | 1852 | +156% | 0.030 |
| 75 | 147 | 74 | 230 | +16% | 0.339 |

### window start weekday (slip0, primary leads)
| group | n | events | PnL $ | ROI | p event-clust |
|---|---|---|---|---|---|
| Fri | 181 | 43 | 1073 | +59% | 0.105 |
| Tue | 203 | 43 | 1551 | +76% | 0.047 |

### tail side vs market mean (slip1c, primary leads)
| group | n | events | PnL $ | ROI | p event-clust |
|---|---|---|---|---|---|
| lower | 178 | 50 | 260 | +15% | 0.310 |
| straddles mean | 1 | 1 | 22 | +216% |  |
| unknown | 6 | 6 | -63 | -105% | 1.000 |
| upper | 97 | 45 | 223 | +23% | 0.283 |

### entry price band (slip1c, primary leads)
| group | n | events | PnL $ | ROI | p event-clust |
|---|---|---|---|---|---|
| <2c | 31 | 20 | -325 | -105% | 1.000 |
| 2-5c | 87 | 47 | -88 | -10% | 0.597 |
| 5-15c | 128 | 68 | 707 | +55% | 0.073 |
| 15-50c | 36 | 27 | 148 | +41% | 0.149 |

### lead (slip1c, primary leads)
| group | n | events | PnL $ | ROI | p event-clust |
|---|---|---|---|---|---|
| 0 | 21 | 20 | -220 | -105% | 1.000 |
| 25 | 46 | 24 | 200 | +43% | 0.336 |
| 50 | 98 | 47 | 159 | +16% | 0.323 |
| 75 | 117 | 64 | 303 | +26% | 0.231 |

### window start weekday (slip1c, primary leads)
| group | n | events | PnL $ | ROI | p event-clust |
|---|---|---|---|---|---|
| Fri | 123 | 39 | 397 | +32% | 0.218 |
| Tue | 159 | 38 | 45 | +3% | 0.471 |

### tail side vs market mean (real10, primary leads)
| group | n | events | PnL $ | ROI | p event-clust |
|---|---|---|---|---|---|
| lower | 207 | 55 | 408 | +20% | 0.290 |
| straddles mean | 1 | 1 | 20 | +197% |  |
| unknown | 16 | 13 | 27 | +17% | 0.396 |
| upper | 122 | 47 | 1659 | +136% | 0.050 |

### entry price band (real10, primary leads)
| group | n | events | PnL $ | ROI | p event-clust |
|---|---|---|---|---|---|
| <2c | 99 | 49 | 447 | +45% | 0.382 |
| 2-5c | 103 | 58 | 643 | +62% | 0.171 |
| 5-15c | 121 | 68 | 980 | +81% | 0.029 |
| 15-50c | 23 | 20 | 43 | +19% | 0.375 |

### lead (real10, primary leads)
| group | n | events | PnL $ | ROI | p event-clust |
|---|---|---|---|---|---|
| 0 | 36 | 31 | -183 | -51% | 0.782 |
| 25 | 71 | 33 | 451 | +64% | 0.215 |
| 50 | 106 | 51 | 1639 | +155% | 0.046 |
| 75 | 133 | 67 | 206 | +16% | 0.341 |

### window start weekday (real10, primary leads)
| group | n | events | PnL $ | ROI | p event-clust |
|---|---|---|---|---|---|
| Fri | 161 | 42 | 1073 | +67% | 0.094 |
| Tue | 185 | 40 | 1040 | +56% | 0.137 |

### Full lead grid 0..95 (slip0, weekly as-known)
| group | n | events | PnL $ | ROI | p event-clust |
|---|---|---|---|---|---|
| 0 | 43 | 34 | 67 | +15% | 0.459 |
| 5 | 46 | 31 | 158 | +34% | 0.337 |
| 10 | 48 | 29 | -52 | -11% | 0.627 |
| 15 | 55 | 27 | 350 | +64% | 0.227 |
| 20 | 66 | 31 | 210 | +32% | 0.320 |
| 25 | 75 | 35 | 476 | +63% | 0.216 |
| 30 | 75 | 39 | 443 | +59% | 0.238 |
| 35 | 84 | 37 | 810 | +96% | 0.093 |
| 40 | 112 | 50 | 754 | +67% | 0.175 |
| 45 | 106 | 48 | 428 | +40% | 0.286 |
| 50 | 119 | 54 | 1852 | +156% | 0.030 |
| 55 | 141 | 61 | 3538 | +251% | 0.029 |
| 60 | 143 | 65 | -202 | -14% | 0.689 |
| 65 | 158 | 68 | 326 | +21% | 0.294 |
| 70 | 141 | 71 | -222 | -16% | 0.756 |
| 75 | 147 | 74 | 230 | +16% | 0.333 |
| 80 | 138 | 78 | 559 | +41% | 0.217 |
| 85 | 124 | 75 | -56 | -5% | 0.579 |
| 90 | 100 | 72 | -424 | -42% | 0.996 |
| 95 | 76 | 60 | -437 | -58% | 0.999 |

### Tail side, all leads 0..95 (slip0)
| group | n | events | PnL $ | ROI | p event-clust |
|---|---|---|---|---|---|
| lower | 1280 | 77 | 1715 | +13% | 0.318 |
| straddles mean | 12 | 7 | 42 | +35% | 0.093 |
| unknown | 23 | 15 | -41 | -18% | 0.668 |
| upper | 682 | 67 | 7088 | +104% | 0.045 |

### Full lead grid 0..95 (slip1c, weekly as-known)
| group | n | events | PnL $ | ROI | p event-clust |
|---|---|---|---|---|---|
| 0 | 21 | 20 | -220 | -105% | 1.000 |
| 5 | 23 | 19 | -241 | -105% | 1.000 |
| 10 | 27 | 21 | 76 | +28% | 0.457 |
| 15 | 36 | 19 | -118 | -33% | 0.776 |
| 20 | 37 | 19 | -276 | -75% | 0.984 |
| 25 | 46 | 24 | 200 | +43% | 0.332 |
| 30 | 43 | 22 | -274 | -64% | 0.982 |
| 35 | 53 | 29 | 106 | +20% | 0.407 |
| 40 | 69 | 34 | -195 | -28% | 0.796 |
| 45 | 71 | 35 | -105 | -15% | 0.681 |
| 50 | 98 | 47 | 159 | +16% | 0.339 |
| 55 | 116 | 57 | 161 | +14% | 0.370 |
| 60 | 105 | 53 | -325 | -31% | 0.870 |
| 65 | 134 | 63 | 156 | +12% | 0.383 |
| 70 | 119 | 64 | -196 | -17% | 0.755 |
| 75 | 117 | 64 | 303 | +26% | 0.243 |
| 80 | 117 | 71 | 117 | +10% | 0.425 |
| 85 | 101 | 70 | -66 | -6% | 0.598 |
| 90 | 86 | 68 | -358 | -42% | 0.996 |
| 95 | 66 | 54 | -348 | -53% | 0.998 |

### Tail side, all leads 0..95 (slip1c)
| group | n | events | PnL $ | ROI | p event-clust |
|---|---|---|---|---|---|
| lower | 994 | 74 | -1112 | -11% | 0.724 |
| straddles mean | 9 | 5 | 42 | +47% | 0.055 |
| unknown | 11 | 8 | -115 | -105% | 1.000 |
| upper | 471 | 62 | -260 | -6% | 0.600 |

### Full lead grid 0..95 (real10, weekly as-known)
| group | n | events | PnL $ | ROI | p event-clust |
|---|---|---|---|---|---|
| 0 | 36 | 31 | -183 | -51% | 0.785 |
| 5 | 39 | 28 | -97 | -25% | 0.687 |
| 10 | 40 | 27 | 9 | +2% | 0.553 |
| 15 | 52 | 27 | 331 | +64% | 0.213 |
| 20 | 58 | 26 | 1 | +0% | 0.544 |
| 25 | 71 | 33 | 451 | +64% | 0.235 |
| 30 | 67 | 35 | 147 | +22% | 0.412 |
| 35 | 74 | 35 | 670 | +91% | 0.125 |
| 40 | 103 | 49 | 663 | +64% | 0.193 |
| 45 | 94 | 46 | -179 | -19% | 0.744 |
| 50 | 106 | 51 | 1639 | +155% | 0.040 |
| 55 | 122 | 58 | 3077 | +252% | 0.032 |
| 60 | 126 | 59 | -267 | -21% | 0.770 |
| 65 | 149 | 67 | 159 | +11% | 0.412 |
| 70 | 129 | 66 | -240 | -19% | 0.780 |
| 75 | 133 | 67 | 206 | +16% | 0.357 |
| 80 | 128 | 73 | 493 | +39% | 0.233 |
| 85 | 101 | 66 | -165 | -16% | 0.701 |
| 90 | 83 | 67 | -489 | -59% | 1.000 |
| 95 | 66 | 51 | -487 | -74% | 1.000 |

### Tail side, all leads 0..95 (real10)
| group | n | events | PnL $ | ROI | p event-clust |
|---|---|---|---|---|---|
| lower | 1149 | 76 | 1000 | +9% | 0.390 |
| straddles mean | 4 | 2 | 19 | +47% | 0.000 |
| unknown | 22 | 15 | -36 | -17% | 0.686 |
| upper | 602 | 65 | 4756 | +79% | 0.090 |

### 48h tail side (slip0, primary leads)
| group | n | events | PnL $ | ROI | p event-clust |
|---|---|---|---|---|---|
| lower | 252 | 82 | 366 | +15% | 0.348 |
| straddles mean | 6 | 6 | 78 | +130% | 0.191 |
| unknown | 71 | 45 | 181 | +26% | 0.230 |
| upper | 257 | 68 | 4277 | +166% | 0.143 |

### 48h window start weekday (slip0)
| group | n | events | PnL $ | ROI | p event-clust |
|---|---|---|---|---|---|
| Mon | 197 | 39 | 4195 | +213% | 0.105 |
| Sat | 187 | 40 | 1599 | +86% | 0.083 |
| Thu | 202 | 40 | -892 | -44% | 0.923 |

### 48h tail side (slip1c, primary leads)
| group | n | events | PnL $ | ROI | p event-clust |
|---|---|---|---|---|---|
| lower | 231 | 79 | 42 | +2% | 0.481 |
| straddles mean | 5 | 5 | 79 | +159% | 0.179 |
| unknown | 66 | 43 | 167 | +25% | 0.223 |
| upper | 218 | 64 | 755 | +35% | 0.275 |

### 48h window start weekday (slip1c)
| group | n | events | PnL $ | ROI | p event-clust |
|---|---|---|---|---|---|
| Mon | 165 | 39 | 1064 | +64% | 0.108 |
| Sat | 177 | 40 | 770 | +44% | 0.168 |
| Thu | 178 | 39 | -791 | -44% | 0.921 |

## Q5 As-known versus lookahead

| family | slip | n as-known | PnL as | ROI as | p as | n look | PnL look | ROI look | p look | PnL diff (look - as) |
|---|---|---|---|---|---|---|---|---|---|---|
| weekly | 0.0 | 384 | 2624 | +68% | 0.018 | 385 | 2614 | +68% | 0.018 | -10 |
| weekly | 0.005 | 327 | 1350 | +41% | 0.077 | 329 | 1330 | +40% | 0.080 | -21 |
| weekly | 0.01 | 282 | 442 | +16% | 0.251 | 281 | 452 | +16% | 0.235 | +11 |
| 48h | 0.0 | 586 | 4903 | +84% | 0.090 | 587 | 4892 | +83% | 0.092 | -11 |
| 48h | 0.005 | 556 | 2424 | +44% | 0.123 | 557 | 2414 | +43% | 0.124 | -11 |
| 48h | 0.01 | 520 | 1043 | +20% | 0.222 | 518 | 1064 | +21% | 0.217 | +21 |

### Per month (primary leads): mean K_final - K_asknown per event x lead, and PnL as-known vs lookahead
| family | month | events | mean dK | share dK>0 | max dK | PnL as slip0 | PnL look slip0 | PnL as slip1c | PnL look slip1c |
|---|---|---|---|---|---|---|---|---|---|
| weekly | 2025-12 | 9 | 0.14 | 8% | 3 | -323 | -323 | -388 | -388 |
| weekly | 2026-01 | 9 | 0.06 | 6% | 1 | 145 | 135 | 129 | 129 |
| weekly | 2026-02 | 8 | 0.22 | 6% | 4 | 789 | 779 | -59 | -59 |
| weekly | 2026-03 | 9 | 0.28 | 14% | 4 | 331 | 331 | 269 | 280 |
| weekly | 2026-04 | 8 | 0.25 | 6% | 5 | 42 | 31 | 6 | -4 |
| weekly | 2026-05 | 9 | 0.06 | 6% | 1 | 402 | 402 | 116 | 116 |
| weekly | 2026-06 | 9 | 0.08 | 6% | 2 | 877 | 877 | 214 | 214 |
| weekly | 2026-07 | 9 | 0.06 | 3% | 2 | 217 | 217 | 121 | 121 |
| weekly | 2026-08 | 8 | 0.31 | 6% | 7 | 298 | 287 | 142 | 132 |
| weekly | 2026-09 | 9 | 0.08 | 6% | 2 | -82 | -72 | -36 | -36 |
| weekly | 2026-10 | 1 | 16.00 | 50% | 63 | -73 | -52 | -73 | -52 |
| 48h | 2026-01 | 14 | 0.12 | 11% | 2 | -111 | -111 | -253 | -253 |
| 48h | 2026-02 | 12 | 0.00 | 0% | 0 | 935 | 935 | 489 | 489 |
| 48h | 2026-03 | 13 | 0.12 | 8% | 3 | -12 | -12 | 6 | 6 |
| 48h | 2026-04 | 13 | 0.02 | 2% | 1 | -515 | -515 | -433 | -433 |
| 48h | 2026-05 | 12 | 0.10 | 8% | 2 | -42 | -42 | -98 | -98 |
| 48h | 2026-06 | 13 | 0.04 | 4% | 1 | 870 | 870 | 683 | 683 |
| 48h | 2026-07 | 13 | 0.06 | 4% | 2 | 762 | 752 | 574 | 574 |
| 48h | 2026-08 | 15 | 0.42 | 3% | 21 | 3430 | 3419 | 415 | 415 |
| 48h | 2026-09 | 12 | 0.62 | 10% | 22 | -331 | -321 | -268 | -247 |
| 48h | 2026-10 | 3 | 1.50 | 17% | 15 | -83 | -83 | -73 | -73 |

## Q6 Independence (weekly primary)

### slip0: trades 384, events with trades 86, non-overlapping windows (greedy) among traded events 43, among all 88 weekly events 44; p 14d-block 0.017
| independent subset | windows | trades | events traded | PnL $ | ROI | p (event boot) |
|---|---|---|---|---|---|---|
| greedy-all offset0 | 44 | 203 | 43 | 1551 | +76% | 0.051 |
| greedy-all offset1 | 44 | 181 | 43 | 1073 | +59% | 0.103 |
| greedy-all offset2 | 43 | 196 | 42 | 1624 | +83% | 0.039 |
| greedy-all offset3 | 43 | 169 | 42 | 1156 | +68% | 0.087 |
| greedy-all offset4 | 42 | 188 | 41 | 1455 | +77% | 0.062 |
| greedy-all offset5 | 42 | 164 | 41 | 1209 | +74% | 0.073 |
| greedy-all offset6 | 41 | 184 | 40 | 1497 | +81% | 0.055 |
| alt set A (greedy) | 44 | 203 | 43 | 1551 | +76% | 0.050 |
| alt set B (greedy on remainder) | 44 | 181 | 43 | 1073 | +59% | 0.108 |
| greedy on traded events only | 43 | 203 | 43 | 1551 | +76% | 0.052 |

### slip0.5c: trades 327, events with trades 82, non-overlapping windows (greedy) among traded events 42, among all 88 weekly events 44; p 14d-block 0.088
| independent subset | windows | trades | events traded | PnL $ | ROI | p (event boot) |
|---|---|---|---|---|---|---|
| greedy-all offset0 | 44 | 181 | 40 | 750 | +41% | 0.166 |
| greedy-all offset1 | 44 | 146 | 42 | 600 | +41% | 0.169 |
| greedy-all offset2 | 43 | 174 | 39 | 823 | +47% | 0.132 |
| greedy-all offset3 | 43 | 137 | 41 | 653 | +48% | 0.137 |
| greedy-all offset4 | 42 | 167 | 38 | 864 | +52% | 0.113 |
| greedy-all offset5 | 42 | 134 | 40 | 684 | +51% | 0.128 |
| greedy-all offset6 | 41 | 163 | 37 | 906 | +56% | 0.100 |
| alt set A (greedy) | 44 | 181 | 40 | 750 | +41% | 0.164 |
| alt set B (greedy on remainder) | 44 | 146 | 42 | 600 | +41% | 0.166 |
| greedy on traded events only | 42 | 151 | 42 | 826 | +55% | 0.144 |

### slip1c: trades 282, events with trades 77, non-overlapping windows (greedy) among traded events 40, among all 88 weekly events 44; p 14d-block 0.279
| independent subset | windows | trades | events traded | PnL $ | ROI | p (event boot) |
|---|---|---|---|---|---|---|
| greedy-all offset0 | 44 | 159 | 38 | 45 | +3% | 0.475 |
| greedy-all offset1 | 44 | 123 | 39 | 397 | +32% | 0.206 |
| greedy-all offset2 | 43 | 154 | 37 | 97 | +6% | 0.424 |
| greedy-all offset3 | 43 | 114 | 38 | 451 | +40% | 0.168 |
| greedy-all offset4 | 42 | 147 | 36 | 138 | +9% | 0.378 |
| greedy-all offset5 | 42 | 112 | 37 | 471 | +42% | 0.157 |
| greedy-all offset6 | 41 | 143 | 35 | 180 | +13% | 0.338 |
| alt set A (greedy) | 44 | 159 | 38 | 45 | +3% | 0.470 |
| alt set B (greedy on remainder) | 44 | 123 | 39 | 397 | +32% | 0.205 |
| greedy on traded events only | 40 | 132 | 40 | 171 | +13% | 0.318 |

### real10: trades 346, events with trades 82, non-overlapping windows (greedy) among traded events 42, among all 88 weekly events 44; p 14d-block 0.040
| independent subset | windows | trades | events traded | PnL $ | ROI | p (event boot) |
|---|---|---|---|---|---|---|
| greedy-all offset0 | 44 | 185 | 40 | 1040 | +56% | 0.143 |
| greedy-all offset1 | 44 | 161 | 42 | 1073 | +67% | 0.096 |
| greedy-all offset2 | 43 | 179 | 39 | 1103 | +62% | 0.124 |
| greedy-all offset3 | 43 | 150 | 41 | 1151 | +77% | 0.073 |
| greedy-all offset4 | 42 | 171 | 38 | 944 | +55% | 0.177 |
| greedy-all offset5 | 42 | 147 | 40 | 1182 | +80% | 0.066 |
| greedy-all offset6 | 41 | 167 | 37 | 986 | +59% | 0.160 |
| alt set A (greedy) | 44 | 185 | 40 | 1040 | +56% | 0.152 |
| alt set B (greedy on remainder) | 44 | 161 | 42 | 1073 | +67% | 0.091 |
| greedy on traded events only | 42 | 162 | 42 | 1723 | +106% | 0.045 |
