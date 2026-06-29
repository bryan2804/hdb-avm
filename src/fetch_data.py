"""
Fetch latest HDB resale transactions from data.gov.sg API.
Merges with existing CSV and removes duplicates.
Run monthly to keep the dataset current.

Usage:
    python3 src/fetch_data.py
"""

import time
import pandas as pd
import requests
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
# To verify this resource_id:
# 1. Go to data.gov.sg
# 2. Search "resale flat prices based on registration date from jan-2017"
# 3. Click the dataset → click API → copy resource_id from the URL
RESOURCE_ID = "d_8b84c4ee58e3cfc0ece0d773c8ca6abc"
API_URL = "https://data.gov.sg/api/action/datastore_search"
RAW_PATH = "data/resale-flat-prices.csv"
LIMIT = 500  # max records per API call


def get_latest_month(path: str) -> str | None:
    if not Path(path).exists():
        return None
    df = pd.read_csv(path, usecols=["month"])
    return df["month"].max()


def fetch_page(offset: int, sort: str = "month asc") -> dict:
    resp = requests.get(API_URL, params={
        "resource_id": RESOURCE_ID,
        "limit": LIMIT,
        "offset": offset,
        "sort": sort,
    }, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_all() -> pd.DataFrame:
    """Fetch every record from the API (used when no existing data)."""
    records = []
    offset = 0

    first = fetch_page(0)
    total = first["result"]["total"]
    print(f"Total records available: {total:,}")

    records.extend(first["result"]["records"])
    offset += LIMIT

    while offset < total:
        data = fetch_page(offset)
        batch = data["result"]["records"]
        if not batch:
            break
        records.extend(batch)
        offset += LIMIT
        print(f"  {len(records):,} / {total:,}", end="\r")
        time.sleep(0.2)

    print(f"\nFetched {len(records):,} total records")
    return pd.DataFrame(records)


def fetch_since(latest_month: str) -> pd.DataFrame:
    """Fetch only records newer than latest_month."""
    records = []
    offset = 0

    print(f"Fetching records after {latest_month}...")
    while True:
        data = fetch_page(offset, sort="month desc")
        batch = data["result"]["records"]
        if not batch:
            break

        new_in_batch = [r for r in batch if r["month"] > latest_month]
        records.extend(new_in_batch)

        # If this batch contains old records we've hit the boundary
        if len(new_in_batch) < len(batch):
            break

        offset += LIMIT
        time.sleep(0.2)

    print(f"Found {len(records):,} new records")
    return pd.DataFrame(records) if records else pd.DataFrame()


def clean_api_df(df: pd.DataFrame) -> pd.DataFrame:
    """Drop API internal columns and standardise types."""
    if "_id" in df.columns:
        df = df.drop(columns=["_id"])
    # API returns everything as strings — cast numeric columns
    for col in ["floor_area_sqm", "resale_price", "lease_commence_date"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def update_dataset():
    latest_month = get_latest_month(RAW_PATH)

    if latest_month is None:
        print("No existing data found. Fetching full dataset...")
        new_df = fetch_all()
    else:
        print(f"Existing data latest month: {latest_month}")
        new_df = fetch_since(latest_month)

    if new_df.empty:
        print("Dataset already up to date.")
        return

    new_df = clean_api_df(new_df)

    if latest_month is not None:
        existing = pd.read_csv(RAW_PATH)
        combined = pd.concat([existing, new_df], ignore_index=True)
        combined = combined.drop_duplicates(
            subset=["month", "block", "street_name", "flat_type",
                    "storey_range", "resale_price"]
        )
        combined = combined.sort_values("month").reset_index(drop=True)
    else:
        combined = new_df.sort_values("month").reset_index(drop=True)

    combined.to_csv(RAW_PATH, index=False)
    print(f"Saved {len(combined):,} rows. Latest month: {combined['month'].max()}")


if __name__ == "__main__":
    update_dataset()
