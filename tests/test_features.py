import json

import numpy as np
import pandas as pd
import pytest

from hdb_avm.features.encoding import FeatureEncoder
from hdb_avm.features.geo import haversine_km, nearest_station
from hdb_avm.features.parsing import remaining_lease_to_years, storey_range_to_mid

FEATURE_COLUMNS_PATH = "models/feature_columns.json"


# ── Parsing ───────────────────────────────────────────────────────────────────

def test_remaining_lease_years_and_months():
    assert remaining_lease_to_years("61 years 04 months") == pytest.approx(61.33)
    assert remaining_lease_to_years("99 years") == 99.0
    assert remaining_lease_to_years("70") == 0.0  # malformed → 0, matches training


def test_storey_range_to_mid():
    assert storey_range_to_mid("10 TO 12") == 11
    assert storey_range_to_mid("01 TO 03") == 2
    assert storey_range_to_mid("7") == 7
    assert storey_range_to_mid("") == 0


# ── Geo ───────────────────────────────────────────────────────────────────────

def test_haversine_known_distance():
    # Raffles Place (1.2840, 103.8515) to Jurong East (1.3330, 103.7422) ≈ 13.3 km
    d = haversine_km(1.2840, 103.8515, np.array([1.3330]), np.array([103.7422]))
    assert d[0] == pytest.approx(13.3, abs=0.5)


def test_nearest_station_picks_minimum():
    stations = pd.DataFrame(
        {
            "station_name": ["FAR", "NEAR"],
            "latitude": [1.40, 1.30],
            "longitude": [103.90, 103.80],
        }
    )
    dist, name = nearest_station(1.301, 103.801, stations)
    assert name == "NEAR"
    assert dist < 1.0


# ── Encoding ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def encoder() -> FeatureEncoder:
    with open(FEATURE_COLUMNS_PATH) as f:
        return FeatureEncoder(json.load(f))


def test_encoder_derives_categories_from_artifact(encoder):
    assert "ANG MO KIO" in encoder.towns
    assert "MULTI-GENERATION" in encoder.flat_types
    assert len(encoder.towns) == 26
    assert len(encoder.flat_types) == 7


def test_encode_column_order_matches_model(encoder):
    row = encoder.encode(
        town="BEDOK",
        flat_type="4 ROOM",
        floor_area_sqm=95,
        storey_mid=8,
        remaining_lease_years=70.5,
        mrt_distance_km=0.4,
    )
    assert list(row.columns) == encoder.feature_columns
    assert row.shape == (1, len(encoder.feature_columns))


def test_encode_one_hot_correctness(encoder):
    row = encoder.encode(
        town="BEDOK",
        flat_type="4 ROOM",
        floor_area_sqm=95,
        storey_mid=8,
        remaining_lease_years=70.5,
        mrt_distance_km=0.4,
    )
    town_cols = [c for c in row.columns if c.startswith("town_")]
    assert row[town_cols].values.sum() == 1
    assert row["town_BEDOK"].iloc[0] == 1
    assert row["flat_type_4 ROOM"].iloc[0] == 1
    assert row["floor_area_sqm"].iloc[0] == 95


def test_encode_rejects_unknown_categories(encoder):
    with pytest.raises(ValueError, match="Unknown town"):
        encoder.encode(
            town="TENGAH",  # not in training data — must fail loudly, not extrapolate
            flat_type="4 ROOM",
            floor_area_sqm=95,
            storey_mid=8,
            remaining_lease_years=70.5,
            mrt_distance_km=0.4,
        )
    with pytest.raises(ValueError, match="Unknown flat type"):
        encoder.encode(
            town="BEDOK",
            flat_type="10 ROOM",
            floor_area_sqm=95,
            storey_mid=8,
            remaining_lease_years=70.5,
            mrt_distance_km=0.4,
        )


def test_encode_centroid_imputation():
    with open(FEATURE_COLUMNS_PATH) as f:
        cols = json.load(f)
    enc = FeatureEncoder(cols, town_centroids={"BEDOK": (1.324, 103.93)})
    row = enc.encode(
        town="BEDOK",
        flat_type="4 ROOM",
        floor_area_sqm=95,
        storey_mid=8,
        remaining_lease_years=70.5,
        mrt_distance_km=0.4,
    )
    assert row["latitude"].iloc[0] == pytest.approx(1.324)
    # Explicit coordinates take precedence over the centroid
    row2 = enc.encode(
        town="BEDOK",
        flat_type="4 ROOM",
        floor_area_sqm=95,
        storey_mid=8,
        remaining_lease_years=70.5,
        mrt_distance_km=0.4,
        latitude=1.35,
        longitude=103.94,
    )
    assert row2["latitude"].iloc[0] == pytest.approx(1.35)
