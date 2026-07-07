from typing import Annotated

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from hdb_avm.api.deps import get_trends
from hdb_avm.api.schemas import TrendPoint, TrendsResponse

router = APIRouter(tags=["trends"])


@router.get("/trends", response_model=TrendsResponse)
def trends(
    town: str,
    flat_type: str,
    trends_df: Annotated[pd.DataFrame, Depends(get_trends)],
) -> TrendsResponse:
    """Quarterly median resale price history for a town + flat type."""
    subset = trends_df[
        (trends_df["town"] == town.upper()) & (trends_df["flat_type"] == flat_type.upper())
    ].sort_values("period")
    if subset.empty:
        raise HTTPException(
            status_code=404, detail=f"No trend data for {flat_type!r} in {town!r}."
        )
    prices = subset["resale_price"]
    first, last = float(prices.iloc[0]), float(prices.iloc[-1])
    return TrendsResponse(
        town=town.upper(),
        flat_type=flat_type.upper(),
        points=[
            TrendPoint(period=r.period, median_price=float(r.resale_price))
            for r in subset.itertuples()
        ],
        change_pct=round((last - first) / first * 100, 1) if first else None,
    )
