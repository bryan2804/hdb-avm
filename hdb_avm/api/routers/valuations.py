from functools import partial
from typing import Annotated

import anyio.to_thread
from fastapi import APIRouter, Depends, HTTPException

from hdb_avm.api import onemap
from hdb_avm.api.deps import get_registry, get_service
from hdb_avm.api.schemas import (
    ContributionOut,
    Explanation,
    ResolvedLocation,
    ValuationRequest,
    ValuationResponse,
)
from hdb_avm.features.geo import nearest_station
from hdb_avm.ml.registry import ModelRegistry
from hdb_avm.ml.service import ValuationService

router = APIRouter(tags=["valuations"])


async def _resolve_location(
    req: ValuationRequest, registry: ModelRegistry
) -> ResolvedLocation:
    matched_address = None

    if req.address:
        try:
            geo = await onemap.geocode(req.address)
        except onemap.OneMapError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        if geo is None:
            raise HTTPException(
                status_code=404,
                detail=f"Address not found: {req.address!r}. "
                "Use format 'BLOCK STREET NAME', e.g. '406 ANG MO KIO AVE 10'.",
            )
        source = "address"
        lat, lon = geo.latitude, geo.longitude
        matched_address = geo.matched_address
    elif req.latitude is not None and req.longitude is not None:
        source = "explicit"
        lat, lon = req.latitude, req.longitude
    else:
        centroid = registry.encoder.town_centroids.get(req.town)
        if centroid is None:
            raise HTTPException(
                status_code=422,
                detail=f"No centroid for town {req.town!r}; "
                "provide an address or coordinates.",
            )
        source = "town_centroid"
        lat, lon = centroid

    nearest_mrt = None
    mrt_km = req.mrt_distance_km
    if mrt_km is None:
        mrt_km, nearest_mrt = nearest_station(lat, lon, registry.mrt_stations)
        mrt_km = round(mrt_km, 3)

    return ResolvedLocation(
        coordinate_source=source,
        latitude=lat,
        longitude=lon,
        mrt_distance_km=mrt_km,
        nearest_mrt=nearest_mrt,
        matched_address=matched_address,
    )


@router.post("/valuations", response_model=ValuationResponse)
async def create_valuation(
    req: ValuationRequest,
    service: Annotated[ValuationService, Depends(get_service)],
    registry: Annotated[ModelRegistry, Depends(get_registry)],
) -> ValuationResponse:
    """Value a flat: point estimate, town-level confidence band, and an exact
    TreeSHAP breakdown of what drove the price."""
    if req.town not in registry.encoder.towns:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown town {req.town!r}. Valid towns: {registry.encoder.towns}",
        )
    if req.flat_type not in registry.encoder.flat_types:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown flat type {req.flat_type!r}. "
            f"Valid types: {registry.encoder.flat_types}",
        )

    location = await _resolve_location(req, registry)
    # Model inference is CPU-bound; run it in the threadpool so it never
    # blocks the event loop while other requests are being handled.
    valuation = await anyio.to_thread.run_sync(
        partial(
            service.value_flat,
            town=req.town,
            flat_type=req.flat_type,
            floor_area_sqm=req.floor_area_sqm,
            storey_mid=req.storey,
            remaining_lease_years=req.remaining_lease_years,
            mrt_distance_km=location.mrt_distance_km,
            latitude=location.latitude,
            longitude=location.longitude,
        )
    )
    return ValuationResponse(
        point_estimate=round(valuation.point_estimate),
        band_low=round(valuation.band_low),
        band_high=round(valuation.band_high),
        rmse=valuation.rmse,
        rmse_scope=valuation.rmse_scope,
        mispricing_exposure_pct=valuation.mispricing_exposure_pct,
        valuation_date=valuation.valuation_date,
        resolved_location=location,
        explanation=Explanation(
            baseline=round(valuation.baseline),
            contributions=[
                ContributionOut(feature=c.feature, label=c.label, amount=c.amount)
                for c in valuation.contributions
            ],
        ),
    )
