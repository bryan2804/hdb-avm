"""Tests for the DuckDB analytics layer: the built artifact's shape, the live
trends query, and the market-movers window-function query (checked against
a synthetic fixture so the math doesn't depend on real-world data)."""

import duckdb
import pytest

from hdb_avm.api.routers.market_movers import MARKET_MOVERS_SQL
from hdb_avm.api.routers.trends import _TRENDS_SQL
from hdb_avm.config import get_settings
from hdb_avm.db import Database


@pytest.fixture(scope="module")
def db():
    return Database.load(get_settings())


def test_resale_transactions_table_shape(db):
    cols = {row[0] for row in db.cursor().execute("DESCRIBE resale_transactions").fetchall()}
    assert {"town", "flat_type", "resale_price", "year", "quarter", "period"} <= cols
    n = db.cursor().execute("SELECT COUNT(*) FROM resale_transactions").fetchone()[0]
    assert n > 100_000


def test_trends_query_returns_well_formed_periods(db):
    rows = db.cursor().execute(_TRENDS_SQL, ["BEDOK", "4 ROOM"]).fetchall()
    assert len(rows) > 10
    periods = [period for period, _ in rows]
    assert periods == sorted(periods)  # ORDER BY period actually orders
    assert all(len(p) == 7 and p[4:6] == "-Q" for p in periods)  # e.g. "2017-Q1"


def test_trends_query_empty_for_unknown_combination(db):
    rows = db.cursor().execute(_TRENDS_SQL, ["BEDOK", "MULTI-GENERATION"]).fetchall()
    assert rows == []


def _synthetic_db(tmp_path, rows: list[tuple]) -> duckdb.DuckDBPyConnection:
    con = duckdb.connect(str(tmp_path / "synthetic.duckdb"))
    con.execute(
        "CREATE TABLE resale_transactions "
        "(town VARCHAR, flat_type VARCHAR, resale_price DOUBLE, year INTEGER, "
        "quarter INTEGER, period VARCHAR)"
    )
    con.executemany("INSERT INTO resale_transactions VALUES (?, ?, ?, ?, 1, ?)", rows)
    return con


def test_market_movers_yoy_math(tmp_path):
    """Hand-computed YoY check for the LAG window function, independent of
    real data: TESTVILLE goes 400,000 -> 440,000 (+10%), CONTROLTOWN has only
    one year of history so it must be excluded (no prior year to compare)."""
    con = _synthetic_db(
        tmp_path,
        [
            ("TESTVILLE", "4 ROOM", 400_000, 2023, "2023-Q1"),
            ("TESTVILLE", "4 ROOM", 440_000, 2024, "2024-Q1"),
            ("CONTROLTOWN", "4 ROOM", 500_000, 2024, "2024-Q1"),
        ],
    )
    rows = con.execute(MARKET_MOVERS_SQL, ["4 ROOM"]).fetchall()
    assert rows == [("TESTVILLE", 440_000.0, 10.0)]


def test_market_movers_ranks_descending_by_change(tmp_path):
    con = _synthetic_db(
        tmp_path,
        [
            ("RISING", "4 ROOM", 100_000, 2023, "2023-Q1"),
            ("RISING", "4 ROOM", 120_000, 2024, "2024-Q1"),  # +20%
            ("FALLING", "4 ROOM", 100_000, 2023, "2023-Q1"),
            ("FALLING", "4 ROOM", 90_000, 2024, "2024-Q1"),  # -10%
        ],
    )
    rows = con.execute(MARKET_MOVERS_SQL, ["4 ROOM"]).fetchall()
    assert [town for town, _, _ in rows] == ["RISING", "FALLING"]
