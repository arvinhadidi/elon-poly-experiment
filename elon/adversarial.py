"""Adversarial review of the weekly Elon tweet-bucket edge. Offline only, no orders."""
import numpy as np, pandas as pd, glob, os, json, warnings
warnings.filterwarnings("ignore")
rng = np.random.default_rng(12345)
O = "out"; D = "data"
OUT = []
def P(s=""): print(s); OUT.append(str(s))
def tab(df, fmt=None):
    df = df.copy()
    cols = list(df.columns)
    s = "| " + " | ".join(map(str, cols)) + " |\n|" + "---|" * len(cols) + "\n"
    for _, r in df.iterrows():
        s += "| " + " | ".join((f"{v:.3f}" if isinstance(v, (float, np.floating)) else str(v)) for v in r) + " |\n"
    return s

pr = pd.read_parquet(f"{O}/bt_preds.parquet")
pr["ws"] = pd.to_datetime(pr.window_start_utc)
W = pr[(pr.family == "weekly") & pr.price.notna()].copy()
PRIM = [0, 25, 50, 75]
W["month"] = W.ws.dt.strftime("%Y-%m")

def trades(d, slip=0.0, edge=0.05, cap=0.50, lo=0.001, leads=PRIM, pcol="p_model"):
    x = d[d.lead_pct.isin(leads)] if leads is not None else d
    e = x.price + slip
    m = ((x[pcol] - e) >= edge - 1e-12) & (e <= cap) & (e >= lo)
    x = x[m].copy(); x["entry"] = e[m]
    x["shares"] = 10 / x.entry
    x["pnl"] = x.shares * x.outcome_yes - 10 - x.shares * 0.05 * x.entry * (1 - x.entry)
    return x

def roi(x): return x.pnl.sum() / (10 * len(x)) if len(x) else np.nan

def evagg(x):
    g = x.groupby("event_slug").agg(pnl=("pnl", "sum"), n=("pnl", "size"))
    return g

def boot_p(x, B=4000, rs=None):
    rs = rs or np.random.default_rng(1)
    g = evagg(x)
    if len(g) < 2: return np.nan
    pn = g.pnl.values; st = g.n.values * 10.0
    idx = rs.integers(0, len(g), (B, len(g)))
    r = pn[idx].sum(1) / st[idx].sum(1)
    return (r <= 0).mean()

def leavek(x, ks=range(0, 11)):
    g = evagg(x).sort_values("pnl", ascending=False)
    tot_n = g.n.sum(); out = []
    for k in ks:
        rest = g.iloc[k:]
        out.append(rest.pnl.sum() / (10 * rest.n.sum()) if rest.n.sum() else np.nan)
    return np.array(out)

base = trades(W, 0.0)
P("# Adversarial review: is the weekly Elon bucket edge fake?\n")
P(f"Replication check: primary weekly slip0 n={len(base)} ROI={roi(base):+.1%} PnL=${base.pnl.sum():.0f} (bt_summary: 384, +68%, $2624). "
  f"Events with trades={base.event_slug.nunique()}.")
bt = pd.read_csv(f"{O}/bt_trades.csv")
chk = bt[(bt.variant == "asknown") & (bt.family == "weekly") & (bt.slippage == 0) & bt.lead_pct.isin(PRIM)]
P(f"bt_trades.csv cross-check: n={len(chk)} pnl=${chk.pnl.sum():.0f}\n")
base05 = trades(W, 0.005); base10 = trades(W, 0.01)
P(f"0.5c: n={len(base05)} ROI={roi(base05):+.1%}; 1c: n={len(base10)} ROI={roi(base10):+.1%}\n")

# ================= 1. lottery skew / null =================
P("## 1. Lottery skew: null strategies\n")
real_lk = {s: leavek(t) for s, t in [(0.0, base), (0.005, base05)]}
# unconditional market calibration on the same rows (does the market underprice longshots at all?)
Wp = W[W.lead_pct.isin(PRIM) & (W.price >= 0.001) & (W.price <= 0.5)].copy()
Wp["pb"] = pd.cut(Wp.price, [0, .005, .01, .02, .05, .10, .20, .35, .5])
cal = Wp.groupby("pb").agg(n=("outcome_yes", "size"), mean_price=("price", "mean"), hit=("outcome_yes", "mean")).reset_index()
cal["pb"] = cal.pb.astype(str)
cal["hit_minus_price"] = cal.hit - cal.mean_price
P("Market calibration of ALL weekly priced buckets (primary leads), no model involved. If hit >> price the market is longshot-underpriced and ANY random longshot buyer wins:\n")
P(tab(cal))

NR = 2000
pool = {l: Wp[Wp.lead_pct == l].reset_index(drop=True) for l in PRIM}
def null_matched(real, slip, rs):
    """for each real trade pick random row (any event) at same lead with entry in [0.7,1.43]x real entry"""
    rows = []
    for l in PRIM:
        rt = real[real.lead_pct == l]
        if rt.empty: continue
        pl = pool[l]; pe = pl.price.values + slip
        order = np.argsort(pe); pes = pe[order]
        lo = np.searchsorted(pes, rt.entry.values * 0.7); hi = np.searchsorted(pes, rt.entry.values * 1.43)
        for a, b in zip(lo, hi):
            if b > a: rows.append(order[rs.integers(a, b)] + 0 * l + 1_000_000 * l)
    return rows
def pnl_rows(rowsel, slip):
    out = []
    for key in rowsel:
        l = key // 1_000_000; i = key % 1_000_000
        r = pool[l].iloc[i]
        e = r.price + slip
        out.append((r.event_slug, 10 / e * r.outcome_yes - 10 - 10 / e * 0.05 * e * (1 - e)))
    return pd.DataFrame(out, columns=["event_slug", "pnl"])

# fast arrays for matched null
def null_matched_fast(real, slip, B, rs):
    res = []
    arr = {}
    for l in PRIM:
        pl = pool[l]; pe = pl.price.values + slip
        order = np.argsort(pe)
        arr[l] = (pe[order], pl.outcome_yes.values[order], pl.event_slug.values[order])
    spans = []
    for l in PRIM:
        rt = real[real.lead_pct == l]
        pes, y, ev = arr[l]
        lo = np.searchsorted(pes, rt.entry.values * 0.7); hi = np.searchsorted(pes, rt.entry.values * 1.43)
        spans += [(l, a, max(b, a + 1)) for a, b in zip(lo, hi)]
    out = []
    for b in range(B):
        pn = []; ev_ = []
        for (l, a, bb) in spans:
            pes, y, ev = arr[l]
            i = min(rs.integers(a, bb), len(pes) - 1)
            e = pes[i]
            pn.append(10 / e * y[i] - 10 - 10 / e * 0.05 * e * (1 - e)); ev_.append(ev[i])
        s = pd.DataFrame({"event_slug": ev_, "pnl": pn})
        out.append((np.sum(pn) / (10 * len(pn)), leavek(s.assign(), [5])[0] if False else None, s))
    return out
def drop_top5_roi(s):
    g = s.groupby("event_slug").pnl.agg(["sum", "size"]).sort_values("sum", ascending=False)
    r = g.iloc[5:]
    return r["sum"].sum() / (10 * r["size"].sum()) if len(r) else np.nan

def run_null_matched(slip, real, B=600):
    rs = np.random.default_rng(7)
    res = null_matched_fast(real, slip, B, rs)
    r0 = np.array([r[0] for r in res]); r5 = np.array([drop_top5_roi(r[2]) for r in res])
    top5share = np.array([ (lambda g: g.sort_values(ascending=False).iloc[:5].sum()/g.sum() if g.sum()>0 else np.nan)(r[2].groupby("event_slug").pnl.sum()) for r in res])
    return r0, r5, top5share
def run_null_shuffle(slip, B=1000):
    """shuffle p_model among buckets within event x lead (information destroyed, price & count structure of p kept), apply the rule."""
    rs = np.random.default_rng(11)
    x = W[W.lead_pct.isin(PRIM)].reset_index(drop=True)
    groups = x.groupby(["event_slug", "lead_pct"]).indices
    gl = list(groups.values())
    p = x.p_model.values; pr_ = x.price.values; y = x.outcome_yes.values; ev = x.event_slug.values
    r0 = []; r5 = []; ns = []
    for b in range(B):
        ps = p.copy()
        for ix in gl:
            ps[ix] = p[ix][rs.permutation(len(ix))]
        e = pr_ + slip
        m = (ps - e >= 0.05) & (e <= 0.5) & (e >= 0.001)
        ee = e[m]
        pn = 10 / ee * y[m] - 10 - 10 / ee * 0.05 * ee * (1 - ee)
        if len(pn) < 20: r0.append(np.nan); r5.append(np.nan); ns.append(len(pn)); continue
        s = pd.DataFrame({"event_slug": ev[m], "pnl": pn})
        r0.append(pn.sum() / (10 * len(pn))); r5.append(drop_top5_roi(s)); ns.append(len(pn))
    return np.array(r0), np.array(r5), np.array(ns)
def run_null_inevent(slip, real, B=1000):
    """same trade count per event x lead, random eligible buckets (0.1c..50c) of that event x lead"""
    rs = np.random.default_rng(13)
    x = W[W.lead_pct.isin(PRIM)].reset_index(drop=True)
    x["entry"] = x.price + slip
    el = x[(x.entry >= 0.001) & (x.entry <= 0.5)]
    cnt = real.groupby(["event_slug", "lead_pct"]).size()
    grp = el.groupby(["event_slug", "lead_pct"]).indices
    e_ = el.entry.values; y_ = el.outcome_yes.values; ev_ = el.event_slug.values
    keys = [(k, n, grp[k]) for k, n in cnt.items() if k in grp]
    r0 = []; r5 = []
    for b in range(B):
        pn = []; evs = []
        for k, n, ix in keys:
            pick = rs.choice(ix, size=min(n, len(ix)), replace=False)
            e = e_[pick]
            pn.extend(10 / e * y_[pick] - 10 - 10 / e * 0.05 * e * (1 - e)); evs.extend(ev_[pick])
        s = pd.DataFrame({"event_slug": evs, "pnl": pn})
        r0.append(np.sum(pn) / (10 * len(pn))); r5.append(drop_top5_roi(s))
    return np.array(r0), np.array(r5)

nulls = {}
rows = []
for slip, real in [(0.0, base), (0.005, base05)]:
    rl = roi(real); r5l = leavek(real, [5])[0]
    g = evagg(real).sort_values("pnl", ascending=False)
    for nm, fn in [("matched-price random buckets (any event, same lead)", lambda: run_null_matched(slip, real)[:2]),
                   ("shuffled model within event x lead (no information)", lambda: run_null_shuffle(slip)[:2]),
                   ("random buckets, same count per event x lead", lambda: run_null_inevent(slip, real))]:
        a, b = fn()
        a = a[~np.isnan(a)]; b = b[~np.isnan(b)]
        rows.append(dict(slip=slip, null=nm, null_ROI_mean=a.mean(), null_ROI_p2_5=np.quantile(a, .025), null_ROI_p97_5=np.quantile(a, .975),
                         ours=rl, pct_null_ge_ours=(a >= rl).mean(),
                         null_drop5_mean=b.mean(), ours_drop5=r5l, pct_null_drop5_ge_ours=(b >= r5l).mean(),
                         null_drop5_p97_5=np.quantile(b, .975)))
nt = pd.DataFrame(rows)
P("\nNull strategies (ROI, $10 flat, same fee), real strategy vs distribution under 'no model information':\n")
P(tab(nt[["slip", "null", "null_ROI_mean", "null_ROI_p2_5", "null_ROI_p97_5", "ours", "pct_null_ge_ours"]]))
P("\nLeave-top-5-events-out (fragility) under the same nulls:\n")
P(tab(nt[["slip", "null", "null_drop5_mean", "null_drop5_p97_5", "ours_drop5", "pct_null_drop5_ge_ours"]]))
P("\nOur leave-k-out curve (ROI after dropping top-k events by PnL), k=0..10:\n")
P(tab(pd.DataFrame({"k": list(range(11)), "slip0": real_lk[0.0], "slip0.5c": real_lk[0.005]})))

# ================= 2. forking paths =================
P("\n## 2. Multiple testing: threshold/lead/band grid (weekly, as-known)\n")
LEADSETS = {"primary0-25-50-75": PRIM, "lead0": [0], "lead25": [25], "lead50": [50], "lead75": [75],
            "mid20-60": [20, 25, 30, 35, 40, 45, 50, 55, 60], "early0-45": list(range(0, 50, 5)), "late65-95": list(range(65, 100, 5)),
            "all0-95": list(range(0, 100, 5))}
specs = []
for ln, lv in LEADSETS.items():
    for ed in [0.02, 0.05, 0.08, 0.12]:
        for cp in [0.15, 0.30, 0.50]:
            for mn in [0.001, 0.02]:
                specs.append((ln, lv, ed, cp, mn))
evlist = sorted(W.event_slug.unique())
evidx = {e: i for i, e in enumerate(evlist)}
evstart = W.groupby("event_slug").ws.first().reindex(evlist)
blk = ((evstart - evstart.min()).dt.days // 14).values
nb = blk.max() + 1
def spec_vec(spec, slip):
    ln, lv, ed, cp, mn = spec
    x = trades(W, slip, ed, cp, mn, lv)
    pn = np.zeros(len(evlist)); n = np.zeros(len(evlist))
    if len(x):
        g = x.groupby("event_slug").pnl.agg(["sum", "size"])
        ii = [evidx[e] for e in g.index]
        pn[ii] = g["sum"].values; n[ii] = g["size"].values
    return pn, n
res = []; VEC = {}
for slip in [0.0, 0.005, 0.01]:
    for sp in specs:
        pn, n = spec_vec(sp, slip)
        VEC[(sp[0], sp[2], sp[3], sp[4], slip)] = (pn, n)
        if n.sum() < 15: continue
        res.append(dict(leads=sp[0], edge=sp[2], cap=sp[3], minentry=sp[4], slip=slip, n=int(n.sum()), ROI=pn.sum() / (10 * n.sum()),
                        key=(sp[0], sp[2], sp[3], sp[4], slip)))
G = pd.DataFrame(res)
# block bootstrap p-values (14d blocks) and reality check
Bq = 3000
rsb = np.random.default_rng(99)
bidx = rsb.integers(0, nb, (Bq, nb))
def block_stat(pn, n):
    bp = np.bincount(blk, weights=pn, minlength=nb); bn = np.bincount(blk, weights=n, minlength=nb)
    return bp, bn
def boot_roi(pn, n):
    bp, bn = block_stat(pn, n)
    num = bp[bidx].sum(1); den = bn[bidx].sum(1) * 10
    return num / np.where(den == 0, np.nan, den)
pvals = []; BR = {}
for i, r in G.iterrows():
    pn, n = VEC[r.key]
    br = boot_roi(pn, n); BR[r.key] = br
    pvals.append(np.nanmean(br <= 0))
G["p_block"] = pvals
P(f"Specs enumerated: {len(specs)} per slippage level (leads sets x edge x cap x min-entry) = {len(specs)*3} total, {len(G)} with >=15 trades.\n")
sumrows = []
for slip in [0.0, 0.005, 0.01]:
    g = G[G.slip == slip]
    sumrows.append(dict(slip=slip, n_specs=len(g), share_ROI_gt0=(g.ROI > 0).mean(), median_ROI=g.ROI.median(), p10=g.ROI.quantile(.1), p90=g.ROI.quantile(.9),
                        n_p_lt_05=(g.p_block < .05).sum(), share_p_lt_05=(g.p_block < .05).mean(),
                        n_holm_sig=int(sum(np.sort(g.p_block.values)[i] <= 0.05 / (len(g) - i) for i in range(len(g))) if True else 0)))
# Holm properly
def holm_count(p, a=0.05):
    ps = np.sort(p); k = 0
    for i, v in enumerate(ps):
        if v <= a / (len(ps) - i): k += 1
        else: break
    return k
for r in sumrows:
    g = G[G.slip == r["slip"]]; r["n_holm_sig"] = holm_count(g.p_block.values)
P(tab(pd.DataFrame(sumrows)))
P("\nNote: p_block floor is 1/3000, Holm over ~%d specs needs p < %.1e, so Holm counts are limited by bootstrap resolution; read them as 'cannot be rejected', not proof.\n" % (len(specs), 0.05 / len(specs)))
# By leadset at 0.5c
g5 = G[G.slip == 0.005]
P("Share of specs with ROI>0 at 0.5c by lead set:\n")
P(tab(g5.groupby("leads").agg(n_specs=("ROI", "size"), share_pos=("ROI", lambda s: (s > 0).mean()), median_ROI=("ROI", "median")).reset_index()))
P("\nBy edge threshold at 0.5c:\n")
P(tab(g5.groupby("edge").agg(n_specs=("ROI", "size"), share_pos=("ROI", lambda s: (s > 0).mean()), median_ROI=("ROI", "median")).reset_index()))
P("\nBy price cap at 0.5c:\n")
P(tab(g5.groupby("cap").agg(n_specs=("ROI", "size"), share_pos=("ROI", lambda s: (s > 0).mean()), median_ROI=("ROI", "median")).reset_index()))
# White reality check on specs at slip s: stat=max ROI; null by recentering
for slip in [0.0, 0.005, 0.01]:
    g = G[G.slip == slip]
    obs = g.ROI.values
    boots = np.vstack([BR[k] for k in g.key])
    boots = np.where(np.isnan(boots), 0.0, boots)
    centered = boots - obs[:, None]
    # use ROI * sqrt-n studentisation to avoid small-n specs dominating
    sd = boots.std(1); sd[sd == 0] = np.nan
    tobs = np.nanmax(obs / sd); tb = np.nanmax(centered / sd[:, None], axis=0)
    rc_p = (tb >= tobs).mean()
    best = g.iloc[np.nanargmax(obs / sd)]
    P(f"White RC (studentised max over {len(g)} specs, 14d block bootstrap), slip {slip}: best spec = leads {best.leads}, edge {best.edge}, cap {best.cap}, minentry {best.minentry}, ROI {best.ROI:+.0%}; RC p = {rc_p:.3f}")
    # primary spec's own studentised rank
pidx = G[(G.leads == "primary0-25-50-75") & (G.edge == .05) & (G.cap == .5) & (G.minentry == .001)]
for _, r in pidx.iterrows():
    rank = (G[G.slip == r.slip].ROI > r.ROI).mean()
    P(f"Primary spec slip {r.slip}: ROI {r.ROI:+.0%}, p_block {r.p_block:.3f}, ROI percentile within grid (share of specs better) {rank:.0%}")

# honest 'family of forks' tally including those not in grid
P("""
Forks actually taken in this project (not all in the grid): family (weekly vs 48h vs monthly/daily/related), 21 leads then a 4-lead 'primary', edge 5pp, cap 50c, floor 0.1c, walk-forward k vs in-sample k vs bias-adjust, as-known vs lookahead, 4-week rate window, slippage levels, entry<2c/>=2c split, Tue/Fri split, price bands, per-lead hotspot analysis. A defensible effective number of independent specs is 30-100, not 1.""")

# ================= 3. Executable prices =================
P("\n## 3. Mid/last-trade price vs executable ask\n")
bk = pd.read_csv(f"{D}/ops_books.csv"); bk = bk[bk.has_book == True].copy()
bk["band"] = pd.cut(bk.best_ask, [0, .02, .05, .15, .5, 1.01], labels=["<=2c", "2-5c", "5-15c", "15-50c", ">50c"])
bk["mid_vs_ask"] = bk.best_ask - bk.book_mid
bk["ask_vs_mid_rel"] = bk.mid_vs_ask / bk.book_mid
b3 = bk.groupby("band").agg(n=("spread", "size"), median_spread=("spread", "median"), med_ask_minus_mid=("mid_vs_ask", "median"),
                            med_rel_ask_over_mid=("ask_vs_mid_rel", "median"), med_ask_usd_touch=("ask_usd_touch", "median"),
                            med_ask_usd_2c=("ask_usd_2c", "median")).reset_index()
P("Live books (one snapshot, 2026-10-10, 90 books with quotes): ask - mid by best-ask band. Backtest enters at the snapshot price (mid/last-trade) + slip.\n")
P(tab(b3))
P(f"\nBooks with a quote that are 1-sided/crossed or best_bid==0: {int((bk.best_bid.fillna(0)<=0.001).sum())} of {len(bk)}. In a <=2c band a mid of (0+ask)/2 is not a price you can buy at.\n")

# raw trades: YES-space buy/sell prints
snap = pd.read_csv(f"{D}/price_snapshots.csv")
snapw = snap[(snap.family == "weekly") & snap.lead_pct.isin(PRIM)].copy()
tfiles = glob.glob(f"{D}/raw/trades/*.parquet")
TR = pd.concat([pd.read_parquet(f) for f in tfiles], ignore_index=True)
TR = TR[TR.eventSlug.notna()]
# convert to Yes-space
yes = TR.outcomeIndex == 0
TR["yprice"] = np.where(yes, TR.price, 1 - TR.price)
TR["ybuy"] = np.where(yes, TR.side == "BUY", TR.side == "SELL")   # taker buying YES exposure
TR = TR.rename(columns={"market_id": "mid_"})
yes_tok = snap.drop_duplicates(["event_slug", "bucket_lo", "bucket_hi"])[["event_slug", "bucket_lo", "bucket_hi", "yes_token"]]
tokmap = TR.drop_duplicates("asset")[["asset", "eventSlug", "outcomeIndex"]]
# match trades to buckets via market_id->events
ev = pd.read_csv(f"{D}/events.csv")[["market_id", "event_slug", "bucket_lo", "bucket_hi"]].drop_duplicates()
TR["market_id"] = TR.mid_.astype("int64")
TR = TR.merge(ev.rename(columns={"event_slug": "es"}), on="market_id", how="left")
TR = TR[TR.es.notna()]
P(f"Raw trade files cover {TR.es.nunique()} events, {len(TR)} prints, {pd.to_datetime(TR.timestamp.min(),unit='s'):%Y-%m-%d} to {pd.to_datetime(TR.timestamp.max(),unit='s'):%Y-%m-%d} (Jul-Oct 2026 only; none cover Dec-Jun, i.e. none cover the high-vol regime that made the PnL).")
# all snapshots rows (not only traded) for weekly events in coverage
S = snapw[snapw.event_slug.isin(TR.es.unique())].copy()
S = S[(S.price >= 0.001) & (S.price <= 0.5)]
TRg = {k: g.sort_values("timestamp") for k, g in TR.groupby(["es", "bucket_lo", "bucket_hi"])}
recs = []
for _, r in S.iterrows():
    g = TRg.get((r.event_slug, r.bucket_lo, r.bucket_hi))
    if g is None: continue
    t0 = r.target_ts
    ts = g.timestamp.values
    w = g[(ts >= t0 - 600) & (ts <= t0 + 600)]
    bw = w[w.ybuy]; sw = w[~w.ybuy]
    after = g[(g.timestamp >= t0) & (g.timestamp <= t0 + 1800) & g.ybuy]
    before = g[g.timestamp <= t0]
    last_before = before.iloc[-1] if len(before) else None
    recs.append(dict(event_slug=r.event_slug, lead=r.lead_pct, bucket_lo=r.bucket_lo, price=r.price,
                     n_buy=len(bw), n_sell=len(sw),
                     buy_med=bw.yprice.median() if len(bw) else np.nan, sell_med=sw.yprice.median() if len(sw) else np.nan,
                     first_buy_after=after.yprice.iloc[0] if len(after) else np.nan,
                     last_is_buy=(bool(last_before.ybuy) if last_before is not None else np.nan),
                     outcome=r.outcome_yes))
R = pd.DataFrame(recs)
R["band"] = pd.cut(R.price, [0, .02, .05, .15, .5], labels=["<=2c", "2-5c", "5-15c", "15-50c"])
R["buy_over_snap"] = R.buy_med - R.price
R["first_buy_over_snap"] = R.first_buy_after - R.price
R["buy_rel"] = R.buy_med / R.price
r3 = R.groupby("band").agg(rows=("price", "size"), with_buy_print=("buy_med", lambda s: s.notna().mean()), mean_snap=("price", "mean"),
                           mean_buy_print=("buy_med", "mean"), med_buy_minus_snap=("buy_over_snap", "median"),
                           med_first_buy_minus_snap=("first_buy_over_snap", "median"), med_ratio=("buy_rel", "median"),
                           last_print_was_sell=("last_is_buy", lambda s: 1 - s.dropna().astype(float).mean())).reset_index()
P("\nJul-Oct 2026 weekly rows with Polymarket trade history: snapshot price vs actual BUY-YES prints in +-10 min (YES-space; NO sells/buys converted). Only rows with a snapshot price in [0.1c,50c] on primary leads:\n")
P(tab(r3))
# ROI of 'trades' (edge rule) in the covered window under snapshot price vs buy print
cov = base[base.event_slug.isin(TR.es.unique())].copy()
P(f"\nStrategy trades inside raw-trade coverage (Jul-Oct 2026 weekly events): n={len(cov)}, ROI at snapshot price {roi(cov):+.1%}" if len(cov) else "\nNo strategy trades inside raw-trade coverage.")
if len(cov):
    cc = cov.merge(R[["event_slug", "lead", "bucket_lo", "buy_med", "first_buy_after", "n_buy"]], left_on=["event_slug", "lead_pct", "bucket_lo"], right_on=["event_slug", "lead", "bucket_lo"], how="left")
    ok = cc.buy_med.notna()
    e = cc.buy_med[ok]
    pn = 10 / e * cc.outcome_yes[ok] - 10 - 10 / e * 0.05 * e * (1 - e)
    P(f" of which with BUY prints within +-10min: {int(ok.sum())}; ROI at actual median BUY print {pn.sum()/(10*ok.sum()):+.1%} vs at snapshot {cc.pnl[ok].sum()/(10*ok.sum()):+.1%}; mean entry print/snap = {(e/cc.price[ok]).mean():.2f}")
    P(f" unfillable-in-window (no BUY print in +-10min): {int((~ok).sum())} of {len(cc)}")

# ================= 4. Stale prices =================
P("\n## 4. Stale snapshot prices\n")
P("price_snapshots.dt_sec = |price_ts - target_ts| (<=600). Distribution on strategy trades:")
bs = base.merge(snap[["event_slug", "bucket_lo", "bucket_hi", "lead_pct", "price_ts", "dt_sec", "yes_token", "target_ts"]], on=["event_slug", "bucket_lo", "bucket_hi", "lead_pct"], how="left")
P(f" median dt_sec {bs.dt_sec.median():.0f}, share dt>300s {(bs.dt_sec>300).mean():.1%}")
# time since last change using raw minute history
ages = {}
for es, g in bs.groupby("event_slug"):
    f = f"{D}/raw/prices/{es}.parquet"
    if not os.path.exists(f): continue
    pxs = pd.read_parquet(f)
    for tok, gg in g.groupby("yes_token"):
        s = pxs[pxs.token.astype(str) == str(tok)].sort_values("t")
        if s.empty: continue
        t = s.t.values; p = s.p.values
        chg = np.r_[True, p[1:] != p[:-1]]
        tchg = t[chg]
        for i, r in gg.iterrows():
            j = np.searchsorted(t, r.price_ts, side="right") - 1
            if j < 0: continue
            tc = tchg[tchg <= t[j]]
            ages[i] = (r.price_ts - tc[-1]) / 60.0 if len(tc) else np.nan
bs["age_min"] = pd.Series(ages)
P(f" rows with computed last-change age: {bs.age_min.notna().sum()} of {len(bs)}")
qs = bs.age_min.quantile([.25, .5, .75, .9]).round(1).to_dict()
P(f" minutes since last price change (strategy trades): quantiles {qs}")
fresh = bs[bs.age_min <= 30]; stale = bs[bs.age_min > 30]
rowsx = []
for nm, sub in [("age<=30m", fresh), ("age>30m", stale), ("age<=10m", bs[bs.age_min <= 10]), ("age>120m", bs[bs.age_min > 120])]:
    sub = sub.copy()
    rowsx.append(dict(subset=nm, n=len(sub), events=sub.event_slug.nunique(), ROI_slip0=roi(sub) if len(sub) else np.nan, PnL=sub.pnl.sum(), p_boot=boot_p(sub) if len(sub) > 5 else np.nan))
P(tab(pd.DataFrame(rowsx)))
# same at 0.5c using fresh keys
k05 = base05.merge(bs[["event_slug", "bucket_lo", "lead_pct", "age_min"]], on=["event_slug", "bucket_lo", "lead_pct"], how="left")
f05 = k05[k05.age_min <= 30]
P(f" At 0.5c slip: fresh (<=30m) n={len(f05)} ROI {roi(f05):+.1%} p={boot_p(f05):.3f}; stale n={int((k05.age_min>30).sum())} ROI {roi(k05[k05.age_min>30]):+.1%}")
top = base.groupby("event_slug").pnl.sum().sort_values(ascending=False).head(5).index
tp = bs[bs.event_slug.isin(top)]
P(f" Top-5 PnL events: median age of their winning trades' price = {tp[tp.pnl>0].age_min.median():.1f} min; share of their winning trades with stale (>30m) price = {(tp[tp.pnl>0].age_min>30).mean():.0%}")

# ================= 5. Regime =================
P("\n## 5. Regime (post-rate)\n")
posts = pd.read_csv(f"{D}/posts_elonmusk.csv", usecols=["createdAt", "importedAt", "lag_sec"])
posts["c"] = pd.to_datetime(posts.createdAt)
pm = posts.groupby(posts.c.dt.strftime("%Y-%m")).size().rename("posts")
days = posts.groupby(posts.c.dt.strftime("%Y-%m")).c.agg(lambda s: (s.max() - s.min()).days + 1)
rate = (pm / days).rename("posts_per_day")
def per_period(slip, edge=0.05):
    x = trades(W, slip, edge)
    g = x.groupby("month").agg(n=("pnl", "size"), events=("event_slug", "nunique"), PnL=("pnl", "sum"))
    g["ROI"] = g.PnL / (10 * g.n)
    return g
for slip in [0.0, 0.005, 0.01]:
    g = per_period(slip)
    g = g.join(rate).reset_index()
    P(f"Monthly, slip {slip}:\n")
    P(tab(g))
    P("")
rg = []
for slip in [0.0, 0.005, 0.01]:
    x = trades(W, slip)
    x["reg"] = np.where(x.month.isin(["2025-12", "2026-01", "2026-02"]), "Dec-Feb", "Mar-Oct")
    for rn, sub in x.groupby("reg"):
        rg.append(dict(slip=slip, regime=rn, n=len(sub), events=sub.event_slug.nunique(), ROI=roi(sub), PnL=sub.pnl.sum(), p_boot=boot_p(sub), share_of_total_PnL=sub.pnl.sum() / x.pnl.sum()))
P(tab(pd.DataFrame(rg)))
x = trades(W, 0.0); xm = x[~x.month.isin(["2025-12", "2026-01", "2026-02"])]
P(f"\nMar-Oct only, slip 0: leave-k-out ROI (k=0,1,2,3,5): {np.round(leavek(xm,[0,1,2,3,5]),2).tolist()}; top-3 events of Mar-Oct: "
  + ", ".join(f"{e[-22:]}:${v:.0f}" for e, v in xm.groupby('event_slug').pnl.sum().sort_values(ascending=False).head(3).items()))
# top 5 event table
t5 = base.groupby("event_slug").agg(PnL=("pnl", "sum"), n=("pnl", "size"), start=("window_start_utc", "first")).sort_values("PnL", ascending=False).head(8).reset_index()
P("\nTop-8 events by PnL (slip 0):\n"); P(tab(t5))

# ================= 6. Data integrity =================
P("\n## 6. Data integrity\n")
fin = pr.drop_duplicates("event_slug").set_index("event_slug")[["family", "final_count", "window_start_utc"]]
wins = ev.merge(pd.read_csv(f"{D}/events.csv")[["market_id", "outcome_yes"]].drop_duplicates(), on="market_id")
wins = wins[wins.outcome_yes == 1].groupby("event_slug").agg(lo=("bucket_lo", "min"), hi=("bucket_hi", "max"))
j = fin.join(wins, how="inner")
j = j[j.family == "weekly"]
j["ok"] = (j.final_count >= j.lo) & (j.final_count <= j.hi)
P(f"Backtest weekly events: {len(j)}; tracker final_count inside Polymarket's resolved bucket: {int(j.ok.sum())}; MISMATCH: {int((~j.ok).sum())}")
mm = j[~j.ok]
if len(mm):
    mm = mm.assign(gap=np.where(mm.final_count < mm.lo, mm.final_count - mm.lo, mm.final_count - mm.hi))
    P(tab(mm.reset_index()[["event_slug", "final_count", "lo", "hi", "gap"]]))
    mmtr = base[base.event_slug.isin(mm.index)]
    P(f"Strategy PnL in mismatch events (slip0): n={len(mmtr)}, PnL=${mmtr.pnl.sum():.0f} (of ${base.pnl.sum():.0f})")
    # recompute PnL with outcome flipped to tracker-implied bucket
    alt = base.copy()
    alt["y2"] = ((alt.event_slug.map(j.final_count) >= alt.bucket_lo) & (alt.event_slug.map(j.final_count) <= alt.bucket_hi)).astype(int)
    alt["pnl2"] = alt.shares * alt.y2 - 10 - alt.shares * 0.05 * alt.entry * (1 - alt.entry)
    P(f"Re-scoring ALL trades against tracker-implied winner instead of Polymarket resolution: PnL ${alt.pnl2.sum():.0f}, ROI {alt.pnl2.sum()/(10*len(alt)):+.1%} (vs {roi(base):+.1%})")
# tracker lag inside event windows
posts["imp"] = pd.to_datetime(posts.importedAt)
bad = []
for _, r in pr.drop_duplicates("event_slug")[["event_slug", "family", "window_start_utc", "window_end_utc"]].query("family=='weekly'").iterrows():
    a, b = pd.Timestamp(r.window_start_utc), pd.Timestamp(r.window_end_utc)
    s = posts[(posts.c >= a) & (posts.c < b)]
    bad.append(dict(event_slug=r.event_slug, n=len(s), late1h=int((s.lag_sec > 3600).sum()), late6h=int((s.lag_sec > 21600).sum())))
bad = pd.DataFrame(bad)
P(f"\nWeekly events containing >=1 post imported >1h late: {int((bad.late1h>0).sum())} of {len(bad)}; >=5 late posts: {int((bad.late1h>=5).sum())}. Late-import events' trades (slip0): n={len(base[base.event_slug.isin(bad[bad.late1h>0].event_slug)])}, PnL ${base[base.event_slug.isin(bad[bad.late1h>0].event_slug)].pnl.sum():.0f}")
lt = bad[bad.late1h > 0].merge(base.groupby("event_slug").pnl.agg(["sum", "size"]).reset_index(), on="event_slug", how="left").sort_values("late1h", ascending=False).head(8)
P(tab(lt))
P("Nov 2025 backfill: 65% of Nov-2025 posts were imported >24h late (648 posts in one batch on 2025-11-24), so K_asknown for any Nov window is junk; backtest starts Dec 1 so unaffected, but the model's trailing 4-week rate for Dec 2025 events straddles the Nov backfill. Deleted posts: the CSV has no deletion flag, so deletions cannot be audited from this data; mismatches above are the only proxy.")

# ================= 7. Edge monotonicity / calibration =================
P("\n## 7. Does bigger model-minus-market edge earn more?\n")
A = W[W.lead_pct.isin(PRIM) & (W.price >= 0.001) & (W.price <= 0.5)].copy()
A["edge"] = A.p_model - A.price
A["eb"] = pd.cut(A.edge, [-1, -0.05, -0.02, 0.0, 0.02, 0.05, 0.08, 0.12, 0.2, 1])
A["rt"] = A.outcome_yes - A.price
g7 = A.groupby("eb").agg(n=("rt", "size"), events=("event_slug", "nunique"), mean_price=("price", "mean"), mean_model=("p_model", "mean"), hit=("outcome_yes", "mean")).reset_index()
g7["hit_minus_price"] = g7.hit - g7.mean_price
g7["model_minus_hit"] = g7.mean_model - g7.hit
g7["eb"] = g7.eb.astype(str)
P("All priced weekly rows (price 0.1c-50c, primary leads) binned by edge = p_model - price. Pre-fee excess return = hit - price. For a real edge, hit - price should rise with edge and track mean_model - mean_price:\n")
P(tab(g7))
from scipy import stats
sp = stats.spearmanr(A.edge, A.rt)
P(f"\nSpearman(edge, outcome-price) over all rows: rho={sp.correlation:.3f}, p={sp.pvalue:.3g} (rows are heavily clustered, p is optimistic).")
# trades only, by edge bin, with ROI
tb = []
for slip in [0.0, 0.005]:
    x = trades(W, slip)
    x["eb"] = pd.cut(x.p_model - x.entry, [0.05, 0.08, 0.12, 0.2, 1], right=False)
    for b, sub in x.groupby("eb"):
        tb.append(dict(slip=slip, edge_bin=str(b), n=len(sub), events=sub.event_slug.nunique(), hit=sub.outcome_yes.mean(), mean_entry=sub.entry.mean(), mean_model=sub.p_model.mean(), ROI=roi(sub), PnL=sub.pnl.sum(), p_boot=boot_p(sub) if len(sub) > 5 else np.nan))
P("\nStrategy trades by edge bin:\n"); P(tab(pd.DataFrame(tb)))
x = trades(W, 0.0)
P(f"\nSpearman(edge, pnl) over trades slip0: {stats.spearmanr(x.p_model-x.entry, x.pnl).correlation:.3f}")
# cluster regression slope of y on (p_model, price)
import numpy.linalg as la
X = np.c_[np.ones(len(A)), A.price, A.p_model]
bhat = la.lstsq(X, A.outcome_yes.values, rcond=None)[0]
# cluster bootstrap by event
evs_ = A.event_slug.unique(); gi = {e: np.where(A.event_slug.values == e)[0] for e in evs_}
bs_ = []
rsr = np.random.default_rng(5)
for b in range(400):
    pick = rsr.choice(evs_, len(evs_)); ix = np.concatenate([gi[e] for e in pick])
    bs_.append(la.lstsq(X[ix], A.outcome_yes.values[ix], rcond=None)[0])
bs_ = np.array(bs_)
P(f"Linear regression outcome ~ price + p_model on all rows: coef price {bhat[1]:.2f} [{np.quantile(bs_[:,1],.025):.2f},{np.quantile(bs_[:,1],.975):.2f}], coef p_model {bhat[2]:.2f} [{np.quantile(bs_[:,2],.025):.2f},{np.quantile(bs_[:,2],.975):.2f}] (event-cluster bootstrap 95%). If the market is efficient price coef ~1 and p_model coef ~0.")
# Brier for rows with common support
cal = pd.read_csv(f"{O}/chart_calibration.csv") if os.path.exists(f"{O}/chart_calibration.csv") else None

# ================= 8. Capacity =================
P("\n## 8. Capacity / dollars\n")
weeks = (W.ws.max() - W.ws.min()).days / 7
for slip, nm in [(0.0, "slip0"), (0.005, "0.5c"), (0.01, "1c")]:
    x = trades(W, slip)
    P(f"- {nm}: ${x.pnl.sum():.0f} on ${10*len(x):.0f} staked over {weeks:.0f} weeks = ${x.pnl.sum()/weeks:.1f}/week at $10/trade, {len(x)/weeks:.1f} trades/week; leave-top-5 PnL ${x.pnl.sum()-x.groupby('event_slug').pnl.sum().sort_values(ascending=False).head(5).sum():.0f}")
P("Depth (live books, medians): <=2c ask depth within 2c ~ $28, 2-5c ~ $41, 5-15c ~ $155, 15-50c ~ $45. Scaling to $100/trade, robustness.md already shows ROI +30% at p=0.12 (realistic fill).")
rp = pd.read_csv(f"{O}/repricing_by_month.csv") if os.path.exists(f"{O}/repricing_by_month.csv") else None

# overall per-lead sign test at 0.5c (21 leads)
LL = []
for l in range(0, 100, 5):
    for slip in [0.0, 0.005]:
        x = trades(W, slip, leads=[l]); LL.append(dict(lead=l, slip=slip, n=len(x), ROI=roi(x)))
LL = pd.DataFrame(LL)
for slip in [0.0, 0.005]:
    s = LL[(LL.slip == slip) & (LL.n >= 10)]
    P(f"Per-lead (21 leads) slip {slip}: {int((s.ROI>0).sum())}/{len(s)} positive. Binomial p(>= this many | 50%) = {stats.binomtest(int((s.ROI>0).sum()), len(s), .5, alternative='greater').pvalue:.3f}")


# ================= 9. Extra: model-free longshot bias & regression robustness =================
P("\n## 9. Extra objections\n")
P("9a. Is it just a model-free 'buy cheap buckets' effect? Buy EVERY weekly bucket with entry in a price band at primary leads (no model, no edge rule):\n")
rows9 = []
for lo_, hi_ in [(0.001, 0.02), (0.005, 0.05), (0.02, 0.05), (0.05, 0.15), (0.001, 0.5)]:
    for slip in [0.0, 0.005, 0.01]:
        x = W[W.lead_pct.isin(PRIM)].copy(); e = x.price + slip
        x = x[(e >= lo_) & (e <= hi_)].copy(); x["entry"] = x.price + slip
        x["pnl"] = 10 / x.entry * x.outcome_yes - 10 - 10 / x.entry * 0.05 * x.entry * (1 - x.entry)
        rows9.append(dict(band=f"{lo_}-{hi_}", slip=slip, n=len(x), events=x.event_slug.nunique(), ROI=roi(x), p_boot=boot_p(x)))
P(tab(pd.DataFrame(rows9)))
x = trades(W, 0.0); sh = x[x.entry < 0.05].pnl.sum() / x.pnl.sum()
P(f"\nShare of our slip0 PnL from entries < 5c: {sh:.0%}; from entries >=5c: {1-sh:.0%} (n={int((x.entry>=0.05).sum())}, ROI {roi(x[x.entry>=0.05]):+.0%}).")
x5 = trades(W, 0.005); x5b = x5[x5.entry >= 0.05]
P(f"At 0.5c, entries >=5c: n={len(x5b)}, ROI {roi(x5b):+.0%}, p={boot_p(x5b):.3f}; entries <5c: n={len(x5)-len(x5b)}, ROI {roi(x5[x5.entry<0.05]):+.0%}")
P("\n9b. Regression robustness (outcome ~ price + p_model, rows price 0.1c-50c). Drop top-5 PnL events / drop Dec-Feb:")
for nm, mask in [("all", np.ones(len(A), bool)), ("drop top5 events", ~A.event_slug.isin(top).values), ("Mar-Oct only", ~A.month.isin(["2025-12","2026-01","2026-02"]).values), ("only Dec-Feb", A.month.isin(["2025-12","2026-01","2026-02"]).values)]:
    Xm = X[mask]; ym = A.outcome_yes.values[mask]
    bh = la.lstsq(Xm, ym, rcond=None)[0]
    es_ = A.event_slug.values[mask]; u = np.unique(es_); gi2 = {e: np.where(es_ == e)[0] for e in u}
    bb = []
    for b in range(300):
        pick = rsr.choice(u, len(u)); ix = np.concatenate([gi2[e] for e in pick]); bb.append(la.lstsq(Xm[ix], ym[ix], rcond=None)[0][2])
    P(f" - {nm}: n={mask.sum()}, coef p_model {bh[2]:.2f} [{np.quantile(bb,.025):.2f},{np.quantile(bb,.975):.2f}], coef price {bh[1]:.2f}")

open(f"{O}/adversarial_raw.txt", "w").write("\n".join(OUT))
