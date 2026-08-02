"""SQL analytics layer: a read-only DuckDB connection over the
``resale_transactions`` artifact built by ``hdb_avm.training.build_duckdb``.
"""

from dataclasses import dataclass

import duckdb

from hdb_avm.config import Settings, get_settings


@dataclass(frozen=True)
class Database:
    conn: duckdb.DuckDBPyConnection

    @classmethod
    def load(cls, settings: Settings | None = None) -> "Database":
        settings = settings or get_settings()
        return cls(conn=duckdb.connect(str(settings.duckdb_path), read_only=True))

    def cursor(self) -> duckdb.DuckDBPyConnection:
        """A cheap per-request handle onto the same database. DuckDB allows
        unlimited concurrent readers with no locking; a fresh cursor per
        request just keeps each query's session state isolated."""
        return self.conn.cursor()
