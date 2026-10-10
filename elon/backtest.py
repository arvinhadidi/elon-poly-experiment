#!/usr/bin/env python3
"""Independent rebuild: NB model + backtest for Polymarket Elon tweet-count bucket markets. Never places orders."""
import os, sys, numpy as np, pandas as pd
from scipy.stats import nbinom
from scipy.special import gammaln
from scipy.optimize import minimize_scalar

BASE = os.path.dirname(os.path.abspath(__file__))
D, O = f"{BASE}/data", f"{BASE}/out"
os.makedirs(O, exist_ok=True)
rng = np.random.default_rng(12345)
FAMS = ["weekly", "48h"]
PRIMARY = [0, 25, 50, 75]
SLIPS = [0.0, 0.005, 0.01]
DEFAULT_K = 15.0
NB_REPS = 10000

def to_sec(x):  # resolution-safe epoch seconds
    return ((pd.to_datetime(x, utc=True) - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(seconds=1)).astype("int64")
# ---------------- load ----------------
P = pd.read_csv(f"{D}/posts_elonmusk.csv", usecols=["id", "createdAt", "importedAt"]).drop_duplicates("id")
P["c"] = to_sec(P.createdAt)
P["i"] = to_sec(P.importedAt)
P = P.sort_values("c").reset_index(drop=True)
PC, PI = P.c.values, P.i.values
PSLOT = (PC // 3600) % 168

ev = pd.read_csv(f"{D}/events.csv")
ev = ev[(ev.window_start_utc >= "2025-12-01") & ev.event_closed & ~ev.event_slug.str.startswith("arch-")
        & ev.bucket_lo.notna() & ev.family.isin(FAMS)].copy()
ev["S"] = to_sec(ev.window_start_utc)
ev["E"] = to_sec(ev.window_end_utc)
ev["bucket_lo"] = ev.bucket_lo.astype(int); ev["bucket_hi"] = ev.bucket_hi.astype(int)
snap = pd.read_csv(f"{D}/price_snapshots.csv", usecols=["yes_token", "lead_pct", "price", "dt_sec"])
snap = snap[snap.dt_sec.abs() <= 600].drop(columns="dt_sec")
LEADS = sorted(pd.read_csv(f"{D}/price_snapshots.csv", usecols=["lead_pct"]).lead_pct.unique())

events = ev.drop_duplicates("event_slug")[["event_slug", "family", "window_start_utc", "window_end_utc", "S", "E"]] \
    .sort_values("E").reset_index(drop=True)

# ---------------- pass 1: per event x lead decision quantities ----------------
def lam_vec(t):
    lo = np.searchsorted(PC, t - 28 * 86400, "left"); hi = np.searchsorted(PC, t, "left")
    c, i, s = PC[lo:hi], PI[lo:hi], PSLOT[lo:hi]
    ok = (c < t - 86400) | (i <= t)
    return np.bincount(s[ok], minlength=168) / 4.0

def mu_remaining(t, S, E):
    lam = lam_vec(t); a = max(t, S); mu = 0.0
    while a < E:
        b = min((a // 3600 + 1) * 3600, E)
        mu += lam[(a // 3600) % 168] * (b - a) / 3600.0
        a = b
    return mu

dec = []
for r in events.itertuples():
    lo_f, hi_f = np.searchsorted(PC, r.S, "left"), np.searchsorted(PC, r.E, "left")
    final = hi_f - lo_f
    for L in LEADS:
        t = int(round(r.S + L / 100.0 * (r.E - r.S)))
        te = min(t, r.E)
        a = np.searchsorted(PC, r.S, "left"); b = np.searchsorted(PC, te, "left")
        K_final = max(b - a, 0) if te > r.S else 0
        K_as = int(((PI[a:b] <= t)).sum()) if te > r.S else 0
        dec.append(dict(event_slug=r.event_slug, family=r.family, S=r.S, E=r.E, lead_pct=L, t=t,
                        K_asknown=K_as, K_final=K_final, final_count=final, mu=mu_remaining(t, r.S, r.E)))
dec = pd.DataFrame(dec)
dec["R_as"] = dec.final_count - dec.K_asknown
dec["R_fin"] = dec.final_count - dec.K_final

# ---------------- NB helpers ----------------
def nb_ll(k, R, mu):
    mu = np.maximum(mu, 1e-6)
    return np.sum(gammaln(R + k) - gammaln(k) - gammaln(R + 1) + k * np.log(k / (k + mu)) + R * np.log(mu / (k + mu)))

def fit_k(R, mu):
    res = minimize_scalar(lambda lk: -nb_ll(np.exp(lk), R, mu), bounds=(np.log(0.5), np.log(2000)), method="bounded")
    return float(np.exp(res.x))

# ---------------- walk-forward k and bias ----------------
N_LEAD_MIN, N_POOL_MIN = 10, 4
kcache = {}
def k_walk(fam, lead, t):
    past = dec[(dec.family == fam) & (dec.E < t)]
    pl = past[past.lead_pct == lead]
    n_lead = len(pl)
    key = (fam, lead, n_lead, len(past))
    if key in kcache: return kcache[key]
    if n_lead >= N_LEAD_MIN:
        out = (fit_k(pl.R_as.values, pl.mu.values), "lead", n_lead)
    elif past.event_slug.nunique() >= N_POOL_MIN:
        out = (fit_k(past.R_as.values, past.mu.values), "pooled", past.event_slug.nunique())
    else:
        out = (DEFAULT_K, "default", past.event_slug.nunique())
    kcache[key] = out
    return out

def bias_walk(fam, lead, t):
    pl = dec[(dec.family == fam) & (dec.lead_pct == lead) & (dec.E < t)]
    return float((pl.R_as - pl.mu).mean()) if len(pl) >= 5 else 0.0

ks = [k_walk(r.family, r.lead_pct, r.t) for r in dec.itertuples()]
dec["k_used"] = [x[0] for x in ks]; dec["k_src"] = [x[1] for x in ks]; dec["k_n"] = [x[2] for x in ks]
dec["bias"] = [bias_walk(r.family, r.lead_pct, r.t) for r in dec.itertuples()]
kin = {(f, l): fit_k(g.R_as.values, g.mu.values) for (f, l), g in dec.groupby(["family", "lead_pct"])}
dec["k_insample"] = [kin[(r.family, r.lead_pct)] for r in dec.itertuples()]

# ---------------- bucket probabilities ----------------
def bucket_p(K, mu, k, lo, hi):
    mu = np.maximum(mu, 1e-6)
    p = k / (k + mu)
    return np.clip(nbinom.cdf(hi - K, k, p) - nbinom.cdf(lo - 1 - K, k, p), 0, 1)

df = ev[["event_slug", "family", "window_start_utc", "window_end_utc", "bucket_lo", "bucket_hi", "yes_token", "outcome_yes"]] \
    .merge(dec.drop(columns=["S", "E", "t"]), on=["event_slug", "family"])
df = df.merge(snap, on=["yes_token", "lead_pct"], how="left")
df["p_model"] = bucket_p(df.K_asknown.values, df.mu.values, df.k_used.values, df.bucket_lo.values, df.bucket_hi.values)
df["p_model_lookahead"] = bucket_p(df.K_final.values, df.mu.values, df.k_used.values, df.bucket_lo.values, df.bucket_hi.values)
df["p_model_kinsample"] = bucket_p(df.K_asknown.values, df.mu.values, df.k_insample.values, df.bucket_lo.values, df.bucket_hi.values)
df["p_model_bias"] = bucket_p(df.K_asknown.values, np.maximum(df.mu.values + df.bias.values, 1e-6), df.k_used.values, df.bucket_lo.values, df.bucket_hi.values)
df["outcome_yes"] = df.outcome_yes.astype(int)
cols = ["event_slug", "family", "window_start_utc", "window_end_utc", "lead_pct", "bucket_lo", "bucket_hi", "outcome_yes", "price",
        "K_asknown", "K_final", "mu", "k_used", "p_model", "p_model_lookahead", "final_count",
        "k_src", "k_insample", "bias", "p_model_kinsample", "p_model_bias"]
df = df[cols]
df.to_parquet(f"{O}/bt_preds.parquet", index=False)

# ---------------- trades ----------------
def make_trades(d, pcol, variant, slip):
    x = d[d.price.notna()].copy()
    x["entry"] = x.price + slip
    x["p"] = x[pcol]
    x["edge"] = x.p - x.entry
    x = x[(x.edge >= 0.05) & (x.entry <= 0.50) & (x.entry >= 0.001)].copy()
    x["shares"] = 10.0 / x.entry
    x["fee"] = 0.05 * x.entry * (1 - x.entry)
    x["pnl"] = x.shares * x.outcome_yes - 10.0 - x.shares * x.fee
    x["variant"] = variant; x["slippage"] = slip; x["p_model"] = x.p
    return x

tr = []
for var, pc in [("asknown", "p_model"), ("lookahead", "p_model_lookahead")]:
    for s in SLIPS:
        tr.append(make_trades(df, pc, var, s))
tr = pd.concat(tr, ignore_index=True)
tr["stake"] = 10.0
tr["band_lt2c"] = tr.entry < 0.02
tcols = ["variant", "slippage", "family", "event_slug", "window_start_utc", "window_end_utc", "lead_pct", "bucket_lo", "bucket_hi",
         "price", "entry", "p_model", "edge", "shares", "fee", "pnl", "outcome_yes", "band_lt2c"]
tr[tcols].to_csv(f"{O}/bt_trades.csv", index=False)

# ---------------- clusters ----------------
def components(evs):
    evs = evs.sort_values("S"); comp, cur, end, cid = {}, -1, -1, -1
    for r in evs.itertuples():
        if r.S >= end or cid < 0:
            cid += 1; end = r.E
        else:
            end = max(end, r.E)
        comp[r.event_slug] = cid
    return comp
comp_map, blk_map = {}, {}
for f in FAMS:
    e = events[events.family == f]
    comp_map.update({k: f"{f}-c{v}" for k, v in components(e).items()})
    blk_map.update({r.event_slug: f"{f}-b{int(r.E // (14 * 86400))}" for r in e.itertuples()})
tr["comp"] = tr.event_slug.map(comp_map); tr["blk"] = tr.event_slug.map(blk_map)
ncomp = {f: len(set(v for k, v in comp_map.items() if k.startswith(tuple(events[events.family == f].event_slug)) and v.startswith(f))) for f in FAMS}
ncomp = {f: len({v for v in comp_map.values() if v.startswith(f + "-")}) for f in FAMS}
nblk = {f: len({v for v in blk_map.values() if v.startswith(f + "-")}) for f in FAMS}

def boot_p(g, key):
    a = g.groupby(key).agg(pnl=("pnl", "sum"), st=("stake", "sum"))
    n = len(a)
    if n < 2: return np.nan, n
    idx = rng.integers(0, n, size=(NB_REPS, n))
    roi = a.pnl.values[idx].sum(1) / a.st.values[idx].sum(1)
    return float((roi <= 0).mean()), n

def indep(g):
    w = g.drop_duplicates("event_slug")[["window_start_utc", "window_end_utc"]].sort_values("window_end_utc")
    last, c = "", 0
    for r in w.itertuples():
        if r.window_start_utc >= last:
            c += 1; last = r.window_end_utc
    return c

def stats(g):
    if len(g) == 0: return dict(n=0, ev=0, roi=np.nan, p_ev=np.nan, p_comp=np.nan, ncl=0, p_blk=np.nan, nblk=0, indep=0, pnl=0.0)
    p_ev, _ = boot_p(g, "event_slug"); p_c, nc = boot_p(g, "comp"); p_b, nb = boot_p(g, "blk")
    return dict(n=len(g), ev=g.event_slug.nunique(), roi=g.pnl.sum() / g.stake.sum(), p_ev=p_ev, p_comp=p_c, ncl=nc,
                p_blk=p_b, nblk=nb, indep=indep(g), pnl=g.pnl.sum())

rows = []
LEADSETS = [("0", [0]), ("25", [25]), ("50", [50]), ("75", [75]), ("primary 0/25/50/75", PRIMARY), ("all grid leads", list(LEADS))] \
    + [(str(l), [l]) for l in LEADS if l not in PRIMARY]
BANDS = [("all", None), ("<2c", True), (">=2c", False)]
for f in FAMS:
    for var in ["asknown", "lookahead"]:
        for s in SLIPS:
            base = tr[(tr.family == f) & (tr.variant == var) & (tr.slippage == s)]
            for ln, ls in LEADSETS:
                for bn, bf in BANDS:
                    g = base[base.lead_pct.isin(ls)]
                    if bf is not None: g = g[g.band_lt2c == bf]
                    rows.append(dict(family=f, variant=var, slip=s, leads=ln, band=bn, **stats(g)))
S = pd.DataFrame(rows)
S.to_csv(f"{O}/bt_stats.csv", index=False)

# ---------------- calibration ----------------
cal = df.dropna(subset=["price"]).copy()
cnt = df.groupby(["event_slug", "lead_pct"]).bucket_lo.count().rename("nb")
okc = cal.groupby(["event_slug", "lead_pct"]).price.count().rename("np").reset_index().merge(cnt.reset_index())
okc = okc[okc.nb == okc.np][["event_slug", "lead_pct"]]
cal = cal.merge(okc, on=["event_slug", "lead_pct"])
cal["pn"] = cal.price / cal.groupby(["event_slug", "lead_pct"]).price.transform("sum")
def clipp(x): return np.clip(x, 1e-4, 1 - 1e-4)
def sc(p, y): return np.mean((p - y) ** 2), -np.mean(y * np.log(clipp(p)) + (1 - y) * np.log(1 - clipp(p)))
cr = []
for (f, l), g in list(cal.groupby(["family", "lead_pct"])) + [((f, "all"), g) for f, g in cal.groupby("family")]:
    y = g.outcome_yes.values
    r = dict(family=f, lead=l, n_rows=len(g), n_events=g.event_slug.nunique())
    for nm, c in [("model", "p_model"), ("model_lookahead", "p_model_lookahead"), ("model_kinsample", "p_model_kinsample"),
                  ("model_bias", "p_model_bias"), ("mkt_raw", "price"), ("mkt_norm", "pn")]:
        b, ll = sc(g[c].values, y); r[f"brier_{nm}"] = b; r[f"ll_{nm}"] = ll
    cr.append(r)
cr = pd.DataFrame(cr)

# ---------------- k over time ----------------
kt = dec[dec.lead_pct.isin(PRIMARY)].sort_values(["family", "lead_pct", "E"])
kt["month"] = pd.to_datetime(kt.E.astype("int64") * 10**9, utc=True).dt.strftime("%Y-%m")
kt_tab = kt.groupby(["family", "lead_pct", "month"]).agg(k=("k_used", "mean"), src=("k_src", lambda s: "/".join(sorted(set(s))))).reset_index()
defaults = dec[(dec.k_src == "default")].groupby("family").event_slug.nunique()
defev = dec[(dec.k_src == "default") & dec.lead_pct.isin([0])].groupby("family").event_slug.apply(lambda s: ", ".join(sorted(s.unique())[:6]))

# ---------------- summary md ----------------
def fm(x, d=3): return "" if pd.isna(x) else f"{x:.{d}f}"
def tab(sub, cols_):
    h = "| " + " | ".join(cols_) + " |\n|" + "---|" * len(cols_) + "\n"
    return h + "".join("| " + " | ".join(str(v) for v in r) + " |\n" for r in sub)

def stat_table(var, band="all", leadlist=None):
    leadlist = leadlist or ["0", "25", "50", "75", "primary 0/25/50/75", "all grid leads"]
    out = []
    for f in FAMS:
        for s in SLIPS:
            for ln in leadlist:
                r = S[(S.family == f) & (S.variant == var) & (S.slip == s) & (S.leads == ln) & (S.band == band)].iloc[0]
                out.append([f, s, ln, r.n, r.ev, f"{r.roi*100:+.0f}%" if r.n else "", fm(r.p_ev), fm(r.p_comp), r.ncl, fm(r.p_blk), r.nblk, r.indep, f"{r.pnl:.0f}"])
    return tab(out, ["family", "slip", "lead", "n trades", "n events", "ROI", "p event-clust", "p comp-clust", "#comp", "p 14d-block", "#blk", "indep bets", "PnL $"])

md = []
md.append("# Elon tweet-count buckets: independent rebuild\n")
md.append(f"Events: {events.family.value_counts().to_dict()} (closed, window_start >= 2025-12-01, not arch-). Decision rows: {len(df)} (event x bucket x lead), "
          f"rows with matched price: {int(df.price.notna().sum())}. Rule: buy YES if p_model - entry >= 0.05, entry <= 0.50, entry >= 0.001, $10 flat, fee 0.05*e*(1-e)/share. "
          f"Default NB size k={DEFAULT_K} until >= {N_POOL_MIN} prior events (pooled over leads), per-lead fit once >= {N_LEAD_MIN} prior events at that lead.\n")
md.append(f"Clusters: connected components of overlapping windows -> weekly {ncomp['weekly']}, 48h {ncomp['48h']} (all-events); 14-day blocks by window_end -> weekly {nblk['weekly']}, 48h {nblk['48h']}. "
          "If components collapse to ~1 chain the component p-value is NaN/meaningless and the 14d-block p is the one to read. Cluster bootstraps resample clusters that contain >=1 trade.\n")
md.append("## Headline: as-known model, all prices (band = all)\n" + stat_table("asknown"))
md.append("\n## As-known, entry < 2c band only\n" + stat_table("asknown", "<2c", ["primary 0/25/50/75", "all grid leads"]))
md.append("\n## As-known, entry >= 2c only\n" + stat_table("asknown", ">=2c", ["primary 0/25/50/75", "all grid leads"]))
md.append("\n## Lookahead variant (K = final count at t, ignores importedAt)\n" + stat_table("lookahead", "all", ["primary 0/25/50/75", "all grid leads"]))
# lookahead vs asknown pnl diff
dd = []
for f in FAMS:
    for s in SLIPS:
        for ln in ["primary 0/25/50/75", "all grid leads"]:
            a = S[(S.family == f) & (S.variant == "asknown") & (S.slip == s) & (S.leads == ln) & (S.band == "all")].iloc[0]
            b = S[(S.family == f) & (S.variant == "lookahead") & (S.slip == s) & (S.leads == ln) & (S.band == "all")].iloc[0]
            dd.append([f, s, ln, a.n, f"{a.pnl:.0f}", f"{a.roi*100:+.0f}%", b.n, f"{b.pnl:.0f}", f"{b.roi*100:+.0f}%", f"{b.pnl-a.pnl:+.0f}"])
md.append("\n### As-known vs lookahead PnL\n" + tab(dd, ["family", "slip", "leads", "n asknown", "PnL asknown", "ROI asknown", "n lookahead", "PnL lookahead", "ROI lookahead", "PnL diff (look - as)"]))
lagd = df.drop_duplicates(["event_slug", "lead_pct"]).assign(d=lambda x: x.K_final - x.K_asknown).groupby(["family", "lead_pct"]).d.mean().unstack(0)
md.append("\n### Mean (K_final - K_asknown) posts by lead (how much the lookahead leaks)\n" + tab([[l] + [fm(lagd.loc[l, f], 2) for f in FAMS] for l in lagd.index], ["lead"] + FAMS))
md.append("\n## Per-lead breakdown, as-known, slippage 0 and 1c (all grid leads)\n")
bl = []
for f in FAMS:
    for s in [0.0, 0.01]:
        for l in LEADS:
            r = S[(S.family == f) & (S.variant == "asknown") & (S.slip == s) & (S.leads == str(l)) & (S.band == "all")].iloc[0]
            bl.append([f, s, l, r.n, r.ev, f"{r.roi*100:+.0f}%" if r.n else "", fm(r.p_ev), fm(r.p_blk), r.indep])
md.append(tab(bl, ["family", "slip", "lead", "n", "events", "ROI", "p event", "p 14d-block", "indep"]))
md.append("\n## Calibration (rows where every bucket of the event x lead has a matched price; same rows for all columns)\n")
cc = []
for r in cr.itertuples():
    cc.append([r.family, r.lead, r.n_events, r.n_rows] + [fm(getattr(r, f"brier_{m}"), 4) for m in ["model", "model_lookahead", "model_kinsample", "model_bias", "mkt_raw", "mkt_norm"]]
              + [fm(getattr(r, f"ll_{m}"), 4) for m in ["model", "model_kinsample", "model_bias", "mkt_raw", "mkt_norm"]])
md.append(tab(cc, ["family", "lead", "events", "rows", "Brier model", "Brier lookahead", "Brier k-insample", "Brier bias-adj", "Brier mkt raw", "Brier mkt norm",
                   "LL model", "LL k-insample", "LL bias-adj", "LL mkt raw", "LL mkt norm"]))
md.append("\n## Trades by variant of model: bias-adjusted (late-import/bias term) and k-insample, weekly+48h, primary leads, slip 0, for comparison\n")
alt = []
for nm, pc in [("p_model (walk-fwd k)", "p_model"), ("p_model_kinsample", "p_model_kinsample"), ("p_model_bias", "p_model_bias")]:
    for f in FAMS:
        t_ = make_trades(df[(df.family == f) & df.lead_pct.isin(PRIMARY)], pc, "x", 0.0)
        alt.append([nm, f, len(t_), t_.event_slug.nunique(), f"{t_.pnl.sum()/max(t_.shape[0]*10,1)*100:+.0f}%"])
md.append(tab(alt, ["model", "family", "n", "events", "ROI"]))
md.append("\n## k over time (mean walk-forward k_used by exit-month of the event; src = default/pooled/lead)\n")
for f in FAMS:
    pv = kt_tab[kt_tab.family == f].pivot(index="month", columns="lead_pct", values="k")
    sv = kt_tab[kt_tab.family == f].pivot(index="month", columns="lead_pct", values="src")
    md.append(f"\n### {f}\n" + tab([[m] + [f"{pv.loc[m, l]:.1f} ({sv.loc[m, l]})" if pd.notna(pv.loc[m, l]) else "" for l in pv.columns] for m in pv.index], ["month"] + [f"lead {l}" for l in pv.columns]))
md.append("\nIn-sample (look-ahead) k per family x lead: " + ", ".join(f"{f}/{l}: {v:.1f}" for (f, l), v in sorted(kin.items()) if l in PRIMARY) + "\n")
md.append("\nEvents using default k at lead 0: " + "; ".join(f"{f}: {defev.get(f, '')}" for f in FAMS) + f"  (number of events that ever used the default at some lead: {defaults.to_dict()})\n")

def g_(f, var, sl, ln, band="all"):
    return S[(S.family == f) & (S.variant == var) & (S.slip == sl) & (S.leads == ln) & (S.band == band)].iloc[0]
def cl(f, sl, ln):
    r = g_(f, "asknown", sl, ln); return f"n={r.n}/{r.ev} ev, ROI {r.roi*100:+.0f}%, p_event={r.p_ev:.3f}, p_14d-block={r.p_blk:.3f}"
expl = f"""
## Comparison with the earlier claim (weekly, edge>=5pp, price<=50c, $10 flat)

| item | earlier claim | this rebuild (as-known, weekly) |
|---|---|---|
| all leads, 0 slip | 298 trades / 65 events, +115%, p=0.001 | primary leads 0/25/50/75: {cl('weekly', 0.0, 'primary 0/25/50/75')}; all 21 grid leads: {cl('weekly', 0.0, 'all grid leads')} |
| 1c slippage | +66%, p=0.012 | primary: {cl('weekly', 0.01, 'primary 0/25/50/75')}; all grid leads: {cl('weekly', 0.01, 'all grid leads')} |
| start of window (lead 0) | +90%, n=47, p=0.25 | {cl('weekly', 0.0, '0')} |
| 50% elapsed | +224%, p=0.007 | {cl('weekly', 0.0, '50')} |

Explanation (the earlier code was not available, so these are tested or reasoned, not diffed line by line):
1. As-known vs lookahead count is NOT the reason. The mean gap K_final - K_asknown is under ~1.5 posts at every lead (largest late in weekly windows), and lookahead vs as-known PnL differs by only a few tens of dollars (table above). The earlier number is not an artefact of using the final count.
2. Same sign, weaker significance. Directionally the rebuild reproduces positive weekly ROI at 0 slippage (+68% primary leads, +53% all leads) and a hot spot at 50-55% elapsed (+156% / +251%), but the effect is about half the size claimed and p-values are 0.02 (primary, event- or block-clustered), not 0.001. The earlier count of 298 trades / 65 events is in between my primary-lead (384 / 86) and nothing else I can match; trade counts depend on dispersion k and on the 5pp rule, which I fit walk-forward (k 13 -> 5.5 for weekly lead 0-75), whereas a single in-sample k (the k-insample row above: +80%) is somewhat more favourable.
3. Slippage fragility. Much of the PnL comes from entries below ~2c where a 0.5-1c slippage multiplies the entry price by 1.3-3x. At 1c slip weekly ROI falls to {g_('weekly','asknown',0.01,'primary 0/25/50/75').roi*100:+.0f}% (p={g_('weekly','asknown',0.01,'primary 0/25/50/75').p_ev:.2f}) and with all grid leads it is {g_('weekly','asknown',0.01,'all grid leads').roi*100:+.0f}%; the earlier +66% at 1c is not reproduced. In the >=2c band weekly ROI at 0 slip is +79% (p~0.003) but only +31% at 1c (p~0.11).
4. Independence. Weekly windows overlap in one chain (1 component), so the event bootstrap is anti-conservative; 14-day blocks (23) and greedy independent bets (~43 of 88 events at most) give the honest count. Combined leads are not independent decisions at all (same event, same outcome).
5. Calibration does not support a model edge over the market: model Brier/log-loss is worse than market-normalised in 48h at all leads, and roughly equal in weekly (weekly all-leads Brier model 0.0323 vs market-normalised 0.0328, raw 0.0382 because lead-0 raw prices sum to >1). Positive ROI is therefore concentrated in tail/longshot buckets where a fat-tailed NB assigns more mass than the market; these are lottery-like (few wins drive PnL), especially for 48h (<2c band ROI +300%+ on ~100 trades, p~0.26).
6. Fee convention: fee per share is charged on all shares (including losers), per the spec, so a loss is -105% at e->0, and ROI cannot be below about -105%.
"""
open(f"{O}/bt_summary.md", "w").write("\n".join(md) + expl)
os.remove(f"{O}/bt_stats.csv") if False else None
print("done")
