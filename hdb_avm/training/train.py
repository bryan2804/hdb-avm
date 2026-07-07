"""Train the AVM (XGBoost) and linear-regression baseline; write all artifacts.

Replaces the legacy ``src/train_v2.py`` + ``src/update_rmse.py`` pair. The key
difference: evaluation metrics — including per-town RMSE — are *computed* on the
held-out test window and written to ``models/metrics.json``, instead of being
hardcoded and regex-patched into the Streamlit app. Both the API and the
Streamlit app read that artifact.

Methodology (unchanged from v2):
  - time-ordered split, most recent 10% of transactions held out
  - XGBoost: 500 trees, lr 0.05, depth 7, subsample/colsample 0.8
"""

import json
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from xgboost import XGBRegressor

PROCESSED = "data/processed_v2.csv"
MODEL_DIR = "models"
TARGET = "resale_price"
MIN_TOWN_TEST_SAMPLES = 30  # below this, a town RMSE is too noisy to publish


def _per_town_rmse(
    test_df: pd.DataFrame, y_true: np.ndarray, y_pred: np.ndarray
) -> dict[str, int]:
    town_cols = [c for c in test_df.columns if c.startswith("town_")]
    towns = test_df[town_cols].idxmax(axis=1).str[len("town_") :].values
    errors = pd.DataFrame({"town": towns, "sq_err": (y_true - y_pred) ** 2})
    grouped = errors.groupby("town")["sq_err"].agg(["mean", "count"])
    grouped = grouped[grouped["count"] >= MIN_TOWN_TEST_SAMPLES]
    return {t: int(round(np.sqrt(m))) for t, m in grouped["mean"].items()}


def train(processed_path: str | Path = PROCESSED, model_dir: str | Path = MODEL_DIR) -> dict:
    model_dir = Path(model_dir)
    print("Loading features...")
    df = pd.read_csv(processed_path)
    print(f"  {len(df):,} rows, {df.shape[1]} columns")

    # Time-based split: hold out the most recent 10% of transactions
    df = df.sort_values(["transaction_year", "transaction_month"])
    cutoff = int(len(df) * 0.90)
    train_df, test_df = df.iloc[:cutoff], df.iloc[cutoff:]

    feature_cols = [c for c in df.columns if c != TARGET]
    X_train, y_train = train_df[feature_cols].values, train_df[TARGET].values
    X_test, y_test = test_df[feature_cols].values, test_df[TARGET].values
    print(f"Train: {len(X_train):,} | Test: {len(X_test):,}")

    print("Training Linear Regression baseline...")
    lr = LinearRegression()
    lr.fit(X_train, y_train)
    lr_pred = lr.predict(X_test)
    lr_rmse = float(np.sqrt(mean_squared_error(y_test, lr_pred)))
    lr_r2 = float(r2_score(y_test, lr_pred))
    print(f"  RMSE: ${lr_rmse:,.0f}  R²: {lr_r2:.4f}")

    print("Training XGBoost...")
    xgb = XGBRegressor(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=7,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
    )
    xgb.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
    xgb_pred = xgb.predict(X_test)
    xgb_rmse = float(np.sqrt(mean_squared_error(y_test, xgb_pred)))
    xgb_r2 = float(r2_score(y_test, xgb_pred))
    median = float(np.median(y_test))
    print(f"  RMSE: ${xgb_rmse:,.0f} ({xgb_rmse / median * 100:.1f}% of median ${median:,.0f})")
    print(f"  R²:   {xgb_r2:.4f}")
    print(f"  Improvement over baseline: ${lr_rmse - xgb_rmse:,.0f}")

    metrics = {
        "trained_at": date.today().isoformat(),
        "model": "xgboost",
        "evaluation": "held-out most recent 10% of transactions (time-ordered split)",
        "n_train": len(X_train),
        "n_test": len(X_test),
        "median_test_price": int(median),
        "xgboost": {"rmse": int(round(xgb_rmse)), "r2": round(xgb_r2, 4)},
        "baseline_linear_regression": {"rmse": int(round(lr_rmse)), "r2": round(lr_r2, 4)},
        "default_rmse": int(round(xgb_rmse)),
        "town_rmse": _per_town_rmse(test_df, y_test, xgb_pred),
    }

    print("Saving artifacts...")
    joblib.dump(xgb, model_dir / "xgboost.joblib")
    joblib.dump(lr, model_dir / "linear_regression.joblib")
    with open(model_dir / "feature_columns.json", "w") as f:
        json.dump(feature_cols, f, indent=2)
    with open(model_dir / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"  models + feature_columns.json + metrics.json → {model_dir}/")
    return metrics


if __name__ == "__main__":
    train()
