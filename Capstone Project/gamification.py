"""
gamification.py -- XP / Streak / Badge / PDF / Wrapped-card logic for Life-OS
"""
import io
from datetime import datetime

import pandas as pd

# --- XP / Streak constants ---
XP_PER_DAY_UNDER   = 10
XP_BONUS_THRESHOLD = 0.20    # >20% under goal => bonus XP
XP_BONUS           = 5
XP_PER_LEVEL       = 50
SEVERE_THRESHOLD   = 60      # minutes over goal => "severe"

LEVEL_LABELS = [
    "Couch Potato", "Screen Watcher", "Aware Scroller",
    "Digital Mindful", "Focus Master", "Productivity God",
]


# --- Streak & XP ---
def compute_streak_xp(totals_series: pd.Series, goal: int) -> tuple:
    """Given Series (index=date, value=minutes) => (current_streak, total_xp)."""
    streak, xp = 0, 0
    for _, total in totals_series.sort_index().items():
        if total <= goal:
            streak += 1
            xp += XP_PER_DAY_UNDER
            if (goal - total) / goal >= XP_BONUS_THRESHOLD:
                xp += XP_BONUS
        else:
            streak = 0
    return streak, xp


def compute_day_records(totals_series: pd.Series, goal: int) -> list:
    """
    Returns list of (date, total_mins, status, streak_run) for each day.
    status: 'good' | 'ok' | 'moderate' | 'severe'
    """
    records, streak_run = [], 0
    for _d, _tot in totals_series.sort_index().items():
        _tot = int(_tot)
        if _tot <= goal:
            streak_run += 1
            pct_under = (goal - _tot) / goal
            status = "good" if pct_under >= 0.20 else "ok"
        else:
            streak_run = 0
            status = "moderate" if (_tot - goal) <= SEVERE_THRESHOLD else "severe"
        records.append((_d.date(), _tot, status, streak_run))
    return records


# --- Badges ---
def compute_badges(
    dataframe: pd.DataFrame,
    goal: int,
    streak_max: int,
    total_xp: int,
    compute_daily_totals_fn,
    compute_life_score_fn,
    get_day_df_fn,
) -> list:
    """Rule-based achievement badges. Returns list of {emoji, name, desc, unlocked}."""
    cat_by_day    = dataframe.groupby([dataframe["Date"].dt.date, "Category"])["Minutes_Used"].sum()
    totals_by_day = compute_daily_totals_fn(dataframe)
    days_under    = int((totals_by_day <= goal).sum())
    total_days    = len(totals_by_day)
    cats          = cat_by_day.index.get_level_values("Category")

    def _max_cat(name):
        return int(cat_by_day.xs(name, level="Category").max()) if name in cats else 0

    max_coding    = _max_cat("Coding")
    max_education = _max_cat("Education")
    max_social    = _max_cat("Social Media")

    # Comeback Kid: severe day immediately followed by a good day
    sorted_totals = totals_by_day.sort_index()
    comeback, prev = False, None
    for _, _t in sorted_totals.items():
        if prev is not None and (prev - goal) > SEVERE_THRESHOLD and _t <= goal:
            comeback = True
            break
        prev = _t

    avg_life = int(sum(
        compute_life_score_fn(get_day_df_fn(dataframe, d), int(t), goal)
        for d, t in sorted_totals.items()
    ) / max(1, total_days))

    return [
        {"emoji": "💻", "name": "Coding Beast",       "desc": "90+ min coding in one day",             "unlocked": max_coding >= 90},
        {"emoji": "📚", "name": "Bookworm",            "desc": "60+ min education in one day",           "unlocked": max_education >= 60},
        {"emoji": "🎯", "name": "Goal Crusher",        "desc": f"Under goal {max(1,total_days-4)}+ of {total_days} days", "unlocked": days_under >= max(1, total_days - 4)},
        {"emoji": "🔥", "name": "Streak Master",       "desc": "5+ day streak under goal",               "unlocked": streak_max >= 5},
        {"emoji": "⚖️", "name": "Balanced Human",      "desc": "Avg Life Score 70+",                     "unlocked": avg_life >= 70},
        {"emoji": "🌱", "name": "Comeback Kid",        "desc": "Bounced back after a severe day",         "unlocked": comeback},
        {"emoji": "📱", "name": "Doomscroll Champion", "desc": "150+ min Social Media in one day",        "unlocked": max_social >= 150},
        {"emoji": "⚡", "name": "XP Grinder",          "desc": "100+ total XP earned",                    "unlocked": total_xp >= 100},
    ]


# --- Wrapped Card (PNG via matplotlib) ---
def generate_wrapped_card(
    dataframe: pd.DataFrame,
    goal: int,
    avg_life_score: int,
    compute_daily_totals_fn,
) -> bytes:
    """Spotify-Wrapped-style shareable summary PNG. Zero API calls."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    totals     = compute_daily_totals_fn(dataframe)
    top_app    = dataframe.groupby("App_Name")["Minutes_Used"].sum().idxmax()
    top_cat    = dataframe.groupby("Category")["Minutes_Used"].sum().idxmax()
    best_day   = totals.idxmin().strftime("%b %d")
    worst_day  = totals.idxmax().strftime("%b %d")
    days_under = int((totals <= goal).sum())

    fig, ax = plt.subplots(figsize=(6, 10), dpi=150)
    fig.patch.set_facecolor("#0f0c29")
    ax.set_facecolor("#0f0c29")
    ax.axis("off")
    grad = mpatches.FancyBboxPatch(
        (0.03, 0.03), 0.94, 0.94,
        boxstyle="round,pad=0.01", linewidth=2,
        edgecolor="#a78bfa", facecolor="#1a1633",
        transform=ax.transAxes,
    )
    ax.add_patch(grad)
    ax.text(0.5, 0.93, "LIFE-OS WRAPPED",         ha="center", fontsize=24, fontweight="bold", color="#ec4899", transform=ax.transAxes)
    ax.text(0.5, 0.89, "14-Day Screen Time Recap", ha="center", fontsize=11, color="#9ca3af",  transform=ax.transAxes)

    stats = [
        (f"{totals.sum()/60:.1f} hrs",       "Total Screen Time"),
        (top_app,                             "Most Used App"),
        (top_cat,                             "Top Category"),
        (f"{avg_life_score}/100",             "Avg Life Score"),
        (f"{days_under}/{len(totals)} days",  "Under Goal"),
        (f"{best_day} to {worst_day}",        "Best to Worst Day"),
    ]
    y = 0.76
    for value, label in stats:
        ax.text(0.5, y,        str(value),    ha="center", fontsize=20, fontweight="bold", color="white",   transform=ax.transAxes)
        ax.text(0.5, y-0.035,  label.upper(), ha="center", fontsize=9,  color="#a78bfa", transform=ax.transAxes)
        y -= 0.115

    ax.text(0.5, 0.05, "Built with Life-OS", ha="center", fontsize=9, color="#6b7280", transform=ax.transAxes)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


# --- PDF Performance Review ---
def generate_pdf(
    dataframe: pd.DataFrame,
    personality: str,
    coaching_text: str,
    all_dates: list,
    compute_daily_totals_fn,
) -> bytes:
    """
    Generate satirical fpdf2 performance-review PDF.
    Returns bytes on success, None on any failure (error shown via st.error).
    All non-latin-1 chars (emojis) are silently replaced.
    """
    try:
        from fpdf import FPDF
        from fpdf.enums import XPos, YPos

        def _safe(text: str) -> str:
            return text.encode("latin-1", errors="replace").decode("latin-1")

        totals     = compute_daily_totals_fn(dataframe)
        total_all  = int(totals.sum())
        worst_day  = totals.idxmax().strftime("%Y-%m-%d")
        best_day   = totals.idxmin().strftime("%Y-%m-%d")
        top_cat    = dataframe.groupby("Category")["Minutes_Used"].sum().idxmax()
        worst_mins = int(totals.max())
        best_mins  = int(totals.min())
        safe_coaching    = _safe(coaching_text)
        safe_personality = _safe(personality)

        pdf = FPDF()
        pdf.add_page()
        pdf.set_margins(20, 20, 20)

        # Letterhead
        pdf.set_fill_color(15, 12, 41)
        pdf.rect(0, 0, 210, 40, "F")
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(0, 8)
        pdf.cell(210, 10, "LIFE-OS PERFORMANCE MANAGEMENT DIVISION", align="C")
        pdf.set_font("Helvetica", "", 10)
        pdf.set_xy(0, 22)
        pdf.cell(210, 6, "Internal Memo  |  STRICTLY CONFIDENTIAL  |  Digital Productivity Bureau", align="C")
        pdf.set_xy(0, 30)
        pdf.cell(210, 6, f"Review Period: {all_dates[0]}  to  {all_dates[-1]}  |  Coach: {safe_personality}", align="C")

        # Body
        pdf.set_text_color(20, 20, 40)
        pdf.set_xy(20, 50)
        pdf.set_font("Helvetica", "B", 13)
        pdf.cell(0, 8, "QUARTERLY PERFORMANCE REVIEW", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 11)
        pdf.set_x(20)
        pdf.multi_cell(0, 7, _safe(
            f"Subject: Screen Time Performance Review\n"
            f"Reviewed by: Life-OS AI Coaching Engine ({personality})\n"
            f"Date of Issue: {datetime.now().strftime('%Y-%m-%d')}\n"
        ))

        # KPI table
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_x(20)
        pdf.cell(0, 8, "KEY PERFORMANCE INDICATORS (14-Day Period)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 10)
        for label, value in [
            ("Total Screen Time", f"{total_all:,} minutes  ({total_all/60:.1f} hours)"),
            ("Worst Offence Day", f"{worst_day}  -  {worst_mins} minutes"),
            ("Best Recovery Day", f"{best_day}  -  {best_mins} minutes"),
            ("Top Category",      top_cat),
        ]:
            pdf.set_x(20)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(60, 7, label + ":", border="B")
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 7, value, border="B", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Coach assessment
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
            "Life-OS Performance Management Division  |  "
            "Auto-generated for accountability. No screens were harmed in its production.",
            align="C",
        )
        return bytes(pdf.output())

    except Exception as exc:
        import streamlit as st
        st.error(f"PDF generation failed: {exc}")
        return None