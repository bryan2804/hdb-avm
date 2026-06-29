# HDB Automated Valuation Model (AVM)

A simplified Automated Valuation Model trained on 232,000 HDB resale transactions, deployed as an interactive Streamlit app. Modelled on the collateral validation tools used by bank home loan teams to sanity-check property valuations before mortgage approval.

**[Live Demo →](https://hdb-avm-aj2yyyvwanht7ghcwpv8gs.streamlit.app/)**

---

## The Problem

When a bank approves a mortgage, it needs to know the flat is worth what the buyer is paying. Manual valuations are slow and expensive. Automated Valuation Models run instantly at scale — but their error rate directly determines the bank's collateral mispricing exposure.

A model with $51,616 RMSE on a $630,000 flat means the bank could be approving loans against collateral that is 8.2% overvalued. This project quantifies that exposure and makes it interactive.

---

## Features

**Price Estimator** — Input town, flat type, storey, floor area, remaining lease, and MRT distance. Returns predicted price with a town-specific confidence band and collateral mispricing exposure percentage.

**SHAP Explainability** — Waterfall chart showing which features drove the prediction up or down, and by how much. Floor area, remaining lease, and MRT distance are consistently the top three drivers.

**Scenario Comparison** — Side-by-side comparison of two flats. Shows price per sqm and flags which offers better collateral value for a lender.

**Price Trends** — Historical median price by quarter for any town and flat type combination, from Q1 2017 to Q2 2026.

**Mortgage Exposure Calculator** — Input loan amount and LTV ratio. Outputs worst-case effective LTV if the model overvalues by one RMSE, with risk flagging against 80% and 90% LTV thresholds.

**Model Performance** — Town-by-town RMSE breakdown. Shows where the model is reliable (Sembawang ±$27,674) and where it isn't (Ang Mo Kio ±$101,908), with plain-English explanation of why.

---

## Model

| Model | RMSE | MAE | R² |
|---|---|---|---|
| Linear Regression (baseline) | $87,775 | $61,591 | 0.826 |
| XGBoost | $51,616 | $34,825 | 0.940 |

XGBoost reduces error by $36,159 over the baseline. The app uses XGBoost.

**Training split:** Time-based. Most recent 12 months held out as test set. A random split would let the model see future transactions during training, overstating real-world accuracy.

**Key features:**
- Floor area (sqm)
- Storey midpoint
- Remaining lease (years) — parsed from strings like "61 years 04 months"
- Town and flat type (one-hot encoded)
- Distance to nearest MRT station (km) — geocoded via OneMap API, haversine distance

---

## Why Town RMSE Varies

The model struggles most in mature central estates like Central Area (±$84,272) and Bukit Merah (±$78,569). A 1990 ground-floor 3-room flat and a 2015 high-floor 5-room flat sit in the same town category but are priced worlds apart — the model cannot resolve that heterogeneity.

It performs best in newer, more uniform towns like Sembawang (±$27,674) and Bukit Batok (±$28,924), where flat characteristics genuinely predict price.

**Known limitation:** Tengah has zero resale transactions — flats are still under the 5-year Minimum Occupation Period. Predictions there would be unreliable extrapolations and the model explicitly flags this.

---

## Stack

- **Data:** data.gov.sg HDB resale flat prices (Jan 2017 – Jun 2026)
- **Geocoding:** OneMap API — 9,714 unique block addresses geocoded, results cached
- **Modelling:** scikit-learn (Linear Regression), XGBoost, SHAP
- **App:** Streamlit, Plotly
- **Deployment:** Streamlit Community Cloud

---

## Project Structure

```
hdb-avm/
├── app/
│   └── main.py              # Streamlit app
├── data/
│   ├── resale-flat-prices.csv
│   ├── processed.csv        # Feature-engineered dataset
│   ├── mrt_station_coords.csv
│   └── price_trends.csv     # Quarterly medians by town and flat type
├── models/
│   ├── xgboost.joblib
│   ├── linear_regression.joblib
│   └── feature_columns.json
├── src/
│   ├── explore_data.py
│   ├── features.py          # Feature engineering pipeline
│   ├── geocode_mrt.py       # MRT station coordinate fetching
│   ├── mrt_distance.py      # Haversine distance calculation
│   └── train.py             # Model training and evaluation
└── requirements.txt
```

---

## Run Locally

```bash
git clone https://github.com/bryan2804/hdb-avm.git
cd hdb-avm
pip install -r requirements.txt
streamlit run app/main.py
```
