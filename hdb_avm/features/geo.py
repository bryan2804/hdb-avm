"""Geospatial helpers: haversine distance and nearest-MRT lookup."""

from pathlib import Path

import numpy as np
import pandas as pd

EARTH_RADIUS_KM = 6371.0


def haversine_km(
    lat: float, lon: float, lats: np.ndarray, lons: np.ndarray
) -> np.ndarray:
    """Vectorised haversine distance (km) from one point to many."""
    lat_r, lon_r = np.radians(lat), np.radians(lon)
    lats_r, lons_r = np.radians(lats), np.radians(lons)
    dlat = lats_r - lat_r
    dlon = lons_r - lon_r
    a = np.sin(dlat / 2) ** 2 + np.cos(lat_r) * np.cos(lats_r) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def load_mrt_stations(path: str | Path) -> pd.DataFrame:
    """Load MRT station coordinates with normalised column names.

    Returns a DataFrame guaranteed to have ``latitude`` and ``longitude``
    columns; a station-name column is preserved if present in the source file.
    """
    mrt = pd.read_csv(path)
    mrt.columns = [c.lower() for c in mrt.columns]
    lat_col = next(c for c in mrt.columns if "lat" in c)
    lon_col = next(c for c in mrt.columns if "lon" in c)
    mrt = mrt.rename(columns={lat_col: "latitude", lon_col: "longitude"})

    # Whatever column is left holds the station name (source file calls it 'query')
    name_col = next((c for c in mrt.columns if c not in ("latitude", "longitude")), None)
    if name_col is not None:
        mrt = mrt.rename(columns={name_col: "station_name"})
        mrt["station_name"] = (
            mrt["station_name"].str.replace(r"\s+MRT STATION$", "", regex=True, case=False)
        )
    return mrt


def nearest_station(lat: float, lon: float, stations: pd.DataFrame) -> tuple[float, str]:
    """Return (distance_km, station_name) of the nearest MRT station."""
    dists = haversine_km(lat, lon, stations["latitude"].values, stations["longitude"].values)
    idx = int(np.argmin(dists))
    name_cols = [c for c in stations.columns if "name" in c.lower()]
    name = str(stations.iloc[idx][name_cols[0]]) if name_cols else "nearest MRT"
    return float(dists[idx]), name


def min_mrt_distance_km(lat: float, lon: float, stations: pd.DataFrame) -> float:
    """Distance in km from (lat, lon) to the nearest MRT station."""
    return float(
        np.min(haversine_km(lat, lon, stations["latitude"].values, stations["longitude"].values))
    )
