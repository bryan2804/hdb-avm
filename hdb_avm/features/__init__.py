"""Shared feature engineering used by BOTH training and serving.

This package is the single source of truth for how raw flat attributes become
model features. Training (``hdb_avm.features.pipeline``) and the API serving
layer (``hdb_avm.features.encoding``) import the same parsers and geo helpers,
eliminating training/serving skew.
"""

from hdb_avm.features.encoding import FeatureEncoder
from hdb_avm.features.geo import haversine_km, load_mrt_stations, nearest_station
from hdb_avm.features.parsing import remaining_lease_to_years, storey_range_to_mid

__all__ = [
    "FeatureEncoder",
    "haversine_km",
    "load_mrt_stations",
    "nearest_station",
    "remaining_lease_to_years",
    "storey_range_to_mid",
]
