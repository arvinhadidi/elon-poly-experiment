"""Pull YES-token price histories for bucket markets and build price snapshots.

Public endpoints only (CLOB prices-history). Read-only: never places orders.

Usage:
  python3 pull_prices.py            # resumable: skips events whose parquet exists
  python3 pull_prices.py --force    # re-pull every event
  python3 pull_prices.py --snapshots-only

Outputs:
  data/raw/prices/<event_slug>.parquet   columns: token, t (int unix), p (float)
  data/price_snapshots.csv               one row per event x bucket x lead
  data/price_sums.csv                    one row per event x lead
"""
import argparse
import os
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import get, parse_json_field, CLOB, GAMMA  # noqa: E402  (GAMMA/parse_json_field unused, imported per spec)

HERE = os.path.dirname(os.path.abspath(__file__))
EVENTS_CSV = os.path.join(HERE, "data", "events.csv")
RAW_DIR = os.path.join(HERE, "data", "raw", "prices")
SNAP_CSV = os.path.join(HERE, "data", "price_snapshots.csv")
SUMS_CSV = os.path.join(HERE, "data", "price_sums.csv")

FAMILIES = ["weekly", "48h", "daily", "monthly"]
MIN_WINDOW_START = pd.Timestamp("2025-12-01T00:00:00Z")
PRE_PAD_SEC = 7 * 86400
POST_PAD_SEC = 3600
CHUNK_SEC = 2 * 86400
MAX_SINGLE_SEC = 14 * 86400   # API rejects longer intervals (400 "interval is too long")
SUSPICIOUS_FRAC = 0.5          # fewer than 50% of expected 1-min points => re-split
SNAP_TOLERANCE_SEC = 600
LEADS = [-10, 0] + list(range(5, 100, 5))   # 5..95 inclusive
WORKERS = 8
TOKEN_TRIES = 3


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def load_events():
    df = pd.read_csv(EVENTS_CSV, dtype=str, keep_default_na=False)
    df = df[df["family"].isin(FAMILIES)]
    df = df[pd.to_datetime(df["window_start_utc"], utc=True) >= MIN_WINDOW_START]
    df = df[~df["event_slug"].str.startswith("arch-")]
    df = df[df["bucket_lo"].str.strip() != ""]
    df = df[df["yes_token"].str.strip() != ""]
    df = df.copy()
    df["_ws"] = pd.to_datetime(df["window_start_utc"], utc=True)
    df["_we"] = pd.to_datetime(df["window_end_utc"], utc=True)
    df["_mc"] = pd.to_datetime(df["market_created_at"], utc=True, errors="coerce")
    return df


def _call(token, start, end):
    """One prices-history call. Retries 429/5xx/network errors; a 4xx (e.g. 'interval too long') raises at once."""
    params = {"market": token, "startTs": start, "endTs": end, "fidelity": 1}
    for i in range(5):
        try:
            return get(f"{CLOB}/prices-history", params=params, tries=1).get("history", []) or []
        except Exception as ex:  # noqa: BLE001
            resp = getattr(ex, "response", None)
            if resp is not None and resp.status_code < 500 and resp.status_code != 429:
                raise
            if i == 4:
                raise
            time.sleep(2 ** i)


def _chunked(token, start, end, chunk):
    out, s = [], start
    while s < end:
        e = min(s + chunk, end)
        out.extend(_call(token, s, e))
        s = e
    return out


def fetch_range(token, start, end):
    """Fetch [start, end]. The API rejects intervals over ~14 days, so those are split into 7-day chunks.
    A sparse answer for a long range is re-split into 2-day chunks."""
    if (end - start) > MAX_SINGLE_SEC:
        return _chunked(token, start, end, 7 * 86400)
    hist = _call(token, start, end)
    minutes = (end - start) / 60.0
    if (end - start) > CHUNK_SEC and len(hist) < SUSPICIOUS_FRAC * minutes:
        hist2 = _chunked(token, start, end, CHUNK_SEC)
        log(f"    sparse ({len(hist)} pts / {minutes:.0f} min) -> 2-day re-split gave {len(hist2)} pts")
        hist = hist2
    return hist


def pull_token(token, start, end):
    last_err = None
    for attempt in range(TOKEN_TRIES):
        try:
            hist = fetch_range(token, start, end)
            seen = {}
            for pt in hist:
                t = int(pt["t"])
                if t not in seen:
                    seen[t] = float(pt["p"])
            return [(token, t, p) for t, p in sorted(seen.items())]
        except Exception as ex:  # noqa: BLE001
            last_err = ex
            time.sleep(2 ** attempt * 2)
    raise RuntimeError(f"token {token[:12]}.. failed after {TOKEN_TRIES} tries: {last_err}")


def pull_event(slug, rows, force):
    path = os.path.join(RAW_DIR, f"{slug}.parquet")
    if os.path.exists(path) and not force:
        return slug, "skipped", 0, 0
    now = int(time.time())
    recs = []
    for _, r in rows.iterrows():
        ws = int(r["_ws"].timestamp())
        we = int(r["_we"].timestamp())
        mc = r["_mc"]
        start = ws - PRE_PAD_SEC
        if pd.notna(mc):
            start = max(int(mc.timestamp()), start)
        end = min(we + POST_PAD_SEC, now)   # no point asking for the future
        if end <= start:
            continue
        recs.extend(pull_token(r["yes_token"], start, end))
    df = pd.DataFrame(recs, columns=["token", "t", "p"])
    df["t"] = df["t"].astype("int64")
    df["p"] = df["p"].astype("float64")
    tmp = path + ".tmp"
    df.to_parquet(tmp, index=False)
    os.replace(tmp, path)
    return slug, "ok", len(rows["yes_token"].unique()), len(df)


def run_pulls(events, force, workers):
    os.makedirs(RAW_DIR, exist_ok=True)
    groups = list(events.groupby("event_slug", sort=False))
    stats = {"ok": 0, "skipped": 0, "failed": 0}
    tokens_done = {f: 0 for f in FAMILIES}
    failures = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(pull_event, slug, g, force): (slug, g) for slug, g in groups}
        for i, fut in enumerate(as_completed(futs), 1):
            slug, g = futs[fut]
            try:
                _, status, ntok, npts = fut.result()
                stats[status] += 1
                if status == "ok":
                    tokens_done[g["family"].iloc[0]] += ntok
                if i % 20 == 0 or i == len(groups):
                    log(f"[{i}/{len(groups)}] {slug} {status} tokens={ntok} pts={npts}")
            except Exception as ex_:  # noqa: BLE001
                stats["failed"] += 1
                failures.append((slug, str(ex_)))
                log(f"[{i}/{len(groups)}] FAILED {slug}: {ex_}")
    log(f"pulls done: {stats}")
    return stats, tokens_done, failures


def nearest_price(ts_arr, p_arr, targets):
    """For each target, nearest point by |t - target|; NaN if >600s away."""
    n = len(ts_arr)
    out_p = np.full(len(targets), np.nan)
    out_t = np.full(len(targets), np.nan)
    if n == 0:
        return out_p, out_t
    idx = np.searchsorted(ts_arr, targets)
    lo = np.clip(idx - 1, 0, n - 1)
    hi = np.clip(idx, 0, n - 1)
    d_lo = np.abs(ts_arr[lo] - targets)
    d_hi = np.abs(ts_arr[hi] - targets)
    pick = np.where(d_lo <= d_hi, lo, hi)
    dist = np.minimum(d_lo, d_hi)
    ok = dist <= SNAP_TOLERANCE_SEC
    out_p[ok] = p_arr[pick[ok]]
    out_t[ok] = ts_arr[pick[ok]]
    return out_p, out_t


def build_snapshots(events):
    snap_rows, sum_rows = [], []
    groups = list(events.groupby("event_slug", sort=False))
    missing_files = 0
    for slug, g in groups:
        path = os.path.join(RAW_DIR, f"{slug}.parquet")
        if not os.path.exists(path):
            missing_files += 1      # failed pull: leave out rather than write all-NaN rows
            continue
        raw = pd.read_parquet(path)
        series = {}
        for tok, sub in raw.groupby("token"):
            sub = sub.sort_values("t").drop_duplicates("t")
            series[tok] = (sub["t"].to_numpy(dtype=np.int64).astype(np.float64),
                           sub["p"].to_numpy(dtype=np.float64))
        ws = g["_ws"].iloc[0]
        we = g["_we"].iloc[0]
        ws_ts = ws.timestamp()
        dur = we.timestamp() - ws_ts
        family = g["family"].iloc[0]
        for lead in LEADS:
            T = ws_ts + lead / 100.0 * dur
            tgt = np.full(len(g), T)
            prices = np.full(len(g), np.nan)
            pts = np.full(len(g), np.nan)
            for k, tok in enumerate(g["yes_token"].values):
                if tok not in series:
                    continue
                ts_arr, p_arr = series[tok]
                pp, tt = nearest_price(ts_arr, p_arr, np.array([T]))
                prices[k], pts[k] = pp[0], tt[0]
            tgt_int = int(round(T))
            for k, (_, r) in enumerate(g.iterrows()):
                snap_rows.append({
                    "event_slug": slug,
                    "family": family,
                    "window_start_utc": r["window_start_utc"],
                    "window_end_utc": r["window_end_utc"],
                    "bucket_label": r["bucket_label"],
                    "bucket_lo": r["bucket_lo"],
                    "bucket_hi": r["bucket_hi"],
                    "yes_token": r["yes_token"],
                    "outcome_yes": r["outcome_yes"],
                    "lead_pct": lead,
                    "target_ts": tgt_int,
                    "price": prices[k],
                    "price_ts": pts[k],
                    "dt_sec": (pts[k] - T) if not np.isnan(pts[k]) else np.nan,
                })
            n_priced = int(np.sum(~np.isnan(prices)))
            sum_rows.append({
                "event_slug": slug,
                "family": family,
                "window_start_utc": g["window_start_utc"].iloc[0],
                "window_end_utc": g["window_end_utc"].iloc[0],
                "lead_pct": lead,
                "target_ts": tgt_int,
                "sum_p": float(np.nansum(prices)) if n_priced else np.nan,
                "n_priced": n_priced,
                "n_buckets": len(g),
            })
    if missing_files:
        log(f"WARNING: {missing_files} events had no raw parquet and are left out of the CSVs")
    snaps = pd.DataFrame(snap_rows)
    sums = pd.DataFrame(sum_rows)
    snaps.to_csv(SNAP_CSV, index=False)
    sums.to_csv(SUMS_CSV, index=False)
    log(f"wrote {SNAP_CSV} ({len(snaps)} rows), {SUMS_CSV} ({len(sums)} rows)")
    return snaps, sums


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-pull events that already have a parquet")
    ap.add_argument("--snapshots-only", action="store_true", help="skip pulls, build CSVs from existing parquet")
    ap.add_argument("--workers", type=int, default=WORKERS)
    ap.add_argument("--limit", type=int, default=0, help="only first N events (testing)")
    args = ap.parse_args()

    events = load_events()
    slugs = list(dict.fromkeys(events["event_slug"]))
    if args.limit:
        keep = set(slugs[: args.limit])
        events = events[events["event_slug"].isin(keep)]
    log(f"events={events['event_slug'].nunique()} tokens={events['yes_token'].nunique()} "
        f"rows={len(events)} by family={events.groupby('family')['event_slug'].nunique().to_dict()}")

    if not args.snapshots_only:
        stats, tokens_done, failures = run_pulls(events, args.force, args.workers)
        log(f"tokens pulled per family (this run, ok events): {tokens_done}")
        for slug, err in failures:
            log(f"FAILED {slug}: {err}")
    build_snapshots(events)


if __name__ == "__main__":
    main()
