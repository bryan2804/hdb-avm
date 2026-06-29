"""
Full retraining pipeline for HDB AVM.
Runs: fetch new data → build features → train → evaluate → save.

Usage:
    python3 src/retrain.py              # fetch new data then retrain
    python3 src/retrain.py --skip-fetch # retrain on existing data only
"""

import sys
import json
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from xgboost import XGBRegressor

PROCESSED_PATH  = "data/processed_v2.csv"
MODEL_DIR       = Path("models")
LOG_PATH        = "models/retrain_log.json"


# ── Train / evaluate ──────────────────────────────────────────────────────────

def time_split(df: pd.DataFrame, test_months: int = 12):
    """Hold out the most recent N months as test set."""
    df = df.sort_values(["transaction_year", "transaction_month"])
    cutoff_year  = df["transaction_year"].max()
    cutoff_month = df["transaction_month"].max() - test_months
    if cutoff_month <= 0:
        cutoff_year  -= 1
        cutoff_month += 12

    mask = (df["transaction_year"] < cutoff_year) | (
        (df["transaction_year"] == cutoff_year) & (df["transaction_month"] <= cutoff_month)
    )
    return df[mask], df[~mask]


def rmse(y_true, y_pred):
    return float(np.sqrt(mean_squared_error(y_true, y_pred)))


def train_and_evaluate(df: pd.DataFrame) -> dict:
    target = "resale_price"
    drop   = [target, "transaction_year", "transaction_month"]
    feature_cols = [c for c in df.columns if c not in drop]

    # Time-based split
    train_df, test_df = time_split(df)
    X_train = train_df[feature_cols].values
    y_train = train_df[target].values
    X_test  = test_df[feature_cols].values
    y_test  = test_df[target].values

    print(f"Train: {len(X_train):,} rows | Test: {len(X_test):,} rows")

    # Linear regression baseline
    lr = LinearRegression()
    lr.fit(X_train, y_train)
    lr_rmse = rmse(y_test, lr.predict(X_test))
    lr_r2   = r2_score(y_test, lr.predict(X_test))
    print(f"Linear Regression  RMSE: ${lr_rmse:,.0f}  R²: {lr_r2:.4f}")

    # XGBoost
    xgb = XGBRegressor(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=7,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
    )
    xgb.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )
    xgb_rmse = rmse(y_test, xgb.predict(X_test))
    xgb_r2   = r2_score(y_test, xgb.predict(X_test))
    print(f"XGBoost            RMSE: ${xgb_rmse:,.0f}  R²: {xgb_r2:.4f}")

    median_price = float(np.median(y_test))
    improvement  = lr_rmse - xgb_rmse
    print(f"Improvement over baseline: ${improvement:,.0f}")
    print(f"Collateral exposure (XGBoost): {xgb_rmse/median_price*100:.1f}% of median ${median_price:,.0f}")

    # Town-level RMSE on test set
    test_copy = test_df.copy()
    test_copy["pred"] = xgb.predict(X_test)
    test_copy["error"] = (test_copy["pred"] - test_copy[target]).abs()
    town_cols = [c for c in test_copy.columns if c.startswith("town_")]
    test_copy["town"] = (
        pd.DataFrame(test_copy[town_cols].values, columns=[c[5:] for c in town_cols])
        .idxmax(axis=1)
    )
    town_rmse = (
        test_copy.groupby("town")
        .apply(lambda g: float(np.sqrt(mean_squared_error(g[target], g["pred"]))))
        .sort_values()
    )
    print("\nBest 5 towns by RMSE:")
    print(town_rmse.head(5).to_string())
    print("\nWorst 5 towns by RMSE:")
    print(town_rmse.tail(5).to_string())

    return {
        "lr": lr,
        "xgb": xgb,
        "feature_cols": feature_cols,
        "metrics": {
            "lr_rmse": lr_rmse, "lr_r2": lr_r2,
            "xgb_rmse": xgb_rmse, "xgb_r2": xgb_r2,
            "median_price": median_price,
            "improvement": improvement,
        },
        "town_rmse": town_rmse.to_dict(),
    }


def save_models(result: dict):
    MODEL_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    joblib.dump(result["xgb"], MODEL_DIR / "xgboost.joblib")
    joblib.dump(result["lr"],  MODEL_DIR / "linear_regression.joblib")

    with open(MODEL_DIR / "feature_columns.json", "w") as f:
        json.dump(result["feature_cols"], f, indent=2)

    # Append to retrain log
    log = []
    if Path(LOG_PATH).exists():
        with open(LOG_PATH) as f:
            log = json.load(f)

    log.append({
        "timestamp": ts,
        "metrics": result["metrics"],
        "town_rmse": result["town_rmse"],
    })
    with open(LOG_PATH, "w") as f:
        json.dump(log, f, indent=2)

    print(f"\nModels saved to {MODEL_DIR}/")
    print(f"Retrain log updated: {LOG_PATH}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    skip_fetch = "--skip-fetch" in sys.argv

    if not skip_fetch:
        print("=" * 50)
        print("Step 1: Fetch latest data")
        print("=" * 50)
        try:
            from fetch_data import update_dataset
            update_dataset()
        except Exception as e:
            print(f"Data fetch failed: {e}")
            print("Continuing with existing data...")

    print("\n" + "=" * 50)
    print("Step 2: Build features")
    print("=" * 50)
    from features_v2 import build_features
    df = build_features()

    print("\n" + "=" * 50)
    print("Step 3: Train models")
    print("=" * 50)
    result = train_and_evaluate(df)

    print("\n" + "=" * 50)
    print("Step 4: Save models")
    print("=" * 50)
    save_models(result)

    print("\nRetraining complete.")


if __name__ == "__main__":
    main()
