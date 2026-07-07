"""Bulk feature-building pipeline for training.

This is the refactor of the legacy ``src/features_v2.py`` script. It uses the
same parsers and haversine implementation as the serving encoder, and
additionally writes ``models/town_centroids.json`` so serving can impute
sensible coordinates when a caller provides only a town.
"""

import json
from pathlib import Path

import pandas as pd

from hdb_avm.features.geo import load_mrt_stations, min_mrt_distance_km
from hdb_avm.features.parsing import remaining_lease_to_years, storey_range_to_mid

RAW_PATH = "data/resale-flat-prices.csv"
BLOCK_COORDS = "data/block_coords.csv"
MRT_COORDS = "data/mrt_station_coords.csv"
PROCESSED_PATH = "data/processed_v2.csv"
CENTROIDS_PATH = "models/town_centroids.json"

NUMERIC_COLUMNS = [
    "floor_area_sqm",
    "storey_mid",
    "remaining_lease_years",
    "transaction_year",
    "transaction_month",
    "latitude",
    "longitude",
    "mrt_distance_km",
    "resale_price",
]


def build_features(
    raw_path: str | Path = RAW_PATH,
    block_coords_path: str | Path = BLOCK_COORDS,
    mrt_coords_path: str | Path = MRT_COORDS,
    processed_path: str | Path = PROCESSED_PATH,
    centroids_path: str | Path | None = CENTROIDS_PATH,
) -> pd.DataFrame:
    print("Loading raw data...")
    df = pd.read_csv(raw_path)
    print(f"  {len(df):,} rows")

    df["month_dt"] = pd.to_datetime(df["month"])
    df["transaction_year"] = df["month_dt"].dt.year
    df["transaction_month"] = df["month_dt"].dt.month
    df["remaining_lease_years"] = df["remaining_lease"].apply(remaining_lease_to_years)
    df["storey_mid"] = df["storey_range"].apply(storey_range_to_mid)

    # Block-level lat/lon join
    print("Joining block coordinates...")
    coords = pd.read_csv(block_coords_path)
    coords.columns = ["query", "latitude", "longitude"]
    coords["query"] = coords["query"].str.strip().str.upper()

    df["query"] = (df["block"].astype(str) + " " + df["street_name"]).str.strip().str.upper()
    df = df.merge(coords[["query", "latitude", "longitude"]], on="query", how="left")

    missing = df["latitude"].isna().sum()
    print(f"  Blocks without coordinates: {missing:,} ({missing / len(df) * 100:.1f}%) — dropped")
    df = df.dropna(subset=["latitude", "longitude"])

    # Town centroids artifact (serving uses these when no address is given)
    if centroids_path is not None:
        centroids = (
            df.groupby("town")[["latitude", "longitude"]].mean().round(6)
        )
        Path(centroids_path).parent.mkdir(parents=True, exist_ok=True)
        with open(centroids_path, "w") as f:
            json.dump(
                {t: [row.latitude, row.longitude] for t, row in centroids.iterrows()},
                f,
                indent=2,
            )
        print(f"  Saved town centroids for {len(centroids)} towns → {centroids_path}")

    # MRT distance from block coords
    print("Computing MRT distances from block coordinates...")
    mrt = load_mrt_stations(mrt_coords_path)
    df["mrt_distance_km"] = df.apply(
        lambda r: min_mrt_distance_km(r["latitude"], r["longitude"], mrt), axis=1
    )

    # Encode categoricals
    print("Encoding categoricals...")
    town_dummies = pd.get_dummies(df["town"], prefix="town")
    flat_type_dummies = pd.get_dummies(df["flat_type"], prefix="flat_type")

    numeric = df[NUMERIC_COLUMNS].reset_index(drop=True)
    processed = pd.concat(
        [numeric, town_dummies.reset_index(drop=True), flat_type_dummies.reset_index(drop=True)],
        axis=1,
    )

    processed.to_csv(processed_path, index=False)
    print(f"Saved {len(processed):,} rows → {processed_path}")
    print(f"Feature columns: {processed.shape[1] - 1} features + target")
    return processed


if __name__ == "__main__":
    build_features()
