"""Valuation service: prediction, confidence band, and explanation.

Explanations use XGBoost's native ``pred_contribs`` (exact TreeSHAP), which
produces the same values as ``shap.TreeExplainer`` without the heavyweight
dependency — the serving image stays lean and immune to shap/xgboost
version-compatibility breakage.
"""

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd
import xgboost as xgb

from hdb_avm.ml.registry import ModelRegistry

_NUMERIC_LABELS = {
    "floor_area_sqm": "Floor area (sqm)",
    "storey_mid": "Storey",
    "remaining_lease_years": "Remaining lease (years)",
    "transaction_year": "Valuation year",
    "transaction_month": "Valuation month",
    "mrt_distance_km": "Distance to MRT (km)",
    "latitude": "Location (latitude)",
    "longitude": "Location (longitude)",
}


def feature_label(column: str) -> str:
    if column.startswith("town_"):
        return f"Town: {column[5:]}"
    if column.startswith("flat_type_"):
        return f"Flat type: {column[10:]}"
    return _NUMERIC_LABELS.get(column, column)


@dataclass(frozen=True)
class Contribution:
    feature: str
    label: str
    amount: float  # dollar impact on the estimate (+/-)


@dataclass(frozen=True)
class Valuation:
    point_estimate: float
    band_low: float
    band_high: float
    rmse: int
    rmse_scope: str  # "town" | "global"
    mispricing_exposure_pct: float  # rmse as % of estimate — lender's risk framing
    valuation_date: date
    baseline: float  # model expected value (average-flat starting point)
    contributions: list[Contribution]


class ValuationService:
    def __init__(self, registry: ModelRegistry):
        self._registry = registry

    def value_flat(
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
        top_k: int = 8,
    ) -> Valuation:
        as_of = as_of or date.today()
        features = self._registry.encoder.encode(
            town=town,
            flat_type=flat_type,
            floor_area_sqm=floor_area_sqm,
            storey_mid=storey_mid,
            remaining_lease_years=remaining_lease_years,
            mrt_distance_km=mrt_distance_km,
            latitude=latitude,
            longitude=longitude,
            as_of=as_of,
        )
        estimate = float(self._registry.model.predict(features)[0])
        rmse, scope = self._registry.town_rmse(town)
        baseline, contributions = self._explain(features, top_k=top_k)
        return Valuation(
            point_estimate=estimate,
            band_low=max(0.0, estimate - rmse),
            band_high=estimate + rmse,
            rmse=rmse,
            rmse_scope=scope,
            mispricing_exposure_pct=round(rmse / estimate * 100, 1) if estimate > 0 else 0.0,
            valuation_date=as_of,
            baseline=baseline,
            contributions=contributions,
        )

    def _explain(
        self, features: pd.DataFrame, top_k: int
    ) -> tuple[float, list[Contribution]]:
        contribs = self._registry.booster.predict(
            xgb.DMatrix(features), pred_contribs=True
        )[0]
        baseline = float(contribs[-1])
        values = contribs[:-1]
        top_idx = np.argsort(-np.abs(values))[:top_k]
        columns = self._registry.encoder.feature_columns
        return baseline, [
            Contribution(
                feature=columns[i],
                label=feature_label(columns[i]),
                amount=round(float(values[i])),
            )
            for i in top_idx
        ]
