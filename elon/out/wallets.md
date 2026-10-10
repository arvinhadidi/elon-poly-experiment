# Wallet profile: Elon tweet-count markets

Trade files used: 58 (files modified <2 min ago excluded); 2,220,317 resolved fills; 26,521 wallets; 58 events.

Interpretation: each row is one wallet's fill (proxyWallet = that participant, side = THAT wallet's side). Both sides of a match appear as separate rows under the same transactionHash (every hash has >=2 rows; e.g. BUY No@0.999 + BUY Yes@0.001 = a mint, or BUY+SELL of the same asset). So per-wallet PnL is correct, but summed notional/PnL across wallets double-counts volume (PnL sums to ~0 across counterparties, before fees/unresolved).

PnL = realised to resolution (hold-to-resolution mark; ignores exits' timing). Lead % = notional-weighted % of the window still remaining at trade time (negative = after window end; >100 = before window start).

## Classes

| class | wallets | notional share | notional $ | PnL $ | ROI |
|---|---|---|---|---|---|
| consistent loser | 273.0 | 2.1% | 1,321,965 | -85,023 | -6.43% |
| market-maker-like | 111.0 | 40.8% | 25,776,551 | 35,171 | 0.14% |
| one-off | 16780.0 | 3.0% | 1,924,809 | -41,801 | -2.17% |
| other | 8075.0 | 37.6% | 23,788,186 | -125,634 | -0.53% |
| sharp | 1282.0 | 16.5% | 10,414,037 | 217,287 | 2.09% |

4209 wallets have >=10 events; with a 5% test ~210 false-positive 'sharp' labels are expected by chance alone, so treat the sharp class as an upper bound.

Total notional (double-counted) $63,225,548; net PnL $-0.

## Concentration
Top 10 wallets = 27.3% of notional; top 50 = 54.4%; top 1 = 6.7%.

## Top 20 by notional

| pseudonym | addr | events | notional $ | PnL $ | ROI | p(PnL>0) | class | cheap share | avg lead % |
|---|---|---|---|---|---|---|---|---|---|
| Oddball-Deviance | 0x590e..e43d | 58 | 4,256,660 | 11,219 | 0.3% | 0.103 | market-maker-like | 46% | 51 |
| Courageous-Polish | 0xc4d5..87cf | 57 | 2,620,650 | 19,821 | 0.8% | 0.000 | market-maker-like | 29% | 39 |
| Private-Patrolling | 0x7789..a280 | 54 | 1,894,172 | 9,711 | 0.5% | 0.000 | sharp | 0% | 11 |
| Right-Simple | 0xfbcb..bb5d | 50 | 1,503,187 | 19,497 | 1.3% | 0.018 | market-maker-like | 22% | 24 |
| Husky-Labourer | 0x5409..79db | 23 | 1,413,245 | -2,981 | -0.2% | 0.668 | other | 1% | 59 |
| Serpentine-Maggot | 0x6964..ef53 | 56 | 1,288,486 | 4,378 | 0.3% | 0.018 | market-maker-like | 22% | 7 |
| Verifiable-Macaw | 0x1e1a..7690 | 24 | 1,124,094 | 7,966 | 0.7% | 0.000 | market-maker-like | 25% | 76 |
| Well-Worn-Foundation-Thread | 0x9d80..fcaf | 48 | 1,077,566 | -4,070 | -0.4% | 0.921 | market-maker-like | 0% | 54 |
| Writhing-Rib | 0x2eb6..3e31 | 35 | 1,056,035 | 433 | 0.0% | 0.512 | market-maker-like | 38% | 38 |
| Motionless-Everyone | 0x48c5..89f3 | 31 | 1,030,990 | -5,435 | -0.5% | 0.634 | market-maker-like | 11% | 15 |
| Intelligent-Tax | 0x913f..c676 | 57 | 1,010,848 | -10,497 | -1.0% | 0.641 | market-maker-like | 9% | 17 |
| Vengeful-Fiery | 0xe6c6..77b7 | 51 | 992,218 | -543 | -0.1% | 0.602 | other | 1% | 24 |
| Best-Radish | 0x2924..dcde | 57 | 901,982 | -18,025 | -2.0% | 0.775 | market-maker-like | 49% | 37 |
| Thin-Tiara | 0xc757..ccfc | 43 | 856,321 | 3,332 | 0.4% | 0.000 | sharp | 3% | 13 |
| Tough-Hammer | 0xaac2..e8ce | 55 | 827,613 | -3,671 | -0.4% | 0.654 | market-maker-like | 0% | 16 |
| Weird-Nylon | 0x6864..294b | 44 | 821,194 | -6,237 | -0.8% | 0.839 | market-maker-like | 60% | 55 |
| Every-Reform | 0x8eab..a56d | 56 | 794,337 | 5,649 | 0.7% | 0.072 | other | 84% | 7 |
| Impassioned-Prohibition | 0xfaf9..f4c4 | 47 | 651,918 | -1,699 | -0.3% | 0.640 | other | 0% | 26 |
| Careful-Bunch | 0x122c..fbed | 56 | 576,198 | 11,709 | 2.0% | 0.001 | sharp | 31% | 24 |
| Everlasting-Fit | 0x12ed..c9b4 | 55 | 567,756 | 7,024 | 1.2% | 0.193 | market-maker-like | 29% | 31 |

## Top 20 by PnL

| pseudonym | addr | events | notional $ | PnL $ | ROI | p(PnL>0) | class | cheap share | avg lead % |
|---|---|---|---|---|---|---|---|---|---|
| Hospitable-Maestro | 0x2061..8ec9 | 4 | 45,855 | 22,646 | 49.4% | 0.134 | other | 52% | 16 |
| Courageous-Polish | 0xc4d5..87cf | 57 | 2,620,650 | 19,821 | 0.8% | 0.000 | market-maker-like | 29% | 39 |
| Right-Simple | 0xfbcb..bb5d | 50 | 1,503,187 | 19,497 | 1.3% | 0.018 | market-maker-like | 22% | 24 |
| Unsightly-Dilapidation | 0xb0cc..f09b | 56 | 334,096 | 17,510 | 5.2% | 0.000 | sharp | 26% | 20 |
| Slight-Campaign | 0x7505..2978 | 57 | 278,232 | 16,594 | 6.0% | 0.000 | sharp | 16% | 18 |
| Careful-Bunch | 0x122c..fbed | 56 | 576,198 | 11,709 | 2.0% | 0.001 | sharp | 31% | 24 |
| Terrible-Drudgery-Bloodflow | 0x2ea8..ffcf | 22 | 31,215 | 11,546 | 37.0% | 0.238 | other | 84% | 30 |
| Oddball-Deviance | 0x590e..e43d | 58 | 4,256,660 | 11,219 | 0.3% | 0.103 | market-maker-like | 46% | 51 |
|  | 0xf14e..6173 | 45 | 282,405 | 10,114 | 3.6% | 0.034 | sharp | 1% | 37 |
| Private-Patrolling | 0x7789..a280 | 54 | 1,894,172 | 9,711 | 0.5% | 0.000 | sharp | 0% | 11 |
| Distant-Inhibitor | 0x524d..4495 | 51 | 177,987 | 9,581 | 5.4% | 0.352 | other | 83% | 42 |
| Black-Perpendicular-Shrimp | 0xc5e8..8354 | 41 | 40,664 | 8,666 | 21.3% | 0.263 | other | 97% | 24 |
| Delightful-Freak | 0x811e..265c | 34 | 479,760 | 8,264 | 1.7% | 0.000 | market-maker-like | 25% | 29 |
| Royal-Knickers | 0xb831..892b | 38 | 47,273 | 8,148 | 17.2% | 0.048 | sharp | 69% | 67 |
| Verifiable-Macaw | 0x1e1a..7690 | 24 | 1,124,094 | 7,966 | 0.7% | 0.000 | market-maker-like | 25% | 76 |
| Everlasting-Fit | 0x12ed..c9b4 | 55 | 567,756 | 7,024 | 1.2% | 0.193 | market-maker-like | 29% | 31 |
| Fussy-Dad | 0xa59c..bb62 | 53 | 450,573 | 7,006 | 1.6% | 0.000 | market-maker-like | 47% | 16 |
| Hidden-Contention | 0x42b8..1305 | 33 | 143,730 | 6,496 | 4.5% | 0.002 | sharp | 12% | 8 |
| Plump-Turtle | 0x6d3f..a942 | 39 | 115,871 | 6,224 | 5.4% | 0.124 | other | 3% | 29 |
| Teeming-Settler | 0xd317..025a | 53 | 124,188 | 5,979 | 4.8% | 0.000 | sharp | 60% | 9 |

## Worst 10 by PnL

| pseudonym | addr | events | notional $ | PnL $ | ROI | p(PnL>0) | class | cheap share | avg lead % |
|---|---|---|---|---|---|---|---|---|---|
| Best-Radish | 0x2924..dcde | 57 | 901,982 | -18,025 | -2.0% | 0.775 | market-maker-like | 49% | 37 |
| Several-Alien | 0xaca2..b9a1 | 56 | 155,136 | -15,422 | -9.9% | 0.830 | other | 11% | 37 |
| Normal-Mainland | 0xe089..ad3a | 51 | 34,842 | -11,021 | -31.6% | 0.899 | other | 98% | 49 |
| Intelligent-Tax | 0x913f..c676 | 57 | 1,010,848 | -10,497 | -1.0% | 0.641 | market-maker-like | 9% | 17 |
| Cumbersome-Parent | 0x0472..fc04 | 8 | 351,704 | -9,974 | -2.8% | 0.647 | other | 38% | 43 |
| Hollow-Palm | 0x6167..4447 | 8 | 35,328 | -7,882 | -22.3% | 0.675 | other | 78% | 120 |
| Adored-Flour | 0xa301..bcbd | 22 | 50,852 | -6,583 | -12.9% | 0.983 | consistent loser | 13% | 36 |
| Rusty-Afterlife | 0xf00c..40e4 | 12 | 25,388 | -6,456 | -25.4% | 0.629 | other | 2% | 54 |
| Weird-Nylon | 0x6864..294b | 44 | 821,194 | -6,237 | -0.8% | 0.839 | market-maker-like | 60% | 55 |
| Profitable-Violation | 0xf452..8ff9 | 54 | 126,623 | -6,041 | -4.8% | 0.943 | other | 46% | 28 |

## Cheap (<0.15) YES tokens: who buys vs sells

| set | notional $ | PnL $ | ROI | wallets |
|---|---|---|---|---|
| BUY cheap YES (our strategy) | 1,519,840 | 48,590 | 3.2% | 4676 |
| SELL cheap YES (counterparty) | 1,047,573 | -47,267 | -4.5% | 3136 |
| BUY cheap upper-tail YES | 747,976 | -438,771 | -58.7% | 3197 |
| SELL cheap upper-tail YES | 514,070 | 309,672 | 60.2% | 2174 |

Sellers of cheap upper-tail YES: 2174 wallets; top 10 = 40.4% of that volume. Notional-weighted share of those sellers with positive overall PnL: 67.0%; weighted mean overall ROI 0.41%. Aggregate overall PnL of sellers $50,217; their PnL on those tail sells $309,672.

| pseudonym | addr | tail-sell notional | tail PnL | overall PnL | overall ROI | events | class |
|---|---|---|---|---|---|---|---|
| Oddball-Deviance | 0x590e..e43d | 97,971 | 82,138 | 11,219 | 0.3% | 58 | market-maker-like |
| Verifiable-Macaw | 0x1e1a..7690 | 19,685 | 19,685 | 7,966 | 0.7% | 24 | market-maker-like |
| Courageous-Polish | 0xc4d5..87cf | 15,765 | 3,788 | 19,821 | 0.8% | 57 | market-maker-like |
| Writhing-Rib | 0x2eb6..3e31 | 12,194 | 12,194 | 433 | 0.0% | 35 | market-maker-like |
| Everlasting-Fit | 0x12ed..c9b4 | 11,736 | 9,092 | 7,024 | 1.2% | 55 | market-maker-like |
| Secondary-Clogs | 0x74ff..be5b | 11,676 | -9,167 | -3,067 | -1.5% | 56 | market-maker-like |
| Right-Simple | 0xfbcb..bb5d | 10,211 | 6,814 | 19,497 | 1.3% | 50 | market-maker-like |
| Weird-Nylon | 0x6864..294b | 10,012 | 10,012 | -6,237 | -0.8% | 44 | market-maker-like |
| Robust-Creature | 0x17f1..0528 | 9,465 | 5,465 | 5,278 | 3.9% | 54 | sharp |
| Big-Personality | 0xbbdc..5d81 | 8,855 | 8,855 | 2,049 | 1.1% | 37 | other |
|  | 0x849c..4009 | 8,628 | -3,223 | -1,903 | -1.0% | 45 | market-maker-like |
| Best-Radish | 0x2924..dcde | 7,548 | 6,342 | -18,025 | -2.0% | 57 | market-maker-like |
| Pertinent-Bronco | 0x6be9..3493 | 6,434 | -3,409 | 2,152 | 7.4% | 57 | other |
| Secret-Neurobiologist | 0xb7fd..cc88 | 6,102 | 5,162 | 263 | 0.5% | 38 | sharp |
| Fussy-Dad | 0xa59c..bb62 | 5,824 | 5,824 | 7,006 | 1.6% | 53 | market-maker-like |

## Do profitable wallets buy or sell cheap tokens?

| group | wallets | cheap-buy notional | cheap-sell notional | buy share of cheap notional |
|---|---|---|---|---|
| sharp | 1282 | 114,396 | 109,912 | 51% |
| consistent loser | 273 | 84,207 | 27,268 | 76% |
| market-maker-like | 111 | 677,321 | 595,558 | 53% |
| one-off | 16780 | 37,825 | 19,749 | 66% |
| other | 8075 | 692,010 | 338,768 | 67% |
| profitable (>=5 ev) | 3928 | 866,479 | 680,836 | 56% |
| unprofitable (>=5 ev) | 2994 | 660,745 | 372,444 | 64% |

## Broader PnL via data-api (top 5 sharp by PnL)

- Unsightly-Dilapidation 0xb0cc..f09b: /positions ok, 72 open positions, cashPnl sum $-3,004, realizedPnl sum $-245 (current positions only)
- Slight-Campaign 0x7505..2978: /positions ok, 1 open positions, cashPnl sum $23, realizedPnl sum $0 (current positions only)
- Careful-Bunch 0x122c..fbed: /positions ok, 500 open positions, cashPnl sum $-37,715, realizedPnl sum $-30,017 (current positions only)
-  0xf14e..6173: /positions ok, 6 open positions, cashPnl sum $-4,668, realizedPnl sum $-1,965 (current positions only)
- Private-Patrolling 0x7789..a280: /positions ok, 30 open positions, cashPnl sum $-5,125, realizedPnl sum $1,306 (current positions only)
