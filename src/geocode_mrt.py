"""Geocode every MRT/LRT station name to (lat, lon) via OneMap. Fast (~160 lookups)."""

from geocode import geocode_all
from mrt_stations import MRT_STATIONS, LRT_ONLY_STATIONS

OUT_PATH = "data/mrt_station_coords.csv"


def main():
    queries = [f"{name} MRT STATION" for name in MRT_STATIONS]
    queries += [f"{name} LRT STATION" for name in LRT_ONLY_STATIONS]

    cache = geocode_all(queries, OUT_PATH)

    missing = [q for q, v in cache.items() if v is None]
    print(f"\nDone. {len(cache) - len(missing)}/{len(cache)} resolved.")
    if missing:
        print("Unresolved (may need a manual fix in the CSV):")
        for q in missing:
            print(" -", q)


if __name__ == "__main__":
    main()
