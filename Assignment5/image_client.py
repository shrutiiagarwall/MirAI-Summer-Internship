"""
image_client.py
===============
Image generation with Gemini API key rotation + Pollinations fallback.

GENERATION STRATEGY (in order):
  For Key 1:
    Try gemini-2.5-flash-image
    Try gemini-3.1-flash-image-preview
    Try gemini-3.1-flash-lite-image
    Try gemini-3.1-flash-image
    Try gemini-3-pro-image-preview
    Try gemini-3-pro-image
    (rate limit / quota → move to Key 2)
    (bad key → mark invalid, move to Key 2)
    (model not found → try next model, same key)
  For Key 2: same model chain
  For Key 3 ... Key 5: same
  If ALL keys × ALL models fail:
    → Pollinations API (free, no key, URL-based)
  If Pollinations also fails:
    → Local mood asset (assets/mood_{mood}.png)
    → None (app shows placeholder text)

WHY google-genai (not google-generativeai):
  Image generation with response_modalities=['IMAGE'] is only supported
  in the newer unified SDK (google-genai). The legacy google-generativeai
  SDK (0.8.x) does not expose GenerateContentConfig.response_modalities.

IMAGE RETURN:
  Gemini returns base64-encoded PNG inside inline_data.
  We decode and save to temp_images/ just like Pollinations images.
  The local path is what gets stored in session_state and shown with st.image().
"""

import os
import base64
import time
import requests
import streamlit as st
from urllib.parse import quote

from story_state import bump_metric

# ─────────────────────────────────────────────────────────────────────────────
# SDK IMPORTS
# ─────────────────────────────────────────────────────────────────────────────
try:
    from google import genai as google_genai
    from google.genai import types as genai_types
    GEMINI_IMAGE_AVAILABLE = True
except ImportError:
    GEMINI_IMAGE_AVAILABLE = False

from dotenv import load_dotenv

# ─────────────────────────────────────────────────────────────────────────────
# GEMINI IMAGE MODEL FALLBACK CHAIN
# Ordered: best quality / most available → fastest / most lenient quota
# ─────────────────────────────────────────────────────────────────────────────
GEMINI_IMAGE_MODELS = [
    "gemini-2.5-flash-image",
    "gemini-3.1-flash-image-preview",
    "gemini-3.1-flash-lite-image",
    "gemini-3.1-flash-image",
    "gemini-3-pro-image-preview",
    "gemini-3-pro-image",
]

# ─────────────────────────────────────────────────────────────────────────────
# POLLINATIONS (final fallback — free, no key)
# ─────────────────────────────────────────────────────────────────────────────
POLLINATIONS_BASE  = "https://image.pollinations.ai/prompt"
IMAGE_WIDTH        = 768
IMAGE_HEIGHT       = 512
REQUEST_TIMEOUT = 30   # Pollinations can be slow — give it a full 30s

# ─────────────────────────────────────────────────────────────────────────────
# LOCAL FALLBACK ASSETS
# ─────────────────────────────────────────────────────────────────────────────
TEMP_IMAGE_DIR = os.path.join(os.path.dirname(__file__), "temp_images")
os.makedirs(TEMP_IMAGE_DIR, exist_ok=True)

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
FALLBACK_IMAGES: dict[str, str] = {
    "joyful":     os.path.join(ASSETS_DIR, "mood_joyful.png"),
    "tense":      os.path.join(ASSETS_DIR, "mood_tense.png"),
    "mysterious": os.path.join(ASSETS_DIR, "mood_mysterious.png"),
    "neutral":    os.path.join(ASSETS_DIR, "mood_neutral.png"),
    "triumphant": os.path.join(ASSETS_DIR, "mood_triumphant.png"),
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _load_api_keys() -> list[str]:
    """Load keys from st.secrets (Streamlit Cloud) or .env (local)."""
    load_dotenv(override=False)
    placeholders = {"your_primary_key_here", "your_second_key_here",
                    "your_key_here", "your_gemini_api_key_here", ""}
    keys: list[str] = []

    try:
        import streamlit as _st
        for i in range(1, 6):
            k = _st.secrets.get(f"GEMINI_API_KEY_{i}", "").strip()
            if k and k not in placeholders:
                keys.append(k)
        if not keys:
            legacy = _st.secrets.get("GEMINI_API_KEY", "").strip()
            if legacy and legacy not in placeholders:
                keys.append(legacy)
    except Exception:
        pass

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


def _classify_error(err: str) -> str:
    """
    Classify API error to decide rotation strategy:
      'rate_limit'  → try next key (same model)
      'bad_key'     → skip key permanently
      'model_error' → try next model (same key continues)
      'unknown'     → try next key as safe default
    """
    e = err.lower()
    if any(x in e for x in ("429", "quota", "resource_exhausted",
                             "rate limit", "rate_limit", "too many")):
        return "rate_limit"
    if any(x in e for x in ("401", "api_key_invalid", "invalid api key",
                             "api key not valid", "permission_denied",
                             "unauthenticated")):
        return "bad_key"
    if any(x in e for x in ("404", "not found", "model_not_found",
                             "does not exist", "not supported",
                             "deprecated", "invalid model", "invalid_argument")):
        return "model_error"
    return "unknown"


def _save_image(content: bytes, scene_index: int, suffix: str = "") -> str:
    """Save image bytes to temp_images/, return absolute path."""
    filename = f"scene_{scene_index}_{int(time.time())}{suffix}.png"
    path = os.path.join(TEMP_IMAGE_DIR, filename)
    with open(path, "wb") as f:
        f.write(content)
    return path


def _get_fallback(mood: str) -> str | None:
    """Return local mood asset path, or None if not present."""
    path = FALLBACK_IMAGES.get(mood)
    if path and os.path.exists(path):
        return path
    neutral = FALLBACK_IMAGES.get("neutral")
    if neutral and os.path.exists(neutral):
        return neutral
    return None


# ─────────────────────────────────────────────────────────────────────────────
# GEMINI IMAGE GENERATION
# ─────────────────────────────────────────────────────────────────────────────
def _try_gemini_image(api_key: str, model_name: str,
                      prompt: str, scene_index: int) -> tuple[str | None, str | None]:
    """
    Try one (key, model) combination.
    Returns (local_image_path, None) on success or (None, error_string) on failure.
    """
    try:
        client = google_genai.Client(api_key=api_key)
        resp = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"]
            ),
        )
        # Find the inline_data part (the image)
        for part in resp.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                img_bytes = base64.b64decode(part.inline_data.data)
                if len(img_bytes) > 500:
                    path = _save_image(img_bytes, scene_index, suffix="_gemini")
                    return path, None

        # Response came back but had no image part
        return None, "model_error: response contained no image data"

    except Exception as e:
        return None, str(e)


def _fetch_gemini_image(image_prompt: str, mood: str,
                        scene_index: int) -> str | None:
    """
    Attempt Gemini image generation across all keys x all models.

    Strategy per (key, model) combination:
      rate_limit  → BREAK model loop immediately (quota is per-key, not per-model;
                    trying other models with same key wastes calls and time)
                    → move to next key
      bad_key     → mark key as permanently invalid → move to next key
      model_error → try next model, same key (model unavailable on this key)
      unknown     → try next model, same key

    Returns local image path or None if everything fails.
    """
    if not GEMINI_IMAGE_AVAILABLE:
        return None

    keys = _load_api_keys()
    if not keys:
        return None

    bad_keys = set()

    for key_idx, key in enumerate(keys):
        if key in bad_keys:
            continue

        key_label   = f"Key {key_idx + 1}"

        for model_name in GEMINI_IMAGE_MODELS:
            path, error = _try_gemini_image(key, model_name, image_prompt, scene_index)

            if path is not None:
                return path  # SUCCESS

            err_class = _classify_error(error or "")

            if err_class == "bad_key":
                bad_keys.add(key)
                st.toast(f"🔑 API {key_label} rejected — trying next key.", icon="🔑")
                break  # break model loop → try next key

            if err_class == "rate_limit":
                # Quota is per-key — no point trying other models on same key
                if key_idx + 1 < len(keys):
                    st.toast(f"⏱️ {key_label} rate-limited — switching to next key.", icon="⏱️")
                break  # FIX: break immediately instead of trying all models

            # model_error or unknown → try next model on same key
            continue

        # After exhausting all keys, fall through to Pollinations

    return None  # All keys exhausted × all models.


# ─────────────────────────────────────────────────────────────────────────────
# POLLINATIONS FALLBACK
# ─────────────────────────────────────────────────────────────────────────────
def _fetch_pollinations_image(image_prompt: str, scene_index: int) -> str | None:
    """Download an image from Pollinations. Returns local path or None."""
    encoded = quote(image_prompt, safe="")
    seed    = int(time.time()) % 10000
    url     = (
        f"{POLLINATIONS_BASE}/{encoded}"
        f"?width={IMAGE_WIDTH}&height={IMAGE_HEIGHT}&nologo=true&seed={seed}"
    )
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT, stream=True)
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "image" not in content_type:
            raise ValueError(f"Non-image response: {content_type}")
        image_bytes = response.content
        if len(image_bytes) < 1000:
            raise ValueError("Payload too small — likely an error page")
        return _save_image(image_bytes, scene_index, suffix="_pollinations")
    except requests.exceptions.Timeout:
        st.toast("🖼️ Pollinations timed out — using local visual.", icon="⏱️")
    except requests.exceptions.ConnectionError:
        st.toast("🖼️ Pollinations unreachable — using local visual.", icon="📡")
    except Exception:
        st.toast("🖼️ Image generation skipped — using local visual.", icon="🖼️")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
def fetch_image(image_prompt: str, mood: str,
                scene_index: int, demo_mode: bool) -> str | None:
    """
    Fetch an image for the given prompt and return a local file path.

    Priority:
      1. Demo mode      → local mood asset immediately (no network)
      2. Gemini API     → Key 1 × all models → Key 2 × all models → … → Key N
      3. Pollinations   → free URL-based generation, no key required
      4. Local asset    → mood-matched PNG from assets/
      5. None           → app.py shows placeholder div

    Returns: absolute path to a local PNG file, or None.
    """
    # ── Demo mode ──────────────────────────────────────────────────────────────
    if demo_mode:
        return _get_fallback(mood)

    bump_metric("image_calls")

    # ── 1. Try Gemini image generation ────────────────────────────────────────
    gemini_path = _fetch_gemini_image(image_prompt, mood, scene_index)
    if gemini_path:
        return gemini_path

    # ── 2. Fall back to Pollinations ──────────────────────────────────────────
    st.toast("🖼️ Gemini image quota reached — using Pollinations instead.", icon="🔄")
    pollinations_path = _fetch_pollinations_image(image_prompt, scene_index)
    if pollinations_path:
        return pollinations_path

    # ── 3. Final fallback: local mood asset ───────────────────────────────────
    bump_metric("fallback_count")
    return _get_fallback(mood)
