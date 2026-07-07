"""Single-observation feature encoding for serving.

``FeatureEncoder`` is driven entirely by ``feature_columns.json`` (the artifact
written at training time), so the valid towns, flat types, and column order can
never drift from what the model expects. This replaces the hand-maintained
constant lists and ``make_input`` helper in the legacy Streamlit app.
"""

import json
from datetime import date
from pathlib import Path

import pandas as pd

TOWN_PREFIX = "town_"
FLAT_TYPE_PREFIX = "flat_type_"


class FeatureEncoder:
    def __init__(
        self,
        feature_columns: list[str],
        town_centroids: dict[str, tuple[float, float]] | None = None,
    ):
        self.feature_columns = list(feature_columns)
        self.town_centroids = town_centroids or {}
        self.towns = sorted(
            c[len(TOWN_PREFIX) :] for c in self.feature_columns if c.startswith(TOWN_PREFIX)
        )
        self.flat_types = sorted(
            c[len(FLAT_TYPE_PREFIX) :]
            for c in self.feature_columns
            if c.startswith(FLAT_TYPE_PREFIX)
        )

    @classmethod
    def from_artifacts(cls, model_dir: str | Path) -> "FeatureEncoder":
        model_dir = Path(model_dir)
        with open(model_dir / "feature_columns.json") as f:
            feature_columns = json.load(f)
        centroids_path = model_dir / "town_centroids.json"
        town_centroids = None
        if centroids_path.exists():
            with open(centroids_path) as f:
                town_centroids = {k: tuple(v) for k, v in json.load(f).items()}
        return cls(feature_columns, town_centroids)

    def encode(
        self,
        *,
        town: str,
        flat_type: str,
        floor_area_sqm: float,
        storey_mid: int,
        remaining_lease_years: float,
        mrt_distance_km: float,
        latitude: float | None = None,
        longitude: float | None = None,
        as_of: date | None = None,
    ) -> pd.DataFrame:
        """Encode one flat into a single-row frame in exact model column order.

        If ``latitude``/``longitude`` are not supplied, the town centroid is
        used when available (computed at training time), falling back to 0.0
        (the legacy Streamlit behaviour). ``as_of`` sets the valuation date;
        it defaults to today so estimates don't silently go stale.
        """
        if town not in self.towns:
            raise ValueError(f"Unknown town {town!r}. Valid towns: {self.towns}")
        if flat_type not in self.flat_types:
            raise ValueError(f"Unknown flat type {flat_type!r}. Valid types: {self.flat_types}")

        as_of = as_of or date.today()
        if latitude is None or longitude is None:
            latitude, longitude = self.town_centroids.get(town, (0.0, 0.0))

        row = dict.fromkeys(self.feature_columns, 0)
        row.update(
            floor_area_sqm=floor_area_sqm,
            storey_mid=storey_mid,
            remaining_lease_years=remaining_lease_years,
            transaction_year=as_of.year,
            transaction_month=as_of.month,
            latitude=latitude,
            longitude=longitude,
            mrt_distance_km=mrt_distance_km,
        )
        row[f"{TOWN_PREFIX}{town}"] = 1
        row[f"{FLAT_TYPE_PREFIX}{flat_type}"] = 1
        return pd.DataFrame([row])[self.feature_columns]
