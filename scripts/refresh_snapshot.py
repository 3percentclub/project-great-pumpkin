"""Re-download the offline snapshot in data/. Run this before class:

    python scripts/refresh_snapshot.py

The lab falls back to this snapshot when NYC Open Data is slow or says
"429 Too Many Requests", which happens when a whole room hits it at once.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import httpx

DATA = Path(__file__).resolve().parent.parent / "data"
BASE = "https://data.cityofnewyork.us/resource"

gardens = httpx.get(f"{BASE}/p78i-pat6.json", timeout=60, params={
    "$select": "gardenname,address,zipcode,borough,nta", "$limit": 5000}).json()

since = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT00:00:00")
rows = httpx.get(f"{BASE}/erm2-nwe9.json", timeout=120, params={
    "$select": "incident_zip, count(*) AS n",
    "$where": f"complaint_type like 'Noise%' AND created_date > '{since}' AND incident_zip IS NOT NULL",
    "$group": "incident_zip", "$limit": 5000}).json()
noise = {r["incident_zip"]: int(r["n"]) for r in rows}

DATA.mkdir(exist_ok=True)
(DATA / "gardens.json").write_text(json.dumps(gardens, indent=0))
(DATA / "noise_7d.json").write_text(json.dumps(
    {"captured": datetime.now().strftime("%Y-%m-%d"), "days": 7, "counts": noise}, indent=0))
print(f"Saved {len(gardens)} gardens and noise counts for {len(noise)} zips.")
