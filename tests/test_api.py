"""End-to-end API tests over the real artifacts (no network calls —
address-based flows are covered by mocking the OneMap client)."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from hdb_avm.api.main import create_app
from hdb_avm.api.onemap import GeocodeResult, OneMapError

VALID_BODY = {
    "town": "BEDOK",
    "flat_type": "4 ROOM",
    "floor_area_sqm": 95,
    "storey": 8,
    "remaining_lease_years": 70.5,
}


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app()) as c:
        yield c


# ── /valuations ───────────────────────────────────────────────────────────────

def test_valuation_town_only(client):
    resp = client.post("/api/v1/valuations", json=VALID_BODY)
    assert resp.status_code == 200
    body = resp.json()
    assert 300_000 < body["point_estimate"] < 1_500_000
    assert body["band_low"] < body["point_estimate"] < body["band_high"]
    assert body["rmse_scope"] == "town"
    loc = body["resolved_location"]
    assert loc["coordinate_source"] == "town_centroid"
    assert loc["nearest_mrt"] is not None  # MRT distance computed from centroid
    assert len(body["explanation"]["contributions"]) == 8


def test_valuation_with_explicit_coordinates(client):
    body = {**VALID_BODY, "latitude": 1.3078, "longitude": 103.9310}
    resp = client.post("/api/v1/valuations", json=body)
    assert resp.status_code == 200
    assert resp.json()["resolved_location"]["coordinate_source"] == "explicit"


def test_valuation_respects_supplied_mrt_distance(client):
    resp = client.post("/api/v1/valuations", json={**VALID_BODY, "mrt_distance_km": 2.5})
    assert resp.status_code == 200
    loc = resp.json()["resolved_location"]
    assert loc["mrt_distance_km"] == 2.5
    assert loc["nearest_mrt"] is None  # not computed when caller supplied distance


def test_valuation_unknown_town_is_422(client):
    resp = client.post("/api/v1/valuations", json={**VALID_BODY, "town": "TENGAH"})
    assert resp.status_code == 422
    assert "Unknown town" in resp.json()["detail"]


def test_valuation_lat_without_lon_is_422(client):
    resp = client.post("/api/v1/valuations", json={**VALID_BODY, "latitude": 1.33})
    assert resp.status_code == 422


def test_valuation_address_flow_mocked(client):
    geo = GeocodeResult(
        latitude=1.3625, longitude=103.8547, matched_address="406 ANG MO KIO AVE 10"
    )
    with patch("hdb_avm.api.routers.valuations.onemap.geocode", new=AsyncMock(return_value=geo)):
        resp = client.post(
            "/api/v1/valuations",
            json={**VALID_BODY, "town": "ANG MO KIO", "address": "406 ANG MO KIO AVE 10"},
        )
    assert resp.status_code == 200
    loc = resp.json()["resolved_location"]
    assert loc["coordinate_source"] == "address"
    assert loc["matched_address"] == "406 ANG MO KIO AVE 10"


def test_valuation_address_not_found_is_404(client):
    with patch("hdb_avm.api.routers.valuations.onemap.geocode", new=AsyncMock(return_value=None)):
        resp = client.post("/api/v1/valuations", json={**VALID_BODY, "address": "NOWHERE 999"})
    assert resp.status_code == 404


def test_valuation_onemap_down_is_502(client):
    with patch(
        "hdb_avm.api.routers.valuations.onemap.geocode",
        new=AsyncMock(side_effect=OneMapError("boom")),
    ):
        resp = client.post("/api/v1/valuations", json={**VALID_BODY, "address": "406 AMK"})
    assert resp.status_code == 502


# ── /metadata, /metrics, /trends ─────────────────────────────────────────────

def test_metadata(client):
    resp = client.get("/api/v1/metadata")
    assert resp.status_code == 200
    body = resp.json()
    assert "BEDOK" in body["towns"]
    assert "4 ROOM" in body["flat_types"]
    assert body["rmse"] > 0


def test_metrics_exposes_town_rmse(client):
    resp = client.get("/api/v1/metrics")
    assert resp.status_code == 200
    assert "town_rmse" in resp.json()


def test_trends_happy_path(client):
    resp = client.get("/api/v1/trends", params={"town": "bedok", "flat_type": "4 room"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["town"] == "BEDOK"
    assert len(body["points"]) > 10
    assert body["change_pct"] is not None


def test_trends_unknown_combination_is_404(client):
    resp = client.get("/api/v1/trends", params={"town": "BEDOK", "flat_type": "MULTI-GENERATION"})
    assert resp.status_code == 404


def test_market_movers_happy_path(client):
    resp = client.get("/api/v1/market-movers", params={"flat_type": "4 room"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["flat_type"] == "4 ROOM"
    assert len(body["movers"]) > 10
    towns = {m["town"] for m in body["movers"]}
    assert "BEDOK" in towns
    # Ranked descending by YoY change
    changes = [m["yoy_change_pct"] for m in body["movers"]]
    assert changes == sorted(changes, reverse=True)
