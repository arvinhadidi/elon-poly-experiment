"""Shared helpers for the SHADOW logger. PAPER TRADING ONLY: this package only issues public HTTP GETs.
There is no key handling, no signing and no order code anywhere. Do not add any."""
import os, sys, re, json, gzip, math, sqlite3, datetime as dt
from zoneinfo import ZoneInfo
import numpy as np
from scipy.stats import nbinom

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import common  # noqa: E402  (UA, GAMMA, CLOB, XT, get)
from common import GAMMA, CLOB, XT, UA  # noqa: E402

DB = os.environ.get("SHADOW_DB", os.path.join(HERE, "shadow.db"))
SERIES = {"10000": "weekly", "10816": "48h"}
EDGE_MIN, ASK_MAX, ASK_MIN, STAKE = 0.05, 0.50, 0.001, 10.0
EVENT_CAP, REBUY_HOURS, DEPTH_BAND = 100.0, 12, 0.02
LEAD_MIN_TRADE, LEAD_MAX_TRADE = -10, 95     # leads validated in backtest.py
SLIP_ALT = 0.005

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs(run_id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER, ts_iso TEXT, status TEXT, n_events INTEGER,
  n_books INTEGER, n_trades INTEGER, last_sync TEXT, last_sync_error TEXT, errors TEXT);
CREATE TABLE IF NOT EXISTS posts(id TEXT PRIMARY KEY, c INTEGER, i INTEGER);
CREATE INDEX IF NOT EXISTS posts_c ON posts(c);
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS tracker(run_id INTEGER, ts INTEGER, event_slug TEXT, family TEXT, window_start INTEGER, window_end INTEGER,
  window_source TEXT, raw_count INTEGER, asknown_count INTEGER, newest_created TEXT, newest_imported TEXT, last_sync TEXT, last_sync_error TEXT);
CREATE TABLE IF NOT EXISTS books(run_id INTEGER, ts INTEGER, event_slug TEXT, token_id TEXT, bucket_lo INTEGER, bucket_hi INTEGER,
  status TEXT, best_ask REAL, best_bid REAL, depth2c_usd REAL, book_gz BLOB);
CREATE INDEX IF NOT EXISTS books_ev ON books(event_slug, ts);
CREATE TABLE IF NOT EXISTS preds(run_id INTEGER, ts INTEGER, event_slug TEXT, family TEXT, bucket_lo INTEGER, bucket_hi INTEGER, token_id TEXT,
  lead_pct REAL, lead_grid INTEGER, k REAL, k_src TEXT, K_asknown INTEGER, mu REAL, p_model REAL, ask REAL, bid REAL, depth2c_usd REAL,
  edge REAL, would_trade INTEGER, skip_reason TEXT);
CREATE INDEX IF NOT EXISTS preds_ev ON preds(event_slug, ts);
CREATE TABLE IF NOT EXISTS paper_trades(trade_id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER, ts INTEGER, event_slug TEXT, family TEXT,
  bucket_lo INTEGER, bucket_hi INTEGER, token_id TEXT, lead_pct REAL, lead_grid INTEGER, p_model REAL, ask REAL, bid REAL, edge REAL,
  stake REAL, shares REAL, fee_per_share REAL, depth2c_usd REAL, K_asknown INTEGER, mu REAL, k REAL);
CREATE TABLE IF NOT EXISTS settlements(trade_id INTEGER PRIMARY KEY, event_slug TEXT, outcome_yes INTEGER, pnl REAL, pnl_p05 REAL, settled_ts INTEGER);
CREATE TABLE IF NOT EXISTS event_results(event_slug TEXT PRIMARY KEY, family TEXT, window_start INTEGER, window_end INTEGER, win_lo INTEGER,
  win_hi INTEGER, tracker_final INTEGER, tracker_lo INTEGER, tracker_hi INTEGER, mismatch INTEGER, note TEXT, settled_ts INTEGER);
"""

def db():
    c = sqlite3.connect(DB, timeout=60)
    c.executescript(SCHEMA)
    return c

def now_s(): return int(dt.datetime.now(dt.timezone.utc).timestamp())

def iso(ts): return dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def to_s(x):
    """ISO string -> floored epoch seconds (same convention as backtest.to_sec)."""
    return int(dt.datetime.fromisoformat(x.replace("Z", "+00:00")).timestamp() // 1)

# ---------- bucket parsing ----------
def parse_bucket(label):
    s = label.strip().lower().replace(",", "")
    m = re.match(r"^<\s*(\d+)$", s)
    if m: return 0, int(m.group(1)) - 1
    m = re.match(r"^(\d+)\s*(\+|or more)$", s)
    if m: return int(m.group(1)), 999999
    m = re.match(r"^(\d+)\s*[-–]\s*(\d+)$", s)
    if m: return int(m.group(1)), int(m.group(2))
    return None

# ---------- window ----------
def parse_description_window(desc, end_hint=None):
    """'from October 8 12:00 PM ET to October 10, 2026 12:00 PM ET' -> (S, E) epoch seconds."""
    m = re.search(r"from\s+([A-Za-z]+)\s+(\d+)(?:,?\s*(\d{4}))?\s+(\d+:\d+\s*[AP]M)\s*ET\s+to\s+([A-Za-z]+)\s+(\d+),?\s*(\d{4})\s+(\d+:\d+\s*[AP]M)\s*ET", desc or "")
    if not m: return None
    m1, d1, y1, t1, m2, d2, y2, t2 = m.groups()
    et = ZoneInfo("America/New_York")
    def mk(mon, d, y, t):
        return int(dt.datetime.strptime(f"{mon} {d} {y} {t.replace(' ', '')}", "%B %d %Y %I:%M%p").replace(tzinfo=et).timestamp())
    E = mk(m2, d2, y2, t2)
    S = mk(m1, d1, y1 or y2, t1)
    if S >= E:  # year rollover
        S = mk(m1, d1, str(int(y2) - 1), t1)
    return S, E

# ---------- model (identical to backtest.py) ----------
def lam_vec(PC, PI, PSLOT, t):
    lo = np.searchsorted(PC, t - 28 * 86400, "left"); hi = np.searchsorted(PC, t, "left")
    c, i, s = PC[lo:hi], PI[lo:hi], PSLOT[lo:hi]
    ok = (c < t - 86400) | (i <= t)
    return np.bincount(s[ok], minlength=168) / 4.0

def mu_remaining(lam, t, S, E):
    a = max(t, S); mu = 0.0
    while a < E:
        b = min((a // 3600 + 1) * 3600, E)
        mu += lam[(a // 3600) % 168] * (b - a) / 3600.0
        a = b
    return mu

def bucket_p(K, mu, k, lo, hi):
    mu = max(mu, 1e-6)
    p = k / (k + mu)
    return float(np.clip(nbinom.cdf(hi - K, k, p) - nbinom.cdf(lo - 1 - K, k, p), 0, 1))

def load_k_table():
    return json.load(open(os.path.join(HERE, "k_table.json")))

def k_for(ktab, family, lead_pct):
    leads = ktab["families"][family]["leads"]
    grid = sorted(int(x) for x in leads)
    g = min(grid, key=lambda x: abs(x - lead_pct))
    e = leads[str(g)]
    return e["k"], e["src"], g

def fee_ps(e): return 0.05 * e * (1 - e)

def pnl(entry, win):
    sh = STAKE / entry
    return sh * win - STAKE - sh * fee_ps(entry)

def tracker_posts(start_s, end_s):
    """Public GET only. endDate is exclusive."""
    r = common.get(f"{XT}/users/elonmusk/posts", {"platform": "x", "startDate": iso(start_s), "endDate": iso(end_s)})
    return r["data"]
