"""Live operational checks for the Elon tweet-count markets. Public endpoints only.

Subcommands:
  tracker      sample xtracker lag/sync state every 2 min for 40 min -> data/ops_tracker_samples.csv
  lag          tracker lag analysis from data/posts_elonmusk.csv    -> data/ops_tracker_lag.md
  books        CLOB book depth for live weekly + 48h buckets, 3 snapshots -> data/ops_books.csv
  rewards      rewards + fee fields for live Elon markets           -> data/ops_rewards.csv
  resolution   resolution risk audit                                -> data/ops_resolution.md
No order placement, no signing.
"""
import csv, datetime as dt, json, os, statistics, sys, time
from collections import Counter, defaultdict
from common import get, parse_json_field, GAMMA, CLOB, DATA, XT

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def p(name):
    return os.path.join(DATA_DIR, name)


def utc_now():
    return dt.datetime.now(dt.timezone.utc)


def iso_to_dt(s):
    if not s:
        return None
    s = s.strip().replace("Z", "+00:00")
    try:
        d = dt.datetime.fromisoformat(s)
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d


def read_events():
    with open(p("events.csv"), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def live_events(rows=None, families=None):
    rows = rows if rows is not None else read_events()
    out = [r for r in rows if r["event_closed"].strip().lower() != "true"]
    if families:
        out = [r for r in out if r["family"] in families]
    return out


def live_weekly_windows():
    seen = {}
    for r in live_events(families={"weekly"}):
        seen[r["event_slug"]] = (r["window_start_utc"], r["window_end_utc"])
    return seen


# ---------------------------------------------------------------- 1a. tracker sampler
def tracker_sample(interval_sec=120, duration_min=40):
    wins = live_weekly_windows()
    if not wins:
        raise SystemExit("no live weekly windows found")
    lo = min(dt.datetime.fromisoformat(s.replace("Z", "+00:00")) for s, _ in wins.values()).date()
    hi = max(dt.datetime.fromisoformat(e.replace("Z", "+00:00")) for _, e in wins.values()).date()
    end_excl = (hi + dt.timedelta(days=1)).isoformat()
    start = lo.isoformat()
    slugs = sorted(wins, key=lambda k: wins[k][0])
    win_spans = {k: (iso_to_dt(wins[k][0]), iso_to_dt(wins[k][1])) for k in slugs}
    cols = ["sample_ts", "minute", "lastSync", "lastSyncError"] + \
           [f"n_{k}" for k in slugs] + ["n_fetched", "newest_createdAt", "newest_importedAt"]
    out_path = p("ops_tracker_samples.csv")
    t0 = time.time()
    n_samples = duration_min * 60 // interval_sec + 1
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for i in range(n_samples):
            target = t0 + i * interval_sec
            time.sleep(max(0, target - time.time()))
            now = utc_now()
            row = {"sample_ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "minute": i * interval_sec // 60}
            try:
                user = get(f"{XT}/users/elonmusk", tries=3)["data"]
                row["lastSync"] = user.get("lastSync") or ""
                row["lastSyncError"] = user.get("lastSyncError") or ""
            except Exception as e:
                row["lastSync"] = f"ERR:{type(e).__name__}"
                row["lastSyncError"] = str(e)[:200]
            try:
                posts = get(f"{XT}/users/elonmusk/posts", tries=3,
                            params={"platform": "x", "startDate": start, "endDate": end_excl})
                posts = posts.get("data", posts) if isinstance(posts, dict) else posts
                cr = [iso_to_dt(x["createdAt"]) for x in posts]
                im = [iso_to_dt(x["importedAt"]) for x in posts if x.get("importedAt")]
                for k in slugs:
                    a, b = win_spans[k]
                    row[f"n_{k}"] = sum(1 for c in cr if c and a <= c < b)
                row["n_fetched"] = len(posts)
                row["newest_createdAt"] = max(cr).strftime("%Y-%m-%dT%H:%M:%SZ") if cr else ""
                row["newest_importedAt"] = max(im).strftime("%Y-%m-%dT%H:%M:%SZ") if im else ""
            except Exception as e:
                row["n_fetched"] = f"ERR:{type(e).__name__}"
            w.writerow([row.get(c, "") for c in cols])
            f.flush()
            print(row, flush=True)
    print(f"wrote {out_path}")


# ---------------------------------------------------------------- 2. book depth
def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def book_metrics(book):
    bids = sorted(((_f(b["price"]), _f(b["size"])) for b in book.get("bids", [])
                   if _f(b.get("price")) is not None and _f(b.get("size")) is not None
                   and _f(b["size"]) > 0), reverse=True)
    asks = sorted(((_f(a["price"]), _f(a["size"])) for a in book.get("asks", [])
                   if _f(a.get("price")) is not None and _f(a.get("size")) is not None
                   and _f(a["size"]) > 0))
    out = {"best_bid": None, "best_ask": None, "spread": None, "book_mid": None,
           "ask_size_touch": None, "ask_usd_touch": None, "ask_usd_1c": None,
           "ask_usd_2c": None, "bid_usd_2c": None, "n_bid_levels": len(bids), "n_ask_levels": len(asks)}
    if asks:
        ba = asks[0][0]
        out["best_ask"] = ba
        out["ask_size_touch"] = sum(s for p_, s in asks if abs(p_ - ba) < 1e-9)
        out["ask_usd_touch"] = sum(p_ * s for p_, s in asks if abs(p_ - ba) < 1e-9)
        out["ask_usd_1c"] = sum(p_ * s for p_, s in asks if p_ <= ba + 0.01 + 1e-9)
        out["ask_usd_2c"] = sum(p_ * s for p_, s in asks if p_ <= ba + 0.02 + 1e-9)
    if bids:
        bb = bids[0][0]
        out["best_bid"] = bb
        out["bid_usd_2c"] = sum(p_ * s for p_, s in bids if p_ >= bb - 0.02 - 1e-9)
    if asks and bids:
        out["spread"] = out["best_ask"] - out["best_bid"]
        out["book_mid"] = (out["best_ask"] + out["best_bid"]) / 2
    return out


def books(n_snap=3, gap_sec=900):
    import statistics as st
    rows = live_events(families={"weekly", "48h"})
    seen, targets = set(), []
    for r in rows:
        if r["yes_token"] in seen:
            continue
        seen.add(r["yes_token"])
        targets.append(r)
    fields = ["snapshot_ts", "event_slug", "family", "bucket_label", "market_id", "yes_token", "has_book",
              "book_mid", "best_bid", "best_ask", "spread", "ask_size_touch", "ask_usd_touch",
              "ask_usd_1c", "ask_usd_2c", "bid_usd_2c", "n_bid_levels", "n_ask_levels"]
    path = p("ops_books.csv")
    t0 = time.time()
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for s in range(n_snap):
            time.sleep(max(0, t0 + s * gap_sec - time.time()))
            ts = utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")
            nb = 0
            for r in targets:
                base = {"snapshot_ts": ts, "event_slug": r["event_slug"], "family": r["family"],
                        "bucket_label": r["bucket_label"], "market_id": r["market_id"], "yes_token": r["yes_token"]}
                try:
                    book = get(f"{CLOB}/book", params={"token_id": r["yes_token"]}, tries=3)
                    m = book_metrics(book)
                    base["has_book"] = True
                    nb += 1
                except Exception as e:
                    # 404 "No orderbook exists" = market closed / not accepting orders
                    m = book_metrics({})
                    base["has_book"] = False
                w.writerow({**base, **{k: ("" if v is None else (round(v, 4) if isinstance(v, float) else v))
                                       for k, v in m.items() if k in fields}, "book_mid": ("" if m["book_mid"] is None else round(m["book_mid"], 4))})
            f.flush()
            print(f"snapshot {s} {ts}: {nb}/{len(targets)} buckets with a live book", flush=True)
    # summary per event (averaged over snapshots)
    with open(path, newline="", encoding="utf-8") as f:
        data = list(csv.DictReader(f))
    by_ev = defaultdict(lambda: defaultdict(list))
    spreads = defaultdict(list)
    for d in data:
        if d["has_book"] != "True" or d["best_ask"] == "":
            continue
        ba = float(d["best_ask"])
        by_ev[d["event_slug"]][d["snapshot_ts"]].append(d)
        if d["spread"] != "":
            cls = "cheap(<=0.15)" if ba <= 0.15 else ("mid(0.15-0.50)" if ba <= 0.50 else "expensive(>0.50)")
            spreads[(d["event_slug"], cls)].append(float(d["spread"]))
    lines = ["event_slug,n_snapshots,n_buckets_cheap_le50,ask_usd_1c_le50_mean,ask_usd_2c_le50_mean,"
             "median_spread_cheap,median_spread_mid,median_spread_expensive,n_buckets_live_last"]
    for ev in sorted(by_ev):
        snaps = by_ev[ev]
        c1, c2, nb_ = [], [], []
        for ts_, lst in snaps.items():
            cheap = [d for d in lst if float(d["best_ask"]) <= 0.50]
            c1.append(sum(float(d["ask_usd_1c"]) for d in cheap))
            c2.append(sum(float(d["ask_usd_2c"]) for d in cheap))
            nb_.append(len(cheap))
        med = lambda k: (f"{st.median(spreads[(ev, k)]):.4f}" if spreads.get((ev, k)) else "")
        lines.append(",".join([ev, str(len(snaps)), str(round(st.mean(nb_))), f"{st.mean(c1):.0f}",
                               f"{st.mean(c2):.0f}", med("cheap(<=0.15)"), med("mid(0.15-0.50)"),
                               med("expensive(>0.50)"), str(len(snaps[max(snaps)]))]))
    with open(p("ops_books_summary.csv"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


# ---------------------------------------------------------------- 3. rewards / fees
def fetch_rewards_current():
    out, cursor = [], None
    while True:
        params = {"next_cursor": cursor} if cursor else None
        r = get(f"{CLOB}/rewards/markets/current", params=params)
        out.extend(r.get("data", []))
        cursor = r.get("next_cursor")
        if not cursor or cursor == "LTE=":
            break
    return out


def rewards():
    rew = fetch_rewards_current()
    rew_by_cid = {str(x.get("condition_id", "")).lower(): x for x in rew}
    print(f"rewards/markets/current: {len(rew)} markets")
    rows = live_events()
    seen, targets = set(), []
    for r in rows:
        if r["market_id"] not in seen:
            seen.add(r["market_id"])
            targets.append(r)
    fields = ["market_id", "event_slug", "family", "bucket_label", "condition_id", "in_rewards_current",
              "rewards_daily_rate", "rewards_config_rate_sum", "rewards_min_size", "rewards_max_spread",
              "gamma_rewardsMinSize", "gamma_rewardsMaxSpread", "maker_base_fee", "taker_base_fee",
              "gamma_makerBaseFee", "gamma_takerBaseFee", "feesEnabled", "feeType", "fee_rate",
              "fee_exponent", "fee_takerOnly", "fee_rebateRate", "clob_fee_keys", "clob_accepting_orders"]
    out = []
    for r in targets:
        row = {k: "" for k in fields}
        row.update({"market_id": r["market_id"], "event_slug": r["event_slug"], "family": r["family"],
                    "bucket_label": r["bucket_label"]})
        try:
            g = get(f"{GAMMA}/markets/{r['market_id']}", tries=3)
            cid = g.get("conditionId", "")
            row["condition_id"] = cid
            row["gamma_rewardsMinSize"] = g.get("rewardsMinSize", "")
            row["gamma_rewardsMaxSpread"] = g.get("rewardsMaxSpread", "")
            row["gamma_makerBaseFee"] = g.get("makerBaseFee", "")
            row["gamma_takerBaseFee"] = g.get("takerBaseFee", "")
            row["feesEnabled"] = g.get("feesEnabled", "")
            row["feeType"] = g.get("feeType", "") or ""
            fs = g.get("feeSchedule") or {}
            if fs:
                row["fee_rate"], row["fee_exponent"] = fs.get("rate", ""), fs.get("exponent", "")
                row["fee_takerOnly"], row["fee_rebateRate"] = fs.get("takerOnly", ""), fs.get("rebateRate", "")
            x = rew_by_cid.get(str(cid).lower())
            row["in_rewards_current"] = x is not None
            if x:
                row["rewards_daily_rate"] = x.get("total_daily_rate", x.get("native_daily_rate", ""))
                row["rewards_config_rate_sum"] = sum(float(c.get("rate_per_day", 0) or 0) for c in x.get("rewards_config", []))
                row["rewards_min_size"] = x.get("rewards_min_size", "")
                row["rewards_max_spread"] = x.get("rewards_max_spread", "")
            if cid:
                c = get(f"{CLOB}/markets/{cid}", tries=3)
                row["maker_base_fee"] = c.get("maker_base_fee", "")
                row["taker_base_fee"] = c.get("taker_base_fee", "")
                row["clob_accepting_orders"] = c.get("accepting_orders", "")
                row["clob_fee_keys"] = ";".join(sorted(k for k in c if "fee" in k.lower() or "rebate" in k.lower()))
        except Exception as e:
            row["clob_fee_keys"] = f"ERR:{type(e).__name__}"
        out.append(row)
    with open(p("ops_rewards.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out)
    n_rew = sum(1 for x in out if x["in_rewards_current"] is True)
    print(f"wrote data/ops_rewards.csv: {len(out)} live markets, {n_rew} in rewards/current")
    fee_vals = Counter((str(x["maker_base_fee"]), str(x["taker_base_fee"]), str(x["feeType"])) for x in out)
    print("fee combos (maker,taker,feeType):", fee_vals.most_common(10))


# ---------------------------------------------------------------- 1b. tracker lag analysis
def _pct(sorted_vals, q):
    if not sorted_vals:
        return float("nan")
    k = (len(sorted_vals) - 1) * q
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def _ts(s):
    return iso_to_dt(s)


def lag():
    with open(p("posts_elonmusk.csv"), newline="", encoding="utf-8") as f:
        posts = list(csv.DictReader(f))
    for x in posts:
        x["_c"] = _ts(x["createdAt"])
        x["_i"] = _ts(x["importedAt"]) if x["importedAt"] else None
        x["_lag"] = (x["_i"] - x["_c"]).total_seconds() if x["_i"] and x["_c"] else None
    n_noimp = sum(1 for x in posts if x["_i"] is None)
    print(f"posts={len(posts)} missing importedAt={n_noimp}")
    md = ["# Tracker lag (xtracker, elonmusk X posts)", "",
          f"Generated {utc_now().strftime('%Y-%m-%d %H:%M UTC')} from data/posts_elonmusk.csv "
          f"({len(posts)} posts, {n_noimp} without importedAt). lag = importedAt - createdAt.", ""]

    # (a) monthly percentiles
    bym = defaultdict(list)
    for x in posts:
        if x["_lag"] is not None:
            bym[x["_c"].strftime("%Y-%m")].append(x["_lag"])
    md += ["## (a) Lag distribution per month (by createdAt month)", "",
           "| month | n | p50 s | p90 s | p99 s | max s | max h | share >1h |",
           "|---|---|---|---|---|---|---|---|"]
    for mth in sorted(bym):
        v = sorted(bym[mth])
        md.append(f"| {mth} | {len(v)} | {_pct(v,.5):.0f} | {_pct(v,.9):.0f} | {_pct(v,.99):.0f} | "
                  f"{v[-1]:.0f} | {v[-1]/3600:.1f} | {sum(1 for z in v if z>3600)/len(v):.3f} |")
    md.append("")

    # (b) import batches: >=5 posts sharing an importedAt minute, median lag > 1h
    grp = defaultdict(list)
    for x in posts:
        if x["_i"] is not None and x["_lag"] is not None:
            grp[x["_i"].strftime("%Y-%m-%dT%H:%M")].append(x)
    batches = []
    for minute, lst in grp.items():
        if len(lst) >= 5:
            lags = sorted(x["_lag"] for x in lst)
            if _pct(lags, .5) > 3600:
                batches.append((minute, len(lst), lags[-1], lags[0], _pct(lags, .5)))
    batches.sort()
    md += ["## (b) Import batches (>=5 posts with identical importedAt minute, median createdAt > 1h earlier)", "",
           f"{len(batches)} batches. Columns: importedAt minute (UTC), n posts, max delay h, min delay h.", "",
           "| importedAt (UTC, minute) | n | max delay h | min delay h |", "|---|---|---|---|"]
    for minute, n, mx, mn, _ in batches:
        md.append(f"| {minute} | {n} | {mx/3600:.1f} | {mn/3600:.1f} |")
    md.append("")

    # (c) gaps between consecutive importedAt values
    imps = sorted(x["_i"] for x in posts if x["_i"] is not None)
    cre = sorted(x["_c"] for x in posts if x["_c"] is not None)
    import bisect
    gaps = []
    for a, b in zip(imps, imps[1:]):
        if (b - a).total_seconds() > 0:
            lo = bisect.bisect_right(cre, a)
            hi = bisect.bisect_left(cre, b)
            gaps.append({"start": a, "end": b, "hours": (b - a).total_seconds() / 3600,
                         "created_in_gap": hi - lo})
    bym_gap = defaultdict(list)
    for g in gaps:
        bym_gap[g["start"].strftime("%Y-%m")].append(g)
    md += ["## (c) Gaps with no importedAt (longest gap per month)", "",
           "Gap = time between consecutive importedAt values. `created_in_gap` = posts whose createdAt falls inside "
           "the gap; >0 means posts existed but were not yet imported (outage-like). 0 means probably just no posts "
           "(quiet period), so most gaps are not outages.", "",
           "| month | longest gap h | start (UTC) | end (UTC) | created_in_gap |", "|---|---|---|---|---|"]
    for mth in sorted(bym_gap):
        g = max(bym_gap[mth], key=lambda z: z["hours"])
        md.append(f"| {mth} | {g['hours']:.2f} | {g['start']:%Y-%m-%d %H:%M} | {g['end']:%Y-%m-%d %H:%M} | {g['created_in_gap']} |")
    md += ["", "Top 10 gaps overall:", "",
           "| rank | gap h | start (UTC) | end (UTC) | created_in_gap |", "|---|---|---|---|---|"]
    for i, g in enumerate(sorted(gaps, key=lambda z: -z["hours"])[:10], 1):
        md.append(f"| {i} | {g['hours']:.2f} | {g['start']:%Y-%m-%d %H:%M} | {g['end']:%Y-%m-%d %H:%M} | {g['created_in_gap']} |")
    md.append("")

    # (d) late-imported share per closed weekly window since 2025-12
    es = list(csv.DictReader(open(p("events_summary.csv"), newline="", encoding="utf-8")))
    md += ["## (d) Posts that would only appear after the window closed (closed weekly events since 2025-12)", "",
           "late = posts with createdAt inside [start,end) and importedAt > end. frac = late / final count.", "",
           "| event | window start | window end | final n | late n | frac late | max lag h in window |",
           "|---|---|---|---|---|---|---|"]
    d_rows = []
    for e in es:
        if e["family"] != "weekly" or e["closed"].strip().lower() != "true":
            continue
        s_, e_ = _ts(e["window_start_utc"]), _ts(e["window_end_utc"])
        if s_ is None or s_ < dt.datetime(2025, 12, 1, tzinfo=dt.timezone.utc):
            continue
        inw = [x for x in posts if x["_c"] and s_ <= x["_c"] < e_]
        late = [x for x in inw if x["_i"] is not None and x["_i"] > e_]
        mx = max((x["_lag"] for x in inw if x["_lag"] is not None), default=0)
        frac = len(late) / len(inw) if inw else float("nan")
        d_rows.append((e["event_slug"], len(inw), len(late), frac))
        md.append(f"| {e['event_slug']} | {e['window_start_utc']} | {e['window_end_utc']} | {len(inw)} | "
                  f"{len(late)} | {frac:.4f} | {mx/3600:.2f} |")
    md.append("")
    with open(p("ops_tracker_lag.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(f"wrote data/ops_tracker_lag.md: {len(batches)} batches, {len(gaps)} gaps, {len(d_rows)} windows")
    print("top gaps:", [(round(g['hours'], 1), f"{g['start']:%Y-%m-%d %H:%M}", g['created_in_gap'])
                        for g in sorted(gaps, key=lambda z: -z['hours'])[:10]])
    print("late windows with frac>0:", sum(1 for r in d_rows if r[2] > 0), "of", len(d_rows))


# ---------------------------------------------------------------- 4. resolution risk
def _gamma_fetch_closed(market_ids, cache_path):
    from concurrent.futures import ThreadPoolExecutor
    cache = {}
    if os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            cache = json.load(f)
    todo = [m for m in market_ids if m not in cache]

    def one(mid):
        try:
            g = get(f"{GAMMA}/markets/{mid}", tries=4)
            return mid, {k: g.get(k) for k in g if any(s in k.lower() for s in
                         ["uma", "resol", "dispute", "closed", "automatically", "outcomeprices",
                          "outcome", "question", "conditionid", "endDate".lower(), "endate", "question"])} | \
                         {"_error": None}
        except Exception as e:
            return mid, {"_error": f"{type(e).__name__}: {str(e)[:120]}"}

    with ThreadPoolExecutor(max_workers=6) as ex:
        for i, (mid, data) in enumerate(ex.map(one, todo), 1):
            cache[mid] = data
            if i % 500 == 0:
                print(f"  gamma fetched {i}/{len(todo)}", flush=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f)
    return cache


def _status_list(v):
    if isinstance(v, list):
        return v
    if isinstance(v, str) and v.strip().startswith("["):
        try:
            return json.loads(v)
        except Exception:
            return [v]
    return [v] if v else []


def resolution():
    ev_rows = read_events()
    closed = [r for r in ev_rows if r["event_closed"].strip().lower() == "true"]
    # (1) distinct uma_status per market in events.csv
    st_by_mkt = defaultdict(set)
    fam_by_mkt = {}
    slug_by_mkt = {}
    for r in closed:
        st_by_mkt[r["market_id"]].add(r["uma_status"] or "<blank>")
        fam_by_mkt[r["market_id"]] = r["family"]
        slug_by_mkt[r["market_id"]] = r["event_slug"]
    status_counts = Counter(s for v in st_by_mkt.values() for s in v)
    nonplain_mkts = {m for m, v in st_by_mkt.items() if v - {"resolved"}}
    nonplain_events = {slug_by_mkt[m] for m in nonplain_mkts}
    all_events = {r["event_slug"] for r in closed}
    print(f"closed rows={len(closed)} markets={len(st_by_mkt)} events={len(all_events)}")
    print("uma_status counts over closed markets:", status_counts.most_common())

    # (2) gamma per-market UMA history for all closed markets
    cache = _gamma_fetch_closed(sorted(st_by_mkt), p("..", "data", "raw", "gamma_closed_markets.json")
                                if False else os.path.join(DATA_DIR, "raw", "gamma_closed_markets.json"))
    os.makedirs(os.path.join(DATA_DIR, "raw"), exist_ok=True)
    errs = sum(1 for m in st_by_mkt if cache.get(m, {}).get("_error"))
    g_status = Counter()
    g_multi_prop = set()
    g_dispute = set()
    g_mismatch = []
    keys_seen = Counter()
    for m in st_by_mkt:
        c = cache.get(m, {})
        if c.get("_error"):
            continue
        for k in c:
            keys_seen[k] += 1
        stl = _status_list(c.get("umaResolutionStatuses"))
        cur = c.get("umaResolutionStatus") or ""
        g_status[cur or "<blank>"] += 1
        if sum(1 for s in stl if str(s).lower() == "proposed") >= 2:
            g_multi_prop.add(m)
        if any(("dispute" in str(s).lower()) or ("challenge" in str(s).lower()) for s in stl + [cur]):
            g_dispute.add(m)
        local = st_by_mkt[m] - {"<blank>"}
        if local and cur and cur not in local:
            g_mismatch.append((m, slug_by_mkt[m], sorted(local), cur))
    uma_fields = sorted(k for k in keys_seen if any(s in k.lower() for s in ["uma", "resol", "dispute"]))

    # (3) tracker count vs winning bucket per closed event
    es = list(csv.DictReader(open(p("events_summary.csv"), newline="", encoding="utf-8")))
    posts = list(csv.DictReader(open(p("posts_elonmusk.csv"), newline="", encoding="utf-8")))
    pc = [iso_to_dt(x["createdAt"]) for x in posts]
    buckets_by_ev = defaultdict(set)
    for r in ev_rows:
        buckets_by_ev[r["event_slug"]].add((r["bucket_label"], r["bucket_lo"], r["bucket_hi"]))
    dis, checked, disagree_rows = 0, 0, []
    for e in es:
        if e["closed"].strip().lower() != "true":
            continue
        s_, e_ = iso_to_dt(e["window_start_utc"]), iso_to_dt(e["window_end_utc"])
        if not s_ or not e_:
            continue
        n = sum(1 for c in pc if c and s_ <= c < e_)
        win = (e["winning_lo"], e["winning_hi"])
        matched = None
        for lbl, lo, hi in buckets_by_ev.get(e["event_slug"], []):
            try:
                lo_f = float(lo) if lo not in ("", None) else 0
                hi_f = float(hi) if hi not in ("", None) else 1e9
            except ValueError:
                continue
            if lo_f <= n <= hi_f:
                matched = (lo, hi, lbl)
                break
        checked += 1
        if matched is None or (matched[0], matched[1]) != win:
            dis += 1
            disagree_rows.append((e["event_slug"], e["family"], n, win, matched[2] if matched else "no bucket"))

    # (4) sample gamma fields report
    sample = []
    for m in list(st_by_mkt)[:: max(1, len(st_by_mkt) // 12)][:12]:
        c = cache.get(m, {})
        sample.append((m, slug_by_mkt[m], c.get("umaResolutionStatus"), c.get("umaResolutionStatuses"),
                       c.get("automaticallyResolved"), c.get("closedTime")))

    md = ["# Resolution risk audit (closed Elon weekly/48h/monthly/daily events)", "",
          f"Generated {utc_now().strftime('%Y-%m-%d %H:%M UTC')}. Sources: data/events.csv (uma_status), "
          "Gamma /markets/<id> (umaResolutionStatus, umaResolutionStatuses), data/events_summary.csv vs "
          "data/posts_elonmusk.csv counts with window [start,end) on createdAt.", "",
          "## Local uma_status (events.csv)", "",
          f"- closed events: {len(all_events)}; closed markets: {len(st_by_mkt)}",
          f"- status values per market: " + ", ".join(f"{k}={v}" for k, v in status_counts.most_common()),
          f"- markets with anything other than plain `resolved`: {len(nonplain_mkts)} "
          f"({', '.join(sorted({s for m in nonplain_mkts for s in st_by_mkt[m] - {'resolved'}}))})",
          f"- events affected: {len(nonplain_events)} of {len(all_events)}", "",
          "## Gamma UMA history (all closed markets in events.csv)", "",
          f"- fetched {len(st_by_mkt) - errs}/{len(st_by_mkt)} markets ({errs} errors)",
          f"- current umaResolutionStatus: " + ", ".join(f"{k}={v}" for k, v in g_status.most_common()),
          f"- markets with >=2 'proposed' entries in umaResolutionStatuses: {len(g_multi_prop)}",
          f"- markets with any dispute/challenge entry: {len(g_dispute)}",
          f"- markets where local uma_status disagrees with Gamma current status: {len(g_mismatch)}",
          f"- Gamma fields with uma/resolution/dispute in name: {', '.join(uma_fields)}", "",
          "Sample (every ~N-th market):", "",
          "| market_id | event | gamma umaResolutionStatus | umaResolutionStatuses | automaticallyResolved | closedTime |",
          "|---|---|---|---|---|---|"]
    for row in sample:
        md.append("| " + " | ".join(str(x) for x in row) + " |")
    md += ["", "## Tracker count vs gamma winning bucket (closed events in events_summary.csv)", "",
           f"- checked {checked} closed events; disagreements: {dis}",
           "", "| event | family | tracker n (createdAt in window) | gamma winning bucket lo/hi | tracker-matching bucket |",
           "|---|---|---|---|---|"]
    for r in disagree_rows:
        md.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3][0]}-{r[3][1]} | {r[4]} |")
    md += ["", "## Web search", "", "(filled in separately)", ""]
    with open(p("ops_resolution.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(f"wrote data/ops_resolution.md; nonplain markets={len(nonplain_mkts)} events={len(nonplain_events)} "
          f"multi_proposed={len(g_multi_prop)} dispute={len(g_dispute)} gamma_mismatch={len(g_mismatch)} "
          f"tracker_disagree={dis}/{checked}")


# ---------------------------------------------------------------- main
if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "tracker":
        tracker_sample()
    elif cmd == "books":
        books()
    elif cmd == "rewards":
        rewards()
    elif cmd == "lag":
        lag()
    elif cmd == "resolution":
        resolution()
    else:
        raise SystemExit(f"unknown or unimplemented subcommand: {cmd!r}")
