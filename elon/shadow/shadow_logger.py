#!/usr/bin/env python3
"""SHADOW logger for Polymarket Elon tweet-count markets. PAPER ONLY: public GET endpoints, no keys, no order code."""
import os, sys, json, gzip, time, traceback, bisect
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from shadowlib import *

HERE_ = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(HERE_, "logs"), exist_ok=True)
os.makedirs(os.path.join(HERE_, "rawbooks"), exist_ok=True)
ERRS = []

def err(where, e):
    msg = f"{where}: {type(e).__name__}: {e}"
    ERRS.append(msg); print("ERROR", msg, file=sys.stderr)

def discover(trackings):
    """Live events in both series + their windows. Returns list of dict."""
    tmap = {}
    for t in trackings or []:
        slug = (t.get("marketLink") or "").rstrip("/").split("/")[-1]
        if slug: tmap[slug] = t
    out = []
    for sid, fam in SERIES.items():
        try:
            evs = common.get(f"{GAMMA}/events", {"series_id": sid, "closed": "false", "limit": 100})
        except Exception as e:
            err(f"gamma series {sid}", e); continue
        for e in evs:
            try:
                slug = e["slug"]; t = tmap.get(slug); src = None
                if t and t.get("startDate") and t.get("endDate"):
                    S = to_s(t["startDate"]); E = to_s(t["endDate"]); E = (E + 59) // 60 * 60 if E % 60 else E  # 15:59:59 -> 16:00:00
                    src = "xtracker"
                else:
                    w = parse_description_window(e.get("description"))
                    if w: S, E = w; src = "description"
                if not src:
                    err(f"window {slug}", ValueError("no window")); continue
                buckets = []
                for m in e.get("markets", []):
                    b = parse_bucket(m.get("groupItemTitle") or "")
                    toks = common.parse_json_field(m.get("clobTokenIds"))
                    if b is None or not toks:
                        err(f"bucket {slug}", ValueError(f"unparsed {m.get('groupItemTitle')}")); continue
                    buckets.append(dict(lo=b[0], hi=b[1], token=toks[0], closed=bool(m.get("closed")), market_id=m.get("id")))
                out.append(dict(slug=slug, family=fam, S=S, E=E, src=src, buckets=buckets))
            except Exception as ex:
                err(f"event parse {e.get('slug')}", ex)
    return out

def fetch_book(tok):
    """Returns (status, book_json). 404 => bucket closed."""
    try:
        r = common._s.get(f"{CLOB}/book", params={"token_id": tok}, timeout=20)
        if r.status_code == 404: return "closed", None
        r.raise_for_status()
        return "ok", r.json()
    except Exception as e:
        try:
            time.sleep(1.5)
            r = common._s.get(f"{CLOB}/book", params={"token_id": tok}, timeout=20)
            if r.status_code == 404: return "closed", None
            r.raise_for_status(); return "ok", r.json()
        except Exception as e2:
            err(f"book {tok[:10]}", e2); return "error", None

def book_stats(b):
    asks = sorted(((float(x["price"]), float(x["size"])) for x in b.get("asks", [])))
    bids = sorted(((float(x["price"]), float(x["size"])) for x in b.get("bids", [])), reverse=True)
    ask = asks[0][0] if asks else None
    bid = bids[0][0] if bids else None
    depth = sum(p * s for p, s in asks if ask is not None and p <= ask + DEPTH_BAND + 1e-9) if asks else 0.0
    return ask, bid, depth

def refresh_posts(con, events, now):
    """Incremental pull into the local cache; whole 29 days once per day (late imports revise old rows)."""
    row = con.execute("SELECT v FROM meta WHERE k='full_pull'").fetchone()
    full = (row is None) or (now - int(row[0]) > 86400)
    start = now - 29 * 86400 if full else min([now - 3 * 86400] + [e["S"] for e in events])
    start = min(start, min([e["S"] for e in events] + [start]))
    data = tracker_posts(start, now + 3600)
    rows = [(p["id"], to_s(p["createdAt"]), to_s(p["importedAt"])) for p in data if p.get("createdAt") and p.get("importedAt")]
    con.executemany("INSERT OR REPLACE INTO posts VALUES(?,?,?)", rows)
    if full: con.execute("INSERT OR REPLACE INTO meta VALUES('full_pull',?)", (str(now),))
    con.commit()
    return len(rows), data

def main():
    now = now_s()
    con = db()
    cur = con.execute("INSERT INTO runs(ts,ts_iso,status) VALUES(?,?,?)", (now, iso(now), "started"))
    run_id = cur.lastrowid; con.commit()
    n_books = n_trades = 0; last_sync = last_err = None; n_ev = 0; status = "ok"
    try:
        ktab = load_k_table()
        user = {}
        try:
            user = common.get(f"{XT}/users/elonmusk")["data"]
            last_sync, last_err = user.get("lastSync"), user.get("lastSyncError")
        except Exception as e:
            err("xtracker user", e)
        events = [e for e in discover(user.get("trackings")) if e["E"] > now]
        n_ev = len(events)
        if not events:
            raise RuntimeError("no live events discovered")
        try:
            npost, _ = refresh_posts(con, events, now)
        except Exception as e:
            err("tracker posts", e)
        P = con.execute("SELECT c,i FROM posts ORDER BY c").fetchall()
        PC = np.array([p[0] for p in P], dtype="int64"); PI = np.array([p[1] for p in P], dtype="int64")
        PSLOT = (PC // 3600) % 168
        newest_c = iso(int(PC.max())) if len(PC) else None
        newest_i = iso(int(PI.max())) if len(PI) else None
        if len(PC) < 200: raise RuntimeError(f"post cache too small ({len(PC)})")
        lam = lam_vec(PC, PI, PSLOT, now)

        # books, concurrently (public GETs)
        jobs = [(e, b) for e in events for b in e["buckets"]]
        with ThreadPoolExecutor(6) as ex:
            res = list(ex.map(lambda j: fetch_book(j[1]["token"]), jobs))
        day = time.strftime("%Y%m%d", time.gmtime(now))
        raw = gzip.open(os.path.join(HERE_, "rawbooks", f"books_{day}.jsonl.gz"), "at")
        bk = {}
        for (e, b), (st, bj) in zip(jobs, res):
            ask = bid = None; depth = 0.0
            if st == "ok" and bj:
                ask, bid, depth = book_stats(bj)
            gz = gzip.compress(json.dumps(bj, separators=(",", ":")).encode()) if bj else None
            con.execute("INSERT INTO books VALUES(?,?,?,?,?,?,?,?,?,?,?)", (run_id, now, e["slug"], b["token"], b["lo"], b["hi"], st, ask, bid, depth, gz))
            raw.write(json.dumps(dict(ts=now, event=e["slug"], token=b["token"], lo=b["lo"], hi=b["hi"], status=st, book=bj), separators=(",", ":")) + "\n")
            bk[(e["slug"], b["token"])] = (st, ask, bid, depth); n_books += 1
        raw.close(); con.commit()

        for e in events:
            S, E = e["S"], e["E"]
            inwin = (PC >= S) & (PC < min(now, E))
            raw_count = int(inwin.sum())
            K = int((inwin & (PI <= now)).sum())
            con.execute("INSERT INTO tracker VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (run_id, now, e["slug"], e["family"], S, E, e["src"], raw_count, K, newest_c, newest_i, last_sync, last_err))
            lead = (now - S) / (E - S) * 100.0
            k, ksrc, grid = k_for(ktab, e["family"], lead)
            mu = mu_remaining(lam, now, S, E)
            spent = con.execute("SELECT COALESCE(SUM(stake),0) FROM paper_trades WHERE event_slug=?", (e["slug"],)).fetchone()[0]
            cands = []
            for b in e["buckets"]:
                st, ask, bid, depth = bk[(e["slug"], b["token"])]
                p = bucket_p(K, mu, k, b["lo"], b["hi"])
                edge = None if ask is None else p - ask
                reason = None
                if st != "ok": reason = f"book_{st}"
                elif ask is None: reason = "no_asks"
                elif b["closed"]: reason = "market_closed"
                elif not (LEAD_MIN_TRADE <= lead <= LEAD_MAX_TRADE): reason = "lead_outside_validated"
                elif ask < ASK_MIN: reason = "ask_below_min"
                elif ask > ASK_MAX: reason = "ask_gt_0.50"
                elif edge < EDGE_MIN: reason = "edge_lt_0.05"
                row = dict(b=b, p=p, ask=ask, bid=bid, depth=depth, edge=edge, reason=reason)
                if reason is None: cands.append(row)
                row["id"] = con.execute("INSERT INTO preds VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (run_id, now, e["slug"], e["family"], b["lo"], b["hi"], b["token"], lead, grid, k, ksrc, K, mu, p, ask, bid, depth, edge, 0, reason)).lastrowid
            for c in sorted(cands, key=lambda r: -r["edge"]):
                b = c["b"]
                recent = con.execute("SELECT 1 FROM paper_trades WHERE event_slug=? AND token_id=? AND ts>?", (e["slug"], b["token"], now - REBUY_HOURS * 3600)).fetchone()
                if recent: why = "dedupe_12h"
                elif spent + STAKE > EVENT_CAP + 1e-9: why = "event_cap_100"
                else: why = None
                if why:
                    con.execute("UPDATE preds SET skip_reason=? WHERE rowid=?", (why, c["id"])); continue
                con.execute("UPDATE preds SET would_trade=1 WHERE rowid=?", (c["id"],))
                con.execute("INSERT INTO paper_trades(run_id,ts,event_slug,family,bucket_lo,bucket_hi,token_id,lead_pct,lead_grid,p_model,ask,bid,edge,stake,shares,fee_per_share,depth2c_usd,K_asknown,mu,k) "
                            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (run_id, now, e["slug"], e["family"], b["lo"], b["hi"], b["token"], lead, grid, c["p"], c["ask"], c["bid"], c["edge"],
                             STAKE, STAKE / c["ask"], fee_ps(c["ask"]), c["depth"], K, mu, k))
                spent += STAKE; n_trades += 1
            con.commit()
            print(f"{e['slug']} [{e['family']}] lead={lead:.1f}% K={K} mu={mu:.1f} k={k:.2f}({ksrc}) src={e['src']} cands={len(cands)}")
    except Exception as ex:
        err("main", ex); traceback.print_exc(); status = "error"
    finally:
        try:
            con.execute("UPDATE runs SET status=?,n_events=?,n_books=?,n_trades=?,last_sync=?,last_sync_error=?,errors=? WHERE run_id=?",
                        (status if not ERRS or status == "error" else "partial", n_ev, n_books, n_trades, last_sync, last_err, json.dumps(ERRS) if ERRS else None, run_id))
            con.commit()
        except Exception as e:
            print("could not finalise run", e, file=sys.stderr)
    print(f"{iso(now)} run={run_id} status={status} events={n_ev} books={n_books} new_paper_trades={n_trades} errors={len(ERRS)} lastSync={last_sync} lastSyncError={last_err}")

if __name__ == "__main__":
    try:
        main()
    except BaseException as e:   # cron must never see a crash
        print("FATAL (swallowed)", type(e).__name__, e, file=sys.stderr)
    sys.exit(0)
