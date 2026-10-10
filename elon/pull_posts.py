"""Download Elon Musk's full X post history from xtracker (Polymarket settlement counter).

Outputs (relative to this elon/ dir):
  data/raw/xt_users.json            raw GET {XT}/users
  data/trackings_elonmusk.json      raw data.trackings from GET {XT}/users/elonmusk
  data/posts_elonmusk.csv           one row per post, sorted by createdAt
  data/posts_lag_monthly.csv        per calendar month lag stats (UTC month of createdAt)
Also prints boundary/cap findings and probe results for extra endpoints.
"""
import csv, json, os, re, statistics, sys, datetime as dt
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import requests
from common import get, XT, UA

DATA = HERE / "data"
RAW = DATA / "raw"
RAW.mkdir(parents=True, exist_ok=True)
POSTS_URL = f"{XT}/users/elonmusk/posts"
START = dt.date(2025, 11, 1)
TODAY = dt.date(2026, 10, 10)
END_EXCL = TODAY + dt.timedelta(days=2)  # endDate is exclusive (see probe); covers through 2026-10-11

def day(d): return d.strftime("%Y-%m-%d")

def fetch(s, e):
    r = get(POSTS_URL, params={"platform": "x", "startDate": s, "endDate": e})
    if not r.get("success"):
        raise RuntimeError(f"not success for {s}..{e}: {r}")
    return r["data"]

# ---------- 1. boundary / cap probes ----------
print("== boundary probes ==")
for s, e in [("2025-11-17", "2025-11-18"), ("2025-11-18", "2025-11-18"), ("2025-11-18", "2025-11-19")]:
    d = fetch(s, e); ts = sorted(p["createdAt"] for p in d)
    print(f"  startDate={s} endDate={e}: n={len(d)} min={ts[0] if ts else '-'} max={ts[-1] if ts else '-'}")
print("  -> endDate is exclusive; dates are UTC day boundaries (createdAt 00:00-23:59Z matches the UTC day)")

print("== earliest-post probes ==")
for s, e in [("2025-01-01", "2025-02-01"), ("2025-10-01", "2025-11-01"), ("2025-11-01", "2025-11-18")]:
    print(f"  {s}..{e}: n={len(fetch(s, e))}")

print("== cap probes (single call vs sum of daily calls) ==")
def cap_check(a, b):
    big = fetch(day(a), day(b))
    ids_daily, tot, cur = set(), 0, a
    while cur < b:
        d = fetch(day(cur), day(cur + dt.timedelta(1)))
        tot += len(d); ids_daily |= {p["id"] for p in d}; cur += dt.timedelta(1)
    print(f"  {day(a)}..{day(b)} ({(b-a).days}d): single={len(big)} (unique {len({p['id'] for p in big})}) daily_sum={tot} (unique {len(ids_daily)})")
    return big
cap_check(dt.date(2026, 9, 1), dt.date(2026, 10, 1))
cap_check(dt.date(2025, 11, 18), dt.date(2026, 1, 1))  # 44 days, earlier run returned 2001 rows
cap_check(dt.date(2026, 1, 1), dt.date(2026, 2, 10))

# ---------- 2. raw users + trackings ----------
print("== users / trackings ==")
users = get(f"{XT}/users")
(RAW / "xt_users.json").write_text(json.dumps(users, ensure_ascii=False, indent=2))
user = get(f"{XT}/users/elonmusk")
trackings = user["data"]["trackings"]
(DATA / "trackings_elonmusk.json").write_text(json.dumps(trackings, ensure_ascii=False, indent=2))
print(f"  trackings for elonmusk: {len(trackings)} (isActive: {sum(bool(t.get('isActive')) for t in trackings)})")

# ---------- 3. full post pull (7-day windows, 1-day overlap, dedupe by id) ----------
print("== pulling posts ==")
by_id = {}
raw_rows = 0
cur = START
WIN = 7
while cur < END_EXCL:
    win_end = min(cur + dt.timedelta(WIN + 1), END_EXCL)  # +1 day overlap with next window
    rows = fetch(day(cur), day(win_end))
    raw_rows += len(rows)
    for p in rows:
        by_id[p["id"]] = p
    cur += dt.timedelta(WIN)
print(f"  raw rows across windows={raw_rows}, unique posts={len(by_id)}")

def parse_iso(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(dt.timezone.utc)

def iso_out(d):
    return d.strftime("%Y-%m-%dT%H:%M:%SZ")

RT_RE = re.compile(r"^RT @")
LINK_RE = re.compile(r"(?<![\w.])(?:x|twitter)\.com/\S+/status/\d+")
rows = []
for p in by_id.values():
    c = p.get("content") or ""
    created = parse_iso(p["createdAt"]); imported = parse_iso(p["importedAt"])
    lag = (imported - created).total_seconds()
    rows.append({
        "id": p["id"],
        "platformId": p.get("platformId"),
        "createdAt": iso_out(created),
        "importedAt": iso_out(imported),
        "lag_sec": round(lag, 3),
        "content_len": len(c),
        "starts_with_RT": bool(RT_RE.search(c)),
        "has_quote_link": bool(LINK_RE.search(c)),
        "snippet": c[:80].replace("\r", " ").replace("\n", " "),
        "_created_dt": created,
    })
rows.sort(key=lambda r: r["_created_dt"])
cols = ["id", "platformId", "createdAt", "importedAt", "lag_sec", "content_len", "starts_with_RT", "has_quote_link", "snippet"]
with open(DATA / "posts_elonmusk.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=cols)
    w.writeheader()
    for r in rows:
        w.writerow({k: r[k] for k in cols})
print(f"  wrote {len(rows)} rows -> data/posts_elonmusk.csv")
if rows:
    print(f"  earliest createdAt={rows[0]['createdAt']} latest createdAt={rows[-1]['createdAt']}")
    neg = sum(1 for r in rows if r["lag_sec"] < 0)
    print(f"  negative lags: {neg}")

# ---------- 4. monthly lag table ----------
by_month = {}
for r in rows:
    by_month.setdefault(r["_created_dt"].strftime("%Y-%m"), []).append(r["lag_sec"])
def pct(vals, q):
    return statistics.quantiles(vals, n=100, method="inclusive")[q - 1] if len(vals) > 1 else vals[0]
mcols = ["month", "n_posts", "median_lag_sec", "p90_lag_sec", "share_gt_600s", "share_gt_3600s", "share_gt_6h", "share_gt_24h"]
with open(DATA / "posts_lag_monthly.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(mcols)
    for m in sorted(by_month):
        v = by_month[m]; n = len(v)
        w.writerow([m, n, round(statistics.median(v), 2), round(pct(v, 90), 2),
                    round(sum(x > 600 for x in v) / n, 4), round(sum(x > 3600 for x in v) / n, 4),
                    round(sum(x > 21600 for x in v) / n, 4), round(sum(x > 86400 for x in v) / n, 4)])
print("  wrote data/posts_lag_monthly.csv")
for m in sorted(by_month):
    v = by_month[m]
    print(f"  {m} n={len(v)} med={statistics.median(v):.1f} p90={pct(v,90):.1f}")

# ---------- 5. extra endpoint probes (read-only, no retries) ----------
print("== extra endpoint probes ==")
S = requests.Session(); S.headers.update(UA)
UID = user["data"]["id"]; TID = trackings[0]["id"] if trackings else None
probes = [
    f"{XT}/users/elonmusk/trackings",
    f"{XT}/users/elonmusk/trackings?includeInactive=true",
    f"{XT}/trackings?userId={UID}",
    f"{XT}/trackings?userId={UID}&includeInactive=true",
    f"{XT}/users/elonmusk/stats",
    f"{XT}/users/elonmusk/metrics",
    f"{XT}/users/elonmusk/count",
    f"{XT}/users/elonmusk/posts/count",
    f"{XT}/trackings/{TID}",
    f"{XT}/trackings/{TID}/count",
    f"{XT}/trackings/{TID}/stats",
    f"{XT}/trackings/{TID}/posts",
]
for u in probes:
    try:
        r = S.get(u, timeout=30)
        ok = r.status_code == 200 and r.headers.get("content-type", "").startswith("application/json")
        note = r.text[:100].replace("\n", " ") if ok else ""
        print(f"  {r.status_code} {'JSON' if ok else '   '} {u.replace(XT, 'XT')} {note}")
    except Exception as e:
        print(f"  ERR {u.replace(XT, 'XT')} {e}")
