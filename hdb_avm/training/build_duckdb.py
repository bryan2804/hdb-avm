"""Build the DuckDB analytics artifact from the raw resale transactions.

Loads ``data/resale-flat-prices.csv`` (the tidy data.gov.sg export — town,
flat_type, month, resale_price, ...) into a ``resale_transactions`` table,
deriving year/quarter/period columns entirely in SQL. This is what the
``/trends`` and ``/market-movers`` endpoints query live; it replaces the old
``data/price_trends.csv``, which nothing in this repo actually generated.
"""

from pathlib import Path

import duckdb

RAW_CSV = "data/resale-flat-prices.csv"
OUTPUT_PATH = "models/hdb_avm.duckdb"

_BUILD_SQL = """
    CREATE TABLE resale_transactions AS
    SELECT
        town,
        flat_type,
        resale_price,
        CAST(substr(month, 1, 4) AS INTEGER) AS year,
        ((CAST(substr(month, 6, 2) AS INTEGER) - 1) // 3) + 1 AS quarter,
        substr(month, 1, 4) || '-Q' ||
            CAST(((CAST(substr(month, 6, 2) AS INTEGER) - 1) // 3) + 1 AS VARCHAR) AS period
    FROM read_csv_auto(?)
"""


def build(raw_csv: str | Path = RAW_CSV, output_path: str | Path = OUTPUT_PATH) -> int:
    output_path = Path(output_path)
    output_path.unlink(missing_ok=True)  # rebuild from scratch each run

    print(f"Loading {raw_csv} into {output_path}...")
    con = duckdb.connect(str(output_path))
    con.execute(_BUILD_SQL, [str(raw_csv)])
    con.execute("CREATE INDEX idx_town_flat_type ON resale_transactions (town, flat_type)")
    n = con.execute("SELECT COUNT(*) FROM resale_transactions").fetchone()[0]
    con.close()
    print(f"  {n:,} rows -> {output_path}")
    return n


if __name__ == "__main__":
    build()
