"""
app.py
======
MirAI Visual Novel — Main Streamlit Application

ARCHITECTURE OVERVIEW:
  This file is the thin orchestrator. All heavy logic lives in modules:
    gemini_client.py  → story generation
    image_client.py   → scene visuals
    tts_client.py     → narration audio
    pdf_export.py     → story export
    story_state.py    → session_state management
    ui_components.py  → CSS/UI helpers
    demo_data.py      → offline fallback scenes

  app.py only:
    1. Initializes state (once, via story_state.init_state)
    2. Routes between landing screen and story screen
    3. Renders scene content from session_state
    4. Handles choice button clicks → calls process_choice()
    5. Wires sidebar controls

STATEFUL RENDERING PATTERN:
  Streamlit re-runs this entire file on EVERY user action. The rendered
  content (image, audio, story text) is read from session_state, not
  re-fetched. process_choice() updates session_state, then st.rerun()
  triggers a clean render of the new scene. This is why assets persist
  across button clicks — they live in session_state, not in local vars.

"""

import os
import time
import streamlit as st
from dotenv import load_dotenv

# Local modules
import story_state as ss
import gemini_client
import image_client
import tts_client
import pdf_export
import ui_components as ui

# ─────────────────────────────────────────────────────────────────────────────
# FEATURE FLAGS
# ─────────────────────────────────────────────────────────────────────────────
ENABLE_VOICE_INPUT = True   # Set True if streamlit-mic-recorder is installed

# ─────────────────────────────────────────────────────────────────────────────
# ENVIRONMENT + PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
load_dotenv()  # Load GEMINI_API_KEY from .env file
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

st.set_page_config(
    page_title="MirAI Visual Novel",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# STATE INITIALIZATION — must happen before any rendering
# WHY HERE: init_state() uses setdefault() so it's safe to call on every rerun.
# It will only write keys that don't exist yet (first load).
# ─────────────────────────────────────────────────────────────────────────────
ss.init_state()


# ═════════════════════════════════════════════════════════════════════════════
# CORE LOGIC — process_choice()
# ═════════════════════════════════════════════════════════════════════════════

def process_choice(choice_text: str) -> None:
    """
    Handle a player's choice button click. This is the central game loop step.

    Flow:
      1. Record the choice for story_history (before advancing scene_index)
      2. Save current scene to story_history
      3. Advance scene index
      4. Fetch next Gemini scene (or demo/cache)
      5. Fetch image (or fallback)
      6. Generate TTS audio (or fallback)
      7. Update trust score
      8. Update story map graph
      9. Write all new values to session_state
      10. Check for endings / achievements

    WHY update session_state THEN rerun:
      Streamlit renders from session_state. Updating it here, then calling
      st.rerun(), gives a clean render with new data — no partial states shown.
    """
    demo_mode     = st.session_state.demo_mode
    genre         = st.session_state.genre or "mystery"
    scene_index   = st.session_state.scene_index
    trust_score   = st.session_state.trust_score
    trust_label   = ss.get_trust_label()
    story_history = st.session_state.story_history

    # ── 1. Save previous scene to history ────────────────────────────────────
    if st.session_state.current_story_text:
        ss.record_scene({
            "scene_index": scene_index,
            "story_text":  st.session_state.current_story_text,
            "choice_made": choice_text,
            "image_path":  st.session_state.current_image_path,
            "mood":        st.session_state.current_mood,
        })

    # ── 2. Fetch next scene ───────────────────────────────────────────────────
    with st.spinner("✨ The story unfolds…"):
        scene = gemini_client.get_scene(
            choice_text    = choice_text,
            scene_index    = scene_index,
            genre          = genre,
            trust_score    = trust_score,
            trust_label    = trust_label,
            story_history  = story_history,
            demo_mode      = demo_mode,
            demo_scene_idx = st.session_state.demo_scene_idx,
            api_key        = GEMINI_API_KEY,
        )

    new_scene_index = scene_index + 1

    # ── 3. Fetch image ────────────────────────────────────────────────────────
    image_path = image_client.fetch_image(
        image_prompt = scene["image_prompt"],
        mood         = scene["mood"],
        scene_index  = new_scene_index,
        demo_mode    = demo_mode,
    )

    # ── 4. Generate TTS ───────────────────────────────────────────────────────
    audio_path = tts_client.generate_narration(
        story_text  = scene["story_text"],
        speaker     = scene.get("speaker", "narrator"),
        scene_index = new_scene_index,
        demo_mode   = demo_mode,
    )

    # ── 5. Update trust score ─────────────────────────────────────────────────
    ss.update_trust(scene.get("trust_delta", 0))

    # ── 6. Update story map ───────────────────────────────────────────────────
    ss.add_story_node(new_scene_index, scene["story_text"], scene["mood"])
    ss.add_story_edge(scene_index, new_scene_index, choice_text)

    # ── 7. Advance demo index (if demo mode) ──────────────────────────────────
    if demo_mode:
        st.session_state.demo_scene_idx += 1

    # ── 8. Write all new values to session_state ──────────────────────────────
    # WHY all at once: prevents partial-render between individual assignments.
    st.session_state.scene_index          = new_scene_index
    st.session_state.current_story_text   = scene["story_text"]
    st.session_state.current_options      = scene["options"]
    st.session_state.current_image_path   = image_path
    st.session_state.current_audio_path   = audio_path
    st.session_state.current_mood         = scene["mood"]
    st.session_state.current_commentary   = scene.get("commentary", "")
    st.session_state.current_speaker      = scene.get("speaker", "narrator")
    st.session_state.is_ending            = scene.get("is_ending", False)
    st.session_state.last_choice_made     = choice_text

    # ── 9. Check for endings ──────────────────────────────────────────────────
    if scene.get("is_ending") and scene.get("ending_id"):
        ending_id = scene["ending_id"]
        if ending_id not in st.session_state.endings_unlocked:
            st.session_state.endings_unlocked.add(ending_id)
            n_unlocked = len(st.session_state.endings_unlocked)
            n_total    = st.session_state.total_endings
            st.balloons()
            st.toast(
                f"🏆 You unlocked Ending {ending_id} of {n_total}! "
                f"({n_unlocked}/{n_total} found)",
                icon="🏆",
            )
            # Save ending scene to history (no choice recorded)
            ss.record_scene({
                "scene_index": new_scene_index,
                "story_text":  scene["story_text"],
                "choice_made": None,
                "image_path":  image_path,
                "mood":        scene["mood"],
            })


# ═════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═════════════════════════════════════════════════════════════════════════════

def render_sidebar() -> None:
    """
    Build the sidebar with all controls, meters, and the metrics dashboard.
    Sidebar state changes (toggles) trigger a Streamlit rerun automatically.
    """
    with st.sidebar:
        # ── Branding ─────────────────────────────────────────────────────────
        st.markdown("""
        <div style="text-align:center;padding:10px 0 16px;">
            <div style="font-size:2rem;">📖</div>
            <div style="font-size:1.1rem;font-weight:bold;color:#c8a2ff;">
                MirAI Visual Novel
            </div>
            <div style="font-size:0.72rem;color:#666;margin-top:2px;">
                AI-Powered Interactive Story
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # ── Genre badge ───────────────────────────────────────────────────────
        if st.session_state.genre:
            genre_icons = {
                "horror": "👻", "romance": "💕",
                "sci-fi": "🚀", "mystery": "🔍"
            }
            icon = genre_icons.get(st.session_state.genre, "📖")
            st.markdown(
                f"<div style='text-align:center;color:#aaa;font-size:0.82rem;"
                f"margin-bottom:12px;'>{icon} Genre: "
                f"<b style='color:#c8a2ff'>{st.session_state.genre.upper()}</b></div>",
                unsafe_allow_html=True,
            )

        # ── Trust meter ───────────────────────────────────────────────────────
        if st.session_state.game_started:
            ui.render_trust_meter(st.session_state.trust_score)
            st.divider()

        # ── Controls ──────────────────────────────────────────────────────────
        st.markdown(
            "<div style='color:#666;font-size:0.72rem;font-weight:bold;"
            "letter-spacing:0.1em;margin-bottom:8px;'>⚙️ CONTROLS</div>",
            unsafe_allow_html=True,
        )

        # Demo Mode toggle
        demo = st.checkbox(
            "🎬 Demo Mode (offline)",
            value=st.session_state.demo_mode,
            help="Uses pre-scripted scenes — no API calls, safe for screen recording.",
        )
        if demo != st.session_state.demo_mode:
            st.session_state.demo_mode = demo
            if demo:
                st.toast("Demo Mode ON — using pre-scripted story.", icon="🎬")

        # Director's Commentary toggle
        commentary = st.checkbox(
            "🎬 Director's Commentary",
            value=st.session_state.show_commentary,
            help="Shows the AI's reasoning behind each plot choice.",
        )
        st.session_state.show_commentary = commentary

        # Story map toggle
        show_map = st.checkbox(
            "🗺️ Show Story Map",
            value=st.session_state.show_story_map,
        )
        st.session_state.show_story_map = show_map

        # Voice input (behind feature flag)
        if ENABLE_VOICE_INPUT:
            voice_input = st.checkbox(
                "🎙️ Voice Input",
                value=st.session_state.voice_input_enabled,
                help="Speak your choice instead of clicking (requires mic).",
            )
            st.session_state.voice_input_enabled = voice_input

        st.divider()

        # ── Endings tracker ───────────────────────────────────────────────────
        if st.session_state.game_started:
            ui.render_endings_panel(
                st.session_state.endings_unlocked,
                st.session_state.total_endings,
            )
            st.divider()



        # ── PDF Export ────────────────────────────────────────────────────────
        if st.session_state.story_history:
            st.markdown(
                "<div style='color:#666;font-size:0.72rem;font-weight:bold;"
                "letter-spacing:0.1em;margin-bottom:8px;'>📄 EXPORT</div>",
                unsafe_allow_html=True,
            )
            with st.spinner("Building PDF…"):
                pdf_bytes = pdf_export.build_pdf(
                    story_history    = st.session_state.story_history,
                    genre            = st.session_state.genre or "story",
                    trust_score      = st.session_state.trust_score,
                    endings_unlocked = st.session_state.endings_unlocked,
                    total_endings    = st.session_state.total_endings,
                )
            if pdf_bytes:
                st.download_button(
                    label    = "📥 Export Story as PDF",
                    data     = pdf_bytes,
                    file_name= f"mirai_story_{st.session_state.genre}.pdf",
                    mime     = "application/pdf",
                    width    = "stretch",
                )
            else:
                st.caption("⚠️ fpdf2 not installed — PDF export unavailable.")

        # ── Restart button ────────────────────────────────────────────────────
        if st.session_state.game_started:
            st.divider()
            if st.button("🔄 Restart Story", width="stretch"):
                # Clear all state except persistent endings tracker
                saved_endings = st.session_state.endings_unlocked.copy()
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                ss.init_state()
                st.session_state.endings_unlocked = saved_endings
                st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
# LANDING SCREEN
# ═════════════════════════════════════════════════════════════════════════════

def render_landing_screen() -> None:
    """
    Show the genre selection landing screen before the story begins.
    Clicking a genre card sets the genre and starts the game.
    """
    # Full-page dark gradient via injected CSS
    st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #0a0a1a 0%, #1a0a2e 50%, #0a1a1a 100%) !important; }
    section[data-testid="stSidebar"] { background: #0d0d1a !important; }
    </style>
    """, unsafe_allow_html=True)

    # Hero section
    st.markdown("""
    <div style="text-align:center;padding:40px 0 20px;">
        <div style="font-size:4rem;margin-bottom:10px;">📖✨</div>
        <h1 style="
            font-size:3rem;
            font-weight:900;
            background:linear-gradient(135deg, #c8a2ff, #82c8ff, #82ffca);
            -webkit-background-clip:text;
            -webkit-text-fill-color:transparent;
            background-clip:text;
            margin:0;
            letter-spacing:-0.02em;
        ">MirAI Visual Novel</h1>
        <p style="color:#888;font-size:1.1rem;margin-top:10px;letter-spacing:0.05em;">
            An AI-Powered Interactive Narrative Experience
        </p>
        <p style="color:#555;font-size:0.9rem;margin-top:4px;">
            Mirai School of Technology · Capstone Project
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<h3 style='text-align:center;color:#aaa;margin:30px 0 20px;'>"
                "Choose Your Story Genre</h3>", unsafe_allow_html=True)

    # Genre cards in a 4-column grid
    genres = [
        {
            "key":   "horror",
            "icon":  "👻",
            "name":  "Horror",
            "desc":  "Supernatural dread, psychological twists, dark atmosphere",
            "color": "#8b0000",
            "glow":  "#ff333366",
        },
        {
            "key":   "romance",
            "icon":  "💕",
            "name":  "Romance",
            "desc":  "Heartfelt connections, witty dialogue, emotional moments",
            "color": "#8b2252",
            "glow":  "#ff69b466",
        },
        {
            "key":   "sci-fi",
            "icon":  "🚀",
            "name":  "Sci-Fi",
            "desc":  "Futuristic worlds, AI ethics, first contact & exploration",
            "color": "#003366",
            "glow":  "#5d9cec66",
        },
        {
            "key":   "mystery",
            "icon":  "🔍",
            "name":  "Mystery",
            "desc":  "Detective intrigue, hidden clues, logical deduction",
            "color": "#2d4a1e",
            "glow":  "#7dbb5066",
        },
    ]

    cols = st.columns(4, gap="medium")
    for col, genre in zip(cols, genres):
        with col:
            # Styled card via HTML
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, {genre['color']}cc, {genre['color']}55);
                border: 1px solid {genre['color']};
                border-radius: 16px;
                padding: 28px 20px;
                text-align: center;
                margin-bottom: 12px;
                box-shadow: 0 0 20px {genre['glow']};
                min-height: 180px;
                display: flex;
                flex-direction: column;
                justify-content: center;
            ">
                <div style="font-size:2.5rem;margin-bottom:10px;">{genre['icon']}</div>
                <div style="font-size:1.2rem;font-weight:bold;color:#fff;
                            margin-bottom:8px;">{genre['name']}</div>
                <div style="font-size:0.78rem;color:#ccc;line-height:1.5;">
                    {genre['desc']}
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(
                f"Begin {genre['name']} Story",
                key=f"genre_btn_{genre['key']}",
                width="stretch",
            ):
                _start_game(genre["key"])

    # Feature preview
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="
        text-align:center;
        color:#444;
        font-size:0.8rem;
        padding:20px;
        border-top:1px solid #222;
    ">
        🤖 Gemini AI &nbsp;·&nbsp; 🖼️ Pollinations Images &nbsp;·&nbsp;
        🎙️ Neural TTS &nbsp;·&nbsp; 🗺️ Live Story Map &nbsp;·&nbsp;
        📄 PDF Export &nbsp;·&nbsp; 🏆 Achievement System
    </div>
    """, unsafe_allow_html=True)


def _start_game(genre: str) -> None:
    """
    Initialize the game with the chosen genre and generate the opening scene.

    WHY we add node 0 here and then process_choice adds node 1:
      Node 0 is the virtual "game start" node. process_choice() always
      adds the destination node (new_scene_index = scene_index + 1),
      and an edge FROM scene_index TO new_scene_index. So the graph
      correctly shows: [0: Start] --> [1: First Scene] --> [2: ...]
    """
    st.session_state.genre        = genre
    st.session_state.game_started = True

    # Root node: "Start" (scene 0 = before any choices)
    genre_icons = {"horror": "👻", "romance": "💕", "sci-fi": "🚀", "mystery": "🔍"}
    icon = genre_icons.get(genre, "📖")
    ss.add_story_node(0, f"{icon} {genre.upper()} START", "neutral")

    # Synthesize an opening prompt to kick off Gemini / Demo
    opening_choice = f"Start a {genre} story. Open with a powerful, immersive scene."

    with st.spinner(f"Opening your {genre} story…"):
        process_choice(opening_choice)
    st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
# STORY SCREEN
# ═════════════════════════════════════════════════════════════════════════════

def render_story_screen() -> None:
    """
    Render the active story scene with image, audio, text, and choice buttons.
    All content is read from session_state so it persists across reruns.
    """
    mood = st.session_state.current_mood

    # ── Apply mood CSS theme ──────────────────────────────────────────────────
    # WHY: Called on every render so theme updates live as mood changes.
    ui.inject_mood_css(mood)

    # ── Scene image ───────────────────────────────────────────────────────────
    image_path = st.session_state.current_image_path
    if image_path and os.path.exists(image_path):
        st.image(
            image_path,
            width="stretch",
            caption=f"Scene {st.session_state.scene_index}  ·  "
                    f"{ui.MOOD_THEMES.get(mood, {}).get('label', mood)}",
        )
    else:
        # No image available — render a themed placeholder
        theme = ui.MOOD_THEMES.get(mood, ui.MOOD_THEMES["neutral"])
        st.markdown(f"""
        <div style="
            width:100%;height:200px;
            background:linear-gradient(135deg, {theme['bg_start']}, {theme['bg_end']});
            border:1px solid {theme['border']};
            border-radius:12px;
            display:flex;align-items:center;justify-content:center;
            font-size:1.2rem;color:{theme['text_sub']};
            margin-bottom:12px;
        ">
            🖼️ &nbsp; Scene image generating…
        </div>
        """, unsafe_allow_html=True)

    # ── Story text card ───────────────────────────────────────────────────────
    story_text = st.session_state.current_story_text
    mood_label = ui.MOOD_THEMES.get(mood, {}).get("label", mood)
    st.markdown(
        f'<div class="story-card">'
        f'<span class="mood-badge">{mood_label}</span>'
        f"<p style='margin-top:12px;'>{story_text}</p>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── Audio player ──────────────────────────────────────────────────────────
    audio_path = st.session_state.current_audio_path
    if audio_path and os.path.exists(audio_path):
        # Determine MIME type
        mime = "audio/mpeg" if audio_path.endswith(".mp3") else "audio/wav"
        st.audio(audio_path, format=mime)

    # ── Director's Commentary ─────────────────────────────────────────────────
    commentary = st.session_state.current_commentary
    if st.session_state.show_commentary and commentary:
        with st.expander("🎬 Director's Commentary", expanded=False):
            st.markdown(
                f"<i style='color:#aaa;font-size:0.9rem;'>{commentary}</i>",
                unsafe_allow_html=True,
            )

    # ── Scene stats row ───────────────────────────────────────────────────────
    scene_idx = st.session_state.scene_index
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.caption(f"📍 Scene {scene_idx}")
    with col_b:
        st.caption(f"🎭 Speaker: {st.session_state.current_speaker.title()}")
    with col_c:
        st.caption(f"❤️ Trust: {st.session_state.trust_score}/100")

    st.divider()

    # ── ENDING STATE ─────────────────────────────────────────────────────────
    if st.session_state.is_ending:
        st.markdown("""
        <div style="
            text-align:center;
            padding:30px;
            background:rgba(0,0,0,0.6);
            border-radius:16px;
            border:1px solid #555;
        ">
            <div style="font-size:2rem;margin-bottom:10px;">🎊</div>
            <div style="color:#ffd700;font-size:1.3rem;font-weight:bold;">
                Story Complete
            </div>
            <div style="color:#aaa;font-size:0.9rem;margin-top:8px;">
                Your choices shaped this ending. Try again to discover more.
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Play Again", width="stretch", type="primary"):
            saved_endings = st.session_state.endings_unlocked.copy()
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            ss.init_state()
            st.session_state.endings_unlocked = saved_endings
            st.rerun()
        return  # Don't render choice buttons after ending

    # ── CHOICE BUTTONS ────────────────────────────────────────────────────────
    # WHY a for-loop with dynamic buttons (not st.chat_input):
    #   Choices are defined by the Gemini JSON (2-4 per scene).
    #   Dynamic buttons give click-to-advance UX matching visual novel conventions.
    #   Each button has a unique key including scene_index to prevent Streamlit
    #   key conflicts across reruns.

    options = st.session_state.current_options
    st.markdown(
        "<div style='color:#888;font-size:0.78rem;font-weight:bold;"
        "letter-spacing:0.1em;margin-bottom:10px;'>YOUR CHOICE</div>",
        unsafe_allow_html=True,
    )

    if options:
        # Voice input (bonus feature — behind ENABLE_VOICE_INPUT flag)
        if ENABLE_VOICE_INPUT and st.session_state.voice_input_enabled:
            _render_voice_input()

        # Render one button per option
        for i, option in enumerate(options):
            btn_key = f"choice_{scene_idx}_{i}"
            if st.button(
                f"▶  {option}",
                key=btn_key,
                width="stretch",
            ):
                # Disable further clicks while processing
                with st.spinner("Continuing the story…"):
                    process_choice(option)
                st.rerun()

    else:
        st.info("Waiting for story options… try refreshing.")

    # ── STORY MAP ─────────────────────────────────────────────────────────────
    if st.session_state.show_story_map:
        st.divider()
        st.markdown(
            "<div style='color:#888;font-size:0.78rem;font-weight:bold;"
            "letter-spacing:0.1em;margin-bottom:8px;'>🗺️ YOUR STORY MAP</div>",
            unsafe_allow_html=True,
        )
        ui.render_story_map(
            st.session_state.story_nodes,
            st.session_state.story_edges,
        )


# ─────────────────────────────────────────────────────────────────────────────
# VOICE INPUT (bonus feature)
# ─────────────────────────────────────────────────────────────────────────────

def _render_voice_input() -> None:
    """
    Full voice input pipeline:
      1. mic_recorder captures audio from the browser mic in WAV format
      2. WAV bytes → io.BytesIO → sr.AudioFile → sr.Recognizer.record()
         This is the correct SpeechRecognition path for file-based audio.
      3. recognize_google() sends FLAC-encoded audio to Google's free endpoint
      4. Transcription shown → user confirms → process_choice() advances story

    WHY WAV, not WebM:
      sr.AudioData(bytes, rate, width) expects raw PCM (uncompressed) bytes.
      WebM is a compressed container — passing it as raw PCM corrupts the signal
      and causes garbled or empty transcriptions.
      Using format='wav' + sr.AudioFile(BytesIO(...)) lets SpeechRecognition parse
      the WAV header correctly and extract clean PCM before sending to Google.

    NO API KEY NEEDED:
      recognize_google() uses Google's public Speech Recognition endpoint.
      PyAudio is also NOT required — we read from BytesIO, not a microphone stream.
    """
    try:
        from streamlit_mic_recorder import mic_recorder
    except ImportError:
        st.caption("Voice input: run `pip install streamlit-mic-recorder`")
        return

    st.markdown(
        "<div style='color:#8ab4d8;font-size:0.82rem;font-weight:bold;"
        "letter-spacing:0.05em;margin:12px 0 6px;'>"
        "🎙️ SPEAK YOUR CHOICE</div>",
        unsafe_allow_html=True,
    )

    # Key for persisting the transcript while the user decides
    scene_idx   = st.session_state.scene_index
    pending_key = f"voice_transcript_{scene_idx}"

    # ── Capture new audio ────────────────────────────────────────────────────
    audio_data = mic_recorder(
        start_prompt="🔴  Start Recording",
        stop_prompt="⏹️  Stop",
        just_once=True,
        format="wav",
        key=f"mic_{scene_idx}",
    )

    # ── Transcribe fresh audio when it arrives ────────────────────────────────
    if audio_data:
        audio_bytes = audio_data.get("bytes", b"")
        if not audio_bytes or len(audio_bytes) < 200:
            st.warning("Recording seems empty -- please speak and try again.")
        else:
            st.audio(audio_bytes, format="audio/wav")
            try:
                import io
                import speech_recognition as sr
                r = sr.Recognizer()
                r.dynamic_energy_threshold = True
                with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
                    r.adjust_for_ambient_noise(source, duration=0.3)
                    audio_obj = r.record(source)
                with st.spinner("🎙️ Transcribing..."):
                    transcribed = r.recognize_google(audio_obj)
                # Store so the Use button survives the next rerun
                st.session_state[pending_key] = transcribed
            except ImportError:
                st.info("Run `pip install SpeechRecognition` to enable transcription.")
            except Exception as e:
                err = str(e).lower()
                if "unknown value" in err or "could not understand" in err:
                    st.warning("Couldn't understand -- speak clearly and try again.")
                elif "request error" in err or "connection" in err:
                    st.warning("Google Speech API unreachable. Check your internet.")
                else:
                    st.warning(f"Voice error: {e}. Use the buttons above instead.")

    # ── Show confirm/discard whenever a transcript is stored ──────────────────
    if pending_key in st.session_state:
        transcribed = st.session_state[pending_key]
        st.success(f'🎙️ Heard: **"{transcribed}"**')
        short    = transcribed[:60] + ("..." if len(transcribed) > 60 else "")
        col_use, col_discard = st.columns([3, 1])
        with col_use:
            if st.button(
                f'✅  Use: "{short}"',
                key=f"voice_use_{scene_idx}",
                type="primary",
            ):
                text = st.session_state.pop(pending_key)
                with st.spinner("Continuing the story..."):
                    process_choice(text)
                st.rerun()
        with col_discard:
            if st.button("🗑️ Discard", key=f"voice_discard_{scene_idx}"):
                st.session_state.pop(pending_key, None)
                st.rerun()
    elif not audio_data:
        st.caption("Click **Start Recording**, speak your choice, then click **Stop**.")




# ═════════════════════════════════════════════════════════════════════════════
# MAIN ROUTER
# ═════════════════════════════════════════════════════════════════════════════

def main() -> None:
    """
    Top-level router. Decides which screen to show based on session_state.
    Sidebar is always rendered first (it's page-persistent in Streamlit).
    """
    render_sidebar()

    if not st.session_state.game_started:
        render_landing_screen()
    else:
        render_story_screen()


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__" or True:
    # WHY `or True`: Streamlit doesn't use __name__ == "__main__" — it imports
    # the module directly. The `or True` ensures main() always runs.
    main()
