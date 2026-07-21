"""
ui_components.py
================
Reusable UI building blocks for the Visual Novel app.

Contains:
  1. inject_mood_css()     — Live background theming via CSS injection
  2. render_story_map()    — Graphviz branch visualizer
  3. render_sidebar()      — Trust meter + live metrics dashboard
  4. render_trust_meter()  — Styled progress bar for trust score
  5. MOOD_THEMES           — CSS gradient config per mood

WHY SEPARATE FROM app.py:
  Keeping visual logic here lets app.py stay as a clean orchestrator.
  Each function has one job. If you want to change the theming, you
  touch only this file — not the 400-line main app.

CSS INJECTION:
  Streamlit doesn't natively support per-page theming. We use
  st.markdown(unsafe_allow_html=True) to inject a <style> block that
  sets CSS custom properties on :root. The Streamlit container element
  picks up these properties via the stApp selector.
  WHY unsafe_allow_html: There's no other way. This is the standard
  Streamlit pattern for custom theming and it's safe here since we
  control 100% of the injected string.

GRAPHVIZ STORY MAP:
  We build a DOT language string programmatically from session_state
  story_nodes and story_edges. Node colors match the scene's mood.
  The graph is directed (LR layout) to show player progression linearly.
"""

import streamlit as st

# ─────────────────────────────────────────────────────────────────────────────
# MOOD → CSS THEME CONFIG
# Each entry: (bg_gradient_start, bg_gradient_end, accent_color, text_glow)
# ─────────────────────────────────────────────────────────────────────────────
MOOD_THEMES: dict[str, dict] = {
    "tense": {
        "bg_start":  "#1a0505",
        "bg_end":    "#3d0a0a",
        "accent":    "#ff3333",
        "border":    "#8b0000",
        "text_main": "#ffcccc",
        "text_sub":  "#ff8888",
        "label":     "🔴 Tense",
    },
    "joyful": {
        "bg_start":  "#1a1500",
        "bg_end":    "#2d2800",
        "accent":    "#ffd700",
        "border":    "#b8860b",
        "text_main": "#fff8dc",
        "text_sub":  "#ffd700",
        "label":     "🌟 Joyful",
    },
    "mysterious": {
        "bg_start":  "#0d0520",
        "bg_end":    "#1a0a35",
        "accent":    "#9b59b6",
        "border":    "#6c3483",
        "text_main": "#e8d5f5",
        "text_sub":  "#c39bd3",
        "label":     "🌙 Mysterious",
    },
    "neutral": {
        "bg_start":  "#0a1020",
        "bg_end":    "#141e30",
        "accent":    "#5d9cec",
        "border":    "#3a6ea5",
        "text_main": "#d5e8f5",
        "text_sub":  "#8ab4d8",
        "label":     "⚪ Neutral",
    },
    "triumphant": {
        "bg_start":  "#0d1200",
        "bg_end":    "#1f2500",
        "accent":    "#f1c40f",
        "border":    "#b7950b",
        "text_main": "#fefbd8",
        "text_sub":  "#f9e79f",
        "label":     "🏆 Triumphant",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# GRAPHVIZ NODE COLORS per mood
# ─────────────────────────────────────────────────────────────────────────────
MOOD_GRAPH_COLORS: dict[str, str] = {
    "tense":      "#8b0000",
    "joyful":     "#b8860b",
    "mysterious": "#6c3483",
    "neutral":    "#2e4057",
    "triumphant": "#7d6608",
}


def inject_mood_css(mood: str) -> None:
    """
    Dynamically inject CSS to retheme the app background/accents
    based on the current scene's mood.

    Called on every rerender so the theme updates live as the story
    advances. Uses CSS custom properties for clean, conflict-free overrides.
    """
    theme = MOOD_THEMES.get(mood, MOOD_THEMES["neutral"])

    css = f"""
    <style>
    /* ── App background gradient ─────────────────────────────────── */
    .stApp {{
        background: linear-gradient(
            135deg,
            {theme['bg_start']} 0%,
            {theme['bg_end']} 100%
        ) !important;
    }}

    /* ── Story text card ─────────────────────────────────────────── */
    .story-card {{
        background: rgba(0,0,0,0.55);
        border: 1px solid {theme['border']};
        border-radius: 12px;
        padding: 24px 28px;
        margin: 12px 0;
        backdrop-filter: blur(8px);
        box-shadow: 0 0 20px {theme['accent']}33;
    }}

    .story-card p {{
        color: {theme['text_main']};
        font-size: 1.1rem;
        line-height: 1.8;
        font-family: 'Georgia', serif;
        letter-spacing: 0.02em;
    }}

    /* ── Choice buttons ──────────────────────────────────────────── */
    .stButton > button {{
        background: linear-gradient(135deg, rgba(0,0,0,0.7), rgba(30,30,50,0.8)) !important;
        color: {theme['text_main']} !important;
        border: 1px solid {theme['accent']}88 !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        font-size: 0.95rem !important;
        transition: all 0.25s ease !important;
        backdrop-filter: blur(4px) !important;
        width: 100% !important;
    }}
    .stButton > button:hover {{
        border-color: {theme['accent']} !important;
        box-shadow: 0 0 12px {theme['accent']}66 !important;
        transform: translateY(-1px) !important;
        background: linear-gradient(135deg, rgba(0,0,0,0.8), rgba(40,40,70,0.9)) !important;
    }}

    /* ── Sidebar ─────────────────────────────────────────────────── */
    section[data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #0d0d1a 0%, #1a1a2e 100%) !important;
    }}

    /* ── Mood badge ──────────────────────────────────────────────── */
    .mood-badge {{
        display: inline-block;
        background: {theme['accent']}33;
        border: 1px solid {theme['accent']};
        color: {theme['accent']};
        border-radius: 20px;
        padding: 3px 14px;
        font-size: 0.8rem;
        font-weight: bold;
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }}

    /* ── Expander styling ────────────────────────────────────────── */
    .streamlit-expanderHeader {{
        color: {theme['text_sub']} !important;
    }}

    /* ── General text contrast ───────────────────────────────────── */
    .stMarkdown, .stText, label {{
        color: {theme['text_main']} !important;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def render_story_map(nodes: list[dict], edges: list[dict]) -> None:
    """
    Render the player's branching story path as a live Graphviz chart.
    Uses st.graphviz_chart() which renders DOT language in the browser.

    WHY GRAPHVIZ: It's built into Streamlit's dependency tree (no extra
    install needed for basic rendering), and DOT language is easy to build
    programmatically from our node/edge lists.
    """
    if not nodes:
        st.info("Your story map will appear here after your first choice.")
        return

    # Build DOT language string
    lines = [
        "digraph story {",
        "    rankdir=LR;",          # Left-to-right layout
        "    bgcolor=transparent;",
        '    node [fontname="Helvetica" fontsize=9 style=filled fontcolor=white shape=box];',
        '    edge [fontname="Helvetica" fontsize=8 color="#aaaaaa" fontcolor="#cccccc"];',
        "",
    ]

    # Nodes
    for node in nodes:
        node_id    = node["id"]
        label      = node["label"].replace('"', '\\"').replace("\n", "\\n")
        fill_color = MOOD_GRAPH_COLORS.get(node["mood"], "#2e4057")
        lines.append(f'    n{node_id} [label="{label}" fillcolor="{fill_color}"];')

    lines.append("")

    # Edges
    for edge in edges:
        from_id = edge["from"]
        to_id   = edge["to"]
        label   = edge["label"].replace('"', '\\"')
        lines.append(f'    n{from_id} -> n{to_id} [label="{label}"];')

    lines.append("}")
    dot_source = "\n".join(lines)

    st.graphviz_chart(dot_source, use_container_width=True)  # still valid for graphviz in this version


def render_trust_meter(trust_score: int) -> None:
    """
    Display a styled trust/relationship meter in the sidebar.
    Color shifts from red (low) → yellow (mid) → green (high).
    """
    normalized = trust_score / 100.0

    if trust_score >= 70:
        color = "#2ecc71"   # Green
        emoji = "💚"
        label = "Trusted"
    elif trust_score >= 40:
        color = "#f39c12"   # Orange
        emoji = "🤝"
        label = "Neutral"
    else:
        color = "#e74c3c"   # Red
        emoji = "❤️‍🔥"
        label = "Guarded"

    st.markdown(f"""
    <div style="margin-bottom:8px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
            <span style="color:#aaa;font-size:0.8rem;font-weight:bold;">
                {emoji} TRUST SCORE
            </span>
            <span style="color:{color};font-size:0.85rem;font-weight:bold;">
                {trust_score}/100 &nbsp;·&nbsp; {label}
            </span>
        </div>
        <div style="background:#222;border-radius:8px;height:10px;overflow:hidden;">
            <div style="
                width:{trust_score}%;
                height:100%;
                background:linear-gradient(90deg, {color}88, {color});
                border-radius:8px;
                transition:width 0.4s ease;
            "></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_metrics_panel(metrics: dict) -> None:
    """
    Render the live cost/metrics dashboard in the sidebar.
    Shows API calls, fallback counts, and average latency.
    """
    gemini_calls  = metrics.get("gemini_calls", 0)
    image_calls   = metrics.get("image_calls", 0)
    tts_calls     = metrics.get("tts_calls", 0)
    fallbacks     = metrics.get("fallback_count", 0)
    lat_total     = metrics.get("latency_ms_total", 0)
    lat_count     = metrics.get("latency_call_count", 0)
    avg_latency   = (lat_total / lat_count) if lat_count > 0 else 0
    session_start = metrics.get("session_start", "—")

    def _metric_row(label: str, value: str, color: str = "#8ab4d8") -> str:
        return f"""
        <div style="display:flex;justify-content:space-between;
                    padding:4px 0;border-bottom:1px solid #333;">
            <span style="color:#888;font-size:0.78rem;">{label}</span>
            <span style="color:{color};font-size:0.78rem;font-weight:bold;">{value}</span>
        </div>"""

    html = f"""
    <div style="background:#111;border-radius:10px;padding:12px;margin-top:8px;">
        <div style="color:#666;font-size:0.72rem;font-weight:bold;
                    letter-spacing:0.1em;margin-bottom:8px;">
            📊 SESSION METRICS
        </div>
        {_metric_row("Gemini API calls", str(gemini_calls), "#82e0aa")}
        {_metric_row("Image API calls",  str(image_calls),  "#82c8e0")}
        {_metric_row("TTS calls",        str(tts_calls),    "#c8a2e0")}
        {_metric_row("Fallbacks used",   str(fallbacks),    "#e0a282")}
        {_metric_row("Avg. latency",     f"{avg_latency:.0f} ms", "#f0e68c")}
        {_metric_row("Session started",  session_start,     "#888")}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_endings_panel(endings_unlocked: set, total_endings: int) -> None:
    """
    Render the achievements/endings tracker in the sidebar.
    """
    st.markdown(
        f"<div style='color:#888;font-size:0.72rem;font-weight:bold;"
        f"letter-spacing:0.1em;margin-bottom:6px;'>🏆 ENDINGS</div>",
        unsafe_allow_html=True,
    )
    for i in range(1, total_endings + 1):
        if i in endings_unlocked:
            st.markdown(
                f"<span style='color:#2ecc71;font-size:0.82rem;'>✓ Ending {i} — Unlocked</span>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<span style='color:#555;font-size:0.82rem;'>○ Ending {i} — Undiscovered</span>",
                unsafe_allow_html=True,
            )
