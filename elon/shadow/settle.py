#!/usr/bin/env python3
"""Settle paper trades of resolved events (gamma outcomePrices) and flag tracker-vs-resolution mismatches. Public GETs only. Run daily."""
import sys, json, traceback
from shadowlib import *

def winner(markets):
    """Return (lo,hi) of the single bucket whose Yes price is ~1 and all others ~0, only if every market is closed."""
    win = None; ok_all = True
    for m in markets:
        pr = common.parse_json_field(m.get("outcomePrices"))
        b = parse_bucket(m.get("groupItemTitle") or "")
        if not pr or b is None or not m.get("closed"): return None
        y = float(pr[0])
        if y >= 0.99:
            if win is not None: return None
            win = b
        elif y > 0.01: return None
    return win

def main():
    con = db(); now = now_s(); n_ev = n_tr = 0
    rows = con.execute("SELECT event_slug, family, window_start, window_end FROM tracker GROUP BY event_slug").fetchall()
    for slug, fam, S, E in rows:
        if con.execute("SELECT 1 FROM event_results WHERE event_slug=?", (slug,)).fetchone() or E > now: continue
        try:
            evs = common.get(f"{GAMMA}/events", {"slug": slug})
            if not evs: continue
            w = winner(evs[0].get("markets", []))
            if w is None: print(f"{slug}: not resolved yet"); continue
            posts = tracker_posts(S, E)           # endDate exclusive; fresh pull picks up late imports
            cnt = len(posts)
            tb = None
            for m in evs[0]["markets"]:
                b = parse_bucket(m.get("groupItemTitle") or "")
                if b and b[0] <= cnt <= b[1]: tb = b
            mism = int(tb != w)
            note = f"tracker_final={cnt} tracker_bucket={tb} resolved_bucket={w}"
            con.execute("INSERT INTO event_results VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                        (slug, fam, S, E, w[0], w[1], cnt, tb[0] if tb else None, tb[1] if tb else None, mism, note, now))
            for tid, lo, hi, ask in con.execute("SELECT trade_id,bucket_lo,bucket_hi,ask FROM paper_trades WHERE event_slug=?", (slug,)).fetchall():
                win = int((lo, hi) == w)
                con.execute("INSERT OR REPLACE INTO settlements VALUES(?,?,?,?,?,?)", (tid, slug, win, pnl(ask, win), pnl(ask + SLIP_ALT, win), now)); n_tr += 1
            con.commit(); n_ev += 1
            print(f"{slug}: settled; {note}{'  ** MISMATCH **' if mism else ''}")
        except Exception as e:
            print(f"ERROR {slug}: {type(e).__name__}: {e}", file=sys.stderr)
    print(f"{iso(now)} settled events={n_ev} trades={n_tr}")

if __name__ == "__main__":
    try: main()
    except BaseException as e:
        traceback.print_exc(); print("FATAL (swallowed)", e, file=sys.stderr)
    sys.exit(0)
