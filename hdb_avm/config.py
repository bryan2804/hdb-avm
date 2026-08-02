"""Application configuration.

All settings can be overridden via environment variables prefixed with ``HDB_``,
e.g. ``HDB_MODEL_DIR=/opt/models``. Paths default to the repository layout so the
API runs from a repo checkout with zero configuration.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HDB_", env_file=".env", extra="ignore")

    # Artifact locations
    model_dir: Path = REPO_ROOT / "models"
    data_dir: Path = REPO_ROOT / "data"

    # External services
    onemap_search_url: str = "https://www.onemap.gov.sg/api/common/elastic/search"
    onemap_timeout_seconds: float = 8.0

    # API behaviour
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    @property
    def xgboost_path(self) -> Path:
        return self.model_dir / "xgboost.joblib"

    @property
    def feature_columns_path(self) -> Path:
        return self.model_dir / "feature_columns.json"

    @property
    def metrics_path(self) -> Path:
        return self.model_dir / "metrics.json"

    @property
    def mrt_coords_path(self) -> Path:
        return self.data_dir / "mrt_station_coords.csv"

    @property
    def duckdb_path(self) -> Path:
        return self.model_dir / "hdb_avm.duckdb"


@lru_cache
def get_settings() -> Settings:
    return Settings()
