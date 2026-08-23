"""
data.py -- CSV loading, aggregation, and scoring for Life-OS
"""
from pathlib import Path

import pandas as pd
import streamlit as st

# --- Paths & constants ---
CSV_PATH = Path(__file__).parent / "screentime.csv"

WORDS_PER_MIN      = 250
WORDS_PER_BOOK     = 80_000
WALK_KM_PER_HR     = 5
PUSHUPS_PER_MIN    = 12
SLEEP_EQUIV_RATIO  = 0.85

SEVERE_THRESHOLD   = 60
MODERATE_THRESHOLD = 0


# --- CSV loading ---
@st.cache_data
def load_data() -> pd.DataFrame:
    """Load & parse screentime.csv. Shows st.error and returns empty DF on failure."""
    try:
        df = pd.read_csv(CSV_PATH)
        df["Date"] = pd.to_datetime(df["Date"])
        return df
    except FileNotFoundError:
        st.error(
            f"**screentime.csv not found** at `{CSV_PATH}`. "
            "Place the CSV next to app.py and restart."
        )
        return pd.DataFrame(columns=["Date", "App_Name", "Category", "Minutes_Used"])
    except Exception as exc:
        st.error(f"**Failed to load screentime.csv:** {exc}")
        return pd.DataFrame(columns=["Date", "App_Name", "Category", "Minutes_Used"])


# --- Aggregation helpers ---
def compute_daily_totals(dataframe: pd.DataFrame) -> pd.Series:
    """Total minutes per date across the full dataset."""
    return dataframe.groupby("Date")["Minutes_Used"].sum()


def get_day_df(dataframe: pd.DataFrame, chosen_date) -> pd.DataFrame:
    """Filter to a single date."""
    return dataframe[dataframe["Date"].dt.date == chosen_date].copy()


def day_category_summary(day_df: pd.DataFrame) -> str:
    """Category totals as a clean string for Gemini prompts."""
    return day_df.groupby("Category")["Minutes_Used"].sum().to_string()


# --- Scoring ---
def compute_severity(today_total: int, goal: int) -> str:
    """Return 'good' | 'moderate' | 'severe' based on minutes over goal."""
    delta = today_total - goal
    if delta > SEVERE_THRESHOLD:
        return "severe"
    elif delta > MODERATE_THRESHOLD:
        return "moderate"
    return "good"


def compute_life_score(day_df: pd.DataFrame, today_total: int, goal: int) -> int:
    """
    Composite 0-100:
      60% category balance (productive vs junk) + 40% goal adherence.
    A high-coding day at 9h total can outscore a short doomscrolling day.
    """
    cat        = day_df.groupby("Category")["Minutes_Used"].sum()
    productive = int(cat.get("Education", 0) + cat.get("Coding", 0))
    junk       = int(cat.get("Social Media", 0) + cat.get("Entertainment", 0))
    balance_score = 50 + 50 * (productive - junk) / (productive + junk + 1)
    goal_ratio    = (today_total / goal) if goal else 1.0
    goal_score    = max(0, min(100, 100 - max(0.0, goal_ratio - 1) * 150))
    return int(max(0, min(100, round(0.6 * balance_score + 0.4 * goal_score))))