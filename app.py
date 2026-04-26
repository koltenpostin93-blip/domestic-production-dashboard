import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
from datetime import date

# ── Constants ────────────────────────────────────────────────────────────────
API_KEY   = st.secrets["NASS_API_KEY"]
BASE_URL  = "https://quickstats.nass.usda.gov/api/api_GET/"
THIS_YEAR = date.today().year

# JPSI brand colors — sourced directly from jpsi.com computed styles
DARK_BG   = "#4a4849"   # JPSI top banner dark
DARK_CARD = "#3a3838"   # slightly deeper card surface
DARK_ALT  = "#1f1f1f"   # JPSI footer dark (sidebar, deepest bg)
TEAL      = "#5ba5af"   # JPSI primary CTA teal
TEAL_DIM  = "#3d7a84"   # darker teal for hover / secondary accents
AMBER     = "#f59e0b"
GREEN     = "#22c55e"
RED       = "#ef4444"
WHITE     = "#ffffff"
GRAY      = "#b0abab"   # warm gray to match JPSI's warm dark palette
BLUE      = TEAL        # alias so chart helpers keep working

STATE_ABBREV = {
    "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR",
    "CALIFORNIA": "CA", "COLORADO": "CO", "CONNECTICUT": "CT", "DELAWARE": "DE",
    "FLORIDA": "FL", "GEORGIA": "GA", "HAWAII": "HI", "IDAHO": "ID",
    "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA", "KANSAS": "KS",
    "KENTUCKY": "KY", "LOUISIANA": "LA", "MAINE": "ME", "MARYLAND": "MD",
    "MASSACHUSETTS": "MA", "MICHIGAN": "MI", "MINNESOTA": "MN", "MISSISSIPPI": "MS",
    "MISSOURI": "MO", "MONTANA": "MT", "NEBRASKA": "NE", "NEVADA": "NV",
    "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ", "NEW MEXICO": "NM", "NEW YORK": "NY",
    "NORTH CAROLINA": "NC", "NORTH DAKOTA": "ND", "OHIO": "OH", "OKLAHOMA": "OK",
    "OREGON": "OR", "PENNSYLVANIA": "PA", "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC",
    "SOUTH DAKOTA": "SD", "TENNESSEE": "TN", "TEXAS": "TX", "UTAH": "UT",
    "VERMONT": "VT", "VIRGINIA": "VA", "WASHINGTON": "WA", "WEST VIRGINIA": "WV",
    "WISCONSIN": "WI", "WYOMING": "WY",
}
ABBREV_STATE = {v: k for k, v in STATE_ABBREV.items()}

# ── Commodity definitions — add new crops here ───────────────────────────────
# Each commodity maps metric labels to NASS QuickStats parameters.
COMMODITIES = {
    "Corn": {
        "Planted Acres":   {"commodity_desc": "CORN", "statisticcat_desc": "AREA PLANTED",  "unit_desc": "ACRES",      "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Harvested Acres": {"commodity_desc": "CORN", "statisticcat_desc": "AREA HARVESTED","unit_desc": "ACRES",      "reference_period_desc": "YEAR", "source_desc": "SURVEY", "util_practice_desc": "GRAIN"},
        "Yield (Bu/Ac)":   {"commodity_desc": "CORN", "statisticcat_desc": "YIELD",         "unit_desc": "BU / ACRE",  "reference_period_desc": "YEAR", "source_desc": "SURVEY", "util_practice_desc": "GRAIN"},
        "Production (Bu)": {"commodity_desc": "CORN", "statisticcat_desc": "PRODUCTION",    "unit_desc": "BU",         "reference_period_desc": "YEAR", "source_desc": "SURVEY", "util_practice_desc": "GRAIN"},
    },
    "Soybeans": {
        "Planted Acres":   {"commodity_desc": "SOYBEANS", "statisticcat_desc": "AREA PLANTED",  "unit_desc": "ACRES",     "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Harvested Acres": {"commodity_desc": "SOYBEANS", "statisticcat_desc": "AREA HARVESTED","unit_desc": "ACRES",     "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Yield (Bu/Ac)":   {"commodity_desc": "SOYBEANS", "statisticcat_desc": "YIELD",         "unit_desc": "BU / ACRE", "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Production (Bu)": {"commodity_desc": "SOYBEANS", "statisticcat_desc": "PRODUCTION",    "unit_desc": "BU",        "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
    },
    "Wheat": {
        "Planted Acres":   {"commodity_desc": "WHEAT", "statisticcat_desc": "AREA PLANTED",  "unit_desc": "ACRES",     "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Harvested Acres": {"commodity_desc": "WHEAT", "statisticcat_desc": "AREA HARVESTED","unit_desc": "ACRES",     "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Yield (Bu/Ac)":   {"commodity_desc": "WHEAT", "statisticcat_desc": "YIELD",         "unit_desc": "BU / ACRE", "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Production (Bu)": {"commodity_desc": "WHEAT", "statisticcat_desc": "PRODUCTION",    "unit_desc": "BU",        "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
    },
    "Cotton": {
        "Planted Acres":            {"commodity_desc": "COTTON", "statisticcat_desc": "AREA PLANTED",  "unit_desc": "ACRES",        "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Harvested Acres":          {"commodity_desc": "COTTON", "statisticcat_desc": "AREA HARVESTED","unit_desc": "ACRES",        "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Yield (Lb/Ac)":            {"commodity_desc": "COTTON", "statisticcat_desc": "YIELD",         "unit_desc": "LB / ACRE",    "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Production (480 Lb Bales)":{"commodity_desc": "COTTON", "statisticcat_desc": "PRODUCTION",    "unit_desc": "480 LB BALES", "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
    },
    "Sorghum": {
        "Planted Acres":   {"commodity_desc": "SORGHUM", "statisticcat_desc": "AREA PLANTED",  "unit_desc": "ACRES",     "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Harvested Acres": {"commodity_desc": "SORGHUM", "statisticcat_desc": "AREA HARVESTED","unit_desc": "ACRES",     "reference_period_desc": "YEAR", "source_desc": "SURVEY", "util_practice_desc": "GRAIN"},
        "Yield (Bu/Ac)":   {"commodity_desc": "SORGHUM", "statisticcat_desc": "YIELD",         "unit_desc": "BU / ACRE", "reference_period_desc": "YEAR", "source_desc": "SURVEY", "util_practice_desc": "GRAIN"},
        "Production (Bu)": {"commodity_desc": "SORGHUM", "statisticcat_desc": "PRODUCTION",    "unit_desc": "BU",        "reference_period_desc": "YEAR", "source_desc": "SURVEY", "util_practice_desc": "GRAIN"},
    },
    "Barley": {
        "Planted Acres":   {"commodity_desc": "BARLEY", "statisticcat_desc": "AREA PLANTED",  "unit_desc": "ACRES",     "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Harvested Acres": {"commodity_desc": "BARLEY", "statisticcat_desc": "AREA HARVESTED","unit_desc": "ACRES",     "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Yield (Bu/Ac)":   {"commodity_desc": "BARLEY", "statisticcat_desc": "YIELD",         "unit_desc": "BU / ACRE", "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Production (Bu)": {"commodity_desc": "BARLEY", "statisticcat_desc": "PRODUCTION",    "unit_desc": "BU",        "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
    },
    "Canola": {
        "Planted Acres":    {"commodity_desc": "CANOLA", "statisticcat_desc": "AREA PLANTED",  "unit_desc": "ACRES",     "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Harvested Acres":  {"commodity_desc": "CANOLA", "statisticcat_desc": "AREA HARVESTED","unit_desc": "ACRES",     "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Yield (Lb/Ac)":    {"commodity_desc": "CANOLA", "statisticcat_desc": "YIELD",         "unit_desc": "LB / ACRE", "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Production (Lb)":  {"commodity_desc": "CANOLA", "statisticcat_desc": "PRODUCTION",    "unit_desc": "LB",        "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
    },
    "Sugarbeets": {
        "Planted Acres":       {"commodity_desc": "SUGARBEETS", "statisticcat_desc": "AREA PLANTED",  "unit_desc": "ACRES",      "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Harvested Acres":     {"commodity_desc": "SUGARBEETS", "statisticcat_desc": "AREA HARVESTED","unit_desc": "ACRES",      "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Yield (Tons/Ac)":     {"commodity_desc": "SUGARBEETS", "statisticcat_desc": "YIELD",         "unit_desc": "TONS / ACRE","reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Production (Tons)":   {"commodity_desc": "SUGARBEETS", "statisticcat_desc": "PRODUCTION",    "unit_desc": "TONS",       "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
    },
    "Peanuts": {
        "Planted Acres":   {"commodity_desc": "PEANUTS", "statisticcat_desc": "AREA PLANTED",  "unit_desc": "ACRES",     "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Harvested Acres": {"commodity_desc": "PEANUTS", "statisticcat_desc": "AREA HARVESTED","unit_desc": "ACRES",     "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Yield (Lb/Ac)":   {"commodity_desc": "PEANUTS", "statisticcat_desc": "YIELD",         "unit_desc": "LB / ACRE", "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Production (Lb)": {"commodity_desc": "PEANUTS", "statisticcat_desc": "PRODUCTION",    "unit_desc": "LB",        "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
    },
    "Hay": {
        "Planted Acres":      {"commodity_desc": "HAY", "statisticcat_desc": "AREA PLANTED",  "unit_desc": "ACRES",      "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Harvested Acres":    {"commodity_desc": "HAY", "statisticcat_desc": "AREA HARVESTED","unit_desc": "ACRES",      "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Yield (Tons/Ac)":    {"commodity_desc": "HAY", "statisticcat_desc": "YIELD",         "unit_desc": "TONS / ACRE","reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Production (Tons)":  {"commodity_desc": "HAY", "statisticcat_desc": "PRODUCTION",    "unit_desc": "TONS",       "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
    },
    "Sunflower": {
        "Planted Acres":   {"commodity_desc": "SUNFLOWER", "statisticcat_desc": "AREA PLANTED",  "unit_desc": "ACRES",     "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Harvested Acres": {"commodity_desc": "SUNFLOWER", "statisticcat_desc": "AREA HARVESTED","unit_desc": "ACRES",     "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Yield (Lb/Ac)":   {"commodity_desc": "SUNFLOWER", "statisticcat_desc": "YIELD",         "unit_desc": "LB / ACRE", "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
        "Production (Lb)": {"commodity_desc": "SUNFLOWER", "statisticcat_desc": "PRODUCTION",    "unit_desc": "LB",        "reference_period_desc": "YEAR", "source_desc": "SURVEY"},
    },
}

COMMODITY_ICONS = {
    "Corn": "🌽", "Soybeans": "🫘", "Wheat": "🌾", "Cotton": "🪴", "Sorghum": "🌿",
    "Barley": "🫚", "Canola": "🌼", "Sugarbeets": "🟤", "Peanuts": "🥜",
    "Hay": "🌱", "Sunflower": "🌻",
}

LOGO_WHITE = "https://www.jpsi.com/wp-content/themes/gate39media/img/logo-white.png"
LOGO_FULL  = "https://www.jpsi.com/wp-content/themes/gate39media/img/logo-full.png"

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Domestic Production | JSA",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700&display=swap');

  .stApp {{ background-color: {DARK_BG}; color: {WHITE}; font-family: 'Open Sans', sans-serif; }}
  section[data-testid="stSidebar"] {{ background-color: {DARK_ALT}; border-right: 1px solid #1e2226; }}
  section[data-testid="stSidebar"] * {{ font-family: 'Open Sans', sans-serif; }}

  /* Top accent bar */
  .jsa-topbar {{
    background: linear-gradient(90deg, {TEAL} 0%, {TEAL_DIM} 100%);
    height: 5px;
    width: 100%;
    margin-bottom: 0;
  }}

  /* Page header */
  .jsa-header {{
    display: flex;
    align-items: center;
    gap: 18px;
    padding: 18px 0 14px;
    border-bottom: 1px solid #4a5568;
    margin-bottom: 20px;
  }}
  .jsa-header img {{ height: 36px; }}
  .jsa-header-divider {{
    width: 1px; height: 36px;
    background: #4a5568;
  }}
  .jsa-header-title {{
    font-size: 20px;
    font-weight: 700;
    color: {WHITE};
    letter-spacing: -0.01em;
  }}
  .jsa-header-sub {{
    font-size: 12px;
    color: {GRAY};
    margin-top: 2px;
    font-weight: 400;
  }}

  /* Sidebar logo area */
  .jsa-sidebar-logo {{
    padding: 20px 0 16px;
    text-align: center;
    border-bottom: 1px solid #3a3f44;
    margin-bottom: 4px;
  }}
  .jsa-sidebar-logo img {{ height: 28px; }}

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] {{
    background-color: {DARK_CARD};
    border-radius: 6px;
    gap: 2px;
    border: 1px solid #4a5568;
  }}
  .stTabs [data-baseweb="tab"] {{
    color: {GRAY};
    border-radius: 5px;
    font-family: 'Open Sans', sans-serif;
    font-size: 13px;
    font-weight: 600;
  }}
  .stTabs [aria-selected="true"] {{
    color: {WHITE};
    background-color: {BLUE} !important;
  }}

  /* Sidebar labels */
  div[data-testid="stSelectbox"] label,
  div[data-testid="stMultiSelect"] label,
  div[data-testid="stSlider"] label {{
    color: {GRAY} !important;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}

  /* KPI cards */
  .kpi-card {{
    background: {DARK_CARD};
    border-radius: 8px;
    padding: 18px 20px 14px;
    border-top: 3px solid {BLUE};
    border-left: none;
    height: 100%;
    box-shadow: 0 2px 8px rgba(0,0,0,0.25);
  }}
  .kpi-label  {{ color: {GRAY}; font-size: 11px; font-weight: 700;
                 text-transform: uppercase; letter-spacing: .08em; margin-bottom: 8px; }}
  .kpi-value  {{ color: {WHITE}; font-size: 28px; font-weight: 700; line-height: 1.1;
                 font-family: 'Open Sans', sans-serif; }}
  .kpi-year   {{ color: {GRAY}; font-size: 11px; margin-top: 5px; }}
  .kpi-delta  {{ font-size: 13px; margin-top: 3px; font-weight: 600; }}
  .pos {{ color: {GREEN}; }}
  .neg {{ color: {RED}; }}

  .data-note {{
    background: {DARK_CARD};
    border-left: 3px solid {AMBER};
    padding: 8px 14px;
    border-radius: 4px;
    font-size: 13px;
    color: {GRAY};
  }}
  hr {{ border-color: #4a5568; margin: 16px 0; }}

  /* Pill-style radio filter */
  div[data-testid="stRadio"] > label {{ display: none; }}
  div[data-testid="stRadio"] > div {{
    display: flex; gap: 8px; flex-wrap: wrap;
  }}
  div[data-testid="stRadio"] > div > label {{
    background: {DARK_CARD};
    border: 1px solid #4a5568;
    border-radius: 20px;
    padding: 6px 18px;
    color: {GRAY};
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
  }}
  div[data-testid="stRadio"] > div > label:hover {{
    border-color: {TEAL};
    color: {WHITE};
  }}
  div[data-testid="stRadio"] > div > label[data-checked="true"] {{
    background: {TEAL};
    border-color: {TEAL};
    color: {WHITE};
  }}
</style>
""", unsafe_allow_html=True)

# ── API helpers ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def _fetch(params: dict) -> pd.DataFrame:
    p = {**params, "key": API_KEY, "format": "JSON"}
    try:
        r = requests.get(BASE_URL, params=p, timeout=30)
        d = r.json()
        return pd.DataFrame(d.get("data", []))
    except Exception as e:
        st.error(f"NASS API error: {e}")
        return pd.DataFrame()

def _clean(val) -> float | None:
    try:
        return float(str(val).replace(",", "").strip())
    except Exception:
        return None

def _fmt(v: float, metric: str) -> str:
    if "Yield" in metric or "/Ac" in metric:
        return f"{v:.1f}"
    if v >= 1_000_000_000:
        return f"{v/1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"{v/1_000:.1f}K"
    return f"{v:,.0f}"

def _ytick(metric: str) -> str:
    return ".1f" if ("Yield" in metric or "/Ac" in metric) else ",.0f"

def _bar_label(v: float, metric: str) -> str:
    """Format bar chart labels: production in millions with unit suffix, acres in M ac, yield as-is."""
    if "Production" in metric:
        unit = metric.split("(")[-1].replace(")", "").strip()
        if unit == "Bu":
            return f"{v/1_000_000:.1f}M Bu"
        elif unit == "Lb":
            return f"{v/1_000_000:.1f}M Lbs"
        elif unit == "Tons":
            return f"{v/1_000_000:.1f}M T"
        elif "Bales" in unit:
            return f"{v/1_000:.0f}K Bales"
    if "Acres" in metric:
        return f"{v/1_000_000:.1f}M Ac"
    return _fmt(v, metric)

# ── Data loaders ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def load_national(commodity: str, y0: int, y1: int) -> pd.DataFrame:
    params_map = COMMODITIES[commodity]
    frames = []
    for label, mp in params_map.items():
        df = _fetch({
            **mp,
            "agg_level_desc": "NATIONAL",
            "domain_desc":    "TOTAL",
            "freq_desc":      "ANNUAL",
            "year__GE":       str(y0),
            "year__LE":       str(y1),
        })
        if df.empty:
            continue
        df = df[["year", "Value"]].copy()
        df["year"]   = df["year"].astype(int)
        df["value"]  = df["Value"].apply(_clean)
        df["metric"] = label
        df = df.dropna(subset=["value"]).sort_values("year")
        df = df.drop_duplicates(subset=["year"])
        frames.append(df)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def load_state_snapshot(commodity: str, year: int) -> pd.DataFrame:
    params_map = COMMODITIES[commodity]
    frames = []
    for label, mp in params_map.items():
        df = _fetch({
            **mp,
            "agg_level_desc": "STATE",
            "domain_desc":    "TOTAL",
            "freq_desc":      "ANNUAL",
            "year":           str(year),
        })
        if df.empty:
            continue
        df["value"]      = df["Value"].apply(_clean)
        df["state_abbr"] = df["state_name"].str.upper().map(STATE_ABBREV)
        df["metric"]     = label
        df = df.dropna(subset=["value", "state_abbr"])
        df = df.drop_duplicates(subset=["state_abbr"])
        frames.append(df[["state_name", "state_abbr", "value", "metric"]])
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

@st.cache_data(ttl=3600, show_spinner=False)
def load_state_history(commodity: str, metric: str, y0: int, y1: int) -> pd.DataFrame:
    mp = COMMODITIES[commodity][metric]
    df = _fetch({
        **mp,
        "agg_level_desc": "STATE",
        "domain_desc":    "TOTAL",
        "freq_desc":      "ANNUAL",
        "year__GE":       str(y0),
        "year__LE":       str(y1),
    })
    if df.empty:
        return pd.DataFrame()
    df["year"]       = df["year"].astype(int)
    df["value"]      = df["Value"].apply(_clean)
    df["state_abbr"] = df["state_name"].str.upper().map(STATE_ABBREV)
    df = df.dropna(subset=["value", "state_abbr"])
    df = df.drop_duplicates(subset=["year", "state_abbr"])
    return df[["year", "value", "state_abbr", "state_name"]].sort_values(["state_abbr", "year"])

# ── Chart base theme ─────────────────────────────────────────────────────────
def _base_layout(fig, title="", height=390):
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color=WHITE)),
        plot_bgcolor=DARK_CARD, paper_bgcolor=DARK_CARD,
        font=dict(color=WHITE, family="sans-serif"),
        height=height,
        margin=dict(l=55, r=20, t=48, b=40),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=WHITE)),
        xaxis=dict(gridcolor="#4a5568", linecolor="#4a5568", tickfont=dict(color=GRAY)),
        yaxis=dict(gridcolor="#4a5568", linecolor="#4a5568", tickfont=dict(color=GRAY)),
        hoverlabel=dict(bgcolor=DARK_ALT, font_color=WHITE, bordercolor=BLUE),
    )
    return fig

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f"<div class='jsa-sidebar-logo'><img src='{LOGO_WHITE}' alt='JSA Logo'></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='color:{GRAY};font-size:11px;text-align:center;margin:-8px 0 12px;'>"
        f"DOMESTIC PRODUCTION</p>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    commodity = st.selectbox(
        "Commodity",
        list(COMMODITIES.keys()),
        format_func=lambda c: f"{COMMODITY_ICONS.get(c, '')}  {c}",
    )
    metric_list = list(COMMODITIES[commodity].keys())

    st.markdown("---")
    year_range = st.slider("Historical Range", 1980, THIS_YEAR, (1990, THIS_YEAR), step=1)

    st.markdown("---")
    st.markdown(f"<p style='color:{GRAY};font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.05em'>State Level</p>", unsafe_allow_html=True)
    map_year = st.selectbox("Map Year", list(range(THIS_YEAR, 1999, -1)))

    st.markdown("---")
    st.markdown(f"<p style='color:{GRAY};font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.05em'>State Trend</p>", unsafe_allow_html=True)
    trend_metric = st.selectbox("Trend Metric", metric_list, key="trend_m")
    trend_states = st.multiselect(
        "States",
        sorted(STATE_ABBREV.values()),
        default=["IA", "IL", "NE", "MN", "IN"],
    )

# ── Header ───────────────────────────────────────────────────────────────────
icon = COMMODITY_ICONS.get(commodity, "")
st.markdown("<div class='jsa-topbar'></div>", unsafe_allow_html=True)
st.markdown(f"""
<div class='jsa-header'>
  <img src='{LOGO_WHITE}' alt='JSA'>
  <div class='jsa-header-divider'></div>
  <div>
    <div class='jsa-header-title'>{icon} {commodity} Production Dashboard</div>
    <div class='jsa-header-sub'>National &amp; State Level &nbsp;·&nbsp; USDA NASS Annual Data &nbsp;·&nbsp; John Stewart &amp; Associates</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Load data ────────────────────────────────────────────────────────────────
with st.spinner("Fetching USDA NASS data..."):
    nat_df     = load_national(commodity, year_range[0], year_range[1])
    snap_df    = load_state_snapshot(commodity, map_year)
    state_hist = load_state_history(commodity, trend_metric, year_range[0], year_range[1]) if trend_states else pd.DataFrame()

# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_nat, tab_state = st.tabs(["  📊  National Overview  ", "  🗺️  State Level  "])

# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — NATIONAL
# ═════════════════════════════════════════════════════════════════════════════
with tab_nat:
    if nat_df.empty:
        st.warning("No national data returned from NASS for this commodity/year range.")
        st.stop()

    latest = int(nat_df["year"].max())
    prev   = latest - 1

    # Flag if latest year is current — data may be preliminary or incomplete
    if latest == THIS_YEAR:
        st.markdown(
            f"<div class='data-note'>⚠️ <b>{THIS_YEAR} data is preliminary</b> — NASS releases estimates throughout the year. "
            f"Some metrics may not yet be available.</div><br>",
            unsafe_allow_html=True,
        )

    def get_val(metric, yr):
        rows = nat_df[(nat_df["metric"] == metric) & (nat_df["year"] == yr)]
        return float(rows["value"].values[0]) if len(rows) else None

    # ── KPI cards ────────────────────────────────────────────────────────────
    cols = st.columns(len(metric_list), gap="small")
    for i, metric in enumerate(metric_list):
        v      = get_val(metric, latest)
        v_prev = get_val(metric, prev)
        label  = metric.split("(")[0].strip()

        if v is None:
            cols[i].markdown(
                f"<div class='kpi-card'><div class='kpi-label'>{label}</div>"
                f"<div class='kpi-value' style='font-size:18px;color:{GRAY}'>Not yet available</div>"
                f"<div class='kpi-year'>{latest}</div></div>",
                unsafe_allow_html=True,
            )
            continue

        delta_html = ""
        if v_prev:
            pct  = (v - v_prev) / v_prev * 100
            cls  = "pos" if pct >= 0 else "neg"
            sign = "▲" if pct >= 0 else "▼"
            delta_html = f"<div class='kpi-delta {cls}'>{sign} {abs(pct):.1f}% vs {prev}</div>"

        unit = f" {metric.split('(')[-1].replace(')', '')}" if "(" in metric else ""
        cols[i].markdown(
            f"<div class='kpi-card'>"
            f"<div class='kpi-label'>{label}</div>"
            f"<div class='kpi-value'>{_fmt(v, metric)}</div>"
            f"{delta_html}"
            f"<div class='kpi-year'>{latest}{' — preliminary' if latest == THIS_YEAR else ''}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── 4 trend charts (2×2) ──────────────────────────────────────────────────
    col_left, col_right = st.columns(2, gap="medium")
    panels = [col_left, col_right, col_left, col_right]

    for idx, metric in enumerate(metric_list):
        mdf = nat_df[nat_df["metric"] == metric].sort_values("year")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=mdf["year"], y=mdf["value"],
            mode="lines+markers",
            line=dict(color=BLUE, width=2.5),
            marker=dict(size=4, color=BLUE),
            fill="tozeroy",
            fillcolor="rgba(6,147,227,0.10)",
            name=metric,
            hovertemplate=f"<b>%{{x}}</b><br>{metric}: %{{y:{_ytick(metric)}}}<extra></extra>",
        ))
        fig.update_yaxes(tickformat=_ytick(metric))
        _base_layout(fig, title=metric)
        panels[idx % 4].plotly_chart(fig, use_container_width=True)

    # ── Production vs Harvested Acres dual-axis ───────────────────────────────
    prod_label = [m for m in metric_list if "Production" in m]
    harv_label = [m for m in metric_list if "Harvested" in m]

    if prod_label and harv_label:
        st.markdown(f"<h3 style='color:{WHITE};margin-bottom:4px'>Production vs. Harvested Acres</h3>", unsafe_allow_html=True)
        prod  = nat_df[nat_df["metric"] == prod_label[0]].sort_values("year")
        harv  = nat_df[nat_df["metric"] == harv_label[0]].sort_values("year")
        combo = prod.merge(harv, on="year", suffixes=("_prod", "_harv"))

        fig_dual = go.Figure()
        fig_dual.add_trace(go.Bar(
            x=combo["year"], y=combo["value_harv"],
            name="Harvested Acres",
            marker_color=BLUE, opacity=0.65, yaxis="y",
            hovertemplate="<b>%{x}</b><br>Harvested: %{y:,.0f} ac<extra></extra>",
        ))
        fig_dual.add_trace(go.Scatter(
            x=combo["year"], y=combo["value_prod"],
            name=prod_label[0],
            line=dict(color=AMBER, width=2.5),
            mode="lines+markers", marker=dict(size=4),
            yaxis="y2",
            hovertemplate=f"<b>%{{x}}</b><br>Production: %{{y:,.0f}}<extra></extra>",
        ))
        fig_dual.update_layout(
            plot_bgcolor=DARK_CARD, paper_bgcolor=DARK_CARD,
            font=dict(color=WHITE), height=420,
            margin=dict(l=65, r=65, t=30, b=40),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=WHITE)),
            hoverlabel=dict(bgcolor=DARK_ALT, font_color=WHITE, bordercolor=BLUE),
            xaxis=dict(gridcolor="#4a5568", tickfont=dict(color=GRAY)),
            yaxis=dict(title="Harvested Acres", tickformat=",.0f", gridcolor="#4a5568",
                       tickfont=dict(color=GRAY), title_font=dict(color=GRAY)),
            yaxis2=dict(title=prod_label[0], overlaying="y", side="right",
                        tickformat=",.0f", gridcolor="rgba(0,0,0,0)",
                        tickfont=dict(color=AMBER), title_font=dict(color=AMBER)),
        )
        st.plotly_chart(fig_dual, use_container_width=True)

    # ── Yield trend with 5-yr rolling avg ────────────────────────────────────
    yield_label = [m for m in metric_list if "Yield" in m]
    if yield_label:
        st.markdown(f"<h3 style='color:{WHITE};margin-bottom:4px'>Yield Trend with 5-Year Rolling Average</h3>", unsafe_allow_html=True)
        ydf = nat_df[nat_df["metric"] == yield_label[0]].sort_values("year").copy()
        ydf["roll5"] = ydf["value"].rolling(5, center=True).mean()

        fig_yield = go.Figure()
        fig_yield.add_trace(go.Bar(
            x=ydf["year"], y=ydf["value"],
            name="Annual Yield",
            marker_color=BLUE, opacity=0.6,
            hovertemplate="<b>%{x}</b><br>Yield: %{y:.1f}<extra></extra>",
        ))
        fig_yield.add_trace(go.Scatter(
            x=ydf["year"], y=ydf["roll5"],
            name="5-Yr Avg",
            line=dict(color=AMBER, width=2.5, dash="dash"),
            mode="lines",
            hovertemplate="<b>%{x}</b><br>5-Yr Avg: %{y:.1f}<extra></extra>",
        ))
        _base_layout(fig_yield, height=380)
        fig_yield.update_yaxes(tickformat=".1f", title=yield_label[0], title_font=dict(color=GRAY))
        st.plotly_chart(fig_yield, use_container_width=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — STATE LEVEL
# ═════════════════════════════════════════════════════════════════════════════
with tab_state:
    if snap_df.empty:
        st.warning(f"No state data available for {commodity} in {map_year}.")
        st.stop()

    # ── Metric pill filter ────────────────────────────────────────────────────
    prod_default = next((m for m in metric_list if "Production" in m), metric_list[0])
    map_metric = st.radio(
        "State metric",
        metric_list,
        index=metric_list.index(prod_default),
        horizontal=True,
        label_visibility="collapsed",
    )
    st.markdown("<div style='margin-bottom:12px'></div>", unsafe_allow_html=True)

    metric_snap = snap_df[snap_df["metric"] == map_metric].copy()

    if not metric_snap.empty:
        # ── Choropleth ───────────────────────────────────────────────────────
        fig_map = px.choropleth(
            metric_snap,
            locations="state_abbr",
            locationmode="USA-states",
            color="value",
            scope="usa",
            color_continuous_scale=[[0, "#1a2a2c"], [0.4, "#5ba5af"], [1, "#b8dde2"]],
            hover_name="state_name",
            hover_data={"value": ":,.0f", "state_abbr": False},
            labels={"value": map_metric},
            title=f"{commodity} — {map_metric} by State ({map_year})",
        )
        fig_map.update_layout(
            geo=dict(bgcolor=DARK_BG, lakecolor=DARK_BG, landcolor=DARK_CARD, showlakes=True, showcoastlines=False),
            plot_bgcolor=DARK_BG, paper_bgcolor=DARK_BG,
            font=dict(color=WHITE),
            title_font=dict(size=15, color=WHITE),
            coloraxis_colorbar=dict(
                title=dict(text=map_metric, font=dict(color=GRAY, size=11)),
                tickfont=dict(color=WHITE), bgcolor=DARK_CARD, bordercolor=DARK_ALT,
            ),
            height=460,
            margin=dict(l=0, r=0, t=50, b=0),
        )
        st.plotly_chart(fig_map, use_container_width=True)

        # ── Top-15 bar ───────────────────────────────────────────────────────
        top15 = metric_snap.sort_values("value", ascending=False).head(15)
        fig_bar = go.Figure(go.Bar(
            x=top15["state_abbr"], y=top15["value"],
            marker_color=BLUE,
            text=top15["value"].apply(lambda v: _bar_label(v, map_metric)),
            textposition="outside", textfont=dict(color=WHITE, size=11),
            hovertemplate="<b>%{x}</b><br>" + map_metric + ": %{y:" + _ytick(map_metric) + "}<extra></extra>",
        ))
        _base_layout(fig_bar, title=f"Top 15 States — {map_metric} ({map_year})", height=400)
        fig_bar.update_yaxes(tickformat=_ytick(map_metric))
        fig_bar.update_layout(showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)

    # ── State historical trend ────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"<h3 style='color:{WHITE};margin-bottom:4px'>State Historical Trend — {trend_metric}</h3>", unsafe_allow_html=True)

    STATE_COLORS = [BLUE, AMBER, GREEN, RED, "#a78bfa", "#f97316", "#06b6d4", "#ec4899", "#84cc16", "#e879f9"]

    if not trend_states:
        st.info("Select states in the sidebar to view historical trends.")
    elif state_hist.empty:
        st.warning("No state history data returned.")
    else:
        fig_trend = go.Figure()
        for i, abbr in enumerate(trend_states):
            s = state_hist[state_hist["state_abbr"] == abbr].sort_values("year")
            if s.empty:
                continue
            label = s["state_name"].iloc[0].title()
            fig_trend.add_trace(go.Scatter(
                x=s["year"], y=s["value"],
                mode="lines+markers", name=label,
                line=dict(color=STATE_COLORS[i % len(STATE_COLORS)], width=2),
                marker=dict(size=4),
                hovertemplate=f"<b>{label}</b><br>%{{x}}: %{{y:{_ytick(trend_metric)}}}<extra></extra>",
            ))
        _base_layout(fig_trend, title=f"{commodity} {trend_metric} — {', '.join(trend_states)}", height=430)
        fig_trend.update_yaxes(tickformat=_ytick(trend_metric))
        st.plotly_chart(fig_trend, use_container_width=True)

    # ── State vs National comparison ─────────────────────────────────────────
    if trend_states and not state_hist.empty:
        st.markdown(f"<h3 style='color:{WHITE};margin-bottom:4px'>State vs. U.S. — {trend_metric}</h3>", unsafe_allow_html=True)

        nat_metric = nat_df[nat_df["metric"] == trend_metric][["year", "value"]].rename(columns={"value": "national"})

        fig_vs = go.Figure()
        fig_vs.add_trace(go.Scatter(
            x=nat_metric["year"], y=nat_metric["national"],
            mode="lines", name="U.S.",
            line=dict(color=WHITE, width=2, dash="dot"),
            hovertemplate="<b>U.S.</b><br>%{x}: %{y:" + _ytick(trend_metric) + "}<extra></extra>",
        ))
        for i, abbr in enumerate(trend_states):
            s = state_hist[state_hist["state_abbr"] == abbr].sort_values("year")
            if s.empty:
                continue
            label = s["state_name"].iloc[0].title()
            fig_vs.add_trace(go.Scatter(
                x=s["year"], y=s["value"],
                mode="lines+markers", name=label,
                line=dict(color=STATE_COLORS[i % len(STATE_COLORS)], width=2),
                marker=dict(size=4),
                hovertemplate=f"<b>{label}</b><br>%{{x}}: %{{y:{_ytick(trend_metric)}}}<extra></extra>",
            ))
        _base_layout(fig_vs, title="", height=410)
        fig_vs.update_yaxes(tickformat=_ytick(trend_metric))
        st.plotly_chart(fig_vs, use_container_width=True)
