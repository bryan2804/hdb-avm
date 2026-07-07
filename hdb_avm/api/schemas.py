"""Pydantic request/response schemas for the public API."""

from datetime import date

from pydantic import BaseModel, Field, model_validator


class ValuationRequest(BaseModel):
    """Attributes of the flat to value.

    Location can be given three ways, in order of precision:
      1. ``address``           — geocoded live via OneMap (block-level)
      2. ``latitude/longitude``— explicit coordinates
      3. neither               — falls back to the town centroid

    ``mrt_distance_km`` is computed from the resolved coordinates when not
    supplied explicitly.
    """

    town: str = Field(examples=["BEDOK"])
    flat_type: str = Field(examples=["4 ROOM"])
    floor_area_sqm: float = Field(gt=20, lt=350)
    storey: int = Field(ge=1, le=60)
    remaining_lease_years: float = Field(gt=0, le=99)
    address: str | None = Field(default=None, examples=["406 ANG MO KIO AVE 10"])
    latitude: float | None = Field(default=None, ge=1.1, le=1.5)
    longitude: float | None = Field(default=None, ge=103.6, le=104.1)
    mrt_distance_km: float | None = Field(default=None, ge=0, le=15)

    @model_validator(mode="after")
    def coordinates_come_in_pairs(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be provided together")
        return self


class ResolvedLocation(BaseModel):
    coordinate_source: str  # "address" | "explicit" | "town_centroid"
    latitude: float
    longitude: float
    mrt_distance_km: float
    nearest_mrt: str | None = None
    matched_address: str | None = None


class ContributionOut(BaseModel):
    feature: str
    label: str
    amount: float


class Explanation(BaseModel):
    baseline: float = Field(description="Model expected value: the average-flat starting point")
    contributions: list[ContributionOut]


class ValuationResponse(BaseModel):
    point_estimate: float
    band_low: float
    band_high: float
    rmse: int
    rmse_scope: str
    mispricing_exposure_pct: float
    valuation_date: date
    resolved_location: ResolvedLocation
    explanation: Explanation


class TrendPoint(BaseModel):
    period: str
    median_price: float


class TrendsResponse(BaseModel):
    town: str
    flat_type: str
    points: list[TrendPoint]
    change_pct: float | None = Field(
        default=None, description="Percent change from first to last period"
    )


class Metadata(BaseModel):
    towns: list[str]
    flat_types: list[str]
    model_version: str
    trained_at: str | None
    rmse: int
    r2: float | None
