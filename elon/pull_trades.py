#!/usr/bin/env python3
"""Pull the full trade tape for Polymarket Elon weekly + 48h tweet-count markets.

Public endpoints only (gamma-api + data-api). No keys. Never places orders.

Stages (all resumable; existing per-event parquet files are skipped):
  1. select closed weekly/48h buckets from data/events.csv
  2. map market_id -> conditionId via gamma (cached in data/raw/condition_ids.json)
  3. per event: pull every market's trades (takerOnly=false), write data/raw/trades/<slug>.parquet
  4. concatenate into data/trades_all.parquet and write data/trades_coverage.csv
  5. (--probe) test holders / leaderboard / wallet endpoints and print samples

Paging: data-api trades takes limit (tested up to 10000, effective 1000 per call is
used here) and offset (works up to offset 3000; higher offsets return 0 or 400).
Windows exceeding 4000 rows are split in half by time using start/end (inclusive).
"""
import sys, os, json, csv, time, datetime as dt, threading, argparse
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import get, parse_json_field, GAMMA, DATA  # noqa: E402

DATA_DIR = os.path.join(HERE, "data")
EVENTS_CSV = os.path.join(DATA_DIR, "events.csv")
RAW_TRADES = os.path.join(DATA_DIR, "raw", "trades")
COND_CACHE = os.path.join(DATA_DIR, "raw", "condition_ids.json")
ALL_PARQUET = os.path.join(DATA_DIR, "trades_all.parquet")
COVERAGE_CSV = os.path.join(DATA_DIR, "trades_coverage.csv")
HOLDERS_JSON = os.path.join(DATA_DIR, "raw", "holders_recent_weekly.json")

PAGE = 1000
MAX_OFFSET = 3000          # offset >=3000 with a full page -> split window by time
DROP_FIELDS = {"name", "bio", "profileImage", "profileImageOptimized"}
TODAY_END = int(dt.datetime(2026, 10, 11, tzinfo=dt.timezone.utc).timestamp())
WORKERS = 6
_lock = threading.Lock()
STATS = {"split_markets": 0, "failed_markets": []}


def ts_of(s):
    return int(dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())


def select_rows():
    rows = list(csv.DictReader(open(EVENTS_CSV)))
    return [
        r for r in rows
        if r["family"] in ("weekly", "48h")
        and r["event_closed"].strip().lower() == "true"
        and r["window_start_utc"] >= "2025-12-01"
        and not r["event_slug"].startswith("arch-")
        and r["bucket_lo"].strip() != ""
    ]


def load_cache():
    if os.path.exists(COND_CACHE):
        return json.load(open(COND_CACHE))
    return {}


def save_cache(cache):
    os.makedirs(os.path.dirname(COND_CACHE), exist_ok=True)
    json.dump(cache, open(COND_CACHE, "w"))


def condition_for(market_id, cache):
    key = str(market_id)
    if key in cache:
        return cache[key]
    g = get(f"{GAMMA}/markets/{key}")
    info = {
        "conditionId": g.get("conditionId"),
        "volume": g.get("volume"),
        "clobTokenIds": parse_json_field(g.get("clobTokenIds")),
    }
    with _lock:
        cache[key] = info
    return info


def _page(cid, s, e, off):
    p = {"market": cid, "limit": PAGE, "offset": off, "takerOnly": "false",
         "start": s, "end": e}
    return get(f"{DATA}/trades", p)


def fetch_window(cid, s, e, out, depth=0):
    """Collect all trades for cid with timestamp in [s, e] (inclusive)."""
    buf, off = [], 0
    while True:
        r = _page(cid, s, e, off)
        buf.extend(r)
        if len(r) < PAGE:
            out.extend(buf)
            return
        off += PAGE
        if off >= MAX_OFFSET:
            # window may hold more rows than offset paging can reach: split by time.
            # start/end are inclusive, so [s, mid-1] and [mid, e] neither overlap nor gap.
            if e - s < 2:
                out.extend(buf)
                with _lock:
                    print(f"  WARN dense window cid={cid[:12]} s={s} e={e}", flush=True)
                return
            with _lock:
                STATS["split_markets"] += 1
            mid = (s + e) // 2
            fetch_window(cid, s, mid - 1, out, depth + 1)
            fetch_window(cid, mid, e, out, depth + 1)
            return


def fetch_market_trades(cid, created_iso):
    s = ts_of(created_iso) - 86400
    out = []
    fetch_window(cid, s, TODAY_END, out)
    return out


def clean(rec):
    return {k: v for k, v in rec.items() if k not in DROP_FIELDS}


def main(limit_events=None):
    os.makedirs(RAW_TRADES, exist_ok=True)
    sel = select_rows()
    print(f"selected {len(sel)} market rows across {len({r['event_slug'] for r in sel})} events", flush=True)

    cache = load_cache()
    # group by event, keep order by window_start desc (most recent first)
    by_event = {}
    for r in sel:
        by_event.setdefault(r["event_slug"], []).append(r)
    events = sorted(by_event, key=lambda s: by_event[s][0]["window_start_utc"], reverse=True)
    if limit_events:
        events = events[:limit_events]

    failed_events = []
    t0 = time.time()
    for i, slug in enumerate(events, 1):
        out_path = os.path.join(RAW_TRADES, f"{slug}.parquet")
        rows = by_event[slug]
        if os.path.exists(out_path):
            continue
        # resolve condition ids
        for r in rows:
            try:
                condition_for(r["market_id"], cache)
            except Exception as ex:
                print(f"  gamma fail market {r['market_id']}: {ex}", flush=True)
        save_cache(cache)

        def work(r):
            info = cache.get(str(r["market_id"]))
            if not info or not info.get("conditionId"):
                return r, None, "no conditionId"
            try:
                recs = fetch_market_trades(info["conditionId"], r["market_created_at"])
                return r, recs, None
            except Exception as ex:
                return r, None, str(ex)[:200]

        event_recs, ok = [], True
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for r, recs, err in ex.map(work, rows):
                if err is not None:
                    ok = False
                    STATS["failed_markets"].append((r["market_id"], slug, err))
                    print(f"  FAIL {slug} market {r['market_id']}: {err}", flush=True)
                    continue
                for rec in recs:
                    d = clean(rec)
                    d["market_id"] = r["market_id"]
                    event_recs.append(d)
        if not ok:
            failed_events.append(slug)
            continue
        df = pd.DataFrame(event_recs)
        if df.empty:
            df = pd.DataFrame(columns=["proxyWallet", "side", "asset", "conditionId", "size", "price",
                                       "timestamp", "title", "slug", "icon", "eventSlug", "outcome",
                                       "outcomeIndex", "pseudonym", "transactionHash", "market_id"])
        df.to_parquet(out_path, index=False)
        print(f"[{i}/{len(events)}] {slug}: {len(df)} trades, {len(rows)} markets "
              f"({time.time()-t0:.0f}s)", flush=True)

    print(f"done pulling. failed events: {len(failed_events)}; split markets: {STATS['split_markets']}", flush=True)
    if failed_events:
        print("failed:", failed_events, flush=True)
    return by_event, cache


def build_outputs(sel_by_event, cache):
    frames = []
    cov = []
    for slug, rows in sel_by_event.items():
        p = os.path.join(RAW_TRADES, f"{slug}.parquet")
        if not os.path.exists(p):
            continue
        raw = pd.read_parquet(p)
        meta = {r["market_id"]: r for r in rows}
        if not raw.empty:
            raw["bucket_lo"] = raw["market_id"].map(lambda m: meta[m]["bucket_lo"])
            raw["bucket_hi"] = raw["market_id"].map(lambda m: meta[m]["bucket_hi"])
            raw["bucket_label"] = raw["market_id"].map(lambda m: meta[m]["bucket_label"])
            raw["outcome_yes"] = raw["market_id"].map(lambda m: meta[m]["outcome_yes"])
            raw["event_slug"] = slug
            raw["family"] = rows[0]["family"]
            raw["window_start_utc"] = rows[0]["window_start_utc"]
            raw["window_end_utc"] = rows[0]["window_end_utc"]
            frames.append(raw)
        notional = float((raw["size"] * raw["price"]).sum()) if not raw.empty else 0.0
        gamma_vol = float(rows[0]["event_volume"]) if rows[0]["event_volume"] else float("nan")
        cov.append({
            "event_slug": slug, "family": rows[0]["family"], "window_start_utc": rows[0]["window_start_utc"],
            "n_markets": len(rows), "n_trades": len(raw), "notional_usd": round(notional, 2),
            "gamma_volume": round(gamma_vol, 2), "ratio": round(notional / gamma_vol, 4) if gamma_vol else None,
        })
    all_df = pd.concat(frames, ignore_index=True)
    all_df["outcome_yes"] = pd.to_numeric(all_df["outcome_yes"], errors="coerce")
    all_df.to_parquet(ALL_PARQUET, index=False)
    pd.DataFrame(cov).to_csv(COVERAGE_CSV, index=False)
    return all_df, pd.DataFrame(cov)


def probe(sel):
    """Test holders / leaderboard / wallet endpoints. Prints samples for the probe notes."""
    import requests
    from common import UA
    # holders on the 10 most recent closed weekly events
    weekly = [r for r in sel if r["family"] == "weekly"]
    recent = []
    seen = set()
    for r in sorted(weekly, key=lambda r: r["window_start_utc"], reverse=True):
        if r["event_slug"] not in seen:
            seen.add(r["event_slug"])
            recent.append(r["event_slug"])
        if len(recent) == 10:
            break
    cache = load_cache()
    holders = {}
    for slug in recent:
        for r in [x for x in weekly if x["event_slug"] == slug]:
            info = condition_for(r["market_id"], cache)
            try:
                h = get(f"{DATA}/holders", {"market": info["conditionId"], "limit": 100})
                holders.setdefault(slug, {})[r["bucket_label"]] = h
            except Exception as ex:
                holders.setdefault(slug, {})[r["bucket_label"]] = f"ERR {str(ex)[:120]}"
    save_cache(cache)
    os.makedirs(os.path.dirname(HOLDERS_JSON), exist_ok=True)
    json.dump(holders, open(HOLDERS_JSON, "w"))
    n_ok = sum(1 for s in holders.values() for v in s.values() if isinstance(v, list))
    n_tot = sum(len(s) for s in holders.values())
    print(f"holders: {n_ok}/{n_tot} market calls ok across {len(recent)} events", flush=True)

    # leaderboards
    for label, url, params in [
        ("data-api /leaderboard", f"{DATA}/leaderboard", None),
        ("lb-api /profit", "https://lb-api.polymarket.com/profit", {"window": "all", "limit": 50}),
        ("data-api /v1/leaderboard", f"{DATA}/v1/leaderboard", {"category": "overall"}),
    ]:
        try:
            r = requests.get(url, params=params, headers=UA, timeout=30)
            print(label, r.status_code, r.text[:200].replace("\n", " "), flush=True)
        except Exception as ex:
            print(label, "EXC", ex, flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--build-only", action="store_true")
    ap.add_argument("--limit-events", type=int, default=None)
    args = ap.parse_args()
    sel = select_rows()
    if args.probe:
        probe(sel)
        sys.exit(0)
    if not args.build_only:
        by_event, cache = main(args.limit_events)
    else:
        by_event = {}
        for r in sel:
            by_event.setdefault(r["event_slug"], []).append(r)
        cache = load_cache()
    all_df, cov = build_outputs(by_event, cache)
    print(f"trades_all rows={len(all_df)} unique wallets={all_df['proxyWallet'].nunique()} "
          f"events={all_df['event_slug'].nunique()}", flush=True)
    print(f"coverage written: {len(cov)} events", flush=True)
