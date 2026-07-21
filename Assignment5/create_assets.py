"""
create_assets.py
================
One-time setup script to generate local fallback assets.
Run this ONCE before launching the app:

    python create_assets.py

Creates:
  assets/mood_joyful.png
  assets/mood_tense.png
  assets/mood_mysterious.png
  assets/mood_neutral.png
  assets/mood_triumphant.png
  assets/ambient.mp3      (short spoken placeholder via gTTS/edge-tts)

These files serve as fallback images/audio when Pollinations or TTS APIs
are unavailable. They are NOT meant to look polished — just functional.
"""

import os
import sys

# ─────────────────────────────────────────────────────────────────────────────
# DEPENDENCY CHECK
# ─────────────────────────────────────────────────────────────────────────────
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_OK = True
except ImportError:
    PIL_OK = False
    print("⚠️  Pillow not found. Install with: pip install Pillow")

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# MOOD IMAGE GENERATION
# Each image is a 768×512 gradient with the mood name overlaid.
# ─────────────────────────────────────────────────────────────────────────────
MOOD_GRADIENTS = {
    "joyful":     {"top": (255, 210, 80),  "bot": (255, 140, 30),  "emoji": "🌟"},
    "tense":      {"top": (160, 20,  20),  "bot": (60,  0,   10),  "emoji": "⚡"},
    "mysterious": {"top": (70,  20,  130), "bot": (15,  5,   50),  "emoji": "🌙"},
    "neutral":    {"top": (80,  110, 160), "bot": (40,  60,  100), "emoji": "⚪"},
    "triumphant": {"top": (220, 180, 30),  "bot": (140, 90,  0),   "emoji": "🏆"},
}

IMG_W, IMG_H = 768, 512


def lerp_color(c1: tuple, c2: tuple, t: float) -> tuple:
    """Linearly interpolate between two RGB colors."""
    return tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3))


def create_mood_image(mood: str, config: dict, output_path: str) -> None:
    """Generate a gradient PNG for a given mood."""
    img = Image.new("RGB", (IMG_W, IMG_H))
    draw = ImageDraw.Draw(img)

    # Vertical gradient
    for y in range(IMG_H):
        t = y / IMG_H
        color = lerp_color(config["top"], config["bot"], t)
        draw.line([(0, y), (IMG_W, y)], fill=color)

    # Semi-transparent overlay rectangle for text contrast
    overlay = Image.new("RGBA", (IMG_W, IMG_H), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    box_y = IMG_H // 2 - 55
    ov_draw.rectangle(
        [IMG_W // 4, box_y, 3 * IMG_W // 4, box_y + 110],
        fill=(0, 0, 0, 140)
    )
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # Mood emoji + text
    emoji_text = f"{config['emoji']}  {mood.upper()}"
    sub_text = "MirAI Visual Novel — Fallback Asset"

    # Try to load a font; fall back to PIL default
    try:
        font_large = ImageFont.truetype("arial.ttf", 42)
        font_small = ImageFont.truetype("arial.ttf", 18)
    except (IOError, OSError):
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Center text
    draw.text(
        (IMG_W // 2, IMG_H // 2 - 20),
        emoji_text,
        fill=(255, 255, 255),
        font=font_large,
        anchor="mm",
    )
    draw.text(
        (IMG_W // 2, IMG_H // 2 + 30),
        sub_text,
        fill=(200, 200, 200),
        font=font_small,
        anchor="mm",
    )

    img.save(output_path, "PNG")
    print(f"  [OK] Created {output_path}")


def create_all_mood_images() -> None:
    if not PIL_OK:
        print("  [SKIP] Skipping images - Pillow not installed.")
        return
    print("\n[IMG] Generating mood images...")
    for mood, config in MOOD_GRADIENTS.items():
        path = os.path.join(ASSETS_DIR, f"mood_{mood}.png")
        if os.path.exists(path):
            print(f"  [SKIP] {path} already exists.")
            continue
        create_mood_image(mood, config, path)


# ─────────────────────────────────────────────────────────────────────────────
# AMBIENT AUDIO GENERATION
# ─────────────────────────────────────────────────────────────────────────────

def create_ambient_audio() -> None:
    """
    Generate a short ambient audio clip as the TTS fallback.
    Tries edge-tts first (better quality), then gTTS, then skips.
    """
    output_path = os.path.join(ASSETS_DIR, "ambient.mp3")
    if os.path.exists(output_path):
        print(f"\n[SKIP] {output_path} already exists.")
        return

    print("\n[TTS] Generating ambient audio fallback...")
    ambient_text = (
        "Welcome to MirAI Visual Novel. "
        "Your story continues. "
        "The path ahead is yours to choose."
    )

    # Try edge-tts
    try:
        import asyncio
        import edge_tts

        async def _gen():
            c = edge_tts.Communicate(ambient_text, "en-US-AriaNeural")
            await c.save(output_path)

        asyncio.run(_gen())
        print(f"  [OK] Created {output_path} via edge-tts")
        return
    except Exception as e:
        print(f"  [INFO] edge-tts failed ({e}), trying gTTS...")

    # Try gTTS
    try:
        from gtts import gTTS
        tts = gTTS(text=ambient_text, lang="en")
        tts.save(output_path)
        print(f"  [OK] Created {output_path} via gTTS")
        return
    except Exception as e:
        print(f"  [FAIL] gTTS also failed ({e})")

    print("  [WARN] Ambient audio skipped - no TTS library available.")
    print("         Place any MP3 at assets/ambient.mp3 manually.")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("  MirAI Visual Novel - Asset Generator")
    print("=" * 50)
    create_all_mood_images()
    create_ambient_audio()
    print("\n[DONE] Assets ready! Run the app with:")
    print("   streamlit run app.py\n")
