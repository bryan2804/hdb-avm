"""
Shared geocoding helper using OneMap's public search API (no API key
needed for basic search). Rate-limited to ~2 requests/sec since the
endpoint returns 429 above that without an auth token.
"""

import csv
import os
import time
from urllib.parse import quote
from urllib.request import urlopen
from urllib.error import HTTPError
import json

ONEMAP_SEARCH_URL = (
    "https://www.onemap.gov.sg/api/common/elastic/search"
    "?searchVal={query}&returnGeom=Y&getAddrDetails=Y&pageNum=1"
)
REQUEST_DELAY_SEC = 0.5
MAX_RETRIES = 5


def geocode(query: str) -> tuple[float, float] | None:
    """Look up a single address/building name. Returns (lat, lon) or None."""
    url = ONEMAP_SEARCH_URL.format(query=quote(query))

    for attempt in range(MAX_RETRIES):
        try:
            with urlopen(url, timeout=10) as resp:
                data = json.load(resp)
            results = data.get("results") or []
            if not results:
                return None
            r = results[0]
            return float(r["LATITUDE"]), float(r["LONGITUDE"])
        except HTTPError as e:
            if e.code == 429:
                time.sleep(2 * (attempt + 1))
                continue
            return None
        except Exception:
            return None
    return None


def load_cache(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    cache = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            lat, lon = row.get("lat"), row.get("lon")
            cache[row["query"]] = (float(lat), float(lon)) if lat and lon else None
    return cache


def geocode_all(queries: list[str], cache_path: str, log_every: int = 50) -> dict:
    """
    Geocode a list of queries, resuming from cache_path if it exists.
    Writes incrementally so an interrupted run can resume.
    """
    cache = load_cache(cache_path)
    todo = [q for q in queries if q not in cache]
    print(f"{len(cache)} cached, {len(todo)} to geocode")

    write_header = not os.path.exists(cache_path)
    with open(cache_path, "a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(["query", "lat", "lon"])

        for i, q in enumerate(todo):
            result = geocode(q)
            cache[q] = result
            lat, lon = result if result else ("", "")
            writer.writerow([q, lat, lon])
            f.flush()
            if (i + 1) % log_every == 0:
                print(f"  {i + 1}/{len(todo)} geocoded")
            time.sleep(REQUEST_DELAY_SEC)

    return cache
