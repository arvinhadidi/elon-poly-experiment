# Wallet profile: Elon tweet-count markets

Trade files used: 208 (files modified <2 min ago excluded); 21,142,623 resolved fills; 179,052 wallets; 208 events.

Interpretation: each row is one wallet's fill (proxyWallet = that participant, side = THAT wallet's side). Both sides of a match appear as separate rows under the same transactionHash (every hash has >=2 rows; e.g. BUY No@0.999 + BUY Yes@0.001 = a mint, or BUY+SELL of the same asset). So per-wallet PnL is correct, but summed notional/PnL across wallets double-counts volume (PnL sums to ~0 across counterparties, before fees/unresolved).

PnL = realised to resolution (hold-to-resolution mark; ignores exits' timing). Lead % = notional-weighted % of the window still remaining at trade time (negative = after window end; >100 = before window start).

## Classes

| class | wallets | notional share | notional $ | PnL $ | ROI |
|---|---|---|---|---|---|
| consistent loser | 1339.0 | 2.2% | 16,434,770 | -771,438 | -4.69% |
| market-maker-like | 1115.0 | 36.4% | 276,867,088 | 570,598 | 0.21% |
| one-off | 113756.0 | 4.2% | 32,202,337 | -1,198,804 | -3.72% |
| other | 55710.0 | 38.2% | 290,254,762 | -1,625,264 | -0.56% |
| sharp | 7132.0 | 19.1% | 144,986,890 | 2,996,695 | 2.07% |

21753 wallets have >=10 events; with a 5% test ~1088 false-positive 'sharp' labels are expected by chance alone, so treat the sharp class as an upper bound.

Total notional (double-counted) $760,745,847; net PnL $-28,213.

## Concentration
Top 10 wallets = 16.0% of notional; top 50 = 35.5%; top 1 = 2.6%.

## Top 20 by notional

| pseudonym | addr | events | notional $ | PnL $ | ROI | p(PnL>0) | class | cheap share | avg lead % |
|---|---|---|---|---|---|---|---|---|---|
| Gracious-Movement | 0xdf1b..b963 | 39 | 19,656,371 | 15,759 | 0.1% | 0.000 | sharp | 0% | 28 |
| Courageous-Polish | 0xc4d5..87cf | 202 | 17,475,744 | 159,006 | 0.9% | 0.000 | market-maker-like | 24% | 33 |
| Standard-Verification | 0x689a..779e | 108 | 16,991,938 | 605,513 | 3.6% | 0.000 | sharp | 62% | 29 |
| Real-Veteran | 0xe8dd..ec86 | 74 | 15,966,211 | 3,991 | 0.0% | 0.276 | other | 1% | 64 |
| Husky-Labourer | 0x5409..79db | 114 | 13,393,340 | 3,961 | 0.0% | 0.239 | other | 0% | 45 |
| Lost-Macadamia | 0x45b3..35bc | 80 | 9,140,723 | -16,992 | -0.2% | 0.710 | other | 0% | 28 |
| Motionless-Everyone | 0x48c5..89f3 | 141 | 8,077,604 | -50,875 | -0.6% | 0.788 | market-maker-like | 32% | 15 |
| Serpentine-Maggot | 0x6964..ef53 | 202 | 7,756,198 | 35,741 | 0.5% | 0.005 | market-maker-like | 32% | 6 |
| Creepy-Meteor | 0x471a..0328 | 168 | 7,430,089 | 45,493 | 0.6% | 0.003 | market-maker-like | 20% | 6 |
| Wee-Globe | 0x5116..58c4 | 46 | 5,968,593 | -33,208 | -0.6% | 0.728 | other | 82% | 31 |
| Pure-Hospitality | 0xf5d9..be50 | 97 | 5,839,456 | -554 | -0.0% | 0.473 | other | 2% | 9 |
| Oddball-Deviance | 0x590e..e43d | 95 | 5,808,368 | 20,403 | 0.4% | 0.025 | market-maker-like | 46% | 49 |
|  | 0x849c..4009 | 190 | 5,409,054 | 19,090 | 0.4% | 0.175 | market-maker-like | 48% | 31 |
| Private-Patrolling | 0x7789..a280 | 178 | 5,407,189 | -21,305 | -0.4% | 0.842 | other | 0% | 33 |
| Total-Pronoun | 0xd362..9bc4 | 68 | 5,233,430 | 833 | 0.0% | 0.093 | market-maker-like | 0% | 39 |
| Fussy-Dad | 0xa59c..bb62 | 158 | 4,951,603 | 72,422 | 1.5% | 0.000 | market-maker-like | 49% | 8 |
| Tough-Hammer | 0xaac2..e8ce | 136 | 4,920,235 | 4,109 | 0.1% | 0.342 | market-maker-like | 0% | 15 |
| Every-Reform | 0x8eab..a56d | 196 | 4,615,321 | 30,474 | 0.7% | 0.000 | market-maker-like | 74% | 9 |
| Verifiable-Macaw | 0x1e1a..7690 | 101 | 4,518,818 | 68,580 | 1.5% | 0.000 | market-maker-like | 52% | 74 |
| Glamorous-Motel | 0x2d4c..2e02 | 49 | 4,485,763 | -63,756 | -1.4% | 0.977 | market-maker-like | 15% | 35 |

## Top 20 by PnL

| pseudonym | addr | events | notional $ | PnL $ | ROI | p(PnL>0) | class | cheap share | avg lead % |
|---|---|---|---|---|---|---|---|---|---|
| Standard-Verification | 0x689a..779e | 108 | 16,991,938 | 605,513 | 3.6% | 0.000 | sharp | 62% | 29 |
| Flamboyant-Disability | 0x90ed..b5bc | 54 | 2,300,656 | 300,543 | 13.1% | 0.026 | sharp | 73% | 26 |
| Courageous-Polish | 0xc4d5..87cf | 202 | 17,475,744 | 159,006 | 0.9% | 0.000 | market-maker-like | 24% | 33 |
| Scared-Chaos | 0x063a..eb4b | 3 | 275,158 | 155,964 | 56.7% | 0.036 | other | 86% | 39 |
| Broken-Teriyaki | 0xbb9c..072b | 103 | 2,362,275 | 118,552 | 5.0% | 0.000 | sharp | 20% | 4 |
| Unhealthy-Bog | 0xcbbc..b5d0 | 28 | 555,639 | 103,728 | 18.7% | 0.003 | sharp | 93% | 28 |
| Lustrous-Proceedings | 0xacbc..7cc3 | 48 | 388,498 | 93,908 | 24.2% | 0.155 | other | 59% | 23 |
|  | 0x265f..a448 | 62 | 1,009,976 | 85,635 | 8.5% | 0.000 | sharp | 31% | 4 |
| Genuine-Armpit | 0xa638..1d87 | 87 | 1,279,281 | 82,272 | 6.4% | 0.080 | other | 32% | 11 |
| Bumpy-Owl | 0xd8c4..848d | 138 | 1,884,984 | 74,197 | 3.9% | 0.001 | sharp | 94% | 30 |
| Fussy-Dad | 0xa59c..bb62 | 158 | 4,951,603 | 72,422 | 1.5% | 0.000 | market-maker-like | 49% | 8 |
| Bustling-Scene | 0x1355..6591 | 43 | 270,986 | 70,547 | 26.0% | 0.003 | sharp | 71% | 30 |
| Verifiable-Macaw | 0x1e1a..7690 | 101 | 4,518,818 | 68,580 | 1.5% | 0.000 | market-maker-like | 52% | 74 |
| Hefty-Sunshine | 0x7744..999e | 3 | 83,216 | 64,731 | 77.8% | 0.300 | other | 40% | 11 |
| Glass-Typewriter | 0xa49b..7054 | 189 | 1,059,753 | 57,031 | 5.4% | 0.001 | sharp | 75% | 57 |
| Several-Alien | 0xaca2..b9a1 | 177 | 704,915 | 54,970 | 7.8% | 0.151 | other | 30% | 24 |
| Fabulous-Rating | 0x77c8..bc8c | 139 | 2,485,735 | 49,418 | 2.0% | 0.100 | other | 49% | 17 |
| Creepy-Meteor | 0x471a..0328 | 168 | 7,430,089 | 45,493 | 0.6% | 0.003 | market-maker-like | 20% | 6 |
| Crisp-Jumbo | 0x6df5..6430 | 138 | 240,913 | 39,292 | 16.3% | 0.026 | sharp | 83% | 7 |
| Everlasting-Fit | 0x12ed..c9b4 | 162 | 1,479,691 | 38,493 | 2.6% | 0.002 | sharp | 27% | 32 |

## Worst 10 by PnL

| pseudonym | addr | events | notional $ | PnL $ | ROI | p(PnL>0) | class | cheap share | avg lead % |
|---|---|---|---|---|---|---|---|---|---|
| Kindly-Patrolling | 0xd3d7..ac2b | 6 | 1,662,397 | -648,378 | -39.0% | 0.913 | other | 0% | 24 |
| Each-Sneeze | 0x9193..b1f1 | 1 | 401,115 | -391,980 | -97.7% |  | one-off | 27% | 0 |
| Minor-Applause | 0xd5af..5d38 | 22 | 4,330,857 | -166,366 | -3.8% | 0.631 | other | 1% | 22 |
| Sparse-Teammate | 0xf5b1..c7e3 | 2 | 1,009,482 | -121,303 | -12.0% |  | one-off | 1% | 36 |
| Hidden-Bloodflow | 0xce1e..851f | 6 | 112,347 | -73,406 | -65.3% | 0.990 | other | 96% | 45 |
| Salty-Geometry | 0xbac4..1ab2 | 58 | 1,289,530 | -65,309 | -5.1% | 0.998 | consistent loser | 43% | 26 |
| Necessary-Inversion | 0x8556..fad9 | 10 | 153,215 | -64,780 | -42.3% | 1.000 | consistent loser | 72% | 19 |
| Glamorous-Motel | 0x2d4c..2e02 | 49 | 4,485,763 | -63,756 | -1.4% | 0.977 | market-maker-like | 15% | 35 |
| Willing-Eve | 0xca6e..46f2 | 79 | 762,564 | -62,901 | -8.2% | 0.743 | other | 88% | 23 |
| Motionless-Everyone | 0x48c5..89f3 | 141 | 8,077,604 | -50,875 | -0.6% | 0.788 | market-maker-like | 32% | 15 |

## Cheap (<0.15) YES tokens: who buys vs sells

| set | notional $ | PnL $ | ROI | wallets |
|---|---|---|---|---|
| BUY cheap YES (our strategy) | 19,169,833 | 3,607,240 | 18.8% | 65152 |
| SELL cheap YES (counterparty) | 14,203,481 | -2,124,317 | -15.0% | 39126 |
| BUY cheap upper-tail YES | 8,956,103 | -8,472,229 | -94.6% | 40191 |
| SELL cheap upper-tail YES | 6,534,562 | 6,213,171 | 95.1% | 25634 |

Sellers of cheap upper-tail YES: 25634 wallets; top 10 = 19.8% of that volume. Notional-weighted share of those sellers with positive overall PnL: 68.9%; weighted mean overall ROI 1.12%. Aggregate overall PnL of sellers $2,405,169; their PnL on those tail sells $6,213,171.

| pseudonym | addr | tail-sell notional | tail PnL | overall PnL | overall ROI | events | class |
|---|---|---|---|---|---|---|---|
| Standard-Verification | 0x689a..779e | 252,150 | 251,828 | 605,513 | 3.6% | 108 | sharp |
|  | 0x849c..4009 | 247,410 | 235,560 | 19,090 | 0.4% | 190 | market-maker-like |
| Verifiable-Macaw | 0x1e1a..7690 | 147,760 | 147,760 | 68,580 | 1.5% | 101 | market-maker-like |
| Oddball-Deviance | 0x590e..e43d | 134,580 | 118,747 | 20,403 | 0.4% | 95 | market-maker-like |
| Awkward-Patriot | 0xe372..eb38 | 118,523 | 118,523 | 2,061 | 0.2% | 72 | sharp |
| Courageous-Polish | 0xc4d5..87cf | 91,247 | 77,268 | 159,006 | 0.9% | 202 | market-maker-like |
| Murky-Oversight | 0x8e9e..38e4 | 83,981 | 83,981 | 2,527 | 0.5% | 27 | sharp |
| Right-Interferometer | 0x071d..07ef | 82,455 | 82,396 | 624 | 0.0% | 115 | market-maker-like |
| Legal-Zucchini | 0xa459..7dd6 | 70,468 | 70,468 | 1,870 | 1.1% | 58 | sharp |
| Robust-Creature | 0x17f1..0528 | 63,239 | 59,239 | 7,732 | 1.6% | 125 | market-maker-like |
| Pertinent-Bronco | 0x6be9..3493 | 61,828 | 48,186 | 6,686 | 0.7% | 204 | other |
| Gleeful-Bookmark | 0x1022..f0cf | 55,561 | 55,561 | -8,306 | -0.2% | 20 | market-maker-like |
| Glass-Typewriter | 0xa49b..7054 | 54,450 | 53,472 | 57,031 | 5.4% | 189 | sharp |
| Unhealthy-Bog | 0xcbbc..b5d0 | 51,714 | 51,714 | 103,728 | 18.7% | 28 | sharp |
| Spirited-Motion | 0x70b6..aa2f | 51,219 | 51,149 | 790 | 0.0% | 49 | market-maker-like |

## Do profitable wallets buy or sell cheap tokens?

| group | wallets | cheap-buy notional | cheap-sell notional | buy share of cheap notional |
|---|---|---|---|---|
| sharp | 7132 | 3,435,187 | 3,021,441 | 53% |
| consistent loser | 1339 | 738,253 | 464,784 | 61% |
| market-maker-like | 1115 | 5,849,375 | 5,371,804 | 52% |
| one-off | 113756 | 791,065 | 390,250 | 67% |
| other | 55710 | 8,905,892 | 5,217,122 | 63% |
| profitable (>=5 ev) | 24409 | 12,324,082 | 9,541,611 | 56% |
| unprofitable (>=5 ev) | 17665 | 5,946,398 | 4,109,085 | 59% |

## Broader PnL via data-api (top 5 sharp by PnL)

- Standard-Verification 0x689a..779e: /positions ok, 0 open positions, cashPnl sum $0, realizedPnl sum $0 (current positions only)
- Flamboyant-Disability 0x90ed..b5bc: /positions ok, 174 open positions, cashPnl sum $-178,138, realizedPnl sum $70,490 (current positions only)
- Broken-Teriyaki 0xbb9c..072b: /positions ok, 7 open positions, cashPnl sum $-302, realizedPnl sum $15 (current positions only)
- Unhealthy-Bog 0xcbbc..b5d0: /positions ok, 500 open positions, cashPnl sum $-106,523, realizedPnl sum $7,957 (current positions only)
-  0x265f..a448: /positions ok, 74 open positions, cashPnl sum $-10,136, realizedPnl sum $122 (current positions only)
