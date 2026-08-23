"""
╔══════════════════════════════════════════════════════════╗
║             LIFE-OS  —  Productivity Command Center      ║
║         v3: Modular · Hardened · AI-Native · Polished    ║
╚══════════════════════════════════════════════════════════╝

app.py is the thin Streamlit UI router.
All logic lives in:
  data.py         — CSV loading, aggregation, scoring
  ai_coach.py     — Gemini API, prompts, cache, offline fallback
  viz.py          — Plotly & HTML chart builders
  gamification.py — XP, streaks, badges, PDF, Wrapped card
"""

import calendar as _cal
import hashlib
import io
from datetime import date as _date
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# ─── Module imports ────────────────────────────────────────────────────────────
from data import (
    SEVERE_THRESHOLD,
    compute_daily_totals,
    compute_life_score,
    compute_severity,
    get_day_df,
    load_data,
)
from ai_coach import (
    OFFLINE_TEMPLATES,
    PERSONALITIES,
    get_coaching,
)
from viz import (
    build_compare_chart,
    build_life_score_gauge,
    build_real_world_gauges_html,
    build_sankey,
    build_trend_chart,
)
from gamification import (
    LEVEL_LABELS,
    XP_PER_LEVEL,
    compute_badges,
    compute_day_records,
    compute_streak_xp,
    generate_pdf,
    generate_wrapped_card,
)
from layout import render_sidebar, render_kpi_row

load_dotenv()

# Color palette (used in inline HTML)
COLOR_JUNK    = "#FF4B4B"
COLOR_PROTEIN = "#FFA500"
COLOR_GRAINS  = "#00C49A"

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Life-OS | Productivity Command Center",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Global CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&family=JetBrains+Mono:wght@400;700&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  .stApp { background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%); }

  /* ── Global text visibility — white on ALL three dynamic backgrounds ── */
  /* Main content area */
  .stApp p, .stApp span, .stApp div,
  .stApp label, .stApp small { color: #e5e7eb; }

  /* Sidebar text */
  [data-testid="stSidebar"] p,
  [data-testid="stSidebar"] span,
  [data-testid="stSidebar"] div,
  [data-testid="stSidebar"] label,
  [data-testid="stSidebar"] small { color: #e5e7eb !important; }

  /* Streamlit widget labels (selectbox, slider, radio) */
  .stSelectbox label, .stSlider label,
  .stRadio label, .stTextInput label,
  .stNumberInput label, .stTextArea label,
  [data-testid="stWidgetLabel"] { color: #e5e7eb !important; }

  /* Metric cards — force all text white */
  [data-testid="metric-container"] {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 12px;
    padding: 16px !important;
    backdrop-filter: blur(10px);
  }
  [data-testid="stMetricLabel"],
  [data-testid="stMetricLabel"] p,
  [data-testid="stMetricLabel"] span { color: #d1d5db !important; font-weight: 600; }
  [data-testid="stMetricValue"],
  [data-testid="stMetricValue"] div { color: #ffffff !important; font-weight: 800; }
  /* Delta keeps its semantic color (red/green) but must be legible */
  [data-testid="stMetricDelta"] { opacity: 1 !important; }
  [data-testid="stMetricDelta"] span { font-weight: 700 !important; }

  /* Caption / small text */
  [data-testid="stCaptionContainer"] p,
  .stCaption p { color: #9ca3af !important; }

  /* Expander headers */
  [data-testid="stExpander"] summary p,
  [data-testid="stExpander"] summary span { color: #e5e7eb !important; font-weight: 600; }

  /* Markdown paragraphs inside main area */
  .stMarkdown p, .stMarkdown li,
  .stMarkdown td, .stMarkdown th { color: #e5e7eb !important; }

  /* Radio button labels */
  .stRadio div[role="radiogroup"] label,
  .stRadio div[role="radiogroup"] p { color: #e5e7eb !important; }

  /* Headings always white */
  h1, h2, h3, h4 { color: #ffffff !important; }
  h1 { font-weight: 900 !important; }

  /* Sidebar nav/title */
  [data-testid="stSidebar"] h1,
  [data-testid="stSidebar"] h2,
  [data-testid="stSidebar"] h3 { color: #ffffff !important; }

  /* ── Light-background inputs: use DARK text so it's readable ──────────────
     Selectbox, multiselect, number/text inputs all render a white/near-white
     box. Our global white-text rule makes the selected value invisible there.
     These overrides target the inner value display and the dropdown list.    */

  /* Selectbox — closed state: selected value text */
  [data-testid="stSelectbox"] [data-baseweb="select"] span,
  [data-testid="stSelectbox"] [data-baseweb="select"] div,
  [data-testid="stSelectbox"] [data-baseweb="select"] input,
  /* Sidebar selectbox */
  [data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] span,
  [data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] div {
    color: #1e1b4b !important;
  }

  /* Selectbox — dropdown list items */
  [data-baseweb="popover"] li,
  [data-baseweb="popover"] span,
  [data-baseweb="menu"] li,
  [data-baseweb="menu"] span,
  [role="option"] span,
  [role="listbox"] li { color: #1e1b4b !important; }

  /* Selectbox — dropdown list background */
  [data-baseweb="popover"],
  [data-baseweb="menu"] {
    background: #ffffff !important;
  }

  /* Text / Number inputs */
  [data-testid="stTextInput"] input,
  [data-testid="stNumberInput"] input,
  [data-testid="stTextArea"] textarea {
    color: #1e1b4b !important;
    background: rgba(255,255,255,0.92) !important;
  }

  /* Multiselect — tags and input text */
  [data-testid="stMultiSelect"] [data-baseweb="tag"] span,
  [data-testid="stMultiSelect"] [data-baseweb="select"] input { color: #1e1b4b !important; }

  /* Selectbox label (above the box) stays white */
  [data-testid="stSelectbox"] label,
  [data-testid="stSelectbox"] [data-testid="stWidgetLabel"] p { color: #e5e7eb !important; }

  /* ── Buttons ── */
  .stButton > button {
    background: linear-gradient(90deg, #7C3AED, #EC4899);
    color: white !important; border: none; border-radius: 8px; font-weight: 700;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
  }
  .stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 24px rgba(124,58,237,0.5);
  }
  .stDownloadButton > button {
    background: linear-gradient(90deg, #059669, #10b981);
    color: white !important; border: none; border-radius: 8px; font-weight: 700;
  }
  /* Form submit button */
  [data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(90deg, #7C3AED, #EC4899);
    color: white !important; font-weight: 700; border: none; border-radius: 8px;
  }

  /* ── Section headers (monospace pill) ── */
  .section-header {
    font-family: 'JetBrains Mono', monospace;
    color: #c4b5fd !important; font-size: 0.75rem; letter-spacing: 0.15em;
    text-transform: uppercase; border-bottom: 1px solid rgba(167,139,250,0.4);
    padding-bottom: 6px; margin-bottom: 16px;
  }

  /* ── Status badges ── */
  .badge { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
  .badge-live    { background:#064e3b; color:#6ee7b7 !important; border:1px solid #059669; }
  .badge-cached  { background:#78350f; color:#fcd34d !important; border:1px solid #d97706; }
  .badge-offline { background:#7f1d1d; color:#fca5a5 !important; border:1px solid #dc2626; }

  /* ── Pyramid blocks ── */
  .pyramid-block {
    border-radius: 10px; display: block; height: auto; font-weight: 700;
    font-size: 0.88rem; color: white !important; padding: 12px 16px;
    margin: 5px auto; text-align: center; line-height: 1.6;
    box-shadow: 0 4px 16px rgba(0,0,0,0.3); transition: transform 0.2s ease;
  }
  .pyramid-block:hover { transform: scale(1.02); }

  /* ── XP bar ── */
  .xp-bar-bg   { background:rgba(255,255,255,0.12); border-radius:999px; height:10px; overflow:hidden; margin-top:6px; }
  .xp-bar-fill { height:100%; border-radius:999px; background:linear-gradient(90deg,#7C3AED,#EC4899); transition:width 0.4s ease; }

  /* ── Accountability link box ── */
  .copy-box {
    background:rgba(255,255,255,0.07); border:1px solid rgba(124,58,237,0.4);
    border-radius:8px; padding:8px 12px; font-family:'JetBrains Mono',monospace;
    font-size:0.8rem; color:#d8b4fe !important; word-break:break-all;
  }

  /* ── Voice journal card ── */
  .voice-card {
    background: rgba(124,58,237,0.1); border: 1px solid rgba(167,139,250,0.3);
    border-radius: 12px; padding: 14px 16px; margin-bottom: 12px;
  }
  .voice-card p, .voice-card span, .voice-card strong { color: #e5e7eb !important; }

  /* ── Data editor ── */
  [data-testid="stDataFrame"] th,
  [data-testid="stDataFrame"] td { color: #e5e7eb !important; }

  /* ── Info / warning / error boxes keep Streamlit's colors ── */
  [data-testid="stAlert"] p { color: inherit !important; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

df = load_data()
all_dates = sorted(df["Date"].dt.date.unique()) if not df.empty else []

# ─── Session state defaults ───────────────────────────────────────────────────
for _key, _val in {
    "xp": 0, "streak": 0, "xp_computed": False,
    "ai_status": None, "last_coaching": None, "last_severity": None,
    "voice_transcript": "",
}.items():
    if _key not in st.session_state:
        st.session_state[_key] = _val


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR

# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR  (delegated to layout.py)
# ═══════════════════════════════════════════════════════════════════════════════

selected_date, goal, personality, coach_submitted = render_sidebar(df, all_dates)

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN AREA — early exit guard
# ═══════════════════════════════════════════════════════════════════════════════

if df.empty or not all_dates:
    st.error("No data loaded. Fix the CSV file path and restart.")
    st.stop()

# ─── App header ───────────────────────────────────────────────────────────────
st.markdown(
    '<h1 style="text-align:center;font-size:2.8rem;background:linear-gradient(90deg,#a78bfa,#ec4899);'
    '-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:0">🧠 Life-OS</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    '<p style="text-align:center;color:#9ca3af;margin-top:0">Productivity Command Center '
    '— Brutally Honest. Beautifully Designed.</p>',
    unsafe_allow_html=True,
)
st.markdown("---")

# ─── Per-day data ─────────────────────────────────────────────────────────────
day_df      = get_day_df(df, selected_date)
today_total = int(day_df["Minutes_Used"].sum())

# ─── Phase 3: st.data_editor expander — BEFORE KPIs so edits propagate ────────
with st.expander("📋 Raw Daily Log — view & edit app-by-app minutes", expanded=False):
    st.caption(
        "Correct any app's minutes below. Edits propagate to KPIs, charts, "
        "and gauges for this session (not saved to CSV)."
    )
    _day_display = day_df[["App_Name", "Category", "Minutes_Used"]].reset_index(drop=True)
    _edited = st.data_editor(
        _day_display,
        column_config={
            "App_Name":     st.column_config.TextColumn("App", disabled=True),
            "Category":     st.column_config.TextColumn("Category", disabled=True),
            "Minutes_Used": st.column_config.NumberColumn("Minutes", min_value=0, max_value=600, step=1),
        },
        hide_index=True,
        width="stretch",
        key="log_editor",
    )
    # Apply edits if changed
    if not _edited["Minutes_Used"].equals(_day_display["Minutes_Used"]):
        day_df = day_df.copy()
        day_df["Minutes_Used"] = _edited["Minutes_Used"].values
        today_total = int(day_df["Minutes_Used"].sum())
        st.info("✏️ KPIs and charts reflect your edits for this session.")

# ─── Dynamic background based on severity ─────────────────────────────────────
_sev_now = compute_severity(today_total, goal)
_BG = {
    "good":     {"bg": "linear-gradient(135deg,#042a14 0%,#0d3b2e 45%,#063324 100%)",
                 "sidebar": "rgba(4,42,20,0.97)", "border": "rgba(16,185,129,0.35)",
                 "label": "🟢 Low Screen Time Day", "label_color": "#6ee7b7"},
    "moderate": {"bg": "linear-gradient(135deg,#0f0c29 0%,#302b63 50%,#24243e 100%)",
                 "sidebar": "rgba(15,12,41,0.97)", "border": "rgba(124,58,237,0.35)",
                 "label": "🟡 Moderate Screen Time Day", "label_color": "#fcd34d"},
    "severe":   {"bg": "linear-gradient(135deg,#1e0505 0%,#4a1010 45%,#2d0a0a 100%)",
                 "sidebar": "rgba(30,5,5,0.97)", "border": "rgba(220,38,38,0.4)",
                 "label": "🔴 High Screen Time Day", "label_color": "#fca5a5"},
}
_cfg = _BG[_sev_now]
st.markdown(f"""
<style>
  .stApp {{background:{_cfg['bg']} !important; transition:background 0.8s ease;}}
  [data-testid="stSidebar"] {{
    background:{_cfg['sidebar']} !important;
    border-right:1px solid {_cfg['border']} !important;
    transition:background 0.8s ease;
  }}
  .st-severity-badge {{
    display:inline-block; padding:4px 14px; border-radius:999px;
    font-size:0.78rem; font-weight:700;
    color:{_cfg['label_color']}; border:1px solid {_cfg['label_color']}40;
    background:{_cfg['label_color']}15; letter-spacing:0.04em;
  }}
</style>
""", unsafe_allow_html=True)
st.markdown(
    f'<p style="text-align:center;margin-bottom:16px">'
    f'<span class="st-severity-badge">{_cfg["label"]}</span></p>',
    unsafe_allow_html=True,
)

# ─── KPI row  (delegated to layout.py) ────────────────────────────────────────────────────────
most_used_app = (
    day_df.loc[day_df["Minutes_Used"].idxmax(), "App_Name"]
    if not day_df.empty else "N/A"
)
delta_vs_goal = today_total - goal

_yesterday        = selected_date - timedelta(days=1)
_daily_totals_map = compute_daily_totals(df)
_yesterday_total  = (
    int(_daily_totals_map.get(pd.Timestamp(_yesterday), None) or 0)
    if _yesterday in [d.date() for d in _daily_totals_map.index]
    else None
)

render_kpi_row(today_total, _yesterday_total, goal, most_used_app, delta_vs_goal, selected_date)
st.markdown("---")

# ─── Life Score Gauge ──────────────────────────────────────────────────────────
st.markdown('<p class="section-header">// 🎯 Life Score</p>', unsafe_allow_html=True)
life_score_today = compute_life_score(day_df, today_total, goal)
_ls_color = "#22c55e" if life_score_today >= 70 else ("#f59e0b" if life_score_today >= 40 else "#ef4444")

ls_col1, ls_col2 = st.columns([1, 1])
with ls_col1:
    st.plotly_chart(build_life_score_gauge(life_score_today), width="stretch")
with ls_col2:
    # Phase 3: yesterday Life Score for delta
    _yday_ls = None
    if _yesterday_total is not None:
        _yday_df = get_day_df(df, _yesterday)
        _yday_ls = compute_life_score(_yday_df, _yesterday_total, goal)
    _ls_delta = (life_score_today - _yday_ls) if _yday_ls is not None else None
    st.metric(
        "Life Score",
        f"{life_score_today} / 100",
        delta=f"{_ls_delta:+d} vs yesterday" if _ls_delta is not None else None,
        delta_color="normal",
    )
    st.markdown(f"""
    <div style="padding-top:10px">
      <p style="color:#9ca3af;font-size:0.85rem;line-height:1.6">
        Life Score isn't just "less time = better" — it's <strong style="color:{_ls_color}">60% category
        balance</strong> (productive vs junk time) <strong>+ 40% goal adherence</strong>.<br><br>
        A day full of coding at 9 hours can score higher than a "short" day of pure doomscrolling.
      </p>
    </div>
    """, unsafe_allow_html=True)

# Phase 3: How Life Score is calculated expander
with st.expander("ℹ️ How is the Life Score calculated?", expanded=False):
    st.markdown("""
    The **Life Score (0–100)** uses a two-component formula:

    | Component | Weight | Description |
    |---|---|---|
    | **Category Balance** | 60% | `50 + 50 × (productive − junk) / (productive + junk + 1)` |
    | **Goal Adherence**   | 40% | `100 − max(0, ratio−1) × 150` — steep penalty once over goal |

    - **Productive** = Education + Coding minutes
    - **Junk** = Social Media + Entertainment minutes
    - Scores range 0–100. **≥70** = great day. **40–69** = moderate. **<40** = intervention needed.
    - A high-coding day at 9 h total can score higher than a 2 h pure doomscrolling day.
    """)

st.markdown("---")

# ─── 14-Day Trend Chart ────────────────────────────────────────────────────────
st.markdown('<p class="section-header">// 📈 14-Day Screen Time Trend</p>', unsafe_allow_html=True)
daily_totals_df = compute_daily_totals(df).reset_index()
daily_totals_df.columns = ["Date", "Minutes"]
st.plotly_chart(
    build_trend_chart(daily_totals_df, selected_date, goal),
    width="stretch",
)

st.markdown("---")

# ─── Compare Two Days ─────────────────────────────────────────────────────────
st.markdown('<p class="section-header">// ⚔️ Compare Two Days</p>', unsafe_allow_html=True)
cmp_c1, cmp_c2 = st.columns(2)
with cmp_c1:
    day_a = st.selectbox("Day A", options=all_dates, index=len(all_dates)-1,
                          format_func=lambda d: d.strftime("%A, %b %d"), key="cmp_day_a")
with cmp_c2:
    day_b = st.selectbox("Day B", options=all_dates, index=max(0, len(all_dates)-2),
                          format_func=lambda d: d.strftime("%A, %b %d"), key="cmp_day_b")

df_a = get_day_df(df, day_a).groupby("Category")["Minutes_Used"].sum()
df_b = get_day_df(df, day_b).groupby("Category")["Minutes_Used"].sum()
st.plotly_chart(build_compare_chart(df_a, df_b, day_a, day_b), width="stretch")

total_a, total_b = int(df_a.sum()), int(df_b.sum())
diff = total_a - total_b
st.caption(
    f"{day_a.strftime('%b %d')}: **{total_a} min** vs {day_b.strftime('%b %d')}: **{total_b} min** — "
    f"{'Day A' if diff > 0 else 'Day B'} used {abs(diff)} more minutes."
)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# CUSTOM FEATURES
# ═══════════════════════════════════════════════════════════════════════════════

feat_col1, feat_col2 = st.columns([1, 1], gap="large")

# ─── Feature 1: What-If Time Machine ──────────────────────────────────────────
with feat_col1:
    st.markdown('<p class="section-header">// ⏳ What-If Time Machine</p>', unsafe_allow_html=True)
    reduce_pct = st.slider(
        "Reduce screen time by:", min_value=5, max_value=90, value=30, step=5,
        format="%d%%", key="time_machine_slider",
    )
    hours_saved = (today_total * (reduce_pct / 100) * 365) / 60
    days_saved  = hours_saved / 24
    waking_days = hours_saved / 16
    st.markdown(f"""
    <div style="background:rgba(124,58,237,0.15);border:1px solid rgba(124,58,237,0.4);
                border-radius:12px;padding:16px;margin-top:8px">
      <p style="color:#a78bfa;font-size:0.8rem;margin:0 0 6px 0;font-weight:600">YEARLY PROJECTION</p>
      <p style="color:white;font-size:1.1rem;font-weight:700;margin:0">
        {reduce_pct}% kam karo screen time,<br>
        saal me milenge <span style="color:#ec4899">~{days_saved:.1f} extra din</span><br>
        <span style="color:#fbbf24;font-size:0.95rem">({waking_days:.1f} waking-hours basis)</span>
      </p>
    </div>
    """, unsafe_allow_html=True)

# ─── Feature 2: Real-World Equivalents (gauge bars via viz.py) ────────────────
with feat_col2:
    st.markdown('<p class="section-header">// 📚 Real-World Equivalents</p>', unsafe_allow_html=True)
    junk_mins = int(
        day_df[day_df["Category"].isin(["Social Media", "Entertainment"])]["Minutes_Used"].sum()
    )
    st.markdown(build_real_world_gauges_html(junk_mins), unsafe_allow_html=True)
    st.caption(f"Based on {junk_mins} min of Social + Entertainment today")

st.markdown("---")

feat_col3, feat_col4 = st.columns([1, 1], gap="large")

# ─── Feature 3: Digital Diet Pyramid ──────────────────────────────────────────
with feat_col3:
    st.markdown('<p class="section-header">// 🍕 Digital Diet Pyramid</p>', unsafe_allow_html=True)
    cat_totals   = day_df.groupby("Category")["Minutes_Used"].sum()
    junk_p   = int(cat_totals.get("Social Media", 0) + cat_totals.get("Entertainment", 0))
    protein_p = int(cat_totals.get("Communication", 0))
    grains_p  = int(cat_totals.get("Education", 0) + cat_totals.get("Coding", 0))
    pyr_total = junk_p + protein_p + grains_p or 1
    junk_w  = max(30, int((junk_p   / pyr_total) * 75) + 10)
    prot_w  = max(45, int((protein_p / pyr_total) * 75) + 20)
    grain_w = 100
    st.markdown(f"""
    <div style="display:flex;flex-direction:column;align-items:center;gap:8px;padding:12px 4px">
      <div class="pyramid-block" style="background:linear-gradient(135deg,{COLOR_JUNK},{COLOR_JUNK}cc);width:{junk_w}%">
        <div style="font-size:1.2rem">🍬</div>
        <div style="font-size:0.9rem;font-weight:800">JUNK</div>
        <div style="font-size:0.75rem;opacity:0.85">Social + Entertainment</div>
        <div style="font-size:1.1rem;font-weight:900;margin-top:2px">{junk_p} min</div>
      </div>
      <div class="pyramid-block" style="background:linear-gradient(135deg,{COLOR_PROTEIN},{COLOR_PROTEIN}cc);width:{prot_w}%">
        <div style="font-size:1.2rem">🥩</div>
        <div style="font-size:0.9rem;font-weight:800">PROTEIN</div>
        <div style="font-size:0.75rem;opacity:0.85">Communication</div>
        <div style="font-size:1.1rem;font-weight:900;margin-top:2px">{protein_p} min</div>
      </div>
      <div class="pyramid-block" style="background:linear-gradient(135deg,{COLOR_GRAINS},{COLOR_GRAINS}cc);width:{grain_w}%">
        <div style="font-size:1.2rem">🌾</div>
        <div style="font-size:0.9rem;font-weight:800">WHOLE GRAINS</div>
        <div style="font-size:0.75rem;opacity:0.85">Education + Coding</div>
        <div style="font-size:1.1rem;font-weight:900;margin-top:2px">{grains_p} min</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ─── Feature 4: Streak & XP System (GitHub-style monthly heatmap) ─────────────
with feat_col4:
    st.markdown('<p class="section-header">// 🏅 Streak & XP System</p>', unsafe_allow_html=True)

    # Compute per-day records for heatmap
    _day_totals_series = compute_daily_totals(df).sort_index()
    day_records = compute_day_records(_day_totals_series, goal)
    _streak_max = max((r[3] for r in day_records), default=0)

    if not st.session_state["xp_computed"]:
        streak, xp = compute_streak_xp(_day_totals_series, goal)
        st.session_state["streak"] = streak
        st.session_state["xp"]     = xp
        st.session_state["xp_computed"] = True

    streak = st.session_state["streak"]
    xp     = st.session_state["xp"]
    level  = xp // XP_PER_LEVEL
    xp_in_level = xp % XP_PER_LEVEL
    xp_pct = int((xp_in_level / XP_PER_LEVEL) * 100)

    sx1, sx2, sx3 = st.columns(3)
    with sx1:
        st.metric("🔥 Streak", f"{streak} days",
                  delta=f"Max: {_streak_max}d", delta_color="off")
    with sx2:
        st.metric("⚡ Total XP", f"{xp} XP")
    with sx3:
        st.metric("🎖️ Level", f"Lvl {level}")

    # Full-month GitHub-style heatmap
    _STATUS_COLORS = {
        "good":     ("#22c55e", "#166534"),
        "ok":       ("#4ade80", "#14532d"),
        "moderate": ("#f59e0b", "#78350f"),
        "severe":   ("#ef4444", "#7f1d1d"),
    }
    _data_lookup   = {rec[0]: (rec[1], rec[2]) for rec in day_records}
    _month_year    = (selected_date.year, selected_date.month)
    _month_name    = _date(*_month_year, 1).strftime("%B %Y")
    _days_in_month = _cal.monthrange(*_month_year)[1]
    _first_wd      = _cal.monthrange(*_month_year)[0]
    _WD_LABELS     = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
    BOX = "width:26px;height:26px;border-radius:5px;display:inline-flex;align-items:center;justify-content:center;"

    cal_html = (
        '<div style="margin:8px 0 4px 0">'
        f'<div style="color:#a78bfa;font-size:0.78rem;font-weight:700;margin-bottom:8px;letter-spacing:0.05em">{_month_name}</div>'
        '<div style="display:grid;grid-template-columns:repeat(7,30px);gap:4px;margin-bottom:4px">'
    )
    for wd in _WD_LABELS:
        cal_html += f'<div style="width:26px;text-align:center;font-size:0.6rem;color:#6b7280;font-weight:700">{wd}</div>'
    cal_html += '</div><div style="display:grid;grid-template-columns:repeat(7,30px);gap:4px">'

    for _ in range(_first_wd):
        cal_html += f'<div style="{BOX}background:transparent"></div>'

    for _dn in range(1, _days_in_month + 1):
        _d     = _date(*_month_year, _dn)
        _is_sel = (_d == selected_date)
        if _d in _data_lookup:
            _tot, _stat = _data_lookup[_d]
            fg, bg = _STATUS_COLORS[_stat]
            _tip   = f"{_d}  {_tot} min"
            _inner = (f'background:linear-gradient(135deg,{fg}cc,{fg}55);'
                      f'border:{"2px solid "+fg if _is_sel else "1.5px solid "+bg};'
                      f'box-shadow:{"0 0 10px "+fg+"aa" if _is_sel else "none"};')
            _lc    = "white"
        else:
            fg, _inner = "#374151", (
                f'background:rgba(255,255,255,0.04);'
                f'border:{"2px solid #a78bfa" if _is_sel else "1.5px solid rgba(255,255,255,0.07)"};'
                f'box-shadow:{"0 0 8px #a78bfaaa" if _is_sel else "none"};'
            )
            _tip = f"{_d}  no data"
            _lc  = "#4b5563"
        cal_html += (
            f'<div title="{_tip}" style="{BOX}{_inner}cursor:default;transition:transform 0.15s,box-shadow 0.15s;" '
            f'onmouseover="this.style.transform=\'scale(1.3)\'" onmouseout="this.style.transform=\'scale(1)\'"><span '
            f'style="font-size:0.6rem;font-weight:700;color:{_lc}">{_dn}</span></div>'
        )

    cal_html += '</div>'
    cal_html += (
        '<div style="display:flex;gap:10px;align-items:center;margin-top:10px;flex-wrap:wrap">'
        '<span style="font-size:0.65rem;color:#6b7280">Legend:</span>'
        '<span style="display:inline-flex;align-items:center;gap:3px;font-size:0.65rem;color:#9ca3af"><span style="width:10px;height:10px;border-radius:2px;background:#22c55e;display:inline-block"></span>Great</span>'
        '<span style="display:inline-flex;align-items:center;gap:3px;font-size:0.65rem;color:#9ca3af"><span style="width:10px;height:10px;border-radius:2px;background:#4ade80;display:inline-block"></span>Good</span>'
        '<span style="display:inline-flex;align-items:center;gap:3px;font-size:0.65rem;color:#9ca3af"><span style="width:10px;height:10px;border-radius:2px;background:#f59e0b;display:inline-block"></span>Moderate</span>'
        '<span style="display:inline-flex;align-items:center;gap:3px;font-size:0.65rem;color:#9ca3af"><span style="width:10px;height:10px;border-radius:2px;background:#ef4444;display:inline-block"></span>Over limit</span>'
        '<span style="display:inline-flex;align-items:center;gap:3px;font-size:0.65rem;color:#9ca3af"><span style="width:10px;height:10px;border-radius:2px;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);display:inline-block"></span>No data</span>'
        '</div></div>'
    )
    st.markdown(cal_html, unsafe_allow_html=True)

    # XP level bar
    _lvl_label = LEVEL_LABELS[min(level, len(LEVEL_LABELS) - 1)]
    st.markdown(f"""
    <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(124,58,237,0.25);
                border-radius:10px;padding:10px 14px;margin-top:8px">
      <div style="display:flex;justify-content:space-between;margin-bottom:5px">
        <span style="color:#a78bfa;font-size:0.78rem;font-weight:700">Lvl {level} &mdash; {_lvl_label}</span>
        <span style="color:#6b7280;font-size:0.72rem">{xp_in_level}/{XP_PER_LEVEL} XP to Lvl {level+1}</span>
      </div>
      <div class="xp-bar-bg"><div class="xp-bar-fill" style="width:{xp_pct}%"></div></div>
      <div style="margin-top:6px;font-size:0.7rem;color:#6b7280">
        Max streak: {_streak_max} days &nbsp;|&nbsp; Total XP: {xp} &nbsp;|&nbsp;
        +10/day under goal, +5 bonus if &gt;20% under
      </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ─── Sankey ───────────────────────────────────────────────────────────────────
st.markdown('<p class="section-header">// 🌊 App-Flow Sankey</p>', unsafe_allow_html=True)
st.caption("How your total 14-day time in each category flows into individual apps.")
st.plotly_chart(build_sankey(df), width="stretch")

st.markdown("---")

# ─── Achievement Badges ───────────────────────────────────────────────────────
st.markdown('<p class="section-header">// 🏆 Achievement Badges</p>', unsafe_allow_html=True)
badges = compute_badges(df, goal, _streak_max, xp, compute_daily_totals, compute_life_score, get_day_df)
badge_cols = st.columns(4)
for i, b in enumerate(badges):
    with badge_cols[i % 4]:
        opacity = "1" if b["unlocked"] else "0.35"
        glow    = "0 0 14px rgba(167,139,250,0.5)" if b["unlocked"] else "none"
        st.markdown(f"""
        <div style="text-align:center;padding:14px 8px;border-radius:12px;margin-bottom:10px;
                    background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);
                    opacity:{opacity};box-shadow:{glow}">
          <div style="font-size:1.8rem">{b['emoji'] if b['unlocked'] else '🔒'}</div>
          <div style="font-size:0.78rem;font-weight:700;color:white;margin-top:4px">{b['name']}</div>
          <div style="font-size:0.65rem;color:#9ca3af;margin-top:2px">{b['desc']}</div>
        </div>
        """, unsafe_allow_html=True)
st.caption(f"{sum(1 for b in badges if b['unlocked'])}/{len(badges)} badges unlocked.")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — VOICE JOURNAL + AI COACHING
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown('<p class="section-header">// 🤖 AI Coaching — Powered by Gemini</p>',
            unsafe_allow_html=True)

coach_col, = st.columns([1])

with coach_col:
    # ── Voice Journal (Innovation Deliverable) ─────────────────────────────────
    st.markdown('<div class="voice-card">', unsafe_allow_html=True)
    st.markdown("**🎙️ Voice Journal**")
    st.caption("Record a quick note: Why were you on your phone today?")

    voice_transcript = st.session_state.get("voice_transcript", "")

    try:
        audio_input = st.audio_input("Record voice note", key="voice_journal", label_visibility="collapsed")
        if audio_input:
            try:
                import speech_recognition as sr
                recognizer = sr.Recognizer()
                with sr.AudioFile(audio_input) as source:
                    audio_data = recognizer.record(source)
                voice_transcript = recognizer.recognize_google(audio_data)
                st.session_state["voice_transcript"] = voice_transcript
                st.success(f"✅ Transcript: *\"{voice_transcript}\"*")
            except Exception as _sr_exc:
                st.warning(f"⚠️ Transcription failed ({_sr_exc}). Coaching will use data only.")
                voice_transcript = ""
    except AttributeError:
        # Streamlit version < 1.37 doesn't have st.audio_input
        st.info("🎙️ Voice journal requires Streamlit ≥ 1.37. Update to enable.")

    if voice_transcript:
        st.caption(f"📝 Voice context will be included in coaching: *\"{voice_transcript[:80]}{'…' if len(voice_transcript)>80 else ''}\"*")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Coaching trigger (from sidebar st.form) ────────────────────────────────
    if coach_submitted:
        with st.spinner("Consulting your coach…"):
            coaching_text, severity, ai_status = get_coaching(
                selected_date, day_df, personality, goal, voice_transcript
            )
            st.session_state["last_coaching"] = coaching_text
            st.session_state["last_severity"] = severity
            st.session_state["ai_status"]      = ai_status
            st.rerun()

    if st.session_state["last_coaching"]:
        sev = st.session_state["last_severity"]
        txt = st.session_state["last_coaching"]
        status_icon = {
            "live":    "🟢 Live AI response",
            "cached":  "🟡 Cached response",
            "offline": "🔴 Offline fallback",
        }.get(st.session_state["ai_status"], "")
        st.caption(status_icon)
        if sev == "severe":
            st.warning(txt, icon="🚨")
        else:
            st.info(txt, icon="✅" if sev == "good" else "⚠️")


st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# PDF & WRAPPED CARD DOWNLOADS
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown('<p class="section-header">// 📄 Weekly Roast Report (PDF)</p>',
            unsafe_allow_html=True)

coaching_for_pdf = st.session_state["last_coaching"] or OFFLINE_TEMPLATES["moderate"]
pdf_bytes = generate_pdf(df, personality, coaching_for_pdf, all_dates, compute_daily_totals)
if pdf_bytes:
    st.download_button(
        label="⬇️ Download My Performance Review",
        data=pdf_bytes,
        file_name=f"LifeOS_Review_{datetime.now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf",
        width="stretch",
        key="pdf_download",
    )
else:
    st.warning("PDF could not be generated. See error above.")

st.markdown("---")

# ─── Life-OS Wrapped Card (PNG) ───────────────────────────────────────────────
st.markdown('<p class="section-header">// 🎁 Life-OS Wrapped</p>', unsafe_allow_html=True)

_avg_ls = int(sum(
    compute_life_score(get_day_df(df, d), int(t), goal)
    for d, t in compute_daily_totals(df).items()
) / max(1, len(all_dates)))
try:
    wrapped_png = generate_wrapped_card(df, goal, _avg_ls, compute_daily_totals)
    st.download_button(
        label="🎁 Download My Life-OS Wrapped Card",
        data=wrapped_png,
        file_name=f"LifeOS_Wrapped_{datetime.now().strftime('%Y%m%d')}.png",
        mime="image/png",
        width="stretch",
        key="wrapped_download",
    )
except Exception as _wrap_exc:
    st.error(f"Wrapped card generation failed: {_wrap_exc}")

st.markdown("---")

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown(
    '<p style="text-align:center;color:#4b5563;font-size:0.75rem;font-family:monospace">'
    '© Life-OS 2026 | Built with Streamlit + Gemini | Your data stays local</p>',
    unsafe_allow_html=True,
)
