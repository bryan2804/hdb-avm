"""Async client for the OneMap geocoding API (data.gov.sg's national geocoder)."""

from dataclasses import dataclass

import httpx

from hdb_avm.config import get_settings


@dataclass(frozen=True)
class GeocodeResult:
    latitude: float
    longitude: float
    matched_address: str


class OneMapError(Exception):
    """Upstream geocoding service failed (network / non-2xx / bad payload)."""


async def geocode(address: str) -> GeocodeResult | None:
    """Geocode an address. Returns None when the address has no matches.

    Raises OneMapError on upstream failure so callers can distinguish
    'not found' (client's problem) from 'OneMap is down' (not their problem).
    """
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=settings.onemap_timeout_seconds) as client:
            resp = await client.get(
                settings.onemap_search_url,
                params={
                    "searchVal": address,
                    "returnGeom": "Y",
                    "getAddrDetails": "Y",
                    "pageNum": 1,
                },
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])
    except httpx.HTTPError as exc:
        raise OneMapError(f"OneMap request failed: {exc}") from exc

    if not results:
        return None
    top = results[0]
    try:
        return GeocodeResult(
            latitude=float(top["LATITUDE"]),
            longitude=float(top["LONGITUDE"]),
            matched_address=top.get("ADDRESS", address),
        )
    except (KeyError, ValueError) as exc:
        raise OneMapError(f"Unexpected OneMap payload: {exc}") from exc
