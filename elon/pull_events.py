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
        off += 100
    return out


def is_tweet_count_title(t):
    return bool(ELON_RE.search(t or "")) and bool(re.search(r"tweet", t or "", re.I))


# ---------- 1. Discover series ----------
series_info = {}   # id -> dict
events_by_id = {}  # id -> event (dedupe)


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

# Events reached through the series pulls are kept as-is (all are tweet-count markets).
# Orphans were filtered above, so no further filtering is needed.
events = list(events_by_id.values())
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

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
MON = r"([A-Za-z]{3,9})"
TIME = r"(\d{1,2}:\d{2}\s*[AP]M)"
RANGE_RE = re.compile(
    r"(?:from|between)\s+" + MON + r"\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s*(\d{4}))?(?:,?\s*" + TIME + r"\s*ET)?"
    r"\s+(?:to|and|-|\u2013)\s+" + MON + r"\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s*(\d{4}))?(?:,?\s*" + TIME + r"\s*ET)?",
    re.I)
SINGLE_DAY_RE = re.compile(r"\bon\s+" + MON + r"\s+(\d{1,2})(?:st|nd|rd|th)?,?\s+(\d{4})\s*\(?ET", re.I)
MONTH_RE = re.compile(r"(?:month of|in)\s+" + MON + r"(?:\s+(\d{4}))?\s*\(?(?:ET)?", re.I)


def _mon(name):
    m = MONTHS.get(name[:3].lower())
    if m is None or name.lower()[:3] not in MONTHS:
        raise ValueError(name)
    return m


def _et(y, mo, d, tm=None):
    hh, mm = 0, 0
    if tm:
        t = datetime.strptime(tm.upper().replace(" ", ""), "%I:%M%p")
        hh, mm = t.hour, t.minute
    return datetime(y, mo, d, hh, mm, tzinfo=ET).astimezone(UTC)


def parse_desc_window(desc, end_hint=None):
    """Return (start_utc, end_utc, rule) parsed from description text, or None."""
    desc = desc or ""
    hint_year = end_hint.year if end_hint else None
    try:
        m = RANGE_RE.search(desc)
        if m:
            s_mon, s_day, s_yr, s_t, e_mon, e_day, e_yr, e_t = m.groups()
            if e_yr is None and s_yr is None and hint_year is None:
                return None
            e_yr = int(e_yr) if e_yr else (int(s_yr) if s_yr else hint_year)
            if s_yr:
                s_yr = int(s_yr)
            else:
                # no year on the start date: a range crossing New Year starts in the prior year
                s_yr = e_yr - 1 if _mon(s_mon) > _mon(e_mon) else e_yr
            # xtracker/Polymarket weekly windows end at 12:00 PM ET when the text omits a time
            s_t = s_t or "12:00 PM"
            e_t = e_t or "12:00 PM"
            return _et(s_yr, _mon(s_mon), int(s_day), s_t), _et(e_yr, _mon(e_mon), int(e_day), e_t), "range"
        m = SINGLE_DAY_RE.search(desc)
        if m:
            mo, d, yr = m.group(1), int(m.group(2)), int(m.group(3))
            return _et(yr, _mon(mo), d), _next_day(yr, _mon(mo), d), "single-day"
        m = MONTH_RE.search(desc)
        if m:
            mo_name, yr = m.group(1), m.group(2)
            mo = _mon(mo_name)
            if yr:
                yr = int(yr)
            elif hint_year:
                yr = hint_year if mo <= end_hint.month else hint_year - 1
            else:
                return None
            nxt_y, nxt_m = (yr + 1, 1) if mo == 12 else (yr, mo + 1)
            return _et(yr, mo, 1), _et(nxt_y, nxt_m, 1), "month"
    except ValueError:
        return None
    return None


def _next_day(y, mo, d):
    from datetime import date, timedelta
    nd = date(y, mo, d) + timedelta(days=1)
    return _et(nd.year, nd.month, nd.day)


TITLE_RANGE_RE = re.compile(
    MON + r"\s+(\d{1,2})\s*(?:-|\u2013|to|and)\s*(?:" + MON + r"\s+)?(\d{1,2})(?!\d)", re.I)


def parse_title_window(title, g_start, g_end):
    """Date-level window from a title like 'Elon Musk # of tweets June 14-21?'.
    The end instant is the Gamma endDate when present (its ET clock time is reused for the start)."""
    if not title:
        return None
    anchor = g_end or g_start
    if anchor is None:
        return None
    year = anchor.astimezone(ET).year
    clock = (g_end or anchor).astimezone(ET)
    for m in TITLE_RANGE_RE.finditer(title):
        try:
            s_mon = _mon(m.group(1))
        except ValueError:
            continue
        s_day = int(m.group(2))
        e_mon = _mon(m.group(3)) if m.group(3) else s_mon
        e_day = int(m.group(4))
        if not m.group(3) and e_day < s_day:
            e_mon = s_mon + 1 if s_mon < 12 else 1
        s_year = year if s_mon <= e_mon else year - 1
        if g_end is not None:
            end_utc = g_end
        else:
            end_utc = _et(year, e_mon, e_day, "12:00 PM")
        # start at the same ET clock time as the end, on the start date
        s_local = datetime(s_year, s_mon, s_day, clock.hour, clock.minute, tzinfo=ET).astimezone(UTC)
        return s_local, end_utc
    return None


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_gamma_dt(s):
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(UTC)


def family_of(start, end):
    days = (end - start).total_seconds() / 86400
    if days <= 1.5:
        return "daily", days
    if days <= 3.5:
        return "48h", days
    if 6.0 <= days <= 8.0:
        return "weekly", days
    if 26.0 <= days <= 32.0:
        return "monthly", days
    return "other", days


BUCKET_RE_RANGE = re.compile(r"^\s*(\d[\d,]*)\s*[-–]\s*(\d[\d,]*)\s*$")
BUCKET_RE_PLUS = re.compile(r"^\s*(\d[\d,]*)\s*\+\s*$")
BUCKET_RE_LT = re.compile(r"^\s*(?:<|less than|under)\s*(\d[\d,]*)\s*$", re.I)
BUCKET_RE_GT = re.compile(r"^\s*(?:>|more than|over)\s*(\d[\d,]*)\s*$", re.I)
BUCKET_RE_OR_MORE = re.compile(r"^\s*(\d[\d,]*)\s*(?:\+|or more|or higher|and above)\s*$", re.I)
BUCKET_RE_OR_LESS = re.compile(r"^\s*(\d[\d,]*)\s*(?:or less|or fewer|or below)\s*$", re.I)


def bucket_bounds(label, question=""):
    def n(x):
        return int(x.replace(",", ""))
    for src in (label or "", question or ""):
        if not src:
            continue
        m = BUCKET_RE_RANGE.match(src)
        if m:
            return n(m.group(1)), n(m.group(2))
        m = BUCKET_RE_PLUS.match(src) or BUCKET_RE_OR_MORE.match(src)
        if m:
            return n(m.group(1)), 999999
        m = BUCKET_RE_OR_LESS.match(src)
        if m:
            return 0, n(m.group(1))
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


def outcome_of(prices, closed):
    """1 = YES won, 0 = NO won, None = not settled. Only closed markets settle.
    Settled prices are exact (1/0) or within 0.01 of it (e.g. 0.9995/0.0005)."""
    if not closed:
        return None
    try:
        p = [float(x) for x in prices]
    except Exception:
        return None
    if len(p) < 2:
        return None
    if all(abs(x - round(x)) <= 0.01 for x in p[:2]) and round(p[0]) + round(p[1]) == 1:
        if p[0] not in (0.0, 1.0):
            anomalies.append(f"near-settled prices {prices}")
        return int(round(p[0]))
    return None


EVENT_ROWS, SUMMARY_ROWS, SUMMARY_ROWS_SRC, anomalies = [], [], [], []
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
        g_end = parse_gamma_dt(e.get("endDate"))
        pw = parse_desc_window(e.get("description") or "", g_end)
        if pw and pw[2] == "range" and (pw[1] - pw[0]).days > 10:
            # description text disagrees with the title for this range; trust the title
            anomalies.append(f"description span {(pw[1] - pw[0]).days}d overridden by title: {slug}")
            pw = None
        if pw:
            w_start, w_end, rule = pw
            src = "description"
            if rule != "range":
                src = f"description-{rule}"
        else:
            g_start = parse_gamma_dt(e.get("startDate"))
            g_end = parse_gamma_dt(e.get("endDate"))
            tw = parse_title_window(e.get("title"), g_start, g_end)
            if tw:
                w_start, w_end = tw
                src = "title"
            else:
                w_start, w_end = g_start, g_end
                src = "gamma_dates"
            anomalies.append(f"window fallback to {src}: {slug} -> {iso(w_start) if w_start else None} .. {iso(w_end) if w_end else None}")
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
        outcome = outcome_of(prices, bool(m.get("closed") or e.get("closed")))
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
    SUMMARY_ROWS_SRC.append({"window_source": src})
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

print("\n== Bucket width pattern per family (hi-lo+1, interior buckets only) ==")
width = defaultdict(Counter)
for r in EVENT_ROWS:
    if r["bucket_lo"] == "" or r["bucket_hi"] == "":
        continue
    if r["bucket_hi"] == 999999 or r["bucket_lo"] == 0:
        continue  # open-ended "N+" and "<N" buckets have no true width
    width[r["family"]][int(r["bucket_hi"]) - int(r["bucket_lo"]) + 1] += 1
for fam in sorted(width):
    print(fam, dict(width[fam].most_common(8)))

print("\n== Window source counts ==")
print(Counter(r["window_source"] for r in SUMMARY_ROWS_SRC))

print("\n== Anomalies (%d) ==" % len(anomalies))
for a in anomalies[:80]:
    print(" -", a)
