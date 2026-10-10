#!/usr/bin/env python3
"""Write report.md: shadow results + go-live checklist."""
import sys, os, numpy as np, pandas as pd
from shadowlib import *

rng = np.random.default_rng(7)
def boot_p(g, n=10000):
    a = g.groupby("event_slug").agg(p=("pnl", "sum"), s=("stake", "sum"))
    if len(a) < 2: return np.nan
    idx = rng.integers(0, len(a), (n, len(a)))
    return float(((a.p.values[idx].sum(1) / a.s.values[idx].sum(1)) <= 0).mean())
def roi(g): return g.pnl.sum() / g.stake.sum() if len(g) else np.nan
def f(x, d=3): return "n/a" if pd.isna(x) else f"{x:.{d}f}"
def pc(x): return "n/a" if pd.isna(x) else f"{x*100:+.1f}%"
def tab(df):
    if not len(df): return "_none_\n"
    return "| " + " | ".join(map(str, df.columns)) + " |\n|" + "---|" * len(df.columns) + "\n" + "".join("| " + " | ".join(map(str, r)) + " |\n" for r in df.values)
def chk(ok, none_msg=None):
    return "PASS" if ok is True else ("FAIL" if ok is False else "FAIL (no data)")

def main():
    con = db(); now = now_s()
    runs = pd.read_sql("SELECT * FROM runs", con)
    tr = pd.read_sql("SELECT * FROM paper_trades", con)
    st = pd.read_sql("SELECT * FROM settlements", con)
    er = pd.read_sql("SELECT * FROM event_results", con)
    posts = pd.read_sql("SELECT * FROM posts", con)
    t = tr.merge(st[["trade_id", "outcome_yes", "pnl", "pnl_p05"]], on="trade_id", how="inner")
    t["lead_bin"] = pd.cut(t.lead_pct, [-11, 0, 25, 50, 75, 101], labels=["<0", "0-25", "25-50", "50-75", "75+"])
    t["band"] = pd.cut(t.ask, [0, .02, .05, .10, .20, .50], labels=["<2c", "2-5c", "5-10c", "10-20c", "20-50c"])
    L = ["# Shadow report", f"Generated {iso(now)}.\n"]
    first = runs.ts.min() if len(runs) else now
    weeks = (now - first) / (7 * 86400)
    nres = len(er); nres_w = int((er.family == "weekly").sum())
    ok_runs = int((runs.status == "ok").sum()) if len(runs) else 0
    L.append(f"- runs: {len(runs)} (ok {ok_runs}, partial {(runs.status=='partial').sum() if len(runs) else 0}, error {(runs.status=='error').sum() if len(runs) else 0}); first {iso(int(first))}; span {weeks:.2f} weeks")
    L.append(f"- paper trades logged: {len(tr)} over {tr.event_slug.nunique()} events; settled: {len(t)} trades over {t.event_slug.nunique()} events")
    L.append(f"- resolved events: {nres} (weekly {nres_w}, 48h {nres - nres_w})")
    L.append(f"- open (unsettled) paper trades: {len(tr) - len(t)} (${(len(tr)-len(t))*STAKE:.0f} staked)\n")

    L.append("## Results (settled, at logged best ask)")
    if len(t):
        r_ask, r_05 = roi(t), t.pnl_p05.sum() / t.stake.sum() if False else None
        t2 = t.copy(); t2["pnl_x"] = t2.pnl_p05
        r_05 = t2.pnl_x.sum() / t2.stake.sum() if "stake" in t2 else np.nan
        p = boot_p(t)
        L.append(f"- n trades {len(t)}, n events {t.event_slug.nunique()}, PnL ${t.pnl.sum():.2f}, ROI at ask {pc(roi(t))}, ROI at ask+0.5c {pc(r_05)}, hit rate {t.outcome_yes.mean():.1%}")
        L.append(f"- event-clustered bootstrap p (ROI <= 0, 10k resamples of events): {f(p)}")
        for fam, g in t.groupby("family"):
            L.append(f"- {fam}: n={len(g)}, events={g.event_slug.nunique()}, ROI {pc(roi(g))}, p={f(boot_p(g))}")
        def grp(col):
            o = t.groupby(col, observed=True).agg(n=("pnl", "size"), events=("event_slug", "nunique"), pnl=("pnl", "sum"), stake=("stake", "sum"), hit=("outcome_yes", "mean")).reset_index()
            o["ROI"] = (o.pnl / o.stake).map(pc); o["pnl"] = o.pnl.round(2); o["hit"] = o.hit.map(lambda x: f"{x:.0%}")
            return o.drop(columns="stake")
        L.append("\n### PnL by ask band\n" + tab(grp("band")))
        L.append("### PnL by lead (% of window elapsed at trade time)\n" + tab(grp("lead_bin")))
    else:
        L.append("_No settled trades yet._")

    L.append("\n## Fill realism (all logged paper trades)")
    if len(tr):
        d = tr.depth2c_usd
        L.append(f"- $ available within 2c of the ask: median ${d.median():.1f}, 25th pct ${d.quantile(.25):.1f}; share with >= $10: {(d>=STAKE).mean():.1%}; share with >= $25: {(d>=25).mean():.1%}")
        gap = (tr.ask - (tr.ask + tr.bid.fillna(0)) / 2)
        L.append(f"- ask-mid gap on traded buckets: median {gap.median()*100:.2f}c, mean {gap.mean()*100:.2f}c (bid missing treated as 0)")
    else:
        gap = pd.Series(dtype=float); L.append("_No trades._")

    # tracker health
    shadow_posts = posts[posts.c >= first]
    late = (shadow_posts.i - shadow_posts.c > 3600).mean() if len(shadow_posts) else np.nan
    L.append("\n## Tracker health")
    L.append(f"- posts created during shadow period: {len(shadow_posts)}; imported > 1h after creation: {pc(late).replace('+','') if not pd.isna(late) else 'n/a'}")
    nm = int(er.mismatch.sum()) if len(er) else 0
    L.append(f"- resolution mismatches: {nm} of {nres}")
    if nm: L.append(tab(er[er.mismatch == 1][["event_slug", "note"]]))
    if len(runs):
        lse = runs.last_sync_error.dropna()
        L.append(f"- runs with xtracker lastSyncError: {len(lse)}; runs with API errors: {runs.errors.notna().sum()}")

    # checklist
    L.append("\n## Go-live checklist")
    rows = []
    c1 = (weeks >= 8) and (nres_w >= 15)
    rows.append(("(i) >= 8 weeks and >= 15 resolved weekly events", chk(c1), f"{weeks:.1f} weeks, {nres_w} weekly events"))
    if len(t):
        ev_pnl = t.groupby("event_slug").agg(p=("pnl", "sum"), s=("stake", "sum")).sort_values("p", ascending=False)
        rest = ev_pnl.iloc[2:]
        r_drop = rest.p.sum() / rest.s.sum() if len(rest) else np.nan
        c2 = bool(roi(t) >= 0.15 and r_drop > 0) if not pd.isna(r_drop) else False
        rows.append(("(ii) ROI at logged ask >= +15% and > 0 after dropping top 2 events", chk(c2), f"ROI {pc(roi(t))}; drop top 2: {pc(r_drop)}"))
        p = boot_p(t)
        rows.append(("(iii) event-clustered p < 0.10", chk(bool(p < 0.10) if not pd.isna(p) else False), f"p={f(p)}"))
    else:
        rows.append(("(ii) ROI >= +15% and > 0 after dropping top 2", chk(None), "no settled trades"))
        rows.append(("(iii) event-clustered p < 0.10", chk(None), "no settled trades"))
    if len(gap):
        rows.append(("(iv) median ask-mid gap on traded buckets <= 0.5c", chk(bool(gap.median() <= 0.005 + 1e-9)), f"{gap.median()*100:.2f}c"))
    else:
        rows.append(("(iv) median ask-mid gap <= 0.5c", chk(None), "no trades"))
    c5 = (not pd.isna(late)) and late < 0.10 and nm == 0 and nres > 0
    rows.append(("(v) late-import share < 10% and no resolution mismatches", chk(c5), f"late {pc(late) if not pd.isna(late) else 'n/a'}, mismatches {nm}"))
    if len(tr):
        rows.append(("(vi) median $ within 2c of ask on would-trades >= $25", chk(bool(tr.depth2c_usd.median() >= 25)), f"${tr.depth2c_usd.median():.1f}"))
    else:
        rows.append(("(vi) median $ within 2c >= $25", chk(None), "no trades"))
    L.append(tab(pd.DataFrame(rows, columns=["criterion", "result", "value"])))
    allpass = all(r[1] == "PASS" for r in rows)
    L.append(f"**Overall: {'ALL PASS - eligible for go-live review' if allpass else 'NOT READY'}**\n")
    txt = "\n".join(L)
    open(os.path.join(HERE, "report.md"), "w").write(txt)
    print(txt)

if __name__ == "__main__":
    main()
