"""The "hands": plain Python that talks to NYC Open Data.

No model lives here. These functions are what the model *asks* for. Your loop
(or an MCP client) runs them and hands the result back to the model.

No print() here except in the __main__ smoke test, because server.py imports
this module and in an MCP server stdout carries the protocol.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()  # picks up SODA_APP_TOKEN and OFFLINE from .env, if you set them
log = logging.getLogger(__name__)  # logs go to stderr, never stdout

GARDENS_URL = "https://data.cityofnewyork.us/resource/p78i-pat6.json"  # GreenThumb gardens
NOISE_URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"  # 311 requests

# GreenThumb stores borough as a one-letter code, not a name.
BOROUGH_CODES = {
    "BROOKLYN": "B",
    "MANHATTAN": "M",
    "QUEENS": "Q",
    "BRONX": "X",
    "STATEN ISLAND": "R",
}

TIMEOUT = 10  # seconds
DATA_DIR = Path(__file__).resolve().parent.parent / "data"  # offline snapshot


def _get(url: str, params: dict) -> list[dict] | None:
    """GET from NYC Open Data. Returns None if it's busy, slow, or offline.

    When a whole room hits the city API at once it answers "429 Too Many
    Requests". Instead of failing, the callers below fall back to a snapshot
    saved in data/. Set OFFLINE=1 in .env to always use the snapshot.
    """
    if os.getenv("OFFLINE") == "1":
        return None
    token = os.getenv("SODA_APP_TOKEN")  # optional free token raises the limit
    headers = {"X-App-Token": token} if token else {}
    try:
        resp = httpx.get(url, params=params, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        log.warning("NYC Open Data unavailable (%s). Using the offline snapshot.", e)
        return None


def _snapshot(name: str):
    return json.loads((DATA_DIR / name).read_text())


def get_gardens(borough: str, limit: int = 5) -> list[dict]:
    """Return up to `limit` community gardens in a borough.

    `borough` must be a full borough name like "QUEENS". Anything else
    (for example "Astoria") returns [] with no hint. That is on purpose:
    it's the bug you fix in Milestone 2.
    """
    code = BOROUGH_CODES.get(borough.strip().upper())
    if code is None:
        return []

    params = {
        "borough": code,
        "$select": "gardenname,address,zipcode,borough,nta",
        "$order": "gardenname",  # stable order, so two runs look the same
        "$limit": max(1, min(int(limit), 20)),
    }
    rows = _get(GARDENS_URL, params)
    if rows is None:  # live API unavailable: same query against the snapshot
        rows = sorted((r for r in _snapshot("gardens.json") if r.get("borough") == code),
                      key=lambda r: r.get("gardenname", ""))[: params["$limit"]]
    return [
        {
            "gardenname": row.get("gardenname", ""),
            "address": row.get("address", ""),
            "zipcode": row.get("zipcode", ""),
            "borough": borough.strip().upper(),
            "nta": row.get("nta", ""),
        }
        for row in rows
    ]


def count_noise_complaints(zipcode: str, days: int = 7) -> int:
    """Count 311 noise complaints in one zip code over the last `days` days.

    We ask the API for count(*) instead of downloading rows and counting them.
    Counting downloaded rows would top out at the row limit, so every busy
    zip would get the same number.
    """
    since = (datetime.now() - timedelta(days=int(days))).strftime("%Y-%m-%dT00:00:00")
    where = (
        f"incident_zip = '{int(zipcode):05d}' "  # int() rejects anything that isn't a number
        f"AND complaint_type like 'Noise%' "
        f"AND created_date > '{since}'"
    )
    params = {"$select": "count(*)", "$where": where}
    rows = _get(NOISE_URL, params)
    if rows is None:  # live API unavailable: use the saved 7-day counts
        return _snapshot("noise_7d.json")["counts"].get(f"{int(zipcode):05d}", 0)
    return int(rows[0]["count"]) if rows else 0


def sincerity(noise_complaints: int) -> dict:
    """Turn a noise count into Linus's sincerity score. Pure code, no model.

    The model should never do this math itself. Arithmetic is the exact half
    of the job, and plain code gets it right every time.
    """
    score = max(0, 100 - noise_complaints // 2)
    if score >= 60:
        label = "Sincere"
    elif score >= 30:
        label = "Mostly sincere"
    else:
        label = "Chaotic patch"
    return {"noise_complaints": noise_complaints, "sincerity_score": score, "label": label}


if __name__ == "__main__":
    # Smoke test: no LLM, just proves the data side works.
    print("Gardens in QUEENS:")
    for g in get_gardens("QUEENS", limit=3):
        print(f"  - {g['gardenname']} | {g['address']} | {g['zipcode']}")
    print("Gardens in 'Astoria' (should be empty):", get_gardens("Astoria"))
    print("Noise complaints in 11102, last 7 days:", count_noise_complaints("11102"))
