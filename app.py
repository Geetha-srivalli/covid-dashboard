from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="COVID-19 | Data dashboard", page_icon="🦠", layout="wide")

DEFAULT_WORKBOOK = Path(__file__).with_name("COVID19_Filtered.xlsx")

ALIASES = {
    "date": ["date", "observationdate", "reportdate", "day"],
    "country": ["countryregion", "country", "location", "countriesregions", "nation"],
    "region": ["whoregion", "who_region", "region", "who region"],
    "confirmed": ["confirmed", "confirmedcases", "totalconfirmed"],
    "deaths": ["deaths", "death", "totaldeaths"],
    "recovered": ["recovered", "recoveries", "totalrecovered"],
    "active": ["active", "activecases", "totalactive"],
    "new_cases": ["newcases", "dailynewcases", "newconfirmed"],
    "new_deaths": ["newdeaths", "dailynewdeaths"],
    "new_recovered": ["newrecovered", "newrecoveries", "dailynewrecovered"],
}

COUNTRY_MAP_NAMES = {
    "US": "United States",
    "Korea, South": "South Korea",
    "Taiwan*": "Taiwan",
    "Congo (Kinshasa)": "Democratic Republic of the Congo",
    "Congo (Brazzaville)": "Republic of the Congo",
    "Burma": "Myanmar",
    "Cote d'Ivoire": "Ivory Coast",
    "West Bank and Gaza": "Palestine",
    "Holy See": "Vatican City",
}

METRICS = ["confirmed", "deaths", "recovered", "active"]
DAILY_METRICS = ["new_cases", "new_deaths", "new_recovered"]
MODULES = [
    "Overview",
    "Data Analysis",
    "Country Details",
    "World Map",
    "Upload & Preview",
    "Data & About",
]


def key(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()
    lookup = {key(column): column for column in data.columns}
    rename = {}
    for standard, choices in ALIASES.items():
        for choice in choices:
            original = lookup.get(key(choice))
            if original is not None:
                rename[original] = standard
                break
    return data.rename(columns=rename)


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

    for column in METRICS + DAILY_METRICS:
        if column not in data.columns:
            data[column] = pd.NA
        data[column] = pd.to_numeric(data[column], errors="coerce")

    # Keep zero-valued records. Drop a row only when all core measures are missing.
    data = data.dropna(subset=METRICS[:3], how="all")
    if data.empty:
        raise ValueError("No rows with usable COVID metrics were found.")

    data = data.sort_values(["country", "date"]).copy()
    if data["active"].isna().all():
        data["active"] = data["confirmed"] - data["deaths"] - data["recovered"]
    else:
        derived_active = data["confirmed"] - data["deaths"] - data["recovered"]
        data["active"] = data["active"].fillna(derived_active)

    # Use supplied daily measures when available. Otherwise derive day-to-day
    # differences within each country; negative corrections are retained.
    cumulative_for_daily = {
        "new_cases": "confirmed",
        "new_deaths": "deaths",
        "new_recovered": "recovered",
    }
    for daily, cumulative in cumulative_for_daily.items():
        derived = data.groupby("country", sort=False)[cumulative].diff()
        first_record = data.groupby("country", sort=False).cumcount() == 0
        derived = derived.where(~first_record, data[cumulative])
        data[daily] = data[daily].fillna(derived)

    return data.sort_values("date").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def read_excel_bytes(contents: bytes) -> tuple[dict[str, pd.DataFrame], str]:
    excel = pd.ExcelFile(BytesIO(contents))
    sheets = {name: pd.read_excel(excel, sheet_name=name) for name in excel.sheet_names}
    preferred = next((name for name in excel.sheet_names if key(name) == "fullgrouped"), excel.sheet_names[0])
    return sheets, preferred


@st.cache_data(show_spinner=False)
def read_csv_bytes(contents: bytes) -> pd.DataFrame:
    return pd.read_csv(BytesIO(contents))


def sum_latest(frame: pd.DataFrame) -> pd.Series:
    latest_date = frame["date"].max()
    latest_rows = frame[frame["date"] == latest_date]
    return latest_rows[METRICS].sum(min_count=1).fillna(0)


def make_trend(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    return frame.groupby("date", as_index=False)[columns].sum(min_count=1).sort_values("date")


def moneyless_number(value: float | int) -> str:
    return f"{int(value):,}"


st.markdown(
    """
    <style>
      .stApp { background: #f4f7fb; }
      section[data-testid="stSidebar"] { background: #10243a; }
      section[data-testid="stSidebar"] h1,
      section[data-testid="stSidebar"] h2,
      section[data-testid="stSidebar"] h3,
      section[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
      section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
      section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #f6f8fb; }
      section[data-testid="stSidebar"] [data-baseweb="select"] *,
      section[data-testid="stSidebar"] [data-testid="stDateInput"] input,
      section[data-testid="stSidebar"] [data-testid="stFileUploader"] *,
      section[data-testid="stSidebar"] [data-testid="stAlert"] * { color: #263445 !important; }
      .hero { padding: 1.2rem 1.5rem; border-radius: 18px; color: white;
              background: linear-gradient(115deg, #10243a 0%, #145b73 100%); margin-bottom: 1rem; }
      .hero h1 { margin: 0 0 .35rem 0; font-size: 2rem; }
      .hero p { margin: 0; color: #d9e9ef; }
      div[data-testid="stMetric"] { background: white; border: 1px solid #e6edf3;
              border-radius: 14px; padding: 1rem; box-shadow: 0 3px 12px #10243a0b; }
      h2, h3 { color: #17344d; }
    </style>
    <div class="hero">
      <h1>COVID-19 Data Dashboard</h1>
      <p>Explore reported cases, outcomes, and regional patterns over time.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.title("Dashboard setup")
    st.caption("Choose a module, filter the data, or upload your own file.")
    module = st.radio("Modules", MODULES, index=0)
    st.divider()
    uploaded = st.file_uploader(
        "Use your own COVID dataset",
        type=["xlsx", "xls", "csv"],
        help="Your upload is private to your current visit and will not replace the shared project dataset.",
    )

if uploaded is not None:
    filename = uploaded.name
    contents = uploaded.getvalue()
    try:
        if filename.lower().endswith(".csv"):
            sheets = {"Uploaded CSV": read_csv_bytes(contents)}
            preferred_sheet = "Uploaded CSV"
        else:
            sheets, preferred_sheet = read_excel_bytes(contents)
    except Exception as exc:
        st.error(f"I couldn't read that upload: {exc}")
        st.stop()
    source_label = "Visitor upload (this session only)"
elif DEFAULT_WORKBOOK.exists():
    filename = DEFAULT_WORKBOOK.name
    try:
        sheets, preferred_sheet = read_excel_bytes(DEFAULT_WORKBOOK.read_bytes())
    except Exception as exc:
        st.error(f"I couldn't open the project workbook: {exc}")
        st.stop()
    source_label = "Project workbook"
else:
    st.info("Upload an Excel workbook or CSV in the left sidebar to start exploring.")
    st.stop()

with st.sidebar:
    selected_sheet = st.selectbox("Worksheet", list(sheets), index=list(sheets).index(preferred_sheet))

try:
    data = prepare_data(sheets[selected_sheet])
except Exception as exc:
    st.error(f"The selected sheet could not be prepared. {exc}")
    st.caption("Required columns include Date, Country/Region, Confirmed, Deaths, and Recovered. WHO Region and Active are optional.")
    st.stop()

with st.sidebar:
    st.caption(f"Source: {filename} · {len(data):,} usable records")
    st.divider()
    st.subheader("Filters")
    min_date, max_date = data["date"].min().date(), data["date"].max().date()
    date_value = st.date_input("Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    if isinstance(date_value, (tuple, list)) and len(date_value) == 2:
        start_date, end_date = date_value
    elif isinstance(date_value, (tuple, list)) and len(date_value) == 1:
        start_date = end_date = date_value[0]
    else:
        start_date = end_date = date_value

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

latest_date = filtered["date"].max()
latest_totals = sum_latest(filtered)
latest_rows = filtered[filtered["date"] == latest_date]
st.caption(f"{source_label} · Sheet: {selected_sheet} · {len(filtered):,} records in the selected filters")


def show_kpis(totals: pd.Series) -> None:
    st.markdown(f"### Snapshot on {latest_date.strftime('%d %b %Y')}")
    columns = st.columns(4)
    labels = [("Confirmed", "confirmed"), ("Deaths", "deaths"), ("Recovered", "recovered"), ("Active", "active")]
    for column, (label, field) in zip(columns, labels):
        column.metric(label, moneyless_number(totals[field]))


def chart_layout(fig, height: int | None = None):
    fig.update_layout(
        template="plotly_white",
        margin=dict(l=12, r=12, t=55, b=12),
        hovermode="x unified",
        height=height,
    )
    return fig


if module == "Overview":
    show_kpis(latest_totals)
    st.markdown("### Trends over time")
    trend = make_trend(filtered, METRICS[:3])
    trend_cols = st.columns(2)
    for target, metric, color in [
        (trend_cols[0], "confirmed", "#1976d2"),
        (trend_cols[1], "deaths", "#d9534f"),
    ]:
        fig = px.line(trend, x="date", y=metric, markers=True, color_discrete_sequence=[color], title=f"{metric.title()} over time")
        target.plotly_chart(chart_layout(fig), use_container_width=True)
    recovered_fig = px.line(trend, x="date", y="recovered", markers=True, color_discrete_sequence=["#23936b"], title="Recovered over time")
    st.plotly_chart(chart_layout(recovered_fig), use_container_width=True)

    st.markdown("### Country and region comparison")
    left, right = st.columns(2)
    top = latest_rows.groupby("country", as_index=False)["confirmed"].sum().nlargest(10, "confirmed").sort_values("confirmed")
    top_fig = px.bar(top, x="confirmed", y="country", orientation="h", title="Top 10 countries by confirmed cases", color="confirmed", color_continuous_scale="Blues")
    top_fig.update_layout(coloraxis_showscale=False, xaxis_title="Confirmed cases", yaxis_title="")
    left.plotly_chart(chart_layout(top_fig), use_container_width=True)
    region_data = latest_rows.groupby("region", as_index=False)[METRICS].sum().sort_values("confirmed", ascending=False)
    region_long = region_data.melt(id_vars="region", value_vars=METRICS[:3], var_name="metric", value_name="people")
    region_fig = px.bar(region_long, x="region", y="people", color="metric", barmode="group", title="Latest totals by WHO region", color_discrete_map={"confirmed": "#1976d2", "deaths": "#d9534f", "recovered": "#23936b"})
    region_fig.update_layout(xaxis_title="WHO region", yaxis_title="People", legend_title="Metric")
    right.plotly_chart(chart_layout(region_fig), use_container_width=True)

elif module == "Data Analysis":
    show_kpis(latest_totals)
    confirmed = latest_totals["confirmed"]
    case_fatality = latest_totals["deaths"] / confirmed * 100 if confirmed else None
    recovery_rate = latest_totals["recovered"] / confirmed * 100 if confirmed else None
    rate_cols = st.columns(2)
    rate_cols[0].metric("Case fatality rate", f"{case_fatality:.2f}%" if case_fatality is not None else "—", help="Deaths ÷ confirmed cases on the snapshot date.")
    rate_cols[1].metric("Recovery rate", f"{recovery_rate:.2f}%" if recovery_rate is not None else "—", help="Recovered ÷ confirmed cases on the snapshot date.")
    st.caption("These simple outcome ratios describe the selected snapshot; they are not individual risk predictions.")

    st.markdown("### Daily reported changes")
    daily = make_trend(filtered, DAILY_METRICS)
    daily_labels = {"new_cases": "New cases", "new_deaths": "New deaths", "new_recovered": "New recoveries"}
    daily_long = daily.rename(columns=daily_labels).melt(id_vars="date", var_name="measure", value_name="people")
    daily_fig = px.line(daily_long, x="date", y="people", color="measure", title="Daily new cases, deaths, and recoveries", color_discrete_map={"New cases": "#1976d2", "New deaths": "#d9534f", "New recoveries": "#23936b"})
    daily_fig.update_layout(xaxis_title="Date", yaxis_title="Reported people", legend_title="Measure")
    st.plotly_chart(chart_layout(daily_fig), use_container_width=True)

    st.markdown("### Compare countries and regions")
    left, right = st.columns(2)
    top = latest_rows.groupby("country", as_index=False)["confirmed"].sum().nlargest(10, "confirmed").sort_values("confirmed")
    top_fig = px.bar(top, x="confirmed", y="country", orientation="h", title="Top 10 countries at snapshot", color="confirmed", color_continuous_scale="Blues")
    top_fig.update_layout(coloraxis_showscale=False, xaxis_title="Confirmed cases", yaxis_title="")
    left.plotly_chart(chart_layout(top_fig), use_container_width=True)
    by_region = latest_rows.groupby("region", as_index=False)[METRICS].sum()
    region_long = by_region.melt(id_vars="region", value_vars=METRICS[:3], var_name="measure", value_name="people")
    region_fig = px.bar(region_long, x="region", y="people", color="measure", barmode="group", title="Snapshot totals by WHO region", color_discrete_map={"confirmed": "#1976d2", "deaths": "#d9534f", "recovered": "#23936b"})
    right.plotly_chart(chart_layout(region_fig), use_container_width=True)

    st.markdown("### Download selected records")
    csv_data = filtered.sort_values(["date", "country"]).to_csv(index=False).encode("utf-8")
    st.download_button("Download filtered data (CSV)", data=csv_data, file_name=f"covid_filtered_{latest_date:%Y%m%d}.csv", mime="text/csv")

elif module == "Country Details":
    country_choices = sorted(filtered["country"].unique().tolist())
    selected_country = st.selectbox("Choose a country", country_choices)
    country_data = filtered[filtered["country"] == selected_country].sort_values("date")
    country_latest = sum_latest(country_data)
    show_kpis(country_latest)
    region_name = country_data["region"].dropna().iloc[-1] if not country_data.empty else "Unknown"
    st.caption(f"WHO region: {region_name} · {len(country_data):,} records in the selected date range")

    cumulative = make_trend(country_data, METRICS[:3])
    cumulative_long = cumulative.melt(id_vars="date", value_vars=METRICS[:3], var_name="measure", value_name="people")
    cumulative_fig = px.line(cumulative_long, x="date", y="people", color="measure", markers=True, title=f"Cumulative totals for {selected_country}", color_discrete_map={"confirmed": "#1976d2", "deaths": "#d9534f", "recovered": "#23936b"})
    st.plotly_chart(chart_layout(cumulative_fig), use_container_width=True)
    daily = make_trend(country_data, DAILY_METRICS)
    daily_fig = px.bar(daily, x="date", y="new_cases", title=f"Daily new cases in {selected_country}", color_discrete_sequence=["#1976d2"])
    daily_fig.update_layout(xaxis_title="Date", yaxis_title="New cases")
    st.plotly_chart(chart_layout(daily_fig), use_container_width=True)

elif module == "World Map":
    st.markdown(f"### Country comparison on {latest_date.strftime('%d %b %Y')}")
    map_metric = st.selectbox("Map measure", METRICS, format_func=lambda item: item.title())
    map_data = latest_rows.groupby("country", as_index=False)[METRICS].sum()
    map_data["map_country"] = map_data["country"].replace(COUNTRY_MAP_NAMES)
    map_fig = px.choropleth(
        map_data,
        locations="map_country",
        locationmode="country names",
        color=map_metric,
        hover_name="country",
        hover_data={map_metric: ":,", "map_country": False},
        color_continuous_scale="Blues",
        title=f"{map_metric.title()} by country",
    )
    map_fig.update_geos(showframe=False, showcoastlines=True, projection_type="natural earth")
    map_fig.update_layout(template="plotly_white", margin=dict(l=0, r=0, t=55, b=0), height=560, coloraxis_colorbar_title=map_metric.title())
    st.plotly_chart(map_fig, use_container_width=True)
    st.caption("Map colors use the latest cumulative snapshot in your current filters. Some territories may not match the map's country-name list.")

elif module == "Upload & Preview":
    st.markdown("### Explore your own dataset")
    st.write("Use **Use your own COVID dataset** in the left sidebar. Choose a CSV or Excel workbook; if it has multiple sheets, choose the worksheet below the upload control. The dashboard modules will then use your selected file.")
    st.info("Your upload is only used for your current visit. It does not replace or edit the shared project workbook, and other visitors cannot see your upload.")
    st.markdown("#### Dataset summary")
    summary_cols = st.columns(4)
    summary_cols[0].metric("Rows", f"{len(data):,}")
    summary_cols[1].metric("Countries", f"{data['country'].nunique():,}")
    summary_cols[2].metric("First date", data["date"].min().strftime("%d %b %Y"))
    summary_cols[3].metric("Last date", data["date"].max().strftime("%d %b %Y"))
    st.markdown("#### Required columns and data check")
    st.write("Required: date, country, confirmed, deaths, recovered. WHO region, active, and daily measures are used when present; daily measures are calculated from cumulative records if absent.")
    st.dataframe(data.head(100), use_container_width=True, hide_index=True)
    st.caption("Preview shows up to 100 rows. Zero values are valid and are kept.")

elif module == "Data & About":
    source_tab, definitions_tab, about_tab = st.tabs(["Data sources", "Definitions", "About this project"])
    with source_tab:
        st.subheader("Current data source")
        st.write(f"**File:** {filename}")
        st.write(f"**Worksheet:** {selected_sheet}")
        st.write(f"**Rows with usable records:** {len(data):,}")
        st.write(f"**Date coverage:** {data['date'].min():%d %b %Y} to {data['date'].max():%d %b %Y}")
        if uploaded is not None:
            st.info("This is a visitor-provided file for this session. It is not saved as the shared source.")
        else:
            st.info("This is the project workbook packaged with the public app. Check its original workbook or project notes for the source citation.")
    with definitions_tab:
        st.subheader("How to read the dashboard")
        st.markdown(
            "- **Confirmed, deaths, recovered, and active** are cumulative snapshots. KPI totals use the latest date available inside the selected filters.\n"
            "- **New cases, new deaths, and new recoveries** are daily changes. If an uploaded file lacks daily measures, the dashboard derives date-to-date differences by country.\n"
            "- **Case fatality rate** is deaths divided by confirmed cases on the snapshot date. **Recovery rate** is recovered divided by confirmed cases on that date.\n"
            "- Zero values are retained. Negative daily changes can appear when the source reports a correction."
        )
    with about_tab:
        st.subheader("COVID-19 Data Dashboard")
        st.write("An interactive learning prototype for exploring reported COVID-19 cases, outcomes, and regional patterns.")
        st.write("Use the module selector and filters to explore the included project workbook or upload a separate dataset for your own session.")
        st.caption("This historical dataset ends on 27 July 2020. The dashboard does not fetch current COVID-19 figures automatically.")

st.divider()
st.caption("Cumulative totals are taken from the latest available date in the current selection; records are not summed across the full date history.")
