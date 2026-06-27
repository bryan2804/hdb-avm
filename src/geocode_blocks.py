"""
Geocode every unique HDB block address in the dataset to (lat, lon) via
OneMap. ~9,700 unique addresses at ~0.5s/request -> roughly 80 minutes.
Resumable: re-running skips addresses already in data/block_coords.csv.
"""

import pandas as pd
from geocode import geocode_all

RAW_PATH = "data/resale-flat-prices.csv"
OUT_PATH = "data/block_coords.csv"


def main():
    df = pd.read_csv(RAW_PATH, usecols=["block", "street_name"])
    addresses = sorted((df["block"] + " " + df["street_name"]).unique())
    print(f"{len(addresses)} unique addresses to geocode")

    cache = geocode_all(addresses, OUT_PATH, log_every=200)

    missing = [q for q, v in cache.items() if v is None]
    print(f"\nDone. {len(cache) - len(missing)}/{len(cache)} resolved.")
    print(f"{len(missing)} unresolved.")


if __name__ == "__main__":
    main()
