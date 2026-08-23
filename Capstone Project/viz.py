"""
viz.py -- Plotly figure builders and HTML chart helpers for Life-OS
"""
import pandas as pd
import plotly.graph_objects as go

COLOR_ACCENT    = "#7C3AED"
COLOR_GOAL_LINE = "#FFD700"

_BOOK_MAX  = 5.0
_KM_MAX    = 30.0
_PU_MAX    = 5000.0
_SLEEP_MAX = 480.0


# --- 14-Day Trend Chart ---
def build_trend_chart(daily_totals: pd.DataFrame, selected_date, goal: int) -> go.Figure:
    """Line chart with filled area, selected-day star, and goal dashed line."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily_totals["Date"], y=daily_totals["Minutes"],
        mode="lines+markers", name="Daily Screen Time",
        line=dict(color="#a78bfa", width=3),
        marker=dict(size=8, color="#ec4899"),
        fill="tozeroy", fillcolor="rgba(167,139,250,0.15)",
    ))
    sel = daily_totals[daily_totals["Date"].dt.date == selected_date]
    if not sel.empty:
        fig.add_trace(go.Scatter(
            x=sel["Date"], y=sel["Minutes"],
            mode="markers", name="Selected Day",
            marker=dict(size=14, color=COLOR_ACCENT, symbol="star"),
        ))
    fig.add_hline(
        y=goal, line_dash="dash", line_color=COLOR_GOAL_LINE,
        annotation_text=f"Goal: {goal} min",
        annotation_position="top right",
        annotation_font_color=COLOR_GOAL_LINE,
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#d1d5db"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", title="Minutes"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=0, r=0, t=30, b=0), height=320,
    )
    return fig


# --- Life Score Gauge ---
def build_life_score_gauge(life_score: int) -> go.Figure:
    """Indicator gauge for the 0-100 Life Score."""
    color = "#22c55e" if life_score >= 70 else ("#f59e0b" if life_score >= 40 else "#ef4444")
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=life_score,
        number={"suffix": " / 100", "font": {"color": "white", "size": 34}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#6b7280"},
            "bar":  {"color": color},
            "bgcolor": "rgba(255,255,255,0.04)", "borderwidth": 0,
            "steps": [
                {"range": [0, 40],   "color": "rgba(239,68,68,0.18)"},
                {"range": [40, 70],  "color": "rgba(245,158,11,0.18)"},
                {"range": [70, 100], "color": "rgba(34,197,94,0.18)"},
            ],
        },
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#d1d5db"),
        height=220, margin=dict(l=20, r=20, t=10, b=0),
    )
    return fig


# --- Compare Two Days Bar Chart ---
def build_compare_chart(df_a: pd.Series, df_b: pd.Series, day_a, day_b) -> go.Figure:
    """Grouped bar chart comparing category totals for two days."""
    all_cats = sorted(set(df_a.index) | set(df_b.index))
    fig = go.Figure([
        go.Bar(x=all_cats, y=[int(df_a.get(c, 0)) for c in all_cats],
               name=day_a.strftime("%b %d"), marker_color="#a78bfa"),
        go.Bar(x=all_cats, y=[int(df_b.get(c, 0)) for c in all_cats],
               name=day_b.strftime("%b %d"), marker_color="#ec4899"),
    ])
    fig.update_layout(
        barmode="group", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#d1d5db"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)", title="Minutes"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=0, r=0, t=30, b=0), height=300,
    )
    return fig


# --- App-Flow Sankey ---
def build_sankey(df: pd.DataFrame) -> go.Figure:
    """Category to App flow Sankey for full 14-day totals."""
    flow   = df.groupby(["Category", "App_Name"])["Minutes_Used"].sum().reset_index()
    cats   = sorted(flow["Category"].unique())
    apps   = sorted(flow["App_Name"].unique())
    labels = cats + apps
    colors = ["#a78bfa"] * len(cats) + ["rgba(236,72,153,0.8)"] * len(apps)
    ci     = {c: i             for i, c in enumerate(cats)}
    ai     = {a: len(cats) + i for i, a in enumerate(apps)}
    fig = go.Figure(go.Sankey(
        node=dict(pad=14, thickness=16, label=labels, color=colors,
                  line=dict(color="rgba(255,255,255,0.15)", width=0.5)),
        link=dict(
            source=[ci[r.Category] for r in flow.itertuples()],
            target=[ai[r.App_Name] for r in flow.itertuples()],
            value=[int(r.Minutes_Used) for r in flow.itertuples()],
            color="rgba(167,139,250,0.25)",
        ),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#d1d5db", size=11),
        height=340, margin=dict(l=10, r=10, t=10, b=10),
    )
    return fig


# --- Real-World Equivalents HTML gauge bars ---
def _gauge_bar(value: float, max_val: float, label: str, unit: str, color: str) -> str:
    pct   = min(value / max_val, 1.0)
    bar_w = int(pct * 100)
    ref   = label.split()[-1] if " " in label else ""
    return (
        f'<div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.1);'
        f'border-radius:12px;padding:12px 14px;margin-bottom:10px">'
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px">'
        f'<span style="color:#9ca3af;font-size:0.75rem;font-weight:600">{label}</span>'
        f'<span style="color:white;font-size:1.05rem;font-weight:800">{unit}</span>'
        f'</div>'
        f'<div style="background:rgba(255,255,255,0.08);border-radius:999px;height:8px;overflow:hidden">'
        f'<div style="width:{bar_w}%;height:100%;border-radius:999px;'
        f'background:linear-gradient(90deg,{color}99,{color});transition:width 0.5s ease"></div>'
        f'</div>'
        f'<div style="text-align:right;color:#6b7280;font-size:0.65rem;margin-top:3px">'
        f'{pct*100:.0f}% of {max_val} {ref} ref</div>'
        f'</div>'
    )


def build_real_world_gauges_html(junk_mins: int) -> str:
    """Returns HTML string of 4 animated gauge bars for real-world equivalents."""
    from ai_coach import get_real_world_equivalent
    rwe = get_real_world_equivalent(junk_mins)
    return (
        _gauge_bar(rwe["books"],               _BOOK_MAX,  "Books read",       f"{rwe['books']:.2f} books",        "#818cf8") +
        _gauge_bar(rwe["km"],                  _KM_MAX,    "Walking km",       f"{rwe['km']:.1f} km",              "#34d399") +
        _gauge_bar(rwe["pushups"],             _PU_MAX,    "Push-ups",         f"{rwe['pushups']:,} reps",         "#f472b6") +
        _gauge_bar(rwe["sleep_recovered_min"], _SLEEP_MAX, "Sleep recovered",  f"{rwe['sleep_recovered_min']} min","#fbbf24")
    )