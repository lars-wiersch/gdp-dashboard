import streamlit as st
import pandas as pd
import math
from pathlib import Path

# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title="GDP dashboard",
    page_icon=":earth_americas:",
)

# -----------------------------------------------------------------------------
# Data loading helpers
@st.cache_data
def get_unemployment_data() -> pd.DataFrame:
    """Load unemployment data (SL.UEM.TOTL.ZS) from a World Bank CSV and return long-form.

    Output columns: Country Code, Year, Unemployment (%)
    """
    DATA_FILENAME = Path(__file__).parent / "data/unemployment_data.csv"
    raw_unemp_df = _read_world_bank_csv_data_table(DATA_FILENAME)

    raw_unemp_df = raw_unemp_df[raw_unemp_df["Indicator Code"] == "SL.UEM.TOTL.ZS"]

    year_cols = [c for c in raw_unemp_df.columns if isinstance(c, str) and c.isdigit()]

    unemp_df = raw_unemp_df.melt(
        id_vars=["Country Code"],
        value_vars=year_cols,
        var_name="Year",
        value_name="Unemployment rate",
    )

    unemp_df["Year"] = pd.to_numeric(unemp_df["Year"], errors="coerce")
    unemp_df["Unemployment rate"] = pd.to_numeric(unemp_df["Unemployment rate"], errors="coerce")

    unemp_df = unemp_df.dropna(subset=["Year"])
    unemp_df["Year"] = unemp_df["Year"].astype(int)

    return unemp_df

@st.cache_data
def _read_world_bank_csv_data_table(filename: Path) -> pd.DataFrame:
    """Read a World Bank CSV that may start with metadata lines before the real header.

    World Bank CSV downloads often begin with lines like:
      "Data Source","World Development Indicators",
      "Last Updated Date","2026-02-24",
    then the real header row begins with "Country Name","Country Code",...
    """
    with open(filename, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()

    header_idx = None
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith('"Country Name"') or stripped.startswith("Country Name"):
            header_idx = i
            break

    if header_idx is None:
        raise ValueError(f"Could not find World Bank header row in {filename}")

    return pd.read_csv(filename, skiprows=header_idx)


@st.cache_data
def get_gdp_data() -> pd.DataFrame:
    """Grab GDP data from a CSV file and return long-form: Country Code, Year, GDP."""
    DATA_FILENAME = Path(__file__).parent / "data/gdp_data.csv"
    raw_gdp_df = pd.read_csv(DATA_FILENAME)

    # Your GDP file is already in a simple format (no metadata lines),
    # and the app currently assumes 1960..2022 exist as columns.
    MIN_YEAR = 1960
    MAX_YEAR = 2022

    gdp_df = raw_gdp_df.melt(
        ["Country Code"],
        [str(x) for x in range(MIN_YEAR, MAX_YEAR + 1)],
        "Year",
        "GDP",
    )

    gdp_df["Year"] = pd.to_numeric(gdp_df["Year"], errors="coerce").astype(int)
    gdp_df["GDP"] = pd.to_numeric(gdp_df["GDP"], errors="coerce")

    return gdp_df


@st.cache_data
def get_population_data() -> pd.DataFrame:
    """Load population data (SP.POP.TOTL) from a World Bank CSV and return long-form.

    Output columns: Country Code, Year, Population
    """
    DATA_FILENAME = Path(__file__).parent / "data/population_data.csv"
    raw_pop_df = _read_world_bank_csv_data_table(DATA_FILENAME)

    # Keep only total population indicator
    raw_pop_df = raw_pop_df[raw_pop_df["Indicator Code"] == "SP.POP.TOTL"]

    # Year columns are strings like "1960", ..., and your file includes 2023..2025 too.
    year_cols = [c for c in raw_pop_df.columns if isinstance(c, str) and c.isdigit()]

    pop_df = raw_pop_df.melt(
        id_vars=["Country Code"],
        value_vars=year_cols,
        var_name="Year",
        value_name="Population",
    )

    pop_df["Year"] = pd.to_numeric(pop_df["Year"], errors="coerce")
    pop_df["Population"] = pd.to_numeric(pop_df["Population"], errors="coerce")

    # drop bad years, convert Year to int
    pop_df = pop_df.dropna(subset=["Year"])
    pop_df["Year"] = pop_df["Year"].astype(int)

    # guard against divide-by-zero
    pop_df.loc[pop_df["Population"] == 0, "Population"] = pd.NA

    return pop_df
    
@st.cache_data
def get_gdp_pc_ppp_data() -> pd.DataFrame:
    """Load GDP per capita, PPP (constant 2021 international $) and return long-form.

    Output columns: Country Code, Year, GDP per capita, PPP (const 2021 int $)
    """
    DATA_FILENAME = Path(__file__).parent / "data/gdp_pc_ppp.csv"
    raw_df = _read_world_bank_csv_data_table(DATA_FILENAME)

    raw_df = raw_df[raw_df["Indicator Code"] == "NY.GDP.PCAP.PP.KD"]

    year_cols = [c for c in raw_df.columns if isinstance(c, str) and c.isdigit()]

    out_df = raw_df.melt(
        id_vars=["Country Code"],
        value_vars=year_cols,
        var_name="Year",
        value_name="GDP pc PPP (const 2021 int$)",
    )

    out_df["Year"] = pd.to_numeric(out_df["Year"], errors="coerce")
    out_df["GDP pc PPP (const 2021 int$)"] = pd.to_numeric(
        out_df["GDP pc PPP (const 2021 int$)"], errors="coerce"
    )

    out_df = out_df.dropna(subset=["Year"])
    out_df["Year"] = out_df["Year"].astype(int)

    return out_df

# Load datasets
gdp_df = get_gdp_data()
pop_df = get_population_data()
unemp_df = get_unemployment_data()
gdp_pc_ppp_df = get_gdp_pc_ppp_data()

min_year = int(gdp_df["Year"].min())
max_year = int(gdp_df["Year"].max())

pop_df = pop_df[pop_df["Year"].between(min_year, max_year)]
unemp_df = unemp_df[unemp_df["Year"].between(min_year, max_year)]
gdp_pc_ppp_df = gdp_pc_ppp_df[gdp_pc_ppp_df["Year"].between(min_year, max_year)]

df = gdp_df.merge(pop_df, on=["Country Code", "Year"], how="left")
df = df.merge(unemp_df, on=["Country Code", "Year"], how="left")
df = df.merge(gdp_pc_ppp_df, on=["Country Code", "Year"], how="left")

df["GDP per capita"] = df["GDP"] / df["Population"]

# -----------------------------------------------------------------------------
# Draw the actual page

"""
# :earth_americas: GDP dashboard

Browse GDP data from the [World Bank Open Data](https://data.worldbank.org/) website.  
Now includes **GDP per capita** (GDP divided by population).
"""

# Add some spacing
""
""

from_year, to_year = st.slider(
    "Which years are you interested in?",
    min_value=min_year,
    max_value=max_year,
    value=[min_year, max_year],
)

countries = df["Country Code"].dropna().unique()

selected_countries = st.multiselect(
    "Which countries would you like to view?",
    countries,
    ["DEU", "FRA", "GBR", "BRA", "MEX", "JPN"],
)

metric = st.radio(
    "Metric",
    options=[
        "GDP",
        "GDP per capita",
        "GDP pc PPP (const 2021 int$)",
        "Unemployment rate",
    ],
    horizontal=True,
)

""
""
""

# Filter the data
filtered_df = df[
    (df["Country Code"].isin(selected_countries))
    & (df["Year"] <= to_year)
    & (from_year <= df["Year"])
]

st.header(f"{metric} over time", divider="gray")
""

st.line_chart(
    filtered_df,
    x="Year",
    y=metric,
    color="Country Code",
)

""
""

# Cards for the selected end-year
first_year_df = df[df["Year"] == from_year]
last_year_df = df[df["Year"] == to_year]

st.header(f"{metric} in {to_year}", divider="gray")
""

cols = st.columns(4)

def _format_value(metric_name: str, value: float) -> str:
    if pd.isna(value):
        return "n/a"
    if metric_name == "GDP":
        return f"{value/1_000_000_000:,.0f}B"
    if metric_name == "Unemployment rate":
        return f"{value:,.1f}%"
    if metric_name == "GDP pc PPP (const 2021 int$)":
        return f"{value:,.0f}"
    return f"{value:,.0f}"

for i, country in enumerate(selected_countries):
    col = cols[i % len(cols)]
    with col:
        first_series = first_year_df.loc[first_year_df["Country Code"] == country, metric]
        last_series = last_year_df.loc[last_year_df["Country Code"] == country, metric]

        if first_series.empty or last_series.empty:
            st.metric(label=f"{country} {metric}", value="n/a", delta="n/a", delta_color="off")
            continue

        first_val = first_series.iloc[0]
        last_val = last_series.iloc[0]

        if pd.isna(first_val) or pd.isna(last_val) or first_val == 0:
            growth = "n/a"
            delta_color = "off"
        else:
            growth = f"{last_val / first_val:,.2f}x"
            delta_color = "normal"

        st.metric(
            label=f"{country} {metric}",
            value=_format_value(metric, last_val),
            delta=growth,
            delta_color=delta_color,
        )
