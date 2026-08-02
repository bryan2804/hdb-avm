from typing import Annotated

from fastapi import APIRouter, Depends

from hdb_avm.api.deps import get_db
from hdb_avm.api.schemas import MarketMover, MarketMoversResponse
from hdb_avm.db import Database

router = APIRouter(tags=["market-movers"])

# Year-over-year median price change per town, for the most recently complete
# year. Framed as a lender's view of collateral risk: towns at the top are
# appreciating (lower risk), towns at the bottom are depreciating (higher
# risk) — not just "which town got more expensive."
MARKET_MOVERS_SQL = """
    WITH yearly AS (
        SELECT town, year, median(resale_price) AS median_price
        FROM resale_transactions
        WHERE flat_type = ?
        GROUP BY town, year
    ),
    with_change AS (
        SELECT
            town, year, median_price,
            LAG(median_price) OVER (PARTITION BY town ORDER BY year) AS prior_price
        FROM yearly
    )
    SELECT town, median_price,
           ROUND((median_price - prior_price) / prior_price * 100, 1) AS yoy_change_pct
    FROM with_change
    WHERE year = (SELECT MAX(year) FROM yearly) AND prior_price IS NOT NULL
    ORDER BY yoy_change_pct DESC
"""


@router.get("/market-movers", response_model=MarketMoversResponse)
def market_movers(
    flat_type: str, db: Annotated[Database, Depends(get_db)]
) -> MarketMoversResponse:
    """Towns ranked by year-over-year median price change for a flat type."""
    rows = db.cursor().execute(MARKET_MOVERS_SQL, [flat_type.upper()]).fetchall()
    return MarketMoversResponse(
        flat_type=flat_type.upper(),
        movers=[
            MarketMover(town=town, median_price=float(price), yoy_change_pct=float(pct))
            for town, price, pct in rows
        ],
    )
