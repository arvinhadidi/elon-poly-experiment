# Out-of-sample replication: Elon NB count model on related xtracker families

Model, rule and costs identical to backtest.py (as-known count with importedAt <= t, NB remaining posts with trailing-4-week hour-of-week mean, buy YES if p_model - entry >= 0.05 and entry <= 0.50, $10 flat, taker fee 0.05*e*(1-e)/share, slippage 0/0.5c/1c). Leads 0/25/50/75, pooled across leads in the ROI/p/SD(z)/Brier columns. Only k differs: fitted walk-forward on each family's own past events (default 15 until 4 prior events, pooled, then per-lead once 10 prior events). No other tuning. p boot = one-sided event-clustered bootstrap (H0 ROI <= 0, 10000 reps, clusters = events with >= 1 trade; leads of one event share a cluster).

Excluded: Elon series 12076 (elon-tweet-mention) is a 'will Elon post the word X' mention market (winning labels are words such as Texas/Tesla), not a post-count bucket market, so the count model does not apply.

Narrowness: z = (final tracker count - market mean)/market SD from price-normalised bucket mids (within-bucket uniform variance included; open-ended top bucket treated as 20 wide); outer-20% share = fraction of outcomes with market-CDF PIT < 0.10 or > 0.90 (calibrated market: SD(z)=1, share=0.20; SD(z)>1 / share>0.20 means the market is too narrow). Computed only on event x lead rows where every bucket has a matched price (+-600 s). Brier = mean over bucket rows on those same rows.

## Main table
| family | n events (scored) | tracker match | n trades (0c) | ROI 0c | ROI 0.5c | ROI 1c | p boot (0c / 0.5c / 1c) | SD(z) | outer-20% share | Brier model | Brier mkt-norm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| trump_truth | 50 | 50/68 = 74% | 350 | +123% | +50% | +33% | 0.065 / 0.156 / 0.211 | 1.12 | 0.30 | 0.0815 | 0.0776 |
| whitehouse | 57 | 57/57 = 100% | 510 | -39% | -50% | -53% | 0.936 / 0.994 / 0.999 | 0.86 | 0.32 | 0.0717 | 0.0747 |
| khamenei | 57 | 57/57 = 100% | 119 | +178% | +168% | +152% | 0.000 / 0.000 / 0.001 | 0.55 | 0.41 | 0.0285 | 0.0380 |
| zelenskyy | 55 | 55/56 = 98% | 382 | +143% | -13% | -56% | 0.360 / 0.658 / 0.967 | 0.73 | 0.06 | 0.1006 | 0.0737 |
| nyc_mayor | 56 | 56/56 = 100% | 231 | -49% | -63% | -70% | 0.867 / 0.952 / 0.988 | 0.45 | 0.05 | 0.0811 | 0.0392 |
| cz | 56 | 56/56 = 100% | 173 | +531% | +220% | +156% | 0.028 / 0.061 / 0.069 | 0.56 | 0.12 | 0.0574 | 0.0531 |
| tedcruz | 57 | 57/57 = 100% | 317 | -71% | -75% | -77% | 1.000 / 1.000 / 1.000 | 0.69 | 0.06 | 0.0849 | 0.0784 |
| POOLED | 388 | 388/407 = 95% | 2082 | +76% | +1% | -18% | 0.080 / 0.521 / 0.891 | 0.80 | 0.19 | 0.0633 | 0.0545 |


## Per family x lead
| family | lead % | events w/ full book | SD(z) | outer-20% share | Brier model | Brier mkt-norm | n trades (0c) | ROI 0c |
|---|---|---|---|---|---|---|---|---|
| trump_truth | 0 | 49 | 1.06 | 0.27 | 0.0806 | 0.0829 | 68 | +264% |
| trump_truth | 25 | 17 | 1.27 | 0.29 | 0.0797 | 0.0717 | 111 | +190% |
| trump_truth | 50 | 4 | 1.23 | 0.50 | 0.0936 | 0.0540 | 106 | +50% |
| trump_truth | 75 | 1 |  | 1.00 | 0.1079 | 0.0115 | 65 | -18% |
| whitehouse | 0 | 56 | 0.79 | 0.36 | 0.0690 | 0.0764 | 105 | -57% |
| whitehouse | 25 | 5 | 0.50 | 0.00 | 0.0984 | 0.0691 | 175 | -53% |
| whitehouse | 50 | 1 |  | 0.00 | 0.0709 | 0.0621 | 128 | +6% |
| whitehouse | 75 | 1 |  | 0.00 | 0.0954 | 0.0191 | 102 | -52% |
| khamenei | 0 | 56 | 0.46 | 0.54 | 0.0350 | 0.0620 | 45 | +61% |
| khamenei | 25 | 55 | 0.42 | 0.35 | 0.0329 | 0.0394 | 31 | +409% |
| khamenei | 50 | 48 | 0.49 | 0.38 | 0.0271 | 0.0297 | 28 | +210% |
| khamenei | 75 | 45 | 0.50 | 0.36 | 0.0165 | 0.0152 | 15 | -8% |
| zelenskyy | 0 | 54 | 0.48 | 0.02 | 0.1026 | 0.0789 | 72 | -105% |
| zelenskyy | 25 | 37 | 0.98 | 0.14 | 0.0985 | 0.0667 | 144 | +385% |
| zelenskyy | 50 | 2 | 0.69 | 0.00 | 0.0878 | 0.0751 | 107 | +33% |
| zelenskyy | 75 | 1 |  | 0.00 | 0.0924 | 0.0515 | 59 | +58% |
| nyc_mayor | 0 | 55 | 0.42 | 0.05 | 0.1017 | 0.0610 | 53 | -104% |
| nyc_mayor | 25 | 53 | 0.38 | 0.06 | 0.0855 | 0.0327 | 80 | -92% |
| nyc_mayor | 50 | 30 | 0.30 | 0.03 | 0.0425 | 0.0181 | 67 | +60% |
| nyc_mayor | 75 | 8 | 0.30 | 0.00 | 0.0556 | 0.0112 | 31 | -82% |
| cz | 0 | 55 | 0.56 | 0.20 | 0.0727 | 0.0717 | 47 | +132% |
| cz | 25 | 55 | 0.45 | 0.07 | 0.0640 | 0.0553 | 51 | +105% |
| cz | 50 | 53 | 0.41 | 0.08 | 0.0516 | 0.0440 | 43 | +1170% |
| cz | 75 | 39 | 0.37 | 0.13 | 0.0347 | 0.0359 | 32 | +937% |
| tedcruz | 0 | 56 | 0.69 | 0.05 | 0.0851 | 0.0807 | 68 | -91% |
| tedcruz | 25 | 14 | 0.64 | 0.07 | 0.0856 | 0.0717 | 101 | -101% |
| tedcruz | 50 | 1 |  | 0.00 | 0.0669 | 0.0741 | 77 | -54% |
| tedcruz | 75 | 1 |  | 0.00 | 0.0833 | 0.0451 | 71 | -25% |
| POOLED | 0 | 381 | 1.00 | 0.21 | 0.0768 | 0.0730 | 458 | +3% |
| POOLED | 25 | 236 | 0.68 | 0.16 | 0.0687 | 0.0503 | 693 | +98% |
| POOLED | 50 | 139 | 0.50 | 0.18 | 0.0423 | 0.0343 | 556 | +118% |
| POOLED | 75 | 96 | 0.50 | 0.23 | 0.0294 | 0.0233 | 375 | +60% |


## Tracker verification (tracker count in resolved bucket)
| family | events | match |
|---|---|---|
| trump_truth | 68 | 50 |
| whitehouse | 57 | 57 |
| khamenei | 57 | 57 |
| zelenskyy | 56 | 55 |
| nyc_mayor | 56 | 56 |
| cz | 56 | 56 |
| tedcruz | 57 | 57 |


Dropped (mismatched) events from scoring: trump_truth:donald-trump-of-truth-social-posts-march-20-march-27 (tracker 97 vs bucket 100-119), trump_truth:donald-trump-of-truth-social-posts-march-24-march-31 (tracker 99 vs bucket 100-119), trump_truth:donald-trump-of-truth-social-posts-april-10-april-17 (tracker 138 vs bucket 140-159), trump_truth:donald-trump-of-truth-social-posts-april-17-april-24 (tracker 198 vs bucket 200-1000000), trump_truth:donald-trump-of-truth-social-posts-may-1-may-8 (tracker 158 vs bucket 160-179), trump_truth:donald-trump-of-truth-social-posts-may-8-may-15 (tracker 176 vs bucket 180-199), trump_truth:donald-trump-of-truth-social-posts-may-12-may-19 (tracker 100 vs bucket 200-1000000), trump_truth:donald-trump-of-truth-social-posts-may-15-may-22 (tracker 68 vs bucket 200-1000000), trump_truth:donald-trump-of-truth-social-posts-may-19-may-26 (tracker 0 vs bucket 160-179), trump_truth:donald-trump-of-truth-social-posts-june-9-june-16 (tracker 119 vs bucket 120-139), trump_truth:donald-trump-of-truth-social-posts-june-12-june-19 (tracker 139 vs bucket 140-159), trump_truth:donald-trump-of-truth-social-posts-june-19-june-26 (tracker 156 vs bucket 160-179), trump_truth:donald-trump-of-truth-social-posts-june-26-july-3 (tracker 119 vs bucket 120-139), trump_truth:donald-trump-of-truth-social-posts-july-28-august-4 (tracker 147 vs bucket 160-179), trump_truth:donald-trump-of-truth-social-posts-august-7-august-14 (tracker 173 vs bucket 180-199), trump_truth:donald-trump-of-truth-social-posts-august-11-august-18 (tracker 141 vs bucket 200-1000000), trump_truth:donald-trump-of-truth-social-posts-august-14-august-21 (tracker 145 vs bucket 200-1000000), trump_truth:donald-trump-of-truth-social-posts-august-28-september-4-2026 (tracker 168 vs bucket 180-199), zelenskyy:zelenskyy-of-tweets-october-2-october-9-2026 (tracker 51 vs bucket 80-99)


Trades at 0 slip: 2082; share with entry < 2c: 0.38. Depth note: books on these markets are thin ($20-200 within 2c), so $10 per trade fills are optimistic and trade counts overstate capacity.
