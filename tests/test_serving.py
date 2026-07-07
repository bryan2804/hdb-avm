"""Serving-layer tests against the real committed artifacts."""

from datetime import date

import pytest

from hdb_avm.config import Settings
from hdb_avm.ml.registry import ModelRegistry
from hdb_avm.ml.service import ValuationService

VALUATION_DATE = date(2025, 6, 1)  # pinned so tests don't drift with the clock


@pytest.fixture(scope="module")
def registry() -> ModelRegistry:
    return ModelRegistry.load(Settings())


@pytest.fixture(scope="module")
def service(registry) -> ValuationService:
    return ValuationService(registry)


def _bedok_valuation(service, **overrides):
    kwargs = dict(
        town="BEDOK",
        flat_type="4 ROOM",
        floor_area_sqm=95,
        storey_mid=8,
        remaining_lease_years=70.5,
        mrt_distance_km=0.4,
        as_of=VALUATION_DATE,
    )
    kwargs.update(overrides)
    return service.value_flat(**kwargs)


def test_valuation_is_plausible(service):
    v = _bedok_valuation(service)
    # A mid-floor Bedok 4-room should land well within this range in any
    # plausibly retrained model; the test survives monthly retrains.
    assert 300_000 < v.point_estimate < 1_500_000
    assert v.band_low < v.point_estimate < v.band_high
    assert v.rmse_scope == "town"
    assert 0 < v.mispricing_exposure_pct < 50


def test_town_rmse_fallback_to_global(registry):
    rmse, scope = registry.town_rmse("NOT A TOWN")
    assert scope == "global"
    assert rmse == registry.metrics["default_rmse"]


def test_contributions_reconcile_with_estimate(service, registry):
    n_features = len(registry.encoder.feature_columns)
    v = _bedok_valuation(service, top_k=n_features)
    reconstructed = v.baseline + sum(c.amount for c in v.contributions)
    # Exact TreeSHAP: baseline + all contributions == prediction (float32 + rounding)
    assert reconstructed == pytest.approx(v.point_estimate, abs=n_features)


def test_explicit_coordinates_change_estimate(service):
    v_centroid = _bedok_valuation(service)
    v_east_coast = _bedok_valuation(service, latitude=1.3078, longitude=103.9310)
    assert v_centroid.point_estimate != v_east_coast.point_estimate


def test_bigger_flat_is_worth_more(service):
    small = _bedok_valuation(service, floor_area_sqm=70)
    large = _bedok_valuation(service, floor_area_sqm=120)
    assert large.point_estimate > small.point_estimate
