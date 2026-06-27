"""
First-pass exploration of the HDB resale flat prices dataset.
Run this before any modeling to sanity-check the data and spot issues
(missing values, sparse towns, lease format, outliers) that will
otherwise bite later in feature engineering.
"""

import pandas as pd

DATA_PATH = "data/resale-flat-prices.csv"


def load_data(path: str = DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["month"] = pd.to_datetime(df["month"], format="%Y-%m")
    return df


def remaining_lease_to_months(text: str) -> int:
    """Convert '61 years 04 months' style strings to total months."""
    years, months = 0, 0
    parts = text.split()
    for i, part in enumerate(parts):
        if part == "years":
            years = int(parts[i - 1])
        elif part == "months":
            months = int(parts[i - 1])
    return years * 12 + months


def main():
    df = load_data()

    print("=" * 60)
    print("SHAPE & DTYPES")
    print("=" * 60)
    print(df.shape)
    print(df.dtypes)

    print("\n" + "=" * 60)
    print("MISSING VALUES")
    print("=" * 60)
    print(df.isna().sum())

    print("\n" + "=" * 60)
    print("DATE RANGE")
    print("=" * 60)
    print(df["month"].min(), "to", df["month"].max())

    print("\n" + "=" * 60)
    print("RESALE PRICE SUMMARY")
    print("=" * 60)
    print(df["resale_price"].describe())

    print("\n" + "=" * 60)
    print("TRANSACTIONS PER TOWN (sparsity check)")
    print("=" * 60)
    town_counts = df["town"].value_counts()
    print(town_counts)
    print("\nTowns with fewer than 500 transactions (likely unreliable predictions):")
    print(town_counts[town_counts < 500])

    print("\n" + "=" * 60)
    print("FLAT TYPE COUNTS")
    print("=" * 60)
    print(df["flat_type"].value_counts())

    print("\n" + "=" * 60)
    print("REMAINING LEASE FORMAT CHECK")
    print("=" * 60)
    print(df["remaining_lease"].head())
    sample_months = df["remaining_lease"].head(5).apply(remaining_lease_to_months)
    print("Parsed to months (sample):")
    print(sample_months)

    print("\n" + "=" * 60)
    print("FLOOR AREA SUMMARY")
    print("=" * 60)
    print(df["floor_area_sqm"].describe())


if __name__ == "__main__":
    main()
