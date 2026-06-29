"""
Train XGBoost and Linear Regression on processed_v2.csv (includes lat/lon).
Saves updated models and feature_columns.json.

Usage:
    python3 src/train_v2.py
"""

import json
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from xgboost import XGBRegressor

PROCESSED = "data/processed_v2.csv"
TARGET    = "resale_price"

print("Loading features...")
df = pd.read_csv(PROCESSED)
print(f"  {len(df):,} rows, {df.shape[1]} columns")

# Time-based split: hold out most recent 12 months
df = df.sort_values(["transaction_year", "transaction_month"])
cutoff_idx = int(len(df) * 0.90)
train_df   = df.iloc[:cutoff_idx]
test_df    = df.iloc[cutoff_idx:]

feature_cols = [c for c in df.columns if c != TARGET]
X_train = train_df[feature_cols].values
y_train = train_df[TARGET].values
X_test  = test_df[feature_cols].values
y_test  = test_df[TARGET].values

print(f"Train: {len(X_train):,} | Test: {len(X_test):,}")

# Linear regression baseline
print("\nTraining Linear Regression...")
lr = LinearRegression()
lr.fit(X_train, y_train)
lr_rmse = float(np.sqrt(mean_squared_error(y_test, lr.predict(X_test))))
lr_r2   = r2_score(y_test, lr.predict(X_test))
print(f"  RMSE: ${lr_rmse:,.0f}  R²: {lr_r2:.4f}")

# XGBoost
print("\nTraining XGBoost...")
xgb = XGBRegressor(
    n_estimators=500, learning_rate=0.05, max_depth=7,
    subsample=0.8, colsample_bytree=0.8,
    random_state=42, n_jobs=-1,
)
xgb.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
xgb_rmse = float(np.sqrt(mean_squared_error(y_test, xgb.predict(X_test))))
xgb_r2   = r2_score(y_test, xgb.predict(X_test))
median   = float(np.median(y_test))
print(f"  RMSE: ${xgb_rmse:,.0f}  ({xgb_rmse/median*100:.1f}% of median ${median:,.0f})")
print(f"  R²:   {xgb_r2:.4f}")
print(f"  Improvement over baseline: ${lr_rmse - xgb_rmse:,.0f}")

# Save
joblib.dump(xgb, "models/xgboost.joblib")
joblib.dump(lr,  "models/linear_regression.joblib")
with open("models/feature_columns.json", "w") as f:
    json.dump(feature_cols, f, indent=2)

print("\nSaved models and feature_columns.json to models/")
