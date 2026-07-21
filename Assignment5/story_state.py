"""
story_state.py
==============
Single source of truth for ALL st.session_state keys in the Visual Novel.

ARCHITECTURAL DECISION — WHY THIS FILE EXISTS:
Streamlit reruns the entire Python script from top to bottom on every
user interaction (button click, slider, toggle, etc.). Without controlled
initialization, direct assignment like `st.session_state.score = 0` in
app.py would RESET live data every time the user clicks anything.

THE FIX — setdefault() pattern:
  st.session_state.setdefault("key", default_value)
  → Only writes if the key is ABSENT (i.e., first load only).
  → All subsequent reruns see the existing live value. Game data survives.

Centralizing here means:
  - One file to audit all state keys
  - No accidental double-initialization across modules
  - New contributors know exactly where to look for state
"""

import streamlit as st
from datetime import datetime


def init_state() -> None:
    """
    Initialize all session_state keys with safe defaults.
    Must be called ONCE at the very top of app.py, before any rendering.
    Safe to call on every rerun — setdefault guards against overwrites.
    """

    # ── GAME FLOW ────────────────────────────────────────────────────────────
    st.session_state.setdefault("game_started", False)   # False = show landing
    st.session_state.setdefault("genre", None)           # Chosen on landing screen
    st.session_state.setdefault("scene_index", 0)        # Increments each turn
    st.session_state.setdefault("is_ending", False)      # True = story concluded

    # ── CURRENT SCENE ────────────────────────────────────────────────────────
    # These hold the RENDERED state for the current scene.
    # Updated by process_choice() → persisted → rendered cleanly on next rerun.
    st.session_state.setdefault("current_story_text", "")
    st.session_state.setdefault("current_options", [])
    st.session_state.setdefault("current_image_path", None)
    st.session_state.setdefault("current_audio_path", None)
    st.session_state.setdefault("current_mood", "neutral")
    st.session_state.setdefault("current_commentary", "")
    st.session_state.setdefault("current_speaker", "narrator")

    # ── STORY HISTORY (for PDF export) ───────────────────────────────────────
    # Each entry: {scene_index, story_text, choice_made, image_path, mood}
    st.session_state.setdefault("story_history", [])

    # ── TRUST / RELATIONSHIP SYSTEM ──────────────────────────────────────────
    # WHY: Score is injected into Gemini system prompt every turn.
    # NPCs become warmer (high trust) or suspicious (low trust) dynamically.
    # Range clamped to [0, 100] to keep prompts coherent.
    st.session_state.setdefault("trust_score", 50)

    # ── ACHIEVEMENTS / ENDINGS ───────────────────────────────────────────────
    st.session_state.setdefault("endings_unlocked", set())  # set of ending_id ints
    st.session_state.setdefault("total_endings", 5)

    # ── STORY MAP (Graphviz) ─────────────────────────────────────────────────
    # nodes: list of {"id": int, "label": str, "mood": str}
    # edges: list of {"from": int, "to": int, "label": str}
    st.session_state.setdefault("story_nodes", [])
    st.session_state.setdefault("story_edges", [])

    # ── GEMINI RESPONSE CACHE ────────────────────────────────────────────────
    # WHY: Keyed by hash(choice_text + scene_index) so retrying the same
    # choice reuses stored JSON instead of burning a fresh API call.
    # Critical for staying within free-tier rate limits.
    st.session_state.setdefault("gemini_cache", {})

    # ── DEMO MODE ────────────────────────────────────────────────────────────
    st.session_state.setdefault("demo_mode", False)
    st.session_state.setdefault("demo_scene_idx", 0)

    # ── UI TOGGLES ───────────────────────────────────────────────────────────
    st.session_state.setdefault("show_commentary", False)
    st.session_state.setdefault("show_story_map", True)
    st.session_state.setdefault("voice_input_enabled", False)

    # ── LIVE METRICS ─────────────────────────────────────────────────────────
    # Displayed in the sidebar dashboard. Accumulated throughout the session.
    st.session_state.setdefault("metrics", {
        "gemini_calls": 0,
        "image_calls": 0,
        "tts_calls": 0,
        "fallback_count": 0,
        "latency_ms_total": 0,
        "latency_call_count": 0,
        "session_start": datetime.now().strftime("%H:%M:%S"),
    })

    # ── LAST CHOICE MADE ─────────────────────────────────────────────────────
    # Stored so story_history can record it after the scene advances.
    st.session_state.setdefault("last_choice_made", None)


# ─────────────────────────────────────────────────────────────────────────────
# STATE HELPER FUNCTIONS
# Thin wrappers so app.py stays readable and business logic stays here.
# ─────────────────────────────────────────────────────────────────────────────

def record_scene(scene_dict: dict) -> None:
    """Append a completed scene dict to story_history for PDF export."""
    st.session_state.story_history.append(scene_dict)


def update_trust(delta: int) -> None:
    """
    Shift trust score by delta, clamped to [0, 100].
    WHY clamped: Prevents runaway values (negative or >100) that break
    the Gemini system prompt's qualitative trust description.
    """
    new = st.session_state.trust_score + delta
    st.session_state.trust_score = max(0, min(100, new))


def add_story_node(scene_index: int, label: str, mood: str) -> None:
    """Add a rendered scene as a node in the Graphviz story map."""
    short = (label[:28] + "…") if len(label) > 28 else label
    st.session_state.story_nodes.append({
        "id": scene_index,
        "label": f"#{scene_index}\n{short}",
        "mood": mood,
    })


def add_story_edge(from_idx: int, to_idx: int, choice_label: str) -> None:
    """Add a directed edge (player choice) to the story map."""
    short = (choice_label[:18] + "…") if len(choice_label) > 18 else choice_label
    st.session_state.story_edges.append({
        "from": from_idx,
        "to": to_idx,
        "label": short,
    })


def bump_metric(key: str, amount: float = 1.0) -> None:
    """Safely increment a metric counter. Used by all client modules."""
    m = st.session_state.metrics
    m[key] = m.get(key, 0) + amount


def get_trust_label() -> str:
    """Return a human-readable trust level for Gemini prompt injection."""
    score = st.session_state.trust_score
    if score >= 80:
        return "very high — NPCs are warm, open, and deeply cooperative"
    elif score >= 60:
        return "moderate-high — NPCs are friendly and mostly trusting"
    elif score >= 40:
        return "neutral — NPCs are cautious but willing to engage"
    elif score >= 20:
        return "low — NPCs are suspicious, guarded, and terse"
    else:
        return "very low — NPCs are hostile, evasive, or openly threatening"
