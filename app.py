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

# Approximate geographic centers for state label placement
STATE_CENTERS = {
    "AL":(32.8,-86.8),"AZ":(34.3,-111.1),"AR":(34.8,-92.2),"CA":(37.2,-119.5),
    "CO":(39.0,-105.5),"CT":(41.6,-72.7),"DE":(39.0,-75.5),"FL":(28.6,-81.5),
    "GA":(32.9,-83.4),"ID":(44.4,-114.6),"IL":(40.0,-89.2),"IN":(39.9,-86.3),
    "IA":(42.1,-93.5),"KS":(38.5,-98.4),"KY":(37.5,-85.3),"LA":(31.0,-91.8),
    "ME":(45.4,-69.0),"MD":(39.1,-76.8),"MA":(42.2,-71.5),"MI":(44.3,-85.4),
    "MN":(46.4,-93.1),"MS":(32.7,-89.7),"MO":(38.4,-92.6),"MT":(47.0,-110.0),
    "NE":(41.5,-99.9),"NV":(39.3,-117.1),"NH":(43.7,-71.6),"NJ":(40.2,-74.7),
    "NM":(34.5,-106.1),"NY":(42.9,-75.5),"NC":(35.5,-79.4),"ND":(47.5,-100.5),
    "OH":(40.3,-82.8),"OK":(35.6,-97.5),"OR":(44.1,-120.5),"PA":(40.9,-77.8),
    "SC":(33.8,-80.9),"SD":(44.4,-100.2),"TN":(35.8,-86.4),"TX":(31.1,-97.6),
    "UT":(39.4,-111.1),"VT":(44.0,-72.7),"VA":(37.8,-79.5),"WA":(47.4,-120.5),
    "WV":(38.6,-80.6),"WI":(44.3,-89.8),"WY":(43.0,-107.6),
}

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


LOGO_WHITE = "https://www.jpsi.com/wp-content/themes/gate39media/img/logo-white.png"
LOGO_FULL  = "https://www.jpsi.com/wp-content/themes/gate39media/img/logo-full.png"

# ── State comparison table structure ─────────────────────────────────────────
# Each group renders individual state rows → subtotal row → spacer row.
# Groups without a subtotal key still get a spacer except the last one.
STATE_TABLE_GROUPS = [
    {"states": ["IL", "IN", "OH", "MI", "KY"], "subtotal": "Eastern Corn Belt Total"},
    {"states": ["IA", "NE", "KS"],              "subtotal": "UP States"},
    {"states": ["MN", "SD", "ND"],              "subtotal": "BN States"},
    {"states": ["MS", "AR", "LA", "TN"],        "subtotal": "Delta Total"},
    {"states": ["WI", "MO", "TX"],              "subtotal": None},   # no subtotal; US Total follows
]

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
    for attempt in range(2):
        try:
            r = requests.get(BASE_URL, params=p, timeout=60)
            d = r.json()
            return pd.DataFrame(d.get("data", []))
        except requests.exceptions.Timeout:
            if attempt == 0:
                continue   # one automatic retry
            st.warning("NASS API timed out after two attempts. Try refreshing in a moment.")
            return pd.DataFrame()
        except Exception as e:
            st.error(f"NASS API error: {e}")
            return pd.DataFrame()
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
    if "Yield" in metric:
        unit = metric.split("(")[-1].replace(")", "").strip()   # Bu/Ac, Lb/Ac, Tons/Ac
        return f"{v:.0f} {unit}"
    if "Acres" in metric:
        return f"{v/1_000_000:.1f}M Ac"
    if "Production" in metric:
        unit = metric.split("(")[-1].replace(")", "").strip()
        if "Bu" in unit:
            return f"{v/1_000_000:.0f}M Bu"
        elif "Lb" in unit:
            return f"{v/1_000_000:.0f}M Lbs"
        elif "Ton" in unit:
            return f"{v/1_000_000:.0f}M Tons"
        elif "Bales" in unit:
            return f"{v/1_000:.0f}K Bales"
    return _fmt(v, metric)

def _olympic6(vals):
    """6-year olympic average: remove highest & lowest, average the rest.
    Accepts up to 6 values (or however many are non-null); needs ≥3 to compute."""
    clean = sorted(v for v in vals if v is not None and not pd.isna(v))
    if len(clean) < 3:
        return None
    return sum(clean[1:-1]) / len(clean[1:-1])

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

PERIOD_PRIORITY = [
    "YEAR",
    "YEAR - NOV FORECAST",
    "YEAR - SEP FORECAST",
    "YEAR - AUG FORECAST",
    "YEAR - JUN ACREAGE",
    "YEAR - JUL FORECAST",
]

@st.cache_data(ttl=3600, show_spinner=False)
def load_state_snapshot(commodity: str, year: int) -> pd.DataFrame:
    params_map = COMMODITIES[commodity]
    frames = []
    for label, mp in params_map.items():
        # Strip reference_period so we get all periods, then pick the best per state
        base = {k: v for k, v in mp.items() if k != "reference_period_desc"}
        df = _fetch({
            **base,
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
        df = df[df["value"] > 0]  # drop suppressed zero rows

        # For each state pick the best available period in priority order
        best_rows = []
        for abbr, grp in df.groupby("state_abbr"):
            for period in PERIOD_PRIORITY:
                row = grp[grp["reference_period_desc"] == period]
                if not row.empty:
                    best_rows.append(row.iloc[0])
                    break
        if not best_rows:
            continue
        result = pd.DataFrame(best_rows)
        frames.append(result[["state_name", "state_abbr", "value", "metric"]])
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
    )
    metric_list = list(COMMODITIES[commodity].keys())

    st.markdown("---")
    year_range = st.slider("Historical Range", 1980, THIS_YEAR, (1990, THIS_YEAR), step=1)

    st.markdown("---")
    st.markdown(f"<p style='color:{GRAY};font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.05em'>State Level</p>", unsafe_allow_html=True)
    map_year = st.selectbox("Map Year", list(range(THIS_YEAR - 1, 1999, -1)))


# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("<div class='jsa-topbar'></div>", unsafe_allow_html=True)
st.markdown(f"""
<div class='jsa-header'>
  <img src='{LOGO_WHITE}' alt='JSA'>
  <div class='jsa-header-divider'></div>
  <div>
    <div class='jsa-header-title'>{commodity} Production Dashboard</div>
    <div class='jsa-header-sub'>National &amp; State Level &nbsp;·&nbsp; USDA NASS Annual Data &nbsp;·&nbsp; John Stewart &amp; Associates</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Load data ────────────────────────────────────────────────────────────────
with st.spinner("Fetching USDA NASS data..."):
    nat_df  = load_national(commodity, year_range[0], year_range[1])
    snap_df = load_state_snapshot(commodity, map_year)

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
    else:
        # ── Metric pill filter ────────────────────────────────────────────────
        prod_default = next((m for m in metric_list if "Production" in m), metric_list[0])
        map_metric = st.radio(
            "State metric",
            metric_list,
            index=metric_list.index(prod_default),
            horizontal=True,
            label_visibility="collapsed",
        )
        st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)

        metric_snap = snap_df[snap_df["metric"] == map_metric].copy()

        if metric_snap.empty:
            st.warning(f"No state data for {map_metric} in {map_year}.")
        else:
            # ── Choropleth ───────────────────────────────────────────────────
            fig_map = px.choropleth(
                metric_snap,
                locations="state_abbr",
                locationmode="USA-states",
                color="value",
                scope="usa",
                color_continuous_scale=[[0, "#1a2a2c"], [0.4, "#5ba5af"], [1, "#b8dde2"]],
                hover_name="state_name",
                hover_data={"value": ":,.0f", "state_abbr": False},
                custom_data=["state_abbr", "state_name"],
                labels={"value": map_metric},
                title=f"{commodity} — {map_metric} by State ({map_year})",
            )
            fig_map.update_layout(
                geo=dict(bgcolor=DARK_BG, lakecolor=DARK_BG, landcolor=DARK_CARD,
                         showlakes=True, showcoastlines=False),
                plot_bgcolor=DARK_BG, paper_bgcolor=DARK_BG,
                font=dict(color=WHITE),
                title_font=dict(size=15, color=WHITE),
                coloraxis_colorbar=dict(
                    title=dict(text=map_metric, font=dict(color=GRAY, size=11)),
                    tickfont=dict(color=WHITE), bgcolor=DARK_CARD, bordercolor=DARK_ALT,
                ),
                height=480,
                margin=dict(l=0, r=0, t=50, b=0),
                dragmode=False,
            )
            # White state borders
            fig_map.update_traces(
                selector=dict(type="choropleth"),
                marker_line_color="white",
                marker_line_width=0.6,
                hovertemplate="<b>%{customdata[1]}</b> (%{customdata[0]})<br>"
                              + map_metric + ": %{z:,.0f}<extra></extra>",
            )

            # State value labels via scattergeo
            lbl_lats, lbl_lons, lbl_texts = [], [], []
            for _, row in metric_snap.iterrows():
                abbr = row["state_abbr"]
                if abbr in STATE_CENTERS:
                    lbl_lats.append(STATE_CENTERS[abbr][0])
                    lbl_lons.append(STATE_CENTERS[abbr][1])
                    lbl_texts.append(_bar_label(row["value"], map_metric))
            fig_map.add_trace(go.Scattergeo(
                lat=lbl_lats, lon=lbl_lons, text=lbl_texts,
                mode="text",
                textfont=dict(color=WHITE, size=8, family="Open Sans"),
                showlegend=False,
                hoverinfo="skip",
            ))

            # Map is the filter — click a state to select it
            map_event = st.plotly_chart(
                fig_map,
                use_container_width=True,
                on_select="rerun",
                key=f"map_{commodity}_{map_year}_{map_metric}",
                config={"scrollZoom": False, "displayModeBar": False},
            )

            # ── Resolve selected state from click event ───────────────────────
            valid_abbrs = set(metric_snap["state_abbr"].tolist())

            if map_event and map_event.selection and map_event.selection.points:
                pt  = map_event.selection.points[0]
                cd  = pt.get("customdata") or []
                abbr_from_click = cd[0] if len(cd) >= 1 else pt.get("location")
                if abbr_from_click in valid_abbrs:
                    st.session_state["sel_state"] = abbr_from_click

            # Validate persisted selection is still in current data
            persisted = st.session_state.get("sel_state")
            if persisted not in valid_abbrs:
                persisted = None
                st.session_state["sel_state"] = None

            selected_abbr = persisted
            selected_name = ABBREV_STATE.get(selected_abbr, "").title() if selected_abbr else None

            # Clear button
            c1, c2 = st.columns([1, 5])
            if selected_abbr:
                c1.caption(f"Selected: **{selected_abbr}**")
                if c2.button("✕ Clear", key="clear_state"):
                    st.session_state["sel_state"] = None
                    st.rerun()
            else:
                c1.caption("Click a state on the map")

            # ── Top-15 bar ───────────────────────────────────────────────────
            top15 = metric_snap.sort_values("value", ascending=False).head(15)
            bar_colors = [
                TEAL if row["state_abbr"] == selected_abbr else TEAL_DIM
                for _, row in top15.iterrows()
            ]
            fig_bar = go.Figure(go.Bar(
                x=top15["state_abbr"],
                y=top15["value"],
                marker_color=bar_colors,
                text=top15["value"].apply(lambda v: _bar_label(v, map_metric)),
                textposition="outside",
                textfont=dict(color=WHITE, size=11),
                hovertemplate="<b>%{x}</b><br>" + map_metric + ": %{y:" + _ytick(map_metric) + "}<extra></extra>",
            ))
            _base_layout(fig_bar, title=f"Top 15 States — {map_metric} ({map_year})", height=400)
            fig_bar.update_yaxes(tickformat=_ytick(map_metric))
            fig_bar.update_layout(showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

            # ── 10-Year State Comparison Table ────────────────────────────────
            st.markdown(
                f"<p style='color:{GRAY};font-size:12px;font-weight:700;text-transform:uppercase;"
                f"letter-spacing:.06em;margin:20px 0 6px'>10-Year State Comparison — {map_metric}</p>",
                unsafe_allow_html=True,
            )

            tbl_y0         = map_year - 9
            tbl_years_list = list(range(tbl_y0, map_year + 1))

            with st.spinner("Loading comparison table..."):
                tbl_shist = load_state_history(commodity, map_metric, tbl_y0, map_year)

            # National values — reuse the already-fetched nat_df (no extra API call)
            nat_yr_vals = (
                nat_df[
                    (nat_df["metric"] == map_metric) &
                    (nat_df["year"].between(tbl_y0, map_year))
                ]
                .set_index("year")["value"].to_dict()
            )
            nat_recent6  = [nat_yr_vals.get(yr) for yr in tbl_years_list[-6:]]
            nat_olym_val = _olympic6(nat_recent6)

            # Per-state year→value lookups
            all_abbrs = [a for grp in STATE_TABLE_GROUPS for a in grp["states"]]
            state_yr_vals = {}
            for abbr in all_abbrs:
                sdf = tbl_shist[tbl_shist["state_abbr"] == abbr]
                state_yr_vals[abbr] = {int(r["year"]): r["value"] for _, r in sdf.iterrows()}

            def _build_row(label, yr_map, row_type="state"):
                row = {"label": label, "row_type": row_type}
                all_vals = []
                for yr in tbl_years_list:
                    v = yr_map.get(yr)
                    row[yr] = v
                    if v is not None:
                        all_vals.append(v)
                recent6  = [yr_map.get(yr) for yr in tbl_years_list[-6:]]
                olym     = _olympic6(recent6)
                row["olym"]    = olym
                row["min_val"] = min(all_vals) if all_vals else None
                row["max_val"] = max(all_vals) if all_vals else None
                row["pct_us"]  = (olym / nat_olym_val * 100) if (olym and nat_olym_val) else None
                return row

            # Build all rows
            tbl_rows = []
            for g_idx, grp in enumerate(STATE_TABLE_GROUPS):
                for abbr in grp["states"]:
                    tbl_rows.append(_build_row(abbr, state_yr_vals.get(abbr, {}), "state"))
                if grp["subtotal"]:
                    sub_yr = {}
                    for yr in tbl_years_list:
                        vals = [state_yr_vals.get(a, {}).get(yr) for a in grp["states"]]
                        valid = [v for v in vals if v is not None]
                        sub_yr[yr] = sum(valid) if valid else None
                    tbl_rows.append(_build_row(grp["subtotal"], sub_yr, "subtotal"))
                # spacer between groups (not after the last one)
                if g_idx < len(STATE_TABLE_GROUPS) - 1:
                    tbl_rows.append({"row_type": "spacer"})

            # US Total
            us_yr_map = {yr: nat_yr_vals.get(yr) for yr in tbl_years_list}
            tbl_rows.append(_build_row("US Total", us_yr_map, "us"))

            # ── Render HTML table ─────────────────────────────────────────────
            def _tc(v, metric, pct=False):
                if v is None or (isinstance(v, float) and pd.isna(v)):
                    return "—"
                if pct:
                    return f"{v:.1f}%"
                return _bar_label(v, metric)

            # Header style tokens
            _TH  = (f"padding:7px 9px;text-align:right;background:{TEAL_DIM};color:{WHITE};"
                    f"font-weight:700;font-size:11px;white-space:nowrap;border-bottom:2px solid {TEAL};")
            _TH0 = (f"padding:7px 10px;text-align:left;background:{TEAL_DIM};color:{WHITE};"
                    f"font-weight:700;font-size:11px;border-bottom:2px solid {TEAL};")
            _THS = (f"padding:7px 10px;text-align:right;background:{DARK_ALT};color:{TEAL};"
                    f"font-weight:700;font-size:11px;white-space:nowrap;"
                    f"border-bottom:2px solid {TEAL};border-left:2px solid #4a5568;")
            _THP = (f"padding:7px 10px;text-align:right;background:{DARK_ALT};color:{AMBER};"
                    f"font-weight:700;font-size:11px;white-space:nowrap;"
                    f"border-bottom:2px solid {TEAL};border-left:1px solid #4a5568;")

            yr_hdrs = "".join(f"<th style='{_TH}'>{yr}</th>" for yr in tbl_years_list)
            thead_html = (
                f"<thead><tr>"
                f"<th style='{_TH0}'>State / Region</th>"
                f"{yr_hdrs}"
                f"<th style='{_THS}'>6-Yr Olympic Avg</th>"
                f"<th style='{_THS}'>Min</th>"
                f"<th style='{_THS}'>Max</th>"
                f"<th style='{_THP}'>% of U.S.</th>"
                f"</tr></thead>"
            )

            tbody_html = ""
            row_idx    = 0
            for row in tbl_rows:
                rtype = row.get("row_type")
                if rtype == "spacer":
                    colspan = 1 + len(tbl_years_list) + 4
                    tbody_html += (
                        f"<tr><td colspan='{colspan}' "
                        f"style='height:9px;background:{DARK_BG};'></td></tr>"
                    )
                    continue

                if rtype == "us":
                    bg     = "#1b2e30"
                    c_lbl  = TEAL
                    c_num  = WHITE
                    c_sp   = TEAL
                    c_pct  = AMBER
                    fw_lbl = "700"
                    fs_lbl = "13px"
                    border_top = f"border-top:2px solid {TEAL};"
                elif rtype == "subtotal":
                    bg     = DARK_ALT
                    c_lbl  = TEAL
                    c_num  = TEAL
                    c_sp   = TEAL
                    c_pct  = AMBER
                    fw_lbl = "700"
                    fs_lbl = "12px"
                    border_top = f"border-top:1px solid {TEAL_DIM};"
                else:
                    bg     = DARK_CARD if row_idx % 2 == 0 else "#302e2e"
                    c_lbl  = WHITE
                    c_num  = GRAY
                    c_sp   = WHITE
                    c_pct  = AMBER
                    fw_lbl = "400"
                    fs_lbl = "12px"
                    border_top = ""
                    row_idx += 1

                td_lbl = (f"padding:7px 10px;text-align:left;background:{bg};color:{c_lbl};"
                          f"font-weight:{fw_lbl};font-size:{fs_lbl};{border_top}")
                td_num = (f"padding:6px 9px;text-align:right;background:{bg};color:{c_num};"
                          f"font-size:12px;{border_top}")
                td_sp  = (f"padding:6px 10px;text-align:right;background:{bg};color:{c_sp};"
                          f"font-weight:600;font-size:12px;border-left:2px solid #4a5568;{border_top}")
                td_pct = (f"padding:6px 10px;text-align:right;background:{bg};color:{c_pct};"
                          f"font-weight:700;font-size:12px;border-left:1px solid #4a5568;{border_top}")

                yr_cells = "".join(
                    f"<td style='{td_num}'>{_tc(row.get(yr), map_metric)}</td>"
                    for yr in tbl_years_list
                )
                tbody_html += (
                    f"<tr>"
                    f"<td style='{td_lbl}'>{row['label']}</td>"
                    f"{yr_cells}"
                    f"<td style='{td_sp}'>{_tc(row.get('olym'),    map_metric)}</td>"
                    f"<td style='{td_sp}'>{_tc(row.get('min_val'), map_metric)}</td>"
                    f"<td style='{td_sp}'>{_tc(row.get('max_val'), map_metric)}</td>"
                    f"<td style='{td_pct}'>{_tc(row.get('pct_us'), map_metric, pct=True)}</td>"
                    f"</tr>"
                )

            st.markdown(
                f"<div style='overflow-x:auto;border-radius:8px;border:1px solid #4a5568;"
                f"margin-bottom:20px;'>"
                f"<table style='border-collapse:collapse;width:100%;font-family:Open Sans,sans-serif;'>"
                f"{thead_html}<tbody>{tbody_html}</tbody></table></div>",
                unsafe_allow_html=True,
            )

            # ── State historical section ──────────────────────────────────────
            st.markdown("---")
            if selected_abbr is None:
                st.markdown(
                    f"<div style='background:{DARK_CARD};border-radius:8px;padding:28px;text-align:center;"
                    f"color:{GRAY};font-size:15px;border:1px dashed #4a5568;'>"
                    f"🗺️ &nbsp; Click a state on the map to view its historical trend"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<h3 style='color:{WHITE};margin-bottom:4px'>"
                    f"{selected_name} — Historical {map_metric}</h3>",
                    unsafe_allow_html=True,
                )

                with st.spinner(f"Loading {selected_name} history..."):
                    s_hist = load_state_history(commodity, map_metric, year_range[0], year_range[1])

                s_data = s_hist[s_hist["state_abbr"] == selected_abbr].sort_values("year")
                nat_data = nat_df[nat_df["metric"] == map_metric][["year", "value"]].sort_values("year")

                if s_data.empty:
                    st.warning(f"No historical data found for {selected_name}.")
                else:
                    col_l, col_r = st.columns(2, gap="medium")

                    # State trend
                    fig_st = go.Figure()
                    fig_st.add_trace(go.Scatter(
                        x=s_data["year"], y=s_data["value"],
                        mode="lines+markers",
                        line=dict(color=TEAL, width=2.5),
                        marker=dict(size=5),
                        fill="tozeroy", fillcolor="rgba(91,165,175,0.12)",
                        name=selected_name,
                        hovertemplate=f"<b>%{{x}}</b><br>{map_metric}: %{{y:{_ytick(map_metric)}}}<extra></extra>",
                    ))
                    _base_layout(fig_st, title=f"{selected_name} — {map_metric}", height=380)
                    fig_st.update_yaxes(tickformat=_ytick(map_metric))
                    col_l.plotly_chart(fig_st, use_container_width=True)

                    # State vs US
                    fig_vs = go.Figure()
                    fig_vs.add_trace(go.Scatter(
                        x=nat_data["year"], y=nat_data["value"],
                        mode="lines", name="U.S. Total",
                        line=dict(color=WHITE, width=2, dash="dot"),
                        hovertemplate="<b>U.S.</b><br>%{x}: %{y:" + _ytick(map_metric) + "}<extra></extra>",
                    ))
                    fig_vs.add_trace(go.Scatter(
                        x=s_data["year"], y=s_data["value"],
                        mode="lines+markers", name=selected_name,
                        line=dict(color=TEAL, width=2.5),
                        marker=dict(size=5),
                        hovertemplate=f"<b>{selected_name}</b><br>%{{x}}: %{{y:{_ytick(map_metric)}}}<extra></extra>",
                    ))
                    _base_layout(fig_vs, title=f"{selected_name} vs. U.S. — {map_metric}", height=380)
                    fig_vs.update_yaxes(tickformat=_ytick(map_metric))
                    col_r.plotly_chart(fig_vs, use_container_width=True)
