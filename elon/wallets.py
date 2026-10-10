"""Wallet profiling of Polymarket Elon tweet-count markets. Offline; reads data/raw/trades."""
import glob, os, time, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
from common import get, DATA  # noqa (used only for optional positions check)

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "out")
CHEAP = 0.15
rng = np.random.default_rng(7)

ev = pd.read_csv(os.path.join(ROOT, "data/events.csv"), dtype={"yes_token": str, "no_token": str})
ev = ev[ev.outcome_yes.isin([0, 1])].copy()
EPOCH = pd.Timestamp("1970-01-01", tz="UTC")
ev["ws"] = (pd.to_datetime(ev.window_start_utc, utc=True) - EPOCH).dt.total_seconds()
ev["we"] = (pd.to_datetime(ev.window_end_utc, utc=True) - EPOCH).dt.total_seconds()
meta = pd.concat([
    ev.assign(token=ev.yes_token, payout=ev.outcome_yes, is_yes=True),
    ev.assign(token=ev.no_token, payout=1 - ev.outcome_yes, is_yes=False)
])[["token", "event_slug", "payout", "is_yes", "bucket_lo", "bucket_hi", "ws", "we", "family"]]

files = [f for f in glob.glob(os.path.join(ROOT, "data/raw/trades/*.parquet")) if time.time() - os.path.getmtime(f) > 120]
def load(f):  # per file, to keep memory bounded on the full 21M-row tape
    x = pd.read_parquet(f, columns=["proxyWallet", "side", "asset", "size", "price", "timestamp", "pseudonym", "eventSlug"])
    x["asset"] = x.asset.astype(str)
    x = x.merge(meta, left_on="asset", right_on="token", how="inner")
    x = x[x.eventSlug == x.event_slug].drop(columns=["asset", "token", "eventSlug"])
    for c in ["proxyWallet", "side", "pseudonym", "event_slug", "family"]:
        x[c] = x[c].astype("category")
    for c in ["size", "price", "payout", "bucket_lo", "bucket_hi"]:
        x[c] = x[c].astype("float32")
    return x
parts = [load(f) for f in files]
d = pd.concat(parts, ignore_index=True); del parts
for c in ["proxyWallet", "side", "pseudonym", "event_slug", "family"]:
    d[c] = d[c].astype(str).astype("category")
n_files, n_rows = len(files), len(d)
d["sgn"] = np.where(d.side == "BUY", 1.0, -1.0)
d["pnl"] = d.sgn * d["size"].astype(float) * (d.payout.astype(float) - d.price.astype(float))
d["notional"] = d["size"].astype(float) * d.price.astype(float)
d["cheap"] = d.price < CHEAP
d["lead"] = 100 * (d.we - d.timestamp) / (d.we - d.ws).clip(lower=1)   # % of window remaining at trade
d["buy"] = d.side == "BUY"
pseud = d.drop_duplicates("proxyWallet").set_index("proxyWallet").pseudonym.astype(str); pseud.index = pseud.index.astype(str)

# upper-tail YES: YES bucket whose lo is above the event's most-traded YES bucket
yv = d[d.is_yes].groupby(["event_slug", "bucket_lo"], observed=True).notional.sum().reset_index()
mode_lo = yv.loc[yv.groupby("event_slug", observed=True).notional.idxmax()].set_index("event_slug").bucket_lo
d["upper_yes"] = d.is_yes & d.cheap & (d.bucket_lo > d.event_slug.map(mode_lo))

# per wallet x event
d["lw"] = d.lead * d.notional
we = d.groupby(["proxyWallet", "event_slug"], observed=True).agg(
    pnl=("pnl", "sum"), notional=("notional", "sum"), n_trades=("size", "size"),
    cheap_share=("cheap", "mean"), med_size=("size", "median"), lw=("lw", "sum"),
    n_buy=("buy", "sum")).reset_index()
we["proxyWallet"] = we.proxyWallet.astype(str); we["event_slug"] = we.event_slug.astype(str)
we["lead_pct"] = we.lw / we.notional.replace(0, np.nan)
we.drop(columns="lw").to_csv(os.path.join(OUT, "wallets_by_event.csv.gz"), index=False)

def boot_p(x, B=2000):
    """cluster (event-level) bootstrap one-sided p for mean>0 and mean<0."""
    n = len(x)
    if n < 3: return np.nan, np.nan
    m = x[rng.integers(0, n, (B, n))].mean(1)
    return (m <= 0).mean(), (m >= 0).mean()

g = we.groupby("proxyWallet")
w = g.agg(n_events=("event_slug", "nunique"), notional=("notional", "sum"), pnl=("pnl", "sum"),
          n_trades=("n_trades", "sum"), n_buy=("n_buy", "sum"), pct_profitable=("pnl", lambda s: (s > 0).mean())).reset_index()
w["roi"] = w.pnl / w.notional.replace(0, np.nan)
w["n_sell"] = w.n_trades - w.n_buy
cs = d.groupby("proxyWallet", observed=True).agg(cheap_share=("cheap", "mean"), med_size=("size", "median"),
                                  lw=("lw", "sum"), nn=("notional", "sum")).reset_index()
cs["avg_lead"] = cs.lw / cs.nn.replace(0, np.nan)
cs["proxyWallet"] = cs.proxyWallet.astype(str)
w = w.merge(cs[["proxyWallet", "cheap_share", "med_size", "avg_lead"]], on="proxyWallet")
w["pseudonym"] = w.proxyWallet.map(pseud)
w["addr"] = w.proxyWallet.str[:6] + ".." + w.proxyWallet.str[-4:]
pe = {k: v.pnl.values for k, v in we.groupby("proxyWallet")}
t, pw, pl = [], [], []
for a, n in zip(w.proxyWallet, w.n_events):
    x = pe[a]
    if n >= 3:
        s = x.std(ddof=1); t.append(x.mean() / (s / np.sqrt(n)) if s > 0 else np.nan)
        p1, p2 = boot_p(x)
    else:
        t.append(np.nan); p1 = p2 = np.nan
    pw.append(p1); pl.append(p2)
w["t_stat"], w["p_pos"], w["p_neg"] = t, pw, pl

def cls(r):
    mm = (r.n_trades >= 500 and min(r.n_buy, r.n_sell) / r.n_trades >= 0.25 and abs(r.pnl) / max(r.notional, 1e-9) < 0.02)
    if mm: return "market-maker-like"
    if r.n_events >= 10 and r.p_pos < 0.05 and r.pnl > 0: return "sharp"
    if r.n_events >= 10 and r.p_neg < 0.05 and r.pnl < 0: return "consistent loser"
    if r.n_events <= 2: return "one-off"
    return "other"
w["class"] = w.apply(cls, axis=1)
w = w.sort_values("notional", ascending=False)
w.drop(columns=["proxyWallet"]).assign(address=w.proxyWallet).to_csv(os.path.join(OUT, "wallets.csv"), index=False)

# ---- report
def fmt(r):
    return (f"| {r.pseudonym} | {r.addr} | {r.n_events} | {r.notional:,.0f} | {r.pnl:,.0f} | {r.roi*100:.1f}% | "
            f"{'' if pd.isna(r.p_pos) else f'{r.p_pos:.3f}'} | {r['class']} | {r.cheap_share*100:.0f}% | {r.avg_lead:.0f} |")
hdr = "| pseudonym | addr | events | notional $ | PnL $ | ROI | p(PnL>0) | class | cheap share | avg lead % |\n|---|---|---|---|---|---|---|---|---|---|"
L = [f"# Wallet profile: Elon tweet-count markets\n",
     f"Trade files used: {n_files} (files modified <2 min ago excluded); {n_rows:,} resolved fills; {len(w):,} wallets; {we.event_slug.nunique()} events.\n",
     "Interpretation: each row is one wallet's fill (proxyWallet = that participant, side = THAT wallet's side). Both sides of a match appear as separate rows under the same transactionHash (every hash has >=2 rows; e.g. BUY No@0.999 + BUY Yes@0.001 = a mint, or BUY+SELL of the same asset). So per-wallet PnL is correct, but summed notional/PnL across wallets double-counts volume (PnL sums to ~0 across counterparties, before fees/unresolved).\n",
     "PnL = realised to resolution (hold-to-resolution mark; ignores exits' timing). Lead % = notional-weighted % of the window still remaining at trade time (negative = after window end; >100 = before window start).\n"]
tn, tp = w.notional.sum(), w.pnl.sum()
cl = w.groupby("class").agg(wallets=("pnl", "size"), notional=("notional", "sum"), pnl=("pnl", "sum"))
cl["notional_share"] = cl.notional / tn
L += ["## Classes\n", "| class | wallets | notional share | notional $ | PnL $ | ROI |\n|---|---|---|---|---|---|"]
for k, r in cl.iterrows(): L.append(f"| {k} | {r.wallets} | {r.notional_share*100:.1f}% | {r.notional:,.0f} | {r.pnl:,.0f} | {r.pnl/r.notional*100:.2f}% |")
n10 = (w.n_events>=10).sum()
L.append(f"\n{n10} wallets have >=10 events; with a 5% test ~{0.05*n10:.0f} false-positive 'sharp' labels are expected by chance alone, so treat the sharp class as an upper bound.")
L.append(f"\nTotal notional (double-counted) ${tn:,.0f}; net PnL ${tp:,.0f}.\n")
top10 = w.notional.head(10).sum() / tn
L.append(f"## Concentration\nTop 10 wallets = {top10*100:.1f}% of notional; top 50 = {w.notional.head(50).sum()/tn*100:.1f}%; top 1 = {w.notional.iat[0]/tn*100:.1f}%.\n")
L += ["## Top 20 by notional\n", hdr] + [fmt(r) for _, r in w.head(20).iterrows()]
L += ["\n## Top 20 by PnL\n", hdr] + [fmt(r) for _, r in w.sort_values("pnl", ascending=False).head(20).iterrows()]
L += ["\n## Worst 10 by PnL\n", hdr] + [fmt(r) for _, r in w.sort_values("pnl").head(10).iterrows()]

# cheap-tail behaviour of profitable vs unprofitable wallets
ch = d[d.cheap & d.is_yes].copy()
L.append("\n## Cheap (<0.15) YES tokens: who buys vs sells\n")
def side_stats(x, name):
    return f"| {name} | {x.notional.sum():,.0f} | {x.pnl.sum():,.0f} | {x.pnl.sum()/x.notional.sum()*100:.1f}% | {x.proxyWallet.nunique()} |"
L.append("| set | notional $ | PnL $ | ROI | wallets |\n|---|---|---|---|---|")
for nm, x in [("BUY cheap YES (our strategy)", ch[ch.buy]), ("SELL cheap YES (counterparty)", ch[~ch.buy]),
              ("BUY cheap upper-tail YES", d[d.upper_yes & d.buy]), ("SELL cheap upper-tail YES", d[d.upper_yes & ~d.buy])]:
    L.append(side_stats(x, nm))
sell = d[d.upper_yes & ~d.buy]
sw = sell.groupby("proxyWallet", observed=True).agg(sell_notional=("notional", "sum"), tail_pnl=("pnl", "sum")).join(w.set_index("proxyWallet")[["pseudonym", "addr", "pnl", "roi", "n_events", "class"]])
sw["share"] = sw.sell_notional / sw.sell_notional.sum()
sw = sw.sort_values("sell_notional", ascending=False)
wt = sw.sell_notional / sw.sell_notional.sum()
L.append(f"\nSellers of cheap upper-tail YES: {len(sw)} wallets; top 10 = {sw.share.head(10).sum()*100:.1f}% of that volume. Notional-weighted share of those sellers with positive overall PnL: {(wt*(sw.pnl>0)).sum()*100:.1f}%; weighted mean overall ROI {np.nansum(wt*sw.roi):.2%}. Aggregate overall PnL of sellers ${sw.pnl.sum():,.0f}; their PnL on those tail sells ${sw.tail_pnl.sum():,.0f}.\n")
L.append("| pseudonym | addr | tail-sell notional | tail PnL | overall PnL | overall ROI | events | class |\n|---|---|---|---|---|---|---|---|")
for _, r in sw.head(15).iterrows():
    L.append(f"| {r.pseudonym} | {r.addr} | {r.sell_notional:,.0f} | {r.tail_pnl:,.0f} | {r.pnl:,.0f} | {r.roi*100:.1f}% | {r.n_events} | {r['class']} |")
# profitable wallets: buyer or seller of cheap
L.append("\n## Do profitable wallets buy or sell cheap tokens?\n")
L.append("| group | wallets | cheap-buy notional | cheap-sell notional | buy share of cheap notional |\n|---|---|---|---|---|")
cb = d[d.cheap].groupby(["proxyWallet", "buy"], observed=True).notional.sum().unstack(fill_value=0).rename(columns={True: "b", False: "s"})
for c in ["sharp", "consistent loser", "market-maker-like", "one-off", "other"]:
    ids = w[w["class"] == c].proxyWallet
    x = cb.reindex(ids).fillna(0)
    tot = x.b.sum() + x.s.sum()
    L.append(f"| {c} | {len(ids)} | {x.b.sum():,.0f} | {x.s.sum():,.0f} | {x.b.sum()/tot*100 if tot else float('nan'):.0f}% |")
prof = w[(w.pnl > 0) & (w.n_events >= 5)].proxyWallet; loss = w[(w.pnl <= 0) & (w.n_events >= 5)].proxyWallet
for nm, ids in [("profitable (>=5 ev)", prof), ("unprofitable (>=5 ev)", loss)]:
    x = cb.reindex(ids).fillna(0); L.append(f"| {nm} | {len(ids)} | {x.b.sum():,.0f} | {x.s.sum():,.0f} | {x.b.sum()/(x.b.sum()+x.s.sum())*100:.0f}% |")

# optional: positions API for top 5 sharp wallets
L.append("\n## Broader PnL via data-api (top 5 sharp by PnL)\n")
for _, r in w[w["class"] == "sharp"].sort_values("pnl", ascending=False).head(5).iterrows():
    try:
        pos = get(f"{DATA}/positions", params={"user": r.proxyWallet, "limit": 500, "sizeThreshold": 0})
        cp = sum(float(p.get("cashPnl") or 0) for p in pos); rp = sum(float(p.get("realizedPnl") or 0) for p in pos)
        L.append(f"- {r.pseudonym} {r.addr}: /positions ok, {len(pos)} open positions, cashPnl sum ${cp:,.0f}, realizedPnl sum ${rp:,.0f} (current positions only)")
    except Exception as e:
        L.append(f"- {r.pseudonym} {r.addr}: /positions failed ({str(e)[:60]})")
open(os.path.join(OUT, "wallets.md"), "w").write("\n".join(L) + "\n")
print("\n".join(L))
