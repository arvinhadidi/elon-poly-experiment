#!/usr/bin/env python3
"""Pull posts, resolved events/buckets and lead-price snapshots for related xtracker-settled
Polymarket count families. Public GET only; never places orders.
Run with cwd = elon/. Outputs data/related/<family>/{posts,buckets,snapshots}.csv"""
import re, sys, json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import get, parse_json_field, GAMMA, CLOB, XT

OUT = HERE / "data" / "related"
FAMILIES = {  # family: (series_id, xtracker handle, platform param)
    "trump_truth": (11108, "realDonaldTrump", "truth_social"),
    "whitehouse": (11335, "WhiteHouse", "x"),
    "khamenei": (11340, "khamenei_ir", "x"),
    "zelenskyy": (11349, "ZelenskyyUa", "x"),
    "nyc_mayor": (11348, "NYCMayor", "x"),
    "cz": (11347, "cz_binance", "x"),
    "tedcruz": (11334, "tedcruz", "x"),
}
LEADS = [-10] + list(range(0, 100, 5))
REL = pd.read_csv(HERE / "data" / "related_events.csv")
TODAY = datetime.now(timezone.utc).date()

def ts(s): return int(pd.Timestamp(s).timestamp())

def parse_bucket(lbl):
    lbl = lbl.strip().replace("–", "-")
    m = re.fullmatch(r"<\s*(\d+)", lbl)
    if m: return 0, int(m.group(1)) - 1
    m = re.fullmatch(r"(\d+)\s*\+", lbl)
    if m: return int(m.group(1)), 10**6
    m = re.fullmatch(r"(\d+)\s*-\s*(\d+)", lbl)
    if m: return int(m.group(1)), int(m.group(2))
    return None, None

def pull_posts(fam, handle, plat, start):
    chunks, d = [], start
    while d <= TODAY + timedelta(days=1):
        chunks.append((d, d + timedelta(days=7))); d += timedelta(days=7)
    def one(c):
        r = get(f"{XT}/users/{handle}/posts", {"platform": plat, "startDate": c[0].isoformat(), "endDate": c[1].isoformat()})
        return r.get("data", [])
    with ThreadPoolExecutor(6) as ex: res = list(ex.map(one, chunks))
    rows = [p for r in res for p in r]
    df = pd.DataFrame(rows)[["id", "createdAt", "importedAt"]].drop_duplicates("id").sort_values("createdAt")
    df.to_csv(OUT / fam / "posts.csv", index=False)
    return len(df)

def pull_events(fam, sid):
    evs, off = [], 0
    while True:
        r = get(f"{GAMMA}/events", {"series_id": sid, "closed": "true", "limit": 100, "offset": off})
        evs += r
        if len(r) < 100: break
        off += 100
    win = REL[REL.series_id == sid].set_index("event_slug")
    rows = []
    for e in evs:
        if e["slug"] not in win.index: continue
        w = win.loc[e["slug"]]
        for m in e["markets"]:
            lo, hi = parse_bucket(m.get("groupItemTitle") or "")
            op = parse_json_field(m.get("outcomePrices")); tk = parse_json_field(m.get("clobTokenIds"))
            if lo is None or not isinstance(op, list) or not isinstance(tk, list): continue
            yes = float(op[0])
            if yes not in (0.0, 1.0): continue
            rows.append(dict(event_slug=e["slug"], family=fam, window_start_utc=w.window_start_utc, window_end_utc=w.window_end_utc,
                             bucket_label=m["groupItemTitle"], bucket_lo=lo, bucket_hi=hi, yes_token=tk[0], outcome_yes=int(yes)))
    df = pd.DataFrame(rows); df.to_csv(OUT / fam / "buckets.csv", index=False)
    return df

def pull_prices(fam, b):
    ev = b.drop_duplicates("event_slug").set_index("event_slug")
    def one(r):
        S, E = ts(r.window_start_utc), ts(r.window_end_utc)
        targets = {L: int(round(S + L / 100 * (E - S))) for L in LEADS}
        lo, hi = min(targets.values()) - 900, max(targets.values()) + 900
        try:
            h = get(f"{CLOB}/prices-history", {"market": r.yes_token, "startTs": lo, "endTs": hi, "fidelity": 1}).get("history", [])
        except Exception:
            h = []
        t = np.array([x["t"] for x in h]); p = np.array([x["p"] for x in h])
        out = []
        for L, tt in targets.items():
            if len(t):
                i = np.abs(t - tt).argmin(); dt = abs(int(t[i]) - tt)
                ok = dt <= 600
            else: ok = False
            out.append(dict(event_slug=r.event_slug, yes_token=r.yes_token, lead_pct=L, target_ts=tt,
                            price=float(p[i]) if ok else np.nan, dt_sec=float(dt) if ok else np.nan))
        return out
    rows = [r for r in b.itertuples()]
    with ThreadPoolExecutor(8) as ex: res = list(ex.map(one, rows))
    df = pd.DataFrame([x for r in res for x in r]); df.to_csv(OUT / fam / "snapshots.csv", index=False)
    return df

if __name__ == "__main__":
    only = sys.argv[1:] or list(FAMILIES)
    for fam in only:
        sid, handle, plat = FAMILIES[fam]
        (OUT / fam).mkdir(parents=True, exist_ok=True)
        first = REL[REL.series_id == sid].window_start_utc.min()
        start = (pd.Timestamp(first) - pd.Timedelta(days=35)).date()
        b = pull_events(fam, sid)
        print(fam, "events", b.event_slug.nunique(), "markets", len(b), flush=True)
        print(fam, "posts", pull_posts(fam, handle, plat, start), flush=True)
        s = pull_prices(fam, b)
        print(fam, "price rows", len(s), "matched", int(s.price.notna().sum()), flush=True)
