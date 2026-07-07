"""Model artifact registry.

Everything the API needs at inference time is loaded exactly once here
(at process startup) and shared across requests: the XGBoost model, the
feature encoder, evaluation metrics, and MRT station coordinates.
"""

import json
from dataclasses import dataclass

import joblib
import pandas as pd
from xgboost import Booster, XGBRegressor

from hdb_avm.config import Settings, get_settings
from hdb_avm.features.encoding import FeatureEncoder
from hdb_avm.features.geo import load_mrt_stations


@dataclass(frozen=True)
class ModelRegistry:
    model: XGBRegressor
    booster: Booster  # used for exact TreeSHAP contributions via pred_contribs
    encoder: FeatureEncoder
    metrics: dict
    mrt_stations: pd.DataFrame

    @classmethod
    def load(cls, settings: Settings | None = None) -> "ModelRegistry":
        settings = settings or get_settings()
        model = joblib.load(settings.xgboost_path)
        encoder = FeatureEncoder.from_artifacts(settings.model_dir)
        with open(settings.metrics_path) as f:
            metrics = json.load(f)
        mrt_stations = load_mrt_stations(settings.mrt_coords_path)
        return cls(
            model=model,
            booster=model.get_booster(),
            encoder=encoder,
            metrics=metrics,
            mrt_stations=mrt_stations,
        )

    def town_rmse(self, town: str | None) -> tuple[int, str]:
        """Return (rmse, scope) where scope is 'town' or 'global'.

        Town-level RMSE reflects how hard each town is to price (heterogeneous
        central towns ~ $60K, uniform newer towns ~ $26K); the global figure is
        the fallback when a town-specific value isn't available.
        """
        town_rmse = self.metrics.get("town_rmse", {})
        if town is not None and town in town_rmse:
            return int(town_rmse[town]), "town"
        return int(self.metrics["default_rmse"]), "global"
