"""
EuroFuelEconomy — interactive country ranking.

Run with: streamlit run app/app.py

Reads only the small, pre-aggregated result tables in db/ (never the raw CSV
or the 6.3M-row vehicles_model table) — see README.md's "Repo structure".
"""
import re
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DB_DIR = ROOT / "db"

BLUE = "#2a78d6"
RED = "#e34948"

COUNTRY_NAMES = {
    "AT": "Austria", "BE": "Belgium", "BG": "Bulgaria", "CY": "Cyprus",
    "CZ": "Czechia", "DE": "Germany", "DK": "Denmark", "EE": "Estonia",
    "ES": "Spain", "FI": "Finland", "FR": "France", "GR": "Greece",
    "HR": "Croatia", "HU": "Hungary", "IE": "Ireland", "IS": "Iceland",
    "IT": "Italy", "LT": "Lithuania", "LU": "Luxembourg", "LV": "Latvia",
    "MT": "Malta", "NL": "Netherlands", "NO": "Norway", "PL": "Poland",
    "PT": "Portugal", "RO": "Romania", "SE": "Sweden", "SI": "Slovenia",
    "SK": "Slovakia",
}

st.set_page_config(page_title="EuroFuelEconomy", page_icon="⛽", layout="centered")


@st.cache_data
def load_results(ref: str) -> pd.DataFrame:
    df = pd.read_csv(DB_DIR / f"country_effects_ref_{ref}.csv")
    df["country"] = df["Coefficient"].str.extract(r"([A-Z]{2})(?:'|\])?$")
    df["country_name"] = df["country"].map(COUNTRY_NAMES)
    return df.dropna(subset=["country"]).sort_values("pct_vs_ref")


st.title("\U0001F6E2️ EuroFuelEconomy")
st.caption(
    "Real-world vs. official (WLTP) fuel consumption, same vehicle model across countries. "
    "Source: JRC OBFCM 2021–2023, vehicle-family fixed effects."
)

ref_label = st.radio(
    "Reference point",
    options=["EU/EEA average", "Portugal"],
    horizontal=True,
)
ref = "EU" if ref_label == "EU/EEA average" else "PT"
df = load_results(ref)

if ref == "PT":
    df = df[df["country"] != "PT"]
    omitted_note = "Portugal is the reference (0% by definition), so it's excluded from the bars above."
else:
    omitted_note = (
        "Slovakia is the implicit baseline for this sum-to-zero reference scheme and isn't "
        "separately estimable here — see the Portugal-referenced view for its position."
    )

axis_label = f"% deviation from {ref_label} (same vehicle model)"

chart = (
    alt.Chart(df)
    .mark_bar(size=14)
    .encode(
        x=alt.X("pct_vs_ref:Q", title=axis_label),
        y=alt.Y("country:N", sort=df["country"].tolist(), title=None),
        color=alt.condition(alt.datum.pct_vs_ref < 0, alt.value(BLUE), alt.value(RED)),
        tooltip=[
            alt.Tooltip("country_name:N", title="Country"),
            alt.Tooltip("pct_vs_ref:Q", title="% vs. reference", format="+.1f"),
            alt.Tooltip("ci_low_pct:Q", title="95% CI low", format="+.1f"),
            alt.Tooltip("ci_high_pct:Q", title="95% CI high", format="+.1f"),
        ],
    )
    .properties(height=26 * len(df))
)
rule = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color="#c3c2b7").encode(x="x:Q")

st.altair_chart(chart + rule, use_container_width=True)
st.caption(omitted_note)

with st.expander("Data table"):
    st.dataframe(
        df[["country_name", "country", "pct_vs_ref", "ci_low_pct", "ci_high_pct"]]
        .rename(columns={
            "country_name": "Country", "country": "ISO",
            "pct_vs_ref": "% vs. reference", "ci_low_pct": "CI low", "ci_high_pct": "CI high",
        })
        .round(2),
        use_container_width=True,
        hide_index=True,
    )

st.caption(
    "Negative = more economical than the reference for the same car. "
    "See [docs/METHODOLOGY.md](https://github.com/pjgoliveira21/EuroFuelEconomy/blob/main/docs/METHODOLOGY.md) "
    "for caveats before reading too much into any single country's position."
)
