"""
Train and compare a linear regression baseline against XGBoost for HDB
resale price prediction.

Uses a time-based split (most recent 12 months held out as test) rather
than a random split. A random split would let the model see transactions
from the same month/year on both sides, overstating accuracy -- in
deployment this model only ever predicts transactions that haven't
happened yet, so validation should reflect that.
"""

import json

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor

from features import PROCESSED_PATH, RAW_PATH

MODELS_DIR = "models"
TEST_MONTHS_HELD_OUT = 12


def load_processed():
    df = pd.read_csv(PROCESSED_PATH)
    df["town"] = pd.read_csv(RAW_PATH, usecols=["town"])["town"]

    before = len(df)
    df = df.dropna(subset=["mrt_distance_km"])
    dropped = before - len(df)
    print(f"Dropped {dropped} rows ({dropped / before:.2%}) with missing mrt_distance_km")

    return df


def time_based_split(df: pd.DataFrame):
    period = df["transaction_year"] * 12 + df["transaction_month"]
    cutoff = period.max() - TEST_MONTHS_HELD_OUT
    train_df = df[period <= cutoff]
    test_df = df[period > cutoff]
    print(
        f"Train: {len(train_df)} rows (up to {train_df['transaction_year'].max()}-"
        f"{train_df[train_df['transaction_year'] == train_df['transaction_year'].max()]['transaction_month'].max():02d}), "
        f"Test: {len(test_df)} rows (most recent {TEST_MONTHS_HELD_OUT} months)"
    )
    return train_df, test_df


def evaluate(name, y_true, y_pred, median_price):
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)
    print(f"\n{name}")
    print(f"  RMSE: ${rmse:,.0f}  ({rmse / median_price:.2%} of median resale price ${median_price:,.0f})")
    print(f"  MAE:  ${mae:,.0f}")
    print(f"  R2:   {r2:.4f}")
    return {"rmse": rmse, "mae": mae, "r2": r2}


def per_town_rmse(test_df, y_true, y_pred, top_n=8):
    err_df = pd.DataFrame({"town": test_df["town"].values, "y_true": y_true, "y_pred": y_pred})
    grouped = err_df.groupby("town").apply(
        lambda g: np.sqrt(mean_squared_error(g["y_true"], g["y_pred"])), include_groups=False
    )
    grouped = grouped.sort_values(ascending=False)
    print(f"\nWorst {top_n} towns by RMSE (test set):")
    print(grouped.head(top_n).to_string())
    print(f"\nBest {top_n} towns by RMSE (test set):")
    print(grouped.tail(top_n).to_string())


def main():
    df = load_processed()
    train_df, test_df = time_based_split(df)

    feature_cols = [c for c in df.columns if c not in ("resale_price", "town")]
    X_train, y_train = train_df[feature_cols], train_df["resale_price"]
    X_test, y_test = test_df[feature_cols], test_df["resale_price"]
    median_price = y_test.median()

    lr = LinearRegression()
    lr.fit(X_train, y_train)
    lr_pred = lr.predict(X_test)
    lr_metrics = evaluate("Linear Regression (baseline)", y_test, lr_pred, median_price)

    xgb = XGBRegressor(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
    )
    xgb.fit(X_train, y_train)
    xgb_pred = xgb.predict(X_test)
    xgb_metrics = evaluate("XGBoost", y_test, xgb_pred, median_price)

    print(f"\nRMSE improvement over baseline: ${lr_metrics['rmse'] - xgb_metrics['rmse']:,.0f}")

    per_town_rmse(test_df, y_test.values, xgb_pred)

    joblib.dump(lr, f"{MODELS_DIR}/linear_regression.joblib")
    joblib.dump(xgb, f"{MODELS_DIR}/xgboost.joblib")
    with open(f"{MODELS_DIR}/feature_columns.json", "w") as f:
        json.dump(feature_cols, f, indent=2)
    print(f"\nSaved models and feature_columns.json to {MODELS_DIR}/")


if __name__ == "__main__":
    main()
