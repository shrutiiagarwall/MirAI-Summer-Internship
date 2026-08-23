"""
layout.py -- Reusable Streamlit UI building blocks for Life-OS.

Functions here own the HTML/widget rendering for specific sections.
All business logic (data aggregation, scoring, API calls) stays in
data.py / ai_coach.py / viz.py / gamification.py.
"""
import pandas as pd
import streamlit as st

from ai_coach import PERSONALITIES
from data import get_day_df


def render_sidebar(df: pd.DataFrame, all_dates: list) -> tuple:
    """
    Render the full sidebar: date picker, goal slider, coach-personality
    st.form with submit button, system-status badge, and accountability link.

    Returns
    -------
    selected_date : date
    goal          : int  (minutes)
    personality   : str  (PERSONALITIES key)
    coach_submitted : bool
    """
    with st.sidebar:
        st.markdown("## 🧠 **Life-OS**")
        st.markdown('<p class="section-header">// Command Controls</p>', unsafe_allow_html=True)

        # Date selector -- OUTSIDE form so KPIs update instantly
        selected_date = st.selectbox(
            "📅 Select Day",
            options=all_dates,
            index=len(all_dates) - 1 if all_dates else 0,
            format_func=lambda d: d.strftime("%A, %b %d"),
            key="selected_date_sb",
        )

        # Goal slider -- OUTSIDE form for live chart updates
        goal = st.slider(
            "🎯 Daily Goal (minutes)",
            min_value=60, max_value=600, value=300, step=10,
            key="goal_slider",
        )

        st.markdown("---")

        # st.form: personality + coaching trigger (batches 2 widget reruns into 1)
        st.markdown('<p class="section-header">// Coach Personality</p>', unsafe_allow_html=True)
        with st.form(key="coach_form"):
            personality = st.radio(
                "Choose your coach:",
                options=list(PERSONALITIES.keys()),
                key="personality_radio",
                label_visibility="collapsed",
            )
            coach_submitted = st.form_submit_button(
                "Get My Coaching 🔥", width="stretch"
            )

        # System Status badge
        st.markdown("---")
        st.markdown('<p class="section-header">// System Status</p>', unsafe_allow_html=True)
        _status = st.session_state.get("ai_status")
        if _status == "live":
            st.markdown('<span class="badge badge-live">🟢 Live AI</span>', unsafe_allow_html=True)
        elif _status == "cached":
            st.markdown('<span class="badge badge-cached">🟡 Cached Response</span>', unsafe_allow_html=True)
        elif _status == "offline":
            st.markdown('<span class="badge badge-offline">🔴 Offline Mode</span>', unsafe_allow_html=True)
        else:
            st.markdown(
                '<span style="color:#6b7280;font-size:0.8rem">⬜ Awaiting coaching call</span>',
                unsafe_allow_html=True,
            )

        # Accountability link
        st.markdown("---")
        st.markdown('<p class="section-header">// Accountability Link</p>', unsafe_allow_html=True)
        if all_dates:
            _day_df_link      = get_day_df(df, selected_date)
            _today_total_link = int(_day_df_link["Minutes_Used"].sum())
            st.query_params["date"]  = str(selected_date)
            st.query_params["total"] = str(_today_total_link)
            base_url  = "https://mirai-summer-internship.onrender.com"
            share_url = f"{base_url}/?date={selected_date}&total={_today_total_link}"
            st.markdown(f'<div class="copy-box">📎 {share_url}</div>', unsafe_allow_html=True)
            st.caption("Copy URL from address bar to share.")

    return selected_date, goal, personality, coach_submitted


def render_kpi_row(
    today_total: int,
    yesterday_total: int | None,
    goal: int,
    most_used_app: str,
    delta_vs_goal: int,
    selected_date,
) -> None:
    """
    Render the 3-column KPI metric row:
      • 📱 Total Screen Time  (with delta vs yesterday)
      • 🏆 Most Used App
      • ⚡ vs Daily Goal      (with raw delta)
    """
    _time_delta = (today_total - yesterday_total) if yesterday_total is not None else None

    kpi1, kpi2, kpi3 = st.columns(3)
    with kpi1:
        st.metric(
            label="📱 Total Screen Time",
            value=f"{today_total} min",
            delta=f"{_time_delta:+d} min vs yesterday" if _time_delta is not None else None,
            delta_color="inverse",   # more screen time = bad = red
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
            delta_color="inverse",
            help=f"Goal: {goal} min | Today: {today_total} min",
        )