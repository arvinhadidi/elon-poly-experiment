#!/usr/bin/env python3
"""Out-of-sample replication of the Elon NB tweet-count model (backtest.py logic, unchanged) on related
xtracker-settled Polymarket families. No retuning; only k is fitted walk-forward on each family's own past events.
Never places orders."""
import os, sys, numpy as np, pandas as pd
from scipy.stats import nbinom
from scipy.special import gammaln
from scipy.optimize import minimize_scalar
BASE = os.path.dirname(os.path.abspath(__file__)); D = f"{BASE}/data/related"; O = f"{BASE}/out"
rng = np.random.default_rng(12345)
FAMS = ["trump_truth", "whitehouse", "khamenei", "zelenskyy", "nyc_mayor", "cz", "tedcruz"]
PRIMARY = [0, 25, 50, 75]; SLIPS = [0.0, 0.005, 0.01]; DEFAULT_K = 15.0; NB_REPS = 10000
N_LEAD_MIN, N_POOL_MIN = 10, 4

def to_sec(x): return ((pd.to_datetime(x, utc=True) - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(seconds=1)).astype("int64")

# ---- NB helpers (copied from backtest.py) ----
def nb_ll(k, R, mu):
    mu = np.maximum(mu, 1e-6)
    return np.sum(gammaln(R + k) - gammaln(k) - gammaln(R + 1) + k * np.log(k / (k + mu)) + R * np.log(mu / (k + mu)))
def fit_k(R, mu):
    res = minimize_scalar(lambda lk: -nb_ll(np.exp(lk), R, mu), bounds=(np.log(0.5), np.log(2000)), method="bounded")
    return float(np.exp(res.x))
def bucket_p(K, mu, k, lo, hi):
    mu = np.maximum(mu, 1e-6); p = k / (k + mu)
    return np.clip(nbinom.cdf(hi - K, k, p) - nbinom.cdf(lo - 1 - K, k, p), 0, 1)

def run_family(fam):
    P = pd.read_csv(f"{D}/{fam}/posts.csv").drop_duplicates("id")
    P["c"] = to_sec(P.createdAt); P["i"] = to_sec(P.importedAt); P = P.sort_values("c").reset_index(drop=True)
    PC, PI = P.c.values, P.i.values; PSLOT = (PC // 3600) % 168
    bk = pd.read_csv(f"{D}/{fam}/buckets.csv")
    bk = bk[~bk.event_slug.str.startswith("arch-")]  # same exclusion as backtest.py
    snap = pd.read_csv(f"{D}/{fam}/snapshots.csv", usecols=["yes_token", "lead_pct", "price"])  # already +-600s matched, else NaN
    bk["S"] = to_sec(bk.window_start_utc); bk["E"] = to_sec(bk.window_end_utc)
    events = bk.drop_duplicates("event_slug")[["event_slug", "family", "window_start_utc", "window_end_utc", "S", "E"]].sort_values("E").reset_index(drop=True)

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
        final = np.searchsorted(PC, r.E, "left") - np.searchsorted(PC, r.S, "left")
        for L in PRIMARY:
            t = int(round(r.S + L / 100.0 * (r.E - r.S))); te = min(t, r.E)
            a = np.searchsorted(PC, r.S, "left"); b = np.searchsorted(PC, te, "left")
            K_as = int((PI[a:b] <= t).sum()) if te > r.S else 0
            dec.append(dict(event_slug=r.event_slug, family=fam, S=r.S, E=r.E, lead_pct=L, t=t, K_asknown=K_as,
                            final_count=final, mu=mu_remaining(t, r.S, r.E)))
    dec = pd.DataFrame(dec); dec["R_as"] = dec.final_count - dec.K_asknown
    kcache = {}
    def k_walk(lead, t):
        past = dec[dec.E < t]; pl = past[past.lead_pct == lead]; n_lead = len(pl)
        key = (lead, n_lead, len(past))
        if key in kcache: return kcache[key]
        if n_lead >= N_LEAD_MIN: out = (fit_k(pl.R_as.values, pl.mu.values), "lead")
        elif past.event_slug.nunique() >= N_POOL_MIN: out = (fit_k(past.R_as.values, past.mu.values), "pooled")
        else: out = (DEFAULT_K, "default")
        kcache[key] = out; return out
    ks = [k_walk(r.lead_pct, r.t) for r in dec.itertuples()]
    dec["k_used"] = [x[0] for x in ks]; dec["k_src"] = [x[1] for x in ks]
    df = bk.drop(columns=["S", "E"]).merge(dec.drop(columns=["S", "E", "t"]), on=["event_slug", "family"])
    df = df.merge(snap, on=["yes_token", "lead_pct"], how="left")
    df["p_model"] = bucket_p(df.K_asknown.values, df.mu.values, df.k_used.values, df.bucket_lo.values, df.bucket_hi.values)
    # tracker verification
    chk = df.drop_duplicates("event_slug")[["event_slug", "final_count"]].merge(
        df[(df.outcome_yes == 1) & (df.lead_pct == 0)].groupby("event_slug").agg(lo=("bucket_lo", "first"), hi=("bucket_hi", "first"), n_win=("outcome_yes", "sum")).reset_index(), on="event_slug", how="left")
    chk["match"] = (chk.n_win == 1) & (chk.final_count >= chk.lo) & (chk.final_count <= chk.hi)
    chk["family"] = fam
    return df, chk

dfs, chks = [], []
for f in FAMS:
    d, c = run_family(f); dfs.append(d); chks.append(c); print(f, len(c), int(c.match.sum()), flush=True)
df = pd.concat(dfs, ignore_index=True); chk = pd.concat(chks, ignore_index=True)
chk.to_csv(f"{O}/related_bt_tracker_check.csv", index=False)
good = set(chk[chk.match].event_slug)
df = df[df.event_slug.isin(good)].copy()
df["cluster"] = df.family + "|" + df.event_slug

# ---- trades (same rule as backtest.py) ----
def make_trades(d, slip):
    x = d[d.price.notna()].copy(); x["entry"] = x.price + slip; x["edge"] = x.p_model - x.entry
    x = x[(x.edge >= 0.05) & (x.entry <= 0.50) & (x.entry >= 0.001)].copy()
    x["shares"] = 10.0 / x.entry; x["fee"] = 0.05 * x.entry * (1 - x.entry)
    x["pnl"] = x.shares * x.outcome_yes - 10.0 - x.shares * x.fee; x["slippage"] = slip; x["stake"] = 10.0
    return x
tr = pd.concat([make_trades(df, s) for s in SLIPS], ignore_index=True)
tcols = ["family", "event_slug", "window_start_utc", "window_end_utc", "lead_pct", "slippage", "bucket_label", "bucket_lo", "bucket_hi",
         "price", "entry", "p_model", "edge", "shares", "fee", "pnl", "outcome_yes", "k_used", "k_src"]
tr[tcols].to_csv(f"{O}/related_bt_trades.csv", index=False)

def boot_p(g):
    a = g.groupby("cluster").agg(pnl=("pnl", "sum"), st=("stake", "sum")); n = len(a)
    if n < 2: return np.nan
    idx = rng.integers(0, n, size=(NB_REPS, n))
    return float(((a.pnl.values[idx].sum(1) / a.st.values[idx].sum(1)) <= 0).mean())
def roi_cell(g):
    if len(g) == 0: return "n/a"
    return f"{g.pnl.sum()/g.stake.sum()*100:+.0f}%"

# ---- narrowness + Brier on fully priced event x lead ----
cal = df.dropna(subset=["price"]).copy()
cnt = df.groupby(["event_slug", "lead_pct"]).bucket_lo.count().rename("nb")
okc = cal.groupby(["event_slug", "lead_pct"]).price.count().rename("np").reset_index().merge(cnt.reset_index())
okc = okc[(okc.nb == okc.np) & (okc.price if False else True)][["event_slug", "lead_pct"]]
cal = cal.merge(okc, on=["event_slug", "lead_pct"])
cal["pn"] = cal.price / cal.groupby(["event_slug", "lead_pct"]).price.transform("sum")
W = 20.0  # all buckets are 20 wide; open ends treated as width 20
cal["lo_"] = cal.bucket_lo.astype(float); cal["hi_"] = np.where(cal.bucket_hi > 10**5, cal.bucket_lo + W - 1, cal.bucket_hi).astype(float)
cal["hi_"] = np.where(cal.bucket_lo == 0, cal.hi_, cal.hi_)
cal["mid"] = (cal.lo_ + cal.hi_) / 2; cal["wid"] = cal.hi_ - cal.lo_ + 1
def zrow(g):
    g = g.sort_values("lo_"); p = g.pn.values
    m = (p * g.mid.values).sum(); var = (p * (g.mid.values ** 2 + (g.wid.values ** 2 - 1) / 12)).sum() - m ** 2
    fin = g.final_count.iloc[0]; cum = np.cumsum(p) - p
    j = np.where((g.lo_.values <= fin) & (fin <= g.hi_.values))[0]
    if len(j) == 0: j = [0 if fin < g.lo_.values[0] else len(g) - 1]
    j = j[0]; u = cum[j] + p[j] * np.clip((fin - g.lo_.values[j] + 0.5) / g.wid.values[j], 0, 1)
    return pd.Series(dict(mkt_mean=m, mkt_sd=np.sqrt(var), z=(fin - m) / np.sqrt(var), pit=u, final=fin))
Z = cal.groupby(["family", "event_slug", "lead_pct"]).apply(zrow, include_groups=False).reset_index()
Z["outer20"] = (Z.pit < 0.10) | (Z.pit > 0.90)
Z.to_csv(f"{O}/related_bt_z.csv", index=False)
def nar(g): return (g.z.std(ddof=1) if len(g) > 1 else np.nan, g.outer20.mean() if len(g) else np.nan, len(g), g.event_slug.nunique())
def brier(g, c): return np.mean((g[c].values - g.outcome_yes.values) ** 2)

# ---- report ----
def fm(x, d=3): return "" if pd.isna(x) else f"{x:.{d}f}"
def tab(rows, cols): return "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n" + "".join("| " + " | ".join(str(v) for v in r) + " |\n" for r in rows)
cols = ["family", "n events (scored)", "tracker match", "n trades (0c)", "ROI 0c", "ROI 0.5c", "ROI 1c", "p boot (0c / 0.5c / 1c)", "SD(z)", "outer-20% share", "Brier model", "Brier mkt-norm"]
rows = []
def build_row(name, fsel):
    c = chk if fsel is None else chk[chk.family.isin(fsel)]
    t = tr if fsel is None else tr[tr.family.isin(fsel)]
    z = Z if fsel is None else Z[Z.family.isin(fsel)]
    ca = cal if fsel is None else cal[cal.family.isin(fsel)]
    t0 = {s: t[(t.slippage == s)] for s in SLIPS}
    sd, out, nz, ne = nar(z)
    return [name, f"{int(c.match.sum())}", f"{c.match.sum()}/{len(c)} = {c.match.mean()*100:.0f}%", len(t0[0.0]),
            roi_cell(t0[0.0]), roi_cell(t0[0.005]), roi_cell(t0[0.01]),
            " / ".join(fm(boot_p(t0[s]) if len(t0[s]) else np.nan, 3) for s in SLIPS),
            fm(sd, 2), fm(out, 2), fm(brier(ca, "p_model"), 4), fm(brier(ca, "pn"), 4)]
for f in FAMS: rows.append(build_row(f, [f]))
rows.append(build_row("POOLED", None))
md = ["# Out-of-sample replication: Elon NB count model on related xtracker families\n",
      "Model, rule and costs identical to backtest.py (as-known count with importedAt <= t, NB remaining posts with trailing-4-week hour-of-week mean, "
      "buy YES if p_model - entry >= 0.05 and entry <= 0.50, $10 flat, taker fee 0.05*e*(1-e)/share, slippage 0/0.5c/1c). Leads 0/25/50/75, pooled across leads in the ROI/p/SD(z)/Brier columns. "
      "Only k differs: fitted walk-forward on each family's own past events (default 15 until 4 prior events, pooled, then per-lead once 10 prior events). No other tuning. "
      "p boot = one-sided event-clustered bootstrap (H0 ROI <= 0, 10000 reps, clusters = events with >= 1 trade; leads of one event share a cluster).\n",
      "Excluded: Elon series 12076 (elon-tweet-mention) is a 'will Elon post the word X' mention market (winning labels are words such as Texas/Tesla), not a post-count bucket market, so the count model does not apply.\n",
      "Narrowness: z = (final tracker count - market mean)/market SD from price-normalised bucket mids (within-bucket uniform variance included; open-ended top bucket treated as 20 wide); "
      "outer-20% share = fraction of outcomes with market-CDF PIT < 0.10 or > 0.90 (calibrated market: SD(z)=1, share=0.20; SD(z)>1 / share>0.20 means the market is too narrow). "
      "Computed only on event x lead rows where every bucket has a matched price (+-600 s). Brier = mean over bucket rows on those same rows.\n",
      "## Main table\n" + tab(rows, cols)]
# per-lead narrowness/brier
pl = []
for f in FAMS + ["POOLED"]:
    for L in PRIMARY:
        z = Z[(Z.lead_pct == L) & ((Z.family == f) if f != "POOLED" else True)]
        ca = cal[(cal.lead_pct == L) & ((cal.family == f) if f != "POOLED" else True)]
        t = tr[(tr.lead_pct == L) & (tr.slippage == 0.0) & ((tr.family == f) if f != "POOLED" else True)]
        sd, out, nz, ne = nar(z)
        pl.append([f, L, ne, fm(sd, 2), fm(out, 2), fm(brier(ca, "p_model"), 4) if len(ca) else "", fm(brier(ca, "pn"), 4) if len(ca) else "", len(t), roi_cell(t)])
md.append("\n## Per family x lead\n" + tab(pl, ["family", "lead %", "events w/ full book", "SD(z)", "outer-20% share", "Brier model", "Brier mkt-norm", "n trades (0c)", "ROI 0c"]))
mm = chk[~chk.match]
md.append("\n## Tracker verification (tracker count in resolved bucket)\n" + tab(
    [[f, len(chk[chk.family == f]), int(chk[chk.family == f].match.sum())] for f in FAMS], ["family", "events", "match"]))
md.append("\nDropped (mismatched) events from scoring: " + (", ".join(f"{r.family}:{r.event_slug} (tracker {r.final_count} vs bucket {r.lo}-{r.hi})" for r in mm.itertuples()) if len(mm) else "none") + "\n")
tl = tr[tr.slippage == 0.0]
md.append(f"\nTrades at 0 slip: {len(tl)}; share with entry < 2c: {(tl.entry < 0.02).mean():.2f}. Depth note: books on these markets are thin ($20-200 within 2c), so $10 per trade fills are optimistic and trade counts overstate capacity.\n")
open(f"{O}/related_bt.md", "w").write("\n".join(md))
print("\n".join(md))
