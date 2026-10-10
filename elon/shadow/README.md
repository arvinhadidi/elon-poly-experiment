# Shadow logger (paper only)

Logs live Polymarket Elon tweet-count markets every 15 min, simulates the backtest rule ("buy YES if p_model - ask >= 0.05 and ask <= 0.50, $10 flat, fee 0.05*e*(1-e)/share"), settles after resolution and checks go-live criteria. It cannot trade: public GET endpoints only. See `SPEC.md`.

## Setup
```
cd elon/shadow
python3 -m venv venv && . venv/bin/activate
pip install requests pandas numpy scipy
python3 export_k.py        # (re)builds k_table.json from ../backtest.py (needs ../data); committed copy is included
python3 shadow_logger.py   # smoke test
```
## Cron (see SPEC.md)
```
*/15 * * * * cd /path/to/elon/shadow && /usr/bin/python3 shadow_logger.py >> logs/cron.log 2>&1
17 6 * * *   cd /path/to/elon/shadow && /usr/bin/python3 settle.py >> logs/settle.log 2>&1
```
Weekly by hand: `python3 report.py` (writes and prints `report.md`). Refresh k monthly with `export_k.py`.

## Reading report.md
- Header: runs, span in weeks, trades logged vs settled, resolved events.
- Results: ROI at the logged ask and at +0.5c, event-clustered bootstrap p, split by family, ask band and lead.
- Fill realism: how much $ sits within 2c of the ask; if < $10 often, paper ROI is optimistic.
- Tracker health: late-import share and tracker-vs-resolution mismatches.
- Go-live checklist: six PASS/FAIL lines; go live only if all PASS (criteria need >= 8 weeks of data, so expect FAIL (no data) early on).

Files: `shadow.db`, `logs/`, `rawbooks/` and `report.md` are gitignored. Env `SHADOW_DB` overrides the DB path.
