#!/usr/bin/env python3
"""Q8/Q9: how fast do Elon tweet-count markets reprice after bursts / quiet spells. Offline only; never places orders."""
import os, numpy as np, pandas as pd
BASE = os.path.dirname(os.path.abspath(__file__)); D, O = f"{BASE}/data", f"{BASE}/out"
rng = np.random.default_rng(7)
TAUS = [5, 15, 30, 60, 120, 240]
MAXT = 240; PRE = 60
def to_sec(x): return ((pd.to_datetime(x, utc=True) - pd.Timestamp("1970-01-01", tz="UTC")) // pd.Timedelta(seconds=1)).astype("int64")

P = pd.read_csv(f"{D}/posts_elonmusk.csv", usecols=["id", "createdAt", "importedAt"]).drop_duplicates("id")
P["c"] = to_sec(P.createdAt); P["i"] = to_sec(P.importedAt); P = P.sort_values("c").reset_index(drop=True)
PC, PI = P.c.values, P.i.values; PSLOT = (PC // 3600) % 168
def lam_vec(t):  # same definition as backtest.py: trailing 4 weeks, hour-of-week rate, import-censored
    lo = np.searchsorted(PC, t - 28 * 86400, "left"); hi = np.searchsorted(PC, t, "left")
    ok = (PC[lo:hi] < t - 86400) | (PI[lo:hi] <= t)
    return np.bincount(PSLOT[lo:hi][ok], minlength=168) / 4.0

ev = pd.read_csv(f"{D}/events.csv", dtype={"yes_token": str})
ev = ev[(ev.window_start_utc >= "2025-12-01") & ev.event_closed & ~ev.event_slug.str.startswith("arch-")
        & ev.bucket_lo.notna() & ev.family.isin(["weekly", "48h"])].copy()
ev["S"] = to_sec(ev.window_start_utc); ev["E"] = to_sec(ev.window_end_utc)

def build(slug, g):
    S, E = int(g.S.iloc[0]), int(g.E.iloc[0]); n = (E - S) // 60
    g = g.sort_values("bucket_lo"); lo = g.bucket_lo.values.astype(float); hi = g.bucket_hi.values.astype(float)
    w = np.median((hi - lo + 1)[hi < 1e5]); mid = np.where(hi > 1e5, lo + w, (lo + hi) / 2)
    pr = pd.read_parquet(f"{D}/raw/prices/{slug}.parquet"); grid = np.arange(S, E, 60)
    cols = []
    for tk in g.yes_token:
        x = pr[pr.token == tk]
        s = pd.Series(x.p.values, index=x.t.values // 60 * 60)
        s = s[~s.index.duplicated(keep="last")].sort_index()
        full = s.reindex(np.union1d(s.index.values, grid)).ffill()
        # never forward-fill more than 30 min: mask where last update is > 30 min old
        lastu = pd.Series(np.where(full.index.isin(s.index), full.index, np.nan), index=full.index).ffill()
        full[(full.index - lastu) > 1800] = np.nan
        cols.append(full.reindex(grid).values)
    raw = np.array(cols).T                      # n x B
    present = ~np.isnan(raw); tot = np.nansum(raw, 1)
    valid = (present.sum(1) >= 0.8 * len(mid)) & (tot > 0.8) & (tot < 1.25)
    pn = np.where(present, raw, 0) / np.where(tot > 0, tot, 1)[:, None]
    M = np.where(valid, pn @ mid, np.nan)
    # K (importedAt, and createdAt variant) and mu, per minute
    a = np.searchsorted(PC, S, "left"); b = np.searchsorted(PC, E, "left")
    imp = np.sort(PI[a:b]); cre = np.sort(PC[a:b])
    K = np.searchsorted(imp, grid, "right"); Kc = np.searchsorted(cre, grid, "right")
    hours = np.arange(S // 3600 * 3600, E, 3600); lam_h = {h: lam_vec(h) for h in hours}
    # remaining expected posts from t: sum over hour slots of lam*overlap, using lam fixed at the hour containing t
    hl = np.array([lam_h[h][(h // 3600) % 168] for h in hours])           # expected posts per hour slot
    ov = np.array([max(0, min(h + 3600, E) - max(h, S)) / 3600 for h in hours])
    cum = np.concatenate([[0], np.cumsum(hl * ov)])
    mu = np.zeros(n)
    for j, t in enumerate(grid):
        h = t // 3600 * 3600; k = int((h - hours[0]) // 3600)
        lam_now = lam_h[h]; rem_in_hr = (min(h + 3600, E) - t) / 3600
        mu[j] = lam_now[(h // 3600) % 168] * rem_in_hr + (cum[-1] - cum[k + 1])
        # later hours use the lam at the time of evaluation (hour start) for fidelity with backtest
        later = sum(lam_now[(hh // 3600) % 168] * ov[m] for m, hh in enumerate(hours) if hh > h)
        mu[j] = lam_now[(h // 3600) % 168] * rem_in_hr + later
    F = K + mu
    exp_hr = np.array([lam_h[t // 3600 * 3600][(t // 3600) % 168] for t in grid])
    # rolling 60-min import count (posts with importedAt in (t-3600, t])
    c60 = K - np.concatenate([np.zeros(min(60, n)), K[:-60]])[:n] if n > 60 else K
    # last import time -> zero-post duration
    lastimp = np.searchsorted(imp, grid, "right")
    since = np.zeros(n)
    for j, t in enumerate(grid):
        k = lastimp[j]; since[j] = (t - imp[k - 1]) / 60 if k > 0 else (t - S) / 60
    # expected count over trailing 4h
    e4 = np.convolve(exp_hr, np.ones(240), "full")[:n] / 60
    return dict(slug=slug, S=S, E=E, fam=g.family.iloc[0], n=n, grid=grid, M=M, K=K, Kc=Kc, mu=mu, F=F,
                exp_hr=exp_hr, c60=c60, since=since, e4=e4, raw=raw, mid=mid, lo=lo, hi=hi, valid=valid)

if __name__ == "__main__":
    EV = []
    for s, g in ev.groupby("event_slug"):
        EV.append(build(s, g))
    print("events", len(EV), "mean valid-minute share", np.mean([e["valid"].mean() for e in EV]).round(3))

    def at(a, i): return a[i] if 0 <= i < len(a) else np.nan
    def response(e, j0, kind):
        """curves over rel minute -PRE..MAXT; c(rel) = (M(t0+rel)-M(t0-PRE)) / (F(t0)-F(t0-PRE))"""
        M, F = e["M"], e["F"]
        if j0 - PRE < 0: return None
        mb, fb, m0, f0 = M[j0 - PRE], F[j0 - PRE], M[j0], F[j0]
        if np.isnan(mb) or np.isnan(m0): return None
        dF = f0 - fb
        r = dict(slug=e["slug"], j0=j0, t0=int(e["grid"][j0]), kind=kind, dF=dF, dFpre=dF, m0=m0, mb=mb, M0=m0)
        for tau in TAUS:
            jt = j0 + tau
            r[f"dM{tau}"] = M[jt] - m0 if jt < e["n"] else np.nan
            r[f"dF{tau}"] = F[jt] - f0 if jt < e["n"] else np.nan
        rel = np.arange(-PRE, MAXT + 1)
        idx = j0 + rel; ok = (idx >= 0) & (idx < e["n"])
        curve = np.full(len(rel), np.nan); curve[ok] = M[idx[ok]] - mb
        r["curve"] = curve
        return r

    bursts, quiets, placebos = [], [], []
    for e in EV:
        n = e["n"]
        # ---- bursts: rolling-60 >= max(8, 3 x expected hourly), first crossing, decluster 240 min
        thr = np.maximum(8, 3 * e["exp_hr"])
        hit = np.where((e["c60"] >= thr))[0]
        last = -10**9; burst_j = []
        for j in hit:
            if j - last >= 240 and j >= PRE: burst_j.append(j); last = j
        for j in burst_j:
            r = response(e, j, "burst"); 
            if r: bursts.append(r)
        # ---- quiet spells: >= 4h zero import posts with expected 4h count >= 4; trigger when 240 min reached
        qh = np.where((e["since"] >= 240) & (e["e4"] >= 4))[0]; last = -10**9
        for j in qh:
            if j - last >= 480:
                last = j; r = response(e, j, "quiet")
                if r: quiets.append(r)
        # ---- placebo pool: no burst/quiet condition within [-120,+0], any time inside window
        bj = set(burst_j)
        near = np.zeros(n, bool)
        for j in list(bj) + [q["j0"] for q in quiets if q["slug"] == e["slug"]]:
            near[max(0, j - 240): j + 241] = True
        cand = np.where((~near) & (e["c60"] < 2 * np.maximum(1, e["exp_hr"])) & (e["since"] < 180))[0]
        cand = cand[(cand >= PRE) & (cand < n - MAXT) & ~np.isnan(e["M"][cand])]
        if len(cand):
            for j in rng.choice(cand, size=min(len(cand), 40), replace=False):
                r = response(e, int(j), "placebo")
                if r: placebos.append(r)
    print("bursts", len(bursts), "quiet", len(quiets), "placebo", len(placebos))

    def frame(lst): 
        d = pd.DataFrame([{k: v for k, v in r.items() if k != "curve"} for r in lst])
        d["month"] = pd.to_datetime(d.t0, unit="s").dt.strftime("%Y-%m")
        return d
    dB, dQ, dP = frame(bursts), frame(quiets), frame(placebos)

    MINSURP = 3.0   # "should-move" must be >= 3 posts of surprise (burst: surplus over expectation) for fraction stats
    def curves(lst, df, cond):
        sel = [i for i in range(len(lst)) if cond(df.iloc[i])]
        C = np.array([lst[i]["curve"] / lst[i]["dF"] for i in sel])   # fraction of the baseline-to-t0 should-move
        return C, sel
    def halflife(curve):  # first rel minute where curve>=0.5 (rel to t0), 'nan' if never within MAXT
        rel = np.arange(-PRE, MAXT + 1); ok = np.where(curve >= 0.5)[0]
        return rel[ok[0]] if len(ok) else np.nan
    def summarize(lst, df, tag):
        out = {}
        sel = df.index[df.dF.abs() >= MINSURP]
        # literal spec: dM(tau)/dF(tau) from t0 (should-move over same horizon)
        for tau in TAUS:
            x = df.loc[sel]; ok = x[f"dF{tau}"].abs() >= 1.0
            ratio = (x.loc[ok, f"dM{tau}"] * np.sign(x.loc[ok, "dF"])) / (x.loc[ok, f"dF{tau}"] * np.sign(x.loc[ok, "dF"]))
            out[f"lit_ratio_{tau}"] = ratio.median()
            out[f"dM_signed_{tau}"] = (x[f"dM{tau}"] * np.sign(x.dF)).mean()
            out[f"dF_signed_{tau}"] = (x[f"dF{tau}"] * np.sign(x.dF)).mean()
        C = np.array([lst[i]["curve"] / lst[i]["dF"] for i in sel])
        rel = np.arange(-PRE, MAXT + 1)
        out["curve_median"] = np.nanmedian(C, 0); out["curve_mean"] = np.nanmean(np.clip(C, -3, 3), 0)
        out["hl_perburst"] = np.nanmedian([halflife(c) for c in C]); out["n_used"] = len(sel)
        out["hl_curve"] = halflife(out["curve_median"])
        for tau in [0, 5, 15, 30, 60, 120, 240]:
            out[f"frac_{tau}"] = np.nanmedian(C[:, PRE + tau])
        return out
    sB, sQ = summarize(bursts, dB, "burst"), summarize(quiets, dQ, "quiet")
    # placebo: same operator, threshold on |dF|>=MINSURP, so it is a "like-sized fundamental move" at a random time
    sP = summarize(placebos, dP, "placebo") if (dP.dF.abs() >= MINSURP).sum() > 20 else None
    # placebo, unconditional: |dM| growth vs bursts in raw units
    rawcmp = {k: (dB.loc[dB.dF.abs() >= MINSURP, f"dM{k}"].abs().mean(), dP[f"dM{k}"].abs().mean()) for k in [15, 60, 240]}

    # ---------- chart csv ----------
    rel = np.arange(-PRE, MAXT + 1)
    ch = pd.DataFrame({"tau_min": rel, "burst_mean_frac": sB["curve_mean"], "burst_median_frac": sB["curve_median"],
                       "quiet_median_frac": sQ["curve_median"],
                       "placebo_median_frac": sP["curve_median"] if sP else np.nan,
                       "placebo_mean_frac": sP["curve_mean"] if sP else np.nan})
    ch.to_csv(f"{O}/chart_repricing.csv", index=False)

    # ---------- profit test ----------
    def rawprice(e, j): return e["raw"][j] if 0 <= j < e["n"] else None
    emap = {e["slug"]: e for e in EV}
    def profit(lst, df, direction, minp=0.0):
        cost = pnl = 0.0; rets = []
        for r in lst:
            if abs(r["dF"]) < MINSURP or np.sign(r["dF"]) != direction: continue
            e = emap[r["slug"]]; j0 = r["j0"]
            p5, p60, pb = rawprice(e, j0 + 5), rawprice(e, j0 + 60), rawprice(e, j0 - PRE)
            if p5 is None or p60 is None or pb is None or np.isnan(pb).all(): continue
            okb = ~np.isnan(pb); q = pb[okb] / pb[okb].sum(); cdf = np.cumsum(q)
            med_i = np.where(okb)[0][np.searchsorted(cdf, 0.5)]          # pre-burst median bucket
            idx = np.arange(len(pb))
            sel = (idx > med_i) if direction > 0 else (idx < med_i)
            sel &= ~np.isnan(p5) & ~np.isnan(p60); sel &= (p5 + 0.005 >= minp)
            if not sel.any(): continue
            c = p5[sel] + 0.005; g = p60[sel] - c        # buy at mid+0.5c, mark at mid (conservative: no exit cost)
            cost += c.sum(); pnl += g.sum(); rets.append(g.sum() / c.sum())
        return dict(n=len(rets), agg_return=pnl / cost if cost else np.nan, mean_return=np.mean(rets) if rets else np.nan,
                    median_return=np.median(rets) if rets else np.nan, win=np.mean(np.array(rets) > 0) if rets else np.nan)
    prof = {}
    prof["burst_up_all"] = profit(bursts, dB, +1)
    prof["burst_up_p>=0.02"] = profit(bursts, dB, +1, 0.02)
    # placebo: same rule at random times with positive should-move
    prof["placebo_up_all"] = profit(placebos, dP, +1)
    prof["placebo_up_p>=0.02"] = profit(placebos, dP, +1, 0.02)
    prof["quiet_down_all"] = profit(quiets, dQ, -1)
    prof["quiet_down_p>=0.02"] = profit(quiets, dQ, -1, 0.02)
    # exit-cost sensitivity: also pay 0.5c on exit
    # ---------- by month / thirds ----------
    def grp_stats(lst, df, sel_idx):
        sub = df.loc[sel_idx]; sub = sub[sub.dF.abs() >= MINSURP]
        if len(sub) < 3: return dict(n_bursts=len(sub))
        C = np.array([lst[i]["curve"] / lst[i]["dF"] for i in sub.index])
        d = dict(n_bursts=len(sub))
        for tau in (15, 60):
            d[f"frac_from_base_{tau}"] = np.nanmedian(C[:, PRE + tau])
            x = sub[sub[f"dF{tau}"].abs() >= 1.0]
            d[f"lit_ratio_{tau}"] = ((x[f"dM{tau}"] * np.sign(x.dF)) / (x[f"dF{tau}"] * np.sign(x.dF))).median() if len(x) else np.nan
        d["frac_at_t0"] = np.nanmedian(C[:, PRE])
        d["halflife_perburst_med"] = np.nanmedian([halflife(c) for c in C])
        d["halflife_of_median_curve"] = halflife(np.nanmedian(C, 0))
        return d
    # pool bursts + quiet spells for power in monthly splits, and report bursts-only too
    allq = pd.concat([dB.assign(src="burst"), dQ.assign(src="quiet")], ignore_index=True)
    allq_curves = bursts + quiets
    t_sorted = allq.t0.sort_values().values; cut = np.quantile(t_sorted, [1/3, 2/3])
    allq["third"] = np.where(allq.t0 <= cut[0], "T1", np.where(allq.t0 <= cut[1], "T2", "T3"))
    rows = []
    for m, g in allq.groupby("month"):
        for src, gg in [("burst+quiet", g), ("burst", g[g.src == "burst"])]:
            rows.append(dict(group=m, kind="month", src=src, **grp_stats(allq_curves, allq, gg.index)))
    for t, g in allq.groupby("third"):
        for src, gg in [("burst+quiet", g), ("burst", g[g.src == "burst"])]:
            rows.append(dict(group=t, kind="third", src=src, **grp_stats(allq_curves, allq, gg.index)))
    # cross-correlation of minute-level changes, lags -30..+120 (positive lag = M changes AFTER K)
    LAGS = np.arange(-30, 121)
    def xc(e, Kkey):
        M = e["M"]; K = e[Kkey].astype(float)
        dM = np.diff(M); dK = np.diff(K); ok = ~np.isnan(dM)
        out = np.full(len(LAGS), np.nan)
        # restrict to valid stretches; standardise globally
        dMv = np.where(ok, dM, 0.0); m = ok.copy()
        if m.sum() < 500: return out
        # winsorise dM (tick noise / stale jumps)
        sd = dMv[m].std(); dMv = np.clip(dMv, -5 * sd, 5 * sd)
        for i, L in enumerate(LAGS):
            if L >= 0: a, b, mm = dMv[L:], dK[:len(dK) - L], m[L:] & m[:len(m) - L] if False else m[L:]
            else: a, b, mm = dMv[:L], dK[-L:], m[:L]
            if mm.sum() > 100 and a[mm].std() > 0 and b[mm].std() > 0: out[i] = np.corrcoef(a[mm], b[mm])[0, 1]
        return out
    xrows = []; xcurves = {}
    for key in ["K", "Kc"]:
        res = []
        for e in EV:
            res.append((pd.to_datetime(e["S"], unit="s").strftime("%Y-%m"), xc(e, key)))
        xcurves[key] = res
    xtab = []
    for key in ["K", "Kc"]:
        df_ = pd.DataFrame({m: v for m, v in []}) 
        bym = {}
        for m, v in xcurves[key]: bym.setdefault(m, []).append(v)
        allv = np.array([v for _, v in xcurves[key]])
        xtab.append(dict(month="ALL", key=key, n_events=len(allv), peak_lag=LAGS[np.nanargmax(np.nanmean(allv, 0))], peak_corr=np.nanmax(np.nanmean(allv, 0))))
        for m, vs in sorted(bym.items()):
            mv = np.nanmean(np.array(vs), 0)
            xtab.append(dict(month=m, key=key, n_events=len(vs), peak_lag=LAGS[np.nanargmax(mv)], peak_corr=np.nanmax(mv)))
    xtab = pd.DataFrame(xtab)
    bm = pd.DataFrame(rows)
    # attach xcorr peak by month
    for key, nm in [("K", "xcorr_peak_lag_importedAt"), ("Kc", "xcorr_peak_lag_createdAt")]:
        mp = xtab[xtab.key == key].set_index("month").peak_lag
        bm[nm] = bm.apply(lambda r: mp.get(r.group) if r.kind == "month" else np.nan, axis=1)
    bm.round(3).to_csv(f"{O}/repricing_by_month.csv", index=False)
    xtab.round(4).to_csv(f"{O}/repricing_xcorr_by_month.csv", index=False)
    allK = np.nanmean(np.array([v for _, v in xcurves["K"]]), 0)
    allKc = np.nanmean(np.array([v for _, v in xcurves["Kc"]]), 0)

    # ---------- markdown ----------
    f = lambda x, d=2: "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:.{d}f}"
    L = []
    L += ["# Repricing speed of Elon tweet-count markets after bursts (offline analysis, no orders)", ""]
    L += [f"Scope: {len(EV)} closed weekly/48h events from Dec 2025 (price data per bucket, forward-filled at most 30 min). "
          f"Valid-M minutes: {np.mean([e['valid'].mean() for e in EV])*100:.0f}% (a minute needs >=80% of buckets priced and a raw price sum within 0.8-1.25).", "",
          "## Definitions", "",
          "- M(t): market-implied mean final count (normalised bucket prices x bucket mids; open top bucket mid = lo + typical width).",
          "- F(t) = K(t) + mu(t): K = posts in window with importedAt <= t; mu = trailing-4-week hour-of-week rate (same function as backtest.py, re-implemented because importing it runs the full backtest).",
          "- Burst: rolling 60-min import count >= max(8, 3 x expected hourly rate); first crossing, de-clustered by 240 min. Trigger time t0 = the minute the counter sees the burst.",
          "- Quiet spell: >= 240 min with no imported post while the expected 4h count >= 4. t0 = minute the 4h mark is reached.",
          f"- Should-move: dF = F(t0) - F(t0-60) (the surprise the burst adds relative to the expected flow). Only events with |dF| >= {MINSURP:.0f} posts are used for fractions. "
          "Response fraction c(rel) = (M(t0+rel) - M(t0-60)) / dF, so 0 = nothing repriced, 1 = fully repriced; rel is measured from the counter-trigger time t0 (negative rel = before the counter saw it).",
          "- Half-life = first rel minute at which c >= 0.5 (negative = the market got there before the counter trigger).", ""]
    L += [f"## Q8: counts", "", f"- Bursts detected: **{len(dB)}** ({(dB.dF.abs()>=MINSURP).sum()} with |dF|>={MINSURP:.0f}); quiet spells: **{len(dQ)}** ({(dQ.dF.abs()>=MINSURP).sum()} used); placebo times: {len(dP)} ({(dP.dF.abs()>=MINSURP).sum()} with |dF|>={MINSURP:.0f}).", ""]
    L += ["### Fraction of the should-move already in the price (median across bursts)", "",
          "| rel min from t0 | burst | quiet spell | placebo (|dF|>=3) |", "|---|---|---|---|"]
    for t in [0, 5, 15, 30, 60, 120, 240]:
        L.append(f"| {t} | {f(sB[f'frac_{t}'])} | {f(sQ[f'frac_{t}'])} | {f(sP[f'frac_{t}']) if sP else 'n/a'} |")
    L += ["", f"Half-life (median per-event first crossing of 0.5, rel to t0): burst **{f(sB['hl_perburst'],0)} min**, quiet **{f(sQ['hl_perburst'],0)} min**"
          f"{', placebo ' + f(sP['hl_perburst'],0) + ' min' if sP else ''}. Half-life of the median curve: burst {f(sB['hl_curve'],0)}, quiet {f(sQ['hl_curve'],0)}.", ""]
    L += ["### Literal spec: median of dM(tau)/dF(tau) with both measured from t0", "",
          "(dF(tau) = F(t0+tau)-F(t0) is small and noisy because the burst is already in K at t0, so this ratio is unstable; pairs with |dF(tau)|<1 post dropped. Signs normalised so the burst direction is positive.)", "",
          "| tau | median dM/dF burst | mean signed dM burst | mean signed dF burst | median dM/dF quiet | mean signed dM quiet |", "|---|---|---|---|---|---|"]
    for t in TAUS:
        L.append(f"| {t} | {f(sB[f'lit_ratio_{t}'])} | {f(sB[f'dM_signed_{t}'])} | {f(sB[f'dF_signed_{t}'])} | {f(sQ[f'lit_ratio_{t}'])} | {f(sQ[f'dM_signed_{t}'])} |")
    L += ["", "Raw |dM| sanity (mean absolute change in M, posts) bursts vs placebo: " + "; ".join(f"tau {k}: {f(a)} vs {f(b)}" for k, (a, b) in rawcmp.items()), ""]
    L += ["### Is there a profitable lag?", "",
          "Rule: at t0+5 buy every bucket above the pre-burst (t0-60) market median bucket at raw mid + 0.5c, mark at mid at t0+60, equal shares, no fees, no exit spread. Quiet spells: mirror (buy buckets below the median). Returns are on cost.", "",
          "| set | n | aggregate return | mean per-trade | median | win rate |", "|---|---|---|---|---|---|"]
    for k, v in prof.items(): L.append(f"| {k} | {v['n']} | {f(v['agg_return']*100 if v['agg_return']==v['agg_return'] else np.nan,1)}% | {f(v['mean_return']*100,1)}% | {f(v['median_return']*100,1)}% | {f(v['win']*100,0)}% |")
    L += ["", "## Q9: does the lag shrink?", "", "Bursts and quiet spells pooled (power), plus bursts only. Full table: out/repricing_by_month.csv. 'frac' = median response fraction from the baseline; 'lit' = literal dM/dF from t0.", ""]
    L += ["| group | src | n | frac@t0 | frac@15 | frac@60 | lit15 | lit60 | half-life (per-event, min) | xcorr peak lag (importedAt) |", "|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in bm.iterrows():
        L.append(f"| {r.group} | {r.src} | {r.n_bursts} | {f(r.get('frac_at_t0'))} | {f(r.get('frac_from_base_15'))} | {f(r.get('frac_from_base_60'))} | {f(r.get('lit_ratio_15'))} | {f(r.get('lit_ratio_60'))} | {f(r.get('halflife_perburst_med'),0)} | {f(r.get('xcorr_peak_lag_importedAt'),0) if r.kind=='month' else ''} |")
    L += ["", "### Price-count cross-correlation (minute changes of M vs minute changes of K; lag>0 = M moves after K)", "",
          "| month | n events | peak lag, K by importedAt (min) | corr | peak lag, K by createdAt (min) | corr |", "|---|---|---|---|---|---|"]
    xa, xb = xtab[xtab.key == "K"].set_index("month"), xtab[xtab.key == "Kc"].set_index("month")
    for m in xa.index: L.append(f"| {m} | {int(xa.loc[m,'n_events'])} | {int(xa.loc[m,'peak_lag'])} | {f(xa.loc[m,'peak_corr'],3)} | {int(xb.loc[m,'peak_lag'])} | {f(xb.loc[m,'peak_corr'],3)} |")
    L += ["", "Caveats: minute-level M changes are dominated by thin-book noise and stale ticks (hence small correlations); few events per month in some months; bursts are clustered in time and overlap across events of the same period (weekly and 48h windows cover the same posts), so the effective sample is smaller than n; the placebo is conditioned on a like-sized fundamental surprise so it is a like-for-like noise reference.", ""]
    open(f"{O}/repricing.md", "w").write("\n".join(L))
    print("\n".join(L))
