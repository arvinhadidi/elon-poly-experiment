#!/usr/bin/env python3
"""Inventory recurring count / posts / views / mentions market families.

Polymarket (Gamma, xtracker, CLOB) is the primary venue. Kalshi and Manifold are
searched as signal-only cross-checks. Public GET endpoints only, no keys.
This script never places or cancels orders.

Run with cwd = elon/:  python3 pull_related.py
Outputs (elon/data/):
  related_inventory.csv  one row per family
  related_events.csv     every resolved Polymarket event of every family
  related_books.csv      per-bucket book snapshot for the open events sampled
  related_notes.md       Kalshi / Manifold findings and method notes
"""
import csv
import json
import re
import statistics
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import get, parse_json_field, GAMMA, CLOB, XT  # noqa: E402

DATA_DIR = HERE / "data"
RAW_DIR = DATA_DIR / "raw" / "related"  # data/raw/ is gitignored
RAW_DIR.mkdir(parents=True, exist_ok=True)

NOW = datetime.now(timezone.utc)
ET = ZoneInfo("America/New_York")
KALSHI = "https://api.elections.kalshi.com/trade-api/v2"
MANIFOLD = "https://api.manifold.markets/v0"

# Series ids named in the brief, plus ones found while scouting.
KNOWN_SERIES = ["10000", "10816", "10181", "12076", "11108", "11335", "11340",
                "10011", "10061", "10321", "12628", "12664", "11265", "10031", "10033", "10019"]

QUERIES = ["# of tweets", "truth social posts", "Trump posts", "MrBeast views", "youtube views",
           "how many times will", "mentions", "posts", "Zelenskyy", "Elon daily tweets",
           "Elon tweets month", "Elon tweets", "tweets", "# of posts", "views",
           "Cobratate", "Andrew Tate tweets", "POTUS tweets", "Powell mentions", "White House posts",
           "Khamenei posts", "NYC Mayor tweets", "Ted Cruz tweets", "CZ tweets"]

SERIES_NAME_RE = re.compile(r"tweet|post|truth social|views|youtube|mrbeast|mention|# of|how many", re.I)
COUNT_RE = re.compile(r"#|how many|view count|\bviews?\b|\btweets?\b|\bmentions?\b|highest daily|"
                      r"what will \w+ (post|say)|truth social posts|\bposts\b", re.I)
EXCL_RE = re.compile(r"how much|\$\d", re.I)

TARGET_NAMES = ["Elon Musk", "Donald Trump", "Trump (@POTUS)", "POTUS", "White House", "Zelenskyy",
                "NYC Mayor", "CZ", "Khamenei", "Ted Cruz", "Andrew Tate", "MrBeast", "Powell",
                "Morgan Wallen", "Drake", "Justin Bieber", "Ariana Grande", "Kanye", "Taylor Swift",
                "Kamala", "Trump", "Putin", "Zelensky"]
TARGET_TO_USER = {"Elon Musk": "elonmusk", "Donald Trump": "realDonaldTrump", "White House": "WhiteHouse",
                  "Zelenskyy": "ZelenskyyUa", "NYC Mayor": "NYCMayor", "CZ": "cz_binance",
                  "Khamenei": "khamenei_ir", "Ted Cruz": "tedcruz", "Andrew Tate": "Cobratate"}
MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep",
                                      "oct", "nov", "dec"], 1)}


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def f(x, default=None):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def iso(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")) if s else None


def extract_target(title):
    low = (title or "").lower()
    for name in TARGET_NAMES:
        if name.lower() in low:
            return name
    return (title or "")[:40]


def metric_of(title):
    t = (title or "").lower()
    if "truth social" in t:
        return "truth social posts"
    if "youtube" in t or "view" in t:
        return "views"
    if "mention" in t or " say " in t:
        return "mentions"
    if "how many times" in t:
        return "count (how many times)"
    if "tweet" in t or "post" in t or "#" in t:
        return "x posts"
    return "other"


def norm_key(t):
    t = (t or "").lower()
    t = re.sub(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\b", " ", t)
    t = re.sub(r"\d+", " ", t)
    t = re.sub(r"\b(to|through|between|and|by|on|the|next|of|in|a)\b", " ", t)
    t = re.sub(r"[^a-z#]+", " ", t)
    return " ".join(t.split())


# ---------- windows ----------
DESC_T = re.compile(r"([A-Za-z]+)\s+(\d{1,2})(?:,?\s+(\d{4}))?,?\s+(\d{1,2}):(\d{2})\s*([AaPp][Mm])\s*ET")


def window_from_desc(e):
    """Parse 'from <start> ET to <end> ET' from the description. Returns (start, end, src)."""
    desc = (e.get("description") or "").replace("\n", " ")
    hits = list(DESC_T.finditer(desc))
    if len(hits) >= 2:
        try:
            a, b = hits[0], hits[1]
            end_year = int(b.group(3)) if b.group(3) else None
            if end_year is None:
                end_year = (iso(e.get("endDate")) or NOW).astimezone(ET).year
            def mk(m, year):
                mon = MONTHS[m.group(1)[:3].lower()]
                h = int(m.group(4)) % 12 + (12 if m.group(6).lower() == "pm" else 0)
                return datetime(year, mon, int(m.group(2)), h, int(m.group(5)), tzinfo=ET)
            end = mk(b, end_year)
            start = mk(a, int(a.group(3)) if a.group(3) else end_year)
            if not a.group(3) and start > end:
                start = start.replace(year=end_year - 1)
            start_u, end_u = start.astimezone(timezone.utc), end.astimezone(timezone.utc)
            hrs = (end_u - start_u).total_seconds() / 3600
            if 0 < hrs < 24 * 400:
                return start_u, end_u, "description"
        except (KeyError, ValueError):
            pass
    return iso(e.get("startDate")), iso(e.get("endDate")), "gamma"


# ---------- fetch helpers ----------
def gamma_event_by_slug(slug):
    r = get(GAMMA + "/events", params={"slug": slug})
    return r[0] if r else None


def all_series():
    out, off = [], 0
    while off < 5000:
        page = get(GAMMA + "/series", params={"limit": 100, "offset": off})
        if not page:
            break
        out += page
        off += len(page)
    return out


def series_events(sid):
    out = {}
    for closed in ("true", "false"):
        off = 0
        while off < 5000:
            try:
                page = get(GAMMA + "/events", params={"series_id": sid, "closed": closed, "limit": 100, "offset": off})
            except Exception as ex:  # noqa: BLE001  (offset cap ~2000)
                log(f"series {sid} paging stopped at offset {off}: {ex}")
                break
            if not page:
                break
            for e in page:
                out[e["id"]] = e
            off += len(page)
    return list(out.values())


def xt_posts(handle, platform, sd, ed):
    r = get(f"{XT}/users/{handle}/posts", params={"platform": platform, "startDate": sd, "endDate": ed})
    return r.get("data", []) or []


def xt_platform(user):
    return "x" if user["platform"] == "X" else user["platform"]


def earliest_xt_data(user, floor=date(2025, 1, 1), step=30):
    """Scan forward in windows until posts appear; return (earliest createdAt date, n posts in last 30d)."""
    h, p = user["handle"], xt_platform(user)
    d = floor
    today = date.today()
    while d <= today:
        ed = min(d + timedelta(days=step - 1), today)
        posts = xt_posts(h, p, d.isoformat(), ed.isoformat())
        if posts:
            first = min(x["createdAt"] for x in posts)
            recent = xt_posts(h, p, (today - timedelta(days=30)).isoformat(), today.isoformat())
            return first[:10], len(recent)
        d = ed + timedelta(days=1)
    return "", 0


# ---------- main pipeline ----------
def discover():
    EV = {}  # event id -> event
    users = [u for u in get(XT + "/users")["data"] if not u["handle"].lower().startswith("mctest")]
    tracked = {}
    win_override = {}
    for u in users:
        for t in u.get("trackings") or []:
            slug = (t.get("marketLink") or "").rstrip("/").split("/")[-1]
            if not slug:
                continue
            tracked[slug] = {"handle": u["handle"], "platform": u["platform"]}
            ev = gamma_event_by_slug(slug)
            if ev:
                EV[ev["id"]] = ev
                win_override[ev["id"]] = (iso(t["startDate"]), iso(t["endDate"]), "xtracker")
                tracked[slug]["event_id"] = ev["id"]
    log(f"xtracker users (non-test): {len(users)}; tracked events resolved: {len(win_override)}")

    cand = {sid: "known" for sid in KNOWN_SERIES}
    for s in all_series():
        if SERIES_NAME_RE.search(s.get("title") or "") or SERIES_NAME_RE.search(s.get("slug") or ""):
            cand.setdefault(str(s["id"]), "series_title")
    for e in EV.values():
        for s in e.get("series") or []:
            cand.setdefault(str(s["id"]), "xtracker")

    hits = 0
    for q in QUERIES:
        try:
            r = get(GAMMA + "/public-search", params={"q": q})
        except Exception as ex:  # noqa: BLE001
            log(f"search failed {q!r}: {ex}")
            continue
        for e in r.get("events", []) or []:
            EV.setdefault(e["id"], e)
            hits += 1
            if COUNT_RE.search(e.get("title") or ""):
                for s in e.get("series") or []:
                    cand.setdefault(str(s["id"]), "search")
    log(f"public-search hits: {hits}")

    off, pages = 0, 0
    while pages < 80:
        try:
            page = get(GAMMA + "/events", params={"closed": "false", "limit": 100, "offset": off})
        except Exception as ex:  # noqa: BLE001  (Gamma rejects offsets past ~2000)
            log(f"open sweep stopped at offset {off}: {ex}")
            break
        if not page:
            break
        for e in page:
            if COUNT_RE.search(e.get("title") or ""):
                EV.setdefault(e["id"], e)
                for s in e.get("series") or []:
                    cand.setdefault(str(s["id"]), "open_sweep")
        off += len(page)
        pages += 1
    log(f"open-event sweep pages: {pages}; candidate series: {len(cand)}")
    return EV, tracked, win_override, cand, users


def build_families(EV, cand):
    families = {}
    for sid, src in cand.items():
        evs = series_events(sid)
        if not evs:
            continue
        share = sum(1 for e in evs if COUNT_RE.search(e.get("title") or "")) / len(evs)
        if share < 0.5:
            log(f"skip series {sid}: only {share:.0%} count-style titles")
            continue
        families[f"S{sid}"] = {"series_id": sid, "events": evs, "src": src}
    # series-less events (search/sweep) grouped by normalised title
    groups = defaultdict(list)
    for e in EV.values():
        if e.get("series"):
            continue
        t = e.get("title") or ""
        if COUNT_RE.search(t) and not EXCL_RE.search(t):
            groups[norm_key(t)].append(e)
    for k, evs in groups.items():
        if len(evs) >= 2 or re.search(r"#|how many", evs[0].get("title") or "", re.I):
            for i, e in enumerate(evs):
                if not e.get("markets") and e.get("slug"):
                    full = gamma_event_by_slug(e["slug"])
                    if full:
                        evs[i] = full
            families[f"K:{k}"] = {"series_id": "", "events": evs, "src": "search/sweep"}
    return families


def event_row(e, fam_name, target, win_override):
    s, en, src = win_override.get(e["id"]) or window_from_desc(e)
    markets = e.get("markets") or []
    winner = ""
    for m in markets:
        pr = parse_json_field(m.get("outcomePrices"))
        if isinstance(pr, list) and pr and f(pr[0], 0) >= 0.99:
            winner = m.get("groupItemTitle") or m.get("question") or ""
    return {"family": fam_name, "event_slug": e.get("slug"), "series_id": (e.get("series") or [{}])[0].get("id", "") if e.get("series") else "",
            "window_start_utc": s.strftime("%Y-%m-%dT%H:%M:%SZ") if s else "",
            "window_end_utc": en.strftime("%Y-%m-%dT%H:%M:%SZ") if en else "",
            "volume": round(f(e.get("volume"), 0.0), 2), "n_buckets": len(markets),
            "winning_label": winner, "_src": src, "_start": s, "_end": en, "_closed": bool(e.get("closed")),
            "_target": target, "_markets": markets, "_event": e}


def bucket_width(titles):
    lows = set()
    for t in titles:
        m = re.search(r"(\d+(?:\.\d+)?)\s*([kKmMbB]?)", (t or "").replace(",", ""))
        if m:
            mult = {"k": 1e3, "m": 1e6, "b": 1e9}.get(m.group(2).lower(), 1)
            lows.add(float(m.group(1)) * mult)
    lows = sorted(lows)
    diffs = [b - a for a, b in zip(lows, lows[1:]) if b > a]
    if not diffs:
        return ""
    w = statistics.median(diffs)
    return f"{w:g}"


def settlement_of(e):
    desc = (e.get("description") or "").replace("\n", " ")
    m = re.search(r"(The resolution source[^.]*\.|resolve[sd]? (?:according to|based on)[^.]*\.)", desc, re.I)
    txt = m.group(1) if m else (e.get("resolutionSource") or "")
    return txt[:200]


def pick_open(evs):
    open_ = [e for e in evs if not e.get("closed") and (iso(e.get("endDate")) or NOW) > NOW]
    started = [e for e in open_ if (iso(e.get("startDate")) or NOW) <= NOW]
    pool = started or open_
    return sorted(pool, key=lambda e: iso(e.get("endDate")) or NOW)[:2]


def book_stats(token):
    try:
        b = get(CLOB + "/book", params={"token_id": token}, tries=3)
    except Exception as ex:  # noqa: BLE001
        return None, str(ex)
    asks = sorted([(f(x["price"]), f(x["size"], 0.0)) for x in b.get("asks") or [] if f(x.get("price")) is not None], key=lambda t: t[0])
    bids = sorted([(f(x["price"]), f(x["size"], 0.0)) for x in b.get("bids") or [] if f(x.get("price")) is not None], key=lambda t: -t[0])
    best_ask = asks[0][0] if asks else None
    best_bid = bids[0][0] if bids else None
    res = {"best_bid": best_bid, "best_ask": best_ask,
           "spread": (best_ask - best_bid) if best_ask is not None and best_bid is not None else None,
           "touch_usd": (asks[0][0] * asks[0][1]) if asks else 0.0}
    if best_ask is not None:
        res["depth_2c_usd"] = sum(p * s for p, s in asks if p <= best_ask + 0.02 + 1e-9)
    else:
        res["depth_2c_usd"] = 0.0
    return res, ""


def main():
    t0 = time.time()
    EV, tracked, win_override, cand, users = discover()
    families = build_families(EV, cand)
    log(f"count families found: {len(families)}")

    # xtracker data availability, one probe per handle
    probe = {}
    for u in users:
        if u.get("trackings") or u["handle"] in TARGET_TO_USER.values():
            try:
                probe[u["handle"]] = earliest_xt_data(u)
            except Exception as ex:  # noqa: BLE001
                log(f"xt probe failed {u['handle']}: {ex}")
                probe[u["handle"]] = ("", 0)
    log(f"xt probes: {probe}")

    user_by_handle = {u["handle"]: u for u in users}
    fam_rows, ev_rows, book_rows = [], [], []
    open_jobs = []  # (family key, event dict, target)

    for key, fam in families.items():
        evs = fam["events"]
        targets = [extract_target(e.get("title")) for e in evs]
        target = max(set(targets), key=targets.count) if targets else ""
        sid = fam["series_id"]
        metric = metric_of(evs[0].get("title")) if evs else ""
        series_slug = next(((e.get("seriesSlug") or "") for e in evs if e.get("seriesSlug")), "")
        fam_name = f"{target} {metric}" + (f" [{series_slug}]" if series_slug else "")
        rows = [event_row(e, fam_name, target, win_override) for e in evs]
        ev_rows += [r for r in rows if r["_closed"]]
        resolved = [r for r in rows if r["_closed"]]
        open_evs = [r["_event"] for r in rows if not r["_closed"]]
        for oe in pick_open(open_evs):
            open_jobs.append((fam_name, oe))

        # xtracker linkage
        xt_handle = ""
        for slug, t in tracked.items():
            if t.get("event_id") in {e.get("id") for e in evs}:
                xt_handle = t["handle"]
                break
        if not xt_handle and target in TARGET_TO_USER:
            cand_h = TARGET_TO_USER[target]
            u = user_by_handle.get(cand_h)
            if u and ((metric == "truth social posts") == (u["platform"] == "TRUTH_SOCIAL")):
                xt_handle = cand_h
        if xt_handle and xt_handle in probe:
            data_start, recent_n = probe[xt_handle]
            data_free = "y" if recent_n > 0 else "n"
        else:
            data_start, recent_n, data_free = "", 0, "n"

        ends = [r["_end"] for r in resolved if r["_end"]]
        cut = NOW - timedelta(days=90)
        r90 = [r for r in resolved if r["_end"] and r["_end"] >= cut]
        vols90 = [r["volume"] for r in r90]
        durs = [(r["_end"] - r["_start"]).total_seconds() / 3600 for r in resolved if r["_start"] and r["_end"]]
        window = f"{statistics.median(durs):.0f}h ({statistics.median(durs)/24:.1f}d)" if durs else ""
        nb = [len(r["_markets"]) for r in resolved]
        bw = bucket_width([m.get("groupItemTitle") for m in (resolved[0]["_markets"] if resolved else [])])
        srcs = defaultdict(int)
        for r in rows:
            srcs[r["_src"]] += 1

        fam_rows.append({
            "family": fam_name, "target": target, "venue": "Polymarket", "series_id": sid,
            "series_slug": series_slug, "settlement": settlement_of(evs[0]) if evs else "",
            "data_free": data_free, "data_start": data_start, "window": window,
            "n_resolved": len(resolved),
            "first_end": min(ends).date().isoformat() if ends else "",
            "last_end": max(ends).date().isoformat() if ends else "",
            "events_per_month": round(len(r90) / 3, 2),
            "median_vol_90d": round(statistics.median(vols90), 2) if vols90 else "",
            "mean_vol_90d": round(statistics.mean(vols90), 2) if vols90 else "",
            "typical_n_buckets": int(statistics.median(nb)) if nb else "",
            "bucket_width": bw,
            "depth_2c_cheap_usd": "", "median_touch_usd": "",
            "notes": f"src={fam['src']}; events_by_window_src={dict(srcs)}; xt_handle={xt_handle or '-'}; "
                     f"all_events={len(rows)}; open={len(open_evs)}; sum_vol={sum(r['volume'] for r in rows):.0f}",
            "_sumvol": sum(r["volume"] for r in rows),
        })

    # live depth for open events (max 2 per family)
    depth_by_fam = defaultdict(list)
    touch_by_fam = defaultdict(list)
    event_depth_notes = []
    jobs = []
    for fam_name, oe in open_jobs:
        for m in oe.get("markets") or []:
            if m.get("closed"):
                continue
            toks = parse_json_field(m.get("clobTokenIds")) or []
            if toks:
                jobs.append((fam_name, oe, m, toks[0]))
    log(f"book fetches: {len(jobs)} for {len(open_jobs)} open events")
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda j: book_stats(j[3]), jobs))
    per_event = defaultdict(lambda: {"depth": 0.0, "n_cheap": 0, "touches": []})
    for (fam_name, oe, m, tok), (st, err) in zip(jobs, results):
        if st is None:
            continue
        bucket = m.get("groupItemTitle") or m.get("question")
        book_rows.append({"family": fam_name, "event_slug": oe.get("slug"), "bucket": bucket,
                          "best_bid": st["best_bid"], "best_ask": st["best_ask"],
                          "spread": round(st["spread"], 4) if st["spread"] is not None else "",
                          "touch_usd": round(st["touch_usd"], 2), "depth_2c_usd": round(st["depth_2c_usd"], 2),
                          "cheap_le_50c": st["best_ask"] is not None and st["best_ask"] <= 0.50})
        if st["best_ask"] is not None and st["best_ask"] <= 0.50:
            pe = per_event[oe.get("slug")]
            pe["depth"] += st["depth_2c_usd"]
            pe["n_cheap"] += 1
            pe["touches"].append(st["touch_usd"])
            pe["fam"] = fam_name
    for slug, pe in per_event.items():
        depth_by_fam[pe["fam"]].append(pe["depth"])
        touch_by_fam[pe["fam"]] += pe["touches"]
        event_depth_notes.append(f"- {slug}: cheap buckets={pe['n_cheap']}, depth within 2c=${pe['depth']:,.0f}, "
                                 f"median touch=${statistics.median(pe['touches']) if pe['touches'] else 0:,.0f}")
    for r in fam_rows:
        name = r["family"]
        if name in depth_by_fam:
            r["depth_2c_cheap_usd"] = round(statistics.mean(depth_by_fam[name]), 0)
            r["median_touch_usd"] = round(statistics.median(touch_by_fam[name]), 0) if touch_by_fam[name] else ""

    fam_rows.sort(key=lambda r: -r["_sumvol"])
    inv_cols = ["family", "target", "venue", "series_id", "series_slug", "settlement", "data_free", "data_start",
                "window", "n_resolved", "first_end", "last_end", "events_per_month", "median_vol_90d",
                "mean_vol_90d", "typical_n_buckets", "bucket_width", "depth_2c_cheap_usd", "median_touch_usd", "notes"]
    with open(DATA_DIR / "related_inventory.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=inv_cols, extrasaction="ignore")
        w.writeheader()
        for r in fam_rows:
            w.writerow(r)

    ev_rows.sort(key=lambda r: (r["family"], r["window_end_utc"]))
    ev_cols = ["family", "event_slug", "series_id", "window_start_utc", "window_end_utc", "volume", "n_buckets", "winning_label"]
    with open(DATA_DIR / "related_events.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=ev_cols, extrasaction="ignore")
        w.writeheader()
        for r in ev_rows:
            w.writerow(r)

    with open(DATA_DIR / "related_books.csv", "w", newline="") as fh:
        cols = ["family", "event_slug", "bucket", "best_bid", "best_ask", "spread", "touch_usd", "depth_2c_usd", "cheap_le_50c"]
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in book_rows:
            w.writerow(r)

    kalshi_md, manifold_md = venue_checks()
    notes = [
        "# Related count-market inventory: notes",
        "",
        f"Generated {NOW.strftime('%Y-%m-%d %H:%M UTC')} by elon/pull_related.py (read-only, no orders).",
        "",
        "## Polymarket method",
        "- Families = Gamma series whose titles are count-style (>=50% of event titles match COUNT_RE), plus",
        "  series-less events grouped by normalised title (only if >=2 hits or a '#'/'how many' title).",
        "- Series-less families come only from public-search (5 hits per query) and the open-event sweep, so",
        "  their history is incomplete.",
        "- Window: xtracker tracking dates when the event is tracked; otherwise the ET window parsed from the",
        "  description; otherwise Gamma startDate/endDate (UTC).",
        "- Live depth: up to 2 open events per family (started, soonest end). Depth = sum(size*price) of asks within",
        "  2c of the best ask, over buckets with best ask <= 0.50. Touch = size*price at the best ask.",
        "- data_free = y only when the xtracker posts endpoint returned posts for the last 30 days (free, no key).",
        "",
        "## Open-event depth detail",
        *(event_depth_notes or ["- none"]),
        "",
        "## Kalshi (signal only, cannot trade)",
        *kalshi_md,
        "",
        "## Manifold and other venues",
        *manifold_md,
        "",
        f"Runtime: {time.time()-t0:.0f}s",
    ]
    (DATA_DIR / "related_notes.md").write_text("\n".join(notes) + "\n")
    log(f"wrote {len(fam_rows)} families, {len(ev_rows)} resolved events, {len(book_rows)} book rows")


def venue_checks():
    kal_md, man_md = [], []
    # Kalshi: list all series, keep title/ticker matches
    try:
        series, cursor = [], None
        while True:
            p = {"limit": 1000}
            if cursor:
                p["cursor"] = cursor
            r = get(KALSHI + "/series", params=p)
            batch = r.get("series", []) or []
            series += batch
            cursor = r.get("cursor")
            if not cursor or not batch:
                break
        kre = re.compile(r"elon|musk|tweet|post|truth|mention|views?\b|youtube|mrbeast", re.I)
        matched = [s for s in series if kre.search((s.get("title") or "") + " " + (s.get("ticker") or ""))]
        kal_md.append(f"- Kalshi series listed: {len(series)}; title/ticker matches: {len(matched)}")
        for s in matched[:40]:
            tk = s.get("ticker")
            try:
                mk = get(KALSHI + "/markets", params={"series_ticker": tk, "limit": 1000})
                markets = mk.get("markets", []) or []
                vol = sum(f(m.get("volume"), 0.0) or 0 for m in markets)
                st = {}
                for m in markets:
                    st[m.get("status")] = st.get(m.get("status"), 0) + 1
                kal_md.append(f"  - {tk} | {s.get('title')} | markets={len(markets)} status={st} contracts_volume={vol:,.0f}")
            except Exception as ex:  # noqa: BLE001
                kal_md.append(f"  - {tk} | {s.get('title')} | market fetch failed: {ex}")
        if not matched:
            kal_md.append("- No Kalshi series matched elon|musk|tweet|post|truth|mention|views|youtube|mrbeast.")
        (RAW_DIR / "kalshi_series.json").write_text(json.dumps(matched, default=str))
    except Exception as ex:  # noqa: BLE001
        kal_md.append(f"- Kalshi check failed: {ex}")

    # Manifold search
    try:
        seen = {}
        for term in ["elon tweets", "elon musk tweets", "tweets", "truth social posts", "trump posts",
                     "mrbeast views", "youtube views", "# of tweets", "mentions"]:
            r = get(MANIFOLD + "/search-markets", params={"term": term, "limit": 100})
            for m in r or []:
                seen.setdefault(m.get("id"), m)
        mre = re.compile(r"elon|musk|tweet|post|truth social|views|mention|mrbeast", re.I)
        hits = [m for m in seen.values() if mre.search(m.get("question") or "")]
        count_hits = [m for m in hits if re.search(r"tweet|post|views|mention", m.get("question") or "", re.I)]
        man_md.append(f"- Manifold search: {len(seen)} unique markets across 9 terms; {len(hits)} match "
                      f"elon/musk/tweet/post/truth/views/mention/mrbeast.")
        for m in sorted(hits, key=lambda x: -(x.get("volume") or 0))[:25]:
            man_md.append(f"  - {m.get('question')} | vol={m.get('volume', 0):,.0f} resolved={m.get('isResolved')} "
                          f"close={datetime.fromtimestamp((m.get('closeTime') or 0)/1000, timezone.utc).date() if m.get('closeTime') else ''} "
                          f"| {m.get('url')}")
        if not count_hits:
            man_md.append("- No Manifold count-style (tweets/posts/views/mentions) market found.")
        (RAW_DIR / "manifold_hits.json").write_text(json.dumps(hits, default=str))
    except Exception as ex:  # noqa: BLE001
        man_md.append(f"- Manifold check failed: {ex}")
    return kal_md, man_md


if __name__ == "__main__":
    main()
