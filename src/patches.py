"""The "hands": plain Python that talks to NYC Open Data.

No model lives here. These functions are what the model *asks* for. Your loop
(or an MCP client) runs them and hands the result back to the model.

No print() here except in the __main__ smoke test, because server.py imports
this module and in an MCP server stdout carries the protocol.
"""

from datetime import datetime, timedelta

import httpx

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

TIMEOUT = 20  # seconds. The city API is sometimes slow, especially with a whole class on it.


def _get(url: str, params: dict) -> list[dict]:
    """GET from Socrata, retrying once if it times out (it sometimes does)."""
    for attempt in range(2):
        try:
            resp = httpx.get(url, params=params, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except httpx.TimeoutException:
            if attempt == 1:
                raise
    return []


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
    return [
        {
            "gardenname": row.get("gardenname", ""),
            "address": row.get("address", ""),
            "zipcode": row.get("zipcode", ""),
            "borough": borough.strip().upper(),
            "nta": row.get("nta", ""),
        }
        for row in _get(GARDENS_URL, params)
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
