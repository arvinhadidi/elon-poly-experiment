# Resolution risk audit (closed Elon weekly/48h/monthly/daily events)

Generated 2026-10-10 17:46 UTC. Sources: data/events.csv (uma_status), Gamma /markets/<id> (umaResolutionStatus, umaResolutionStatuses), data/events_summary.csv vs data/posts_elonmusk.csv counts with window [start,end) on createdAt.

## Local uma_status (events.csv)

- closed events: 368; closed markets: 6132
- status values per market: resolved=6125, proposed=7
- markets with anything other than plain `resolved`: 7 (proposed)
- events affected: 1 of 368

## Gamma UMA history (all closed markets in events.csv)

- fetched 6132/6132 markets (0 errors)
- current umaResolutionStatus: resolved=6125, proposed=7
- markets with >=2 'proposed' entries in umaResolutionStatuses: 562
- markets with any dispute/challenge entry: 12
- markets where local uma_status disagrees with Gamma current status: 0
- Gamma fields with uma/resolution/dispute in name: automaticallyResolved, resolutionSource, resolvedBy, umaBond, umaEndDate, umaEndDateIso, umaResolutionStatus, umaResolutionStatuses, umaReward

Sample (every ~N-th market):

| market_id | event | gamma umaResolutionStatus | umaResolutionStatuses | automaticallyResolved | closedTime |
|---|---|---|---|---|---|
| 253768 | of-elon-musk-tweets-between-january-10-16 | proposed | [] | None | 2024-01-17 09:46:49+00 |
| 524461 | elon-musk-of-tweets-feb-21-28 | resolved | [] | True | 2025-02-28 22:14:39+00 |
| 583671 | elon-musk-of-tweets-in-september | resolved | ["proposed", "resolved"] | True | 2025-09-14 08:29:46+00 |
| 631565 | elon-musk-of-tweets-october-14-october-21 | resolved | ["proposed", "resolved"] | True | 2025-10-21 19:13:05+00 |
| 847526 | elon-musk-of-tweets-december-9-december-16 | resolved | ["proposed", "resolved"] | True | 2025-12-16 16:52:09+00 |
| 1203744 | elon-musk-of-tweets-january-20-january-27 | resolved | ["proposed", "resolved"] | True | 2026-01-23 05:03:54+00 |
| 1387679 | elon-musk-of-tweets-february-20-february-27 | resolved | ["proposed", "resolved"] | True | 2026-02-27 20:53:35+00 |
| 1698808 | elon-musk-of-tweets-may-2026 | resolved | ["proposed"] | True | 2026-05-05 14:50:22+00 |
| 2101864 | elon-musk-of-tweets-may-1-may-8 | resolved | ["proposed"] | True | 2026-05-04 11:41:40+00 |
| 2436825 | elon-musk-of-tweets-june-6-june-8 | resolved | ["proposed"] | True | 2026-06-08 18:13:54+00 |
| 2916670 | elon-musk-of-tweets-july-17-july-24 | resolved | ["proposed"] | True | 2026-07-24 18:04:13+00 |
| 3772767 | elon-musk-of-tweets-august-25-september-1-2026 | resolved | ["proposed", "proposed"] | True | 2026-09-01 18:03:31+00 |

## Tracker count vs gamma winning bucket (closed events in events_summary.csv)

- checked 368 closed events; disagreements: 122

| event | family | tracker n (createdAt in window) | gamma winning bucket lo/hi | tracker-matching bucket |
|---|---|---|---|---|
| of-elon-musk-tweets-between-january-10-16 | other | 0 | 301-375 | <160 |
| how-many-times-will-elon-musk-tweet-between-april-26-and-may-3 | weekly | 0 | 60-79 | <60 |
| of-elon-musk-tweets-between-may-3-and-may-10 | weekly | 0 | 90-104 | <60 |
| of-elon-musk-tweets-between-may-17-and-may-24 | weekly | 0 | 75-84 | <55 |
| of-elon-musk-tweets-between-may-31-and-june-7 | weekly | 0 | 80-89 | <40 |
| of-elon-musk-tweets-june-7-14 | weekly | 0 | 70-79 | <40 |
| elon-musk-of-tweets-june-14-21 | weekly | 0 | 40-49 | <40 |
| elon-musk-of-tweets-june-21-28 | weekly | 0 | 50-59 | <40 |
| elon-musk-of-tweets-june-28-july-5 | weekly | 0 | 70-79 | <40 |
| elon-musk-of-tweets-july-5-july-12 | weekly | 0 | 70-79 | <40 |
| elon-musk-of-tweets-july-12-july-19 | weekly | 0 | 100-999999 | <40 |
| elon-musk-of-tweets-july-19-26 | weekly | 0 | 100-109 | <60 |
| elon-musk-of-tweets-july-26-aug-2 | weekly | 0 | 120-999999 | <60 |
| elon-musk-of-tweets-august-2-9 | weekly | 0 | 80-89 | <60 |
| elon-musk-of-tweets-august-9-16 | weekly | 0 | 130-999999 | <60 |
| elon-musk-of-tweets-august-16-23 | weekly | 0 | 80-99 | <60 |
| elon-musk-of-tweets-august-23-30 | weekly | 0 | 150-999999 | <60 |
| elon-musk-of-tweets-august-30-sept-6 | weekly | 0 | 180-999999 | <80 |
| elon-musk-of-tweets-sept-6-13 | weekly | 0 | 225-249 | <150 |
| elon-musk-of-tweets-sept-13-20 | weekly | 0 | 225-249 | <100 |
| elon-musk-of-tweets-sept-20-27 | weekly | 0 | 200-224 | <100 |
| elon-musk-of-tweets-sept-27-oct-4 | weekly | 0 | 300-999999 | <100 |
| elon-musk-of-tweets-oct-4-11 | weekly | 0 | 175-199 | <150 |
| elon-musk-of-tweets-oct-11-18 | weekly | 0 | 200-224 | <150 |
| elon-musk-of-tweets-oct-18-25 | weekly | 0 | 300-999999 | <100 |
| elon-musk-of-tweets-oct-25-nov-1 | weekly | 0 | 400-999999 | <150 |
| elon-musk-of-tweets-nov-1-8 | weekly | 0 | 375-399 | <250 |
| elon-musk-of-tweets-nov-8-15 | weekly | 0 | 375-399 | <150 |
| elon-musk-of-tweets-nov-15-22 | weekly | 0 | 450-999999 | <200 |
| elon-musk-of-tweets-nov-22-29 | weekly | 0 | 475-499 | <300 |
| elon-musk-of-tweets-december-6-13 | weekly | 0 | 400-424 | <250 |
| elon-musk-of-tweets-december-13-20 | weekly | 0 | 400-424 | <300 |
| elon-musk-of-tweets-december-20-27 | weekly | 0 | 300-324 | <250 |
| elon-musk-of-tweets-december-27-january-3 | weekly | 0 | 400-424 | <250 |
| elon-musk-of-tweets-january-3-january-10 | weekly | 0 | 500-999999 | <250 |
| elon-musk-of-tweets-january-3-10-continued | weekly | 0 | 650-674 | <550 |
| elon-musk-of-tweets-january-10-17 | weekly | 0 | 400-449 | <400 |
| elon-musk-of-tweets-january-10-17-25-strikes | weekly | 0 | 400-424 | <300 |
| elon-musk-of-tweets-january-17-24 | weekly | 0 | 325-349 | <300 |
| elon-musk-of-tweets-january-24-31 | weekly | 0 | 275-299 | <250 |
| elon-musk-of-tweets-january-24-31-lower-options | weekly | 0 | 250-999999 | <100 |
| elon-musk-of-tweets-jan-31-feb-7 | weekly | 0 | 450-999999 | <200 |
| elon-musk-of-tweets-jan-31-feb-7-higher-options | weekly | 0 | 650-674 | <500 |
| elon-musk-of-tweets-feb-7-14 | weekly | 0 | 800-999999 | <300 |
| elon-musk-of-tweets-feb-7-14-higher-options | weekly | 0 | 850-874 | <800 |
| elon-musk-of-tweets-feb-14-21 | weekly | 0 | 600-649 | <500 |
| elon-musk-of-tweets-feb-21-28 | weekly | 0 | 750-799 | <400 |
| elon-musk-of-tweets-feb-28-mar-7 | weekly | 0 | 550-599 | <500 |
| elon-musk-of-tweets-mar-7-14 | weekly | 0 | 500-524 | <450 |
| elon-musk-of-tweets-mar-14-21 | weekly | 0 | 425-449 | <400 |
| elon-musk-of-tweets-mar-14-21-lower-brackets | weekly | 0 | 400-999999 | <250 |
| elon-musk-of-tweets-mar-21-28 | weekly | 0 | 475-499 | <300 |
| elon-musk-of-tweets-mar-28-apr-4 | weekly | 0 | 325-349 | <300 |
| elon-musk-of-tweets-april-4-11-lower-brackets | weekly | 0 | 180-189 | <100 |
| elon-musk-of-tweets-april-11-18-628 | weekly | 0 | 150-174 | <100 |
| elon-musk-of-tweets-april-18-25 | weekly | 0 | 200-224 | <100 |
| elon-musk-of-tweets-april-25-may-2 | weekly | 0 | 150-174 | <100 |
| elon-musk-of-tweets-may-2-9 | weekly | 0 | 225-249 | <100 |
| elon-musk-of-tweets-may-9-16 | weekly | 0 | 250-274 | <100 |
| elon-musk-of-tweets-may-16-23 | weekly | 0 | 150-174 | <100 |
| elon-musk-of-tweets-may-23-30 | weekly | 0 | 125-149 | <100 |
| elon-musk-of-tweets-may-30-june-6 | weekly | 0 | 230-999999 | <80 |
| elon-musk-of-tweets-may-30-june-6-higher-brackets-137 | weekly | 0 | 320-334 | <230 |
| elon-musk-of-tweets-june-6-13 | weekly | 0 | 175-199 | <150 |
| elon-musk-of-tweets-june-13-20 | weekly | 0 | 145-159 | <100 |
| elon-musk-of-tweets-june-20-27 | weekly | 0 | 130-144 | <100 |
| elon-musk-of-tweets-june-27-july-4 | weekly | 0 | 165-179 | <90 |
| elon-musk-of-tweets-july-4-11 | weekly | 0 | 150-164 | <90 |
| elon-musk-of-tweets-july-11-18 | weekly | 0 | 180-194 | <90 |
| elon-musk-of-tweets-july-18-25 | weekly | 0 | 195-209 | <90 |
| elon-musk-number-of-tweets-25-times-thursday | daily | 0 | 25-999999 | no bucket |
| elon-musk-of-tweets-july-25-august-1 | weekly | 0 | 150-164 | <90 |
| elon-musk-number-of-tweets-25-times-7-31 | daily | 0 | - | no bucket |
| elon-musk-tweets-25-times-wednesday | daily | 0 | 25-999999 | no bucket |
| elon-musk-number-of-tweets-25-times-7-29 | daily | 0 | - | no bucket |
| elon-musk-of-tweets-august-1-8 | weekly | 0 | 255-999999 | <90 |
| elon-musk-of-tweets-august-1-8-higher-brackets | weekly | 0 | 360-374 | <255 |
| elon-musk-number-of-tweets-25-times-8-9 | daily | 0 | 25-999999 | no bucket |
| elon-musk-number-of-tweets-25-times-8-6 | daily | 0 | 25-999999 | no bucket |
| elon-musk-number-of-tweets-25-times-8-10 | daily | 0 | 25-999999 | no bucket |
| elon-musk-number-of-tweets-25-times-8-7 | daily | 0 | 25-999999 | no bucket |
| elon-musk-number-of-tweets-25-times-8-8 | daily | 0 | 25-999999 | no bucket |
| elon-musk-of-tweets-august-8-15 | weekly | 0 | 470-999999 | <215 |
| elon-musk-number-of-tweets-35-times-8-12 | daily | 0 | 35-999999 | no bucket |
| elon-musk-number-of-tweets-35-times-8-11 | daily | 0 | 35-999999 | no bucket |
| elon-musk-of-tweets-august-8-15-brackets-of-30 | weekly | 0 | 450-999999 | <150 |
| elon-musk-of-tweets-august-8-15-higher-brackets | weekly | 0 | 500-524 | <450 |
| elon-musk-of-tweets-august-15-22-lower-brackets | weekly | 0 | 225-239 | <150 |
| elon-musk-of-tweets-august-22-29 | weekly | 0 | 195-209 | <150 |
| elon-musk-of-tweets-august-29-september-5 | weekly | 0 | 400-999999 | <100 |
| elon-musk-of-tweets-in-september | monthly | 0 | 900-949 | <400 |
| elon-musk-of-tweets-august-29-september-5-629 | weekly | 0 | 450-479 | <300 |
| elon-musk-of-tweets-september-5-12 | weekly | 0 | 220-239 | <200 |
| elon-musk-of-tweets-september-9-september-16 | weekly | 0 | 240-259 | <20 |
| elon-musk-of-tweets-september-7 | daily | 0 | 30-39 | <30 |
| elon-musk-of-tweets-september-8 | daily | 0 | 40-49 | <30 |
| elon-musk-of-tweets-september-9 | daily | 0 | 30-39 | <30 |
| elon-musk-of-tweets-september-12-september-19 | weekly | 0 | 240-259 | <20 |
| elon-musk-of-tweets-september-10 | daily | 0 | 40-49 | <30 |
| elon-musk-of-tweets-september-12 | daily | 0 | 30-39 | <30 |
| elon-musk-of-tweets-september-13 | daily | 0 | 30-39 | <30 |
| elon-musk-of-tweets-september-16-september-23 | weekly | 0 | 180-199 | <20 |
| elon-musk-of-tweets-september-14 | daily | 0 | 50-59 | <20 |
| elon-musk-of-tweets-september-15 | daily | 0 | 30-39 | <30 |
| elon-musk-of-tweets-september-19-september-26 | weekly | 0 | 120-139 | <20 |
| elon-musk-of-tweets-september-17 | daily | 0 | 30-39 | <30 |
| elon-musk-of-tweets-september-18 | daily | 0 | 40-49 | <10 |
| elon-musk-of-tweets-september-23-september-30 | weekly | 0 | 120-139 | <20 |
| elon-musk-of-tweets-september-26-october-3 | weekly | 0 | 240-259 | <20 |
| elon-musk-of-tweets-october-2025 | monthly | 1 | 1080-1119 | <20 |
| elon-musk-of-tweets-september-30-october-7 | weekly | 0 | 300-319 | <20 |
| elon-musk-of-tweets-october-3-october-10 | weekly | 0 | 280-299 | <20 |
| elon-musk-of-tweets-october-7-october-14 | weekly | 0 | 240-259 | <20 |
| elon-musk-of-tweets-october-10-october-17 | weekly | 0 | 180-199 | <20 |
| elon-musk-of-tweets-october-14-october-21 | weekly | 0 | 260-279 | <20 |
| elon-musk-of-tweets-october-17-october-24 | weekly | 0 | 280-299 | <20 |
| elon-musk-of-tweets-october-21-october-28 | weekly | 0 | 180-199 | <20 |
| elon-musk-of-tweets-october-24-october-31 | weekly | 0 | 200-219 | <20 |
| elon-musk-of-tweets-october-28-november-4 | weekly | 95 | 200-219 | 80-99 |
| elon-musk-of-tweets-october-31-november-7 | weekly | 152 | 160-179 | 140-159 |
| arch-elon-musk-of-tweets-may-19-may-26 | weekly | 260 | 380-399 | 260-279 |
| arch-elon-musk-of-tweets-may-18-may-20 | 48h | 73 | 140-164 | 65-89 |

## Web search

(filled in separately)


## Reading note (added after review)
- The "122 disagreements" above are almost all outside tracker coverage: 120 windows predate the post data (xtracker history starts Nov 2025), so the tracker count there is 0. **Inside coverage (windows from 2025-12-01) only 2 real mismatches remain, both archived "arch-" duplicate events** (arch-elon-musk-of-tweets-may-19-may-26, arch-...-may-18-may-20). Non-arch match rate: 210/212 → 100% excluding arch.
- 562 markets with ≥2 "proposed" entries are the normal propose→confirm path, not disputes. 12 markets have a dispute entry; none changed the outcome.

## Web search (2026-10-10)
- No UMA dispute found that changed an Elon tweet-count outcome. Third-party Orrery pages show some May 2026 post-count markets as "proposed" with disputes (may lag).
- No xtracker-specific outage reported publicly. General Polymarket halts: Aug 31 2026 trading API, June 2026 v2.6.x maintenance.
- Rules: deleted posts count only if the tracker captured them (~5 min); X is the fallback resolution source.
