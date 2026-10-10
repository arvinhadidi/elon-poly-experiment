#!/usr/bin/env python3
"""Robustness analysis of the Elon-tweet-count bucket backtest. Deterministic, read-only (never places orders)."""
import json, numpy as np, pandas as pd
D = "/home/user/elon-poly-experiment/elon"
O = f"{D}/out"
rng = np.random.default_rng(20261010)
NB = 10000
PRIMARY = [0, 25, 50, 75]
SLIPS = [0.0, 0.005, 0.01]
MD = []          # markdown lines
J = {}           # json results

# ------------------------------------------------------------------ helpers
def fm(x, d=3):
    if x is None or (isinstance(x, float) and np.isnan(x)): return ""
    return f"{x:.{d}f}"
def pc(x, d=0):
    return "" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{100*x:+.{d}f}%"
def tab(rows, cols):
    s = "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n"
    for r in rows: s += "| " + " | ".join(str(v) for v in r) + " |\n"
    return s

def boot_p(g, key, reps=NB):
    """P(bootstrap ROI <= 0), resampling clusters given by column `key`."""
    if len(g) == 0: return np.nan
    a = g.groupby(key).agg(pnl=("pnl", "sum"), st=("stake", "sum"))
    n = len(a)
    if n < 2: return np.nan
    idx = rng.integers(0, n, size=(reps, n))
    roi = a.pnl.values[idx].sum(1) / a.st.values[idx].sum(1)
    return float((roi <= 0).mean())

def roi(g): return g.pnl.sum() / g.stake.sum() if len(g) and g.stake.sum() > 0 else np.nan

# ------------------------------------------------------------------ load
tr = pd.read_csv(f"{O}/bt_trades.csv")
pr = pd.read_parquet(f"{O}/bt_preds.parquet")
bk = pd.read_csv(f"{D}/data/ops_books.csv")
for d_ in (tr, pr):
    d_["S"] = pd.to_datetime(d_.window_start_utc, utc=True)
    d_["E"] = pd.to_datetime(d_.window_end_utc, utc=True)
    d_["month"] = d_.S.dt.strftime("%Y-%m")
    d_["Esec"] = d_.E.astype("int64") // 10**9 if d_.E.dtype.kind == "M" else 0
def esec(s):
    return (s - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(seconds=1)
for d_ in (tr, pr):
    d_["Esec"] = esec(d_.E); d_["Ssec"] = esec(d_.S)
    d_["blk"] = d_.family + "-b" + (d_.Esec // (14 * 86400)).astype(str)
    d_["wd"] = d_.S.dt.day_name().str[:3]
tr["stake"] = 10.0

# ------------------------------------------------------------------ live book bands
BANDS = [("<=2c", 0.0, 0.02), ("2-5c", 0.02, 0.05), ("5-15c", 0.05, 0.15), ("15-50c", 0.15, 0.50001)]
def band_of(x):
    x = np.asarray(x, float)
    return np.select([x <= 0.02, x <= 0.05, x <= 0.15], [0, 1, 2], default=3)
bb = bk[bk.has_book.astype(str) == "True"].copy()
bb["b"] = band_of(bb.best_ask)
live = bb.groupby("b").agg(n=("spread", "size"), spread=("spread", "median"), touch=("ask_usd_touch", "median"),
                           d1=("ask_usd_1c", "median"), d2=("ask_usd_2c", "median"))
live.index = [BANDS[i][0] for i in live.index]
# Use the spec's stated live medians (computed values are reported next to them)
SPREAD = np.array([0.0015, 0.003, 0.01, 0.06])
TOUCH = np.array([2.0, 3.0, 22.0, 22.0])
DEPTH2 = np.array([28.0, 41.0, 155.0, 45.0])
MD.append("# Robustness analysis: Elon tweet-count bucket backtest\n")
MD.append("Primary spec: weekly family, as-known model, leads {0,25,50,75}, rule buy YES if p_model - entry >= 0.05, entry <= 0.50, entry >= 0.001, flat stake, fee 0.05 e (1-e) per share. "
          f"Bootstrap: {NB} reps, seed fixed, p = P(bootstrap ROI <= 0). No orders are placed by this script.\n")
MD.append("## Live book medians (data/ops_books.csv, by best_ask band) versus the spec values used\n" +
          tab([[i, int(r.n), fm(r.spread, 4), fm(SPREAD[k], 4), fm(r.touch, 1), fm(TOUCH[k], 0), fm(r.d2, 1), fm(DEPTH2[k], 0)]
               for k, (i, r) in enumerate(live.iterrows())],
              ["band", "n books", "median spread (data)", "spread used", "touch $ (data)", "touch used", "2c depth $ (data)", "2c used"]))
J["live_books"] = {i: dict(n=int(r.n), spread=float(r.spread), touch=float(r.touch), d2=float(r.d2)) for i, r in live.iterrows()}

# ------------------------------------------------------------------ trade construction from preds (for realistic fills)
def build(preds, pcol, fill, stake=10.0, leads=None):
    """fill: float slippage | 'real' (mid + half spread, stake $10 min depth2c) | 'real_touch' | 'real50' | 'real100'."""
    x = preds[preds.price.notna()].copy()
    if leads is not None: x = x[x.lead_pct.isin(leads)]
    b = band_of(x.price.values)
    if isinstance(fill, float):
        x["entry"] = x.price + fill
    else:
        x["entry"] = x.price + SPREAD[b] / 2
    x["band_mid"] = b
    x["p"] = x[pcol]
    x["edge"] = x.p - x.entry
    x = x[(x.edge >= 0.05) & (x.entry <= 0.50) & (x.entry >= 0.001)].copy()
    b = x.band_mid.values.astype(int)
    e = x.entry.values
    if isinstance(fill, float):
        S_ = np.full(len(x), 10.0); sh = S_ / e; fee = sh * 0.05 * e * (1 - e); over = np.zeros(len(x), bool)
    else:
        S_ = {"real": np.minimum(10.0, DEPTH2[b]), "real_touch": np.minimum(10.0, TOUCH[b]),
              "real50": np.full(len(x), 50.0), "real100": np.full(len(x), 100.0)}[fill]
        d = np.minimum(S_, DEPTH2[b]); r = S_ - d
        e2 = np.minimum(e + 0.02, 0.99)
        sh = d / e + r / e2
        fee = d / e * 0.05 * e * (1 - e) + r / e2 * 0.05 * e2 * (1 - e2)
        over = r > 0
    x["stake"] = S_; x["shares"] = sh; x["fee"] = fee; x["over_depth"] = over
    x["pnl"] = sh * x.outcome_yes.values - S_ - fee
    return x

FILLS = [("slip0", 0.0), ("slip0.5c", 0.005), ("slip1c", 0.01), ("real10", "real"), ("real10_touchcap", "real_touch"),
         ("real50", "real50"), ("real100", "real100")]
def trades_for(fam, var="asknown", leads=PRIMARY):
    pcol = "p_model" if var == "asknown" else "p_model_lookahead"
    P = pr[pr.family == fam]
    return {n: build(P, pcol, f, leads=leads) for n, f in FILLS}

W = trades_for("weekly"); H = trades_for("48h")
# sanity check against bt_trades
chk = {}
for s, nm in zip(SLIPS, ["slip0", "slip0.5c", "slip1c"]):
    a = tr[(tr.variant == "asknown") & (tr.family == "weekly") & (tr.slippage == s) & tr.lead_pct.isin(PRIMARY)]
    chk[nm] = (len(a), len(W[nm]), round(a.pnl.sum(), 2), round(W[nm].pnl.sum(), 2))
J["sanity_vs_bt_trades"] = {k: dict(bt_n=v[0], rebuilt_n=v[1], bt_pnl=v[2], rebuilt_pnl=v[3]) for k, v in chk.items()}
MD.append("Sanity: rebuilt slippage trades vs bt_trades.csv (weekly primary): " + "; ".join(f"{k}: n {v[0]}/{v[1]}, pnl {v[2]}/{v[3]}" for k, v in chk.items()) + "\n")
assert all(v[0] == v[1] for v in chk.values()), chk

# ------------------------------------------------------------------ headline table
EVORD = pr[pr.family == "weekly"].drop_duplicates("event_slug").sort_values(["Ssec", "Esec"]).reset_index(drop=True)
EVORD["i"] = np.arange(len(EVORD))
ev_idx = dict(zip(EVORD.event_slug, EVORD.i))
H_EVORD = pr[pr.family == "48h"].drop_duplicates("event_slug").sort_values(["Ssec", "Esec"]).reset_index(drop=True)
h_idx = dict(zip(H_EVORD.event_slug, range(len(H_EVORD))))
def add_c2(g, idx):
    g = g.copy(); g["c2"] = g.event_slug.map(idx) // 2; return g
def head(Tset, idx, label):
    rows, js = [], {}
    for nm, _ in FILLS:
        g = add_c2(Tset[nm], idx)
        r = dict(n=len(g), events=int(g.event_slug.nunique()), stake=float(g.stake.sum()), pnl=float(g.pnl.sum()), roi=float(roi(g)),
                 p_event=boot_p(g, "event_slug"), p_2event=boot_p(g, "c2"), p_14d=boot_p(g, "blk"),
                 n_over_touch10=int(0))
        js[nm] = r
        rows.append([nm, r["n"], r["events"], f"{r['stake']:.0f}", f"{r['pnl']:.0f}", pc(r["roi"]), fm(r["p_event"]), fm(r["p_2event"]), fm(r["p_14d"])])
    MD.append(f"### {label}\n" + tab(rows, ["fill", "n trades", "n events", "stake $", "PnL $", "ROI", "p event-clust", "p 2-event-clust", "p 14d-block"]))
    return js
MD.append("## Headline by fill assumption\nFills: slip0/0.5c/1c = mid + flat slippage at $10. real10 = entry mid + half live median spread of mid's band, stake min($10, median 2c depth) = $10. "
          "real10_touchcap = same but stake capped at min($10, median touch depth) (extra, stricter). real50/real100 = $50/$100 per trade: first part up to the band's median 2c depth at entry, remainder at entry + 2c. "
          "ROI = PnL / total stake. 2-event-clust = bootstrap over blocks of 2 chronologically adjacent events.\n")
J["headline_weekly_primary"] = head(W, ev_idx, "Weekly primary (as-known, leads 0/25/50/75)")
J["headline_48h_primary"] = head(H, h_idx, "48h (as-known, leads 0/25/50/75)")

# ------------------------------------------------------------------ Q1 concentration
MD.append("## Q1 Concentration (weekly primary)\n")
KMAX = 15
leavek = {"k": list(range(KMAX + 1))}
q1 = {}
lk_rows = []
for nm, _ in FILLS:
    g = W[nm]
    ev = g.groupby("event_slug").agg(pnl=("pnl", "sum"), st=("stake", "sum")).sort_values("pnl", ascending=False)
    rois = []
    for k in range(KMAX + 1):
        r_ = ev.iloc[k:]
        rois.append(r_.pnl.sum() / r_.st.sum() if len(r_) else np.nan)
    leavek[nm] = rois
    q1.setdefault(nm, {})["leave_k_roi"] = rois
lk = pd.DataFrame(leavek); lk.to_csv(f"{O}/chart_leavek.csv", index=False)
MD.append("### Leave-k-events-out ROI (drop the top-k events by PnL)\n" + tab([[k] + [pc(lk.loc[k, nm]) for nm, _ in FILLS] for k in lk.k], ["k"] + [n for n, _ in FILLS]))
# split halves
half_rows, top_rows = [], []
med = EVORD.i.median()
for nm, _ in FILLS:
    g = W[nm].copy()
    g["i"] = g.event_slug.map(ev_idx)
    n_ev = len(EVORD)
    cut = n_ev // 2
    splits = {"chron first half": g[g.i < cut], "chron second half": g[g.i >= cut], "even events": g[g.i % 2 == 0], "odd events": g[g.i % 2 == 1]}
    for sn, s in splits.items():
        r = dict(n=len(s), events=int(s.event_slug.nunique()), roi=float(roi(s)), p=boot_p(s, "event_slug"))
        q1[nm][sn] = r
        half_rows.append([nm, sn, r["n"], r["events"], pc(r["roi"]), fm(r["p"])])
    ev = g.groupby("event_slug").pnl.sum().sort_values(ascending=False)
    tot = ev.sum()
    q1[nm].update(top5_pnl=float(ev.iloc[:5].sum()), total_pnl=float(tot), top5_share=float(ev.iloc[:5].sum() / tot) if tot != 0 else np.nan,
                  events_positive=int((ev > 0).sum()), events_negative=int((ev < 0).sum()), events_traded=int(len(ev)),
                  top5=[(k, round(float(v), 1)) for k, v in ev.iloc[:5].items()])
    top_rows.append([nm, f"{tot:.0f}", f"{ev.iloc[:5].sum():.0f}", pc(q1[nm]['top5_share']), f"{(ev>0).sum()}/{len(ev)}"])
MD.append("### Split-half (chronological halves by window_start, and odd/even events)\n" + tab(half_rows, ["fill", "subset", "n", "events", "ROI", "p event-clust"]))
MD.append("### Top-5 events share of PnL and events net positive\n" + tab(top_rows, ["fill", "total PnL $", "top-5 PnL $", "top-5 share", "events net positive / traded"]))
MD.append("Top-5 events at slip0: " + ", ".join(f"{a} ({b:+.0f}$)" for a, b in q1["slip0"]["top5"]) + "\n")
# monthly
mon = []
mrows = []
for nm, _ in FILLS:
    g = W[nm]
    m = g.groupby("month").agg(n=("pnl", "size"), events=("event_slug", "nunique"), stake=("stake", "sum"), pnl=("pnl", "sum"))
    m["roi"] = m.pnl / m.stake; m["fill"] = nm
    mon.append(m.reset_index())
mon = pd.concat(mon)
mon.to_csv(f"{O}/chart_monthly.csv", index=False)
months = sorted(mon.month.unique())
MD.append("### Month-by-month PnL ($) and n trades (window_start month)\n" +
          tab([[m] + [f"{mon[(mon.fill==nm)&(mon.month==m)].pnl.sum():.0f} (n={int(mon[(mon.fill==nm)&(mon.month==m)].n.sum())})" for nm, _ in FILLS] for m in months], ["month"] + [n for n, _ in FILLS]))
q1_months_pos = {nm: int((mon[mon.fill == nm].pnl > 0).sum()) for nm, _ in FILLS}
J["Q1"] = q1; J["Q1"]["months_positive"] = q1_months_pos; J["Q1"]["n_months"] = len(months)
# cum pnl chart
cum = None
for nm, _ in FILLS:
    g = W[nm].groupby("E").pnl.sum().sort_index().cumsum().rename(nm)
    cum = g.to_frame() if cum is None else cum.join(g, how="outer")
cum = cum.sort_index().ffill().fillna(0.0); cum.index.name = "date"
cum.reset_index().assign(date=lambda z: z.date.dt.strftime("%Y-%m-%d")).to_csv(f"{O}/chart_cumpnl.csv", index=False)

# ------------------------------------------------------------------ Q2 fills / depth
MD.append("## Q2 Fills and depth (weekly primary, realistic entries)\n")
q2 = {}
rows = []
g = W["real10"]
for stake in (10, 50, 100):
    for lab, dep in (("touch", TOUCH), ("2c depth", DEPTH2)):
        b = g.band_mid.values.astype(int)
        n_ex = int((stake > dep[b]).sum())
        q2[f"stake{stake}_exceeds_{lab}"] = n_ex
        rows.append([f"${stake}", lab, n_ex, len(g), f"{100*n_ex/len(g):.0f}%"])
MD.append(tab(rows, ["stake", "vs median", "trades exceeding", "of trades", "share"]))
band_rows = []
for k, (bn, _, _) in enumerate(BANDS):
    s = g[g.band_mid == k]
    band_rows.append([bn, len(s), pc(roi(s)), f"{s.pnl.sum():.0f}", f"{TOUCH[k]:.0f}", f"{DEPTH2[k]:.0f}"])
MD.append("Trades by band of mid (real10):\n" + tab(band_rows, ["band", "n", "ROI", "PnL $", "touch $", "2c depth $"]))
q2["by_band_real10"] = {r[0]: dict(n=r[1], roi=r[2], pnl=r[3]) for r in band_rows}
J["Q2"] = q2

# ------------------------------------------------------------------ Q3 narrowness
def market_stats(fam):
    P = pr[pr.family == fam].copy()
    out = []
    for (slug, lead), g in P.groupby(["event_slug", "lead_pct"], sort=False):
        s = g.price.fillna(0).sum()
        if not (0.9 <= s <= 1.15): continue
        g = g.sort_values("bucket_lo")
        widths = (g.bucket_hi - g.bucket_lo + 1)[g.bucket_hi < 900000]
        w = widths.median()
        mid = np.where(g.bucket_hi.values >= 900000, g.bucket_lo.values + w, (g.bucket_lo.values + g.bucket_hi.values) / 2)
        fc = g.final_count.iloc[0]
        ri = int(np.where((g.bucket_lo.values <= fc) & (fc <= g.bucket_hi.values))[0][0])
        rec = dict(family=fam, event_slug=slug, lead=lead, S=g.S.iloc[0], month=g.month.iloc[0], final=fc,
                   bucket_lo=g.bucket_lo.values, bucket_hi=g.bucket_hi.values)
        for nm, col in (("mkt", "price"), ("mod", "p_model")):
            p = g[col].fillna(0).values.astype(float); p = p / p.sum()
            mean = (p * mid).sum(); sd = np.sqrt((p * (mid - mean) ** 2).sum())
            pit = p[:ri].sum() + 0.5 * p[ri]
            rec.update({f"{nm}_mean": mean, f"{nm}_sd": sd, f"{nm}_z": (fc - mean) / sd if sd > 0 else np.nan, f"{nm}_pit": pit})
        out.append(rec)
    return pd.DataFrame(out)
MS = pd.concat([market_stats("weekly"), market_stats("48h")], ignore_index=True)
all_el = pr.groupby("family").apply(lambda z: z.groupby(["event_slug", "lead_pct"]).ngroups, include_groups=False)
J["Q3_coverage"] = {f: dict(used=int((MS.family == f).sum()), total=int(all_el[f])) for f in all_el.index}
MS_ = MS[MS.lead >= 0].copy()
def narrow(g, pre):
    z_raw = g[f"{pre}_z"].dropna(); z = z_raw.clip(-5, 5); pit = g[f"{pre}_pit"].dropna()
    return dict(n=len(g), sd_z=float(z.std(ddof=0)), sd_z_raw=float(z_raw.std(ddof=0)), mean_z=float(z.mean()), outer=float(((pit < 0.1) | (pit > 0.9)).mean()),
                upper=float((pit > 0.9).mean()), lower=float((pit < 0.1).mean()), above_mean=float((g.final > g[f"{pre}_mean"]).mean()),
                sd_pit=float(pit.std(ddof=0)))
def narrow_rows(groups):
    rows, js = [], {}
    for lab, g in groups:
        if len(g) < 5: continue
        m = narrow(g, "mkt"); d = narrow(g, "mod")
        js[str(lab)] = dict(market=m, model=d)
        rows.append([lab, m["n"], fm(m["sd_z"], 2), fm(m["mean_z"], 2), f"{100*m['outer']:.0f}%", f"{100*m['lower']:.0f}%/{100*m['upper']:.0f}%", f"{100*m['above_mean']:.0f}%",
                     fm(d["sd_z"], 2), fm(d["mean_z"], 2), f"{100*d['outer']:.0f}%", f"{100*d['lower']:.0f}%/{100*d['upper']:.0f}%", f"{100*d['above_mean']:.0f}%"])
    return rows, js
NC = ["group", "n", "mkt SD(z)", "mkt mean z", "mkt outer20", "mkt PIT<.1/>.9", "mkt final>mean", "mod SD(z)", "mod mean z", "mod outer20", "mod PIT<.1/>.9", "mod final>mean"]
MD.append("## Q3 Narrowness stability\nMarket distribution = bucket prices (missing price = 0) normalised to sum 1, event x lead rows with raw price sum in [0.9, 1.15]; bucket mids (lo+hi)/2, open top = lo + bucket width; "
          "SD uses mids only (no within-bucket variance). z = (final_count - mean)/SD, clipped to +/-5 in the SD(z) and mean-z columns (raw SD in JSON; the model SD collapses to ~0 at late leads in 48h, giving absurd raw z). PIT = CDF below realised bucket + half its mass. Outer-20% share = PIT<0.1 or >0.9 (calibrated: 20%); SD(z)>1 or outer>20% = too narrow. "
          "'Model' uses p_model on the same rows. Leads 0..95 only (lead -10 excluded).\n")
J["Q3"] = {}
cov = "; ".join(f"{f}: {v['used']}/{v['total']} event-lead rows usable" for f, v in J["Q3_coverage"].items())
MD.append(f"Coverage: {cov}.\n")
for fam in ("weekly", "48h"):
    F = MS_[MS_.family == fam]
    prim = F[F.lead.isin(PRIMARY)]
    MD.append(f"### {fam}: pooled\n")
    rows, js = narrow_rows([("primary leads 0/25/50/75", prim), ("all leads 0..95", F)])
    MD.append(tab(rows, NC)); J["Q3"][f"{fam}_pooled"] = js
    rows, js = narrow_rows([(l, F[F.lead == l]) for l in sorted(F.lead.unique())])
    MD.append(f"### {fam}: per lead\n" + tab(rows, NC)); J["Q3"][f"{fam}_by_lead"] = js
    rows, js = narrow_rows([(m, prim[prim.month == m]) for m in sorted(prim.month.unique())])
    MD.append(f"### {fam}: per month (primary leads)\n" + tab(rows, NC)); J["Q3"][f"{fam}_by_month"] = js
    ev_order = {s: i for i, s in enumerate(prim.drop_duplicates("event_slug").sort_values("S").event_slug)}
    cut = len(ev_order) // 2
    prim = prim.assign(half=np.where(prim.event_slug.map(ev_order) < cut, "first half", "second half"))
    rows, js = narrow_rows([(h, prim[prim.half == h]) for h in ("first half", "second half")])
    MD.append(f"### {fam}: chronological halves (primary leads)\n" + tab(rows, NC)); J["Q3"][f"{fam}_by_half"] = js
# chart_spread
cs = MS[["family", "event_slug", "lead", "S", "final", "mkt_mean", "mkt_sd", "mkt_z", "mkt_pit", "mod_mean", "mod_sd", "mod_z", "mod_pit"]].copy()
cs["abs_err_mkt"] = (cs.final - cs.mkt_mean).abs(); cs["abs_err_mod"] = (cs.final - cs.mod_mean).abs()
cs["date"] = cs.S.dt.strftime("%Y-%m-%d"); cs = cs.drop(columns="S").rename(columns={"final": "final_count"})
cs.to_csv(f"{O}/chart_spread.csv", index=False)
# calibration chart
cal_rows = []
for fam in ("weekly", "48h"):
    P = pr[(pr.family == fam) & pr.lead_pct.isin(PRIMARY)]
    for src, col in (("market", "price"), ("model", "p_model")):
        x = P[P[col].notna() if col == "price" else P.p_model.notna()]
        x = x[x.price.notna()]
        bnames = ["<2c", "2-5c", "5-15c", "15-50c", ">50c"]
        bi = np.select([x[col] < 0.02, x[col] < 0.05, x[col] < 0.15, x[col] < 0.5], [0, 1, 2, 3], default=4)
        for k, bn in enumerate(bnames):
            s = x[bi == k]
            if len(s): cal_rows.append(dict(family=fam, source=src, band=bn, mean_pred=s[col].mean(), realised=s.outcome_yes.mean(), n=len(s)))
cal = pd.DataFrame(cal_rows); cal.to_csv(f"{O}/chart_calibration.csv", index=False)
MD.append("### Calibration by predicted-probability band (primary leads, rows with a price)\n" +
          tab([[r.family, r.source, r.band, fm(r.mean_pred, 4), fm(r.realised, 4), r.n] for r in cal.itertuples()], ["family", "source", "band", "mean pred", "realised freq", "n"]))

# ------------------------------------------------------------------ Q4 breakdowns
MD.append("## Q4 Breakdowns (weekly, as-known)\n")
mk = MS.set_index(["family", "event_slug", "lead"]).mkt_mean
def tail_side(g, fam="weekly"):
    m = [mk.get((fam, a, b), np.nan) for a, b in zip(g.event_slug, g.lead_pct)]
    m = np.array(m)
    return np.select([np.isnan(m), g.bucket_lo.values > m, g.bucket_hi.values < m], ["unknown", "upper", "lower"], default="straddles mean")
def breakdown(g, key, labs=None):
    rows, js = [], {}
    for k, s in g.groupby(key):
        if len(s) == 0: continue
        r = dict(n=len(s), events=int(s.event_slug.nunique()), roi=float(roi(s)), pnl=float(s.pnl.sum()), p=boot_p(s, "event_slug", reps=4000))
        js[str(k)] = r; rows.append([k, r["n"], r["events"], f"{r['pnl']:.0f}", pc(r["roi"]), fm(r["p"])])
    return rows, js
J["Q4"] = {}
BC = ["group", "n", "events", "PnL $", "ROI", "p event-clust"]
for nm in ("slip0", "slip1c", "real10"):
    g = W[nm].copy()
    g["tail"] = tail_side(g)
    g["priceband"] = np.array(["<2c", "2-5c", "5-15c", "15-50c"])[np.minimum(np.select([g.entry < 0.02, g.entry < 0.05, g.entry < 0.15], [0, 1, 2], default=3), 3)]
    for key, lab in (("tail", "tail side vs market mean"), ("priceband", "entry price band"), ("lead_pct", "lead"), ("wd", "window start weekday")):
        rows, js = breakdown(g, key)
        if key == "priceband":
            order = {"<2c": 0, "2-5c": 1, "5-15c": 2, "15-50c": 3}; rows.sort(key=lambda r: order[r[0]])
        MD.append(f"### {lab} ({nm}, primary leads)\n" + tab(rows, BC))
        J["Q4"][f"{nm}_{key}"] = js
# full lead grid, all leads, rebuilt from preds for slip0/1c/real10
LG = sorted(pr[pr.lead_pct >= 0].lead_pct.unique())
for nm in ("slip0", "slip1c", "real10"):
    f = dict(FILLS)[nm]
    g = build(pr[pr.family == "weekly"], "p_model", f, leads=LG)
    rows, js = breakdown(g, "lead_pct")
    rows = [[int(r[0])] + r[1:] for r in rows]
    MD.append(f"### Full lead grid 0..95 ({nm}, weekly as-known)\n" + tab(rows, BC)); J["Q4"][f"{nm}_fullgrid_lead"] = js
    gg = g.copy(); gg["tail"] = tail_side(gg)
    r2, j2 = breakdown(gg, "tail")
    MD.append(f"### Tail side, all leads 0..95 ({nm})\n" + tab(r2, BC)); J["Q4"][f"{nm}_fullgrid_tail"] = j2
# 48h tail/band/lead quick
for nm in ("slip0", "slip1c"):
    g = H[nm].copy(); g["tail"] = tail_side(g, "48h")
    rows, js = breakdown(g, "tail"); MD.append(f"### 48h tail side ({nm}, primary leads)\n" + tab(rows, BC)); J["Q4"][f"48h_{nm}_tail"] = js
    g["wd"] = g.wd
    rows, js = breakdown(g, "wd"); MD.append(f"### 48h window start weekday ({nm})\n" + tab(rows, BC)); J["Q4"][f"48h_{nm}_wd"] = js

# ------------------------------------------------------------------ Q5 asknown vs lookahead
MD.append("## Q5 As-known versus lookahead\n")
q5 = {}
rows = []
for fam in ("weekly", "48h"):
    for s in SLIPS:
        a = tr[(tr.variant == "asknown") & (tr.family == fam) & (tr.slippage == s) & tr.lead_pct.isin(PRIMARY)]
        b = tr[(tr.variant == "lookahead") & (tr.family == fam) & (tr.slippage == s) & tr.lead_pct.isin(PRIMARY)]
        ra, rb = dict(n=len(a), pnl=float(a.pnl.sum()), roi=float(roi(a)), p=boot_p(a, "event_slug")), dict(n=len(b), pnl=float(b.pnl.sum()), roi=float(roi(b)), p=boot_p(b, "event_slug"))
        q5[f"{fam}_{s}"] = dict(asknown=ra, lookahead=rb)
        rows.append([fam, s, ra["n"], f"{ra['pnl']:.0f}", pc(ra["roi"]), fm(ra["p"]), rb["n"], f"{rb['pnl']:.0f}", pc(rb["roi"]), fm(rb["p"]), f"{rb['pnl']-ra['pnl']:+.0f}"])
MD.append(tab(rows, ["family", "slip", "n as-known", "PnL as", "ROI as", "p as", "n look", "PnL look", "ROI look", "p look", "PnL diff (look - as)"]))
rows = []
q5["monthly"] = {}
for fam in ("weekly", "48h"):
    Pf = pr[(pr.family == fam) & pr.lead_pct.isin(PRIMARY)].copy()
    Pf["dK"] = Pf.K_final - Pf.K_asknown
    Pe = Pf.drop_duplicates(["event_slug", "lead_pct"])
    for m in sorted(Pe.month.unique()):
        e_ = Pe[Pe.month == m]
        row = [fam, m, e_.event_slug.nunique(), fm(e_.dK.mean(), 2), f"{100*(e_.dK>0).mean():.0f}%", fm(e_.dK.max(), 0)]
        for s in (0.0, 0.01):
            a = tr[(tr.variant == "asknown") & (tr.family == fam) & (tr.slippage == s) & tr.lead_pct.isin(PRIMARY) & (tr.month == m)]
            b = tr[(tr.variant == "lookahead") & (tr.family == fam) & (tr.slippage == s) & tr.lead_pct.isin(PRIMARY) & (tr.month == m)]
            row += [f"{a.pnl.sum():.0f}", f"{b.pnl.sum():.0f}"]
        rows.append(row)
        q5["monthly"][f"{fam}_{m}"] = dict(mean_dK=float(e_.dK.mean()), share_dK_pos=float((e_.dK > 0).mean()), max_dK=float(e_.dK.max()))
MD.append("### Per month (primary leads): mean K_final - K_asknown per event x lead, and PnL as-known vs lookahead\n" +
          tab(rows, ["family", "month", "events", "mean dK", "share dK>0", "max dK", "PnL as slip0", "PnL look slip0", "PnL as slip1c", "PnL look slip1c"]))
J["Q5"] = q5

# ------------------------------------------------------------------ Q6 independence
MD.append("## Q6 Independence (weekly primary)\n")
q6 = {}
def greedy(evs, start_i=0, exclude=()):
    """evs sorted by end; pick earliest-ending compatible windows beginning at index start_i."""
    chosen, last = [], -1
    for r in evs.iloc[start_i:].itertuples():
        if r.event_slug in exclude: continue
        if r.Ssec >= last:
            chosen.append(r.event_slug); last = r.Esec
    return chosen
ALL = EVORD.sort_values(["Esec", "Ssec"]).reset_index(drop=True)
sets = {}
for j in range(7): sets[f"greedy-all offset{j}"] = greedy(ALL, j)
sets["alt set A (greedy)"] = sets["greedy-all offset0"]
sets["alt set B (greedy on remainder)"] = greedy(ALL, 0, exclude=set(sets["greedy-all offset0"]))
for nm in ("slip0", "slip0.5c", "slip1c", "real10"):
    g = W[nm]
    tev = ALL[ALL.event_slug.isin(g.event_slug.unique())]
    trad_greedy = greedy(tev, 0)
    q6[nm] = dict(n_trades=len(g), n_events=int(g.event_slug.nunique()), n_nonoverlap_traded_events=len(trad_greedy), n_nonoverlap_all_events=len(sets["greedy-all offset0"]), p_14d_block=boot_p(g, "blk"),
                  p_event=boot_p(g, "event_slug"), subsets={})
    rows = []
    for sn, ids in list(sets.items()) + [("greedy on traded events only", trad_greedy)]:
        s = g[g.event_slug.isin(ids)]
        r = dict(n_windows=len(ids), n_trades=len(s), events_traded=int(s.event_slug.nunique()), pnl=float(s.pnl.sum()), roi=float(roi(s)), p=boot_p(s, "event_slug"))
        q6[nm]["subsets"][sn] = r
        rows.append([sn, r["n_windows"], r["n_trades"], r["events_traded"], f"{r['pnl']:.0f}", pc(r["roi"]), fm(r["p"])])
    rr = [v["roi"] for k, v in q6[nm]["subsets"].items() if k.startswith("greedy-all")]
    q6[nm]["offset_roi_mean"] = float(np.mean(rr)); q6[nm]["offset_roi_min"] = float(np.min(rr)); q6[nm]["offset_roi_max"] = float(np.max(rr))
    MD.append(f"### {nm}: trades {len(g)}, events with trades {g.event_slug.nunique()}, non-overlapping windows (greedy) among traded events {len(trad_greedy)}, among all {len(ALL)} weekly events {len(sets['greedy-all offset0'])}; p 14d-block {fm(q6[nm]['p_14d_block'])}\n" +
              tab(rows, ["independent subset", "windows", "trades", "events traded", "PnL $", "ROI", "p (event boot)"]))
J["Q6"] = q6


hw = J["headline_weekly_primary"]
tk = ["## Takeaways (one line per question)\n",
 f"- Q1: Edge is concentrated: dropping the top 5 events takes slip0 ROI from {pc(q1['slip0']['leave_k_roi'][0])} to {pc(q1['slip0']['leave_k_roi'][5])} (0.5c: {pc(q1['slip0.5c']['leave_k_roi'][5])}); top-5 events = {pc(q1['slip0']['top5_share'])} of slip0 PnL; only {q1['slip0']['events_positive']}/{q1['slip0']['events_traded']} events net positive; {q1_months_pos['slip0']}/{len(months)} months positive.",
 f"- Q2: Realistic fill (mid + half spread, $10) keeps ROI {pc(hw['real10']['roi'])} (p={fm(hw['real10']['p_event'])}); $50 {pc(hw['real50']['roi'])} (p={fm(hw['real50']['p_event'])}); $100 {pc(hw['real100']['roi'])} (p={fm(hw['real100']['p_event'])}). $10 exceeds median touch depth on {q2['stake10_exceeds_touch']}/{hw['real10']['n']} trades, never the 2c depth; $50/$100 exceed 2c depth on {q2['stake50_exceeds_2c depth']}.",
 "- Q3: Weekly market is borderline too narrow at primary leads (SD(z) ~1.03, outer-20% share ~25% vs 20%), driven by leads 0-70 and Dec/Feb/May months; late leads (85+) are too wide. 48h market is not too narrow (SD(z) ~0.86, outer ~13%). Model is not too narrow (outer 11-14%). Directional: no clear upper/lower asymmetry overall; Dec 2025 realised was well above, Apr 2026 below.",
 "- Q4: Profit comes from upper-tail buckets (bucket entirely above market mean), mid prices 2-15c, and lead 50-55; <2c and lead 0 vanish at 1c slippage; leads 90-95 lose. Fri and Tue windows are both positive at slip0.",
 "- Q5: As-known vs lookahead differ by only ~$10-20 PnL; late-import K gaps are tiny (mean dK <0.35 posts) except Oct 2026 (one event).",
 f"- Q6: 384 trades from 86 overlapping events collapse to ~44 independent weekly windows; independent Tue-only/Fri-only subsets give ROI {pc(q6['slip0']['subsets']['greedy-all offset0']['roi'])}/{pc(q6['slip0']['subsets']['greedy-all offset1']['roi'])} (p {fm(q6['slip0']['subsets']['greedy-all offset0']['p'])}/{fm(q6['slip0']['subsets']['greedy-all offset1']['p'])}) at slip0, and p 0.15-0.5 at 0.5c-1c.\n"]
MD[2:2] = tk
# ------------------------------------------------------------------ write
open(f"{O}/robustness.md", "w").write("\n".join(MD))
def clean(o):
    if isinstance(o, dict): return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [clean(v) for v in o]
    if isinstance(o, (np.floating, float)): return None if np.isnan(o) else float(o)
    if isinstance(o, (np.integer,)): return int(o)
    return o
json.dump(clean(J), open(f"{O}/robustness.json", "w"), indent=1)
print("done")
