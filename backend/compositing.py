from PIL import Image, ImageDraw, ImageFont
import os
import io

# ── Layout constants — never derived from content ─────────────────────────────
IMAGE_SIZE      = (1080, 1080)

LOGO_SIZE       = (120, 120)
LOGO_MARGIN     = 30
LOGO_POS        = (IMAGE_SIZE[0] - LOGO_SIZE[0] - LOGO_MARGIN, LOGO_MARGIN)  # top-right

TITLE_FONT_SIZE = 48
TITLE_Y         = 740          # fixed y-coordinate of title band top
TITLE_LINE_H    = 68           # fixed line-height regardless of content
TITLE_MAX_LINES = 2
TITLE_MAX_W     = 900          # max pixel width before wrapping
TITLE_X_CENTER  = IMAGE_SIZE[0] // 2
TITLE_COLOR     = (255, 255, 255)

_DIR            = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH   = os.path.join(_DIR, "templates", "post_template.png")
LOGO_PATH       = os.path.join(_DIR, "templates", "logo.png")

_FONT_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/verdanab.ttf",
    "C:/Windows/Fonts/verdana.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def _load_font(size: int):
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _text_w(draw, text, font) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


# ── Placeholder asset generation ──────────────────────────────────────────────

def _ensure_template() -> None:
    if os.path.exists(TEMPLATE_PATH):
        return
    os.makedirs(os.path.dirname(TEMPLATE_PATH), exist_ok=True)

    img = Image.new("RGBA", IMAGE_SIZE, (18, 26, 58, 255))   # deep navy
    draw = ImageDraw.Draw(img)

    # Dark panel for the title band
    draw.rectangle([(0, 690), (IMAGE_SIZE[0], IMAGE_SIZE[1])], fill=(10, 16, 38, 255))
    # Gold separator line
    draw.rectangle([(60, 686), (IMAGE_SIZE[0] - 60, 692)], fill=(200, 160, 40, 255))

    # Brand name top-left
    font = _load_font(30)
    draw.text((44, 38), "Mysoft Heaven", font=font, fill=(200, 160, 40, 220))

    img.save(TEMPLATE_PATH, format="PNG")
    print(f"[compositing] Generated placeholder template -> {TEMPLATE_PATH}")


def _ensure_logo() -> None:
    if os.path.exists(LOGO_PATH):
        return
    os.makedirs(os.path.dirname(LOGO_PATH), exist_ok=True)

    # Generate at 2x for quality, then resize down
    gen_size = 240
    img = Image.new("RGBA", (gen_size, gen_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    draw.ellipse([(0, 0), (gen_size - 1, gen_size - 1)], fill=(200, 160, 40, 255))

    font = _load_font(84)
    bbox = draw.textbbox((0, 0), "MH", font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((gen_size - tw) // 2, (gen_size - th) // 2 - 4), "MH",
              font=font, fill=(18, 26, 58, 255))

    img.save(LOGO_PATH, format="PNG")
    print(f"[compositing] Generated placeholder logo    -> {LOGO_PATH}")


# ── Word-wrap with fixed ellipsis truncation ──────────────────────────────────

def _break_long_word(draw, word: str, font, max_w: int) -> list:
    """Break a single word that is wider than max_w into character chunks
    that each fit. Guarantees no token can overflow the card width."""
    if _text_w(draw, word, font) <= max_w:
        return [word]
    pieces, cur = [], ""
    for ch in word:
        if _text_w(draw, cur + ch, font) <= max_w or not cur:
            cur += ch
        else:
            pieces.append(cur)
            cur = ch
    if cur:
        pieces.append(cur)
    return pieces


def _wrap(draw, text: str, font, max_w: int, max_lines: int) -> list:
    # Expand each word; any word wider than max_w is broken at the character
    # level first, so the wrap loop below only ever sees tokens that fit.
    words = []
    for w in text.split():
        words.extend(_break_long_word(draw, w, font, max_w))

    lines = []
    current = []

    for word in words:
        candidate = " ".join(current + [word])
        if _text_w(draw, candidate, font) <= max_w:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
                current = [word]
            else:
                lines.append(word)   # safety net — should not trigger now

    if current:
        lines.append(" ".join(current))

    if len(lines) <= max_lines:
        return lines

    # Truncate to max_lines, append ellipsis on the last line
    lines = lines[:max_lines]
    last = lines[-1]
    while last:
        trial = last + "..."
        if _text_w(draw, trial, font) <= max_w:
            lines[-1] = trial
            return lines
        parts = last.rsplit(" ", 1)
        if len(parts) == 1:
            break
        last = parts[0]
    lines[-1] = "..."
    return lines


# ── Public function ───────────────────────────────────────────────────────────

def compose_image(title: str) -> bytes:
    """Composite title onto brand card and return PNG bytes."""
    _ensure_template()
    _ensure_logo()

    card = Image.open(TEMPLATE_PATH).convert("RGBA")
    logo = Image.open(LOGO_PATH).convert("RGBA").resize(LOGO_SIZE, Image.LANCZOS)

    # Paste logo at fixed top-right coordinates
    card.paste(logo, LOGO_POS, logo)

    draw = ImageDraw.Draw(card)
    font = _load_font(TITLE_FONT_SIZE)
    lines = _wrap(draw, title, font, TITLE_MAX_W, TITLE_MAX_LINES)

    y = TITLE_Y
    for line in lines:
        w = _text_w(draw, line, font)
        x = TITLE_X_CENTER - w // 2
        draw.text((x, y), line, font=font, fill=TITLE_COLOR)
        y += TITLE_LINE_H

    out = io.BytesIO()
    card.convert("RGB").save(out, format="PNG")
    return out.getvalue()


