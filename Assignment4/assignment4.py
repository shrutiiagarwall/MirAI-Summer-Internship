import streamlit as st
import requests
import urllib.parse
import random
import json
import os
from datetime import datetime
from dotenv import load_dotenv  

load_dotenv()  # loads .env file into os.environ

# ---------------- Gemini Setup (safe, with fallback) ----------------
GEMINI_AVAILABLE = False
try:
    import google.generativeai as genai
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") 
    if not GEMINI_API_KEY:
        try:
            GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", None)
        except Exception:
            GEMINI_API_KEY = None
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

st.title("MY AI IMAGE GENERATOR")

# ---------------- Session State Init ----------------
if "gallery" not in st.session_state:
    st.session_state.gallery = []
if "favorites" not in st.session_state:
    st.session_state.favorites = []
if "battle_votes" not in st.session_state:
    st.session_state.battle_votes = {"A": 0, "B": 0}
if "width" not in st.session_state:
    st.session_state.width = 768
if "height" not in st.session_state:
    st.session_state.height = 768

# ---------------- Style Presets with Negative Prompts ----------------
STYLE_NEGATIVE_PROMPTS = {
    "Photorealistic": "no cartoon, no illustration, no blurry, no distorted faces",
    "Anime": "no photorealistic, no 3d render, no blurry",
    "Vintage Victorian": "no modern elements, no neon, no futuristic objects",
    "Sketch": "no color, no photorealistic, no 3d render",
    "3D Render": "no flat design, no 2d, no sketch lines"
}

LOADING_MESSAGES = [
    "Mixing colors on the AI palette...",
    "Consulting the digital muse...",
    "Rendering pixels into art...",
    "Teaching robots to paint..."
]

SURPRISE_PROMPTS = [
    "An astronaut riding a horse on Mars",
    "A cyberpunk street food vendor in Tokyo",
    "A dragon made entirely of stained glass, flying over a medieval city",
    "A robot barista serving coffee in a floating sky cafe",
    "A underwater library guarded by glowing jellyfish"
]

# ---------------- Sidebar Settings ----------------
st.sidebar.header("SETTINGS")

art_style = st.sidebar.selectbox(
    "Select desired Art Style",
    ["Photorealistic", "Anime", "Vintage Victorian", "Sketch", "3D Render"]
)
st.sidebar.caption(f"🚫 Auto negative prompt: {STYLE_NEGATIVE_PROMPTS[art_style]}")

# Aspect Ratio Presets
st.sidebar.write("Quick Aspect Ratio")
def set_aspect(w, h):
    st.session_state.width = w
    st.session_state.height = h

p1, p2, p3 = st.sidebar.columns(3)
p1.button("⬛ Square", on_click=set_aspect, args=(768, 768))
p2.button("📱 Portrait", on_click=set_aspect, args=(576, 1024))
p3.button("🖥️ Landscape", on_click=set_aspect, args=(1024, 576))

width = st.sidebar.slider("Image width", min_value=256, max_value=1024, step=32, key="width")
height = st.sidebar.slider("Image height", min_value=256, max_value=1024, step=32, key="height")

magic_enhance = st.sidebar.checkbox("✨ Enable Magic Enhance (AI-Powered)")
if GEMINI_AVAILABLE:
    st.sidebar.caption("🟢 Gemini connected — AI enhancement active")
else:
    st.sidebar.caption("🟡 Gemini not connected — using static enhancement")

# ---------------- Helper Functions ----------------
def build_image_url(prompt_text, w, h, model="flux"):
    encoded = urllib.parse.quote(prompt_text)
    return (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width={w}&height={h}&model={model}&nologo=true&referrer=streamlit_ai_studio"
    )

def fetch_image(prompt_text, w, h):
    """Try flux first, fall back to turbo if flux is unavailable."""
    for model_name in ["flux", "turbo"]:
        url = build_image_url(prompt_text, w, h, model=model_name)
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                return response
        except requests.exceptions.RequestException:
            continue
    return response  # returns last failed response if both fail

def get_enhanced_prompt(base_prompt):
    static_boost = ", detailed, high quality" 
    if not GEMINI_AVAILABLE:
        return base_prompt + static_boost
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(
            f"Rewrite this AI image prompt to be more vivid, under 15 words, "
            f"no quotes, no extra text: {base_prompt}"
        )
        enhanced = response.text.strip()
        return enhanced if enhanced else base_prompt + static_boost
    except Exception:
        return base_prompt + static_boost

def get_battle_versions(base_prompt):
    if GEMINI_AVAILABLE:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            instruction = (
                "Create two DIFFERENT short vivid rewrites (under 12 words each) of this image prompt. "
                f"Original prompt: {base_prompt}\n"
                'Respond ONLY with valid JSON, no markdown: {"version_a": "...", "version_b": "..."}'
            )
            response = model.generate_content(instruction)
            text = response.text.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(text)
            return data.get("version_a", base_prompt), data.get("version_b", base_prompt)
        except Exception:
            pass
    return (
        f"{base_prompt}, cinematic style", 
        f"{base_prompt}, fantasy style"
    )

def add_to_gallery(image_bytes, prompt_text, style, w, h):
    st.session_state.gallery.insert(0, {
        "image": image_bytes,
        "prompt": prompt_text,
        "style": style,
        "width": w,
        "height": h,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    })

def display_result(image_bytes, full_prompt, style, w, h):
    st.success("Image Generated")
    st.image(image_bytes, caption=full_prompt)
    st.code(full_prompt, language=None)  # built-in copy icon
    st.caption(f"📐 {w}x{h} | 🎨 {style} | 🕒 {datetime.now().strftime('%H:%M:%S')}")
    st.download_button(
        label="Download Image",
        data=image_bytes,
        file_name=f"{style}_image.png",
        mime="image/png"
    )
    add_to_gallery(image_bytes, full_prompt, style, w, h)
    st.balloons()

# ---------------- Main UI ----------------
user_prompt = st.text_input("Decribe the image you want to generate")

word_count = len(user_prompt.split()) if user_prompt else 0
st.caption(f"Word count: {word_count}")
if 0 < word_count < 3:
    st.warning("Try adding more details for better results!")

col1, col2, col3 = st.columns(3)
with col1:
    generate_clicked = st.button("Generate Image")
with col2:
    surprise_clicked = st.button("🎲 Surprise Me!")
with col3:
    battle_clicked = st.button("⚔️ Prompt Battle")

compare_clicked = st.button("🔍 Compare With/Without Enhance")

# ---------------- Generate Image ----------------
if generate_clicked:
    if user_prompt:
        with st.spinner(random.choice(LOADING_MESSAGES)):
            negative = STYLE_NEGATIVE_PROMPTS.get(art_style, "")
            base_prompt = f"{user_prompt}, {art_style} style"
            full_prompt = get_enhanced_prompt(base_prompt) if magic_enhance else base_prompt
            response = fetch_image(full_prompt, width, height)
            if response.status_code == 200:
                display_result(response.content, full_prompt, art_style, width, height)
            else:
                st.error(f"API is not working — Status Code: {response.status_code}")
                st.code(response.text[:500])  # shows the actual error message from server
    else:
        st.warning("Please add an image description.")

# ---------------- Surprise Me ----------------
if surprise_clicked:
    with st.spinner(random.choice(LOADING_MESSAGES)):
        random_prompt = random.choice(SURPRISE_PROMPTS)
        st.info(f"Surprise prompt: {random_prompt}")
        negative = STYLE_NEGATIVE_PROMPTS.get(art_style, "")
        base_prompt = f"{random_prompt}, make the art style: {art_style}, avoid: {negative}"
        full_prompt = get_enhanced_prompt(base_prompt) if magic_enhance else base_prompt
        response = fetch_image(full_prompt, width, height)
        if response.status_code == 200:
            display_result(response.content, full_prompt, art_style, width, height)
        else:
            st.error("API is not working")

# ---------------- Compare With/Without Enhance ----------------
if compare_clicked:
    if user_prompt:
        with st.spinner("Generating comparison..."):
            base_prompt = f"{user_prompt}, make the art style: {art_style}"
            enhanced_prompt = get_enhanced_prompt(base_prompt)

            respA = fetch_image(base_prompt, width, height)
            respB = fetch_image(enhanced_prompt, width, height)

            colA, colB = st.columns(2)
            with colA:
                st.subheader("Without Enhance")
                if respA.status_code == 200:
                    st.image(respA.content)
                else:
                    st.error("Failed to generate")
            with colB:
                st.subheader("With Magic Enhance")
                if respB.status_code == 200:
                    st.image(respB.content)
                else:
                    st.error("Failed to generate")
    else:
        st.warning("Please add an image description.")

# ---------------- Prompt Battle (A/B Duel) ----------------
if battle_clicked:
    if user_prompt:
        with st.spinner("Preparing the battle..."):
            version_a, version_b = get_battle_versions(user_prompt)
            full_a = f"{version_a}, make the art style: {art_style}"
            full_b = f"{version_b}, make the art style: {art_style}"

            respA = fetch_image(full_a, width, height)
            respB = fetch_image(full_b, width, height)

            colA, colB = st.columns(2)
            with colA:
                st.subheader("Version A")
                if respA.status_code == 200:
                    st.image(respA.content, caption=full_a)
                    if st.button("Vote A", key="vote_a"):
                        st.session_state.battle_votes["A"] += 1
                else:
                    st.error("Failed to generate")
            with colB:
                st.subheader("Version B")
                if respB.status_code == 200:
                    st.image(respB.content, caption=full_b)
                    if st.button("Vote B", key="vote_b"):
                        st.session_state.battle_votes["B"] += 1
                else:
                    st.error("Failed to generate")

            st.caption(f"🗳️ Votes — A: {st.session_state.battle_votes['A']} | B: {st.session_state.battle_votes['B']}")
    else:
        st.warning("Please add an image description.")

# ---------------- Gallery (Session History) ----------------
if st.session_state.gallery:
    st.divider()
    st.subheader("🖼️ Your Session Gallery")
    cols = st.columns(4)
    for idx, item in enumerate(st.session_state.gallery):
        with cols[idx % 4]:
            st.image(item["image"], width=150)
            st.caption(f"{item['style']} | {item['timestamp']}")
            if st.button("❤️ Save", key=f"fav_{idx}"):
                if item not in st.session_state.favorites:
                    st.session_state.favorites.append(item)
                    st.toast("Added to favorites!")

# ---------------- Favorites ----------------
if st.session_state.favorites:
    st.divider()
    with st.expander(f"⭐ Favorites ({len(st.session_state.favorites)})"):
        fav_cols = st.columns(4)
        for idx, item in enumerate(st.session_state.favorites):
            with fav_cols[idx % 4]:
                st.image(item["image"], width=150)
                st.caption(f"{item['style']} | {item['timestamp']}")