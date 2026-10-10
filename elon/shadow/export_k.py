#!/usr/bin/env python3
"""Export the latest walk-forward NB size k per family x lead from backtest.py into k_table.json.
Re-runs backtest.py (about 1 min, offline, read-only) and calls its own k_walk() with t=infinity, so the rule is
identical to the backtest: per-lead fit if >=10 prior events at that lead, else pooled over leads if >=4 events, else 15."""
import os, sys, json, runpy, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
bt = runpy.run_path(os.path.join(HERE, "..", "backtest.py"))
k_walk, LEADS, FAMS, dec, fit_k = bt["k_walk"], bt["LEADS"], bt["FAMS"], bt["dec"], bt["fit_k"]
out = {"generated_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "default_k": bt["DEFAULT_K"],
       "n_events": {f: int(dec[dec.family == f].event_slug.nunique()) for f in FAMS}, "families": {}}
for f in FAMS:
    past = dec[dec.family == f]
    pooled = fit_k(past.R_as.values, past.mu.values) if past.event_slug.nunique() >= 4 else bt["DEFAULT_K"]
    leads = {}
    for l in LEADS:
        k, src, n = k_walk(f, l, 10**12)
        leads[str(int(l))] = {"k": round(float(k), 4), "src": src, "n": int(n)}
    out["families"][f] = {"pooled_k": round(float(pooled), 4), "leads": leads}
json.dump(out, open(os.path.join(HERE, "k_table.json"), "w"), indent=1)
print("wrote k_table.json", out["n_events"])
