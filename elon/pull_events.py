"""Pull all Polymarket Elon Musk tweet-count events (resolved + live) with bucket markets.

Read-only: public Gamma / xtracker endpoints only. Never places orders.
Run with cwd = elon/.
Outputs:
  data/events.csv          one row per bucket market
  data/events_summary.csv  one row per event
  data/series_found.json   discovered series
"""
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import get, parse_json_field, GAMMA, XT  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)
ET = ZoneInfo("America/New_York")
UTC = timezone.utc

SEED_SERIES = ["10000", "10816", "10181"]  # elon-tweets, elon-tweets-48h, elon-tweet-daily (monthly content)
TWEET_RE = re.compile(r"tweet|post", re.I)
ELON_RE = re.compile(r"elon", re.I)
ORPHAN_SLUG_PREFIXES = ("elon-musk-of-tweets", "of-elon-musk-tweets", "how-many-times-will-elon-musk-tweet",
                        "elon-musk-number-of-tweets")


def paginate(url, params):
    out, off = [], 0
    while True:
        p = dict(params, limit=100, offset=off)
        page = get(url, p)
        if not page:
            break
        out.extend(page)
        if len(page) < 100 and off > 0 and False:
            break
        off += 100
    return out


def is_tweet_count_title(t):
    return bool(ELON_RE.search(t or "")) and bool(re.search(r"tweet", t or "", re.I))


# ---------- 1. Discover series ----------
series_info = {}   # id -> dict
events_by_id = {}  # id -> event (dedupe)


def add_events(evs, origin_series=None):
    for e in evs:
        events_by_id.setdefault(e["id"], e)


def ensure_series(sid, source):
    if sid in series_info:
        series_info[sid]["discovered_via"].add(source)
        return
    try:
        s = get(f"{GAMMA}/series/{sid}")
    except Exception as ex:  # fall back to list lookup
        s = {"id": sid, "error": str(ex)}
    series_info[sid] = {
        "id": str(sid),
        "slug": s.get("slug"),
        "title": s.get("title"),
        "recurrence": s.get("recurrence"),
        "active": s.get("active"),
        "closed": s.get("closed"),
        "discovered_via": {source},
    }


# 1a. Gamma series-list scan, filtering titles containing elon/tweet
all_series = {}
for off in range(0, 2000, 100):
    page = get(f"{GAMMA}/series", {"limit": 100, "offset": off})
    if not page:
        break
    for s in page:
        all_series[str(s["id"])] = s
for sid, s in all_series.items():
    t = f"{s.get('title') or ''} {s.get('slug') or ''}"
    if ELON_RE.search(t) and TWEET_RE.search(t):
        ensure_series(sid, "series-list-title")

# 1b. public-search for events
search_queries = ["elon musk tweets", "elon musk # tweets", "elon tweets month", "elon tweets daily",
                  "elon musk of tweets october 2026", "elon tweets"]
search_hits = {}
for q in search_queries:
    for st in ("active", "closed", None):
        page_no = 1
        while True:
            p = {"q": q, "page": page_no, "limit_per_type": 50}
            if st:
                p["events_status"] = st
            r = get(f"{GAMMA}/public-search", p)
            for e in r.get("events", []) or []:
                search_hits.setdefault(e["id"], e)
            if not (r.get("pagination", {}) or {}).get("hasMore") or not r.get("events"):
                break
            page_no += 1

search_series_ids = set()
for e in search_hits.values():
    if is_tweet_count_title(e.get("title")):
        for s in e.get("series") or []:
            search_series_ids.add(str(s["id"]))
for sid in SEED_SERIES:
    search_series_ids.add(sid)
for sid in sorted(search_series_ids):
    ensure_series(sid, "seed-or-search")

# 1c. Pull every event of each discovered series (closed and live)
for sid in sorted(series_info, key=lambda x: int(x)):
    for closed in ("true", "false"):
        evs = paginate(f"{GAMMA}/events", {"series_id": sid, "closed": closed})
        for e in evs:
            events_by_id.setdefault(e["id"], e)
        series_info[sid].setdefault("event_counts", {})[f"closed={closed}"] = len(evs)

# 1d. Orphan events (no series): keep tweet-count ones
orphans_kept, orphans_skipped = [], []
for e in list(search_hits.values()):
    if e["id"] in events_by_id:
        continue
    slug = e.get("slug", "")
    if e.get("series"):
        continue
    if slug.startswith(ORPHAN_SLUG_PREFIXES) or is_tweet_count_title(e.get("title")):
        events_by_id[e["id"]] = e
        orphans_kept.append(slug)
    else:
        orphans_skipped.append(slug)

# also orphans from closed/live pagination of the old, series-less 2024 events, found via search
# (the search pass above covers the closed 2024 "of-elon-musk-tweets-between-..." ones)

# Series-less events from the paginated pulls are not expected; check any remaining series-less
for e in events_by_id.values():
    if not e.get("series") and e.get("slug") not in orphans_kept:
        pass

# Filter: keep only tweet-count events
def keep_event(e):
    if e.get("series"):
        sids = {str(s["id"]) for s in e["series"]}
        return bool(sids & set(series_info)) and is_tweet_count_title(e.get("title")) or bool(sids & {"10000", "10816", "10181"})
    return True  # orphans already filtered above

events = [e for e in events_by_id.values() if keep_event(e)]
print(f"events collected: {len(events)} (orphans kept: {len(orphans_kept)}, orphans skipped: {len(orphans_skipped)})")

# ---------- 2. Exact windows from xtracker ----------
xt_map = {}
try:
    xt = get(f"{XT}/users/elonmusk")
    for t in (xt.get("data", {}) or {}).get("trackings", []) or []:
        link = t.get("marketLink") or ""
        slug = link.rstrip("/").split("/event/")[-1] if "/event/" in link else None
        if slug:
            xt_map[slug] = t
except Exception as ex:
    print("xtracker fetch failed:", ex)
print("xtracker trackings:", len(xt_map))

DESC_RE = re.compile(
    r"from\s+([A-Za-z]+ \d{1,2})(?:,? (\d{4}))?\s+(\d{1,2}:\d{2}\s*[AP]M)\s*ET\s+to\s+([A-Za-z]+ \d{1,2}),?\s*(\d{4})?\s+(\d{1,2}:\d{2}\s*[AP]M)\s*ET",
    re.I)


def parse_desc_window(desc):
    m = DESC_RE.search(desc or "")
    if not m:
        return None
    s_md, s_year, s_t, e_md, e_year, e_t = m.groups()
    e_year = e_year or s_year
    if not e_year:
        return None
    s_year = s_year or e_year

    def mk(md, yr, tm):
        dt = datetime.strptime(f"{md} {yr} {tm.upper().replace(' ', '')}", "%B %d %Y %I:%M%p")
        return dt.replace(tzinfo=ET).astimezone(UTC)

    try:
        return mk(s_md, s_year, s_t), mk(e_md, e_year, e_t)
    except ValueError:
        return None


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_gamma_dt(s):
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(UTC)


def family_of(start, end):
    days = (end - start).total_seconds() / 86400
    if days <= 3.0:
        return "48h", days
    if 0.5 <= days <= 1.5:
        return "daily", days
    if 6.0 <= days <= 8.0:
        return "weekly", days
    if 26.0 <= days <= 32.0:
        return "monthly", days
    return "other", days


BUCKET_RE_RANGE = re.compile(r"^\s*(\d[\d,]*)\s*[-–]\s*(\d[\d,]*)\s*$")
BUCKET_RE_PLUS = re.compile(r"^\s*(\d[\d,]*)\s*\+\s*$")
BUCKET_RE_LT = re.compile(r"^\s*(?:<|less than|under)\s*(\d[\d,]*)\s*$", re.I)
BUCKET_RE_GT = re.compile(r"^\s*(?:>|more than|over)\s*(\d[\d,]*)\s*$", re.I)


def bucket_bounds(label, question=""):
    def n(x):
        return int(x.replace(",", ""))
    for src in (label or "", question or ""):
        if not src:
            continue
        m = BUCKET_RE_RANGE.match(src)
        if m:
            return n(m.group(1)), n(m.group(2))
        m = BUCKET_RE_PLUS.match(src)
        if m:
            return n(m.group(1)), 999999
        m = BUCKET_RE_LT.match(src)
        if m:
            return 0, n(m.group(1)) - 1
        m = BUCKET_RE_GT.match(src)
        if m:
            return n(m.group(1)) + 1, 999999
        m = re.search(r"(\d[\d,]*)\s*[-–]\s*(\d[\d,]*)", src)
        if m and src is label:
            return n(m.group(1)), n(m.group(2))
    # question-based fallbacks
    m = re.search(r"(?:less than|fewer than|under)\s+(\d[\d,]*)", question or "", re.I)
    if m:
        return 0, n(m.group(1)) - 1
    m = re.search(r"(\d[\d,]*)\s*\+", question or "")
    if m:
        return n(m.group(1)), 999999
    m = re.search(r"(\d[\d,]*)\s*[-–]\s*(\d[\d,]*)", question or "")
    if m:
        return n(m.group(1)), n(m.group(2))
    return None, None


def outcome_of(prices):
    try:
        p = [float(x) for x in prices]
    except Exception:
        return None
    if len(p) >= 2 and set(p[:2]) == {0.0, 1.0}:
        return 1 if p[0] == 1.0 else 0
    return None


EVENT_ROWS, SUMMARY_ROWS, anomalies = [], [], []
window_key_index = defaultdict(list)

for e in sorted(events, key=lambda x: (x.get("startDate") or "", x.get("slug") or "")):
    slug = e.get("slug")
    series = e.get("series") or []
    series_id = str(series[0]["id"]) if series else ""
    series_slug = series[0].get("slug", "") if series else ""
    if not series_id:
        series_slug = "(no-series)"

    tracked = xt_map.get(slug)
    if tracked:
        w_start = parse_gamma_dt(tracked["startDate"].replace(".000Z", "Z"))
        w_end = parse_gamma_dt(tracked["endDate"].replace(".000Z", "Z"))
        src = "tracking"
    else:
        pw = parse_desc_window(e.get("description") or "")
        if pw:
            w_start, w_end = pw
            src = "description"
        else:
            w_start = parse_gamma_dt(e.get("startDate"))
            w_end = parse_gamma_dt(e.get("endDate"))
            src = "gamma_dates"
            anomalies.append(f"window fallback to gamma dates: {slug}")
    if w_start is None or w_end is None:
        anomalies.append(f"NO WINDOW: {slug}")
        continue
    family, days = family_of(w_start, w_end)
    window_key_index[(iso(w_start), iso(w_end))].append(slug)

    markets = e.get("markets") or []
    summary_winners = []
    for m in markets:
        label = m.get("groupItemTitle") or ""
        q = m.get("question") or ""
        lo, hi = bucket_bounds(label, q)
        if lo is None:
            anomalies.append(f"unparsed bucket: {slug} | label={label!r} | q={q!r}")
        prices = parse_json_field(m.get("outcomePrices")) or []
        tokens = parse_json_field(m.get("clobTokenIds")) or []
        if not isinstance(tokens, list):
            tokens = []
        outcome = outcome_of(prices) if (m.get("closed") or e.get("closed")) else None
        if outcome is None:
            outcome = outcome_of(prices) if isinstance(prices, list) and prices else None
        if outcome is not None and not (m.get("closed") or e.get("closed")):
            # resolved prices on a not-yet-flagged market: still record
            pass
        row = {
            "event_id": e["id"],
            "event_slug": slug,
            "series_id": series_id,
            "series_slug": series_slug,
            "family": family,
            "event_title": e.get("title", ""),
            "window_start_utc": iso(w_start),
            "window_end_utc": iso(w_end),
            "window_source": src,
            "event_volume": e.get("volume", ""),
            "event_closed": str(bool(e.get("closed"))).lower(),
            "market_id": m.get("id", ""),
            "question": q,
            "bucket_label": label,
            "bucket_lo": "" if lo is None else lo,
            "bucket_hi": "" if hi is None else hi,
            "yes_token": tokens[0] if len(tokens) > 0 else "",
            "no_token": tokens[1] if len(tokens) > 1 else "",
            "outcome_yes": "" if outcome is None else outcome,
            "market_volume": m.get("volume", ""),
            "uma_status": m.get("umaResolutionStatus", "") or "",
            "market_created_at": m.get("createdAt", "") or m.get("startDate", "") or "",
            "event_created_at": e.get("createdAt", "") or e.get("creationDate", "") or "",
        }
        EVENT_ROWS.append(row)
        if outcome == 1:
            summary_winners.append((label, lo, hi))

    n_w = len(summary_winners)
    if n_w != 1:
        anomalies.append(f"n_winners={n_w}: {slug}")
    wl = summary_winners[0] if n_w == 1 else (" | ".join(w[0] for w in summary_winners), "", "")
    SUMMARY_ROWS.append({
        "event_slug": slug,
        "family": family,
        "window_start_utc": iso(w_start),
        "window_end_utc": iso(w_end),
        "n_buckets": len(markets),
        "winning_bucket_label": wl[0],
        "winning_lo": "" if wl[1] == "" or wl[1] is None else wl[1],
        "winning_hi": "" if wl[2] == "" or wl[2] is None else wl[2],
        "event_volume": e.get("volume", ""),
        "closed": str(bool(e.get("closed"))).lower(),
        "n_winners": n_w,
    })

# ---------- 3. Write outputs ----------
ev_cols = list(EVENT_ROWS[0].keys())
with open(os.path.join(DATA, "events.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=ev_cols)
    w.writeheader()
    w.writerows(EVENT_ROWS)

sum_cols = list(SUMMARY_ROWS[0].keys())
with open(os.path.join(DATA, "events_summary.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=sum_cols)
    w.writeheader()
    w.writerows(SUMMARY_ROWS)

series_out = {
    "discovered_series": [
        {**{k: v for k, v in s.items() if k != "discovered_via"}, "discovered_via": sorted(s["discovered_via"])}
        for s in sorted(series_info.values(), key=lambda x: int(x["id"]))
    ],
    "orphan_events_included": orphans_kept,
    "orphan_events_excluded": orphans_skipped,
}
with open(os.path.join(DATA, "series_found.json"), "w") as f:
    json.dump(series_out, f, indent=2, default=str)

# ---------- 4. Sanity report ----------
print("\n== Series ==")
for s in series_out["discovered_series"]:
    print(s["id"], s["slug"], "|", s["title"], "|", s["recurrence"], s.get("event_counts"))
print("orphans included:", len(orphans_kept), orphans_kept[:20])
print("orphans excluded:", len(orphans_skipped))

print("\n== Events by family x closed ==")
cnt = Counter((r["family"], r["closed"]) for r in SUMMARY_ROWS)
for k in sorted(cnt):
    print(k, cnt[k])
print("total events:", len(SUMMARY_ROWS), "| total bucket rows:", len(EVENT_ROWS))

print("\n== Date range per family (window_start min, window_end max) ==")
fam_rng = defaultdict(lambda: [None, None])
for r in SUMMARY_ROWS:
    a, b = fam_rng[r["family"]]
    fam_rng[r["family"]] = [min(filter(None, [a, r["window_start_utc"]])), max(filter(None, [b, r["window_end_utc"]]))]
for k, (a, b) in sorted(fam_rng.items()):
    print(k, a, "->", b)

print("\n== n_winners != 1 ==")
bad = [r for r in SUMMARY_ROWS if r["n_winners"] != 1]
for r in bad:
    print(r["event_slug"], r["n_winners"], r["closed"], r["winning_bucket_label"])
print("count:", len(bad))

print("\n== Twin windows (identical start+end) ==")
twins = {k: v for k, v in window_key_index.items() if len(v) > 1}
for k, v in sorted(twins.items()):
    print(k, v)
print("twin groups:", len(twins))

print("\n== Bucket width pattern per family (hi-lo+1, bounded buckets only) ==")
width = defaultdict(Counter)
for r in EVENT_ROWS:
    if r["bucket_lo"] == "" or r["bucket_hi"] == "":
        continue
    if r["bucket_hi"] == 999999 or r["bucket_lo"] == 0 and r["bucket_hi"] != 999999 and str(r["bucket_label"]).startswith("<"):
        continue
    width[r["family"]][int(r["bucket_hi"]) - int(r["bucket_lo"]) + 1] += 1
for fam in sorted(width):
    print(fam, dict(width[fam].most_common(8)))

print("\n== Window source counts ==")
print(Counter(r["window_source"] for r in SUMMARY_ROWS))

print("\n== Anomalies (%d) ==" % len(anomalies))
for a in anomalies[:80]:
    print(" -", a)
