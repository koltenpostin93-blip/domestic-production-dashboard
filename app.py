import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
from datetime import date
from io import BytesIO

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

# ── Per-commodity state table groups ─────────────────────────────────────────
# Each group renders individual state rows → optional subtotal row → spacer row.
# Keyed by commodity name matching COMMODITIES dict above.
COMMODITY_TABLE_GROUPS: dict = {
    "Corn": [
        {"states": ["IL", "IN", "OH", "MI", "KY"],                                   "subtotal": "Eastern Corn Belt"},
        {"states": ["IA", "NE", "KS", "CO", "MO"],                                   "subtotal": "Central Plains"},
        {"states": ["MN", "SD", "ND"],                                                "subtotal": "BN States"},
        {"states": ["MS", "AR", "LA", "TN"],                                          "subtotal": "Delta"},
        {"states": ["OK", "TX", "NM"],                                                "subtotal": "Southern Plains"},
        {"states": ["AL", "GA", "FL", "SC", "NC", "VA"],                             "subtotal": "SE States"},
        {"states": ["PA", "NY", "MD", "WV", "MA", "VT", "DE", "NJ", "NH", "ME", "CT"], "subtotal": "NE States"},
        {"states": ["WI"],                                                            "subtotal": None},
    ],
    "Soybeans": [
        {"states": ["IL", "IN", "OH", "MI"],        "subtotal": "Eastern Corn Belt"},
        {"states": ["IA", "MN", "MO"],              "subtotal": "Western Corn Belt"},
        {"states": ["ND", "SD", "NE", "KS"],        "subtotal": "Northern Plains"},
        {"states": ["AR", "MS", "TN", "LA"],        "subtotal": "Delta"},
        {"states": ["WI", "KY"],                    "subtotal": None},
    ],
    "Wheat": [
        {"states": ["KS", "OK", "TX"],              "subtotal": "Southern Plains (HRW)"},
        {"states": ["CO", "NE", "SD"],              "subtotal": "Central Plains (HRW)"},
        {"states": ["WA", "OR", "ID"],              "subtotal": "Pacific Northwest"},
        {"states": ["IL", "IN", "OH", "MI"],        "subtotal": "Eastern SRW Belt"},
        {"states": ["MT", "ND"],                    "subtotal": None},
    ],
    "Cotton": [
        {"states": ["TX", "OK", "NM"],              "subtotal": "Southwest"},
        {"states": ["GA", "AL", "SC", "NC"],        "subtotal": "Southeast"},
        {"states": ["MS", "AR", "TN"],              "subtotal": "Delta"},
        {"states": ["CA", "AZ"],                    "subtotal": None},
    ],
    "Sorghum": [
        {"states": ["KS", "TX", "OK"],              "subtotal": "Southern Plains"},
        {"states": ["SD", "NE", "CO"],              "subtotal": "Northern Plains"},
        {"states": ["MO", "AR", "LA"],              "subtotal": None},
    ],
    "Barley": [
        {"states": ["ND", "MT", "ID"],              "subtotal": "Northern Plains"},
        {"states": ["WA", "OR", "WY"],              "subtotal": "Pacific Northwest"},
        {"states": ["CO", "MN"],                    "subtotal": None},
    ],
    "Canola": [
        {"states": ["ND", "MT", "OK"],              "subtotal": None},
    ],
    "Sugarbeets": [
        {"states": ["ND", "MN", "MI"],              "subtotal": "Northern"},
        {"states": ["ID", "WY", "CO"],              "subtotal": "Western"},
        {"states": ["CA", "OR"],                    "subtotal": None},
    ],
    "Peanuts": [
        {"states": ["GA", "AL", "FL"],              "subtotal": "Southeast"},
        {"states": ["TX", "OK", "NM"],              "subtotal": "Southwest"},
        {"states": ["NC", "VA", "SC"],              "subtotal": "Mid-Atlantic"},
        {"states": ["AR", "MS"],                    "subtotal": None},
    ],
    "Hay": [
        {"states": ["TX", "CA", "KS"],              "subtotal": "South / West"},
        {"states": ["SD", "ND", "MT"],              "subtotal": "Northern Plains"},
        {"states": ["WI", "MN", "IA"],              "subtotal": "Midwest"},
        {"states": ["OK", "MO"],                    "subtotal": None},
    ],
    "Sunflower": [
        {"states": ["ND", "SD", "MN"],              "subtotal": "Northern Plains"},
        {"states": ["KS", "CO", "NE"],              "subtotal": "Central Plains"},
        {"states": ["TX"],                          "subtotal": None},
    ],
}

# ── Quarterly Stocks config ───────────────────────────────────────────────────
STOCKS_QUARTERS = ["DEC 1", "MAR 1", "JUN 1", "SEP 1"]
# NASS stores these as "FIRST OF ..." — map display label → API value
STOCKS_QUARTERS_API = {
    "DEC 1": "FIRST OF DEC",
    "MAR 1": "FIRST OF MAR",
    "JUN 1": "FIRST OF JUN",
    "SEP 1": "FIRST OF SEP",
}
# Maps each quarter to (prior_quarter_label, year_delta) for "vs Last Report"
PREV_QUARTER = {
    "DEC 1": ("SEP 1",  0),
    "MAR 1": ("DEC 1", -1),
    "JUN 1": ("MAR 1",  0),
    "SEP 1": ("JUN 1",  0),
}

# Commodities that have quarterly grain stocks in NASS; maps to API params
STOCKS_META = {
    "Corn":     {"commodity_desc": "CORN",     "unit_desc": "BU"},
    "Soybeans": {"commodity_desc": "SOYBEANS", "unit_desc": "BU"},
    "Wheat":    {"commodity_desc": "WHEAT",    "unit_desc": "BU"},
    "Sorghum":  {"commodity_desc": "SORGHUM",  "unit_desc": "BU"},
    "Barley":   {"commodity_desc": "BARLEY",   "unit_desc": "BU"},
}

# ── Revision Tracker config ──────────────────────────────────────────────────
# Ordered NASS reference_period_desc values for each metric category
REVISION_PERIODS_ACRES = [
    "YEAR - JUN ACREAGE",
    "YEAR",
]
REVISION_PERIODS_YLDPROD = [
    "YEAR - MAY FORECAST",
    "YEAR - JUN FORECAST",
    "YEAR - JUL FORECAST",
    "YEAR - AUG FORECAST",
    "YEAR - SEP FORECAST",
    "YEAR - OCT FORECAST",
    "YEAR - NOV FORECAST",
    "YEAR",
]
PERIOD_SHORT = {
    "YEAR - JUN ACREAGE":  "Jun Acreage",
    "YEAR - MAY FORECAST": "May Fcst",
    "YEAR - JUN FORECAST": "Jun Fcst",
    "YEAR - JUL FORECAST": "Jul Fcst",
    "YEAR - AUG FORECAST": "Aug Fcst",
    "YEAR - SEP FORECAST": "Sep Fcst",
    "YEAR - OCT FORECAST": "Oct Fcst",
    "YEAR - NOV FORECAST": "Nov Fcst",
    "YEAR":                "Final",
}
# Curated checkpoints shown in the period-comparison dropdowns.
# The line chart always shows every available period; these are the
# key milestones for the column chart until we confirm more from NASS.
KEY_CMP_ACRES   = ["Jun Acreage", "Final"]
KEY_CMP_YLDPROD = ["Jun Fcst", "Aug Fcst", "Nov Fcst", "Final"]

# 10-step color palette: dark→bright teal, last year = amber
_REV_PALETTE = [
    "#1e4a50","#245860","#2b6870","#347a83","#3d8c95",
    "#479fa8","#51b1bb","#5bbfca","#67d2e0", AMBER,
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
@st.cache_data(ttl=300, show_spinner=False)
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

def _table_to_excel(rows: list, years: list, chg_label: str, title: str,
                    prior_lbl: str | None = None) -> bytes:
    """Convert table row dicts to a formatted Excel workbook and return bytes."""
    records = []
    for row in rows:
        if row.get("row_type") == "spacer":
            continue
        rec = {"State / Region": row.get("label", "")}
        for yr in years:
            rec[str(yr)] = row.get(yr)
        rec[chg_label]          = row.get("chg_vs_ly")
        rec["6-Yr Olympic Avg"] = row.get("olym")
        rec["% of Avg"]         = row.get("pct_of_avg")
        rec["Min"]              = row.get("min_val")
        rec["Max"]              = row.get("max_val")
        rec["% of U.S."]        = row.get("pct_us")
        if prior_lbl:
            rec[prior_lbl]              = row.get("prior_rpt_val")
            rec[f"Chg vs {prior_lbl}"]  = row.get("chg_vs_prior_rpt")
        records.append(rec)
    df = pd.DataFrame(records)
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=title[:31])
        ws = writer.sheets[title[:31]]
        for col in ws.columns:
            max_len = max((len(str(c.value)) if c.value is not None else 0) for c in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 3, 20)
    return buf.getvalue()

def _render_export_buttons(rows: list, years: list, chg_label: str,
                           filename_stem: str, title: str,
                           prior_lbl: str | None = None):
    """Render Excel download + copyable dataframe expander for a table."""
    xlsx_bytes = _table_to_excel(rows, years, chg_label, title, prior_lbl=prior_lbl)
    c1, c2 = st.columns([1, 5])
    c1.download_button(
        "📥 Export to Excel",
        data=xlsx_bytes,
        file_name=f"{filename_stem}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"dl_{filename_stem}",
    )
    with c2.expander("📋 Copy-friendly table (for email / paste)"):
        records = []
        for row in rows:
            if row.get("row_type") == "spacer":
                continue
            rec = {"State / Region": row.get("label", "")}
            for yr in years:
                v = row.get(yr)
                rec[str(yr)] = round(v, 2) if v is not None else None
            rec[chg_label]          = (round(row["chg_vs_ly"], 1)
                                       if row.get("chg_vs_ly") is not None else None)
            rec["6-Yr Olympic Avg"] = (round(row["olym"], 2)
                                       if row.get("olym") is not None else None)
            rec["% of Avg"]         = (round(row["pct_of_avg"], 1)
                                       if row.get("pct_of_avg") is not None else None)
            if prior_lbl:
                pv = row.get("prior_rpt_val")
                cv = row.get("chg_vs_prior_rpt")
                rec[prior_lbl]             = round(pv, 2) if pv is not None else None
                rec[f"Chg vs {prior_lbl}"] = round(cv, 2) if cv is not None else None
            records.append(rec)
        st.dataframe(pd.DataFrame(records), use_container_width=True, hide_index=True)

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
    if "Production" in metric or "Stocks" in metric:
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

def _tbl_num(v, metric) -> str:
    """Table cell: scaled number, no unit suffix.
    Yield and Acres → 1 decimal; Production/Stocks → whole number."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    if "Yield" in metric:
        return f"{v:.1f}"
    if "Acres" in metric:
        return f"{v / 1_000_000:.2f}"
    if "Production" in metric or "Stocks" in metric:
        unit = metric.split("(")[-1].replace(")", "").strip()
        return f"{round(v / 1_000):,}" if "Bales" in unit else f"{round(v / 1_000_000):,}"
    return f"{round(v):,}"

def _nom_chg_str(chg, metric) -> str:
    """Signed nominal change in display units, 1 decimal. e.g. '+50.3M Bu'"""
    if chg is None or (isinstance(chg, float) and pd.isna(chg)):
        return "N/A"
    sign = "+" if chg >= 0 else ""
    if "Yield" in metric:
        unit = metric.split("(")[-1].replace(")", "").strip()
        return f"{sign}{chg:.1f} {unit}"
    if "Acres" in metric:
        return f"{sign}{chg / 1_000_000:.1f}M Ac"
    if "Production" in metric:
        unit = metric.split("(")[-1].replace(")", "").strip()
        if "Bales" in unit:
            return f"{sign}{chg / 1_000:.1f}K Bales"
        if "Bu"  in unit: return f"{sign}{chg / 1_000_000:.1f}M Bu"
        if "Ton" in unit: return f"{sign}{chg / 1_000_000:.1f}M Tons"
        if "Lb"  in unit: return f"{sign}{chg / 1_000_000:.1f}M Lbs"
    return f"{sign}{chg:.1f}"

def _tbl_unit(metric) -> str:
    """Human-readable unit label for table title parenthetical."""
    if "Yield" in metric:
        return metric.split("(")[-1].replace(")", "").strip()
    if "Acres" in metric:
        return "Million Acres"
    if "Production" in metric or "Stocks" in metric:
        unit = metric.split("(")[-1].replace(")", "").strip()
        if "Bales" in unit:   return "Thousand Bales"
        if "Bu"   in unit:   return "Million Bushels"
        if "Ton"  in unit:   return "Million Tons"
        if "Lb"   in unit:   return "Million Lbs"
    return ""

def _olympic6(vals):
    """6-year olympic average: remove highest & lowest, average the rest.
    Accepts up to 6 values (or however many are non-null); needs ≥3 to compute."""
    clean = sorted(v for v in vals if v is not None and not pd.isna(v))
    if len(clean) < 3:
        return None
    return sum(clean[1:-1]) / len(clean[1:-1])

# ── Data loaders ─────────────────────────────────────────────────────────────
def _prefer_all_classes(df: pd.DataFrame) -> pd.DataFrame:
    """When NASS returns multiple class rows per year/state (e.g. Wheat has
    ALL CLASSES / WINTER / SPRING / DURUM), keep only 'ALL CLASSES' rows.
    If the column is absent or no 'ALL CLASSES' row exists, return df unchanged."""
    if "class_desc" not in df.columns:
        return df
    all_cls = df[df["class_desc"].str.upper().str.strip() == "ALL CLASSES"]
    return all_cls if not all_cls.empty else df

@st.cache_data(ttl=300, show_spinner=False)
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
        # Prefer "ALL CLASSES" rows when commodity reports multiple classes
        df = _prefer_all_classes(df)
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
    "YEAR - MAR ACREAGE",   # Prospective Plantings — lowest priority fallback
]

# Ordered (display_label, NASS reference_period_desc) pairs per metric category,
# used by the "vs Prior Report" map view to populate period selectors.
REPORT_PERIODS = {
    "Acres": [
        ("Mar Intentions", "YEAR - MAR ACREAGE"),
        ("Jun Acreage",    "YEAR - JUN ACREAGE"),
        ("Final",          "YEAR"),
    ],
    "Yield": [
        ("May Fcst",  "YEAR - MAY FORECAST"),
        ("Jun Fcst",  "YEAR - JUN FORECAST"),
        ("Jul Fcst",  "YEAR - JUL FORECAST"),
        ("Aug Fcst",  "YEAR - AUG FORECAST"),
        ("Sep Fcst",  "YEAR - SEP FORECAST"),
        ("Oct Fcst",  "YEAR - OCT FORECAST"),
        ("Nov Fcst",  "YEAR - NOV FORECAST"),
        ("Final",     "YEAR"),
    ],
    "Production": [
        ("May Fcst",  "YEAR - MAY FORECAST"),
        ("Jun Fcst",  "YEAR - JUN FORECAST"),
        ("Jul Fcst",  "YEAR - JUL FORECAST"),
        ("Aug Fcst",  "YEAR - AUG FORECAST"),
        ("Sep Fcst",  "YEAR - SEP FORECAST"),
        ("Oct Fcst",  "YEAR - OCT FORECAST"),
        ("Nov Fcst",  "YEAR - NOV FORECAST"),
        ("Final",     "YEAR"),
    ],
}

def _get_report_periods(metric: str):
    if "Acres" in metric:
        return REPORT_PERIODS["Acres"]
    if "Yield" in metric:
        return REPORT_PERIODS["Yield"]
    if "Production" in metric:
        return REPORT_PERIODS["Production"]
    return REPORT_PERIODS["Acres"]

@st.cache_data(ttl=300, show_spinner=False)
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
        # Prefer "ALL CLASSES" rows when commodity reports multiple classes
        df = _prefer_all_classes(df)
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

@st.cache_data(ttl=300, show_spinner=False)
def load_period_snapshot(commodity: str, metric: str, year: int, period: str) -> pd.DataFrame:
    """Fetch state-level values for an explicit NASS reference_period_desc."""
    if commodity not in COMMODITIES or metric not in COMMODITIES[commodity]:
        return pd.DataFrame()
    mp   = COMMODITIES[commodity][metric]
    base = {k: v for k, v in mp.items() if k != "reference_period_desc"}
    df   = _fetch({**base, "agg_level_desc": "STATE", "domain_desc": "TOTAL",
                   "reference_period_desc": period, "year": str(year)})
    if df.empty:
        return pd.DataFrame()
    df = _prefer_all_classes(df)
    df["value"]      = df["Value"].apply(_clean)
    df["state_abbr"] = df["state_name"].str.upper().map(STATE_ABBREV)
    df = df.dropna(subset=["value", "state_abbr"])
    df = df[df["value"] > 0]
    return df[["state_name", "state_abbr", "value"]].copy()

@st.cache_data(ttl=300, show_spinner=False)
def load_national_period_snapshot(commodity: str, metric: str, year: int, period: str) -> float | None:
    """Fetch the US national total for a specific NASS reference_period_desc."""
    if commodity not in COMMODITIES or metric not in COMMODITIES[commodity]:
        return None
    mp   = COMMODITIES[commodity][metric]
    base = {k: v for k, v in mp.items() if k != "reference_period_desc"}
    df   = _fetch({**base, "agg_level_desc": "NATIONAL", "domain_desc": "TOTAL",
                   "reference_period_desc": period, "year": str(year)})
    if df.empty:
        return None
    df = _prefer_all_classes(df)
    df["value"] = df["Value"].apply(_clean)
    df = df.dropna(subset=["value"])
    df = df[df["value"] > 0]
    return float(df["value"].iloc[0]) if not df.empty else None

@st.cache_data(ttl=300, show_spinner=False)
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
    # Prefer "ALL CLASSES" rows when commodity reports multiple classes
    df = _prefer_all_classes(df)
    df["year"]       = df["year"].astype(int)
    df["value"]      = df["Value"].apply(_clean)
    df["state_abbr"] = df["state_name"].str.upper().map(STATE_ABBREV)
    df = df.dropna(subset=["value", "state_abbr"])
    df = df.drop_duplicates(subset=["year", "state_abbr"])
    return df[["year", "value", "state_abbr", "state_name"]].sort_values(["state_abbr", "year"])

# ── Quarterly stocks loaders ─────────────────────────────────────────────────
def _stocks_base(commodity: str, quarter: str) -> dict:
    meta = STOCKS_META[commodity]
    # NASS stores quarterly stocks as "FIRST OF MAR" etc., not "MAR 1".
    api_period = STOCKS_QUARTERS_API.get(quarter, quarter)
    return {**meta, "statisticcat_desc": "STOCKS", "source_desc": "SURVEY",
            "domain_desc": "TOTAL", "reference_period_desc": api_period}

def _filter_storage(df: pd.DataFrame, storage: str) -> pd.DataFrame:
    """Filter a raw NASS stocks DataFrame by storage location via class_desc.
    NASS returns ALL CLASSES + ON FARM + OFF FARM rows for each state; picking
    ALL CLASSES for 'Total' avoids double-counting the sub-categories."""
    if "class_desc" not in df.columns:
        return df
    if storage == "TOTAL":
        # Keep only the aggregate row; fall back to all rows if column is absent
        agg = df[df["class_desc"].str.upper() == "ALL CLASSES"]
        return agg if not agg.empty else df
    return df[df["class_desc"].str.upper() == storage]

@st.cache_data(ttl=300, show_spinner=False)
def load_stocks_snapshot(commodity: str, quarter: str, year: int,
                         storage: str = "TOTAL") -> pd.DataFrame:
    if commodity not in STOCKS_META:
        return pd.DataFrame()
    df = _fetch({**_stocks_base(commodity, quarter),
                 "agg_level_desc": "STATE", "year": str(year)})
    if df.empty:
        return pd.DataFrame()
    df["value"]      = df["Value"].apply(_clean)
    df["state_abbr"] = df["state_name"].str.upper().map(STATE_ABBREV)
    df = df.dropna(subset=["value", "state_abbr"])
    df = df[df["value"] > 0]
    df = _filter_storage(df, storage)
    df = df.groupby(["state_name", "state_abbr"], as_index=False)["value"].sum()
    return df[["state_name", "state_abbr", "value"]].copy()

@st.cache_data(ttl=300, show_spinner=False)
def load_stocks_history(commodity: str, quarter: str, y0: int, y1: int,
                        storage: str = "TOTAL") -> pd.DataFrame:
    if commodity not in STOCKS_META:
        return pd.DataFrame()
    df = _fetch({**_stocks_base(commodity, quarter),
                 "agg_level_desc": "STATE", "year__GE": str(y0), "year__LE": str(y1)})
    if df.empty:
        return pd.DataFrame()
    df["year"]       = df["year"].astype(int)
    df["value"]      = df["Value"].apply(_clean)
    df["state_abbr"] = df["state_name"].str.upper().map(STATE_ABBREV)
    df = df.dropna(subset=["value", "state_abbr"])
    df = _filter_storage(df, storage)
    df = df.groupby(["year", "state_abbr", "state_name"], as_index=False)["value"].sum()
    return df[["year", "value", "state_abbr", "state_name"]].sort_values(["state_abbr", "year"])

@st.cache_data(ttl=300, show_spinner=False)
def load_stocks_national(commodity: str, quarter: str, y0: int, y1: int,
                         storage: str = "TOTAL") -> pd.DataFrame:
    if commodity not in STOCKS_META:
        return pd.DataFrame()
    df = _fetch({**_stocks_base(commodity, quarter),
                 "agg_level_desc": "NATIONAL", "year__GE": str(y0), "year__LE": str(y1)})
    if df.empty:
        return pd.DataFrame()
    df["year"]  = df["year"].astype(int)
    df["value"] = df["Value"].apply(_clean)
    df = df.dropna(subset=["value"])
    df = _filter_storage(df, storage)
    df = df.groupby("year", as_index=False)["value"].sum()
    return df[["year", "value"]].sort_values("year")

# ── Revision-history loader ──────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_revision_data(commodity: str, metric: str, y0: int, y1: int,
                       agg_level: str = "NATIONAL") -> pd.DataFrame:
    """Fetch every reference_period_desc row for a metric across years.
    Returns: year, period, value  [+ state_abbr, state_name for STATE level]."""
    if commodity not in COMMODITIES or metric not in COMMODITIES[commodity]:
        return pd.DataFrame()
    mp   = COMMODITIES[commodity][metric]
    base = {k: v for k, v in mp.items() if k != "reference_period_desc"}
    df   = _fetch({
        **base,
        "agg_level_desc": agg_level,
        "domain_desc":    "TOTAL",
        "year__GE":       str(y0),
        "year__LE":       str(y1),
    })
    if df.empty:
        return pd.DataFrame()
    df["year"]  = df["year"].astype(int)
    df["value"] = df["Value"].apply(_clean)
    df = df.dropna(subset=["value"])
    df = df[df["value"] > 0]
    # Sort by load_desc so keep="last" gives the most-recently published estimate
    if "load_desc" in df.columns:
        df = df.sort_values("load_desc")
    if agg_level == "STATE":
        df["state_abbr"] = df["state_name"].str.upper().map(STATE_ABBREV)
        df = df.dropna(subset=["state_abbr"])
        df = df.drop_duplicates(
            subset=["year", "reference_period_desc", "state_abbr"], keep="last")
        return (df[["year","reference_period_desc","value","state_abbr","state_name"]]
                .rename(columns={"reference_period_desc":"period"})
                .reset_index(drop=True))
    else:
        df = df.drop_duplicates(subset=["year","reference_period_desc"], keep="last")
        return (df[["year","reference_period_desc","value"]]
                .rename(columns={"reference_period_desc":"period"})
                .reset_index(drop=True))

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
    map_year = st.selectbox("Map Year", list(range(THIS_YEAR, 1999, -1)))

    st.markdown("---")
    st.markdown(f"<p style='color:{GRAY};font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.05em'>Quarterly Stocks</p>", unsafe_allow_html=True)
    stocks_year = st.selectbox("Stocks Year", list(range(THIS_YEAR, 1999, -1)))


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
tab_nat, tab_state, tab_stocks, tab_revisions = st.tabs([
    "  📊  National Overview  ",
    "  🗺️  State Level  ",
    "  📦  Quarterly Stocks  ",
    "  🔄  Revision Tracker  ",
])

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
            # ── Map view toggle ───────────────────────────────────────────────
            map_view = st.radio(
                "Map view",
                ["Value", "vs Last Year", "vs Olympic Avg", "vs Year", "vs Prior Report"],
                horizontal=True,
                label_visibility="collapsed",
                key="map_view",
            )
            comp_year = None
            if map_view == "vs Year":
                cv_col, _ = st.columns([2, 8])
                comp_year = cv_col.selectbox(
                    "Compare to",
                    [y for y in range(map_year - 1, 1989, -1)],
                    key="map_comp_year",
                )

            _rp_cur_lbl = _rp_prev_lbl = _rp_cur_nass = _rp_prev_nass = None
            if map_view == "vs Prior Report":
                _rp_opts   = _get_report_periods(map_metric)
                _rp_labels = [p[0] for p in _rp_opts]
                _rp_nass   = dict(_rp_opts)
                _rca, _rcb = st.columns(2)
                _rp_cur_lbl  = _rca.selectbox(
                    "Current Report", _rp_labels,
                    index=min(len(_rp_labels) - 1, 1),
                    key="rp_cur",
                )
                _rp_prev_lbl = _rcb.selectbox(
                    "Prior Report", _rp_labels,
                    index=0,
                    key="rp_prev",
                )
                _rp_cur_nass  = _rp_nass[_rp_cur_lbl]
                _rp_prev_nass = _rp_nass[_rp_prev_lbl]

            # ── Change display toggle (comparison modes only) ──────────────────
            chg_display = "% Change"
            if map_view in ("vs Last Year", "vs Olympic Avg", "vs Year", "vs Prior Report"):
                _cd_col, _ = st.columns([2, 8])
                chg_display = _cd_col.radio(
                    "Show change as",
                    ["% Change", "Nominal"],
                    horizontal=True,
                    label_visibility="collapsed",
                    key="chg_display",
                )
            lbl_display = chg_display
            st.markdown("<div style='margin-bottom:4px'></div>", unsafe_allow_html=True)

            # ── Always load LY for hover ──────────────────────────────────────
            prior_snap = load_state_snapshot(commodity, map_year - 1)
            prior_metric = (
                prior_snap[prior_snap["metric"] == map_metric][["state_abbr", "value"]]
                .rename(columns={"value": "prior_value"})
                if not prior_snap.empty else pd.DataFrame(columns=["state_abbr", "prior_value"])
            )
            metric_snap = metric_snap.merge(prior_metric, on="state_abbr", how="left")
            metric_snap["chg_nom"] = metric_snap["value"] - metric_snap["prior_value"]
            metric_snap["chg_pct"] = metric_snap["chg_nom"] / metric_snap["prior_value"] * 100
            metric_snap["chg_pct_str"] = metric_snap.apply(
                lambda r: "N/A" if pd.isna(r["chg_pct"])
                else f"+{r['chg_pct']:.1f}%" if r["chg_pct"] >= 0
                else f"{r['chg_pct']:.1f}%", axis=1,
            )
            metric_snap["chg_nom_str"] = metric_snap["chg_nom"].apply(
                lambda v: _nom_chg_str(v, map_metric)
            )

            # ── Build color column per view mode ──────────────────────────────
            diverging   = False
            map_cscale  = [[0, "#1a2a2c"], [0.4, "#5ba5af"], [1, "#b8dde2"]]
            color_range = None
            cbar_title  = map_metric

            def _pct_str(v):
                if v is None or (isinstance(v, float) and pd.isna(v)): return "N/A"
                return f"+{v:.1f}%" if v >= 0 else f"{v:.1f}%"

            if map_view == "Value":
                metric_snap["color_val"] = metric_snap["value"]
                metric_snap["lbl_str"]   = metric_snap["value"].apply(
                    lambda v: _bar_label(v, map_metric))
                metric_snap["hover_a"] = metric_snap["chg_pct_str"]
                metric_snap["hover_b"] = metric_snap["chg_nom_str"]
                metric_snap["hover_c"] = ""
                hover_tmpl = (
                    "<b>%{customdata[1]}</b> (%{customdata[0]})<br>"
                    + map_metric + ": %{z:,.1f}<br>"
                    "vs LY: %{customdata[2]}  (%{customdata[3]})"
                    "<extra></extra>"
                )

            elif map_view == "vs Last Year":
                _diff = metric_snap["value"] - metric_snap["prior_value"]
                _pct  = _diff / metric_snap["prior_value"] * 100
                if chg_display == "% Change":
                    metric_snap["color_val"] = _pct
                    cbar_title = "% vs Last Year"
                else:
                    metric_snap["color_val"] = _diff
                    cbar_title = f"Chg vs LY ({_tbl_unit(map_metric)})"
                if lbl_display == "% Change":
                    metric_snap["lbl_str"] = _pct.apply(_pct_str)
                else:
                    metric_snap["lbl_str"] = _diff.apply(lambda v: _nom_chg_str(v, map_metric))
                metric_snap["hover_a"] = metric_snap["value"].apply(lambda v: _bar_label(v, map_metric))
                metric_snap["hover_b"] = metric_snap["prior_value"].apply(
                    lambda v: _bar_label(v, map_metric) if v is not None and not pd.isna(v) else "N/A")
                metric_snap["hover_c"] = _pct.apply(_pct_str) + "  (" + _diff.apply(
                    lambda v: _nom_chg_str(v, map_metric)) + ")"
                hover_tmpl = (
                    "<b>%{customdata[1]}</b> (%{customdata[0]})<br>"
                    f"vs LY: %{{customdata[4]}}<br>"
                    f"{map_year}: %{{customdata[2]}}<br>"
                    f"{map_year - 1}: %{{customdata[3]}}"
                    "<extra></extra>"
                )
                diverging  = True

            elif map_view == "vs Olympic Avg":
                hist_y0 = map_year - 5
                with st.spinner("Loading history for olympic average..."):
                    avg_hist = load_state_history(commodity, map_metric, hist_y0, map_year)
                avg_by_state = {}
                if not avg_hist.empty:
                    for abbr, grp in avg_hist.groupby("state_abbr"):
                        vals = [
                            float(grp.loc[grp["year"] == yr, "value"].iloc[0])
                            if yr in grp["year"].values else None
                            for yr in range(hist_y0, map_year + 1)
                        ]
                        avg_by_state[abbr] = _olympic6(vals)
                metric_snap["state_avg"] = metric_snap["state_abbr"].map(avg_by_state)
                _diff = metric_snap["value"] - metric_snap["state_avg"]
                _pct  = _diff / metric_snap["state_avg"] * 100
                if chg_display == "% Change":
                    metric_snap["color_val"] = _pct
                    cbar_title = "% vs Olympic Avg"
                else:
                    metric_snap["color_val"] = _diff
                    cbar_title = f"Chg vs Olympic Avg ({_tbl_unit(map_metric)})"
                if lbl_display == "% Change":
                    metric_snap["lbl_str"] = _pct.apply(_pct_str)
                else:
                    metric_snap["lbl_str"] = _diff.apply(lambda v: _nom_chg_str(v, map_metric))
                metric_snap["hover_a"] = metric_snap["value"].apply(lambda v: _bar_label(v, map_metric))
                metric_snap["hover_b"] = metric_snap["state_avg"].apply(
                    lambda v: _bar_label(v, map_metric) if v is not None and not pd.isna(v) else "N/A")
                metric_snap["hover_c"] = _pct.apply(_pct_str) + "  (" + _diff.apply(
                    lambda v: _nom_chg_str(v, map_metric)) + ")"
                hover_tmpl = (
                    "<b>%{customdata[1]}</b> (%{customdata[0]})<br>"
                    "vs Olympic Avg: %{customdata[4]}<br>"
                    f"{map_year}: %{{customdata[2]}}<br>"
                    "Olympic Avg: %{customdata[3]}"
                    "<extra></extra>"
                )
                diverging  = True

            elif map_view == "vs Year":
                with st.spinner(f"Loading {comp_year} data..."):
                    comp_snap_raw = load_state_snapshot(commodity, comp_year)
                comp_metric = (
                    comp_snap_raw[comp_snap_raw["metric"] == map_metric][["state_abbr", "value"]]
                    .rename(columns={"value": "comp_value"})
                    if not comp_snap_raw.empty
                    else pd.DataFrame(columns=["state_abbr", "comp_value"])
                )
                metric_snap = metric_snap.merge(comp_metric, on="state_abbr", how="left")
                _diff = metric_snap["value"] - metric_snap["comp_value"]
                _pct  = _diff / metric_snap["comp_value"] * 100
                if chg_display == "% Change":
                    metric_snap["color_val"] = _pct
                    cbar_title = f"% vs {comp_year}"
                else:
                    metric_snap["color_val"] = _diff
                    cbar_title = f"Chg vs {comp_year} ({_tbl_unit(map_metric)})"
                if lbl_display == "% Change":
                    metric_snap["lbl_str"] = _pct.apply(_pct_str)
                else:
                    metric_snap["lbl_str"] = _diff.apply(lambda v: _nom_chg_str(v, map_metric))
                metric_snap["hover_a"] = metric_snap["value"].apply(lambda v: _bar_label(v, map_metric))
                metric_snap["hover_b"] = metric_snap["comp_value"].apply(
                    lambda v: _bar_label(v, map_metric) if v is not None and not pd.isna(v) else "N/A")
                metric_snap["hover_c"] = _pct.apply(_pct_str) + "  (" + _diff.apply(
                    lambda v: _nom_chg_str(v, map_metric)) + ")"
                hover_tmpl = (
                    "<b>%{customdata[1]}</b> (%{customdata[0]})<br>"
                    f"vs {comp_year}: %{{customdata[4]}}<br>"
                    f"{map_year}: %{{customdata[2]}}<br>"
                    f"{comp_year}: %{{customdata[3]}}"
                    "<extra></extra>"
                )
                diverging  = True

            else:   # vs Prior Report
                with st.spinner(f"Loading {_rp_cur_lbl} and {_rp_prev_lbl} data..."):
                    _rp_cur_df  = load_period_snapshot(commodity, map_metric, map_year, _rp_cur_nass)
                    _rp_prev_df = load_period_snapshot(commodity, map_metric, map_year, _rp_prev_nass)
                _rp_cur_vals  = dict(zip(_rp_cur_df["state_abbr"],  _rp_cur_df["value"])) \
                                if not _rp_cur_df.empty else {}
                _rp_prev_vals = dict(zip(_rp_prev_df["state_abbr"], _rp_prev_df["value"])) \
                                if not _rp_prev_df.empty else {}
                metric_snap["value"]      = metric_snap["state_abbr"].map(_rp_cur_vals)
                metric_snap["comp_value"] = metric_snap["state_abbr"].map(_rp_prev_vals)
                metric_snap = metric_snap.dropna(subset=["value", "comp_value"])
                _diff = metric_snap["value"] - metric_snap["comp_value"]
                _pct  = _diff / metric_snap["comp_value"] * 100
                if chg_display == "% Change":
                    metric_snap["color_val"] = _pct
                    cbar_title = f"% vs {_rp_prev_lbl}"
                else:
                    metric_snap["color_val"] = _diff
                    cbar_title = f"Chg vs {_rp_prev_lbl} ({_tbl_unit(map_metric)})"
                if lbl_display == "% Change":
                    metric_snap["lbl_str"] = _pct.apply(_pct_str)
                else:
                    metric_snap["lbl_str"] = _diff.apply(lambda v: _nom_chg_str(v, map_metric))
                metric_snap["hover_a"] = metric_snap["value"].apply(lambda v: _bar_label(v, map_metric))
                metric_snap["hover_b"] = metric_snap["comp_value"].apply(
                    lambda v: _bar_label(v, map_metric) if v is not None and not pd.isna(v) else "N/A")
                metric_snap["hover_c"] = _pct.apply(_pct_str) + "  (" + _diff.apply(
                    lambda v: _nom_chg_str(v, map_metric)) + ")"
                hover_tmpl = (
                    "<b>%{customdata[1]}</b> (%{customdata[0]})<br>"
                    f"vs {_rp_prev_lbl}: %{{customdata[4]}}<br>"
                    f"{_rp_cur_lbl}: %{{customdata[2]}}<br>"
                    f"{_rp_prev_lbl}: %{{customdata[3]}}"
                    "<extra></extra>"
                )
                diverging  = True

            # Diverging scale: red ← 0 → green, symmetric range
            if diverging:
                map_cscale = [[0, "#ef4444"], [0.5, "#e8e8e8"], [1, "#22c55e"]]
                valid_cv   = metric_snap["color_val"].dropna()
                if not valid_cv.empty:
                    max_abs    = max(abs(valid_cv.min()), abs(valid_cv.max())) or 1
                    color_range = [-max_abs, max_abs]

            # ── Choropleth ───────────────────────────────────────────────────
            px_kwargs = dict(
                locations="state_abbr", locationmode="USA-states",
                color="color_val", scope="usa",
                color_continuous_scale=map_cscale,
                hover_name="state_name",
                hover_data={"color_val": False, "state_abbr": False},
                custom_data=["state_abbr", "state_name", "hover_a", "hover_b", "hover_c"],
                labels={"color_val": cbar_title},
                title=f"{commodity} — {map_metric} by State ({map_year})  [{cbar_title}]",
            )
            if color_range:
                px_kwargs["range_color"] = color_range

            fig_map = px.choropleth(metric_snap, **px_kwargs)

            tick_fmt = "+.1f" if (diverging and chg_display == "% Change") else ",.0f"
            fig_map.update_layout(
                geo=dict(bgcolor=DARK_BG, lakecolor=DARK_BG, landcolor=DARK_CARD,
                         showlakes=True, showcoastlines=False),
                plot_bgcolor=DARK_BG, paper_bgcolor=DARK_BG,
                font=dict(color=WHITE),
                title_font=dict(size=14, color=WHITE),
                coloraxis_colorbar=dict(
                    title=dict(text=cbar_title, font=dict(color=GRAY, size=11)),
                    tickfont=dict(color=WHITE), bgcolor=DARK_CARD, bordercolor=DARK_ALT,
                    tickformat=tick_fmt,
                    ticksuffix="%" if (diverging and chg_display == "% Change") else "",
                ),
                height=480,
                margin=dict(l=0, r=0, t=50, b=0),
                dragmode=False,
            )
            fig_map.update_traces(
                selector=dict(type="choropleth"),
                marker_line_color="white",
                marker_line_width=0.6,
                hovertemplate=hover_tmpl,
            )

            # All-50-states white border overlay
            all_state_abbrs = list(STATE_ABBREV.values())
            fig_map.add_trace(go.Choropleth(
                locations=all_state_abbrs, locationmode="USA-states",
                z=[0] * len(all_state_abbrs),
                colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]],
                showscale=False,
                marker_line_color="white", marker_line_width=0.6,
                hoverinfo="skip",
            ))

            # State labels (absolute value or % change depending on mode)
            lbl_lats, lbl_lons, lbl_texts = [], [], []
            for _, row in metric_snap.iterrows():
                abbr = row["state_abbr"]
                if abbr in STATE_CENTERS:
                    lbl_lats.append(STATE_CENTERS[abbr][0])
                    lbl_lons.append(STATE_CENTERS[abbr][1])
                    lbl_texts.append(row["lbl_str"] if row["lbl_str"] not in ("N/A", "") else "")
            fig_map.add_trace(go.Scattergeo(
                lat=lbl_lats, lon=lbl_lons, text=lbl_texts,
                mode="text",
                textfont=dict(color="black", size=8, family="Open Sans", weight="bold"),
                showlegend=False, hoverinfo="skip",
            ))

            # Map is the filter — click a state to select it
            map_event = st.plotly_chart(
                fig_map,
                use_container_width=True,
                on_select="rerun",
                key=f"map_{commodity}_{map_year}_{map_metric}_{map_view}_{comp_year}_{_rp_cur_lbl}_{_rp_prev_lbl}",
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
            tbl_unit_lbl = _tbl_unit(map_metric)
            tbl_unit_sfx = f" <span style='color:{TEAL};font-weight:400;text-transform:none;letter-spacing:0'>({tbl_unit_lbl})</span>" if tbl_unit_lbl else ""
            st.markdown(
                f"<p style='color:{GRAY};font-size:12px;font-weight:700;text-transform:uppercase;"
                f"letter-spacing:.06em;margin:20px 0 6px'>"
                f"10-Year State Comparison — {map_metric}{tbl_unit_sfx}</p>",
                unsafe_allow_html=True,
            )

            tbl_y0         = map_year - 9
            tbl_years_list = list(range(tbl_y0, map_year + 1))

            with st.spinner("Loading comparison table..."):
                tbl_shist = load_state_history(commodity, map_metric, tbl_y0, map_year)

            if tbl_shist.empty or "state_abbr" not in tbl_shist.columns:
                c_msg, c_btn = st.columns([5, 1])
                c_msg.warning(
                    "⏱ State comparison data unavailable — NASS API timed out."
                )
                if c_btn.button("🔄 Retry", key="retry_tbl"):
                    st.cache_data.clear()
                    st.rerun()
            else:
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

                # ── Interactive state filter ─────────────────────────────────
                # Default groups are commodity-specific; user can add/remove states.
                _default_groups = COMMODITY_TABLE_GROUPS.get(commodity, [])
                _default_abbrs  = [a for grp in _default_groups for a in grp["states"]]

                # All states available in NASS data for this commodity/year window
                _available_states = sorted(tbl_shist["state_abbr"].dropna().unique().tolist())

                with st.expander("📋 Customize Table States", expanded=False):
                    _sel_states = st.multiselect(
                        "States to include in table",
                        options=_available_states,
                        default=[s for s in _default_abbrs if s in _available_states],
                        key=f"tbl_states_{commodity}_{map_metric}",
                        help="Defaults to the key producing states for the selected commodity. "
                             "Add or remove states as needed.",
                    )

                # If user has customized away from default, flatten into one group
                # (regional subtotals only apply to the commodity-specific groupings)
                if set(_sel_states) == set(s for s in _default_abbrs if s in _available_states):
                    # Using default groups — preserve regional subtotals
                    _active_groups = [
                        {"states": [s for s in grp["states"] if s in _sel_states],
                         "subtotal": grp["subtotal"]}
                        for grp in _default_groups
                        if any(s in _sel_states for s in grp["states"])
                    ]
                else:
                    # Custom selection — flat list, no subtotals
                    _active_groups = [{"states": _sel_states, "subtotal": None}]

                all_abbrs = [a for grp in _active_groups for a in grp["states"]]

                # Per-state year→value lookups
                state_yr_vals = {}
                for abbr in all_abbrs:
                    sdf = tbl_shist[tbl_shist["state_abbr"] == abbr]
                    state_yr_vals[abbr] = {int(r["year"]): r["value"] for _, r in sdf.iterrows()}

                cur_yr  = tbl_years_list[-1]   # most recent year in window
                prev_yr = tbl_years_list[-2]   # prior year

                def _build_row(label, yr_map, row_type="state", prior_rpt_val=None):
                    row = {"label": label, "row_type": row_type}
                    all_vals = []
                    for yr in tbl_years_list:
                        v = yr_map.get(yr)
                        row[yr] = v
                        if v is not None:
                            all_vals.append(v)
                    recent6  = [yr_map.get(yr) for yr in tbl_years_list[-6:]]
                    olym     = _olympic6(recent6)
                    cur_v    = yr_map.get(cur_yr)
                    prev_v   = yr_map.get(prev_yr)
                    row["olym"]             = olym
                    row["min_val"]          = min(all_vals) if all_vals else None
                    row["max_val"]          = max(all_vals) if all_vals else None
                    row["pct_us"]           = (olym / nat_olym_val * 100) if (olym and nat_olym_val) else None
                    row["chg_vs_ly"]        = ((cur_v - prev_v) / prev_v * 100) if (cur_v and prev_v) else None
                    row["pct_of_avg"]       = (cur_v / olym * 100) if (cur_v and olym) else None
                    row["prior_rpt_val"]    = prior_rpt_val
                    row["chg_vs_prior_rpt"] = (cur_v - prior_rpt_val) if (cur_v is not None and prior_rpt_val is not None) else None
                    return row

                # For yield metrics load harvested acres so subtotals can be
                # weighted averages (Σ yield×acres / Σ acres) instead of sums
                is_yield = "Yield" in map_metric
                harv_yr_vals: dict = {}
                if is_yield:
                    harv_metric = next(
                        (m for m in COMMODITIES[commodity] if "Harvested" in m), None
                    )
                    if harv_metric:
                        with st.spinner("Loading harvested acres for yield weighting..."):
                            tbl_harv = load_state_history(commodity, harv_metric, tbl_y0, map_year)
                        if not tbl_harv.empty and "state_abbr" in tbl_harv.columns:
                            for abbr in all_abbrs:
                                hdf = tbl_harv[tbl_harv["state_abbr"] == abbr]
                                harv_yr_vals[abbr] = {
                                    int(r["year"]): r["value"] for _, r in hdf.iterrows()
                                }

                # ── Prior Report Comparison for table ────────────────────────
                _rp_tbl_opts  = [(l, p) for l, p in _get_report_periods(map_metric)
                                 if p != "YEAR"]
                _pr_tbl_lbl   = None
                _pr_state_vals: dict = {}
                _pr_us_val    = None

                if _rp_tbl_opts:
                    _pr_col, _ = st.columns([3, 7])
                    _pr_tbl_lbl = _pr_col.selectbox(
                        "Prior report to compare:",
                        [l for l, _ in _rp_tbl_opts],
                        index=0,
                        key=f"tbl_prior_{commodity}_{map_metric}",
                    )
                    _pr_tbl_nass = dict(_rp_tbl_opts)[_pr_tbl_lbl]
                    with st.spinner(f"Loading {_pr_tbl_lbl} data..."):
                        _pr_snap = load_period_snapshot(commodity, map_metric, map_year, _pr_tbl_nass)
                        _pr_us_val = load_national_period_snapshot(commodity, map_metric, map_year, _pr_tbl_nass)
                    if not _pr_snap.empty:
                        _pr_state_vals = dict(zip(_pr_snap["state_abbr"], _pr_snap["value"]))

                # Build all rows
                tbl_rows = []
                for g_idx, grp in enumerate(_active_groups):
                    grp_states = grp["states"]
                    for abbr in grp_states:
                        tbl_rows.append(_build_row(
                            abbr, state_yr_vals.get(abbr, {}), "state",
                            prior_rpt_val=_pr_state_vals.get(abbr),
                        ))
                    if grp["subtotal"] and len(grp_states) > 1:
                        sub_yr = {}
                        for yr in tbl_years_list:
                            if is_yield and harv_yr_vals:
                                # Weighted average: Σ(yield_i × harv_acres_i) / Σ harv_acres_i
                                numer = denom = 0.0
                                for a in grp_states:
                                    y = state_yr_vals.get(a, {}).get(yr)
                                    h = harv_yr_vals.get(a, {}).get(yr)
                                    if y is not None and h is not None and h > 0:
                                        numer += y * h
                                        denom += h
                                sub_yr[yr] = (numer / denom) if denom > 0 else None
                            else:
                                vals  = [state_yr_vals.get(a, {}).get(yr) for a in grp_states]
                                valid = [v for v in vals if v is not None]
                                sub_yr[yr] = sum(valid) if valid else None
                        # Subtotal prior = sum of states in group
                        sub_pr_vals = [_pr_state_vals.get(a) for a in grp_states
                                       if _pr_state_vals.get(a) is not None]
                        sub_pr_val  = sum(sub_pr_vals) if sub_pr_vals else None
                        tbl_rows.append(_build_row(grp["subtotal"], sub_yr, "subtotal",
                                                   prior_rpt_val=sub_pr_val))
                    if g_idx < len(_active_groups) - 1:
                        tbl_rows.append({"row_type": "spacer"})

                # US Total row (national data)
                us_yr_map = {yr: nat_yr_vals.get(yr) for yr in tbl_years_list}
                tbl_rows.append(_build_row("US Total", us_yr_map, "us",
                                           prior_rpt_val=_pr_us_val))

                # ── Render HTML table ─────────────────────────────────────────
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

                # Separate header style for % vs LY (green/red delta column)
                _THD = (f"padding:7px 9px;text-align:right;background:{DARK_ALT};color:{WHITE};"
                        f"font-weight:700;font-size:11px;white-space:nowrap;"
                        f"border-bottom:2px solid {TEAL};border-left:2px solid #4a5568;")

                chg_hdr_lbl = "% vs LY"
                yr_hdrs    = "".join(f"<th style='{_TH}'>{yr}</th>" for yr in tbl_years_list)
                # Optional prior report columns
                _pr_col_count = 2 if _pr_tbl_lbl else 0
                _pr_hdr_html  = ""
                if _pr_tbl_lbl:
                    _THR = (f"padding:7px 9px;text-align:right;background:#1c2b35;color:#93c5fd;"
                            f"font-weight:700;font-size:11px;white-space:nowrap;"
                            f"border-bottom:2px solid {TEAL};border-left:2px solid #4a5568;")
                    _pr_hdr_html = (
                        f"<th style='{_THR}'>{_pr_tbl_lbl} ({map_year})</th>"
                        f"<th style='{_THR}'>Chg vs {_pr_tbl_lbl}</th>"
                    )
                thead_html = (
                    f"<thead><tr>"
                    f"<th style='{_TH0}'>State / Region</th>"
                    f"{yr_hdrs}"
                    f"<th style='{_THD}'>{chg_hdr_lbl}</th>"
                    f"<th style='{_THS}'>6-Yr Olympic Avg</th>"
                    f"<th style='{_THP}'>% of Avg</th>"
                    f"<th style='{_THS}'>Min</th>"
                    f"<th style='{_THS}'>Max</th>"
                    f"<th style='{_THP}'>% of U.S.</th>"
                    f"{_pr_hdr_html}"
                    f"</tr></thead>"
                )

                tbody_html = ""
                row_idx    = 0
                for row in tbl_rows:
                    rtype = row.get("row_type")
                    if rtype == "spacer":
                        colspan = 1 + len(tbl_years_list) + 6 + _pr_col_count
                        tbody_html += (
                            f"<tr><td colspan='{colspan}' "
                            f"style='height:9px;background:{DARK_BG};'></td></tr>"
                        )
                        continue

                    # Row base styles
                    if rtype == "us":
                        bg = "#1b2e30"; c_lbl = TEAL; c_num = WHITE; c_sp = TEAL
                        c_pct = AMBER; fw_lbl = "700"; fs_lbl = "13px"
                        border_top = f"border-top:2px solid {TEAL};"
                    elif rtype == "subtotal":
                        bg = DARK_ALT; c_lbl = TEAL; c_num = TEAL; c_sp = TEAL
                        c_pct = AMBER; fw_lbl = "700"; fs_lbl = "12px"
                        border_top = f"border-top:1px solid {TEAL_DIM};"
                    else:
                        bg = DARK_CARD if row_idx % 2 == 0 else "#302e2e"
                        c_lbl = WHITE; c_num = GRAY; c_sp = WHITE; c_pct = AMBER
                        fw_lbl = "400"; fs_lbl = "12px"; border_top = ""
                        row_idx += 1

                    # Per-row top2 / bottom2 for conditional formatting
                    yr_pairs = [(yr, row[yr]) for yr in tbl_years_list
                                if row.get(yr) is not None]
                    sorted_vals = sorted(yr_pairs, key=lambda x: x[1])
                    bottom2_yrs = {yr for yr, _ in sorted_vals[:2]}  if len(sorted_vals) >= 2 else set()
                    top2_yrs    = {yr for yr, _ in sorted_vals[-2:]} if len(sorted_vals) >= 2 else set()

                    td_lbl = (f"padding:7px 10px;text-align:left;background:{bg};color:{c_lbl};"
                              f"font-weight:{fw_lbl};font-size:{fs_lbl};{border_top}")
                    td_sp  = (f"padding:6px 10px;text-align:right;background:{bg};color:{c_sp};"
                              f"font-weight:600;font-size:12px;border-left:2px solid #4a5568;{border_top}")
                    td_pct = (f"padding:6px 10px;text-align:right;background:{bg};color:{c_pct};"
                              f"font-weight:700;font-size:12px;border-left:1px solid #4a5568;{border_top}")

                    # Year cells with conditional highlighting
                    yr_cells = ""
                    for yr in tbl_years_list:
                        v = row.get(yr)
                        if yr in top2_yrs and v is not None:
                            cell_bg  = "rgba(34,197,94,0.18)"
                            cell_clr = "#4ade80"
                            cell_fw  = "700"
                        elif yr in bottom2_yrs and v is not None:
                            cell_bg  = "rgba(239,68,68,0.18)"
                            cell_clr = "#f87171"
                            cell_fw  = "700"
                        else:
                            cell_bg  = bg
                            cell_clr = c_num
                            cell_fw  = "400"
                        yr_cells += (
                            f"<td style='padding:6px 9px;text-align:right;"
                            f"background:{cell_bg};color:{cell_clr};"
                            f"font-weight:{cell_fw};font-size:12px;{border_top}'>"
                            f"{_tbl_num(v, map_metric)}</td>"
                        )

                    # % vs LY — green if up, red if down
                    chg       = row.get("chg_vs_ly")
                    if chg is None:
                        chg_str  = "—"
                        chg_clr  = GRAY
                        chg_bg   = bg
                    elif chg >= 0:
                        chg_str  = f"▲ {chg:.1f}%"
                        chg_clr  = "#4ade80"
                        chg_bg   = "rgba(34,197,94,0.12)"
                    else:
                        chg_str  = f"▼ {abs(chg):.1f}%"
                        chg_clr  = "#f87171"
                        chg_bg   = "rgba(239,68,68,0.12)"
                    td_chg = (f"padding:6px 9px;text-align:right;background:{chg_bg};"
                              f"color:{chg_clr};font-weight:700;font-size:12px;"
                              f"border-left:2px solid #4a5568;{border_top}")

                    # % of Avg — ▲/▼ showing deviation from 100% (same style as % vs LY)
                    poa_val = row.get("pct_of_avg")
                    if poa_val is None:
                        poa_str = "—"; poa_clr = GRAY; poa_bg = bg
                    elif poa_val >= 100:
                        poa_str = f"▲ {poa_val - 100:.1f}%"; poa_clr = "#4ade80"; poa_bg = "rgba(34,197,94,0.12)"
                    else:
                        poa_str = f"▼ {100 - poa_val:.1f}%"; poa_clr = "#f87171"; poa_bg = "rgba(239,68,68,0.12)"
                    td_poa = (f"padding:6px 9px;text-align:right;background:{poa_bg};"
                              f"color:{poa_clr};font-weight:700;font-size:12px;"
                              f"border-left:1px solid #4a5568;{border_top}")

                    pct_val = row.get("pct_us")
                    pct_str = "—" if pct_val is None else f"{pct_val:.1f}%"

                    # Prior report columns
                    _pr_cells_html = ""
                    if _pr_tbl_lbl:
                        _pr_v   = row.get("prior_rpt_val")
                        _pr_chg = row.get("chg_vs_prior_rpt")
                        _pr_val_str = _tbl_num(_pr_v, map_metric) if _pr_v is not None else "—"
                        if _pr_chg is None:
                            _pr_chg_str = "—"; _pr_chg_clr = GRAY; _pr_chg_bg = bg
                        elif _pr_chg >= 0:
                            _pr_chg_str = f"▲ {_nom_chg_str(_pr_chg, map_metric)}"
                            _pr_chg_clr = "#4ade80"; _pr_chg_bg = "rgba(34,197,94,0.12)"
                        else:
                            _pr_chg_str = f"▼ {_nom_chg_str(abs(_pr_chg), map_metric)}"
                            _pr_chg_clr = "#f87171"; _pr_chg_bg = "rgba(239,68,68,0.12)"
                        _td_pr = (f"padding:6px 9px;text-align:right;background:#1c2b35;"
                                  f"color:#93c5fd;font-weight:600;font-size:12px;"
                                  f"border-left:2px solid #4a5568;{border_top}")
                        _td_pr_chg = (f"padding:6px 9px;text-align:right;background:{_pr_chg_bg};"
                                      f"color:{_pr_chg_clr};font-weight:700;font-size:12px;"
                                      f"border-left:1px solid #4a5568;{border_top}")
                        _pr_cells_html = (
                            f"<td style='{_td_pr}'>{_pr_val_str}</td>"
                            f"<td style='{_td_pr_chg}'>{_pr_chg_str}</td>"
                        )

                    tbody_html += (
                        f"<tr>"
                        f"<td style='{td_lbl}'>{row['label']}</td>"
                        f"{yr_cells}"
                        f"<td style='{td_chg}'>{chg_str}</td>"
                        f"<td style='{td_sp}'>{_tbl_num(row.get('olym'),    map_metric)}</td>"
                        f"<td style='{td_poa}'>{poa_str}</td>"
                        f"<td style='{td_sp}'>{_tbl_num(row.get('min_val'), map_metric)}</td>"
                        f"<td style='{td_sp}'>{_tbl_num(row.get('max_val'), map_metric)}</td>"
                        f"<td style='{td_pct}'>{pct_str}</td>"
                        f"{_pr_cells_html}"
                        f"</tr>"
                    )

                st.markdown(
                    f"<div style='overflow-x:auto;border-radius:8px;border:1px solid #4a5568;"
                    f"margin-bottom:12px;'>"
                    f"<table style='border-collapse:collapse;width:100%;font-family:Open Sans,sans-serif;'>"
                    f"{thead_html}<tbody>{tbody_html}</tbody></table></div>",
                    unsafe_allow_html=True,
                )
                _render_export_buttons(
                    tbl_rows, tbl_years_list,
                    chg_hdr_lbl,
                    f"{commodity}_{map_metric}_{map_year}".replace(" ", "_").replace("/", ""),
                    f"{commodity} {map_metric} {map_year}",
                    prior_lbl=_pr_tbl_lbl,
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

# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — QUARTERLY STOCKS
# ═════════════════════════════════════════════════════════════════════════════
with tab_stocks:
    if commodity not in STOCKS_META:
        st.info(
            f"Quarterly grain stocks data is not available for **{commodity}** in USDA NASS. "
            f"Available commodities: {', '.join(STOCKS_META.keys())}."
        )
    else:
        unit_key  = STOCKS_META[commodity]["unit_desc"]
        unit_disp = {"BU": "Bu", "TONS": "Tons"}.get(unit_key, unit_key)
        sk_metric = f"Stocks ({unit_disp})"

        # ── Default quarter: Jan–Mar→DEC 1, Apr–Jun→MAR 1, Jul–Sep→JUN 1, Oct–Dec→SEP 1
        _month = date.today().month
        _def_q = 0 if _month <= 3 else 1 if _month <= 6 else 2 if _month <= 9 else 3

        # ── Quarter pill filter ───────────────────────────────────────────────
        sk_quarter = st.radio(
            "Quarter",
            STOCKS_QUARTERS,
            index=_def_q,
            horizontal=True,
            label_visibility="collapsed",
            key="sk_quarter",
        )
        st.markdown("<div style='margin-bottom:6px'></div>", unsafe_allow_html=True)

        # ── Storage filter pills ──────────────────────────────────────────────
        sk_storage = st.radio(
            "Storage",
            ["Total", "On Farm", "Off Farm"],
            horizontal=True,
            label_visibility="collapsed",
            key="sk_storage",
        )
        storage_param = {"Total": "TOTAL", "On Farm": "ON FARM", "Off Farm": "OFF FARM"}[sk_storage]
        storage_lbl   = sk_storage
        st.markdown("<div style='margin-bottom:4px'></div>", unsafe_allow_html=True)

        # ── View toggle (only when On Farm / Off Farm selected) ───────────────
        pct_mode = False
        if sk_storage != "Total":
            sk_view  = st.radio(
                "View",
                ["Numerical", "% of Total"],
                horizontal=True,
                label_visibility="collapsed",
                key="sk_view",
            )
            pct_mode = (sk_view == "% of Total")

        sk_cmp = st.radio(
            "Compare to",
            ["vs Last Year", "vs Last Report"],
            horizontal=True,
            label_visibility="collapsed",
            key="sk_cmp",
        )
        st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)

        # ── Display-value helpers ─────────────────────────────────────────────
        def _sk_fmt_cell(v):
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return "—"
            return f"{v:.1f}%" if pct_mode else _tbl_num(v, sk_metric)

        def _sk_bar_lbl(v):
            return f"{v:.1f}%" if pct_mode else _bar_label(v, sk_metric)

        # ── Resolve comparison period ─────────────────────────────────────────
        if sk_cmp == "vs Last Report":
            _prev_q, _prev_yr_delta = PREV_QUARTER[sk_quarter]
            _prev_yr  = stocks_year + _prev_yr_delta
            _cmp_label = f"{_prev_q} {_prev_yr}"
        else:
            _prev_q, _prev_yr = sk_quarter, stocks_year - 1
            _cmp_label = str(stocks_year - 1)

        # ── Load snapshot + comparison period ────────────────────────────────
        with st.spinner("Fetching USDA NASS stocks data..."):
            sk_snap       = load_stocks_snapshot(commodity, sk_quarter, stocks_year, storage_param)
            sk_snap_prior = load_stocks_snapshot(commodity, _prev_q, _prev_yr, storage_param)
            if pct_mode:
                sk_tot_snap       = load_stocks_snapshot(commodity, sk_quarter, stocks_year, "TOTAL")
                sk_tot_snap_prior = load_stocks_snapshot(commodity, _prev_q, _prev_yr, "TOTAL")
            else:
                sk_tot_snap = sk_tot_snap_prior = pd.DataFrame()

        if sk_snap.empty:
            c_msg, c_btn = st.columns([5, 1])
            c_msg.warning(f"No stocks data for {commodity} {sk_quarter} {stocks_year}.")
            if c_btn.button("🔄 Retry", key="retry_stocks"):
                st.cache_data.clear(); st.rerun()
        else:
            # ── Compute display values (Bu or % of total) ─────────────────────
            if pct_mode and not sk_tot_snap.empty:
                sk_snap = sk_snap.merge(
                    sk_tot_snap[["state_abbr", "value"]].rename(columns={"value": "tot_val"}),
                    on="state_abbr", how="left",
                )
                sk_snap["disp_val"] = sk_snap["value"] / sk_snap["tot_val"] * 100
            else:
                sk_snap["disp_val"] = sk_snap["value"]
                pct_mode = False   # fallback if total snap is empty

            # Prior-year display values
            if not sk_snap_prior.empty:
                if pct_mode and not sk_tot_snap_prior.empty:
                    sk_snap_prior = sk_snap_prior.merge(
                        sk_tot_snap_prior[["state_abbr", "value"]].rename(columns={"value": "tot_val"}),
                        on="state_abbr", how="left",
                    )
                    sk_snap_prior["prior_disp"] = sk_snap_prior["value"] / sk_snap_prior["tot_val"] * 100
                else:
                    sk_snap_prior["prior_disp"] = sk_snap_prior["value"]
                sk_snap = sk_snap.merge(
                    sk_snap_prior[["state_abbr", "prior_disp"]].rename(columns={"prior_disp": "prior_value"}),
                    on="state_abbr", how="left",
                )
            else:
                sk_snap["prior_value"] = None

            sk_snap["chg_nom"] = sk_snap["disp_val"] - sk_snap["prior_value"]
            sk_snap["chg_pct"] = sk_snap["chg_nom"] / sk_snap["prior_value"] * 100
            sk_snap["chg_pct_str"] = sk_snap.apply(
                lambda r: "N/A" if pd.isna(r["chg_pct"])
                else f"+{r['chg_pct']:.1f}%" if r["chg_pct"] >= 0 else f"{r['chg_pct']:.1f}%", axis=1)
            if pct_mode:
                sk_snap["chg_nom_str"] = sk_snap["chg_nom"].apply(
                    lambda v: "N/A" if (v is None or (isinstance(v, float) and pd.isna(v)))
                    else f"+{v:.1f} ppt" if v >= 0 else f"{v:.1f} ppt"
                )
            else:
                sk_snap["chg_nom_str"] = sk_snap["chg_nom"].apply(
                    lambda v: _nom_chg_str(v, sk_metric))

            # ── Choropleth map ────────────────────────────────────────────────
            if pct_mode:
                map_title  = f"{commodity} Stocks ({storage_lbl}) — {sk_quarter} {stocks_year} (% of Total)"
                cbar_title = "% of Total"
                hover_val_fmt = ".1f"
                hover_val_sfx = "%"
            else:
                map_title  = f"{commodity} Stocks ({storage_lbl}) — {sk_quarter} {stocks_year} (Million Bu)"
                cbar_title = sk_metric
                hover_val_fmt = ",.1f"
                hover_val_sfx = ""

            fig_sk = px.choropleth(
                sk_snap, locations="state_abbr", locationmode="USA-states",
                color="disp_val", scope="usa",
                color_continuous_scale=[[0, "#1a2a2c"], [0.4, "#5ba5af"], [1, "#b8dde2"]],
                hover_name="state_name",
                hover_data={"disp_val": ":.1f", "state_abbr": False},
                custom_data=["state_abbr", "state_name", "chg_pct_str", "chg_nom_str"],
                labels={"disp_val": cbar_title},
                title=map_title,
            )
            fig_sk.update_layout(
                geo=dict(bgcolor=DARK_BG, lakecolor=DARK_BG, landcolor=DARK_CARD,
                         showlakes=True, showcoastlines=False),
                plot_bgcolor=DARK_BG, paper_bgcolor=DARK_BG,
                font=dict(color=WHITE), title_font=dict(size=15, color=WHITE),
                coloraxis_colorbar=dict(
                    title=dict(text=cbar_title, font=dict(color=GRAY, size=11)),
                    tickfont=dict(color=WHITE), bgcolor=DARK_CARD, bordercolor=DARK_ALT,
                ),
                height=480, margin=dict(l=0, r=0, t=50, b=0), dragmode=False,
            )
            fig_sk.update_traces(
                selector=dict(type="choropleth"),
                marker_line_color="white", marker_line_width=0.6,
                hovertemplate=(
                    "<b>%{customdata[1]}</b> (%{customdata[0]})<br>"
                    + cbar_title + f": %{{z:{hover_val_fmt}}}{hover_val_sfx}<br>"
                    f"vs {_cmp_label}: " + "%{customdata[2]}  (%{customdata[3]})<extra></extra>"
                ),
            )
            # All-states outline
            all_abbrs_list = list(STATE_ABBREV.values())
            fig_sk.add_trace(go.Choropleth(
                locations=all_abbrs_list, locationmode="USA-states",
                z=[0] * len(all_abbrs_list),
                colorscale=[[0,"rgba(0,0,0,0)"],[1,"rgba(0,0,0,0)"]],
                showscale=False, marker_line_color="white",
                marker_line_width=0.6, hoverinfo="skip",
            ))
            # Value labels on map
            lbl_lats, lbl_lons, lbl_texts = [], [], []
            for _, row in sk_snap.iterrows():
                ab = row["state_abbr"]
                if ab in STATE_CENTERS:
                    lbl_lats.append(STATE_CENTERS[ab][0])
                    lbl_lons.append(STATE_CENTERS[ab][1])
                    lbl_texts.append(_sk_bar_lbl(row["disp_val"]))
            fig_sk.add_trace(go.Scattergeo(
                lat=lbl_lats, lon=lbl_lons, text=lbl_texts, mode="text",
                textfont=dict(color="black", size=8, family="Open Sans", weight="bold"),
                showlegend=False, hoverinfo="skip",
            ))

            # Click-to-select state
            sk_event = st.plotly_chart(
                fig_sk, use_container_width=True, on_select="rerun",
                key=f"sk_map_{commodity}_{sk_quarter}_{stocks_year}_{sk_storage}",
                config={"scrollZoom": False, "displayModeBar": False},
            )
            valid_sk_abbrs = set(sk_snap["state_abbr"].tolist())
            if sk_event and sk_event.selection and sk_event.selection.points:
                pt  = sk_event.selection.points[0]
                cd  = pt.get("customdata") or []
                ab  = cd[0] if len(cd) >= 1 else pt.get("location")
                if ab in valid_sk_abbrs:
                    st.session_state["sel_state_stocks"] = ab
            sk_persisted = st.session_state.get("sel_state_stocks")
            if sk_persisted not in valid_sk_abbrs:
                sk_persisted = None
                st.session_state["sel_state_stocks"] = None
            sk_selected_abbr = sk_persisted
            sk_selected_name = ABBREV_STATE.get(sk_selected_abbr, "").title() if sk_selected_abbr else None

            # Clear button
            c1, c2 = st.columns([1, 5])
            if sk_selected_abbr:
                c1.caption(f"Selected: **{sk_selected_abbr}**")
                if c2.button("✕ Clear", key="clear_state_stocks"):
                    st.session_state["sel_state_stocks"] = None; st.rerun()
            else:
                c1.caption("Click a state on the map")

            # ── Top-15 bar ────────────────────────────────────────────────────
            top15_sk = sk_snap.sort_values("disp_val", ascending=False).head(15)
            bar_clrs = [TEAL if r["state_abbr"] == sk_selected_abbr else TEAL_DIM
                        for _, r in top15_sk.iterrows()]
            bar_ytick  = ".1f" if pct_mode else ",.0f"
            bar_ysuffix = "%" if pct_mode else ""
            bar_col_lbl = "% of Total" if pct_mode else sk_metric
            bar_title   = f"Top 15 States — {storage_lbl} Stocks ({sk_quarter} {stocks_year})"
            if pct_mode: bar_title += " — % of Total"
            fig_skbar = go.Figure(go.Bar(
                x=top15_sk["state_abbr"], y=top15_sk["disp_val"],
                marker_color=bar_clrs,
                text=top15_sk["disp_val"].apply(_sk_bar_lbl),
                textposition="outside", textfont=dict(color=WHITE, size=11),
                hovertemplate="<b>%{x}</b><br>" + bar_col_lbl + ": %{y:" + bar_ytick + "}" + bar_ysuffix + "<extra></extra>",
            ))
            _base_layout(fig_skbar, title=bar_title, height=400)
            fig_skbar.update_yaxes(tickformat=bar_ytick, ticksuffix=bar_ysuffix)
            fig_skbar.update_layout(showlegend=False)
            st.plotly_chart(fig_skbar, use_container_width=True)

            # ── State comparison table ────────────────────────────────────────
            if pct_mode:
                tbl_hdr_lbl = f"% of Total — {storage_lbl} {sk_quarter} Stocks"
            else:
                tbl_unit_lbl = _tbl_unit(sk_metric)
                tbl_unit_sfx = (f" <span style='color:{TEAL};font-weight:400;text-transform:none;"
                                f"letter-spacing:0'>({tbl_unit_lbl})</span>" if tbl_unit_lbl else "")
                tbl_hdr_lbl = f"{sk_quarter} Stocks{tbl_unit_sfx}"
            st.markdown(
                f"<p style='color:{GRAY};font-size:12px;font-weight:700;"
                f"text-transform:uppercase;letter-spacing:.06em;margin:20px 0 6px'>"
                f"10-Year State Comparison — {tbl_hdr_lbl}</p>",
                unsafe_allow_html=True,
            )

            sk_y0 = stocks_year - 9
            sk_years = list(range(sk_y0, stocks_year + 1))

            with st.spinner("Loading stocks comparison table..."):
                sk_hist = load_stocks_history(commodity, sk_quarter, sk_y0, stocks_year, storage_param)
                sk_nat  = load_stocks_national(commodity, sk_quarter, sk_y0, stocks_year, storage_param)
                if pct_mode:
                    sk_hist_tot = load_stocks_history(commodity, sk_quarter, sk_y0, stocks_year, "TOTAL")
                    sk_nat_tot  = load_stocks_national(commodity, sk_quarter, sk_y0, stocks_year, "TOTAL")
                else:
                    sk_hist_tot = sk_nat_tot = pd.DataFrame()

            if sk_hist.empty or "state_abbr" not in sk_hist.columns:
                c_msg2, c_btn2 = st.columns([5, 1])
                c_msg2.warning("⏱ Stocks comparison data unavailable — NASS API timed out.")
                if c_btn2.button("🔄 Retry", key="retry_stocks_tbl"):
                    st.cache_data.clear(); st.rerun()
            else:
                # Build display history (raw or pct of total)
                if pct_mode and not sk_hist_tot.empty and "state_abbr" in sk_hist_tot.columns:
                    _hm = sk_hist.merge(
                        sk_hist_tot[["year","state_abbr","value"]].rename(columns={"value":"tot_val"}),
                        on=["year","state_abbr"], how="left",
                    )
                    _hm["disp_val"] = _hm["value"] / _hm["tot_val"] * 100
                    sk_hist_disp = _hm[["year","state_abbr","state_name","disp_val"]].rename(columns={"disp_val":"value"})
                else:
                    sk_hist_disp = sk_hist

                if pct_mode and not sk_nat_tot.empty:
                    _nm = sk_nat.merge(
                        sk_nat_tot[["year","value"]].rename(columns={"value":"tot_val"}),
                        on="year", how="left",
                    )
                    _nm["disp_val"] = _nm["value"] / _nm["tot_val"] * 100
                    sk_nat_disp = _nm[["year","disp_val"]].rename(columns={"disp_val":"value"})
                else:
                    sk_nat_disp = sk_nat

                sk_nat_yr   = dict(zip(sk_nat_disp["year"], sk_nat_disp["value"])) if not sk_nat_disp.empty else {}
                sk_nat6     = [sk_nat_yr.get(yr) for yr in sk_years[-6:]]
                sk_nat_olym = _olympic6(sk_nat6)

                # ── Interactive state filter (stocks table) ───────────────────
                _sk_default_groups = COMMODITY_TABLE_GROUPS.get(commodity, [])
                _sk_default_abbrs  = [a for grp in _sk_default_groups for a in grp["states"]]
                _sk_avail_states   = sorted(sk_hist_disp["state_abbr"].dropna().unique().tolist())

                with st.expander("📋 Customize Table States", expanded=False):
                    _sk_sel_states = st.multiselect(
                        "States to include in table",
                        options=_sk_avail_states,
                        default=[s for s in _sk_default_abbrs if s in _sk_avail_states],
                        key=f"sk_tbl_states_{commodity}_{sk_quarter}",
                        help="Defaults to the key producing states for the selected commodity.",
                    )

                if set(_sk_sel_states) == set(s for s in _sk_default_abbrs if s in _sk_avail_states):
                    _sk_active_groups = [
                        {"states": [s for s in grp["states"] if s in _sk_sel_states],
                         "subtotal": grp["subtotal"]}
                        for grp in _sk_default_groups
                        if any(s in _sk_sel_states for s in grp["states"])
                    ]
                else:
                    _sk_active_groups = [{"states": _sk_sel_states, "subtotal": None}]

                sk_all_abbrs = [a for grp in _sk_active_groups for a in grp["states"]]

                sk_state_yr: dict = {}
                for abbr in sk_all_abbrs:
                    sdf = sk_hist_disp[sk_hist_disp["state_abbr"] == abbr]
                    sk_state_yr[abbr] = {int(r["year"]): r["value"] for _, r in sdf.iterrows()}

                sk_cur_yr, sk_prev_yr = sk_years[-1], sk_years[-2]

                def _sk_row(label, yr_map, row_type="state", prior_override=None):
                    row = {"label": label, "row_type": row_type}
                    all_vals = []
                    for yr in sk_years:
                        v = yr_map.get(yr); row[yr] = v
                        if v is not None: all_vals.append(v)
                    recent6 = [yr_map.get(yr) for yr in sk_years[-6:]]
                    olym    = _olympic6(recent6)
                    cur_v   = yr_map.get(sk_cur_yr)
                    prev_v  = prior_override if prior_override is not None else yr_map.get(sk_prev_yr)
                    row["olym"]       = olym
                    row["min_val"]    = min(all_vals) if all_vals else None
                    row["max_val"]    = max(all_vals) if all_vals else None
                    row["pct_us"]     = (olym / sk_nat_olym * 100) if (olym and sk_nat_olym) else None
                    if pct_mode:
                        row["chg_vs_ly"] = (cur_v - prev_v) if (cur_v is not None and prev_v is not None) else None
                    else:
                        row["chg_vs_ly"] = ((cur_v - prev_v) / prev_v * 100) if (cur_v and prev_v) else None
                    row["pct_of_avg"] = (cur_v / olym * 100) if (cur_v and olym) else None
                    return row

                # Build prior-quarter lookup for "vs Last Report" mode
                _sk_prev_q_st: dict = {}
                _sk_prev_q_nat: float | None = None
                if sk_cmp == "vs Last Report" and not sk_snap_prior.empty:
                    for _, _r in sk_snap_prior.iterrows():
                        _sk_prev_q_st[_r["state_abbr"]] = _r["value"]
                    _nat_pq = load_stocks_national(
                        commodity, _prev_q, _prev_yr, _prev_yr, storage_param)
                    _sk_prev_q_nat = _nat_pq["value"].iloc[0] if not _nat_pq.empty else None

                sk_rows = []
                for g_idx, grp in enumerate(_sk_active_groups):
                    grp_states = grp["states"]
                    for abbr in grp_states:
                        po = _sk_prev_q_st.get(abbr) if sk_cmp == "vs Last Report" else None
                        sk_rows.append(_sk_row(abbr, sk_state_yr.get(abbr, {}), "state", po))
                    if grp["subtotal"] and len(grp_states) > 1:
                        sub_yr = {}
                        for yr in sk_years:
                            vals  = [sk_state_yr.get(a, {}).get(yr) for a in grp_states]
                            valid = [v for v in vals if v is not None]
                            sub_yr[yr] = sum(valid) if valid else None
                        if sk_cmp == "vs Last Report":
                            sub_po = sum(_sk_prev_q_st.get(a, 0) for a in grp_states
                                         if _sk_prev_q_st.get(a)) or None
                        else:
                            sub_po = None
                        sk_rows.append(_sk_row(grp["subtotal"], sub_yr, "subtotal", sub_po))
                    if g_idx < len(_sk_active_groups) - 1:
                        sk_rows.append({"row_type": "spacer"})
                us_po = _sk_prev_q_nat if sk_cmp == "vs Last Report" else None
                sk_rows.append(_sk_row("US Total", {yr: sk_nat_yr.get(yr) for yr in sk_years}, "us", us_po))

                # ── Render table (same style as production table) ─────────────
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
                _THD = (f"padding:7px 9px;text-align:right;background:{DARK_ALT};color:{WHITE};"
                        f"font-weight:700;font-size:11px;white-space:nowrap;"
                        f"border-bottom:2px solid {TEAL};border-left:2px solid #4a5568;")

                chg_hdr    = f"ppt vs {_cmp_label}" if pct_mode else f"% vs {_cmp_label}"
                yr_hdrs    = "".join(f"<th style='{_TH}'>{yr}</th>" for yr in sk_years)
                sk_thead   = (f"<thead><tr><th style='{_TH0}'>State / Region</th>{yr_hdrs}"
                              f"<th style='{_THD}'>{chg_hdr}</th>"
                              f"<th style='{_THS}'>6-Yr Olympic Avg</th>"
                              f"<th style='{_THP}'>% of Avg</th>"
                              f"<th style='{_THS}'>Min</th><th style='{_THS}'>Max</th>"
                              f"<th style='{_THP}'>% of U.S.</th></tr></thead>")

                sk_tbody = ""
                row_idx  = 0
                for row in sk_rows:
                    rtype = row.get("row_type")
                    if rtype == "spacer":
                        colspan = 1 + len(sk_years) + 6
                        sk_tbody += (f"<tr><td colspan='{colspan}' "
                                     f"style='height:9px;background:{DARK_BG};'></td></tr>")
                        continue
                    if rtype == "us":
                        bg = "#1b2e30"; c_lbl = TEAL; c_num = WHITE; c_sp = TEAL
                        c_pct = AMBER; fw_lbl = "700"; fs_lbl = "13px"
                        border_top = f"border-top:2px solid {TEAL};"
                    elif rtype == "subtotal":
                        bg = DARK_ALT; c_lbl = TEAL; c_num = TEAL; c_sp = TEAL
                        c_pct = AMBER; fw_lbl = "700"; fs_lbl = "12px"
                        border_top = f"border-top:1px solid {TEAL_DIM};"
                    else:
                        bg = DARK_CARD if row_idx % 2 == 0 else "#302e2e"
                        c_lbl = WHITE; c_num = GRAY; c_sp = WHITE; c_pct = AMBER
                        fw_lbl = "400"; fs_lbl = "12px"; border_top = ""
                        row_idx += 1

                    yr_pairs    = [(yr, row[yr]) for yr in sk_years if row.get(yr) is not None]
                    sorted_vals = sorted(yr_pairs, key=lambda x: x[1])
                    bottom2 = {yr for yr, _ in sorted_vals[:2]}  if len(sorted_vals) >= 2 else set()
                    top2    = {yr for yr, _ in sorted_vals[-2:]} if len(sorted_vals) >= 2 else set()

                    td_lbl = (f"padding:7px 10px;text-align:left;background:{bg};color:{c_lbl};"
                              f"font-weight:{fw_lbl};font-size:{fs_lbl};{border_top}")
                    td_sp  = (f"padding:6px 10px;text-align:right;background:{bg};color:{c_sp};"
                              f"font-weight:600;font-size:12px;border-left:2px solid #4a5568;{border_top}")
                    td_pct = (f"padding:6px 10px;text-align:right;background:{bg};color:{c_pct};"
                              f"font-weight:700;font-size:12px;border-left:1px solid #4a5568;{border_top}")

                    yr_cells = ""
                    for yr in sk_years:
                        v = row.get(yr)
                        if yr in top2 and v is not None:
                            cb = "rgba(34,197,94,0.18)"; cc = "#4ade80"; cf = "700"
                        elif yr in bottom2 and v is not None:
                            cb = "rgba(239,68,68,0.18)"; cc = "#f87171"; cf = "700"
                        else:
                            cb = bg; cc = c_num; cf = "400"
                        yr_cells += (f"<td style='padding:6px 9px;text-align:right;"
                                     f"background:{cb};color:{cc};font-weight:{cf};"
                                     f"font-size:12px;{border_top}'>"
                                     f"{_sk_fmt_cell(v)}</td>")

                    chg = row.get("chg_vs_ly")
                    if chg is None:
                        chg_str = "—"; chg_clr = GRAY; chg_bg = bg
                    elif chg >= 0:
                        chg_sfx = "ppt" if pct_mode else "%"
                        chg_str = f"▲ {chg:.1f}{chg_sfx}"; chg_clr = "#4ade80"; chg_bg = "rgba(34,197,94,0.12)"
                    else:
                        chg_sfx = "ppt" if pct_mode else "%"
                        chg_str = f"▼ {abs(chg):.1f}{chg_sfx}"; chg_clr = "#f87171"; chg_bg = "rgba(239,68,68,0.12)"
                    td_chg = (f"padding:6px 9px;text-align:right;background:{chg_bg};"
                              f"color:{chg_clr};font-weight:700;font-size:12px;"
                              f"border-left:2px solid #4a5568;{border_top}")

                    poa_val = row.get("pct_of_avg")
                    if poa_val is None:
                        poa_str = "—"; poa_clr = GRAY; poa_bg = bg
                    elif poa_val >= 100:
                        poa_str = f"▲ {poa_val - 100:.1f}%"; poa_clr = "#4ade80"; poa_bg = "rgba(34,197,94,0.12)"
                    else:
                        poa_str = f"▼ {100 - poa_val:.1f}%"; poa_clr = "#f87171"; poa_bg = "rgba(239,68,68,0.12)"
                    td_poa = (f"padding:6px 9px;text-align:right;background:{poa_bg};"
                              f"color:{poa_clr};font-weight:700;font-size:12px;"
                              f"border-left:1px solid #4a5568;{border_top}")

                    pct_val = row.get("pct_us")
                    pct_str = "—" if (pct_val is None or pct_mode) else f"{pct_val:.1f}%"

                    sk_tbody += (
                        f"<tr><td style='{td_lbl}'>{row['label']}</td>{yr_cells}"
                        f"<td style='{td_chg}'>{chg_str}</td>"
                        f"<td style='{td_sp}'>{_sk_fmt_cell(row.get('olym'))}</td>"
                        f"<td style='{td_poa}'>{poa_str}</td>"
                        f"<td style='{td_sp}'>{_sk_fmt_cell(row.get('min_val'))}</td>"
                        f"<td style='{td_sp}'>{_sk_fmt_cell(row.get('max_val'))}</td>"
                        f"<td style='{td_pct}'>{pct_str}</td></tr>"
                    )

                st.markdown(
                    f"<div style='overflow-x:auto;border-radius:8px;border:1px solid #4a5568;"
                    f"margin-bottom:12px;'>"
                    f"<table style='border-collapse:collapse;width:100%;font-family:Open Sans,sans-serif;'>"
                    f"{sk_thead}<tbody>{sk_tbody}</tbody></table></div>",
                    unsafe_allow_html=True,
                )
                _render_export_buttons(
                    sk_rows, sk_years,
                    chg_hdr,
                    f"{commodity}_stocks_{sk_quarter}_{stocks_year}".replace(" ", "_"),
                    f"{commodity} Stocks {sk_quarter} {stocks_year}",
                )

            # ── State historical stocks ───────────────────────────────────────
            st.markdown("---")
            if sk_selected_abbr is None:
                st.markdown(
                    f"<div style='background:{DARK_CARD};border-radius:8px;padding:28px;"
                    f"text-align:center;color:{GRAY};font-size:15px;border:1px dashed #4a5568;'>"
                    f"🗺️ &nbsp; Click a state on the map to view its historical trend"
                    f"</div>", unsafe_allow_html=True,
                )
            else:
                hist_sfx = " (% of Total)" if pct_mode else ""
                st.markdown(
                    f"<h3 style='color:{WHITE};margin-bottom:4px'>"
                    f"{sk_selected_name} — Historical {sk_quarter} {storage_lbl} Stocks{hist_sfx}</h3>",
                    unsafe_allow_html=True,
                )
                with st.spinner(f"Loading {sk_selected_name} stocks history..."):
                    sk_full_hist = load_stocks_history(
                        commodity, sk_quarter, year_range[0], year_range[1], storage_param
                    )
                    sk_nat_full  = load_stocks_national(
                        commodity, sk_quarter, year_range[0], year_range[1], storage_param
                    )
                    if pct_mode:
                        sk_full_hist_tot = load_stocks_history(
                            commodity, sk_quarter, year_range[0], year_range[1], "TOTAL"
                        )
                        sk_nat_full_tot  = load_stocks_national(
                            commodity, sk_quarter, year_range[0], year_range[1], "TOTAL"
                        )

                # Convert to % of total for historical charts if needed
                if pct_mode and not sk_full_hist_tot.empty:
                    sk_full_hist = sk_full_hist.merge(
                        sk_full_hist_tot[["year","state_abbr","value"]].rename(columns={"value":"tot_val"}),
                        on=["year","state_abbr"], how="left",
                    )
                    sk_full_hist["value"] = sk_full_hist["value"] / sk_full_hist["tot_val"] * 100
                    sk_nat_full = sk_nat_full.merge(
                        sk_nat_full_tot[["year","value"]].rename(columns={"value":"tot_val"}),
                        on="year", how="left",
                    )
                    sk_nat_full["value"] = sk_nat_full["value"] / sk_nat_full["tot_val"] * 100

                s_sk = sk_full_hist[sk_full_hist["state_abbr"] == sk_selected_abbr].sort_values("year")
                n_sk = sk_nat_full.sort_values("year")

                if s_sk.empty:
                    st.warning(f"No historical stocks data found for {sk_selected_name}.")
                else:
                    col_l, col_r = st.columns(2, gap="medium")
                    h_ytick   = ".1f" if pct_mode else ",.0f"
                    h_ysuffix = "%" if pct_mode else ""
                    h_hover   = f"%{{y:.1f}}%" if pct_mode else "%{y:,.0f}"

                    fig_skt = go.Figure()
                    fig_skt.add_trace(go.Scatter(
                        x=s_sk["year"], y=s_sk["value"],
                        mode="lines+markers",
                        line=dict(color=TEAL, width=2.5), marker=dict(size=5),
                        fill="tozeroy", fillcolor="rgba(91,165,175,0.12)",
                        name=sk_selected_name,
                        hovertemplate=f"<b>%{{x}}</b><br>Stocks: {h_hover}<extra></extra>",
                    ))
                    _base_layout(fig_skt, title=f"{sk_selected_name} — {sk_quarter} {storage_lbl} Stocks{hist_sfx}", height=380)
                    fig_skt.update_yaxes(tickformat=h_ytick, ticksuffix=h_ysuffix)
                    col_l.plotly_chart(fig_skt, use_container_width=True)

                    fig_skv = go.Figure()
                    fig_skv.add_trace(go.Scatter(
                        x=n_sk["year"], y=n_sk["value"],
                        mode="lines", name="U.S. Total",
                        line=dict(color=WHITE, width=2, dash="dot"),
                        hovertemplate=f"<b>U.S.</b><br>%{{x}}: {h_hover}<extra></extra>",
                    ))
                    fig_skv.add_trace(go.Scatter(
                        x=s_sk["year"], y=s_sk["value"],
                        mode="lines+markers", name=sk_selected_name,
                        line=dict(color=TEAL, width=2.5), marker=dict(size=5),
                        hovertemplate=f"<b>{sk_selected_name}</b><br>%{{x}}: {h_hover}<extra></extra>",
                    ))
                    _base_layout(fig_skv, title=f"{sk_selected_name} vs. U.S. — {sk_quarter} {storage_lbl} Stocks{hist_sfx}", height=380)
                    fig_skv.update_yaxes(tickformat=h_ytick, ticksuffix=h_ysuffix)
                    col_r.plotly_chart(fig_skv, use_container_width=True)

# ═════════════════════════════════════════════════════════════════════════════
# TAB 4 — REVISION TRACKER
# ═════════════════════════════════════════════════════════════════════════════
with tab_revisions:
    # Map friendly labels → actual COMMODITIES metric keys
    rev_opts = {}
    for m in metric_list:
        if   "Planted"   in m: rev_opts.setdefault("Planted Acres",   m)
        elif "Harvested" in m: rev_opts.setdefault("Harvested Acres", m)
        elif "Yield"     in m: rev_opts.setdefault("Yield",           m)
        elif "Production" in m: rev_opts.setdefault("Production",     m)

    if not rev_opts:
        st.info(f"No revision data available for {commodity}.")
    else:
        # ── Controls row ─────────────────────────────────────────────────────
        rev_metric_lbl = st.radio(
            "Revision metric",
            list(rev_opts.keys()),
            horizontal=True,
            label_visibility="collapsed",
            key="rev_metric",
        )
        rev_metric = rev_opts[rev_metric_lbl]
        st.markdown("<div style='margin-bottom:6px'></div>", unsafe_allow_html=True)

        rev_level = st.radio(
            "Level",
            ["National", "State"],
            horizontal=True,
            label_visibility="collapsed",
            key="rev_level",
        )
        rev_state_abbr = rev_state_name = None
        if rev_level == "State":
            _sc, _ = st.columns([3, 9])
            rev_state_abbr = _sc.selectbox(
                "State",
                sorted(STATE_ABBREV.values()),
                key="rev_state",
            )
            rev_state_name = ABBREV_STATE.get(rev_state_abbr, "").title()
        st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)

        # Revision period order for this metric type
        _is_acres = ("Acres" in rev_metric_lbl)
        rev_period_list = REVISION_PERIODS_ACRES if _is_acres else REVISION_PERIODS_YLDPROD

        rev_y0 = THIS_YEAR - 9
        rev_y1 = THIS_YEAR

        # ── Load data ─────────────────────────────────────────────────────────
        with st.spinner("Loading revision history from USDA NASS..."):
            rev_df_raw = load_revision_data(
                commodity, rev_metric, rev_y0, rev_y1,
                agg_level="STATE" if rev_level == "State" else "NATIONAL",
            )

        if rev_df_raw.empty:
            _cm, _cb = st.columns([5, 1])
            _cm.warning(f"No revision data found for {commodity} — {rev_metric_lbl}.")
            if _cb.button("🔄 Retry", key="retry_rev"):
                st.cache_data.clear(); st.rerun()
        else:
            # Filter to selected state
            rev_df = rev_df_raw.copy()
            if rev_level == "State" and rev_state_abbr:
                rev_df = rev_df[rev_df["state_abbr"] == rev_state_abbr].copy()

            # Keep only known revision periods and apply short labels
            rev_df = rev_df[rev_df["period"].isin(rev_period_list)].copy()
            rev_df["period_lbl"] = rev_df["period"].map(PERIOD_SHORT).fillna(rev_df["period"])

            # Ordered list of labels that are actually present
            all_labels    = [PERIOD_SHORT.get(p, p) for p in rev_period_list]
            present_lbls  = [l for l in all_labels if l in rev_df["period_lbl"].unique()]

            rev_df["period_cat"] = pd.Categorical(
                rev_df["period_lbl"], categories=all_labels, ordered=True)
            rev_df = rev_df.sort_values(["year", "period_cat"])

            if rev_df.empty or not present_lbls:
                st.info(
                    f"NASS does not publish interim {rev_metric_lbl} estimates — "
                    f"only the final annual value is available for {commodity}."
                )
            else:
                years_avail = sorted(rev_df["year"].unique())
                n_yrs       = len(years_avail)
                yr_colors   = (_REV_PALETTE * 2)[:n_yrs]   # cycle if somehow >10
                yr_colors[-1] = AMBER                       # most recent = amber

                loc_lbl = f" — {rev_state_name}" if rev_state_name else " — U.S. National"

                # ── Section header ────────────────────────────────────────────
                st.markdown(
                    f"<p style='color:{GRAY};font-size:12px;font-weight:700;"
                    f"text-transform:uppercase;letter-spacing:.06em;margin:4px 0 6px'>"
                    f"10-Year Estimate Revision Path — {rev_metric_lbl}{loc_lbl}</p>",
                    unsafe_allow_html=True,
                )

                # ── Chart 1: Line/dot revision paths ─────────────────────────
                fig_rev = go.Figure()
                for i, yr in enumerate(years_avail):
                    ydf = rev_df[rev_df["year"] == yr].sort_values("period_cat")
                    if ydf.empty: continue
                    is_latest = (yr == years_avail[-1])
                    fig_rev.add_trace(go.Scatter(
                        x=ydf["period_lbl"],
                        y=ydf["value"],
                        mode="lines+markers",
                        name=str(yr),
                        line=dict(color=yr_colors[i], width=2.5 if is_latest else 1.5),
                        marker=dict(size=9 if is_latest else 5, color=yr_colors[i]),
                        opacity=1.0 if is_latest else 0.75,
                        hovertemplate=(
                            f"<b>{yr}</b><br>"
                            "%{x}: %{y:,.2f}" if _is_acres else
                            f"<b>{yr}</b><br>%{{x}}: %{{y:{_ytick(rev_metric)}}}"
                        ) + "<extra></extra>",
                    ))

                _base_layout(fig_rev, height=440)
                fig_rev.update_layout(
                    xaxis=dict(
                        categoryorder="array", categoryarray=present_lbls,
                        gridcolor="#4a5568", tickfont=dict(color=WHITE, size=11),
                        title=dict(text="Reporting Period", font=dict(color=GRAY, size=11)),
                    ),
                    yaxis=dict(
                        tickformat=_ytick(rev_metric),
                        title=dict(text=_tbl_unit(rev_metric), font=dict(color=GRAY, size=11)),
                    ),
                    legend=dict(
                        orientation="h", yanchor="bottom", y=1.02,
                        xanchor="left", x=0, font=dict(size=11, color=WHITE),
                    ),
                    hovermode="x unified",
                )
                st.plotly_chart(fig_rev, use_container_width=True)

                # ── Trend callout ─────────────────────────────────────────────
                if len(present_lbls) >= 2 and "Final" in present_lbls:
                    _first_lbl   = present_lbls[0]
                    _completed   = [y for y in years_avail[:-1]][-3:]  # last 3 complete years
                    _rev_changes = []
                    for yr in _completed:
                        _ydf  = rev_df[rev_df["year"] == yr]
                        _vf   = _ydf.loc[_ydf["period_lbl"] == _first_lbl,  "value"]
                        _vfin = _ydf.loc[_ydf["period_lbl"] == "Final",     "value"]
                        if not _vf.empty and not _vfin.empty and _vf.iloc[0] != 0:
                            _rev_changes.append((_vfin.iloc[0] - _vf.iloc[0]) / _vf.iloc[0] * 100)
                    if _rev_changes:
                        _avg_chg   = sum(_rev_changes) / len(_rev_changes)
                        _all_up    = all(c > 0 for c in _rev_changes)
                        _all_down  = all(c < 0 for c in _rev_changes)
                        _direction = "higher" if _avg_chg > 0 else "lower"
                        _consist   = "consistently" if (_all_up or _all_down) else "generally"
                        _clr       = GREEN if _avg_chg > 0 else RED
                        _loc       = f"{rev_state_name} " if rev_state_name else ""
                        st.markdown(
                            f"<div style='background:{DARK_CARD};border-left:4px solid {_clr};"
                            f"border-radius:6px;padding:10px 16px;margin:4px 0 18px'>"
                            f"<span style='color:{GRAY};font-size:11px;font-weight:700;"
                            f"text-transform:uppercase;letter-spacing:.05em'>Recent Revision Trend</span><br>"
                            f"<span style='color:{WHITE};font-size:13px'>"
                            f"Over the last {len(_rev_changes)} completed crop years, USDA has "
                            f"{_consist} revised {_loc}<b>{rev_metric_lbl}</b> "
                            f"<b style='color:{_clr}'>{_direction}</b> from "
                            f"<b>{_first_lbl}</b> to <b>Final</b> "
                            f"(average: <b style='color:{_clr}'>{_avg_chg:+.1f}%</b>)."
                            f"</span></div>",
                            unsafe_allow_html=True,
                        )

                # ── Chart 2: Period-to-Period column chart ────────────────────
                st.markdown("---")
                st.markdown(
                    f"<p style='color:{GRAY};font-size:12px;font-weight:700;"
                    f"text-transform:uppercase;letter-spacing:.06em;margin-bottom:10px'>"
                    f"Period Comparison — select start &amp; end checkpoints</p>",
                    unsafe_allow_html=True,
                )

                # Only offer curated key checkpoints in the comparison dropdowns;
                # the line chart above already shows every available period.
                _key_pool = KEY_CMP_ACRES if _is_acres else KEY_CMP_YLDPROD
                _cmp_opts = [p for p in _key_pool if p in present_lbls]

                if len(_cmp_opts) >= 2:
                    _ca, _cb2, _cc = st.columns([2, 2, 2])
                    _from_lbl = _ca.selectbox(
                        "From",
                        _cmp_opts[:-1],
                        key="rev_from",
                    )
                    _to_opts  = [p for p in _cmp_opts
                                 if _cmp_opts.index(p) > _cmp_opts.index(_from_lbl)]
                    _to_lbl   = _cb2.selectbox(
                        "To",
                        _to_opts if _to_opts else [_cmp_opts[-1]],
                        index=len(_to_opts) - 1 if _to_opts else 0,
                        key="rev_to",
                    )
                    _col_view = _cc.radio(
                        "View as",
                        ["% Change", "Absolute"],
                        horizontal=True,
                        label_visibility="visible",
                        key="rev_view",
                    )

                    _comp_rows = []
                    for yr in years_avail:
                        _ydf   = rev_df[rev_df["year"] == yr]
                        _vs    = _ydf.loc[_ydf["period_lbl"] == _from_lbl, "value"]
                        _ve    = _ydf.loc[_ydf["period_lbl"] == _to_lbl,   "value"]
                        if not _vs.empty and not _ve.empty:
                            vs, ve = _vs.iloc[0], _ve.iloc[0]
                            delta  = ((ve - vs) / vs * 100) if _col_view == "% Change" else (ve - vs)
                            _comp_rows.append({"year": yr, "delta": delta,
                                               "v_start": vs, "v_end": ve})

                    if _comp_rows:
                        _comp_df  = pd.DataFrame(_comp_rows).dropna(subset=["delta"])
                        _avg_d    = _comp_df["delta"].mean()
                        _bar_clrs = [GREEN if d >= 0 else RED for d in _comp_df["delta"]]

                        if _col_view == "% Change":
                            _yt, _ys = "+.1f", "%"
                            _txt_fn  = lambda d: f"{d:+.1f}%"
                        else:
                            _yt, _ys = ",.0f", ""
                            _txt_fn  = lambda d: _nom_chg_str(d, rev_metric)

                        fig_col = go.Figure()
                        fig_col.add_trace(go.Bar(
                            x=_comp_df["year"].astype(str),
                            y=_comp_df["delta"],
                            marker_color=_bar_clrs,
                            text=[_txt_fn(d) for d in _comp_df["delta"]],
                            textposition="outside",
                            textfont=dict(color=WHITE, size=11),
                            hovertemplate=(
                                "<b>%{x}</b><br>"
                                + f"{_from_lbl} → {_to_lbl}: %{{y:{_yt}}}{_ys}<br>"
                                + "From: %{customdata[0]}<br>"
                                + "To:   %{customdata[1]}"
                                + "<extra></extra>"
                            ),
                            customdata=list(zip(
                                _comp_df["v_start"].apply(lambda v: _bar_label(v, rev_metric)),
                                _comp_df["v_end"].apply(lambda v: _bar_label(v, rev_metric)),
                            )),
                        ))
                        # Average line
                        fig_col.add_hline(
                            y=_avg_d, line_dash="dash",
                            line_color=AMBER, line_width=1.5,
                            annotation_text=f"Avg {_avg_d:+.1f}{_ys}",
                            annotation_position="top right",
                            annotation_font_color=AMBER,
                        )
                        fig_col.add_hline(y=0, line_color=GRAY, line_width=0.8)

                        _col_title = (
                            f"{rev_metric_lbl}: {_from_lbl} → {_to_lbl}{loc_lbl}"
                        )
                        _base_layout(fig_col, title=_col_title, height=390)
                        fig_col.update_yaxes(tickformat=_yt, ticksuffix=_ys)
                        fig_col.update_layout(showlegend=False)
                        st.plotly_chart(fig_col, use_container_width=True)
                    else:
                        st.info(
                            f"No years with data for both **{_from_lbl}** and **{_to_lbl}**. "
                            f"Try a different period pair."
                        )
                else:
                    st.info(
                        "Not enough key checkpoints found in NASS for this metric — "
                        "try a different commodity or metric."
                    )
