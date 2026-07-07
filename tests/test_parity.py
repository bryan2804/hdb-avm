"""Parity with the legacy Streamlit app.

Two guarantees:
1. Encoding parity (artifact-independent): FeatureEncoder reproduces the
   legacy ``make_input`` frame exactly, so the migration cannot have changed
   what the model sees for identical inputs.
2. Golden predictions (artifact-pinned): known outputs of the deployed model
   generation. These auto-skip after a retrain produces a new artifact —
   re-record the values when that happens.
"""

import json
from datetime import date

import joblib
import pandas as pd
import pytest

from hdb_avm.features.encoding import FeatureEncoder

GOLDEN_TRAINED_AT = "2026-06-29"
# Recorded from the deployed model generation (see GOLDEN_TRAINED_AT):
# BEDOK 4 ROOM, 95sqm, storey 8, lease 70.5y, MRT 0.4km, valuation 2025-06
GOLDEN_LEGACY_TOWN_MODE = 666_902.5  # lat/lon = 0, as the Streamlit app encodes it


@pytest.fixture(scope="module")
def feature_columns():
    with open("models/feature_columns.json") as f:
        return json.load(f)


def legacy_make_input(
    feature_columns, town, flat_type, floor_area, storey, lease, mrt_dist, lat=None, lon=None
):
    """Verbatim copy of app/main.py::make_input (the legacy encoder)."""
    d = {col: 0 for col in feature_columns}
    d["floor_area_sqm"] = floor_area
    d["storey_mid"] = storey
    d["remaining_lease_years"] = lease
    d["transaction_year"] = 2025
    d["transaction_month"] = 6
    d["mrt_distance_km"] = mrt_dist
    if "latitude" in d and lat is not None:
        d["latitude"] = lat
        d["longitude"] = lon
    if f"town_{town}" in d:
        d[f"town_{town}"] = 1
    if f"flat_type_{flat_type}" in d:
        d[f"flat_type_{flat_type}"] = 1
    return pd.DataFrame([d])[feature_columns]


CASES = [
    dict(town="BEDOK", flat_type="4 ROOM", floor_area=95, storey=8, lease=70.5, mrt=0.4),
    dict(town="QUEENSTOWN", flat_type="3 ROOM", floor_area=68, storey=12, lease=55.0, mrt=0.7),
    dict(town="PUNGGOL", flat_type="5 ROOM", floor_area=112, storey=15, lease=92.0, mrt=1.2),
    dict(
        town="ANG MO KIO", flat_type="EXECUTIVE", floor_area=145, storey=3, lease=61.33,
        mrt=0.25, lat=1.3625, lon=103.8547,
    ),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["town"])
def test_encoding_matches_legacy_make_input(feature_columns, case):
    encoder = FeatureEncoder(feature_columns)  # no centroids → legacy 0.0 fallback
    legacy = legacy_make_input(
        feature_columns,
        case["town"],
        case["flat_type"],
        case["floor_area"],
        case["storey"],
        case["lease"],
        case["mrt"],
        lat=case.get("lat"),
        lon=case.get("lon"),
    )
    new = encoder.encode(
        town=case["town"],
        flat_type=case["flat_type"],
        floor_area_sqm=case["floor_area"],
        storey_mid=case["storey"],
        remaining_lease_years=case["lease"],
        mrt_distance_km=case["mrt"],
        latitude=case.get("lat"),
        longitude=case.get("lon"),
        as_of=date(2025, 6, 1),
    )
    pd.testing.assert_frame_equal(new, legacy, check_dtype=False)


def test_golden_prediction_matches_deployed_model(feature_columns):
    with open("models/metrics.json") as f:
        trained_at = json.load(f).get("trained_at")
    if trained_at != GOLDEN_TRAINED_AT:
        pytest.skip(
            f"Golden values recorded for model trained {GOLDEN_TRAINED_AT}, "
            f"current artifact is {trained_at} — re-record after retrain."
        )
    model = joblib.load("models/xgboost.joblib")
    encoder = FeatureEncoder(feature_columns)
    features = encoder.encode(
        town="BEDOK",
        flat_type="4 ROOM",
        floor_area_sqm=95,
        storey_mid=8,
        remaining_lease_years=70.5,
        mrt_distance_km=0.4,
        as_of=date(2025, 6, 1),
    )
    assert float(model.predict(features)[0]) == pytest.approx(
        GOLDEN_LEGACY_TOWN_MODE, rel=1e-4
    )
