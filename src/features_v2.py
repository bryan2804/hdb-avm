"""
Feature engineering for HDB resale price model — v2.
Adds block-level latitude and longitude from block_coords.csv,
giving the model within-town geographic precision.

Changes vs v1:
  - Merges block_coords.csv using block + street_name as key
  - Adds latitude, longitude as continuous features
  - Keeps town one-hot encoding (model uses both)

Usage:
    python3 src/features_v2.py
"""

import re
import numpy as np
import pandas as pd

RAW_PATH        = "data/resale-flat-prices.csv"
BLOCK_COORDS    = "data/block_coords.csv"
MRT_COORDS      = "data/mrt_station_coords.csv"
PROCESSED_PATH  = "data/processed_v2.csv"


# ── Parsers ───────────────────────────────────────────────────────────────────

def remaining_lease_to_years(text: str) -> float:
    """Convert '61 years 04 months' → 61.33."""
    years, months = 0, 0
    parts = str(text).split()
    for i, part in enumerate(parts):
        if part.startswith("year"):
            years = int(parts[i - 1])
        elif part.startswith("month"):
            months = int(parts[i - 1])
    return round(years + months / 12, 2)


def storey_range_to_mid(storey_range: str) -> int:
    """Convert '10 TO 12' → 11."""
    nums = re.findall(r"\d+", str(storey_range))
    if len(nums) >= 2:
        return (int(nums[0]) + int(nums[1])) // 2
    return int(nums[0]) if nums else 0


# ── Distance helper ───────────────────────────────────────────────────────────

def haversine_min_distance(lat: float, lon: float, mrt_df: pd.DataFrame) -> float:
    """Return distance in km from (lat, lon) to nearest MRT station."""
    R = 6371.0
    lat_r  = np.radians(lat)
    lon_r  = np.radians(lon)
    mlat_r = np.radians(mrt_df["latitude"].values)
    mlon_r = np.radians(mrt_df["longitude"].values)

    dlat = mlat_r - lat_r
    dlon = mlon_r - lon_r
    a = np.sin(dlat / 2) ** 2 + np.cos(lat_r) * np.cos(mlat_r) * np.sin(dlon / 2) ** 2
    return float(np.min(2 * R * np.arcsin(np.sqrt(a))))


# ── Main ──────────────────────────────────────────────────────────────────────

def build_features():
    print("Loading raw data...")
    df = pd.read_csv(RAW_PATH)
    print(f"  {len(df):,} rows")

    # Parse date
    df["month_dt"]          = pd.to_datetime(df["month"])
    df["transaction_year"]  = df["month_dt"].dt.year
    df["transaction_month"] = df["month_dt"].dt.month

    # Parse remaining lease
    df["remaining_lease_years"] = df["remaining_lease"].apply(remaining_lease_to_years)

    # Parse storey
    df["storey_mid"] = df["storey_range"].apply(storey_range_to_mid)

    # ── Block-level lat/lon join ──────────────────────────────────────────────
    print("Joining block coordinates...")
    coords = pd.read_csv(BLOCK_COORDS)
    coords.columns = ["query", "latitude", "longitude"]
    coords["query"] = coords["query"].str.strip().str.upper()

    df["query"] = (df["block"].astype(str) + " " + df["street_name"]).str.strip().str.upper()
    df = df.merge(coords[["query", "latitude", "longitude"]], on="query", how="left")

    missing = df["latitude"].isna().sum()
    pct = missing / len(df) * 100
    print(f"  Blocks without coordinates: {missing:,} ({pct:.1f}%) — will be dropped")
    df = df.dropna(subset=["latitude", "longitude"])

    # ── MRT distance from block coords ────────────────────────────────────────
    print("Computing MRT distances from block coordinates...")
    mrt = pd.read_csv(MRT_COORDS)
    # Normalise MRT column names
    mrt.columns = [c.lower() for c in mrt.columns]
    lat_col = [c for c in mrt.columns if "lat" in c][0]
    lon_col = [c for c in mrt.columns if "lon" in c][0]
    mrt = mrt.rename(columns={lat_col: "latitude", lon_col: "longitude"})

    df["mrt_distance_km"] = df.apply(
        lambda r: haversine_min_distance(r["latitude"], r["longitude"], mrt), axis=1
    )

    # ── Encode categoricals ───────────────────────────────────────────────────
    print("Encoding categoricals...")
    town_dummies      = pd.get_dummies(df["town"],      prefix="town")
    flat_type_dummies = pd.get_dummies(df["flat_type"], prefix="flat_type")

    # ── Assemble feature matrix ───────────────────────────────────────────────
    numeric = df[[
        "floor_area_sqm",
        "storey_mid",
        "remaining_lease_years",
        "transaction_year",
        "transaction_month",
        "latitude",
        "longitude",
        "mrt_distance_km",
        "resale_price",
    ]].reset_index(drop=True)

    processed = pd.concat(
        [numeric, town_dummies.reset_index(drop=True), flat_type_dummies.reset_index(drop=True)],
        axis=1
    )

    processed.to_csv(PROCESSED_PATH, index=False)
    print(f"Saved {len(processed):,} rows → {PROCESSED_PATH}")
    print(f"Feature columns: {processed.shape[1] - 1} features + target")

    return processed


if __name__ == "__main__":
    build_features()
