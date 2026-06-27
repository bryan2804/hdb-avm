"""
Compute, for every HDB block, the haversine distance (km) to the nearest
MRT/LRT station. Merges into the feature set built by features.py.

45 of 9,714 block addresses (~0.5%) failed OneMap geocoding -- mostly
addresses using abbreviated street names (e.g. "BT BATOK", "NTH RD")
that don't match OneMap's indexed building names. Their mrt_distance_km
is left as NaN; see main() for the exact list logged at runtime.
"""

import numpy as np
import pandas as pd

from geocode import load_cache

STATION_COORDS_PATH = "data/mrt_station_coords.csv"
BLOCK_COORDS_PATH = "data/block_coords.csv"

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def nearest_station_distances(block_latlons: np.ndarray, station_latlons: np.ndarray) -> np.ndarray:
    """block_latlons: (n_blocks, 2), station_latlons: (n_stations, 2) -> (n_blocks,) min distance."""
    blk_lat = block_latlons[:, 0:1]
    blk_lon = block_latlons[:, 1:2]
    sta_lat = station_latlons[None, :, 0]
    sta_lon = station_latlons[None, :, 1]
    dists = haversine_km(blk_lat, blk_lon, sta_lat, sta_lon)
    return dists.min(axis=1)


def add_mrt_distance(df: pd.DataFrame) -> pd.DataFrame:
    """df must have 'block' and 'street_name' columns. Adds mrt_distance_km."""
    station_cache = load_cache(STATION_COORDS_PATH)
    station_latlons = np.array([v for v in station_cache.values() if v is not None])

    block_cache = load_cache(BLOCK_COORDS_PATH)

    addr = df["block"] + " " + df["street_name"]
    unique_addrs = addr.unique()

    addr_to_dist = {}
    for a in unique_addrs:
        coords = block_cache.get(a)
        addr_to_dist[a] = None if coords is None else coords

    valid_addrs = [a for a, c in addr_to_dist.items() if c is not None]
    valid_latlons = np.array([addr_to_dist[a] for a in valid_addrs])
    valid_dists = nearest_station_distances(valid_latlons, station_latlons)
    addr_to_dist_km = dict(zip(valid_addrs, valid_dists))

    df = df.copy()
    df["mrt_distance_km"] = addr.map(addr_to_dist_km).round(3)
    return df
