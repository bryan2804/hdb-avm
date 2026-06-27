import streamlit as st
import pandas as pd
import numpy as np
import joblib
import json
import shap
import plotly.graph_objects as go

st.set_page_config(page_title="HDB Resale Price Estimator", layout="centered")

@st.cache_resource
def load_model():
    model = joblib.load("models/xgboost.joblib")
    with open("models/feature_columns.json") as f:
        feature_columns = json.load(f)
    explainer = shap.TreeExplainer(model)
    return model, feature_columns, explainer

model, feature_columns, explainer = load_model()

TOWNS = [
    "ANG MO KIO","BEDOK","BISHAN","BUKIT BATOK","BUKIT MERAH","BUKIT PANJANG",
    "BUKIT TIMAH","CENTRAL AREA","CHOA CHU KANG","CLEMENTI","GEYLANG","HOUGANG",
    "JURONG EAST","JURONG WEST","KALLANG/WHAMPOA","MARINE PARADE","PASIR RIS",
    "PUNGGOL","QUEENSTOWN","SEMBAWANG","SENGKANG","SERANGOON","TAMPINES",
    "TOAPAYOH","WOODLANDS","YISHUN"
]

FLAT_TYPES = ["2 ROOM","3 ROOM","4 ROOM","5 ROOM","EXECUTIVE","MULTI-GENERATION"]

TOWN_RMSE = {
    "ANG MO KIO": 101908, "CENTRAL AREA": 84272, "BUKIT MERAH": 78569,
    "QUEENSTOWN": 76978, "CLEMENTI": 71794, "KALLANG/WHAMPOA": 66438,
    "GEYLANG": 64590, "BISHAN": 64366, "PUNGGOL": 39870,
    "JURONG EAST": 38469, "JURONG WEST": 36977, "YISHUN": 34986,
    "WOODLANDS": 33685, "CHOA CHU KANG": 29164, "BUKIT BATOK": 28924,
    "SEMBAWANG": 27674
}

WORST_TOWNS = {k: TOWN_RMSE[k] for k in list(TOWN_RMSE)[:8]}
BEST_TOWNS = {k: TOWN_RMSE[k] for k in list(TOWN_RMSE)[8:]}

def get_plain_label(col):
    if col.startswith("town_"):
        return f"Town: {col[5:]}"
    elif col.startswith("flat_type_"):
        return f"Flat Type: {col[10:]}"
    return {
        'floor_area_sqm': 'Floor Area (sqm)',
        'storey_mid': 'Storey Level',
        'remaining_lease_years': 'Remaining Lease (years)',
        'transaction_year': 'Year',
        'transaction_month': 'Month',
        'mrt_distance_km': 'Distance to MRT (km)',
    }.get(col, col)

st.title("HDB Resale Price Estimator")
st.caption("A simplified Automated Valuation Model trained on 232,000 transactions (Jan 2017 – Jun 2026)")

tab1, tab2, tab3 = st.tabs(["Price Estimator", "Model Performance", "About"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        town = st.selectbox("Town", TOWNS)
        flat_type = st.selectbox("Flat Type", FLAT_TYPES)
        floor_area = st.slider("Floor Area (sqm)", 30, 200, 90)
    with col2:
        storey_mid = st.slider("Storey (floor)", 1, 50, 10)
        remaining_lease = st.slider("Remaining Lease (years)", 40, 99, 75)
        mrt_distance = st.slider("Distance to MRT (km)", 0.1, 3.0, 0.5, step=0.1)

    input_dict = {col: 0 for col in feature_columns}
    input_dict["floor_area_sqm"] = floor_area
    input_dict["storey_mid"] = storey_mid
    input_dict["remaining_lease_years"] = remaining_lease
    input_dict["transaction_year"] = 2025
    input_dict["transaction_month"] = 6
    input_dict["mrt_distance_km"] = mrt_distance

    town_col = f"town_{town}"
    if town_col in input_dict:
        inputict[town_col] = 1
    flat_col = f"flat_type_{flat_type}"
    if flat_col in input_dict:
        input_dict[flat_col] = 1

    input_df = pd.DataFrame([input_dict])[feature_columns]
    prediction = model.predict(input_df)[0]
    rmse = TOWN_RMSE.get(town, 51616)
    lower = max(0, prediction - rmse)
    upper = prediction + rmse
    mispricing_pct = (rmse / prediction) * 100

    st.divider()
    st.metric("Estimated Resale Price", f"${prediction:,.0f}")
    st.write(f"**Confidence range:** ${lower:,.0f} – ${upper:,.0f} (±${rmse:,} RMSE for {town})")
    st.info(f"At this price, a ${rmse:,} RMSE represents **{mispricing_pct:.1f}% collateral mispricing exposure** for a lender approving a mortgage against this flat.")

    st.subheader("Why this price?")
    st.caption("Which features pushed the prediction up or down from the average")

    shap_values = explainer.shap_values(input_df)
    shap_arr = shap_values[0] if isinstance(shap_values, list) else shap_values[0]
    base_value = explainer.expected_value if not isinstance(explainer.expected_value, list) else explainer.expected_value[0]

    shap_series = pd.Series(shap_arr, index=feature_columns)
    top_features = shap_series.abs().nlargest(8).index
    top_shap = shap_series[top_features]

    labels = [get_plain_label(f) for f in top_features]
    colors = ["#ef4444" if v > 0 else "#3b82f6" for v in top_shap.values]

    fig = go.Figure(go.Bar(
        x=top_shap.values,
        y=labels,
        orientation='h',
        marker_color=colors,
        text=[f"+${v:,.0f}" if v > 0 else f"-${abs(v):,.0f}" for v in top_shap.values],
        textposition='outside'
    ))
    fig.update_layout(
        xaxis_title="Impact on predicted price ($)",
        height=350,
        margin=dict(l=10, r=80, t=10, b=40),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        xaxis=dict(gridcolor='rgba(255,255,255,0.1)')
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Baseline (average prediction across all flats): ${base_value:,.0f} → Final prediction: ${prediction:,.0f}")

with tab2:
    st.subheader("Where the model is reliable — and where it isn't")
    st.write("Newer, more uniform estates are easier to price than mature central towns with highly heterogeneous stock.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Hardest to price**")
        st.dataframe(pd.DataFrame([(t, f"${v:,}") for t, v in WORST_TOWNS.items()], columns=["Town", "RMSE"]), hide_index=True)
    with col2:
        st.markdown("**Most reliable**")
        st.dataframe(pd.DataFrame([(t, f"${v:,}") for t, v in BEST_TOWNS.items()], columns=["Town", "RMSE"]), hide_index=True)

    st.write("Central Area, Bukit Merah, and Queenstown have the highest error because a 1990 ground-floor 3-room and a 2015 high-floor 5-room sit in the same town category but are priced worlds apart. Sembawang, Bukit Batok, and Choa Chu Kang are newer and more uniform — flat characteristics genuinely predict price.")

with tab3:
    st.subheader("About This Model")
    st.write("This is a simplified Automated Valuation Model (AVM) of the type used by bank home loan teams to sanity-check collateral valuations before mortgage approval. It was trained on 232,000 HDB resale transactions from January 2017 to June 2026, sourced from data.gov.sg.")
    st.write("**Models trained:** Linear Regression (baseline RMSE $87,775) vs XGBoost (RMSE $51,616). The app uses XGBoost.")
    st.write("**Key features:** Floor area, storey, remaining lease, town, flat type, distance to nearest MRT station, transaction date.")
    st.write("**Limitation:** The model has no transactions for Tengah, which is still under MOP. Predictions there would be unreliable extrapolations.")
