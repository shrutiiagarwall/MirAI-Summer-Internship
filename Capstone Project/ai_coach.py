"""
ai_coach.py -- Gemini AI coaching for Life-OS.
Implements: system_instruction split, Gemini function calling,
            JSON caching with voice-hash support, offline fallback.
"""
import hashlib
import json
import os
import textwrap
from pathlib import Path

import pandas as pd
import streamlit as st

from data import day_category_summary, compute_severity

CACHE_PATH = Path(__file__).parent / "coaching_cache.json"

# --- Coach personalities ---
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

# --- Offline fallback templates ---
OFFLINE_TEMPLATES = {
    "good": (
        "OK **Solid day!** You stayed within your goal -- that kind of discipline compounds over time. "
        "Keep building on your Education and Coding time; even 15 extra minutes of focused coding "
        "daily beats 3 hours of passive scrolling every week of the year."
    ),
    "moderate": (
        "WARNING **Borderline day.** You are nudging over your screen-time goal. "
        "Your Social Media + Entertainment time is creeping up -- consider a 20-minute scroll tax: "
        "before each social session, complete one coding task or read one article. "
        "Small friction = big behaviour change."
    ),
    "severe": (
        "ALERT **Intervention mode.** You are significantly over your daily goal. "
        "The hours lost to entertainment and social media today could have been: "
        "a 10 km walk, 3 chapters of a book, or a side project feature shipped. "
        "Tomorrow: set your phone to grayscale and put it in another room during your first "
        "2 work hours. Data does not lie -- your future self is watching."
    ),
}


# --- Real-world equivalent (Python function + Gemini tool) ---
def get_real_world_equivalent(minutes: int) -> dict:
    """
    Convert screen-time minutes into real-world activity equivalents.
    Exposed as both a local Python function AND a Gemini function-calling tool.
    """
    WORDS_PER_MIN     = 250
    WORDS_PER_BOOK    = 80_000
    WALK_KM_PER_HR    = 5
    PUSHUPS_PER_MIN   = 12
    SLEEP_EQUIV_RATIO = 0.85
    return {
        "books":               round(minutes / (WORDS_PER_BOOK / WORDS_PER_MIN), 2),
        "km":                  round((minutes / 60) * WALK_KM_PER_HR, 1),
        "pushups":             int(minutes * PUSHUPS_PER_MIN),
        "sleep_recovered_min": int(minutes * SLEEP_EQUIV_RATIO),
    }


# --- Cache I/O ---
def load_cache() -> dict:
    """Load coaching cache. Returns {} on missing file or corrupt JSON."""
    if not CACHE_PATH.exists():
        return {}
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_cache(cache: dict) -> None:
    """Persist cache. Shows st.warning (non-fatal) if filesystem is read-only."""
    try:
        CACHE_PATH.write_text(
            json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except OSError as exc:
        st.warning(f"Cache write failed (responses still work this session): {exc}")


def make_cache_key(
    chosen_date,
    day_df: pd.DataFrame,
    personality: str,
    voice_hash: str = "",
) -> str:
    """SHA-256 key: date + category data + personality + optional voice hash."""
    raw = f"{chosen_date}|{day_category_summary(day_df)}|{personality}|{voice_hash}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


# --- Prompt construction: system_instruction + user prompt split (Phase 2) ---
def build_system_instruction(personality: str) -> str:
    """Persona rules passed as system_instruction to Gemini -- separate from data."""
    persona = PERSONALITIES[personality]
    return textwrap.dedent(f"""
        You are a personal productivity coach.

        PERSONALITY AND TONE:
        {persona}

        BEHAVIORAL RULES (always follow regardless of personality):
        - NEVER give generic advice like "use your phone less".
        - ALWAYS reference the SPECIFIC CATEGORIES from the user screen-time data.
        - Use concrete real-world comparisons (books read, km walked, push-ups).
        - If a tool result is provided in the prompt, incorporate those exact numbers.
        - Return ONLY a single valid JSON object. No markdown fences. No extra text.
        - JSON schema: {{"coaching_text": "<3-5 sentences>", "severity": "<good|moderate|severe>"}}
        - severity must reflect whether total usage is good, moderate, or severe vs the daily goal.
    """).strip()


def build_user_prompt(cat_summary: str, goal: int, voice_transcript: str = "") -> str:
    """User data passed as the user-turn to Gemini. Optionally includes voice journal."""
    voice_section = ""
    if voice_transcript.strip():
        voice_section = (
            f"\nUSER VOICE JOURNAL (why they were on their phone today):\n"
            f'"{voice_transcript}"\n'
            f"Factor this context into your coaching. Acknowledge what they shared.\n"
        )
    return textwrap.dedent(f"""
        The user's DAILY SCREEN TIME GOAL is {goal} minutes.

        Today's screen time by category (minutes):
        {cat_summary}
        {voice_section}
        Provide your structured coaching response now.
    """).strip()


# --- Gemini call with function calling ---
def call_gemini(
    system_instruction: str,
    user_prompt: str,
    api_key: str,
    junk_mins: int = 0,
) -> dict:
    """
    Calls Gemini with system_instruction + user prompt.
    If Gemini issues a get_real_world_equivalent function call, executes it
    locally and feeds the result back before the final response.
    Returns parsed {coaching_text, severity}.
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    # Tool definition
    rwe_tool = types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="get_real_world_equivalent",
                description=(
                    "Convert minutes of junk screen time (Social Media + Entertainment) "
                    "into real-world activity equivalents: books read, km walked, "
                    "push-ups completed, and minutes of sleep recovered."
                ),
                parameters=types.Schema(
                    type="OBJECT",
                    properties={
                        "minutes": types.Schema(
                            type="INTEGER",
                            description="Minutes of junk screen time to convert.",
                        )
                    },
                    required=["minutes"],
                ),
            )
        ]
    )

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[rwe_tool],
    )

    # First turn
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_prompt,
        config=config,
    )

    # Handle function call if issued
    tool_context = ""
    if response.candidates:
        for part in response.candidates[0].content.parts:
            if hasattr(part, "function_call") and part.function_call:
                fc = part.function_call
                if fc.name == "get_real_world_equivalent":
                    mins_arg = int(fc.args.get("minutes", junk_mins or 0))
                    rwe      = get_real_world_equivalent(mins_arg)
                    tool_context = (
                        f"[Tool result -- {mins_arg} min of junk screen time equals: "
                        f"{rwe['books']} books read, {rwe['km']} km walked, "
                        f"{rwe['pushups']} push-ups, {rwe['sleep_recovered_min']} min sleep recovered.]"
                    )

    # Second turn if tool was called
    if tool_context:
        follow_up = f"{user_prompt}\n\n{tool_context}\n\nNow produce the final JSON coaching response."
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=follow_up,
            config=types.GenerateContentConfig(system_instruction=system_instruction),
        )

    raw = response.text.strip()
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:])
        raw = raw.rsplit("```", 1)[0].strip()
    return json.loads(raw)


# --- Public entrypoint ---
def get_coaching(
    chosen_date,
    day_df: pd.DataFrame,
    personality: str,
    goal: int,
    voice_transcript: str = "",
) -> tuple:
    """
    Returns (coaching_text, severity, status).
    status: 'live' | 'cached' | 'offline'
    """
    api_key    = os.getenv("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", "")
    voice_hash = hashlib.sha256(voice_transcript.encode()).hexdigest()[:8] if voice_transcript.strip() else ""
    cache_key  = make_cache_key(chosen_date, day_df, personality, voice_hash)
    cache      = load_cache()

    # Cache hit
    if cache_key in cache:
        entry = cache[cache_key]
        return entry["coaching_text"], entry["severity"], "cached"

    # No key => offline
    if not api_key or api_key in ("", "your_key_here"):
        severity = compute_severity(int(day_df["Minutes_Used"].sum()), goal)
        return OFFLINE_TEMPLATES[severity], severity, "offline"

    # Live API call
    try:
        junk_mins   = int(day_df[day_df["Category"].isin(["Social Media","Entertainment"])]["Minutes_Used"].sum())
        sys_inst    = build_system_instruction(personality)
        user_prompt = build_user_prompt(day_category_summary(day_df), goal, voice_transcript)
        result      = call_gemini(sys_inst, user_prompt, api_key, junk_mins)

        coaching_text = result.get("coaching_text", "")
        severity      = result.get("severity", compute_severity(int(day_df["Minutes_Used"].sum()), goal))

        cache[cache_key] = {"coaching_text": coaching_text, "severity": severity}
        save_cache(cache)
        return coaching_text, severity, "live"

    except Exception as exc:
        severity = compute_severity(int(day_df["Minutes_Used"].sum()), goal)
        return OFFLINE_TEMPLATES[severity] + f"\n\n*(Offline -- API error: {exc})*", severity, "offline"