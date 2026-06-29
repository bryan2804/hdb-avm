import json
import numpy as np
import joblib
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(page_title="HDB Automated Valuation Model", layout="wide")


# ── Loaders ───────────────────────────────────────────────────────────────────

@st.cache_resource
def load_model():
    model = joblib.load("models/xgboost.joblib")
    with open("models/feature_columns.json") as f:
        feature_columns = json.load(f)
    try:
        import shap
        explainer = shap.TreeExplainer(model)
    except Exception:
        explainer = None
    return model, feature_columns, explainer


@st.cache_data
def load_trends():
    return pd.read_csv("data/price_trends.csv")


@st.cache_data
def load_mrt():
    mrt = pd.read_csv("data/mrt_station_coords.csv")
    mrt.columns = [c.lower() for c in mrt.columns]
    lat_col = [c for c in mrt.columns if "lat" in c][0]
    lon_col = [c for c in mrt.columns if "lon" in c][0]
    return mrt.rename(columns={lat_col: "latitude", lon_col: "longitude"})


model, feature_columns, explainer = load_model()
trends = load_trends()
mrt_df = load_mrt()

# ── Constants ─────────────────────────────────────────────────────────────────

TOWNS = [
    "ANG MO KIO","BEDOK","BISHAN","BUKIT BATOK","BUKIT MERAH","BUKIT PANJANG",
    "BUKIT TIMAH","CENTRAL AREA","CHOA CHU KANG","CLEMENTI","GEYLANG","HOUGANG",
    "JURONG EAST","JURONG WEST","KALLANG/WHAMPOA","MARINE PARADE","PASIR RIS",
    "PUNGGOL","QUEENSTOWN","SEMBAWANG","SENGKANG","SERANGOON","TAMPINES",
    "TOAPAYOH","WOODLANDS","YISHUN",
]
FLAT_TYPES = ["2 ROOM","3 ROOM","4 ROOM","5 ROOM","EXECUTIVE","MULTI-GENERATION"]
TOWN_RMSE = {
    "ANG MO KIO":101908,"CENTRAL AREA":84272,"BUKIT MERAH":78569,"QUEENSTOWN":76978,
    "CLEMENTI":71794,"KALLANG/WHAMPOA":66438,"GEYLANG":64590,"BISHAN":64366,
    "PUNGGOL":39870,"JURONG EAST":38469,"JURONG WEST":36977,"YISHUN":34986,
    "WOODLANDS":33685,"CHOA CHU KANG":29164,"BUKIT BATOK":28924,"SEMBAWANG":27674,
}
DEFAULT_RMSE = 51616

# ── Helpers ───────────────────────────────────────────────────────────────────

def haversine_min(lat, lon, mrt):
    R = 6371.0
    lat_r  = np.radians(lat)
    lon_r  = np.radians(lon)
    mlat_r = np.radians(mrt["latitude"].values)
    mlon_r = np.radians(mrt["longitude"].values)
    dlat = mlat_r - lat_r
    dlon = mlon_r - lon_r
    a = np.sin(dlat/2)**2 + np.cos(lat_r)*np.cos(mlat_r)*np.sin(dlon/2)**2
    dists = 2 * R * np.arcsin(np.sqrt(a))
    idx = np.argmin(dists)
    name_col = [c for c in mrt.columns if "name" in c.lower()]
    station = str(mrt.iloc[idx][name_col[0]]) if name_col else "MRT"
    return float(dists[idx]), station


def geocode_onemap(address: str):
    try:
        resp = requests.get(
            "https://www.onemap.gov.sg/api/common/elastic/search",
            params={"searchVal": address, "returnGeom": "Y",
                    "getAddrDetails": "Y", "pageNum": 1},
            timeout=8,
        )
        data = resp.json()
        results = data.get("results", [])
        if not results:
            return None
        r = results[0]
        return {
            "lat": float(r["LATITUDE"]),
            "lon": float(r["LONGITUDE"]),
            "address": r.get("ADDRESS", address),
        }
    except Exception:
        return None


def make_input(town, flat_type, floor_area, storey, lease, mrt_dist,
               lat=None, lon=None):
    d = {col: 0 for col in feature_columns}
    d["floor_area_sqm"]       = floor_area
    d["storey_mid"]            = storey
    d["remaining_lease_years"] = lease
    d["transaction_year"]      = 2025
    d["transaction_month"]     = 6
    d["mrt_distance_km"]       = mrt_dist
    if "latitude" in d and lat is not None:
        d["latitude"]  = lat
        d["longitude"] = lon
    if f"town_{town}" in d:
        d[f"town_{town}"] = 1
    if f"flat_type_{flat_type}" in d:
        d[f"flat_type_{flat_type}"] = 1
    return pd.DataFrame([d])[feature_columns]


def get_label(col):
    if col.startswith("town_"):
        return f"Town: {col[5:]}"
    if col.startswith("flat_type_"):
        return f"Flat: {col[10:]}"
    return {
        "floor_area_sqm":        "Floor Area (sqm)",
        "storey_mid":            "Storey",
        "remaining_lease_years": "Remaining Lease",
        "transaction_year":      "Year",
        "transaction_month":     "Month",
        "mrt_distance_km":       "MRT Distance",
        "latitude":              "Latitude",
        "longitude":             "Longitude",
    }.get(col, col)


def shap_chart(input_df):
    if explainer is None:
        return
    sv = explainer.shap_values(input_df)
    sa = sv[0] if isinstance(sv, list) else sv[0]
    bv = (explainer.expected_value if not isinstance(explainer.expected_value, list)
          else explainer.expected_value[0])
    ss  = pd.Series(sa, index=feature_columns)
    top = ss.abs().nlargest(8).index
    ts  = ss[top]
    fig = go.Figure(go.Bar(
        x=ts.values, y=[get_label(f) for f in top], orientation="h",
        marker_color=["#ef4444" if v > 0 else "#3b82f6" for v in ts.values],
        text=[f"+${v:,.0f}" if v > 0 else f"-${abs(v):,.0f}" for v in ts.values],
        textposition="outside",
    ))
    fig.update_layout(
        xaxis_title="Price impact ($)", height=350,
        margin=dict(l=10, r=80, t=10, b=40),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Baseline average: ${bv:,.0f} → Prediction: ${bv + float(sa.sum()):,.0f}")


def prediction_block(pred, rmse, town=None):
    label = f"±${rmse:,} RMSE" + (f" for {town}" if town else "")
    st.metric("Estimated Resale Price", f"${pred:,.0f}")
    st.write(f"**Confidence range:** ${max(0, pred-rmse):,.0f} – ${pred+rmse:,.0f} ({label})")
    st.info(
        f"A ${rmse:,} RMSE represents "
        f"**{rmse/pred*100:.1f}% collateral mispricing exposure** "
        f"for a mortgage lender."
    )


# ── App ───────────────────────────────────────────────────────────────────────

st.title("HDB Automated Valuation Model")
st.caption(
    "232,000 transactions · Jan 2017 – Jun 2026 · "
    "Modelled on collateral validation tools used by bank home loan teams"
)

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Price Estimator", "Address Lookup", "Scenario Comparison",
    "Price Trends", "Mortgage Calculator", "Model Performance", "About",
])

# ── TAB 1: Price Estimator ────────────────────────────────────────────────────
with tab1:
    c1, c2 = st.columns(2)
    with c1:
        town       = st.selectbox("Town", TOWNS, key="t1_town")
        flat_type  = st.selectbox("Flat Type", FLAT_TYPES, key="t1_flat")
        floor_area = st.slider("Floor Area (sqm)", 30, 200, 90, key="t1_area")
    with c2:
        storey_mid      = st.slider("Storey", 1, 50, 10, key="t1_storey")
        remaining_lease = st.slider("Remaining Lease (years)", 40, 99, 75, key="t1_lease")
        mrt_distance    = st.slider("Distance to MRT (km)", 0.1, 3.0, 0.5, step=0.1, key="t1_mrt")

    input_df = make_input(town, flat_type, floor_area, storey_mid, remaining_lease, mrt_distance)
    pred = model.predict(input_df)[0]
    rmse = TOWN_RMSE.get(town, DEFAULT_RMSE)

    st.divider()
    prediction_block(pred, rmse, town)
    st.subheader("Why this price?")
    shap_chart(input_df)

# ── TAB 2: Address Lookup ─────────────────────────────────────────────────────
with tab2:
    st.subheader("Address-Based Lookup")
    st.write(
        "Enter a block address to predict using the flat's exact coordinates "
        "— more precise than town-level estimation."
    )
    st.caption("Example: `406 ANG MO KIO AVE 10` or `52 COMMONWEALTH DR`")

    address_input = st.text_input("Block address", placeholder="406 ANG MO KIO AVE 10")
    c1, c2 = st.columns(2)
    with c1:
        a_flat_type  = st.selectbox("Flat Type", FLAT_TYPES, key="a_flat")
        a_floor_area = st.slider("Floor Area (sqm)", 30, 200, 90, key="a_area")
    with c2:
        a_storey = st.slider("Storey", 1, 50, 10, key="a_storey")
        a_lease  = st.slider("Remaining Lease (years)", 40, 99, 75, key="a_lease")

    if address_input and st.button("Get Prediction"):
        with st.spinner("Geocoding via OneMap API..."):
            geo = geocode_onemap(address_input)

        if geo is None:
            st.error("Address not found. Try format: `BLOCK STREET NAME` e.g. `406 ANG MO KIO AVE 10`")
        else:
            lat, lon = geo["lat"], geo["lon"]
            mrt_dist, nearest_mrt = haversine_min(lat, lon, mrt_df)

            st.success(f"Found: {geo['address']}")
            col1, col2, col3 = st.columns(3)
            with col1: st.metric("Latitude",  f"{lat:.5f}")
            with col2: st.metric("Longitude", f"{lon:.5f}")
            with col3: st.metric("Nearest MRT", f"{nearest_mrt} ({mrt_dist:.2f} km)")

            input_df = make_input(
                "ANG MO KIO", a_flat_type, a_floor_area,
                a_storey, a_lease, mrt_dist, lat=lat, lon=lon
            )
            pred = model.predict(input_df)[0]

            st.divider()
            prediction_block(pred, DEFAULT_RMSE)
            st.subheader("Why this price?")
            shap_chart(input_df)

# ── TAB 3: Scenario Comparison ────────────────────────────────────────────────
with tab3:
    st.subheader("Compare Two Flats Side by Side")
    st.caption("Which offers better value per sqm? Useful for buyers and lenders comparing collateral.")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Flat A**")
        at  = st.selectbox("Town", TOWNS, key="at")
        af  = st.selectbox("Flat Type", FLAT_TYPES, key="af")
        aa  = st.slider("Floor Area (sqm)", 30, 200, 90, key="aa")
        ast = st.slider("Storey", 1, 50, 10, key="ast")
        al  = st.slider("Remaining Lease (years)", 40, 99, 75, key="al")
        am  = st.slider("Distance to MRT (km)", 0.1, 3.0, 0.5, step=0.1, key="am")
    with c2:
        st.markdown("**Flat B**")
        bt  = st.selectbox("Town", TOWNS, index=5, key="bt")
        bf  = st.selectbox("Flat Type", FLAT_TYPES, index=2, key="bf")
        ba  = st.slider("Floor Area (sqm)", 30, 200, 100, key="ba")
        bst = st.slider("Storey", 1, 50, 15, key="bst")
        bl  = st.slider("Remaining Lease (years)", 40, 99, 80, key="bl")
        bm  = st.slider("Distance to MRT (km)", 0.1, 3.0, 0.3, step=0.1, key="bm")

    ap    = model.predict(make_input(at, af, aa, ast, al, am))[0]
    bp    = model.predict(make_input(bt, bf, ba, bst, bl, bm))[0]
    ar    = TOWN_RMSE.get(at, DEFAULT_RMSE)
    br    = TOWN_RMSE.get(bt, DEFAULT_RMSE)
    appsm = ap / aa
    bppsm = bp / ba

    st.divider()
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Flat A Price", f"${ap:,.0f}", f"±${ar:,}")
        st.metric("Flat A per sqm", f"${appsm:,.0f}")
    with m2:
        st.metric("Flat B Price", f"${bp:,.0f}", f"±${br:,}")
        st.metric("Flat B per sqm", f"${bppsm:,.0f}")
    with m3:
        st.metric("Price Difference", f"${abs(bp-ap):,.0f}")
        st.metric("Better Value", "Flat A" if appsm < bppsm else "Flat B")

    winner = "Flat A" if appsm < bppsm else "Flat B"
    st.success(f"{winner} offers better value at ${min(appsm,bppsm):,.0f}/sqm vs ${max(appsm,bppsm):,.0f}/sqm.")

# ── TAB 4: Price Trends ───────────────────────────────────────────────────────
with tab4:
    st.subheader("Historical Price Trends by Town")
    c1, c2 = st.columns(2)
    with c1:
        tr_town = st.selectbox("Town", TOWNS, key="tr_town")
    with c2:
        tr_flat = st.selectbox("Flat Type", FLAT_TYPES, index=2, key="tr_flat")

    filt = trends[(trends["town"] == tr_town) & (trends["flat_type"] == tr_flat)]
    if filt.empty:
        st.warning("No data for this combination.")
    else:
        fig2 = go.Figure(go.Scatter(
            x=filt["period"], y=filt["resale_price"],
            mode="lines+markers",
            line=dict(color="#ef4444", width=2),
            marker=dict(size=5),
        ))
        fig2.update_layout(
            xaxis_title="Quarter", yaxis_title="Median Price ($)", height=400,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="white"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.1)", tickangle=45),
            yaxis=dict(gridcolor="rgba(255,255,255,0.1)", tickformat="$,.0f"),
        )
        st.plotly_chart(fig2, use_container_width=True)
        first = filt.iloc[0]["resale_price"]
        last  = filt.iloc[-1]["resale_price"]
        st.caption(
            f"{tr_flat} in {tr_town}: ${first:,.0f} → ${last:,.0f} "
            f"({(last-first)/first*100:+.1f}% since Q1 2017)"
        )

# ── TAB 5: Mortgage Calculator ────────────────────────────────────────────────
with tab5:
    st.subheader("Mortgage Collateral Exposure Calculator")
    st.caption("Quantifies a lender's risk from model uncertainty on a specific loan.")
    c1, c2 = st.columns(2)
    with c1:
        loan = st.number_input("Loan Amount ($)", 100000, 2000000, 500000, 10000)
        ltv  = st.slider("Loan-to-Value Ratio (%)", 50, 90, 75)
    with c2:
        mc_town = st.selectbox("Town", TOWNS, key="mc_town")

    collateral = loan / (ltv / 100)
    mc_rmse    = TOWN_RMSE.get(mc_town, DEFAULT_RMSE)
    exposure   = mc_rmse / collateral * 100
    worst      = collateral - mc_rmse
    ltv_worst  = loan / worst * 100 if worst > 0 else 999

    st.divider()
    m1, m2, m3 = st.columns(3)
    with m1: st.metric("Collateral Required", f"${collateral:,.0f}")
    with m2: st.metric(f"Model RMSE ({mc_town})", f"${mc_rmse:,}")
    with m3: st.metric("Mispricing Exposure", f"{exposure:.1f}%")

    st.write(
        f"Worst case: model overvalues by one RMSE → "
        f"actual collateral ${worst:,.0f} → effective LTV **{ltv_worst:.1f}%**"
    )
    if ltv_worst > 90:
        st.error("Breaches 90% LTV limit in worst case. High-risk loan for this town.")
    elif ltv_worst > 80:
        st.warning("Pushes above 80% LTV threshold in worst case. Limited buffer.")
    else:
        st.success("Remains within acceptable LTV parameters even in worst case.")

# ── TAB 6: Model Performance ──────────────────────────────────────────────────
with tab6:
    st.subheader("Model Performance by Town")
    worst_t = {
        "ANG MO KIO":101908,"CENTRAL AREA":84272,"BUKIT MERAH":78569,
        "QUEENSTOWN":76978,"CLEMENTI":71794,"KALLANG/WHAMPOA":66438,
        "GEYLANG":64590,"BISHAN":64366,
    }
    best_t = {
        "SEMBAWANG":27674,"BUKIT BATOK":28924,"CHOA CHU KANG":29164,
        "WOODLANDS":33685,"YISHUN":34986,"JURONG WEST":36977,
        "JURONG EAST":38469,"PUNGGOL":39870,
    }
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Hardest to price**")
        st.dataframe(
            pd.DataFrame([(t, f"${v:,}") for t, v in worst_t.items()], columns=["Town", "RMSE"]),
            hide_index=True,
        )
    with c2:
        st.markdown("**Most reliable**")
        st.dataframe(
            pd.DataFrame([(t, f"${v:,}") for t, v in best_t.items()], columns=["Town", "RMSE"]),
            hide_index=True,
        )
    st.write(
        "Central Area and Bukit Merah score worst because a 1990 ground-floor 3-room "
        "and a 2015 high-floor 5-room sit in the same town category but are priced worlds apart. "
        "Newer, more uniform towns like Sembawang and Bukit Batok are much easier to price."
    )

# ── TAB 7: About ──────────────────────────────────────────────────────────────
with tab7:
    st.subheader("About")
    st.write(
        "A simplified Automated Valuation Model (AVM) of the type used by bank home loan teams "
        "to sanity-check collateral valuations before mortgage approval."
    )
    st.write(
        "Trained on 232,000 HDB resale transactions (Jan 2017 – Jun 2026) from data.gov.sg. "
        "MRT distances computed via OneMap API geocoding (9,714 unique block addresses). "
        "Address Lookup tab geocodes queries live via OneMap API."
    )
    st.write("**Baseline:** Linear Regression RMSE $87,775 | **Final model:** XGBoost RMSE $38,295 | **R²:** 0.94")
    st.write(
        "**Known limitation:** No Tengah transactions exist (flats still under MOP). "
        "Predictions there are unreliable extrapolations."
    )
    st.write("Source: [github.com/bryan2804/hdb-avm](https://github.com/bryan2804/hdb-avm)")
