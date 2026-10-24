from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="COVID-19 | Data dashboard", page_icon="🦠", layout="wide")

# A small optional local workbook can be placed beside this file. Otherwise, upload one in the sidebar.
DEFAULT_WORKBOOK = Path(__file__).with_name("COVID19_Filtered.xlsx")

ALIASES = {
    "date": ["date", "observationdate", "reportdate", "day"],
    "country": ["countryregion", "country", "location", "countriesregions", "nation"],
    "region": ["whoregion", "who_region", "region", "who region"],
    "confirmed": ["confirmed", "confirmedcases", "totalconfirmed"],
    "deaths": ["deaths", "death", "totaldeaths"],
    "recovered": ["recovered", "recoveries", "totalrecovered"],
    "active": ["active", "activecases", "totalactive"],
}


def key(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Rename familiar workbook headers into the dashboard's standard names."""
    normalized = frame.copy()
    lookup = {key(column): column for column in normalized.columns}
    rename = {}
    for standard, choices in ALIASES.items():
        for choice in choices:
            original = lookup.get(key(choice))
            if original is not None:
                rename[original] = standard
                break
    return normalized.rename(columns=rename)


def prepare_data(frame: pd.DataFrame) -> pd.DataFrame:
    data = normalize_columns(frame)
    required = ["date", "country", "confirmed", "deaths", "recovered"]
    missing = [column for column in required if column not in data.columns]
    if missing:
        raise ValueError("Could not find required column(s): " + ", ".join(missing))

    data["date"] = pd.to_datetime(data["date"], errors="coerce", dayfirst=False)
    data = data.dropna(subset=["date", "country"]).copy()
    data["country"] = data["country"].astype(str).str.strip()
    data = data[data["country"] != ""]
    if "region" not in data.columns:
        data["region"] = "Unknown"
    data["region"] = data["region"].fillna("Unknown").astype(str).str.strip().replace("", "Unknown")

    for column in ["confirmed", "deaths", "recovered", "active"]:
        if column not in data.columns:
            data[column] = pd.NA
        data[column] = pd.to_numeric(data[column], errors="coerce")
    # Keep legitimate zeros; only rows with no usable core metrics are excluded.
    data = data.dropna(subset=["confirmed", "deaths", "recovered"], how="all")
    if data.empty:
        raise ValueError("No rows with usable COVID metrics were found.")
    if data["active"].isna().all():
        data["active"] = data["confirmed"] - data["deaths"] - data["recovered"]
    else:
        data["active"] = data["active"].fillna(data["confirmed"] - data["deaths"] - data["recovered"])
    return data.sort_values("date")


def read_workbook(source: bytes | str, filename: str) -> tuple[dict[str, pd.DataFrame], str]:
    excel = pd.ExcelFile(BytesIO(source) if isinstance(source, bytes) else source)
    sheets = {name: pd.read_excel(excel, sheet_name=name) for name in excel.sheet_names}
    preferred = next((name for name in excel.sheet_names if key(name) == "fullgrouped"), excel.sheet_names[0])
    return sheets, preferred


st.markdown("""
<style>
    .stApp { background: #f4f7fb; }
    section[data-testid="stSidebar"] { background: #10243a; color: #f6f8fb; }
    
    /* Keep sidebar headings and labels light on the dark background */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] h4,
    section[data-testid="stSidebar"] h5,
    section[data-testid="stSidebar"] h6,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] label *,
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
    section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] *,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] .stCaption,
    section[data-testid="stSidebar"] .stCaption * {
        color: #f6f8fb !important;
    }

    /* Date range control: start date, end date, date separators, and calendar icon */
    section[data-testid="stSidebar"] [data-testid="stDateInputField"],
    section[data-testid="stSidebar"] [data-testid="stDateInputField"] *,
    section[data-testid="stSidebar"] [data-testid="stDateInputFieldsScroller"],
    section[data-testid="stSidebar"] [data-testid="stDateInputFieldsScroller"] *,
    section[data-testid="stSidebar"] [data-testid="stDateInput"] [role="spinbutton"],
    section[data-testid="stSidebar"] [data-testid="stDateInput"] [aria-hidden="true"],
    section[data-testid="stSidebar"] [data-testid="stDateInputCalendarButton"],
    section[data-testid="stSidebar"] [data-testid="stDateInputCalendarButton"] *,
    section[data-testid="stSidebar"] [data-testid="stDateInputCalendarButton"] svg,
    section[data-testid="stSidebar"] [data-testid="stDateInput"] svg,
    section[data-testid="stSidebar"] [data-testid="stDateInput"] input,
    section[data-testid="stSidebar"] .stDateInput [data-testid="stDateInputField"] *,
    [data-testid="stDateInputCalendar"],
    [data-testid="stDateInputCalendar"] *,
    [data-testid="stDateInputQuickSelect"],
    [data-testid="stDateInputQuickSelect"] * {
        color: #10243a !important;
    }

    /* Make text inside the workbook upload dark-colored */
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"],
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] *,
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"],
    section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] *,
    section[data-testid="stSidebar"] [data-testid="stFileUploader"] button,
    section[data-testid="stSidebar"] [data-testid="stFileUploader"] button *,
    section[data-testid="stSidebar"] [data-testid="stFileUploaderFileData"],
    section[data-testid="stSidebar"] [data-testid="stFileUploaderFileData"] *,
    section[data-testid="stSidebar"] [data-testid="stFileUploader"] svg,
    section[data-testid="stSidebar"] .stFileUploader [data-testid="stFileUploaderDropzone"] *,
    section[data-testid="stSidebar"] .stFileUploader button * {
        color: #10243a !important;
    }

    /* Make text inside the worksheet dropdown dark-colored */
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] > div:not([data-testid="stWidgetLabel"]),
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] > div:not([data-testid="stWidgetLabel"]) *,
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] [role="combobox"],
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] [role="combobox"] *,
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] input,
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] svg,
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] *,
    section[data-testid="stSidebar"] .stSelectbox > div:not([data-testid="stWidgetLabel"]) *,
    [data-testid="stSelectboxVirtualDropdown"],
    [data-testid="stSelectboxVirtualDropdown"] *,
    div[data-baseweb="popover"] [data-baseweb="menu"] *,
    div[role="listbox"],
    div[role="listbox"] * {
        color: #10243a !important;
    }

    /* Keep transparent icon bounding boxes from filling as solid dark squares */
    section[data-testid="stSidebar"] svg path[fill="none"] {
        fill: none !important;
    }

    /* General sidebar inputs readability */
    section[data-testid="stSidebar"] input,
    section[data-testid="stSidebar"] select,
    section[data-testid="stSidebar"] textarea {
        color: #10243a !important;
    }
    .hero { padding: 1.2rem 1.5rem; border-radius: 18px; color: white;
            background: linear-gradient(115deg, #10243a 0%, #145b73 100%); margin-bottom: 1rem; }
    .hero h1 { margin: 0 0 .35rem 0; font-size: 2rem; }
    .hero p { margin: 0; color: #d9e9ef; }
    div[data-testid="stMetric"] { background: white; border: 1px solid #e6edf3;
            border-radius: 14px; padding: 0.8rem 0.75rem; box-shadow: 0 3px 12px #10243a0b; }
    div[data-testid="stMetricValue"],
    div[data-testid="stMetricValue"] * {
        font-size: clamp(1.2rem, 1.8vw, 1.55rem) !important;
        white-space: nowrap;
    }
    h2, h3 { color: #17344d; }
</style>
<div class="hero">
  <h1>COVID-19 Data Dashboard</h1>
  <p>Explore reported cases, outcomes, and regional patterns over time.</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("Dashboard setup")
    st.caption("Start with the project workbook or upload your own Excel file.")
    uploaded = st.file_uploader("Upload COVID-19 Excel workbook", type=["xlsx", "xls"])

    source = None
    filename = ""
    if uploaded is not None:
        source, filename = uploaded.getvalue(), uploaded.name
    elif DEFAULT_WORKBOOK.exists():
        source, filename = str(DEFAULT_WORKBOOK), DEFAULT_WORKBOOK.name
        st.success(f"Using {filename}")
    else:
        st.info("No workbook found beside app.py. Upload the project workbook above.")

if source is None:
    st.info("**To get started:** upload `COVID19_Filtered.xlsx` using the control in the sidebar. The app will look for `full_grouped` automatically.")
    st.stop()

try:
    sheets, preferred_sheet = read_workbook(source, filename)
except Exception as exc:
    st.error(f"I couldn't open that workbook: {exc}")
    st.stop()

with st.sidebar:
    selected_sheet = st.selectbox("Worksheet", list(sheets), index=list(sheets).index(preferred_sheet))
try:
    data = prepare_data(sheets[selected_sheet])
except Exception as exc:
    st.error(f"The selected sheet could not be prepared. {exc}")
    st.caption("Expected columns include Date, Country/Region, Confirmed, Deaths, and Recovered. WHO Region and Active are optional.")
    st.stop()

st.caption(f"Source: **{filename}** · Sheet: **{selected_sheet}** · {len(data):,} usable records")

with st.sidebar:
    st.divider()
    st.subheader("Filters")
    min_date, max_date = data["date"].min().date(), data["date"].max().date()
    selected_dates = st.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
        start_date, end_date = selected_dates
    elif isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 1:
        start_date = end_date = selected_dates[0]
    else:
        start_date = end_date = selected_dates
    countries = sorted(data["country"].dropna().unique().tolist())
    selected_countries = st.multiselect("Countries", countries, default=countries)
    regions = sorted(data["region"].dropna().unique().tolist())
    selected_regions = st.multiselect("WHO regions", regions, default=regions)

filtered = data[
    data["date"].dt.date.between(start_date, end_date)
    & data["country"].isin(selected_countries)
    & data["region"].isin(selected_regions)
].copy()

if filtered.empty:
    st.warning("No records match those filters. Choose a wider date range or more countries and regions.")
    st.stop()

# These are cumulative snapshots: sum records only for the latest date in the current selection.
latest_date = filtered["date"].max()
latest = filtered[filtered["date"] == latest_date]
totals = latest[["confirmed", "deaths", "recovered", "active"]].sum(min_count=1).fillna(0)
st.markdown(f"### Snapshot on {latest_date.strftime('%d %b %Y')}")
kpis = st.columns(4)
for column, label, color in zip(kpis, ["Confirmed", "Deaths", "Recovered", "Active"], ["#1976d2", "#d9534f", "#23936b", "#e59b23"]):
    column.metric(label, f"{int(totals[label.lower()]):,}")

st.markdown("### Trends over time")
trend = filtered.groupby("date", as_index=False)[["confirmed", "deaths", "recovered"]].sum()
chart_cols = st.columns(2)
for target, metric, color in [(chart_cols[0], "confirmed", "#1976d2"), (chart_cols[1], "deaths", "#d9534f")]:
    fig = px.line(trend, x="date", y=metric, markers=True, color_discrete_sequence=[color], title=metric.title() + " over time")
    fig.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=55, b=10), xaxis_title="Date", yaxis_title="People", hovermode="x unified")
    target.plotly_chart(fig, use_container_width=True)
fig = px.line(trend, x="date", y="recovered", markers=True, color_discrete_sequence=["#23936b"], title="Recovered over time")
fig.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=55, b=10), xaxis_title="Date", yaxis_title="People", hovermode="x unified")
st.plotly_chart(fig, use_container_width=True)

st.markdown("### Country and region comparison")
left, right = st.columns(2)
top_countries = latest.groupby("country", as_index=False)["confirmed"].sum().nlargest(10, "confirmed").sort_values("confirmed")
bar = px.bar(top_countries, x="confirmed", y="country", orientation="h", title="Top 10 countries by confirmed cases", color="confirmed", color_continuous_scale="Blues")
bar.update_layout(template="plotly_white", coloraxis_showscale=False, margin=dict(l=10, r=10, t=55, b=10), xaxis_title="Confirmed cases", yaxis_title="")
left.plotly_chart(bar, use_container_width=True)
region_data = latest.groupby("region", as_index=False)[["confirmed", "deaths", "recovered", "active"]].sum().sort_values("confirmed", ascending=False)
region_long = region_data.melt(id_vars="region", value_vars=["confirmed", "deaths", "recovered"], var_name="metric", value_name="people")
region_fig = px.bar(region_long, x="region", y="people", color="metric", barmode="group", title="Latest totals by WHO region", color_discrete_map={"confirmed": "#1976d2", "deaths": "#d9534f", "recovered": "#23936b"})
region_fig.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=55, b=10), xaxis_title="WHO region", yaxis_title="People", legend_title="Metric")
right.plotly_chart(region_fig, use_container_width=True)

st.markdown("### Filtered data")
show_all = st.checkbox("Show all matching dates", value=False)
table = filtered.sort_values(["date", "confirmed"], ascending=[False, False])
if not show_all:
    table = latest.sort_values("confirmed", ascending=False)
st.dataframe(table.rename(columns={"date": "Date", "country": "Country", "region": "WHO Region"}), use_container_width=True, hide_index=True)
st.caption("KPI cards and comparisons use the latest date in the selected filters. Cumulative daily records are not added across dates. Zero values are preserved.")
