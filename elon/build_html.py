#!/usr/bin/env python3
"""Rebuild elon_edge.html from data/ and out/ CSVs. Usage: python3 build_html.py"""
import json, html, os
import pandas as pd

D = os.path.dirname(os.path.abspath(__file__))
P = lambda *a: os.path.join(D, *a)
esc = html.escape

# ---------- data ----------
cal = pd.read_csv(P("out/chart_calibration.csv"))
cal = cal[cal.family == "weekly"]
bands = ["<2c", "2-5c", "5-15c", "15-50c", ">50c"]
def calpts(src):
    d = cal[cal.source == src].set_index("band").reindex(bands)
    return [{"x": round(r.mean_pred * 100, 2), "y": round(r.realised * 100, 2), "n": int(r.n), "b": b}
            for b, r in d.iterrows()]
calib = {"market": calpts("market"), "model": calpts("model")}

sp = pd.read_csv(P("out/chart_spread.csv"))
sp = sp[sp.family == "weekly"]
leads = sorted(sp.lead.unique())
spread = {"leads": [int(l) for l in leads],
          "mkt_sd": [round(float(sp[sp.lead == l].mkt_z.std()), 3) for l in leads],
          "mod_sd": [round(float(sp[sp.lead == l].mod_z.std()), 3) for l in leads],
          "mkt_out": [round(float(((sp[sp.lead == l].mkt_pit < .1) | (sp[sp.lead == l].mkt_pit > .9)).mean() * 100), 1) for l in leads],
          "mod_out": [round(float(((sp[sp.lead == l].mod_pit < .1) | (sp[sp.lead == l].mod_pit > .9)).mean() * 100), 1) for l in leads]}

lk = pd.read_csv(P("out/chart_leavek.csv"))
leavek = {"k": lk.k.tolist(), **{c: [round(v * 100, 1) for v in lk[c]] for c in ["slip0", "slip0.5c", "slip1c", "real10"]}}

cp = pd.read_csv(P("out/chart_cumpnl.csv"))
cum = {"d": cp.date.tolist(), **{c: [round(v, 1) for v in cp[c]] for c in ["slip0", "slip0.5c", "slip1c", "real10"]}}

mo = pd.read_csv(P("out/chart_monthly.csv"))
mo = mo[mo.fill == "real10"]
monthly = {"m": mo.month.tolist(), "roi": [round(v * 100, 0) for v in mo.roi], "n": mo.events.tolist()}

rp = pd.read_csv(P("out/chart_repricing.csv"))
reprice = {"t": rp.tau_min.tolist(), "burst": [round(v, 3) for v in rp.burst_median_frac],
           "placebo": [round(v, 3) for v in rp.placebo_median_frac]}

# example ladder
ps = pd.read_csv(P("data/price_snapshots.csv"))
w = ps[(ps.family == "weekly") & (ps.lead_pct == 50)]
g = w.groupby("event_slug").agg(s=("window_start_utc", "first"), e=("window_end_utc", "first"), win=("outcome_yes", "sum"), nn=("price", lambda x: x.isna().sum()))
g = g[(g.nn == 0) & (g.win == 1) & (g.e <= "2026-10-10T00:00:00Z")].sort_values("s")
slug = g.index[-1]
ev = w[w.event_slug == slug].sort_values("bucket_lo")
ev_start, ev_end = g.loc[slug, "s"][:10], g.loc[slug, "e"][:10]
rows = ""
tot = 0.0
for _, r in ev.iterrows():
    tot += r.price
    win = r.outcome_yes == 1
    rows += (f'<tr class="{"win" if win else ""}"><td>{esc(str(r.bucket_label))}</td>'
             f'<td class="num">{r.price*100:.1f}c</td><td>{"✅ winner" if win else ""}</td></tr>')
ladder = {"rows": rows, "sum": tot, "start": ev_start, "end": ev_end}

DATA = json.dumps({"calib": calib, "spread": spread, "leavek": leavek, "cum": cum,
                   "monthly": monthly, "reprice": reprice}, separators=(",", ":"))

# ---------- content ----------
def table(head, body, cls=""):
    h = "".join(f"<th>{x}</th>" for x in head)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in body)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'

why = table(["", ""], [
    ["<b>The market</b>", "Polymarket weekly (and 48h) “how many times will Elon post?” markets, split into count buckets such as 200–224, 225–249."],
    ["<b>Settles on</b>", "Polymarket's own post tracker (xtracker). Matched the winning bucket in 210 of 212 events since Dec 2025."],
    ["<b>Where the edge comes from</b>", "Our model's forecast spread (sigma) is better matched to reality than the market's early in the week. At the start the outcome lands 1.25 SDs from the market mean and 35% of outcomes fall in the market's outer 20%. Cheap upper-tail buckets are under-priced."],
    ["<b>When it's strongest</b>", "Around 50% elapsed (+156%, p=0.03). 5–15c buckets are best (+81%, p=0.03). At window start it is gone (+15%, p=0.45) because bucket prices sum to about $1.30."],
    ["<b>Why us</b>", "Cheap to run: the model and shadow logger are already built. Settlement is clean (6,125 of 6,132 markets resolved without issue)."],
    ["<b>Risks</b>", "Edge is lumpy (top 5 events ≈ 95% of PnL), vanishes at 1c slippage, does not replicate on sibling markets, pros and bots are present, capacity is tens of dollars a week, tracker late imports are rising."],
    ["<b>Verdict</b>", '<b class="red">GO-to-shadow, not live.</b> Some real information, small and fragile edge.'],
])

green = table(["Weather had", "Elon market", "Fixable?"], [
    ["A physics forecast from outside the market", "Only one person's past behaviour", "<b class=red>No.</b> Partial proxies: news and event calendars (untested)."],
    ["Many independent markets every day", "About 44 independent weeks in 10 months", "<b class=amber>Partly.</b> Add the 48h and sibling families, but those didn't replicate."],
    ["A stable process with published research", "One person, regime shifts (69 → 29 posts a day)", "<b class=red>No.</b> Walk-forward refits help at the margin."],
    ["Two venues agreeing", "Polymarket only. Kalshi's Elon market dormant since Apr 2025", "<b class=red>No</b> for Elon. Possible for Trump via Kalshi KXTRUTHSOCIAL."],
    ["Settlement independent of the venue", "Polymarket's own xtracker, late imports rising", "<b class=amber>Partly.</b> Count from X directly as a cross-check; treat tracker as a lower bound."],
    ["Thin, retail-heavy books", "$2–10M a week; makers and pros hold most volume", "<b class=red>No.</b> That's the market."],
])

related = table(["Family", "Window", "Median vol (90d)", "Free data", "2c depth"], [
    ["Elon posts, weekly", "7d", "$3.0M", "xtracker, from Nov 2025", "≈$2.0k"],
    ["Elon posts, 48h", "2d", "$672k", "xtracker", "≈$1.1k"],
    ["Elon posts, daily / monthly", "1d / 1mo", "$727k", "xtracker", "≈$600"],
    ["Trump Truth Social posts", "7d", "$61k", "xtracker, from Jan 2026", "≈$520"],
    ["White House posts", "7d", "$36k", "xtracker", "≈$50"],
    ["Khamenei / Zelenskyy / NYC Mayor / CZ / Ted Cruz", "7d", "$9–20k", "xtracker, from Mar 2026", "$20–220"],
    ["MrBeast views (several series)", "1–19d", "$36–282k", "<b class=red>No</b>", "$150–230"],
    ["Trump X posts, Trump mentions", "7d", "$12–21k", "<b class=red>No</b>", "≈$20"],
])

G, A, R = "✅", "⚠️", "❌"
QA = [
 (R, "Driven by a few weeks?", "Yes. Top 5 of 86 events make ≈95% of PnL; without them +4% at 0 slippage and −12% at 0.5c. Only 28 of 86 events are net positive. Normal for long shots, but the edge's size can't be measured precisely."),
 (A, "Realistic fills?", "Partly. Mid + half the spread gives +61% at $10; real Jul–Oct fills were ≈4% worse (+54% vs +58%). The &lt;2c band is effectively untradable (touch depth ≈$2). $50+ walks the book on ≈66% of trades."),
 (A, "Is “too narrow” stable?", "Only for weekly, and only early (1.25 SDs, 35% in the outer 20% at start; 1.03 and 25% pooled). From 85% elapsed the market is too wide. 48h is not too narrow (0.86, 13%). No stable direction."),
 (A, "Where does it sit?", "Upper-tail buckets (+151%, p=0.02 vs +23% lower tail; falls to +23% at 1c). 5–15c best (+81%); &lt;2c dies at slippage. Leads 50–55% best, 90–95% lose."),
 (G, "As-known count used?", "Yes. Rebuilt with counts as known at the time; the look-ahead version differs by only $10–20."),
 (A, "Independent bets?", "86 events but only 44 non-overlapping weekly windows. Fri–Fri +59% (p=0.10), Tue–Tue +76% (p=0.05). 14-day block p: 0.018 / 0.09 / 0.28 at 0 / 0.5c / 1c."),
 (R, "Who trades?", "All 208 events, 179k wallets: top 50 hold 35% of volume and ≈1,100 market-maker-like wallets carry 36%. Crowd buyers of cheap upper-tail YES lost 95% of their stake; the model's selective upper-tail picks made +81% in the backtest. Pros sit on the other side."),
 (R, "Repricing speed?", "Fast, no latency edge. ≈88% of a burst is priced in before xtracker imports it. Buying after a burst returns −4%."),
 (R, "Is the lag shrinking?", "Yes, bots are here. Share priced in rose 0.60 → 0.80 → 0.93 across thirds of the sample; price/count correlation 0.13 → ≈0.5."),
 (A, "Related markets", "Inventory done: about 8 free tracker-settled weekly post-count families ($10–60k a week). Few good siblings; view-count markets have no free settlement data."),
 (R, "Does it replicate on related markets?", "No. 7 families, 388 events: +76% at 0 slippage (p=0.08), +1% at 0.5c, −18% at 1c. Model Brier worse than market in 5 of 7."),
 (R, "Same market on other venues?", "No live cross-check. Kalshi KXELONTWEETS dormant since Apr 2025; Manifold has none. Kalshi KXTRUTHSOCIAL could cross-check Trump."),
 (A, "Tracker reliability", "Normal lag 2–3 min. Late imports &lt;1% Dec–Jul, 3.7% Aug–Sep, 26% in Oct 2026. Longest outages 57.7h and 23.5h. Treat live count as a lower bound. Backtest unaffected."),
 (A, "Maker or taker?", "Unknown: resting orders can't be backtested without book history. Maker fee 0 with 25% rebate; median reward $15/day per market. Passive bids on cheap tails face adverse selection. Shadow logger stores books."),
 (R, "Capacity at 1c", "≈8 trades a week, ≈$10/week PnL at 1c (≈$30 at 0.5c). Realistically $50–150/week."),
 (G, "Resolution risk", "6,125 of 6,132 markets resolved cleanly; 12 disputes, none changed the outcome; tracker matched winner in 210 of 212 events. Main risk: rising late imports."),
]
# fix: Q15 flagged against, Q14 unknown (amber) per brief
qa_rows = ""
for i, (s, q, a) in enumerate(QA, 1):
    cls = {G: "green", A: "amber", R: "red"}[s]
    qa_rows += f'<tr><td class="num">Q{i}</td><td class="ic {cls}">{s}</td><td><b>{q}</b><br>{a}</td></tr>'
qa = f'<div class="tw"><table class="qa"><tbody>{qa_rows}</tbody></table></div>'

adv = table(["Objection", "Reviewer", "My ruling"], [
    ["Lottery skew: dropping winners kills anything", "Partly holds", "Agree. Fragility is generic, but we beat a no-information null at 0.5c (90–100th percentile). Real information, size very uncertain."],
    ["Forking paths / many specs tried", "<b>Holds</b>", "Agree: <b>main reason not to go live</b>. White's reality check p=0.45 at 0.5c. Main spec was fixed in advance and sits at the 35th percentile of the grid, but the earlier scan was itself a search."],
    ["Mid vs executable ask", "Partly holds", "Agree. Drop &lt;2c entries live. Actual fills ≈4% worse."],
    ["Stale prices", "Rebutted", "Agree (+70% on freshly updated prices)."],
    ["Regime (post rate halved)", "Rebutted", "Mostly agree: Mar–Oct carries 77% of PnL. But Sep and Oct are negative, the first losing streak since Dec. Watch it."],
    ["Data integrity", "Rebutted for backtest", "Agree, and live risk is rising (26% late imports in Oct)."],
    ["Model no better calibrated than the market", "Partly holds", "Partly. Regressing outcome on both: model weight 0.93 [0.80–1.06], price 0.10. ROI by edge size isn't monotone. Model-picked ≥5c entries make +69% at 0.5c (p=0.017); model-free 5–15c entries lose."],
    ["Capacity and competition", "<b>Holds</b>", "Agree. Tens to low hundreds of dollars a week. Pros and makers present, repricing has sped up."],
    ["<i>Mine:</i> no replication on related markets", "n/a", "A big strike. Weather was confirmed on a second venue; this isn't confirmed on sibling markets."],
])

checklist = [
    "At least 8 weeks and at least 15 resolved weekly events logged.",
    "Paper ROI at the <b>logged ask</b> of at least +15%, and still above 0 after dropping the top 2 events.",
    "Event-clustered p below 0.10, or below 0.20 if the ≥5c arm agrees in sign and size.",
    "Median ask-minus-mid gap on traded buckets ≤ 0.5c, and median $ within 2c of the ask ≥ $25.",
    "Tracker late-import share (&gt;1 hour late) under 10%, and zero resolution mismatches.",
]

def tile(v, l, cls=""):
    return f'<div class="tile"><div class="tv {cls}">{v}</div><div class="tl">{l}</div></div>'
tiles = "".join([
    tile("+68%", "ROI, 0 slippage<br>p=0.018", "green"),
    tile("+41%", "ROI, +0.5c slippage<br>p=0.078", "amber"),
    tile("+16%", "ROI, +1c slippage<br>p=0.24", "red"),
    tile("+61%", "ROI, realistic fills, $10 a trade<br>p=0.042", "amber"),
    tile("44", "independent weeks<br>(86 events overlap)", ""),
    tile("≈95%", "of PnL from the top 5 of 86 events", "red"),
])

def chart(id_, caption, ratio="4/3"):
    return (f'<figure class="{"sq" if ratio=="1/1" else ""}"><div class="cw" style="aspect-ratio:{ratio}"><canvas id="{id_}"></canvas></div>'
            f'<figcaption>{caption}</figcaption></figure>')

body = f"""
<header>
<p class="kicker">Polymarket research · 10 Oct 2026</p>
<h1>Elon Tweet Edge</h1>
<p class="lead">Does the weather-market edge carry over to “how many times will Elon post?” markets? Short answer: <b>some real information, but small and fragile. Shadow it, don't trade it.</b></p>
<div class="verdict-pill">GO-to-shadow, not live</div>
<details class="gloss"><summary>Jargon in 5 lines</summary>
<ul><li><b>Sigma</b> = how spread out a forecast is.</li><li><b>ROI</b> = profit ÷ money staked.</li><li><b>p-value</b> = chance of seeing a result this good by luck alone (lower is better).</li><li><b>Slippage</b> = paying more than the mid price to actually get filled (1c = one cent per share).</li><li><b>Overround</b> = bucket prices adding to more than $1.</li></ul></details>
</header>

<section><h2><span>1</span>What this is</h2>
<p>Every week Polymarket lists about 26 buckets (e.g. 200–224 posts) on how many times Elon Musk will post on X. Each bucket is a YES/NO share that pays $1 if the final count lands in it, and the winner is decided by Polymarket's own post tracker.</p>
<p>We buy YES on cheap buckets when our model says the chance is at least 5 percentage points higher than the price (and price is 50c or less), $10 a trade. The idea: the market sometimes prices the spread of outcomes too narrowly, so far-out buckets are too cheap.</p>
<p>Example, the latest resolved weekly event ({ladder['start']} to {ladder['end']}), prices at 50% of the window elapsed. Prices sum to ${ladder['sum']:.2f}.</p>
<div class="tw narrow"><table class="ladder"><thead><tr><th>Bucket (posts)</th><th>YES price</th><th>Result</th></tr></thead><tbody>{ladder['rows']}</tbody></table></div>
</section>

<section><h2><span>2</span>Why it can work</h2>{why}</section>

<section><h2><span>3</span>Evidence</h2>
<p>Weekly events, as-known counts, buy YES if model − price ≥ 5pp and price ≤ 50c, $10 flat, fee 0.05·p·(1−p).</p>
<div class="tiles">{tiles}</div>
<p class="small">The earlier scan said +115% (p=0.001). My from-scratch rebuild gives about half that ROI and a p-value roughly 20× weaker. The scan's “+90% at window start” does not hold (+15%, p=0.45). Only the 50%-elapsed hot spot holds (+156%, p=0.03).</p>

<h3>a. Calibration: do prices match reality?</h3>
{chart('c_cal', 'Dots on the dashed line are well calibrated. Our model (accent) hugs the line; the market (grey) over-prices the 15–50c band (27% priced, 15% happen) and under-prices cheap buckets slightly. Axes in %, weekly events.', '1/1')}
<h3>b. Market spread vs reality</h3>
{chart('c_spr', 'SD of the outcome in market-sigma units: 1.0 means the market&#39;s spread is right. Early in the week the market is too narrow (1.26 at start); late it is too wide (below 1). Weekly events.')}
{chart('c_out', 'Share of outcomes landing in the market&#39;s outer 20% of its own distribution (20% = calibrated). It is 35% at the start and falls under 20% late.')}
<h3>c. Leave-k-out: drop the best events</h3>
{chart('c_lk', 'Remove the k best events and ROI shrinks fast: dropping the top 5 leaves +4% at 0 slippage and −12% at 0.5c. The edge rides on a handful of winners.')}
<h3>d. Cumulative profit over time</h3>
{chart('c_cum', 'Cumulative PnL in $ at $10 a trade. Gains come in steps (a few big weeks), and the most recent weeks are flat to slightly down.')}
<h3>e. Monthly ROI (realistic fills, $10)</h3>
{chart('c_mon', 'Most months are positive, some hugely so, but Dec, Sep and Oct are negative (Oct is a single event). Lumpy, as expected for long shots.')}
<h3>f. Repricing after bursts of posts</h3>
{chart('c_rep', 'Share of the price move already done, by minutes from the tracker importing a burst (0 = import). Findings: about 88% of a burst is already priced in before the import, so traders watch X directly and there is no latency edge. Placebo = same test at random times.')}
</section>

<section><h2><span>4</span>Green flags weather had that this lacks</h2>{green}</section>

<section><h2><span>5</span>Related markets</h2>{related}
<p><b class="red">Replication (Q11): failed.</b> On 7 sibling families (388 events) with the model unchanged: +76% at 0 slippage (p=0.08), +1% at 0.5c, −18% at 1c. Only Khamenei and CZ are positive after slippage.</p></section>

<section><h2><span>6</span>Answers to Q1–Q16</h2>
<p class="small">✅ favourable or cleanly answered · ⚠️ mixed or unknown · ❌ against the edge</p>{qa}</section>

<section><h2><span>7</span>Adversarial review</h2>{adv}
<p>A reviewer puts the chance a live weekly strategy makes more than $0 after costs over 6 months at about <b>40%</b>; I'd say <b>35–45%</b>. Expected profit is small even if the edge is real.</p></section>

<section><h2><span>8</span>Go / no-go</h2>
<div class="big">GO-to-shadow, not live</div>
<div class="two">
<div><h3>3 biggest reasons for</h3><ul>
<li>Real information: model weight 0.93 vs price 0.10 when regressing outcomes; beats a no-information null at 0.5c.</li>
<li>+61% ROI (p=0.042) at realistic $10 fills.</li>
<li>Shadow logger is free and already built; settlement is clean.</li></ul></div>
<div><h3>3 biggest risks</h3><ul>
<li>Forking paths: p=0.45 after correcting for variants tried, and 1c slippage leaves +16% (p=0.24).</li>
<li>No replication on related markets, bots and pros are present, capacity only tens of dollars a week.</li>
<li>Tracker late imports hit 26% in Oct 2026; Sep and Oct were negative.</li></ul></div>
</div>
<h3>Shadow checklist (all must pass before any live money)</h3>
<ol class="check">{''.join(f'<li>{c}</li>' for c in checklist)}</ol>
<p>The rule is frozen (same spec as the backtest; secondary arm is entries ≥5c only). If it passes: start live at $10 a trade, a $100 cap per event, taker only, buckets of 5c or more. Run the shadow logger for 8–12 weeks.</p>
</section>

<footer>Data date 2026-10-10. Rebuild with <code>python3 build_html.py</code> in <code>elon/</code>. No orders were placed.</footer>
"""

CSS = """
:root{--bg:#fbfaf8;--surface:#fff;--text:#1d2229;--muted:#5b6470;--line:#e2e0db;--accent:#2457c5;--accent-soft:#e6edfb;--green:#17703a;--amber:#a15c00;--red:#b3261e;--grid:#d9d7d2;--series2:#7a8290;--series3:#b86e00;--series4:#7b3fa0}
@media (prefers-color-scheme:dark){:root{--bg:#14171c;--surface:#1c2027;--text:#e7e9ec;--muted:#a0a8b3;--line:#323841;--accent:#7fa6ff;--accent-soft:#1f2a44;--green:#4cc27d;--amber:#f0a73a;--red:#ff7b72;--grid:#363c46;--series2:#9aa3b0;--series3:#f0a73a;--series4:#c79bff}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;padding:32px 16px 64px}
main{max-width:880px;margin:0 auto}
h1{font-size:2.2rem;line-height:1.15;margin:.2em 0 .4em;letter-spacing:-.02em}
h2{font-size:1.4rem;margin:0 0 .8em;display:flex;gap:.6em;align-items:center}
h2 span{background:var(--accent);color:var(--bg);border-radius:50%;min-width:1.7em;height:1.7em;display:inline-flex;align-items:center;justify-content:center;font-size:.8rem}
h3{font-size:1.02rem;margin:1.6em 0 .5em}
section{margin:56px 0}
p{margin:.7em 0}
.kicker{color:var(--muted);font-size:.85rem;text-transform:uppercase;letter-spacing:.08em;margin:0}
.lead{font-size:1.15rem}
.small{font-size:.9rem;color:var(--muted)}
.verdict-pill{display:inline-block;background:var(--accent-soft);color:var(--accent);border:1px solid var(--accent);padding:.3em .9em;border-radius:99px;font-weight:600}
.gloss{margin-top:1em;color:var(--muted);font-size:.92rem}
.gloss summary{cursor:pointer;color:var(--accent)}
.green{color:var(--green)}.amber{color:var(--amber)}.red{color:var(--red)}
.tw{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--surface);margin:1em 0}
.tw.narrow{max-width:460px}
table{border-collapse:collapse;width:100%;font-size:.92rem}
th,td{padding:.6em .8em;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}
tr:last-child td{border-bottom:0}
th{font-size:.78rem;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);background:var(--bg)}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.ladder tr.win td{background:var(--accent-soft);font-weight:600}
.qa td.ic{font-size:1.2rem;width:2.4em;text-align:center}
.qa td.num{color:var(--muted);text-align:left}
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:1em 0}
.tile{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:14px}
.tv{font-size:1.9rem;font-weight:700;letter-spacing:-.02em}
.tl{font-size:.82rem;color:var(--muted);line-height:1.4}
figure.sq{max-width:560px;margin-left:auto;margin-right:auto}
figure{margin:.6em 0 1.4em;background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:12px}
.cw{position:relative;width:100%}
figcaption{font-size:.9rem;color:var(--muted);margin-top:.6em}
.big{font-size:clamp(1.6rem,6vw,2.4rem);font-weight:800;color:var(--accent);background:var(--accent-soft);border-radius:12px;padding:.6em .8em;margin:.5em 0 1em;letter-spacing:-.02em}
.two{display:grid;grid-template-columns:1fr 1fr;gap:20px}
@media(max-width:640px){.tiles{grid-template-columns:repeat(2,1fr)}.two{grid-template-columns:1fr}h1{font-size:1.8rem}}
.check li{margin:.4em 0}
footer{border-top:1px solid var(--line);padding-top:1.2em;color:var(--muted);font-size:.88rem}
code{background:var(--accent-soft);padding:.1em .4em;border-radius:4px}
"""

JS = r"""
const D=JSON.parse(document.getElementById('data').textContent);
const css=n=>getComputedStyle(document.documentElement).getPropertyValue(n).trim();
let charts=[];
function build(){
charts.forEach(c=>c.destroy());charts=[];
const C={text:css('--text'),muted:css('--muted'),grid:css('--grid'),acc:css('--accent'),s2:css('--series2'),s3:css('--series3'),s4:css('--series4'),red:css('--red'),green:css('--green')};
Chart.defaults.color=C.muted;Chart.defaults.font.family='-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif';
Chart.defaults.borderColor=C.grid;
const ax=(t,extra={})=>Object.assign({title:{display:!!t,text:t,color:C.muted},grid:{color:C.grid},ticks:{color:C.muted}},extra);
const base=(x,y,leg=true)=>({responsive:true,maintainAspectRatio:false,animation:false,interaction:{mode:'nearest',intersect:false},plugins:{legend:{display:leg,labels:{color:C.text,boxWidth:14}}},scales:{x:x,y:y}});
const mk=(id,cfg)=>charts.push(new Chart(document.getElementById(id),cfg));
const line=(l,d,c,o={})=>Object.assign({label:l,data:d,borderColor:c,backgroundColor:c,borderWidth:2,pointRadius:0,tension:.2},o);
const ref=(l,d,o={})=>Object.assign({label:l,data:d,borderColor:C.muted,borderDash:[6,4],borderWidth:1.5,pointRadius:0},o);

// a calibration
const pts=a=>a.map(p=>({x:p.x,y:p.y}));
mk('c_cal',{type:'scatter',data:{datasets:[
 {label:'Perfect (y = x)',type:'line',data:[{x:0,y:0},{x:60,y:60}],borderColor:C.muted,borderDash:[6,4],borderWidth:1.5,pointRadius:0},
 {label:'Market',data:pts(D.calib.market),borderColor:C.s2,backgroundColor:C.s2,pointRadius:6,pointStyle:'rectRot',showLine:true,borderWidth:1.5},
 {label:'Model',data:pts(D.calib.model).slice(0,4),borderColor:C.acc,backgroundColor:C.acc,pointRadius:6,showLine:true,borderWidth:1.5}]},
 options:Object.assign(base(ax('Average price / forecast (%)',{min:0,max:60}),ax('Realised frequency (%)',{min:0,max:60})),{plugins:{legend:{labels:{color:C.text,boxWidth:14}},tooltip:{callbacks:{label:c=>c.dataset.label+': priced '+c.parsed.x+'%, happened '+c.parsed.y+'%'}}}})});
// b spread
const L=D.spread.leads;
mk('c_spr',{type:'line',data:{labels:L,datasets:[line('Market',D.spread.mkt_sd,C.s2,{pointRadius:2}),line('Model',D.spread.mod_sd,C.acc,{pointRadius:2}),ref('1.0 = calibrated',L.map(_=>1))]},options:base(ax('% of window elapsed'),ax('SD of outcome (sigma units)',{min:0.4}))});
mk('c_out',{type:'line',data:{labels:L,datasets:[line('Market',D.spread.mkt_out,C.s2,{pointRadius:2}),line('Model',D.spread.mod_out,C.acc,{pointRadius:2}),ref('20% = calibrated',L.map(_=>20))]},options:base(ax('% of window elapsed'),ax('Outcomes in outer 20% (%)',{min:0}))});
// c leave-k
const K=D.leavek.k;
mk('c_lk',{type:'line',data:{labels:K,datasets:[line('0 slippage',D.leavek.slip0,C.acc),line('+0.5c',D.leavek['slip0.5c'],C.s3),line('+1c',D.leavek.slip1c,C.red),line('Realistic $10',D.leavek.real10,C.s4,{borderDash:[2,3]}),ref('Zero',K.map(_=>0),{borderColor:C.text,borderDash:[]})]},options:base(ax('Best events removed (k)'),ax('ROI (%)'))});
// d cum
mk('c_cum',{type:'line',data:{labels:D.cum.d,datasets:[line('0 slippage',D.cum.slip0,C.acc),line('+0.5c',D.cum['slip0.5c'],C.s3),line('+1c',D.cum.slip1c,C.red),line('Realistic $10',D.cum.real10,C.s4,{borderDash:[2,3]})]},options:base(ax('',{ticks:{color:C.muted,maxTicksLimit:7,maxRotation:0}}),ax('Cumulative PnL ($)'))});
// e monthly
mk('c_mon',{type:'bar',data:{labels:D.monthly.m,datasets:[{label:'ROI %',data:D.monthly.roi,backgroundColor:D.monthly.roi.map(v=>v>=0?C.acc:C.red)}]},options:base(ax('',{ticks:{color:C.muted,maxRotation:60}}),ax('ROI (%)'),false)});
// f repricing
const T=D.reprice.t;
mk('c_rep',{type:'line',data:{labels:T,datasets:[line('After a burst',D.reprice.burst,C.acc),line('Placebo (random times)',D.reprice.placebo,C.s2)]},options:base(ax('Minutes from tracker import',{ticks:{color:C.muted,autoSkip:false,maxRotation:0,callback:function(v){return T[v]%60==0?T[v]:''}}}),ax('Median share of move priced in',{min:-0.2,max:1.2}))});
}
build();
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',build);
"""

out = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>Elon Tweet Edge</title>
<style>{CSS}</style></head>
<body><main>{body}</main>
<script type="application/json" id="data">{DATA}</script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<script>{JS}</script>
</body></html>"""
with open(P("elon_edge.html"), "w", encoding="utf-8") as f:
    f.write(out)
print("wrote", P("elon_edge.html"), len(out))
