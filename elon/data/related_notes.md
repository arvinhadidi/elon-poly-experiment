# Related count-market inventory: notes

Generated 2026-10-10 17:32 UTC by elon/pull_related.py (read-only, no orders).

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
- elon-musk-of-tweets-october-6-october-13-2026: cheap buckets=13, depth within 2c=$2,584, median touch=$12
- elon-musk-of-tweets-october-9-october-16-2026: cheap buckets=24, depth within 2c=$3,423, median touch=$13
- elon-musk-of-tweets-october-10-october-12-2026: cheap buckets=10, depth within 2c=$1,884, median touch=$18
- elon-musk-of-tweets-october-12-october-14-2026: cheap buckets=10, depth within 2c=$94, median touch=$2
- elon-musk-of-tweets-october-2026: cheap buckets=24, depth within 2c=$632, median touch=$1
- what-will-elon-post-this-week-october-5-october-11: cheap buckets=1, depth within 2c=$3, median touch=$2
- donald-trump-of-truth-social-posts-october-6-october-13-2026: cheap buckets=9, depth within 2c=$507, median touch=$2
- donald-trump-of-truth-social-posts-october-9-october-16-2026: cheap buckets=10, depth within 2c=$606, median touch=$10
- white-house-of-tweets-october-6-october-13-2026: cheap buckets=4, depth within 2c=$30, median touch=$0
- white-house-of-tweets-october-9-october-16-2026: cheap buckets=9, depth within 2c=$72, median touch=$0
- khamenei-of-tweets-october-6-october-13-2026: cheap buckets=11, depth within 2c=$33, median touch=$0
- khamenei-of-tweets-october-9-october-16-2026: cheap buckets=11, depth within 2c=$33, median touch=$1
- of-views-of-next-mrbeast-video-on-week-1-20261003: cheap buckets=6, depth within 2c=$237, median touch=$15
- of-views-of-next-mrbeast-video-on-week-1-higher-brackets-20261004: cheap buckets=5, depth within 2c=$195, median touch=$1
- of-views-of-next-mrbeast-gaming-video-on-day-1-20261010: cheap buckets=7, depth within 2c=$88, median touch=$3
- of-views-of-mrbeast-gaming-video-week-1-20261010: cheap buckets=8, depth within 2c=$259, median touch=$3
- will-mrbeast-hit-million-subscribers-by-october-31-2026: cheap buckets=1, depth within 2c=$4, median touch=$4
- will-mrbeast-hit-billion-views-by-october-31-2026: cheap buckets=1, depth within 2c=$503, median touch=$3
- what-will-trump-say-this-week-october-5-october-11-20261011: cheap buckets=1, depth within 2c=$18, median touch=$17
- ted-cruz-of-tweets-october-6-october-13-2026: cheap buckets=4, depth within 2c=$17, median touch=$3
- ted-cruz-of-tweets-october-9-october-16-2026: cheap buckets=8, depth within 2c=$76, median touch=$7
- cz-binance-of-tweets-october-6-october-13-2026: cheap buckets=10, depth within 2c=$94, median touch=$1
- cz-binance-of-tweets-october-9-october-16-2026: cheap buckets=9, depth within 2c=$77, median touch=$7
- nyc-mayor-of-tweets-october-6-october-13-2026: cheap buckets=10, depth within 2c=$46, median touch=$1
- nyc-mayor-of-tweets-october-9-october-16-2026: cheap buckets=10, depth within 2c=$22, median touch=$0
- zelenskyy-of-tweets-october-6-october-13-2026: cheap buckets=10, depth within 2c=$125, median touch=$6
- zelenskyy-of-tweets-october-9-october-16-2026: cheap buckets=10, depth within 2c=$302, median touch=$1
- what-will-mrbeast-say-during-his-next-gaming-youtube-video-20261006222126545: cheap buckets=10, depth within 2c=$238, median touch=$0
- what-will-dominos-say-during-their-next-earnings-call-october-13: cheap buckets=6, depth within 2c=$74, median touch=$9
- what-will-jpmorgan-say-during-their-next-earnings-call-october-13: cheap buckets=5, depth within 2c=$77, median touch=$16
- how-many-views-will-the-1-movie-on-netflix-have-this-week-negrisk-20261013: cheap buckets=6, depth within 2c=$123, median touch=$8
- how-many-views-will-the-1-show-on-netflix-have-this-week-negrisk-20261013: cheap buckets=5, depth within 2c=$107, median touch=$3
- what-companies-will-trump-mention-in-october: cheap buckets=4, depth within 2c=$125, median touch=$30
- will-elon-musk-tweet-about-hyperliquid-by: cheap buckets=3, depth within 2c=$316, median touch=$68

## Kalshi (signal only, cannot trade)
- Kalshi series listed: 14935; title/ticker matches: 582
  - KXEARNINGSMENTIONALIBABA | alibaba earnings mention | markets=0 status={} contracts_volume=0
  - KXCUOMOMENTION | Cuomo Mention | markets=0 status={} contracts_volume=0
  - KXWCMENTION | World Cup Mentions | markets=32 status={'closed': 32} contracts_volume=0
  - KXYTVIEWSW | Highest daily view count this week | markets=1000 status={'active': 244, 'finalized': 756} contracts_volume=0
  - KXNYCMAYORDEBATEMENTION | NYC Mayoral Debate | markets=0 status={} contracts_volume=0
  - KXSLOVAKREF | Slovak Referendum on Lifelong Payments for Leaders | markets=0 status={} contracts_volume=0
  - KXELONDEFUND | Elon defund | markets=0 status={} contracts_volume=0
  - KXEARNINGSMENTIONROST | Ross Stores Earnings Call | markets=14 status={'finalized': 14} contracts_volume=0
  - KXYTVIEWSD | daily view count | markets=1000 status={'finalized': 1000} contracts_volume=0
  - KXEARNINGSMENTIONTOL | Toll Brothers Earnings Call | markets=14 status={'finalized': 14} contracts_volume=0
  - KXLATENIGHTMENTION | Late Night Mention | markets=0 status={} contracts_volume=0
  - KXBAMENTION | Boeing Mention | markets=15 status={'finalized': 15} contracts_volume=0
  - KXIMFTWEETS | IMF tweets | markets=42 status={'finalized': 42} contracts_volume=0
  - KXTRUMPMENTIONS | Trump Mentions | markets=0 status={} contracts_volume=0
  - KXTRUMPTOPIC | Trump Topic Mention | markets=0 status={} contracts_volume=0
  - KXZAKARIAMENTION | Fareed Zakaria | markets=0 status={} contracts_volume=0
  - KXMUSKUNFOLLOWDJT | Musk unfollow Trump | markets=0 status={} contracts_volume=0
  - KXJOHNSONMENTION | Mike Johnson Mention | markets=28 status={'finalized': 28} contracts_volume=0
  - KXPARTYSUPPORTMUSKD | Musk Democrat | markets=0 status={} contracts_volume=0
  - KXEARNINGSMENTIONCELH | Celsius Earnings | markets=15 status={'finalized': 15} contracts_volume=0
  - KXPRESENDORSEMUSKD | Musk endorses Democrat for President | markets=1 status={'active': 1} contracts_volume=0
  - KXEARNINGSMENTIONTTWO | Take Two Earnings Call | markets=12 status={'finalized': 12} contracts_volume=0
  - KXEARNINGSMENTIONCRCL | Circle Earnings | markets=0 status={} contracts_volume=0
  - KXMENTIONEARNFDX | FedEx | markets=0 status={} contracts_volume=0
  - KXEARNINGSMENTIONCVNA | Carvana | markets=13 status={'active': 13} contracts_volume=0
  - KXEARNINGSMENTIONUBER | uber earnings mention | markets=20 status={'finalized': 20} contracts_volume=0
  - KXNYCMDEBMENTION | NYC Mayor debate | markets=0 status={} contracts_volume=0
  - KXALTMANMENTION | Sam Altman Mention | markets=17 status={'finalized': 17} contracts_volume=0
  - KXNASCARMENTION | Nascar announcers | markets=0 status={} contracts_volume=0
  - KXMUSKCABLE | Musk Cable company | markets=0 status={} contracts_volume=0
  - KXEARNINGSMENTIONRACE | Ferrari Earnings Call | markets=0 status={} contracts_volume=0
  - KXSASMITH | Stephen A Smith Mention | markets=0 status={} contracts_volume=0
  - KXSTARMERMENTION | Starmer mentions | markets=0 status={} contracts_volume=0
  - KXEARNINGSMENTIONYETI | Yeti earnings call | markets=10 status={'finalized': 10} contracts_volume=0
  - KXYCAITOGETHER | Altman and Musk on stage together | markets=0 status={} contracts_volume=0
  - KXAMODEIMENTION | Amodei  | markets=0 status={} contracts_volume=0
  - KXTAXAPP | Elon tax app | markets=0 status={} contracts_volume=0
  - KXEARNINGSMENTIONTOST | Toast, Inc. | markets=14 status={'finalized': 14} contracts_volume=0
  - KXVZMENTION | Verizon Mention | markets=14 status={'finalized': 14} contracts_volume=0
  - KXSCOTUSMENTION | SCOTUS Mention | markets=0 status={} contracts_volume=0

## Manifold and other venues
- Manifold search: 617 unique markets across 9 terms; 537 match elon/musk/tweet/post/truth/views/mention/mrbeast.
  - Will this Yudkowsky tweet on AI video generation hold up in 2024? | vol=1,107,178 resolved=True close=2024-12-31 | https://manifold.markets/GeorgeVii/will-this-yudkowsky-tweet-hold-up-2
  - Donald Trump's return on Twitter:  Will @realDonaldTrump tweet in 2023? | vol=754,995 resolved=True close=2023-08-25 | https://manifold.markets/itsTomekK/will-realdonaldtrump-tweet-in-2023
  - Will this Yudkowsky tweet hold up? | vol=672,861 resolved=True close=2026-05-12 | https://manifold.markets/journcy/will-this-yudkowsky-tweet-hold-up
  - Will Eliezer Yudkowsky write a tweet containing the word "rationalussy" by the end of 2023? | vol=639,173 resolved=True close=2024-01-02 | https://manifold.markets/SG/will-eliezer-yudkowsky-write-a-twee
  - Donald Trump's return on Twitter: Will @realDonaldTrump tweet in 2022? | vol=627,573 resolved=True close=2022-12-31 | https://manifold.markets/itsTomekK/will-realdonaldtrump-tweet-in-2022
  - 21. Will Donald Trump make at least one tweet in 2023? | vol=461,562 resolved=True close=2023-08-25 | https://manifold.markets/ACXBot/21-will-donald-trump-make-at-least
  - Good Tweet or Bad Tweet? Which controversial posts will Manifold think are a "Good Take" this week? | vol=400,669 resolved=True close=2024-11-02 | https://manifold.markets/Joshua/good-tweet-or-bad-tweet-which-contr
  - Will Donald Trump tweet once in 2023? | vol=261,649 resolved=True close=2023-08-26 | https://manifold.markets/CP/will-donald-trump-tweet-once-in-202
  - Which Tweet will win the "Worst Tweets of 2023" bracket? | vol=141,883 resolved=True close=2023-12-17 | https://manifold.markets/jgyou/which-tweet-will-win-the-worst-twee
  - Will @inerati tweet the word "rationalussy" (and keep the tweet up for at least a day) by the end of August leagues? | vol=138,604 resolved=True close=2023-09-02 | https://manifold.markets/Sketchy/will-inerati-tweet-the-word-rationa
  - Will Sam Altman's next Tweet be an announcement of GPT-5? | vol=123,557 resolved=True close=2024-03-17 | https://manifold.markets/jim/will-sam-altmans-next-tweet-be-an-a
  - Will Elon Musk tweet about Manifold in 2023? | vol=120,105 resolved=True close=2024-01-01 | https://manifold.markets/SG/will-elon-musk-tweet-about-manifold-5df47cac45fe
  - Will @realDonaldTrump tweet in 2024? | vol=117,987 resolved=True close=2024-08-13 | https://manifold.markets/justifieduseofFallibilism/will-realdonaldtrump-tweet-in-2024
  - Will Eliezer Yudkowsky be mentioned or quoted in the White House briefing room within 5 years? | vol=115,369 resolved=False close=2029-06-01 | https://manifold.markets/ZviMowshowitz/will-eliezer-yudkowsky-be-mentioned
  - Will David Pakman have more YouTube video views in February compared to January? | vol=111,615 resolved=True close=2025-03-01 | https://manifold.markets/SirSalty/will-david-pakman-have-more-youtube
  - Will xAI open source Grok within a month, before the end of Apr 11? (Musk tweeted) | vol=111,263 resolved=True close=2024-03-17 | https://manifold.markets/jacksonpolack/will-xai-open-source-grok-within-a
  - What topics or who will Elon Musk tweet about on X before May 1st? | vol=108,498 resolved=True close=2024-05-02 | https://manifold.markets/Lion/what-topics-or-who-will-elon-musk-t
  - Will any of the videos uploaded to Mark Rober's YouTube channel in Mar 2024 surpass 30M views? | vol=106,988 resolved=True close=2024-04-01 | https://manifold.markets/AmmonLam/will-any-of-the-videos-uploaded-to-b68e48553ae1
  - Will xAI open source Grok within a week, before the end of March 17? (Musk tweeted) | vol=102,438 resolved=True close=2024-03-17 | https://manifold.markets/jacksonpolack/musk-this-week-xai-will-open-source
  - Will any of the videos uploaded to Mr Beast's YouTube channel in Feb 2024 surpass 170M views? | vol=96,966 resolved=True close=2024-03-01 | https://manifold.markets/AmmonLam/will-any-of-the-videos-uploaded-to-376da6358d53
  - Will any of the videos uploaded to Rational Animation's YouTube channel in Feb 2024 surpass 200k views? | vol=93,447 resolved=True close=2024-03-01 | https://manifold.markets/AmmonLam/will-any-of-the-videos-uploaded-to-a029fb738be8
  - Will any of the videos uploaded to Mr Beast's YouTube channel in Feb 2024 surpass 150M views? | vol=93,365 resolved=True close=2024-03-01 | https://manifold.markets/AmmonLam/will-any-of-the-videos-uploaded-to-74daff438d86
  - Will Donald Trump make at least three tweets in 2023? | vol=92,966 resolved=True close=2023-12-31 | https://manifold.markets/kian_spire/will-donald-trump-make-at-least-thr
  - Will any of the videos uploaded to Destiny's YouTube channel in Mar 2024 surpass 800k views? | vol=72,300 resolved=True close=2024-03-29 | https://manifold.markets/AmmonLam/will-any-of-the-videos-uploaded-to-8f66bdb4ccde
  - Will Trump tweet again before Sept 1st, 2023? | vol=70,636 resolved=True close=2023-09-01 | https://manifold.markets/ken/will-trump-tweet-again-before-sept

Runtime: 160s
