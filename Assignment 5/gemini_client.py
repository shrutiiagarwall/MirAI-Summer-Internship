"""
gemini_client.py
================
Handles ALL communication with the Google Gemini API.

KEY ROTATION SYSTEM
-------------------
Reads up to 5 API keys from .env (GEMINI_API_KEY_1 ... GEMINI_API_KEY_5).
When a key fails due to rate limiting or quota exhaustion, it automatically
tries the next key. This makes the app resilient to per-key RPM/TPD limits
without any manual intervention.

Retry strategy:
  For each model in MODEL_CANDIDATES:
    For each key in loaded keys:
      → Try the API call
      → Rate limit / quota (429 / RESOURCE_EXHAUSTED): skip to next key
      → Bad key (401 / API_KEY_INVALID):               skip key permanently
      → Model not found (404):                          break, try next model
      → Success:                                        return result

CACHING
-------
Responses are cached in st.session_state keyed by MD5(choice + scene_index).
Same choice on the same scene never costs a second API call.

JSON PARSING
------------
Three-strategy fallback:
  1. Direct json.loads()
  2. Extract from ```json ... ``` markdown block
  3. Find first { to last } in response text
"""

import json
import re
import time
import hashlib
import os
import streamlit as st
from dotenv import load_dotenv

from story_state import bump_metric

# ─────────────────────────────────────────────────────────────────────────────
# Lazy import
# ─────────────────────────────────────────────────────────────────────────────
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────────────
# MODEL FALLBACK CHAIN
# ─────────────────────────────────────────────────────────────────────────────
MODEL_CANDIDATES = [
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.0-pro",
]

# ─────────────────────────────────────────────────────────────────────────────
# FIELD VALIDATION
# ─────────────────────────────────────────────────────────────────────────────
REQUIRED_FIELDS = {"story_text", "options", "image_prompt", "mood"}
VALID_MOODS     = {"tense", "joyful", "mysterious", "neutral", "triumphant"}


# ─────────────────────────────────────────────────────────────────────────────
# LOAD API KEYS
# Reads GEMINI_API_KEY_1 … GEMINI_API_KEY_5 from .env.
# Falls back to legacy GEMINI_API_KEY if no numbered keys are found.
# ─────────────────────────────────────────────────────────────────────────────
def _load_api_keys() -> list[str]:
    """Load keys from st.secrets (Streamlit Cloud) or .env (local)."""
    load_dotenv(override=False)
    placeholders = {"your_primary_key_here", "your_second_key_here",
                    "your_key_here", "your_gemini_api_key_here", ""}
    keys: list[str] = []

    # Streamlit Cloud secrets (set in the dashboard, never committed)
    try:
        for i in range(1, 6):
            k = st.secrets.get(f"GEMINI_API_KEY_{i}", "").strip()
            if k and k not in placeholders:
                keys.append(k)
        if not keys:
            legacy = st.secrets.get("GEMINI_API_KEY", "").strip()
            if legacy and legacy not in placeholders:
                keys.append(legacy)
    except Exception:
        pass  # st.secrets not available locally — fall through to .env

    # Local .env fallback
    if not keys:
        for i in range(1, 6):
            k = os.getenv(f"GEMINI_API_KEY_{i}", "").strip().strip('"').strip("'")
            if k and k not in placeholders:
                keys.append(k)

    if not keys:
        legacy = os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")
        if legacy and legacy not in placeholders:
            keys.append(legacy)

    return keys


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _make_cache_key(choice_text: str, scene_index: int) -> str:
    raw = f"{choice_text}::{scene_index}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _build_system_prompt(genre: str, trust_score: int, trust_label: str) -> str:
    genre_context = {
        "horror":  "psychological horror with supernatural elements, existential dread, and redemption arcs",
        "romance": "contemporary romance with emotional depth, witty dialogue, and heartfelt moments",
        "sci-fi":  "hard sci-fi with AI ethics, first contact, and the future of humanity",
        "mystery": "classic detective mystery with planted clues, red herrings, and logical deduction",
    }.get(genre, "literary fiction with compelling character arcs")

    return f"""You are a master storyteller AI generating an interactive visual novel in the {genre} genre.
The story should feel like {genre_context}.

TRUST CONTEXT:
The player's current trust score is {trust_score}/100 ({trust_label}).
Let this shape how NPCs speak and behave -- do NOT mention the score directly in the story.

OUTPUT FORMAT -- YOU MUST RETURN ONLY VALID JSON, NO MARKDOWN, NO PREAMBLE:
{{
  "story_text": "3-5 vivid, atmospheric sentences of narrative prose",
  "options": ["2-4 choice strings that feel meaningfully different"],
  "image_prompt": "A detailed visual description for AI image generation (1-2 sentences)",
  "mood": "exactly one of: tense, joyful, mysterious, neutral, triumphant",
  "speaker": "narrator, character, or villain",
  "commentary": "1-2 sentences explaining your narrative choice (for Director mode)",
  "trust_delta": an integer from -10 to 10 reflecting how the scene affects trust,
  "is_ending": false,
  "ending_id": null
}}

RULES:
- story_text must be immersive prose, never meta or self-referential
- options must be 2-4 strings, each under 80 characters
- mood must be exactly one of the five valid values
- Return ONLY the JSON object -- no ```json blocks, no explanation
"""


def _parse_gemini_json(raw_text: str) -> dict | None:
    """Three-strategy JSON extraction from Gemini's response."""
    # Strategy 1: direct parse
    try:
        data = json.loads(raw_text.strip())
        if REQUIRED_FIELDS.issubset(data.keys()):
            return data
    except json.JSONDecodeError:
        pass

    # Strategy 2: extract from markdown code block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            if REQUIRED_FIELDS.issubset(data.keys()):
                return data
        except json.JSONDecodeError:
            pass

    # Strategy 3: first { to last }
    start = raw_text.find("{")
    end   = raw_text.rfind("}") + 1
    if start != -1 and end > start:
        try:
            data = json.loads(raw_text[start:end])
            if REQUIRED_FIELDS.issubset(data.keys()):
                return data
        except json.JSONDecodeError:
            pass

    return None


def _sanitize_scene(data: dict) -> dict:
    if data.get("mood") not in VALID_MOODS:
        data["mood"] = "neutral"
    if not isinstance(data.get("options"), list) or len(data["options"]) == 0:
        data["options"] = ["Continue..."]
    data.setdefault("speaker",    "narrator")
    data.setdefault("commentary", "The story continues...")
    data.setdefault("trust_delta", 0)
    data.setdefault("is_ending",  False)
    data.setdefault("ending_id",  None)
    data["trust_delta"] = max(-10, min(10, int(data.get("trust_delta", 0))))
    return data


def _fallback_scene(genre: str) -> dict:
    return {
        "story_text": (
            "The air grows still. Something shifts in the world around you, "
            "as if the universe itself is catching its breath. "
            "The path forward is yours to choose."
        ),
        "options": ["Press on bravely", "Pause and reflect", "Look for another way"],
        "image_prompt": f"Atmospheric {genre} scene, dramatic lighting, cinematic",
        "mood":         "neutral",
        "speaker":      "narrator",
        "commentary":   "A bridge scene used when the story engine encounters an unexpected state.",
        "trust_delta":  0,
        "is_ending":    False,
        "ending_id":    None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CORE CALL — one key, one model
# Returns (response_text, None) or (None, error_string)
# ─────────────────────────────────────────────────────────────────────────────
def _try_call(api_key: str, model_name: str,
              system_prompt: str, user_message: str) -> tuple[str | None, str | None]:
    try:
        genai.configure(api_key=api_key)
        model    = genai.GenerativeModel(model_name=model_name,
                                         system_instruction=system_prompt)
        response = model.generate_content(user_message)
        return response.text, None
    except Exception as e:
        return None, str(e)


# ─────────────────────────────────────────────────────────────────────────────
# ERROR CLASSIFICATION
# ─────────────────────────────────────────────────────────────────────────────
def _classify_error(err: str) -> str:
    """
    Returns one of:
      'rate_limit'   - 429 / RESOURCE_EXHAUSTED / quota → try next key
      'bad_key'      - 401 / API_KEY_INVALID → skip key permanently
      'model_error'  - 404 / not found / deprecated → try next model
      'unknown'      - anything else → try next key as a safe default
    """
    e = err.lower()
    if any(x in e for x in ("429", "quota", "resource_exhausted",
                             "rate limit", "rate_limit", "too many")):
        return "rate_limit"
    if any(x in e for x in ("401", "api_key_invalid", "invalid api key",
                             "api key not valid", "permission_denied",
                             "api_key", "unauthenticated")):
        return "bad_key"
    if any(x in e for x in ("404", "not found", "model_not_found",
                             "does not exist", "not supported",
                             "deprecated", "invalid model")):
        return "model_error"
    return "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PUBLIC FUNCTION
# ─────────────────────────────────────────────────────────────────────────────
def get_scene(
    choice_text:    str,
    scene_index:    int,
    genre:          str,
    trust_score:    int,
    trust_label:    str,
    story_history:  list,
    demo_mode:      bool,
    demo_scene_idx: int,
    api_key:        str,        # legacy single-key param, kept for compatibility
) -> dict:
    """
    Return a validated scene dict for the given player choice.

    Key-rotation flow:
      For each model in MODEL_CANDIDATES:
        For each key in available_keys:
          → Try call
          → rate_limit / unknown → skip to next key (same model)
          → bad_key              → remove key, skip to next key
          → model_error          → break inner loop, try next model
          → success              → parse JSON, cache, return
      If all combinations exhausted → return fallback scene
    """
    # ── Demo mode ─────────────────────────────────────────────────────────────
    if demo_mode:
        from demo_data import get_demo_scene
        return get_demo_scene(genre, demo_scene_idx)

    # ── Cache check ───────────────────────────────────────────────────────────
    cache_key = _make_cache_key(choice_text, scene_index)
    if cache_key in st.session_state.gemini_cache:
        return st.session_state.gemini_cache[cache_key]

    # ── SDK check ─────────────────────────────────────────────────────────────
    if not GEMINI_AVAILABLE:
        st.toast("Gemini SDK not installed. Enable Demo Mode or run: pip install google-generativeai", icon="⚠️")
        bump_metric("fallback_count")
        return _fallback_scene(genre)

    # ── Load all available keys ───────────────────────────────────────────────
    available_keys = _load_api_keys()

    # Also accept the legacy single-key argument passed from app.py
    if api_key and api_key not in ("your_gemini_api_key_here", "") \
            and api_key not in available_keys:
        available_keys.insert(0, api_key)

    if not available_keys:
        st.toast(
            "No Gemini API key found. Add GEMINI_API_KEY_1 to your .env file, "
            "or enable Demo Mode in the sidebar.",
            icon="🔑",
        )
        bump_metric("fallback_count")
        return _fallback_scene(genre)

    # ── Build prompt ──────────────────────────────────────────────────────────
    recent_context = ""
    if story_history:
        recent_context = "\n\n".join(
            f"Scene {s['scene_index']}: {s['story_text'][:200]}..."
            for s in story_history[-3:]
        )

    user_message = (
        f"The player chose: \"{choice_text}\"\n\n"
        f"Recent story context:\n{recent_context}"
        if recent_context else
        f"The player chose: \"{choice_text}\"\n\nThis is the beginning of the story."
    )
    system_prompt = _build_system_prompt(genre, trust_score, trust_label)

    # ── Key-rotation retry loop ───────────────────────────────────────────────
    t_start    = time.time()
    last_error = "No keys or models available"
    bad_keys   = set()          # permanently skip these within this call

    for model_name in MODEL_CANDIDATES:
        for key_index, key in enumerate(available_keys):
            if key in bad_keys:
                continue

            raw_text, error = _try_call(key, model_name, system_prompt, user_message)

            if raw_text is not None:
                # ── SUCCESS ────────────────────────────────────────────────
                latency_ms = (time.time() - t_start) * 1000
                bump_metric("gemini_calls")
                bump_metric("latency_ms_total", latency_ms)
                bump_metric("latency_call_count")

                parsed = _parse_gemini_json(raw_text)
                if parsed is None:
                    st.toast("Gemini responded but JSON was malformed — using fallback.", icon="⚠️")
                    bump_metric("fallback_count")
                    return _fallback_scene(genre)

                scene = _sanitize_scene(parsed)
                st.session_state.gemini_cache[cache_key] = scene
                return scene

            # ── FAILURE — classify and decide what to do ──────────────────
            last_error  = error or "unknown error"
            error_class = _classify_error(last_error)
            key_label   = f"Key {key_index + 1}"

            if error_class == "bad_key":
                bad_keys.add(key)
                st.toast(f"API {key_label} is invalid or lacks permission — skipping.", icon="🔑")
                continue  # try next key, same model

            if error_class == "model_error":
                # This model isn't available — no point trying other keys for it
                break  # break inner (key) loop → outer loop tries next model

            if error_class == "rate_limit":
                keys_left = len([k for k in available_keys if k not in bad_keys])
                if keys_left > key_index + 1:
                    st.toast(f"API {key_label} rate-limited — switching to next key.", icon="⏱️")
                else:
                    st.toast(f"All keys rate-limited on {model_name} — trying next model.", icon="⏱️")
                continue  # try next key

            # unknown error → try next key
            continue

    # ── All models + all keys exhausted ───────────────────────────────────────
    short_err = last_error[:100]
    st.toast(f"All API keys and models failed ({short_err}). Using fallback scene.", icon="⚠️")
    bump_metric("fallback_count")
    return _fallback_scene(genre)
