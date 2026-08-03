"""
╔══════════════════════════════════════════════════════════╗
║             LIFE-OS  —  Productivity Command Center      ║
║         Powered by Streamlit + Gemini AI + Pure 🔥       ║
╚══════════════════════════════════════════════════════════╝

Phases:
  1  Data Ingestion
  2  Command Center UI  (KPI Row + Charts)
  3  AI Integration     (Gemini + cache + offline fallback)
  4  Accountability Link (query params)
  +  Custom Features    (Time Machine, Equivalents, Pyramid,
                         Streak/XP, Roast PDF, Status Badge)
"""

import hashlib
import json
import os
import textwrap
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

# ─── Load environment ──────────────────────────────────────────────────────────
load_dotenv()

# ─── CONSTANTS & MAGIC NUMBERS ────────────────────────────────────────────────
CSV_PATH           = Path(__file__).parent / "screentime.csv"
CACHE_PATH         = Path(__file__).parent / "coaching_cache.json"

# Real-world equivalents conversion constants
WORDS_PER_MIN      = 250          # avg reading speed (words/min)
WORDS_PER_BOOK     = 80_000       # avg book length (words)
WALK_KM_PER_HR     = 5            # avg walking speed (km/h)
PUSHUPS_PER_MIN    = 12           # avg push-ups per minute
SLEEP_EQUIV_RATIO  = 0.85         # screen min → restorative sleep min equivalent

# XP / Streak constants
XP_PER_DAY_UNDER   = 10
XP_BONUS_THRESHOLD = 0.20         # >20% under goal → bonus XP
XP_BONUS           = 5
XP_PER_LEVEL       = 50

# Severity thresholds (minutes over goal)
SEVERE_THRESHOLD   = 60           # >60 min over goal → severe
MODERATE_THRESHOLD = 0            # 0-60 min over goal → moderate

# Color palette
COLOR_JUNK         = "#FF4B4B"
COLOR_PROTEIN      = "#FFA500"
COLOR_GRAINS       = "#00C49A"
COLOR_GOAL_LINE    = "#FFD700"
COLOR_ACCENT       = "#7C3AED"

# Coach personalities ─ each injects distinct prose into the ONE shared prompt template
PERSONALITIES = {
    "🧘 Zen Monk": (
        "You are a calm, reflective Zen mindfulness coach. "
        "Speak in measured, poetic sentences. Use metaphors of water, nature, and impermanence. "
        "Acknowledge the user's struggle with compassion before suggesting a mindful alternative. "
        "Never lecture; invite. End with a short koan or reflective question."
    ),
    "🪖 Drill Sergeant": (
        "You are a blunt, high-intensity military Drill Sergeant productivity coach. "
        "Use short, punchy sentences. Employ military metaphors (missions, AWOL, deployment). "
        "Do NOT sugarcoat anything. Call out wasted time as mission failure. "
        "Issue direct orders for improvement, no room for excuses."
    ),
    "😂 Sarcastic Bestie": (
        "You are a witty, teasing, casual Gen-Z best friend who is also low-key a productivity nerd. "
        "Use irony, sarcasm, internet slang (no filter). "
        "Roast the user's choices hilariously but then pivot to a genuinely helpful suggestion. "
        "Feel free to use emojis and dramatic language. Keep it chaotic but real."
    ),
}

# Offline fallback coaching templates keyed by severity
OFFLINE_TEMPLATES = {
    "good": (
        "✅ **Solid day!** You stayed within your goal — that kind of discipline compounds over time. "
        "Keep building on your Education and Coding time; even 15 extra minutes of focused coding "
        "daily beats 3 hours of passive scrolling every week of the year."
    ),
    "moderate": (
        "⚠️ **Borderline day.** You're nudging over your screen-time goal. "
        "Your Social Media + Entertainment time is creeping up — consider a 20-minute \"scroll tax\": "
        "before each social session, complete one coding task or read one article. "
        "Small friction = big behaviour change."
    ),
    "severe": (
        "🚨 **Intervention mode.** You're significantly over your daily goal. "
        "The hours lost to entertainment and social media today could have been: "
        "a 10 km walk, 3 chapters of a book, or a side project feature shipped. "
        "Tomorrow: set your phone to grayscale and put it in another room during your first "
        "2 work hours. Data doesn't lie — your future self is watching."
    ),
}

# ─── PAGE CONFIG ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Life-OS | Productivity Command Center",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── GLOBAL CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&family=JetBrains+Mono:wght@400;700&display=swap');

  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  /* Dark gradient background */
  .stApp { background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%); }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background: rgba(15,12,41,0.95);
    border-right: 1px solid rgba(124,58,237,0.3);
  }

  /* Metric cards */
  [data-testid="metric-container"] {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(124,58,237,0.4);
    border-radius: 12px;
    padding: 16px !important;
    backdrop-filter: blur(8px);
  }

  /* Headings */
  h1, h2, h3 { color: #ffffff !important; }
  h1 { font-weight: 900 !important; }

  /* Buttons */
  .stButton > button {
    background: linear-gradient(90deg, #7C3AED, #EC4899);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 700;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
  }
  .stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 24px rgba(124,58,237,0.5);
  }

  /* Download button */
  .stDownloadButton > button {
    background: linear-gradient(90deg, #059669, #10b981);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 700;
  }

  /* Section divider */
  .section-header {
    font-family: 'JetBrains Mono', monospace;
    color: #a78bfa;
    font-size: 0.75rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    border-bottom: 1px solid rgba(167,139,250,0.3);
    padding-bottom: 6px;
    margin-bottom: 16px;
  }

  /* Badge / pill */
  .badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
  }
  .badge-live     { background:#064e3b; color:#6ee7b7; border:1px solid #059669; }
  .badge-cached   { background:#78350f; color:#fcd34d; border:1px solid #d97706; }
  .badge-offline  { background:#7f1d1d; color:#fca5a5; border:1px solid #dc2626; }

  /* Pyramid block — block-level so content determines height */
  .pyramid-block {
    border-radius: 10px;
    display: block;
    height: auto;
    font-weight: 700;
    font-size: 0.88rem;
    color: white;
    padding: 12px 16px;
    margin: 5px auto;
    text-align: center;
    line-height: 1.6;
    box-shadow: 0 4px 16px rgba(0,0,0,0.25);
    transition: transform 0.2s ease;
  }
  .pyramid-block:hover { transform: scale(1.02); }

  /* XP bar */
  .xp-bar-bg {
    background: rgba(255,255,255,0.1);
    border-radius: 999px;
    height: 10px;
    overflow: hidden;
    margin-top: 6px;
  }
  .xp-bar-fill {
    height: 100%;
    border-radius: 999px;
    background: linear-gradient(90deg, #7C3AED, #EC4899);
    transition: width 0.4s ease;
  }

  /* Link / copy input */
  .copy-box {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(124,58,237,0.4);
    border-radius: 8px;
    padding: 8px 12px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: #d8b4fe;
    word-break: break-all;
  }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — DATA INGESTION
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data
def load_data() -> pd.DataFrame:
    """Load and parse the screen time CSV."""
    df = pd.read_csv(CSV_PATH)
    df["Date"] = pd.to_datetime(df["Date"])
    return df


df = load_data()
all_dates = sorted(df["Date"].dt.date.unique())

# ─── Streak & XP initialisation (session state) ───────────────────────────────
if "xp" not in st.session_state:
    st.session_state["xp"] = 0
    st.session_state["streak"] = 0
    st.session_state["xp_computed"] = False

# ─── AI status tracking ───────────────────────────────────────────────────────
if "ai_status" not in st.session_state:
    st.session_state["ai_status"] = None          # None | "live" | "cached" | "offline"
if "last_coaching" not in st.session_state:
    st.session_state["last_coaching"] = None
if "last_severity" not in st.session_state:
    st.session_state["last_severity"] = None


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def compute_daily_totals(dataframe: pd.DataFrame) -> pd.Series:
    """Return total minutes per date across the full dataset."""
    return dataframe.groupby("Date")["Minutes_Used"].sum()


def get_day_df(dataframe: pd.DataFrame, chosen_date) -> pd.DataFrame:
    """Filter dataframe to a single date."""
    return dataframe[dataframe["Date"].dt.date == chosen_date]


def day_category_summary(day_df: pd.DataFrame) -> str:
    """Aggregate by category → clean string for Gemini (never raw DataFrame)."""
    summary = day_df.groupby("Category")["Minutes_Used"].sum()
    return summary.to_string()


def compute_severity(today_total: int, goal: int) -> str:
    delta = today_total - goal
    if delta > SEVERE_THRESHOLD:
        return "severe"
    elif delta > MODERATE_THRESHOLD:
        return "moderate"
    return "good"


def compute_life_score(day_df: pd.DataFrame, today_total: int, goal: int) -> int:
    """
    Composite 0-100 score = 60% category balance (productive vs junk) + 40% goal adherence.
    Not just 'less time = better' — rewards a healthy MIX, matching the Digital Diet Pyramid idea.
    """
    cat = day_df.groupby("Category")["Minutes_Used"].sum()
    productive = int(cat.get("Education", 0) + cat.get("Coding", 0))
    junk = int(cat.get("Social Media", 0) + cat.get("Entertainment", 0))

    balance_score = 50 + 50 * (productive - junk) / (productive + junk + 1)

    goal_ratio = (today_total / goal) if goal else 1.0
    goal_score = 100 - max(0.0, goal_ratio - 1) * 150   # steep penalty once over goal
    goal_score = max(0, min(100, goal_score))

    life_score = 0.6 * balance_score + 0.4 * goal_score
    return int(max(0, min(100, round(life_score))))


def compute_badges(dataframe: pd.DataFrame, goal: int, streak_max: int, total_xp: int) -> list[dict]:
    """
    Rule-based achievement badges — purely local, computed from the full 14-day dataset.
    Returns a list of {emoji, name, desc, unlocked}.
    """
    cat_by_day = dataframe.groupby([dataframe["Date"].dt.date, "Category"])["Minutes_Used"].sum()
    totals_by_day = compute_daily_totals(dataframe)
    days_under_goal = int((totals_by_day <= goal).sum())
    total_days = len(totals_by_day)

    max_coding_day = int(cat_by_day.xs("Coding", level="Category").max()) if "Coding" in cat_by_day.index.get_level_values("Category") else 0
    max_education_day = int(cat_by_day.xs("Education", level="Category").max()) if "Education" in cat_by_day.index.get_level_values("Category") else 0
    max_social_day = int(cat_by_day.xs("Social Media", level="Category").max()) if "Social Media" in cat_by_day.index.get_level_values("Category") else 0

    # Comeback Kid: a severe day (>goal by SEVERE_THRESHOLD) immediately followed by a good day
    sorted_totals = totals_by_day.sort_index()
    comeback = False
    prev = None
    for _d, _t in sorted_totals.items():
        if prev is not None and (prev - goal) > SEVERE_THRESHOLD and _t <= goal:
            comeback = True
            break
        prev = _t

    avg_life_score = int(sum(
        compute_life_score(get_day_df(dataframe, d), int(t), goal)
        for d, t in sorted_totals.items()
    ) / max(1, total_days))

    return [
        {"emoji": "💻", "name": "Coding Beast", "desc": "90+ min coding in one day",
         "unlocked": max_coding_day >= 90},
        {"emoji": "📚", "name": "Bookworm", "desc": "60+ min education in one day",
         "unlocked": max_education_day >= 60},
        {"emoji": "🎯", "name": "Goal Crusher", "desc": f"Under goal on {max(1, total_days - 4)}+ of {total_days} days",
         "unlocked": days_under_goal >= max(1, total_days - 4)},
        {"emoji": "🔥", "name": "Streak Master", "desc": "5+ day streak under goal",
         "unlocked": streak_max >= 5},
        {"emoji": "⚖️", "name": "Balanced Human", "desc": "Avg Life Score 70+",
         "unlocked": avg_life_score >= 70},
        {"emoji": "🌱", "name": "Comeback Kid", "desc": "Bounced back the day after a severe day",
         "unlocked": comeback},
        {"emoji": "📱", "name": "Doomscroll Champion", "desc": "150+ min Social Media in one day",
         "unlocked": max_social_day >= 150},
        {"emoji": "⚡", "name": "XP Grinder", "desc": "100+ total XP earned",
         "unlocked": total_xp >= 100},
    ]


def generate_wrapped_card(dataframe: pd.DataFrame, goal: int, avg_life_score: int) -> bytes:
    """Generate a shareable 'Life-OS Wrapped' summary card (PNG) using matplotlib — no API, no external fonts."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    totals = compute_daily_totals(dataframe)
    total_hours = totals.sum() / 60
    top_app = dataframe.groupby("App_Name")["Minutes_Used"].sum().idxmax()
    top_cat = dataframe.groupby("Category")["Minutes_Used"].sum().idxmax()
    best_day = totals.idxmin().strftime("%b %d")
    worst_day = totals.idxmax().strftime("%b %d")
    days_under_goal = int((totals <= goal).sum())

    fig, ax = plt.subplots(figsize=(6, 10), dpi=150)
    fig.patch.set_facecolor("#0f0c29")
    ax.set_facecolor("#0f0c29")
    ax.axis("off")

    grad = mpatches.FancyBboxPatch((0.03, 0.03), 0.94, 0.94, boxstyle="round,pad=0.01",
                                    linewidth=2, edgecolor="#a78bfa", facecolor="#1a1633",
                                    transform=ax.transAxes)
    ax.add_patch(grad)

    ax.text(0.5, 0.93, "LIFE-OS WRAPPED", ha="center", fontsize=24, fontweight="bold",
            color="#ec4899", transform=ax.transAxes)
    ax.text(0.5, 0.89, "14-Day Screen Time Recap", ha="center", fontsize=11,
            color="#9ca3af", transform=ax.transAxes)

    stats = [
        (f"{total_hours:.1f} hrs", "Total Screen Time"),
        (top_app, "Most Used App"),
        (top_cat, "Top Category"),
        (f"{avg_life_score}/100", "Avg Life Score"),
        (f"{days_under_goal}/{len(totals)} days", "Under Goal"),
        (f"{best_day} → {worst_day}", "Best → Worst Day"),
    ]
    y = 0.76
    for value, label in stats:
        ax.text(0.5, y, str(value), ha="center", fontsize=20, fontweight="bold",
                color="white", transform=ax.transAxes)
        ax.text(0.5, y - 0.035, label.upper(), ha="center", fontsize=9,
                color="#a78bfa", transform=ax.transAxes)
        y -= 0.115

    ax.text(0.5, 0.05, "Built with Life-OS", ha="center", fontsize=9,
            color="#6b7280", transform=ax.transAxes)

    buf = BytesIO()
    fig.savefig(buf, format="png", facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


def load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def save_cache(cache: dict):
    CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


def make_cache_key(chosen_date, day_df: pd.DataFrame, personality: str) -> str:
    cat_str = day_category_summary(day_df)
    raw = f"{chosen_date}|{cat_str}|{personality}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def build_prompt(cat_summary: str, personality: str, goal: int) -> str:
    persona_desc = PERSONALITIES[personality]
    return textwrap.dedent(f"""
        You are a personal productivity coach with the following personality:
        {persona_desc}

        The user's DAILY SCREEN TIME GOAL is {goal} minutes.

        Here is today's screen time broken down by category (in minutes):
        {cat_summary}

        Your task: Provide a structured coaching response as a SINGLE valid JSON object.
        Do NOT wrap it in markdown code fences. Return ONLY the JSON.

        JSON schema:
        {{
          "coaching_text": "<your full coaching response here — 3-5 sentences>",
          "severity": "<one of: good | moderate | severe>"
        }}

        Rules you MUST follow:
        - NEVER give generic advice like "use your phone less".
        - ALWAYS tie suggestions to the SPECIFIC CATEGORIES shown in the data above.
        - Use concrete real-world equivalents (e.g. "those 90 minutes on Social Media could have been a full gym session + cooking a healthy meal").
        - Match your tone exactly to the personality description above.
        - severity must reflect whether total usage is good, moderate, or severe relative to the {goal}-minute goal.
    """).strip()


def call_gemini(prompt: str, api_key: str) -> dict:
    """Call Gemini API and return parsed JSON coaching response."""
    from google import genai  # lazy import so app loads without the key
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    raw_text = response.text.strip()
    # Strip markdown fences if model wraps in them
    if raw_text.startswith("```"):
        raw_text = "\n".join(raw_text.split("\n")[1:])
        raw_text = raw_text.rsplit("```", 1)[0].strip()
    return json.loads(raw_text)


def get_coaching(chosen_date, day_df: pd.DataFrame, personality: str, goal: int) -> tuple[str, str, str]:
    """
    Returns (coaching_text, severity, status)
    status: "live" | "cached" | "offline"
    """
    api_key = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", "")
    cat_summary = day_category_summary(day_df)
    cache_key = make_cache_key(chosen_date, day_df, personality)
    cache = load_cache()

    # Check cache first
    if cache_key in cache:
        entry = cache[cache_key]
        return entry["coaching_text"], entry["severity"], "cached"

    if not api_key or api_key == "your_key_here":
        severity = compute_severity(int(day_df["Minutes_Used"].sum()), goal)
        return OFFLINE_TEMPLATES[severity], severity, "offline"

    try:
        prompt = build_prompt(cat_summary, personality, goal)
        result = call_gemini(prompt, api_key)
        coaching_text = result.get("coaching_text", "")
        severity      = result.get("severity", compute_severity(int(day_df["Minutes_Used"].sum()), goal))
        # Save to cache
        cache[cache_key] = {"coaching_text": coaching_text, "severity": severity}
        save_cache(cache)
        return coaching_text, severity, "live"
    except Exception as exc:
        severity = compute_severity(int(day_df["Minutes_Used"].sum()), goal)
        fallback = OFFLINE_TEMPLATES[severity] + f"\n\n*(Offline — API error: {exc})*"
        return fallback, severity, "offline"


def compute_streak_xp(dataframe: pd.DataFrame, goal: int):
    """Compute streak and XP from the dataset dates in order."""
    totals = compute_daily_totals(dataframe)
    streak = 0
    xp = 0
    for _date, total in totals.sort_index().items():
        if total <= goal:
            streak += 1
            xp += XP_PER_DAY_UNDER
            if (goal - total) / goal >= XP_BONUS_THRESHOLD:
                xp += XP_BONUS
        else:
            streak = 0
    return streak, xp


def generate_pdf(df_full: pd.DataFrame, personality: str, coaching_text: str) -> bytes:
    """Generate a satirical one-page PDF performance review using fpdf2."""
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    totals = compute_daily_totals(df_full)
    total_all = int(totals.sum())
    worst_day  = totals.idxmax().strftime("%Y-%m-%d")
    best_day   = totals.idxmin().strftime("%Y-%m-%d")
    top_cat    = df_full.groupby("Category")["Minutes_Used"].sum().idxmax()
    worst_mins = int(totals.max())
    best_mins  = int(totals.min())

    # Sanitise coaching_text for latin-1
    safe_coaching = coaching_text.encode("latin-1", errors="replace").decode("latin-1")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(20, 20, 20)

    # ── Letterhead ──
    pdf.set_fill_color(15, 12, 41)
    pdf.rect(0, 0, 210, 40, "F")
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(0, 8)
    pdf.cell(210, 10, "LIFE-OS PERFORMANCE MANAGEMENT DIVISION", align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_xy(0, 22)
    pdf.cell(210, 6, "Internal Memo - STRICTLY CONFIDENTIAL - Digital Productivity Bureau", align="C")
    pdf.set_xy(0, 30)
    # Sanitise personality name (strip emojis that latin-1 can't encode)
    safe_personality = personality.encode("latin-1", errors="replace").decode("latin-1")
    pdf.cell(210, 6, f"Review Period: {all_dates[0]}  to  {all_dates[-1]}  |  Coach: {safe_personality}", align="C")

    # ── Body ──
    pdf.set_text_color(20, 20, 40)
    pdf.set_xy(20, 50)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "QUARTERLY PERFORMANCE REVIEW", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 11)
    pdf.set_x(20)
    # Strip ALL non-latin-1 chars (emojis, etc.) from every PDF string
    def _safe(text: str) -> str:
        return text.encode("latin-1", errors="replace").decode("latin-1")
    pdf.multi_cell(0, 7,
        _safe(
            f"Subject: Screen Time Performance Review\n"
            f"Reviewed by: Life-OS AI Coaching Engine ({personality})\n"
            f"Date of Issue: {datetime.now().strftime('%Y-%m-%d')}\n"
        )
    )

    # KPIs table
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_x(20)
    pdf.cell(0, 8, "KEY PERFORMANCE INDICATORS (14-Day Period)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)

    rows = [
        ("Total Screen Time", f"{total_all:,} minutes  ({total_all/60:.1f} hours)"),
        ("Worst Offence Day", f"{worst_day}  -  {worst_mins} minutes"),
        ("Best Recovery Day", f"{best_day}  -  {best_mins} minutes"),
        ("Top Category",      top_cat),
    ]
    for label, value in rows:
        pdf.set_x(20)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(60, 7, label + ":", border="B")
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 7, value, border="B", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # AI Coaching section
    pdf.ln(6)
    pdf.set_x(20)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "COACH'S ASSESSMENT", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_x(20)
    pdf.multi_cell(0, 6, safe_coaching)

    # Footer
    pdf.set_y(-25)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(100, 100, 120)
    pdf.cell(0, 6,
        "Life-OS Performance Management Division  |  This document is auto-generated for "
        "accountability purposes only. No screens were harmed in its production.",
        align="C"
    )

    return pdf.output()


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🧠 **Life-OS**")
    st.markdown('<p class="section-header">// Command Controls</p>', unsafe_allow_html=True)

    selected_date = st.selectbox(
        "📅 Select Day",
        options=all_dates,
        index=len(all_dates) - 1,
        format_func=lambda d: d.strftime("%A, %b %d"),
        key="selected_date_sb",
    )

    goal = st.slider(
        "🎯 Daily Goal (minutes)",
        min_value=60, max_value=600, value=300, step=10,
        key="goal_slider",
    )

    st.markdown("---")
    st.markdown('<p class="section-header">// Coach Personality</p>', unsafe_allow_html=True)
    personality = st.radio(
        "Choose your coach:",
        options=list(PERSONALITIES.keys()),
        key="personality_radio",
        label_visibility="collapsed",
    )

    # AI Status Badge
    st.markdown("---")
    st.markdown('<p class="section-header">// System Status</p>', unsafe_allow_html=True)
    status_val = st.session_state.get("ai_status")
    if status_val == "live":
        st.markdown('<span class="badge badge-live">🟢 Live AI</span>', unsafe_allow_html=True)
    elif status_val == "cached":
        st.markdown('<span class="badge badge-cached">🟡 Cached Response</span>', unsafe_allow_html=True)
    elif status_val == "offline":
        st.markdown('<span class="badge badge-offline">🔴 Offline Mode</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span style="color:#6b7280;font-size:0.8rem;">⬜ Awaiting coaching call</span>',
                    unsafe_allow_html=True)

    # Accountability link
    st.markdown("---")
    st.markdown('<p class="section-header">// Accountability Link</p>', unsafe_allow_html=True)

    day_df_link  = get_day_df(df, selected_date)
    today_total_link = int(day_df_link["Minutes_Used"].sum())
    # Write query params
    st.query_params["date"]  = str(selected_date)
    st.query_params["total"] = str(today_total_link)
    base_url = "https://your-app.streamlit.app"  # customise for deployment
    share_url = f"{base_url}/?date={selected_date}&total={today_total_link}"
    st.markdown(
        f'<div class="copy-box">📎 {share_url}</div>',
        unsafe_allow_html=True,
    )
    st.caption("Copy the URL from your browser's address bar to share.")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — COMMAND CENTER UI
# ═══════════════════════════════════════════════════════════════════════════════

# ── App Header ──
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

# --- PHASE 2: KPI ROW ---
day_df = get_day_df(df, selected_date)
today_total = int(day_df["Minutes_Used"].sum())
most_used_app = day_df.loc[day_df["Minutes_Used"].idxmax(), "App_Name"] if not day_df.empty else "N/A"
delta_vs_goal = today_total - goal

# --- DYNAMIC BACKGROUND — changes based on screentime severity ---
_sev_now = compute_severity(today_total, goal)
_BG_CONFIGS = {
    "good": {
        "bg": "linear-gradient(135deg, #042a14 0%, #0d3b2e 45%, #063324 100%)",
        "sidebar": "rgba(4,42,20,0.97)",
        "border": "rgba(16,185,129,0.35)",
        "label": "🟢 Low Screen Time Day",
        "label_color": "#6ee7b7",
    },
    "moderate": {
        "bg": "linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%)",
        "sidebar": "rgba(15,12,41,0.97)",
        "border": "rgba(124,58,237,0.35)",
        "label": "🟡 Moderate Screen Time Day",
        "label_color": "#fcd34d",
    },
    "severe": {
        "bg": "linear-gradient(135deg, #1e0505 0%, #4a1010 45%, #2d0a0a 100%)",
        "sidebar": "rgba(30,5,5,0.97)",
        "border": "rgba(220,38,38,0.4)",
        "label": "🔴 High Screen Time Day",
        "label_color": "#fca5a5",
    },
}
_cfg = _BG_CONFIGS[_sev_now]
st.markdown(f"""
<style>
  .stApp {{
    background: {_cfg['bg']} !important;
    transition: background 0.8s ease;
  }}
  [data-testid="stSidebar"] {{
    background: {_cfg['sidebar']} !important;
    border-right: 1px solid {_cfg['border']} !important;
    transition: background 0.8s ease;
  }}
  /* Screentime status pill in main area */
  .st-severity-badge {{
    display: inline-block;
    padding: 4px 14px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 700;
    color: {_cfg['label_color']};
    border: 1px solid {_cfg['label_color']}40;
    background: {_cfg['label_color']}15;
    letter-spacing: 0.04em;
  }}
</style>
""", unsafe_allow_html=True)

# Severity badge — shows the dynamic background mode to the user
st.markdown(
    f'<p style="text-align:center;margin-bottom:16px">'
    f'<span class="st-severity-badge">{_cfg["label"]}</span></p>',
    unsafe_allow_html=True,
)

kpi1, kpi2, kpi3 = st.columns(3)
with kpi1:
    st.metric(
        label="📱 Total Screen Time",
        value=f"{today_total} min",
        help=f"{today_total/60:.1f} hours on {selected_date}",
    )
with kpi2:
    st.metric(
        label="🏆 Most Used App",
        value=most_used_app,
        help="App with highest minutes today",
    )
with kpi3:
    st.metric(
        label="⚡ vs Daily Goal",
        value=f"{abs(delta_vs_goal)} min {'over' if delta_vs_goal > 0 else 'under'}",
        delta=delta_vs_goal,
        delta_color="inverse",  # MANDATORY — over goal is bad, inverse = red
        help=f"Goal: {goal} min | Today: {today_total} min",
    )

st.markdown("---")

# ─── Feature: Life Score Gauge ─────────────────────────────────────────────
st.markdown('<p class="section-header">// 🎯 Life Score</p>', unsafe_allow_html=True)
life_score_today = compute_life_score(day_df, today_total, goal)
_ls_color = "#22c55e" if life_score_today >= 70 else ("#f59e0b" if life_score_today >= 40 else "#ef4444")

ls_fig = go.Figure(go.Indicator(
    mode="gauge+number",
    value=life_score_today,
    number={"suffix": " / 100", "font": {"color": "white", "size": 34}},
    gauge={
        "axis": {"range": [0, 100], "tickcolor": "#6b7280"},
        "bar": {"color": _ls_color},
        "bgcolor": "rgba(255,255,255,0.04)",
        "borderwidth": 0,
        "steps": [
            {"range": [0, 40], "color": "rgba(239,68,68,0.18)"},
            {"range": [40, 70], "color": "rgba(245,158,11,0.18)"},
            {"range": [70, 100], "color": "rgba(34,197,94,0.18)"},
        ],
    },
))
ls_fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#d1d5db"),
    height=220,
    margin=dict(l=20, r=20, t=10, b=0),
)
ls_col1, ls_col2 = st.columns([1, 1])
with ls_col1:
    st.plotly_chart(ls_fig, width="stretch")
with ls_col2:
    st.markdown(f"""
    <div style="padding-top:30px">
      <p style="color:#9ca3af;font-size:0.85rem;line-height:1.6">
        Life Score isn't just "less time = better" — it's <strong style="color:{_ls_color}">60% category
        balance</strong> (productive vs junk time) <strong>+ 40% goal adherence</strong>.<br><br>
        A day full of coding at 9 hours can score higher than a "short" day of pure doomscrolling.
      </p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# --- PHASE 2: TREND CHART ---
st.markdown('<p class="section-header">// 14-Day Screen Time Trend</p>', unsafe_allow_html=True)

daily_totals = compute_daily_totals(df).reset_index()
daily_totals.columns = ["Date", "Minutes"]

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=daily_totals["Date"],
    y=daily_totals["Minutes"],
    mode="lines+markers",
    name="Daily Screen Time",
    line=dict(color="#a78bfa", width=3),
    marker=dict(size=8, color="#ec4899"),
    fill="tozeroy",
    fillcolor="rgba(167,139,250,0.15)",
))
# Highlight selected day
selected_row = daily_totals[daily_totals["Date"].dt.date == selected_date]
if not selected_row.empty:
    fig.add_trace(go.Scatter(
        x=selected_row["Date"],
        y=selected_row["Minutes"],
        mode="markers",
        name="Selected Day",
        marker=dict(size=14, color=COLOR_ACCENT, symbol="star"),
    ))
# Goal line
fig.add_hline(
    y=goal,
    line_dash="dash",
    line_color=COLOR_GOAL_LINE,
    annotation_text=f"Goal: {goal} min",
    annotation_position="top right",
    annotation_font_color=COLOR_GOAL_LINE,
)
fig.update_layout(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#d1d5db"),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)", title="Minutes"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=0, r=0, t=30, b=0),
    height=320,
)
st.plotly_chart(fig, width="stretch")

st.markdown("---")

# ─── Feature: Compare Two Days Mode ────────────────────────────────────────
st.markdown('<p class="section-header">// ⚔️ Compare Two Days</p>', unsafe_allow_html=True)

cmp_c1, cmp_c2 = st.columns(2)
_default_b_idx = max(0, len(all_dates) - 2)
with cmp_c1:
    day_a = st.selectbox("Day A", options=all_dates, index=len(all_dates) - 1,
                          format_func=lambda d: d.strftime("%A, %b %d"), key="cmp_day_a")
with cmp_c2:
    day_b = st.selectbox("Day B", options=all_dates, index=_default_b_idx,
                          format_func=lambda d: d.strftime("%A, %b %d"), key="cmp_day_b")

df_a = get_day_df(df, day_a).groupby("Category")["Minutes_Used"].sum()
df_b = get_day_df(df, day_b).groupby("Category")["Minutes_Used"].sum()
all_cats = sorted(set(df_a.index) | set(df_b.index))

cmp_fig = go.Figure()
cmp_fig.add_trace(go.Bar(
    x=all_cats, y=[int(df_a.get(c, 0)) for c in all_cats],
    name=day_a.strftime("%b %d"), marker_color="#a78bfa",
))
cmp_fig.add_trace(go.Bar(
    x=all_cats, y=[int(df_b.get(c, 0)) for c in all_cats],
    name=day_b.strftime("%b %d"), marker_color="#ec4899",
))
cmp_fig.update_layout(
    barmode="group",
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#d1d5db"),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)", title="Minutes"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(l=0, r=0, t=30, b=0),
    height=300,
)
st.plotly_chart(cmp_fig, width="stretch")

total_a, total_b = int(df_a.sum()), int(df_b.sum())
cmp_diff = total_a - total_b
st.caption(
    f"{day_a.strftime('%b %d')}: **{total_a} min** vs {day_b.strftime('%b %d')}: **{total_b} min** — "
    f"{'Day A' if cmp_diff > 0 else 'Day B'} used {abs(cmp_diff)} more minutes overall."
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
        "Reduce screen time by:",
        min_value=5, max_value=90, value=30, step=5,
        format="%d%%",
        key="time_machine_slider",
    )
    hours_saved_per_year = (today_total * (reduce_pct / 100) * 365) / 60
    days_saved = hours_saved_per_year / 24
    waking_days = hours_saved_per_year / 16  # 16 active waking hours

    st.markdown(f"""
    <div style="background:rgba(124,58,237,0.15);border:1px solid rgba(124,58,237,0.4);
                border-radius:12px;padding:16px;margin-top:8px;">
      <p style="color:#a78bfa;font-size:0.8rem;margin:0 0 6px 0;font-weight:600;">YEARLY PROJECTION</p>
      <p style="color:white;font-size:1.1rem;font-weight:700;margin:0">
        Agar tum apna screen time {reduce_pct}% kam karo,<br>
        saal me tumhe <span style="color:#ec4899">~{days_saved:.1f} extra din</span> milenge<br>
        <span style="color:#fbbf24;font-size:0.95rem">({waking_days:.1f} active waking hours/day basis)</span>
      </p>
    </div>
    """, unsafe_allow_html=True)

# ─── Feature 2: Real-World Equivalents (Gauge Charts) ───────────────────────
with feat_col2:
    st.markdown('<p class="section-header">// 📚 Real-World Equivalents</p>', unsafe_allow_html=True)
    junk_mins = int(day_df[day_df["Category"].isin(["Social Media", "Entertainment"])]["Minutes_Used"].sum())
    books_equiv   = junk_mins / (WORDS_PER_BOOK / WORDS_PER_MIN)
    km_equiv      = (junk_mins / 60) * WALK_KM_PER_HR
    pushups_equiv = junk_mins * PUSHUPS_PER_MIN
    sleep_equiv   = junk_mins * SLEEP_EQUIV_RATIO

    # Benchmark maxes for gauge reference (what a "great" day looks like)
    BOOK_MAX    = 5.0    # 5 books max reference
    KM_MAX      = 30.0   # 30 km walk max reference
    PU_MAX      = 5000   # 5000 push-ups max reference
    SLEEP_MAX   = 480    # 8 hours max reference

    def _gauge(value, max_val, label, unit, color):
        pct = min(value / max_val, 1.0)
        bar_w = int(pct * 100)
        return f"""
        <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);
                    border-radius:12px;padding:12px 14px;margin-bottom:10px">
          <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px">
            <span style="color:#9ca3af;font-size:0.75rem;font-weight:600">{label}</span>
            <span style="color:white;font-size:1.05rem;font-weight:800">{unit}</span>
          </div>
          <div style="background:rgba(255,255,255,0.08);border-radius:999px;height:8px;overflow:hidden">
            <div style="width:{bar_w}%;height:100%;border-radius:999px;
                        background:linear-gradient(90deg,{color}99,{color});transition:width 0.5s ease"></div>
          </div>
          <div style="text-align:right;color:#6b7280;font-size:0.65rem;margin-top:3px">{pct*100:.0f}% of {max_val} {label.split()[-1] if ' ' in label else ''} ref</div>
        </div>"""

    gauges_html = (
        _gauge(books_equiv,   BOOK_MAX,  "📖 Books read",      f"{books_equiv:.2f} books",   "#818cf8") +
        _gauge(km_equiv,      KM_MAX,    "🚶 Walking km",       f"{km_equiv:.1f} km",          "#34d399") +
        _gauge(pushups_equiv, PU_MAX,    "💪 Push-ups",         f"{int(pushups_equiv):,} reps","#f472b6") +
        _gauge(sleep_equiv,   SLEEP_MAX, "😴 Sleep recovered",  f"{sleep_equiv:.0f} min",      "#fbbf24")
    )
    st.markdown(gauges_html, unsafe_allow_html=True)
    st.caption(f"Based on {junk_mins} min of Social + Entertainment today")

st.markdown("---")

feat_col3, feat_col4 = st.columns([1, 1], gap="large")

# ─── Feature 3: Digital Diet Pyramid ─────────────────────────────────────────
with feat_col3:
    st.markdown('<p class="section-header">// 🍕 Digital Diet Pyramid</p>', unsafe_allow_html=True)
    cat_totals = day_df.groupby("Category")["Minutes_Used"].sum()

    junk_mins_pyr  = int(cat_totals.get("Social Media", 0) + cat_totals.get("Entertainment", 0))
    protein_mins   = int(cat_totals.get("Communication", 0))
    grains_mins    = int(cat_totals.get("Education", 0) + cat_totals.get("Coding", 0))
    pyramid_total  = junk_mins_pyr + protein_mins + grains_mins or 1

    def pct_width(val): return max(20, int((val / pyramid_total) * 100))

    # Pyramid widths — top is narrowest, base is widest (true pyramid shape)
    junk_w   = max(30, int((junk_mins_pyr  / pyramid_total) * 75) + 10)   # 30–85%
    prot_w   = max(45, int((protein_mins   / pyramid_total) * 75) + 20)   # 45–95%
    grain_w  = 100                                                          # always full width

    st.markdown(f"""
    <div style="display:flex;flex-direction:column;align-items:center;gap:8px;padding:12px 4px">

      <!-- JUNK — top, smallest -->
      <div class="pyramid-block"
           style="background:linear-gradient(135deg,{COLOR_JUNK},{COLOR_JUNK}cc);
                  width:{junk_w}%;">
        <div style="font-size:1.2rem">🍬</div>
        <div style="font-size:0.9rem;font-weight:800;letter-spacing:0.03em">JUNK</div>
        <div style="font-size:0.75rem;opacity:0.85">Social + Entertainment</div>
        <div style="font-size:1.1rem;font-weight:900;margin-top:2px">{junk_mins_pyr} min</div>
      </div>

      <!-- PROTEIN — middle -->
      <div class="pyramid-block"
           style="background:linear-gradient(135deg,{COLOR_PROTEIN},{COLOR_PROTEIN}cc);
                  width:{prot_w}%;">
        <div style="font-size:1.2rem">🥩</div>
        <div style="font-size:0.9rem;font-weight:800;letter-spacing:0.03em">PROTEIN</div>
        <div style="font-size:0.75rem;opacity:0.85">Communication</div>
        <div style="font-size:1.1rem;font-weight:900;margin-top:2px">{protein_mins} min</div>
      </div>

      <!-- WHOLE GRAINS — base, widest -->
      <div class="pyramid-block"
           style="background:linear-gradient(135deg,{COLOR_GRAINS},{COLOR_GRAINS}cc);
                  width:{grain_w}%;">
        <div style="font-size:1.2rem">🌾</div>
        <div style="font-size:0.9rem;font-weight:800;letter-spacing:0.03em">WHOLE GRAINS</div>
        <div style="font-size:0.75rem;opacity:0.85">Education + Coding</div>
        <div style="font-size:1.1rem;font-weight:900;margin-top:2px">{grains_mins} min</div>
      </div>

    </div>
    """, unsafe_allow_html=True)

# ─── Feature 4: Streak & XP System (GitHub heatmap) ──────────────────────────
with feat_col4:
    st.markdown('<p class="section-header">// 🏅 Streak & XP System</p>', unsafe_allow_html=True)

    # Compute streak & XP per day for heatmap
    day_totals_series = compute_daily_totals(df).sort_index()
    day_records = []  # list of (date, total, status)
    _streak_run = 0
    _streak_max = 0
    _xp_running = 0
    for _d, _tot in day_totals_series.items():
        _tot = int(_tot)
        if _tot <= goal:
            _streak_run += 1
            _xp_running += XP_PER_DAY_UNDER
            if (goal - _tot) / goal >= XP_BONUS_THRESHOLD:
                _xp_running += XP_BONUS
            _status = "good" if (goal - _tot) / goal >= 0.20 else "ok"
        else:
            _streak_run = 0
            _status = "moderate" if (_tot - goal) <= SEVERE_THRESHOLD else "severe"
        _streak_max = max(_streak_max, _streak_run)
        day_records.append((_d.date(), _tot, _status, _streak_run))

    if not st.session_state["xp_computed"]:
        streak, xp = compute_streak_xp(df, goal)
        st.session_state["streak"] = streak
        st.session_state["xp"] = xp
        st.session_state["xp_computed"] = True

    streak = st.session_state["streak"]
    xp     = st.session_state["xp"]
    level  = xp // XP_PER_LEVEL
    xp_in_level = xp % XP_PER_LEVEL
    xp_pct = int((xp_in_level / XP_PER_LEVEL) * 100)

    # KPI row
    sx1, sx2, sx3 = st.columns(3)
    with sx1:
        st.metric("🔥 Current Streak", f"{streak} days")
    with sx2:
        st.metric("⚡ Total XP", f"{xp} XP")
    with sx3:
        st.metric("🎖️ Level", f"Lvl {level}")

    # ── Full-month calendar heatmap (GitHub-style) ───────────────────────
    import calendar as _cal
    from datetime import date as _date

    STATUS_COLORS = {
        "good":     ("#22c55e", "#166534"),  # bright green
        "ok":       ("#4ade80", "#14532d"),  # light green
        "moderate": ("#f59e0b", "#78350f"),  # amber
        "severe":   ("#ef4444", "#7f1d1d"),  # red
    }

    # Build a lookup: date → (total_mins, status) for dataset days
    _data_lookup = {rec[0]: (rec[1], rec[2]) for rec in day_records}

    # Month to display = month of selected_date
    _month_year = (selected_date.year, selected_date.month)
    _month_name = _date(*_month_year, 1).strftime("%B %Y")
    _days_in_month = _cal.monthrange(*_month_year)[1]
    # weekday of the 1st (Monday=0 … Sunday=6)
    _first_weekday = _cal.monthrange(*_month_year)[0]

    # Weekday headers Mon→Sun
    _WD_LABELS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
    BOX = "width:26px;height:26px;border-radius:5px;display:inline-flex;align-items:center;justify-content:center;"

    # --- Build calendar HTML (NO triple-quoted blocks — avoids Streamlit markdown code-block rendering) ---
    cal_html = (
        '<div style="margin:8px 0 4px 0">'
        f'<div style="color:#a78bfa;font-size:0.78rem;font-weight:700;margin-bottom:8px;letter-spacing:0.05em">{_month_name}</div>'
        '<div style="display:grid;grid-template-columns:repeat(7,30px);gap:4px;margin-bottom:4px">'
    )
    for wd in _WD_LABELS:
        cal_html += (
            f'<div style="width:26px;text-align:center;font-size:0.6rem;'
            f'color:#6b7280;font-weight:700">{wd}</div>'
        )
    cal_html += '</div>\n<div style="display:grid;grid-template-columns:repeat(7,30px);gap:4px">'

    # Empty offset cells for days before the 1st
    for _ in range(_first_weekday):
        cal_html += f'<div style="{BOX}background:transparent"></div>'

    # One box per day of the month
    for _day_num in range(1, _days_in_month + 1):
        _d = _date(*_month_year, _day_num)
        _is_sel = (_d == selected_date)

        if _d in _data_lookup:
            _tot, _status = _data_lookup[_d]
            fg, bg = STATUS_COLORS[_status]
            _tooltip = f"{_d}  {_tot} min"
            _inner = (
                f'background:linear-gradient(135deg,{fg}cc,{fg}55);'
                f'border:{"2px solid " + fg if _is_sel else "1.5px solid " + bg};'
                f'box-shadow:{"0 0 10px " + fg + "aa" if _is_sel else "none"};'
            )
        else:
            # No data for this day → empty/dimmed box
            fg = "#374151"
            _tooltip = f"{_d}  no data"
            _inner = (
                f'background:rgba(255,255,255,0.04);'
                f'border:{"2px solid #a78bfa" if _is_sel else "1.5px solid rgba(255,255,255,0.07)"};'
                f'box-shadow:{"0 0 8px #a78bfaaa" if _is_sel else "none"};'
            )

        _day_label_color = "white" if _d in _data_lookup else "#4b5563"
        cal_html += (
            f'<div title="{_tooltip}" '
            f'style="{BOX}{_inner}cursor:default;transition:transform 0.15s,box-shadow 0.15s;" '
            f'onmouseover="this.style.transform=\'scale(1.3)\'" '
            f'onmouseout="this.style.transform=\'scale(1)\'">'
            f'<span style="font-size:0.6rem;font-weight:700;color:{_day_label_color}">{_day_num}</span>'
            f'</div>'
        )

    cal_html += "</div>"  # close grid

    # Legend — flat string, no indentation to avoid markdown code-block
    cal_html += (
        '<div style="display:flex;gap:10px;align-items:center;margin-top:10px;flex-wrap:wrap">'
        '<span style="font-size:0.65rem;color:#6b7280">Legend:</span>'
        '<span style="display:inline-flex;align-items:center;gap:3px;font-size:0.65rem;color:#9ca3af"><span style="width:10px;height:10px;border-radius:2px;background:#22c55e;display:inline-block"></span>Great</span>'
        '<span style="display:inline-flex;align-items:center;gap:3px;font-size:0.65rem;color:#9ca3af"><span style="width:10px;height:10px;border-radius:2px;background:#4ade80;display:inline-block"></span>Good</span>'
        '<span style="display:inline-flex;align-items:center;gap:3px;font-size:0.65rem;color:#9ca3af"><span style="width:10px;height:10px;border-radius:2px;background:#f59e0b;display:inline-block"></span>Moderate</span>'
        '<span style="display:inline-flex;align-items:center;gap:3px;font-size:0.65rem;color:#9ca3af"><span style="width:10px;height:10px;border-radius:2px;background:#ef4444;display:inline-block"></span>Over limit</span>'
        '<span style="display:inline-flex;align-items:center;gap:3px;font-size:0.65rem;color:#9ca3af"><span style="width:10px;height:10px;border-radius:2px;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.15);display:inline-block"></span>No data</span>'
        '<span style="font-size:0.65rem;color:#a78bfa">[Hover for info]</span>'
        '</div></div>'
    )
    st.markdown(cal_html, unsafe_allow_html=True)

    # XP level bar
    level_labels = ["Couch Potato","Screen Watcher","Aware Scroller","Digital Mindful","Focus Master","Productivity God"]
    current_level_label = level_labels[min(level, len(level_labels)-1)]
    st.markdown(f"""
    <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(124,58,237,0.25);
                border-radius:10px;padding:10px 14px;margin-top:8px">
      <div style="display:flex;justify-content:space-between;margin-bottom:5px">
        <span style="color:#a78bfa;font-size:0.78rem;font-weight:700">Lvl {level} &mdash; {current_level_label}</span>
        <span style="color:#6b7280;font-size:0.72rem">{xp_in_level}/{XP_PER_LEVEL} XP to Lvl {level+1}</span>
      </div>
      <div class="xp-bar-bg">
        <div class="xp-bar-fill" style="width:{xp_pct}%"></div>
      </div>
      <div style="margin-top:6px;font-size:0.7rem;color:#6b7280">
        Max streak: {_streak_max} days &nbsp;|&nbsp; Total XP: {xp} &nbsp;|&nbsp; +10/day under goal, +5 bonus if &gt;20% under
      </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ─── Feature: App-Flow Sankey (Category → App, full 14-day totals) ────────
st.markdown('<p class="section-header">// 🌊 App-Flow Sankey</p>', unsafe_allow_html=True)
st.caption("How your total 14-day time in each category flows into individual apps.")

flow = df.groupby(["Category", "App_Name"])["Minutes_Used"].sum().reset_index()
categories_list = sorted(flow["Category"].unique())
apps_list = sorted(flow["App_Name"].unique())
node_labels = categories_list + apps_list
node_colors = (
    ["#a78bfa"] * len(categories_list) +
    ["rgba(236,72,153,0.8)"] * len(apps_list)
)
cat_idx = {c: i for i, c in enumerate(categories_list)}
app_idx = {a: len(categories_list) + i for i, a in enumerate(apps_list)}

sankey_fig = go.Figure(go.Sankey(
    node=dict(
        pad=14, thickness=16,
        label=node_labels, color=node_colors,
        line=dict(color="rgba(255,255,255,0.15)", width=0.5),
    ),
    link=dict(
        source=[cat_idx[r.Category] for r in flow.itertuples()],
        target=[app_idx[r.App_Name] for r in flow.itertuples()],
        value=[int(r.Minutes_Used) for r in flow.itertuples()],
        color="rgba(167,139,250,0.25)",
    ),
))
sankey_fig.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#d1d5db", size=11),
    height=340,
    margin=dict(l=10, r=10, t=10, b=10),
)
st.plotly_chart(sankey_fig, width="stretch")

st.markdown("---")

# ─── Feature: Achievement Badges ───────────────────────────────────────────
st.markdown('<p class="section-header">// 🏆 Achievement Badges</p>', unsafe_allow_html=True)

badges = compute_badges(df, goal, _streak_max, xp)
badge_cols = st.columns(4)
for i, b in enumerate(badges):
    with badge_cols[i % 4]:
        opacity = "1" if b["unlocked"] else "0.35"
        glow = "0 0 14px rgba(167,139,250,0.5)" if b["unlocked"] else "none"
        st.markdown(f"""
        <div style="text-align:center;padding:14px 8px;border-radius:12px;margin-bottom:10px;
                    background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);
                    opacity:{opacity};box-shadow:{glow}">
          <div style="font-size:1.8rem">{b['emoji'] if b['unlocked'] else '🔒'}</div>
          <div style="font-size:0.78rem;font-weight:700;color:white;margin-top:4px">{b['name']}</div>
          <div style="font-size:0.65rem;color:#9ca3af;margin-top:2px">{b['desc']}</div>
        </div>
        """, unsafe_allow_html=True)

_unlocked_count = sum(1 for b in badges if b["unlocked"])
st.caption(f"{_unlocked_count}/{len(badges)} badges unlocked over this 14-day period.")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — AI COACHING
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown('<p class="section-header">// 🤖 AI Coaching — Powered by Gemini</p>',
            unsafe_allow_html=True)

coach_col, info_col = st.columns([2, 1])

with coach_col:
    btn_clicked = st.button("Get My Coaching 🔥", key="coaching_btn", width="stretch")

    if btn_clicked:
        with st.spinner("Consulting your coach…"):
            coaching_text, severity, ai_status = get_coaching(
                selected_date, day_df, personality, goal
            )
            st.session_state["last_coaching"] = coaching_text
            st.session_state["last_severity"]  = severity
            st.session_state["ai_status"]       = ai_status
            st.rerun()

    if st.session_state["last_coaching"]:
        sev = st.session_state["last_severity"]
        txt = st.session_state["last_coaching"]
        status_icon = {
            "live": "🟢 Live AI response",
            "cached": "🟡 Cached response",
            "offline": "🔴 Offline fallback",
        }.get(st.session_state["ai_status"], "")
        st.caption(status_icon)
        if sev == "severe":
            st.warning(txt, icon="🚨")
        else:
            st.info(txt, icon="✅" if sev == "good" else "⚠️")

with info_col:
    st.markdown("""
    <div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);
                border-radius:12px;padding:16px;">
      <p style="color:#a78bfa;font-weight:700;margin:0 0 8px 0">How Coaching Works</p>
      <p style="color:#9ca3af;font-size:0.82rem;margin:0">
        🔒 <strong>Quota-safe</strong> — API only called on button click<br><br>
        💾 <strong>Cached</strong> — same day + data = no repeat call<br><br>
        🔌 <strong>Offline-ready</strong> — rule-based fallback if API unavailable<br><br>
        🎭 <strong>Personality-aware</strong> — coach tone changes per selection
      </p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════════════════════
# Feature 6: Weekly Roast PDF Download
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown('<p class="section-header">// 📄 Weekly Roast Report (PDF)</p>',
            unsafe_allow_html=True)

pdf_col1, pdf_col2 = st.columns([2, 1])
with pdf_col1:
    coaching_for_pdf = (
        st.session_state["last_coaching"]
        or OFFLINE_TEMPLATES["moderate"]
    )
    pdf_bytes = generate_pdf(df, personality, coaching_for_pdf)
    st.download_button(
        label="⬇️ Download My Performance Review",
        data=bytes(pdf_bytes),
        file_name=f"LifeOS_Review_{datetime.now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf",
        width="stretch",
        key="pdf_download",
    )
with pdf_col2:
    st.markdown("""
    <div style="color:#9ca3af;font-size:0.82rem">
      📋 Satirical "Performance Review" from<br>
      <em>Life-OS Performance Management Division</em><br>
      covering all 14 days. Uses AI coaching text<br>
      already fetched — <strong>zero extra API calls</strong>.
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ─── Feature: Screen Time Wrapped Card (PNG) ───────────────────────────────
st.markdown('<p class="section-header">// 🎁 Life-OS Wrapped</p>', unsafe_allow_html=True)

wrapped_col1, wrapped_col2 = st.columns([2, 1])
with wrapped_col1:
    _avg_life_score = int(sum(
        compute_life_score(get_day_df(df, d), int(t), goal)
        for d, t in compute_daily_totals(df).items()
    ) / max(1, len(all_dates)))
    wrapped_png = generate_wrapped_card(df, goal, _avg_life_score)
    st.download_button(
        label="🎁 Download My Life-OS Wrapped Card",
        data=wrapped_png,
        file_name=f"LifeOS_Wrapped_{datetime.now().strftime('%Y%m%d')}.png",
        mime="image/png",
        width="stretch",
        key="wrapped_download",
    )
with wrapped_col2:
    st.markdown("""
    <div style="color:#9ca3af;font-size:0.82rem">
      📸 Spotify-Wrapped-style shareable summary card<br>
      of your full 14-day period — great for a LinkedIn<br>
      post or the demo video. <strong>Zero API calls</strong>
      (built with matplotlib, purely local).
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown(
    '<p style="text-align:center;color:#4b5563;font-size:0.75rem;font-family:monospace">'
    '© Life-OS 2026 | Built with Streamlit + Gemini | Your data stays local</p>',
    unsafe_allow_html=True,
)
