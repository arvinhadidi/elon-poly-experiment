# Related count-market inventory: notes

Generated 2026-10-10 17:47 UTC by elon/pull_related.py (read-only, no orders).

## Polymarket method
- Families = Gamma series whose titles are count-style (>=50% of event titles match MEDIA_RE), plus
  series-less events grouped by normalised title (only if >=2 hits or a '#'/'how many' title).
- Series-less families come only from public-search (5 hits per query) and the open-event sweep, so
  their history is incomplete.
- Window: xtracker tracking dates when the event is tracked; otherwise the ET window parsed from the
  description; otherwise Gamma startDate/endDate (UTC).
- Live depth: up to 2 open events per family (started, soonest end). Depth = sum(size*price) of asks within
  2c of the best ask, over buckets with best ask <= 0.50. Touch = size*price at the best ask.
- data_free = y only when the xtracker posts endpoint returned posts for the last 30 days (free, no key).

## Open-event depth detail
- elon-musk-of-tweets-october-6-october-13-2026: cheap buckets=13, depth within 2c=$2,797, median touch=$18
- elon-musk-of-tweets-october-9-october-16-2026: cheap buckets=24, depth within 2c=$1,235, median touch=$9
- elon-musk-of-tweets-october-10-october-12-2026: cheap buckets=10, depth within 2c=$2,037, median touch=$10
- elon-musk-of-tweets-october-12-october-14-2026: cheap buckets=10, depth within 2c=$149, median touch=$2
- elon-musk-of-tweets-october-2026: cheap buckets=24, depth within 2c=$659, median touch=$1
- what-will-elon-post-this-week-october-5-october-11: cheap buckets=1, depth within 2c=$3, median touch=$2
- donald-trump-of-truth-social-posts-october-6-october-13-2026: cheap buckets=9, depth within 2c=$544, median touch=$2
- donald-trump-of-truth-social-posts-october-9-october-16-2026: cheap buckets=10, depth within 2c=$701, median touch=$16
- white-house-of-tweets-october-6-october-13-2026: cheap buckets=4, depth within 2c=$30, median touch=$0
- white-house-of-tweets-october-9-october-16-2026: cheap buckets=9, depth within 2c=$72, median touch=$0
- khamenei-of-tweets-october-6-october-13-2026: cheap buckets=11, depth within 2c=$33, median touch=$0
- khamenei-of-tweets-october-9-october-16-2026: cheap buckets=11, depth within 2c=$33, median touch=$1
- of-views-of-next-mrbeast-video-on-week-1-20261003: cheap buckets=6, depth within 2c=$235, median touch=$15
- of-views-of-next-mrbeast-video-on-week-1-higher-brackets-20261004: cheap buckets=5, depth within 2c=$216, median touch=$1
- of-views-of-next-mrbeast-gaming-video-on-day-1-20261010: cheap buckets=7, depth within 2c=$495, median touch=$10
- of-views-of-mrbeast-gaming-video-week-1-20261010: cheap buckets=8, depth within 2c=$268, median touch=$5
- will-mrbeast-hit-million-subscribers-by-october-31-2026: cheap buckets=1, depth within 2c=$4, median touch=$4
- will-mrbeast-hit-billion-views-by-october-31-2026: cheap buckets=1, depth within 2c=$503, median touch=$3
- what-will-trump-say-this-week-october-5-october-11-20261011: cheap buckets=1, depth within 2c=$18, median touch=$17
- ted-cruz-of-tweets-october-6-october-13-2026: cheap buckets=4, depth within 2c=$15, median touch=$3
- ted-cruz-of-tweets-october-9-october-16-2026: cheap buckets=8, depth within 2c=$76, median touch=$7
- cz-binance-of-tweets-october-6-october-13-2026: cheap buckets=10, depth within 2c=$99, median touch=$1
- cz-binance-of-tweets-october-9-october-16-2026: cheap buckets=9, depth within 2c=$77, median touch=$7
- nyc-mayor-of-tweets-october-6-october-13-2026: cheap buckets=10, depth within 2c=$45, median touch=$1
- nyc-mayor-of-tweets-october-9-october-16-2026: cheap buckets=10, depth within 2c=$22, median touch=$0
- zelenskyy-of-tweets-october-6-october-13-2026: cheap buckets=10, depth within 2c=$118, median touch=$3
- zelenskyy-of-tweets-october-9-october-16-2026: cheap buckets=10, depth within 2c=$263, median touch=$1
- what-will-mrbeast-say-during-his-next-gaming-youtube-video-20261006222126545: cheap buckets=10, depth within 2c=$353, median touch=$0
- what-will-dominos-say-during-their-next-earnings-call-october-13: cheap buckets=6, depth within 2c=$74, median touch=$9
- what-will-jpmorgan-say-during-their-next-earnings-call-october-13: cheap buckets=5, depth within 2c=$77, median touch=$16
- how-many-views-will-the-1-movie-on-netflix-have-this-week-negrisk-20261013: cheap buckets=6, depth within 2c=$123, median touch=$8
- how-many-views-will-the-1-show-on-netflix-have-this-week-negrisk-20261013: cheap buckets=5, depth within 2c=$40, median touch=$5
- what-companies-will-trump-mention-in-october: cheap buckets=4, depth within 2c=$123, median touch=$30
- will-elon-musk-tweet-about-hyperliquid-by: cheap buckets=3, depth within 2c=$317, median touch=$70

## Kalshi (signal only, cannot trade)
- Kalshi series listed: 14,935; title/ticker matches (tweet/post/truth/views/mention/MrBeast/YouTube/Elon): 254
- Kalshi table (sorted by contract volume; events_90d = events with close time in last 90 days):

| ticker | title | frequency | markets | events | events_90d | contracts_volume | status |
|---|---|---|---|---|---|---|---|
| KXWORLDNEWSMENTION | World News Mention | one_off | 757 | 48 | 48 | 6,082,256 | finalized:757 |
| KXTRUMPMENTIONB | Trump Mention B | one_off | 423 | 15 | 15 | 5,574,845 | finalized:423 |
| KXTRUTHSOCIAL | Number of Trump Truth Social posts this week? | weekly | 110 | 11 | 11 | 2,789,604 | active:10,finalized:90,initialized:10 |
| KXYTVIEWSHIGH | highest daily views in time period | monthly | 573 | 40 | 40 | 2,277,349 | active:104,finalized:469 |
| KXYTVIEWSW | Highest daily view count this week | weekly | 1000 | 66 | 66 | 2,044,194 | active:244,finalized:756 |
| KXTRUMPSAYCOMPANY | Will Trump mention company | one_off | 129 | 3 | 3 | 1,200,910 | active:41,finalized:88 |
| KXFEDMENTION | Fed mention | custom | 96 | 2 | 2 | 814,648 | active:47,finalized:49 |
| KXPSAKIMENTION | Jen Psaki Mention | one_off | 200 | 15 | 14 | 679,328 | closed:11,finalized:189 |
| KXHEARINGMENTION | Hearing Mention | one_off | 49 | 3 | 3 | 614,816 | finalized:49 |
| KXCARNEYMENTION | Carney Mention | one_off | 65 | 4 | 4 | 573,469 | closed:16,finalized:49 |
| KXNETFLIXTOPVIEWSTV | NETFLIX TOP SHOW VIEW COUNT | one_off | 121 | 11 | 11 | 568,966 | active:11,finalized:110 |
| KXNETFLIXTOPVIEWSMOVIE | NETFLIX TOP MOVIE VIEW COUNT | one_off | 121 | 11 | 11 | 527,641 | active:11,finalized:110 |
| KXDEBATEMENTION | Debate Mentions | one_off | 242 | 12 | 12 | 488,077 | active:42,finalized:200 |
| KXSECPRESSMENTION | Sec Press mentions | custom | 45 | 2 | 1 | 478,058 | closed:15,finalized:30 |
| KXMELANIAMENTION | Melania Mention | one_off | 55 | 4 | 4 | 381,802 | finalized:55 |
| KXFNSMENTION | Fox News Sunday Mention | one_off | 90 | 6 | 6 | 364,655 | finalized:90 |
| KXMRBEASTMENTION | What Will Mr Beast say in his next video | one_off | 13 | 1 | 1 | 272,222 | finalized:13 |
| KXWARSHMENTION | Kevin Warsh Mention | one_off | 29 | 1 | 1 | 269,656 | finalized:29 |
| KXEARNINGSMENTIONNVDA | NVDA Earnings Mention | one_off | 38 | 2 | 2 | 262,856 | active:19,finalized:19 |
| KXFOXSATMENTION | Saturday in America Mention | one_off | 44 | 3 | 3 | 177,889 | finalized:44 |
| KXYTTOPSONGW | youtube weekly top songs | one_off | 166 | 11 | 11 | 155,392 | closed:15,finalized:136,initialized:15 |
| KXTRUTHSOCIALD | Number of Trump Truth Social posts today? | one_off | 80 | 10 | 10 | 153,278 | active:8,finalized:72 |
| KXNETANYAHUMENTION | Netanyahu Mention | one_off | 36 | 2 | 2 | 146,456 | finalized:36 |
| KXWALLERMENTION | Waller Mention | one_off | 48 | 3 | 3 | 144,656 | finalized:48 |
| KXMUSKNW | Elon Musk net worth on [date] | monthly | 49 | 4 | 4 | 136,620 | active:21,finalized:28 |
| KXELONMENTION | Elon Mention | one_off | 18 | 1 | 1 | 136,422 | finalized:18 |
| KXBOWMANMENTION | Michelle Bowman Mention | one_off | 43 | 3 | 3 | 123,212 | finalized:43 |
| KXELONMARS | Elon Mars | custom | 1 | 1 | 1 | 119,806 | active:1 |
| KXEARNINGSMENTIONUBER | uber earnings mention | one_off | 20 | 1 | 1 | 111,570 | finalized:20 |
| KXZELENSKYYMENTION | Zelenskyy Mention | one_off | 15 | 1 | 1 | 103,106 | finalized:15 |
| KXKHANNAMENTION | Ro Khanna Mention | one_off | 58 | 4 | 4 | 102,658 | finalized:58 |
| KXTRUMPSAYCOUNTRY | Will Trump mention country | one_off | 81 | 2 | 2 | 92,058 | active:25,finalized:56 |
| KXAOCMENTION | AOC Mention | one_off | 34 | 2 | 2 | 89,674 | finalized:34 |
| KXBURNHAMMENTION | Andy Burnham mention | one_off | 55 | 4 | 4 | 83,687 | active:15,finalized:40 |
| KXTBLAMENTION | Todd Blanche mentions | one_off | 36 | 2 | 2 | 66,094 | finalized:36 |
| KXTSLAMENTION | Tesla Mention | one_off | 17 | 1 | 1 | 64,873 | finalized:17 |
| KXJENSENMENTION | Jensen Mention | one_off | 20 | 1 | 1 | 61,337 | finalized:20 |
| KXJOHNSONMENTION | Mike Johnson Mention | one_off | 28 | 2 | 2 | 56,648 | finalized:28 |
| KXSPOTMENTION | Spotify Mention | one_off | 17 | 1 | 1 | 50,436 | finalized:17 |
| KXWMTMENTION | Walmart Mention | one_off | 15 | 1 | 1 | 46,294 | finalized:15 |
| KXEARNINGSMENTIONAAPL | Apple earnings mention | one_off | 17 | 1 | 1 | 46,244 | active:17 |
| KXEARNINGSMENTIONAMZN | Amazon earnings mention | one_off | 22 | 1 | 1 | 45,164 | active:22 |
| KXRDDTMENTION | Reddit Mention | one_off | 17 | 1 | 1 | 44,533 | finalized:17 |
| KXBARRMENTION | Barr Mention | one_off | 31 | 2 | 2 | 43,403 | finalized:31 |
| KXDROZMENTION | Dr Oz Mention | one_off | 27 | 2 | 2 | 42,690 | finalized:27 |
| KXNVDAMENTION | NVIDIA Mention | one_off | 44 | 2 | 2 | 40,253 | active:23,finalized:21 |
| KXGOOGLMENTION | Google Mention | one_off | 16 | 1 | 1 | 39,437 | finalized:16 |
| KXEARNINGSMENTIONBAC | Bank of America Earnings Mention | one_off | 15 | 1 | 1 | 36,770 | active:15 |
| KXIMFTWEETS | IMF tweets | weekly | 42 | 7 | 7 | 36,001 | finalized:42 |
| KXBAMENTION | Boeing Mention | one_off | 15 | 1 | 1 | 35,600 | finalized:15 |
| KXABNBMENTION | Airbnb Mention | one_off | 15 | 1 | 1 | 34,020 | finalized:15 |
| KXYTUBESUBSBEAST | YouTube subs Beast | custom | 2 | 2 | 2 | 32,904 | active:2 |
| KXFIGMENTION | Figma Mention | one_off | 13 | 1 | 1 | 31,492 | finalized:13 |
| KXALUNMENTION | Anna Paulina Luna mentions | one_off | 14 | 1 | 1 | 30,448 | finalized:14 |
| KXVZMENTION | Verizon Mention | one_off | 14 | 1 | 1 | 30,424 | finalized:14 |
| KXWDAYMENTION | Workday Mention | one_off | 14 | 1 | 1 | 29,611 | active:14 |
| KXEARNINGSMENTIONUAL | United Airlines Earnings Mention | one_off | 15 | 1 | 1 | 27,404 | active:15 |
| KXACTORELONMUSK | ELON MUSK IN WHAT MOVIE | one_off | 1 | 1 | 1 | 27,257 | active:1 |
| KXSPCXMENTION | SpaceX Mention | one_off | 22 | 1 | 1 | 26,961 | finalized:22 |
| KXMCDMENTION | McDonald's Mention | one_off | 17 | 1 | 1 | 24,715 | finalized:17 |

## Manifold and other venues
- Manifold search: 794 unique markets across 11 terms; 24 are count-style (how many / # of / surpass / N tweets) about Elon, Trump, MrBeast, Zelenskyy, Khamenei, WH, Cruz, NYC Mayor, CZ or Tate.
  - Will any of the videos uploaded to Mr Beast's YouTube channel in Feb 2024 surpass 170M views? | vol=96,966 resolved=True close=2024-03-01 | https://manifold.markets/AmmonLam/will-any-of-the-videos-uploaded-to-376da6358d53
  - Will any of the videos uploaded to Mr Beast's YouTube channel in Feb 2024 surpass 150M views? | vol=93,365 resolved=True close=2024-03-01 | https://manifold.markets/AmmonLam/will-any-of-the-videos-uploaded-to-74daff438d86
  - Will Donald Trump make at least three tweets in 2023? | vol=92,966 resolved=True close=2023-12-31 | https://manifold.markets/kian_spire/will-donald-trump-make-at-least-thr
  - If MrBeast posts 4 full videos on twitter before the end of June 2024, how many Tweet "views" will the fourth get? | vol=12,229 resolved=True close=2024-02-26 | https://manifold.markets/jacksonpolack/if-mrbeast-posts-4-full-videos-on-t
  - How many YouTube views will Don Lemon's interview with Elon Musk receive within 1 week?🎙️📈 | vol=11,464 resolved=True close=2024-03-24 | https://manifold.markets/kanha/how-many-youtube-views-will-don-lem
  - Will Elon Musk successfully defeat at least 5 Republicans in 2026? | vol=11,215 resolved=False close=2026-11-11 | https://manifold.markets/nikki/will-elon-musk-successfully-defeat
  - # of views of next MrBeast video on day 1? [Polymarket] | vol=10,979 resolved=True close=2025-08-31 | https://manifold.markets/bag3lfan/-of-views-of-next-mrbeast-video-on-tzRAcSus5E
  - Will Donald Trump (@realDonaldTrump) post at least 1 time on X/Twitter in 2024? | vol=8,854 resolved=True close=2024-08-12 | https://manifold.markets/kurt/will-donald-trump-realdonaldtrump-p
  - Elon Musk # of tweets Feb 28 - Mar 7? | vol=6,093 resolved=True close=2025-03-08 | https://manifold.markets/MaxZORuL/elon-musk-of-tweets-feb-28-mar-7
  - How many people will repost this tweet by Mr. Beast, at the end of 72 hours? | vol=5,979 resolved=True close=2024-01-25 | https://manifold.markets/Tetraspace/how-many-people-will-repost-this-tw
  - Will MrBeast surpass 37,500,000,000 total views by the end of 2023? | vol=4,609 resolved=True close=2023-11-27 | https://manifold.markets/NickDaTick/will-mrbeast-surpass-37500000000-to
  - how many people will Donald Trump insult in his July 4th social post(s)? [short fuse] | vol=3,641 resolved=True close=2025-07-04 | https://manifold.markets/shankypanky/how-many-people-will-donald-trump-i
  - How many times will Donald Trump tweet (post on X) before November 5, 2024? | vol=3,030 resolved=True close=2024-09-07 | https://manifold.markets/mikeangelo/how-many-times-will-donald-trump-tw
  - # of views of next MrBeast video on day 1? [Polymarket] | vol=2,788 resolved=True close=2025-08-16 | https://manifold.markets/bag3lfan/-of-views-of-next-mrbeast-video-on
  - Will any of the videos uploaded to Mr Beast's YouTube channel in Apr 2024 surpass 150M views? | vol=2,653 resolved=True close=2024-05-01 | https://manifold.markets/AmmonLam/will-any-of-the-videos-uploaded-to-aabc94c2b989

Runtime: 248s
