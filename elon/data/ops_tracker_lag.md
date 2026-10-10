# Tracker lag (xtracker, elonmusk X posts)

Generated 2026-10-10 17:42 UTC from data/posts_elonmusk.csv (13196 posts, 0 without importedAt). lag = importedAt - createdAt.

## (a) Lag distribution per month (by createdAt month)

| month | n | p50 s | p90 s | p99 s | max s | max h | share >1h |
|---|---|---|---|---|---|---|---|
| 2025-11 | 915 | 645875 | 1691792 | 1893210 | 1957051 | 543.6 | 0.713 |
| 2025-12 | 1648 | 158 | 283 | 857 | 5329 | 1.5 | 0.002 |
| 2026-01 | 2136 | 159 | 281 | 309 | 28726 | 8.0 | 0.005 |
| 2026-02 | 1226 | 154 | 277 | 306 | 1416 | 0.4 | 0.000 |
| 2026-03 | 1330 | 159 | 272 | 307 | 706 | 0.2 | 0.000 |
| 2026-04 | 1050 | 147 | 263 | 13686 | 57840 | 16.1 | 0.013 |
| 2026-05 | 843 | 137 | 248 | 296 | 532 | 0.1 | 0.000 |
| 2026-06 | 974 | 142 | 264 | 454 | 34045 | 9.5 | 0.007 |
| 2026-07 | 883 | 133 | 256 | 306 | 336 | 0.1 | 0.000 |
| 2026-08 | 883 | 118 | 266 | 88082 | 165909 | 46.1 | 0.037 |
| 2026-09 | 872 | 156 | 285 | 55327 | 76191 | 21.2 | 0.036 |
| 2026-10 | 436 | 206 | 95436 | 165666 | 182837 | 50.8 | 0.257 |

## (b) Import batches (>=5 posts with identical importedAt minute, median createdAt > 1h earlier)

9 batches. Columns: importedAt minute (UTC), n posts, max delay h, min delay h.

| importedAt (UTC, minute) | n | max delay h | min delay h |
|---|---|---|---|
| 2025-11-24T06:24 | 648 | 543.6 | 0.4 |
| 2025-11-28T10:05 | 13 | 1.5 | 0.8 |
| 2026-01-29T05:15 | 13 | 8.0 | 0.3 |
| 2026-04-30T21:35 | 15 | 16.1 | 0.2 |
| 2026-06-01T13:39 | 9 | 9.5 | 0.3 |
| 2026-08-28T15:39 | 20 | 20.1 | 1.1 |
| 2026-08-28T17:12 | 13 | 46.1 | 21.9 |
| 2026-09-11T21:15 | 32 | 21.2 | 0.8 |
| 2026-10-08T18:20 | 115 | 50.8 | 0.0 |

## (c) Gaps with no importedAt (longest gap per month)

Gap = time between consecutive importedAt values. `created_in_gap` = posts whose createdAt falls inside the gap; >0 means posts existed but were not yet imported (outage-like). 0 means probably just no posts (quiet period), so most gaps are not outages.

| month | longest gap h | start (UTC) | end (UTC) | created_in_gap |
|---|---|---|---|---|
| 2025-11 | 133.67 | 2025-11-18 16:44 | 2025-11-24 06:24 | 145 |
| 2025-12 | 17.67 | 2025-12-13 11:55 | 2025-12-14 05:35 | 2 |
| 2026-01 | 11.83 | 2026-01-04 20:25 | 2026-01-05 08:15 | 1 |
| 2026-02 | 10.75 | 2026-02-05 05:00 | 2026-02-05 15:45 | 1 |
| 2026-03 | 13.33 | 2026-03-17 17:50 | 2026-03-18 07:10 | 1 |
| 2026-04 | 30.58 | 2026-04-29 15:00 | 2026-04-30 21:35 | 15 |
| 2026-05 | 16.83 | 2026-05-10 22:40 | 2026-05-11 15:30 | 1 |
| 2026-06 | 25.00 | 2026-06-13 08:00 | 2026-06-14 09:00 | 3 |
| 2026-07 | 13.66 | 2026-07-03 06:15 | 2026-07-03 19:55 | 1 |
| 2026-08 | 57.73 | 2026-08-26 05:55 | 2026-08-28 15:39 | 33 |
| 2026-09 | 23.50 | 2026-09-10 21:45 | 2026-09-11 21:15 | 32 |
| 2026-10 | 27.50 | 2026-10-05 12:00 | 2026-10-06 15:30 | 1 |

Top 10 gaps overall:

| rank | gap h | start (UTC) | end (UTC) | created_in_gap |
|---|---|---|---|---|
| 1 | 133.67 | 2025-11-18 16:44 | 2025-11-24 06:24 | 145 |
| 2 | 57.73 | 2026-08-26 05:55 | 2026-08-28 15:39 | 33 |
| 3 | 30.58 | 2026-04-29 15:00 | 2026-04-30 21:35 | 15 |
| 4 | 27.50 | 2026-10-05 12:00 | 2026-10-06 15:30 | 1 |
| 5 | 25.00 | 2026-06-13 08:00 | 2026-06-14 09:00 | 3 |
| 6 | 23.50 | 2026-09-10 21:45 | 2026-09-11 21:15 | 32 |
| 7 | 17.67 | 2025-12-13 11:55 | 2025-12-14 05:35 | 2 |
| 8 | 16.83 | 2026-05-10 22:40 | 2026-05-11 15:30 | 1 |
| 9 | 15.25 | 2026-08-16 06:35 | 2026-08-16 21:50 | 1 |
| 10 | 15.08 | 2026-04-28 06:30 | 2026-04-28 21:35 | 1 |

## (d) Posts that would only appear after the window closed (closed weekly events since 2025-12)

late = posts with createdAt inside [start,end) and importedAt > end. frac = late / final count.

| event | window start | window end | final n | late n | frac late | max lag h in window |
|---|---|---|---|---|---|---|
| elon-musk-of-tweets-december-2-december-9 | 2025-12-02T17:00:00Z | 2025-12-09T17:00:00Z | 425 | 1 | 0.0024 | 0.89 |
| elon-musk-of-tweets-december-5-december-12 | 2025-12-05T17:00:00Z | 2025-12-12T17:00:00Z | 443 | 0 | 0.0000 | 0.89 |
| elon-musk-of-tweets-december-9-december-16 | 2025-12-09T17:00:00Z | 2025-12-16T17:00:00Z | 261 | 0 | 0.0000 | 1.48 |
| elon-musk-of-tweets-december-12-december-19 | 2025-12-12T17:00:00Z | 2025-12-19T17:00:00Z | 268 | 0 | 0.0000 | 1.48 |
| elon-musk-of-tweets-december-16-december-23 | 2025-12-16T17:00:00Z | 2025-12-23T17:00:00Z | 350 | 0 | 0.0000 | 0.09 |
| elon-musk-of-tweets-december-19-december-26 | 2025-12-19T17:00:00Z | 2025-12-26T17:00:00Z | 353 | 0 | 0.0000 | 0.09 |
| elon-musk-of-tweets-december-23-december-30 | 2025-12-23T17:00:00Z | 2025-12-30T17:00:00Z | 423 | 3 | 0.0071 | 0.09 |
| elon-musk-of-tweets-december-26-january-2 | 2025-12-26T17:00:00Z | 2026-01-02T17:00:00Z | 502 | 0 | 0.0000 | 0.09 |
| elon-musk-of-tweets-december-30-january-6 | 2025-12-30T17:00:00Z | 2026-01-06T17:00:00Z | 539 | 0 | 0.0000 | 0.09 |
| elon-musk-of-tweets-january-2-january-9 | 2026-01-02T17:00:00Z | 2026-01-09T17:00:00Z | 570 | 0 | 0.0000 | 0.10 |
| elon-musk-of-tweets-january-6-january-13 | 2026-01-06T17:00:00Z | 2026-01-13T17:00:00Z | 559 | 0 | 0.0000 | 0.10 |
| elon-musk-of-tweets-january-9-january-16 | 2026-01-09T17:00:00Z | 2026-01-16T17:00:00Z | 545 | 2 | 0.0037 | 0.75 |
| elon-musk-of-tweets-january-13-january-20 | 2026-01-13T17:00:00Z | 2026-01-20T17:00:00Z | 535 | 0 | 0.0000 | 0.75 |
| elon-musk-of-tweets-january-16-january-23 | 2026-01-16T17:00:00Z | 2026-01-23T17:00:00Z | 471 | 0 | 0.0000 | 0.09 |
| elon-musk-of-tweets-january-20-january-27 | 2026-01-20T17:00:00Z | 2026-01-27T17:00:00Z | 395 | 1 | 0.0025 | 0.09 |
| elon-musk-of-tweets-january-23-january-30 | 2026-01-23T17:00:00Z | 2026-01-30T17:00:00Z | 380 | 0 | 0.0000 | 7.98 |
| elon-musk-of-tweets-january-27-february-3 | 2026-01-27T17:00:00Z | 2026-02-03T17:00:00Z | 351 | 0 | 0.0000 | 7.98 |
| elon-musk-of-tweets-january-30-february-6 | 2026-01-30T17:00:00Z | 2026-02-06T17:00:00Z | 283 | 0 | 0.0000 | 0.09 |
| elon-musk-of-tweets-february-3-february-10 | 2026-02-03T17:00:00Z | 2026-02-10T17:00:00Z | 365 | 0 | 0.0000 | 0.09 |
| elon-musk-of-tweets-february-6-february-13 | 2026-02-06T17:00:00Z | 2026-02-13T17:00:00Z | 363 | 0 | 0.0000 | 0.09 |
| elon-musk-of-tweets-february-10-february-17 | 2026-02-10T17:00:00Z | 2026-02-17T17:00:00Z | 256 | 0 | 0.0000 | 0.39 |
| elon-musk-of-tweets-february-13-february-20 | 2026-02-13T17:00:00Z | 2026-02-20T17:00:00Z | 314 | 0 | 0.0000 | 0.39 |
| elon-musk-of-tweets-february-17-february-24 | 2026-02-17T17:00:00Z | 2026-02-24T17:00:00Z | 361 | 0 | 0.0000 | 0.11 |
| elon-musk-of-tweets-february-20-february-27 | 2026-02-20T17:00:00Z | 2026-02-27T17:00:00Z | 311 | 0 | 0.0000 | 0.09 |
| elon-musk-of-tweets-february-24-march-3 | 2026-02-24T17:00:00Z | 2026-03-03T17:00:00Z | 208 | 0 | 0.0000 | 0.09 |
| elon-musk-of-tweets-february-27-march-6 | 2026-02-27T17:00:00Z | 2026-03-06T17:00:00Z | 211 | 0 | 0.0000 | 0.09 |
| elon-musk-of-tweets-march-3-march-10 | 2026-03-03T17:00:00Z | 2026-03-10T16:00:00Z | 359 | 0 | 0.0000 | 0.13 |
| elon-musk-of-tweets-march-6-march-13 | 2026-03-06T17:00:00Z | 2026-03-13T16:00:00Z | 378 | 0 | 0.0000 | 0.13 |
| elon-musk-of-tweets-march-10-march-17 | 2026-03-10T16:00:00Z | 2026-03-17T16:00:00Z | 286 | 0 | 0.0000 | 0.09 |
| elon-musk-of-tweets-march-13-march-20 | 2026-03-13T16:00:00Z | 2026-03-20T16:00:00Z | 339 | 0 | 0.0000 | 0.20 |
| elon-musk-of-tweets-march-17-march-24 | 2026-03-17T16:00:00Z | 2026-03-24T16:00:00Z | 367 | 0 | 0.0000 | 0.20 |
| elon-musk-of-tweets-march-20-march-27 | 2026-03-20T16:00:00Z | 2026-03-27T16:00:00Z | 269 | 0 | 0.0000 | 0.09 |
| elon-musk-of-tweets-march-24-march-31 | 2026-03-24T16:00:00Z | 2026-03-31T16:00:00Z | 236 | 0 | 0.0000 | 0.15 |
| elon-musk-of-tweets-march-27-april-3 | 2026-03-27T16:00:00Z | 2026-04-03T16:00:00Z | 277 | 0 | 0.0000 | 0.15 |
| elon-musk-of-tweets-march-31-april-7 | 2026-03-31T16:00:00Z | 2026-04-07T16:00:00Z | 275 | 0 | 0.0000 | 0.09 |
| elon-musk-of-tweets-april-3-april-10 | 2026-04-03T16:00:00Z | 2026-04-10T16:00:00Z | 241 | 0 | 0.0000 | 0.08 |
| elon-musk-of-tweets-april-7-april-14 | 2026-04-07T16:00:00Z | 2026-04-14T16:00:00Z | 299 | 0 | 0.0000 | 0.08 |
| elon-musk-of-tweets-april-10-april-17 | 2026-04-10T16:00:00Z | 2026-04-17T16:00:00Z | 305 | 0 | 0.0000 | 0.49 |
| elon-musk-of-tweets-april-14-april-21 | 2026-04-14T16:00:00Z | 2026-04-21T16:00:00Z | 226 | 0 | 0.0000 | 0.49 |
| elon-musk-of-tweets-april-17-april-24 | 2026-04-17T16:00:00Z | 2026-04-24T16:00:00Z | 204 | 0 | 0.0000 | 0.08 |
| elon-musk-of-tweets-april-21-april-28 | 2026-04-21T16:00:00Z | 2026-04-28T16:00:00Z | 227 | 0 | 0.0000 | 0.08 |
| elon-musk-of-tweets-april-24-may-1 | 2026-04-24T16:00:00Z | 2026-05-01T16:00:00Z | 191 | 0 | 0.0000 | 16.07 |
| elon-musk-of-tweets-april-28-may-5 | 2026-04-28T16:00:00Z | 2026-05-05T16:00:00Z | 158 | 0 | 0.0000 | 16.07 |
| elon-musk-of-tweets-may-1-may-8 | 2026-05-01T16:00:00Z | 2026-05-08T16:00:00Z | 164 | 0 | 0.0000 | 0.08 |
| elon-musk-of-tweets-may-5-may-12 | 2026-05-05T16:00:00Z | 2026-05-12T16:00:00Z | 115 | 0 | 0.0000 | 0.07 |
| elon-musk-of-tweets-may-8-may-15 | 2026-05-08T16:00:00Z | 2026-05-15T16:00:00Z | 146 | 0 | 0.0000 | 0.07 |
| elon-musk-of-tweets-may-12-may-19 | 2026-05-12T16:00:00Z | 2026-05-19T16:00:00Z | 232 | 0 | 0.0000 | 0.08 |
| elon-musk-of-tweets-may-15-may-22 | 2026-05-15T16:00:00Z | 2026-05-22T16:00:00Z | 290 | 0 | 0.0000 | 0.08 |
| arch-elon-musk-of-tweets-may-19-may-26 | 2026-05-19T16:00:00Z | 2026-05-26T16:00:00Z | 260 | 1 | 0.0038 | 0.08 |
| elon-musk-of-tweets-may-19-may-26 | 2026-05-19T16:00:00Z | 2026-05-26T16:00:00Z | 260 | 1 | 0.0038 | 0.08 |
| elon-musk-of-tweets-may-22-may-29 | 2026-05-22T16:00:00Z | 2026-05-29T16:00:00Z | 182 | 0 | 0.0000 | 0.09 |
| elon-musk-of-tweets-may-26-june-2 | 2026-05-26T16:00:00Z | 2026-06-02T16:00:00Z | 173 | 0 | 0.0000 | 9.46 |
| elon-musk-of-tweets-may-29-june-5 | 2026-05-29T16:00:00Z | 2026-06-05T16:00:00Z | 192 | 0 | 0.0000 | 9.46 |
| elon-musk-of-tweets-june-2-june-9 | 2026-06-02T16:00:00Z | 2026-06-09T16:00:00Z | 222 | 0 | 0.0000 | 0.08 |
| elon-musk-of-tweets-june-5-june-12 | 2026-06-05T16:00:00Z | 2026-06-12T16:00:00Z | 236 | 1 | 0.0042 | 0.08 |
| elon-musk-of-tweets-june-9-june-16 | 2026-06-09T16:00:00Z | 2026-06-16T16:00:00Z | 204 | 0 | 0.0000 | 0.09 |
| elon-musk-of-tweets-june-12-june-19 | 2026-06-12T16:00:00Z | 2026-06-19T16:00:00Z | 196 | 0 | 0.0000 | 0.09 |
| elon-musk-of-tweets-june-16-june-23 | 2026-06-16T16:00:00Z | 2026-06-23T16:00:00Z | 210 | 0 | 0.0000 | 0.08 |
| elon-musk-of-tweets-june-19-june-26 | 2026-06-19T16:00:00Z | 2026-06-26T16:00:00Z | 240 | 0 | 0.0000 | 0.12 |
| elon-musk-of-tweets-june-23-june-30 | 2026-06-23T16:00:00Z | 2026-06-30T16:00:00Z | 258 | 0 | 0.0000 | 0.12 |
| elon-musk-of-tweets-june-26-july-3 | 2026-06-26T16:00:00Z | 2026-07-03T16:00:00Z | 188 | 0 | 0.0000 | 0.08 |
| elon-musk-of-tweets-june-30-july-7 | 2026-06-30T16:00:00Z | 2026-07-07T16:00:00Z | 123 | 2 | 0.0163 | 0.08 |
| elon-musk-of-tweets-july-3-july-10 | 2026-07-03T16:00:00Z | 2026-07-10T16:00:00Z | 187 | 0 | 0.0000 | 0.09 |
| elon-musk-of-tweets-july-7-july-14 | 2026-07-07T16:00:00Z | 2026-07-14T16:00:00Z | 195 | 0 | 0.0000 | 0.09 |
| elon-musk-of-tweets-july-10-july-17 | 2026-07-10T16:00:00Z | 2026-07-17T16:00:00Z | 160 | 0 | 0.0000 | 0.09 |
| elon-musk-of-tweets-july-14-july-21 | 2026-07-14T16:00:00Z | 2026-07-21T16:00:00Z | 158 | 0 | 0.0000 | 0.09 |
| elon-musk-of-tweets-july-17-july-24 | 2026-07-17T16:00:00Z | 2026-07-24T16:00:00Z | 207 | 0 | 0.0000 | 0.09 |
| elon-musk-of-tweets-july-21-july-28 | 2026-07-21T16:00:00Z | 2026-07-28T16:00:00Z | 281 | 0 | 0.0000 | 0.09 |
| elon-musk-of-tweets-july-24-july-31 | 2026-07-24T16:00:00Z | 2026-07-31T16:00:00Z | 270 | 0 | 0.0000 | 0.09 |
| elon-musk-of-tweets-july-28-august-4 | 2026-07-28T16:00:00Z | 2026-08-04T16:00:00Z | 223 | 0 | 0.0000 | 0.09 |
| elon-musk-of-tweets-july-31-august-7 | 2026-07-31T16:00:00Z | 2026-08-07T16:00:00Z | 187 | 0 | 0.0000 | 0.08 |
| elon-musk-of-tweets-august-4-august-11 | 2026-08-04T16:00:00Z | 2026-08-11T16:00:00Z | 170 | 0 | 0.0000 | 0.07 |
| elon-musk-of-tweets-august-7-august-14 | 2026-08-07T16:00:00Z | 2026-08-14T16:00:00Z | 185 | 0 | 0.0000 | 0.07 |
| elon-musk-of-tweets-august-11-august-18 | 2026-08-11T16:00:00Z | 2026-08-18T16:00:00Z | 160 | 0 | 0.0000 | 0.08 |
| elon-musk-of-tweets-august-14-august-21 | 2026-08-14T16:00:00Z | 2026-08-21T16:00:00Z | 253 | 0 | 0.0000 | 0.09 |
| elon-musk-of-tweets-august-18-august-25 | 2026-08-18T16:00:00Z | 2026-08-25T16:00:00Z | 325 | 0 | 0.0000 | 0.09 |
| elon-musk-of-tweets-august-21-august-28-2026 | 2026-08-21T16:00:00Z | 2026-08-28T16:00:00Z | 190 | 13 | 0.0684 | 46.09 |
| elon-musk-of-tweets-august-25-september-1-2026 | 2026-08-25T16:00:00Z | 2026-09-01T16:00:00Z | 174 | 0 | 0.0000 | 46.09 |
| elon-musk-of-tweets-august-28-september-4-2026 | 2026-08-28T16:00:00Z | 2026-09-04T16:00:00Z | 226 | 0 | 0.0000 | 0.11 |
| elon-musk-of-tweets-september-1-september-8-2026 | 2026-09-01T16:00:00Z | 2026-09-08T16:00:00Z | 209 | 1 | 0.0048 | 0.11 |
| elon-musk-of-tweets-september-4-september-11-2026 | 2026-09-04T16:00:00Z | 2026-09-11T16:00:00Z | 176 | 22 | 0.1250 | 21.16 |
| elon-musk-of-tweets-september-8-september-15-2026 | 2026-09-08T16:00:00Z | 2026-09-15T16:00:00Z | 187 | 0 | 0.0000 | 21.16 |
| elon-musk-of-tweets-september-11-september-18-2026 | 2026-09-11T16:00:00Z | 2026-09-18T16:00:00Z | 204 | 0 | 0.0000 | 5.15 |
| elon-musk-of-tweets-september-15-september-22-2026 | 2026-09-15T16:00:00Z | 2026-09-22T16:00:00Z | 222 | 0 | 0.0000 | 0.16 |
| elon-musk-of-tweets-september-18-september-25-2026 | 2026-09-18T16:00:00Z | 2026-09-25T16:00:00Z | 200 | 0 | 0.0000 | 0.16 |
| elon-musk-of-tweets-september-22-september-29-2026 | 2026-09-22T16:00:00Z | 2026-09-29T16:00:00Z | 182 | 0 | 0.0000 | 3.60 |
| elon-musk-of-tweets-september-25-october-2-2026 | 2026-09-25T16:00:00Z | 2026-10-02T16:00:00Z | 222 | 0 | 0.0000 | 3.60 |
| elon-musk-of-tweets-september-29-october-6-2026 | 2026-09-29T16:00:00Z | 2026-10-06T16:00:00Z | 215 | 3 | 0.0140 | 50.79 |
| elon-musk-of-tweets-october-2-october-9-2026 | 2026-10-02T16:00:00Z | 2026-10-09T16:00:00Z | 326 | 0 | 0.0000 | 50.79 |

