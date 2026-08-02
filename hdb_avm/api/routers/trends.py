from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from hdb_avm.api.deps import get_db
from hdb_avm.api.schemas import TrendPoint, TrendsResponse
from hdb_avm.db import Database

router = APIRouter(tags=["trends"])

_TRENDS_SQL = """
    SELECT period, median(resale_price) AS median_price
    FROM resale_transactions
    WHERE town = ? AND flat_type = ?
    GROUP BY period
    ORDER BY period
"""


@router.get("/trends", response_model=TrendsResponse)
def trends(town: str, flat_type: str, db: Annotated[Database, Depends(get_db)]) -> TrendsResponse:
    """Quarterly median resale price history for a town + flat type."""
    rows = db.cursor().execute(_TRENDS_SQL, [town.upper(), flat_type.upper()]).fetchall()
    if not rows:
        raise HTTPException(
            status_code=404, detail=f"No trend data for {flat_type!r} in {town!r}."
        )
    points = [TrendPoint(period=period, median_price=float(price)) for period, price in rows]
    first, last = points[0].median_price, points[-1].median_price
    return TrendsResponse(
        town=town.upper(),
        flat_type=flat_type.upper(),
        points=points,
        change_pct=round((last - first) / first * 100, 1) if first else None,
    )
