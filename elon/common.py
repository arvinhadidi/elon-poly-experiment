"""Shared HTTP helpers for all elon/ scripts. Public endpoints only, no keys."""
import json, time, requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
DATA = "https://data-api.polymarket.com"
XT = "https://xtracker.polymarket.com/api"

_s = requests.Session()
_s.headers.update(UA)


def get(url, params=None, tries=5, timeout=30):
    """GET JSON with retry/backoff. Returns parsed JSON or raises."""
    for i in range(tries):
        try:
            r = _s.get(url, params=params, timeout=timeout)
            if r.status_code == 429 or r.status_code >= 500:
                raise requests.HTTPError(f"{r.status_code}")
            r.raise_for_status()
            return r.json()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(2 ** i)


def parse_json_field(v):
    """Gamma returns some list fields (clobTokenIds, outcomePrices) as JSON strings."""
    if isinstance(v, str):
        try:
            return json.loads(v)
        except Exception:
            return v
    return v
