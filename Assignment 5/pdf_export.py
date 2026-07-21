"""
pdf_export.py
=============
Exports the player's full story playthrough as a beautifully
formatted PDF using fpdf2 (FPDF v2.x).

WHAT IT PRODUCES:
  - Cover page with genre and session date
  - One section per scene:
      • Scene number + mood badge
      • Scene image (if available, or a mood-colored placeholder rect)
      • Full story text
      • Player's choice (if not the final scene)
  - Final page with trust score + endings unlocked

WHY fpdf2 INSTEAD OF reportlab:
  fpdf2 is pip-installable with zero system dependencies and has a
  simpler API for this use case. reportlab requires C extensions
  that can be tricky on Windows.

LATIN-1 CONSTRAINT & THE _safe() FUNCTION:
  fpdf2's built-in core fonts (Helvetica, Times, Courier) are encoded
  in Latin-1 / cp1252. Any character outside that range — em-dash (—),
  curly quotes, ellipsis (…), checkmarks (✓), bullets (●) — causes
  FPDFUnicodeEncodingException.

  THE FIX: Every string that goes into a cell() or multi_cell() call
  is first passed through _safe(), which replaces known Unicode
  characters with their closest Latin-1 equivalents. This is applied
  ONCE centrally so it's impossible to miss a callsite.

  Alternative (using a TTF font) was considered but rejected because
  it requires shipping a font file — adding a dependency. The _safe()
  approach is zero-dependency and transparent.

IMAGE HANDLING:
  fpdf2's image() method accepts file paths. We use the stored
  local image paths from session_state.story_history. If a scene
  has no image (None), we draw a filled color rectangle as a visual
  placeholder matching the scene's mood color.
"""

import os
from datetime import datetime

# Lazy import — fpdf2 might not be installed in minimal environments
try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────────────
# MOOD → COLOR PALETTE (RGB tuples for PDF styling)
# ─────────────────────────────────────────────────────────────────────────────
MOOD_COLORS: dict[str, tuple[int, int, int]] = {
    "tense":      (180, 30,  30),
    "joyful":     (255, 180, 50),
    "mysterious": (100, 50,  180),
    "neutral":    (100, 130, 160),
    "triumphant": (220, 170, 30),
}
DEFAULT_COLOR = (100, 130, 160)

# Page dimensions (A4 in mm)
PAGE_W = 210
PAGE_H = 297
MARGIN = 15
CONTENT_W = PAGE_W - 2 * MARGIN

# ─────────────────────────────────────────────────────────────────────────────
# UNICODE → LATIN-1 SANITIZER
# WHY: fpdf2 core fonts (Helvetica) only support Latin-1. Any character
# outside that range raises FPDFUnicodeEncodingException. We map every
# commonly-seen Unicode character to the closest ASCII/Latin-1 equivalent,
# then fall back to encode("latin-1", "replace") for anything else.
# Applied to EVERY string before it touches fpdf2 — see every cell() call.
# ─────────────────────────────────────────────────────────────────────────────
_UNICODE_MAP = str.maketrans({
    # Dashes
    "\u2014": "--",   # em dash  —
    "\u2013": "-",    # en dash  –
    "\u2012": "-",    # figure dash
    # Quotes
    "\u201c": '"',    # left double quote  "
    "\u201d": '"',    # right double quote "
    "\u2018": "'",    # left single quote  '
    "\u2019": "'",    # right single quote '
    "\u201a": ",",    # single low-9 quote ‚
    "\u00ab": '"',    # left angle quote  «
    "\u00bb": '"',    # right angle quote »
    # Ellipsis / bullets
    "\u2026": "...",  # ellipsis …
    "\u2022": "*",    # bullet •
    "\u25cf": "*",    # black circle ●
    "\u25cb": "o",    # white circle ○
    "\u25ba": ">",    # right pointer ►
    # Symbols
    "\u2713": "[OK]", # check mark ✓
    "\u2717": "[X]",  # ballot X ✗
    "\u00b7": ".",    # middle dot ·
    "\u2192": "->",   # right arrow →
    "\u00a9": "(c)",  # copyright ©
    "\u00ae": "(R)",  # registered ®
    "\u2122": "(TM)", # trademark ™
    # Spaces
    "\u00a0": " ",    # non-breaking space
    "\u2009": " ",    # thin space
    "\u200b": "",     # zero-width space
    # Misc
    "\u0152": "OE",   # Ligature OE Œ
    "\u0153": "oe",   # ligature oe œ
})


def _safe(text: str) -> str:
    """
    Convert a Unicode string to a fpdf2-safe Latin-1 string.
    1. Replace known special chars with ASCII equivalents via translation table
    2. Encode to latin-1 with 'replace' fallback for anything still outside range
    This is the single choke-point for all text entering fpdf2.
    """
    if not text:
        return ""
    # Step 1: replace known chars
    text = text.translate(_UNICODE_MAP)
    # Step 2: encode→decode to strip anything still outside Latin-1
    return text.encode("latin-1", errors="replace").decode("latin-1")


# ─────────────────────────────────────────────────────────────────────────────
# PDF CLASS
# ─────────────────────────────────────────────────────────────────────────────

class StoryPDF(FPDF):
    """
    Custom FPDF subclass with shared header/footer and helper methods.
    Subclassing is the fpdf2 way to add per-page decorations.
    All text passed to fpdf2 methods must go through _safe() first.
    """

    def __init__(self, genre: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        # _safe() on genre so any special char in genre name is handled too
        self.genre = _safe(genre.upper())
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(MARGIN, MARGIN, MARGIN)

    def header(self):
        """Thin colored header bar on every page."""
        self.set_fill_color(20, 20, 35)
        self.rect(0, 0, PAGE_W, 10, style="F")
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(180, 180, 220)
        self.set_y(2)
        # _safe() applied: the em-dash in the original was the crash culprit
        self.cell(0, 6, _safe(f"MirAI Visual Novel - {self.genre}"), align="C")
        self.set_text_color(0, 0, 0)

    def footer(self):
        """Page number footer."""
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(150, 150, 150)
        self.cell(0, 5, _safe(f"Page {self.page_no()}"), align="C")
        self.set_text_color(0, 0, 0)

    def mood_badge(self, mood: str, x: float, y: float) -> None:
        """Draw a small colored pill badge labeling the scene mood."""
        color = MOOD_COLORS.get(mood, DEFAULT_COLOR)
        self.set_fill_color(*color)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 8)
        self.set_xy(x, y)
        self.cell(30, 6, _safe(f" {mood.upper()} "), border=0, align="C", fill=True)
        self.set_text_color(0, 0, 0)

    def scene_image(self, image_path: str | None, mood: str) -> None:
        """
        Render a scene image or a mood-colored placeholder rectangle.
        Keeps image width fixed at CONTENT_W and scales height proportionally.
        """
        img_h = 70  # fixed height in mm for consistent layout

        if image_path and os.path.exists(image_path):
            try:
                self.image(image_path, x=MARGIN, w=CONTENT_W, h=img_h)
                self.ln(img_h + 3)
                return
            except Exception:
                pass  # Fall through to placeholder

        # Placeholder: filled rectangle with mood color + label
        color = MOOD_COLORS.get(mood, DEFAULT_COLOR)
        self.set_fill_color(*color)
        self.set_draw_color(*color)
        y_pos = self.get_y()
        self.rect(MARGIN, y_pos, CONTENT_W, img_h, style="F")
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 14)
        self.set_xy(MARGIN, y_pos + img_h / 2 - 5)
        self.cell(CONTENT_W, 10, _safe(f"[ {mood.upper()} ]"), align="C")
        self.set_text_color(0, 0, 0)
        self.ln(img_h + 5)


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC BUILD FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def build_pdf(
    story_history: list[dict],
    genre: str,
    trust_score: int,
    endings_unlocked: set,
    total_endings: int,
) -> bytes | None:
    """
    Build and return the PDF as raw bytes for st.download_button().

    Returns None if fpdf2 is not installed (caller shows a toast).

    story_history entries expected format:
      {
        "scene_index": int,
        "story_text":  str,
        "choice_made": str | None,
        "image_path":  str | None,
        "mood":        str,
      }
    """
    if not FPDF_AVAILABLE:
        return None

    try:
        pdf = StoryPDF(genre=genre)

        # ── COVER PAGE ────────────────────────────────────────────────────────
        pdf.add_page()
        pdf.set_fill_color(10, 10, 25)
        pdf.rect(0, 0, PAGE_W, PAGE_H, style="F")

        # Title
        pdf.set_y(60)
        pdf.set_font("Helvetica", "B", 28)
        pdf.set_text_color(200, 180, 255)
        pdf.cell(0, 15, _safe("MirAI Visual Novel"), align="C", new_x="LMARGIN", new_y="NEXT")

        # Genre
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(150, 220, 255)
        pdf.cell(0, 10, _safe(genre.upper()), align="C", new_x="LMARGIN", new_y="NEXT")

        # Subtitle
        pdf.set_font("Helvetica", "I", 12)
        pdf.set_text_color(180, 180, 200)
        pdf.ln(5)
        pdf.cell(0, 8, _safe("A Personalized Story Playthrough"), align="C", new_x="LMARGIN", new_y="NEXT")

        # Date
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(120, 120, 150)
        pdf.ln(5)
        pdf.cell(0, 8, _safe(datetime.now().strftime("%B %d, %Y")), align="C", new_x="LMARGIN", new_y="NEXT")

        # Trust score on cover
        pdf.ln(20)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(200, 200, 100)
        pdf.cell(0, 8, _safe(f"Final Trust Score: {trust_score}/100"), align="C", new_x="LMARGIN", new_y="NEXT")
        if endings_unlocked:
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(150, 200, 150)
            ending_list = ", ".join(f"Ending {e}" for e in sorted(endings_unlocked))
            pdf.cell(0, 7, _safe(f"Endings Unlocked: {ending_list}"), align="C", new_x="LMARGIN", new_y="NEXT")

        pdf.set_text_color(0, 0, 0)

        # ── STORY SCENES ──────────────────────────────────────────────────────
        for entry in story_history:
            pdf.add_page()
            scene_num  = entry.get("scene_index", 0)
            story_text = entry.get("story_text", "")
            choice     = entry.get("choice_made")
            img_path   = entry.get("image_path")
            mood       = entry.get("mood", "neutral")

            # Scene header bar
            color = MOOD_COLORS.get(mood, DEFAULT_COLOR)
            pdf.set_fill_color(*[min(c + 180, 255) for c in color])
            pdf.rect(MARGIN, 12, CONTENT_W, 10, style="F")
            pdf.set_xy(MARGIN, 12)
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(20, 20, 40)
            pdf.cell(CONTENT_W - 35, 10, _safe(f"Scene {scene_num + 1}"), border=0)
            pdf.mood_badge(mood, x=PAGE_W - MARGIN - 35, y=12)
            pdf.ln(14)

            # Scene image (or mood-colored placeholder)
            pdf.scene_image(img_path, mood)

            # Story text — _safe() handles any Unicode from Gemini
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(CONTENT_W, 6, _safe(story_text))

            # Player choice callout box
            if choice:
                pdf.ln(5)
                pdf.set_fill_color(230, 240, 255)
                pdf.set_draw_color(100, 130, 200)
                pdf.set_font("Helvetica", "I", 10)
                pdf.set_text_color(60, 80, 150)
                pdf.multi_cell(
                    CONTENT_W, 7,
                    _safe(f'  Player chose: "{choice}"'),
                    border=1, fill=True,
                )
                pdf.set_text_color(0, 0, 0)

        # ── SUMMARY PAGE ──────────────────────────────────────────────────────
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(60, 40, 100)
        pdf.ln(10)
        pdf.cell(0, 10, _safe("Playthrough Summary"), align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(5)

        pdf.set_font("Helvetica", "", 12)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(0, 8, _safe(f"Total Scenes: {len(story_history)}"), new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8, _safe(f"Final Trust Score: {trust_score}/100"), new_x="LMARGIN", new_y="NEXT")
        pdf.cell(0, 8,
                 _safe(f"Endings Unlocked: {len(endings_unlocked)} / {total_endings}"),
                 new_x="LMARGIN", new_y="NEXT")

        if endings_unlocked:
            pdf.ln(3)
            for eid in sorted(endings_unlocked):
                pdf.set_font("Helvetica", "B", 11)
                pdf.set_text_color(80, 150, 80)
                # ASCII [OK] replaces the ✓ checkmark that caused crashes
                pdf.cell(0, 7, _safe(f"  [OK] Ending {eid} Unlocked"), new_x="LMARGIN", new_y="NEXT")

        remaining = set(range(1, total_endings + 1)) - endings_unlocked
        if remaining:
            pdf.ln(3)
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(150, 100, 100)
            for eid in sorted(remaining):
                # ASCII "o" replaces ○, "--" replaces em-dash —
                pdf.cell(0, 6, _safe(f"  o  Ending {eid} -- Undiscovered"), new_x="LMARGIN", new_y="NEXT")

        # ── OUTPUT ────────────────────────────────────────────────────────────
        return bytes(pdf.output())

    except Exception:
        # Last-resort safety net — never let PDF errors crash the Streamlit app
        return None
