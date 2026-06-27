"""
Feature engineering for the HDB resale price model.

Builds remaining lease (years), storey midpoint, transaction year/month,
mrt_distance_km (haversine to nearest MRT/LRT station), and one-hot
encodings for town and flat_type.

mrt_distance_km requires data/mrt_station_coords.csv and data/block_coords.csv
(built by geocode_mrt.py and geocode_blocks.py respectively) -- run those
first if those files don't exist yet.
"""

import pandas as pd

from mrt_distance import add_mrt_distance

RAW_PATH = "data/resale-flat-prices.csv"
PROCESSED_PATH = "data/processed.csv"


def remaining_lease_to_years(text: str) -> float:
    """Convert '61 years 04 months' style strings to decimal years."""
    years, months = 0, 0
    parts = text.split()
    for i, part in enumerate(parts):
        if part.startswith("year"):
            years = int(parts[i - 1])
        elif part.startswith("month"):
            months = int(parts[i - 1])
    return round(years + months / 12, 2)


def storey_range_to_mid(storey_range: str) -> int:
    """Convert '10 TO 12' to its numeric midpoint, 11."""
    low, high = storey_range.split(" TO ")
    return (int(low) + int(high)) // 2


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out["remaining_lease_years"] = out["remaining_lease"].apply(remaining_lease_to_years)
    out["storey_mid"] = out["storey_range"].apply(storey_range_to_mid)
    out["transaction_year"] = out["month"].dt.year
    out["transaction_month"] = out["month"].dt.month
    out = add_mrt_distance(out)

    feature_cols = [
        "town",
        "flat_type",
        "floor_area_sqm",
        "storey_mid",
        "remaining_lease_years",
        "transaction_year",
        "transaction_month",
        "mrt_distance_km",
        "resale_price",
    ]
    out = out[feature_cols]

    out = pd.get_dummies(out, columns=["town", "flat_type"], drop_first=True)

    return out


def main():
    df = pd.read_csv(RAW_PATH)
    df["month"] = pd.to_datetime(df["month"], format="%Y-%m")

    features = build_features(df)

    print("Feature matrix shape:", features.shape)
    print("\nColumns:")
    print(list(features.columns))
    print("\nSample rows:")
    print(features.head())
    print("\nmrt_distance_km missing:", features["mrt_distance_km"].isna().sum())

    features.to_csv(PROCESSED_PATH, index=False)
    print(f"\nSaved processed features to {PROCESSED_PATH}")


if __name__ == "__main__":
    main()
