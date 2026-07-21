"""
tts_client.py
=============
Converts story text to narration audio using edge-tts (primary)
with gTTS as a silent fallback.

VOICE SYSTEM:
  edge-tts offers 300+ neural voices. We map the `speaker` field from
  Gemini's JSON to different voices to give each narrator/character a
  distinct feel. This adds personality without requiring a paid TTS API.

  Speaker → Voice mapping:
    narrator  → Aria (calm, authoritative US female)
    character → Guy  (warm, relatable US male)
    villain   → Ryan (crisp, British male — naturally sounds more menacing)

WINDOWS + STREAMLIT ASYNCIO FIX:
  edge-tts is fully async (uses asyncio internally). Streamlit already
  manages its own event loop. Calling asyncio.run() directly from the
  Streamlit script would cause "event loop already running" errors.

  The fix: run edge-tts inside a SEPARATE THREAD that creates its own
  clean event loop. The thread is joined with a timeout so the app never
  hangs indefinitely on a slow TTS call.

FALLBACK CHAIN:
  1. edge-tts   — best quality, multiple voices, free
  2. gTTS       — simpler, single voice, requires internet
  3. ambient.mp3 — local fallback for fully offline operation
  4. None       — app renders without audio (story text still visible)
"""

import os
import asyncio
import threading
import time
import streamlit as st

from story_state import bump_metric

# ─────────────────────────────────────────────────────────────────────────────
# Lazy imports — neither TTS library is guaranteed to be installed
# ─────────────────────────────────────────────────────────────────────────────
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
TEMP_AUDIO_DIR = os.path.join(os.path.dirname(__file__), "temp_audio")
os.makedirs(TEMP_AUDIO_DIR, exist_ok=True)

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
AMBIENT_FALLBACK = os.path.join(ASSETS_DIR, "ambient.mp3")

EDGE_TTS_TIMEOUT = 30  # seconds before we give up and fall back

# ─────────────────────────────────────────────────────────────────────────────
# VOICE MAP — speaker field → edge-tts voice name
# WHY: Distinct voices for narrator vs character vs villain make the story
# feel more like a produced audiobook without requiring paid voice actors.
# ─────────────────────────────────────────────────────────────────────────────
VOICE_MAP: dict[str, str] = {
    "narrator":  "en-US-AriaNeural",      # Calm, warm, authoritative
    "character": "en-US-GuyNeural",       # Friendly, relatable
    "villain":   "en-GB-RyanNeural",      # Crisp British — naturally ominous
}
DEFAULT_VOICE = "en-US-AriaNeural"

# ─────────────────────────────────────────────────────────────────────────────
# EDGE-TTS HELPERS (async + thread isolation)
# ─────────────────────────────────────────────────────────────────────────────

def _run_edge_tts_in_thread(text: str, output_path: str, voice: str) -> bool:
    """
    Run edge-tts inside an isolated thread with its own event loop.

    WHY A SEPARATE THREAD:
      Streamlit runs inside an event loop. edge-tts needs to run its own
      async coroutines. Calling asyncio.run() from inside Streamlit's loop
      raises RuntimeError. A separate thread gets a fresh, conflict-free loop.

    Returns True on success, False on any error.
    """
    success_flag = [False]  # Use list so it's mutable inside nested function

    def thread_target():
        # Each thread creates its own event loop — no sharing with Streamlit
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            async def _speak():
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(output_path)

            loop.run_until_complete(_speak())
            success_flag[0] = True
        except Exception:
            success_flag[0] = False
        finally:
            loop.close()

    t = threading.Thread(target=thread_target, daemon=True)
    t.start()
    t.join(timeout=EDGE_TTS_TIMEOUT)

    if t.is_alive():
        # Thread is still running after timeout — TTS call hung
        return False

    return success_flag[0]


# ─────────────────────────────────────────────────────────────────────────────
# GTTS HELPER
# ─────────────────────────────────────────────────────────────────────────────

def _run_gtts(text: str, output_path: str) -> bool:
    """
    Generate audio using gTTS (Google Text-to-Speech via HTTP).
    Returns True on success, False on error.
    """
    try:
        tts = gTTS(text=text, lang="en", slow=False)
        tts.save(output_path)
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def generate_narration(
    story_text: str,
    speaker: str,
    scene_index: int,
    demo_mode: bool,
) -> str | None:
    """
    Convert story_text to an audio file and return its local path.

    In demo mode: skip TTS generation and return the ambient fallback
    immediately (avoids any network call during screen-recorded demos).

    Returns: absolute path to an audio file, or None.
    """
    bump_metric("tts_calls")

    # ── Demo Mode ────────────────────────────────────────────────────────────
    if demo_mode:
        if os.path.exists(AMBIENT_FALLBACK):
            return AMBIENT_FALLBACK
        return None

    # ── Select voice ─────────────────────────────────────────────────────────
    voice = VOICE_MAP.get(speaker, DEFAULT_VOICE)

    # ── Build output path ────────────────────────────────────────────────────
    timestamp = int(time.time())
    mp3_path = os.path.join(TEMP_AUDIO_DIR, f"narration_{scene_index}_{timestamp}.mp3")

    # ── Strategy 1: edge-tts ─────────────────────────────────────────────────
    if EDGE_TTS_AVAILABLE:
        ok = _run_edge_tts_in_thread(story_text, mp3_path, voice)
        if ok and os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 0:
            return mp3_path
        # If edge-tts failed, fall through to gTTS

    # ── Strategy 2: gTTS ─────────────────────────────────────────────────────
    if GTTS_AVAILABLE:
        ok = _run_gtts(story_text, mp3_path)
        if ok and os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 0:
            return mp3_path

    # ── Strategy 3: local ambient fallback ───────────────────────────────────
    st.toast("🎙️ Narration unavailable — playing ambient audio instead.", icon="🔇")
    bump_metric("fallback_count")
    if os.path.exists(AMBIENT_FALLBACK):
        return AMBIENT_FALLBACK

    # ── All strategies exhausted ─────────────────────────────────────────────
    return None
