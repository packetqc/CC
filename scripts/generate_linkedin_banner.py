#!/usr/bin/env python3
"""Generate LinkedIn profile banner — animated GIF + static PNG.

Modernist design: architectural data visualization of the knowledge project.
Captures actual project state as visual structure.

Dimensions: 1584×396 (LinkedIn recommended banner size).
Dual output: animated GIF (10 frames) + static PNG (first frame).
Dual theme: Cayman (light) + Midnight (dark).

Layout concept (modernist / brutalist typography):
  ┌────────────────────────────────────────────────────────────────────┐
  │ ▓▓▓▓ gradient accent bar ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │
  │                                                                    │
  │  [photo]  MARTIN PAQUET              ┌──────┐ ┌──────┐ ┌──────┐  │
  │           Network Security           │v25   │ │12    │ │6     │  │
  │           Embedded · AI · PQC        │KNOW  │ │PUBS  │ │MINDS │  │
  │                                      │LEDGE │ │      │ │      │  │
  │  ┌─ Read packetqc/knowledge ──┐      └──────┘ └──────┘ └──────┘  │
  │  └────────────────────────────┘                                    │
  │                                      ┌──────┐ ┌──────┐ ┌──────┐  │
  │  ❖ autosuffisant · autonome ·        │40    │ │9     │ │5     │  │
  │    concordant · concis ...           │WEB   │ │SESS  │ │DAYS  │  │
  │                                      │CARDS │ │IONS  │ │      │  │
  │                                      └──────┘ └──────┘ └──────┘  │
  │ ▓▓▓▓ gradient accent bar ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │
  └────────────────────────────────────────────────────────────────────┘

Right side: 6 metric blocks arranged in 2x3 grid, each with oversized number
and monospace label. One block highlights per frame (animated scan effect).
"""

from PIL import Image, ImageDraw, ImageFont
import os
import math

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(SCRIPT_DIR, '..', 'references', 'Martin')
REF_DIR = OUT_DIR
os.makedirs(OUT_DIR, exist_ok=True)

PHOTO_PATH = os.path.join(REF_DIR, 'me3.JPG')

# ---------------------------------------------------------------------------
# Fonts
# ---------------------------------------------------------------------------
FONT_BOLD = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
FONT_REGULAR = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONT_MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
FONT_SERIF = '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'

# ---------------------------------------------------------------------------
# Dimensions
# ---------------------------------------------------------------------------
W, H = 1584, 396

# ---------------------------------------------------------------------------
# Theme palettes — Cayman (light) + Midnight (dark)
# ---------------------------------------------------------------------------
THEMES = {
    'cayman': {
        'BG_TOP':        (239, 246, 255),   # #eff6ff  blue-50 (matches webcard Cayman)
        'BG_BOT':        (219, 234, 254),   # #dbeafe  blue-100
        'ACCENT_1':      (29, 78, 216),     # #1d4ed8  blue-700
        'ACCENT_2':      (59, 130, 246),    # #3b82f6  blue-500
        'ACCENT_3':      (2, 132, 199),     # #0284c7  sky-600
        'ACCENT_WARM':   (245, 158, 11),    # amber
        'TEXT_PRIMARY':  (15, 23, 42),      # dark slate
        'TEXT_MUTED':    (71, 85, 105),     # medium slate
        'TEXT_DIM':      (107, 114, 128),   # gray
        'BORDER':        (147, 197, 253),   # blue-200
        'BOX_BG':        (239, 246, 255),   # blue-50
        'CODE_BG':       (219, 234, 254),   # blue-100
        'METRIC_BG':     (224, 238, 255),   # light blue tint
        'METRIC_GLOW':   (59, 130, 246),    # blue-500 glow
    },
    'midnight': {
        'BG_TOP':        (15, 23, 42),      # #0f172a
        'BG_BOT':        (30, 27, 75),      # #1e1b4b
        'ACCENT_1':      (96, 165, 250),    # blue #60a5fa
        'ACCENT_2':      (167, 139, 250),   # purple #a78bfa
        'ACCENT_3':      (34, 211, 238),    # cyan #22d3ee
        'ACCENT_WARM':   (251, 191, 36),    # amber
        'TEXT_PRIMARY':  (226, 232, 240),   # light slate
        'TEXT_MUTED':    (148, 163, 184),   # medium slate
        'TEXT_DIM':      (100, 116, 139),   # dark gray
        'BORDER':        (51, 65, 85),      # slate #334155
        'BOX_BG':        (30, 41, 59),      # dark slate #1e293b
        'CODE_BG':       (51, 65, 85),      # #334155
        'METRIC_BG':     (30, 41, 59),      # dark panel
        'METRIC_GLOW':   (96, 165, 250),    # blue glow
    },
}

T = THEMES['midnight']


def set_theme(name):
    global T
    T = THEMES[name]


# ---------------------------------------------------------------------------
# Actual project metrics (captured from repo state)
# ---------------------------------------------------------------------------
METRICS = [
    # (value, label, sublabel)
    ("v47",  "KNOWLEDGE",  "evolution"),
    ("13",   "PUBS",       "publications"),
    ("6",    "MINDS",      "satellites"),
    ("68",   "WEBCARDS",   "animated GIFs"),
    ("75",   "PAGES",      "web pages"),
    ("9",    "DAYS",       "v1 → v47"),
]

QUALITIES_FR = [
    "autosuffisant", "autonome", "concordant", "concis", "interactif",
    "evolutif", "distribue", "persistant", "recursif", "securitaire",
    "resilient", "structure",
]
QUALITIES_EN = [
    "self-sufficient", "autonomous", "concordant", "concise", "interactive",
    "evolving", "distributed", "persistent", "recursive", "secure",
    "resilient", "structured",
]


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def brighten(color, factor=1.3):
    return tuple(min(255, int(c * factor)) for c in color[:3])


def dim(color, factor=0.5):
    return tuple(int(c * factor) for c in color[:3])


# ---------------------------------------------------------------------------
# Base image
# ---------------------------------------------------------------------------

def build_base():
    """Gradient background with faint isometric grid + accent bars."""
    img = Image.new('RGB', (W, H))
    draw = ImageDraw.Draw(img)

    # Vertical gradient
    for y in range(H):
        t = y / H
        c = lerp_color(T['BG_TOP'], T['BG_BOT'], t)
        draw.line([(0, y), (W, y)], fill=c)

    # Subtle grid — faint, architectural
    is_light = T['BG_TOP'][0] > 128
    grid_alpha = 10 if is_light else 8
    gc = tuple(max(0, min(255, c + (-grid_alpha if is_light else grid_alpha)))
               for c in T['BG_TOP'])
    for y in range(0, H, 44):
        draw.line([(0, y), (W, y)], fill=gc, width=1)
    for x in range(0, W, 44):
        draw.line([(x, 0), (x, H)], fill=gc, width=1)

    # Top accent bar — thick gradient stripe (6px)
    for x in range(W):
        t = x / W
        if t < 0.33:
            c = lerp_color(T['ACCENT_1'], T['ACCENT_2'], t * 3)
        elif t < 0.66:
            c = lerp_color(T['ACCENT_2'], T['ACCENT_3'], (t - 0.33) * 3)
        else:
            c = lerp_color(T['ACCENT_3'], T['ACCENT_1'], (t - 0.66) * 3)
        draw.line([(x, 0), (x, 5)], fill=c)
        draw.line([(x, H - 5), (x, H)], fill=c)

    return img


def load_photo_circular(size=120):
    """Load portrait photo with circular mask — face priority crop from top."""
    try:
        photo = Image.open(PHOTO_PATH).convert('RGBA')
        pw, ph = photo.size
        s = min(pw, ph)
        left = (pw - s) // 2
        photo = photo.crop((left, 0, left + s, s))  # top-biased
        photo = photo.resize((size, size), Image.LANCZOS)
        mask = Image.new('L', (size, size), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
        result = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        result.paste(photo, (0, 0))
        result.putalpha(mask)
        return result
    except FileNotFoundError:
        return None


# ---------------------------------------------------------------------------
# Drawing components
# ---------------------------------------------------------------------------

def draw_photo_ring(img, draw, cx, cy, photo, frame_idx, n_frames, size=120):
    """Circular photo with animated color-cycling border ring."""
    t = frame_idx / n_frames
    border_w = 3 + 5 * (0.5 + 0.5 * math.sin(2 * math.pi * t))
    # Cycle through accent colors
    if t < 0.33:
        bc = lerp_color(T['ACCENT_1'], T['ACCENT_2'], t * 3)
    elif t < 0.66:
        bc = lerp_color(T['ACCENT_2'], T['ACCENT_3'], (t - 0.33) * 3)
    else:
        bc = lerp_color(T['ACCENT_3'], T['ACCENT_1'], (t - 0.66) * 3)
    bc = brighten(bc, 1.0 + 0.3 * (border_w - 3) / 5)
    total_r = size // 2 + int(border_w)

    # Glow rings
    for off in range(4, 0, -1):
        glow_c = lerp_color(T['BG_TOP'], bc, 0.12 * (5 - off) / 4)
        draw.ellipse([cx - total_r - off, cy - total_r - off,
                      cx + total_r + off, cy + total_r + off],
                     outline=glow_c, width=1)
    # Main border
    draw.ellipse([cx - total_r, cy - total_r,
                  cx + total_r, cy + total_r],
                 fill=T['BOX_BG'], outline=bc, width=max(2, int(border_w / 2)))
    # Photo
    if photo:
        img.paste(photo, (cx - size // 2, cy - size // 2), photo)
    else:
        fnt = ImageFont.truetype(FONT_BOLD, 44)
        draw.text((cx, cy), "MP", fill=T['ACCENT_1'], font=fnt, anchor="mm")


def draw_metric_block(draw, x, y, w, h, value, label, sublabel,
                      active=False, frame_t=0.0):
    """Draw a modernist metric block — oversized number with monospace label.

    Active blocks get a glowing border and brighter fill.
    """
    # Border + fill
    if active:
        pulse = 0.6 + 0.4 * math.sin(2 * math.pi * frame_t)
        border_c = lerp_color(T['ACCENT_2'], brighten(T['ACCENT_3'], 1.4), pulse)
        fill_c = lerp_color(T['METRIC_BG'], T['CODE_BG'], 0.5)
        # Outer glow
        for off in range(3, 0, -1):
            glow_c = lerp_color(T['BG_TOP'], T['METRIC_GLOW'], 0.08 * (4 - off))
            draw.rounded_rectangle([x - off, y - off, x + w + off, y + h + off],
                                   radius=6, outline=glow_c, width=1)
    else:
        border_c = T['BORDER']
        fill_c = T['METRIC_BG']

    draw.rounded_rectangle([x, y, x + w, y + h], radius=4,
                           fill=fill_c, outline=border_c, width=2)

    # Value — oversized, bold, monospace
    val_size = 38 if len(value) <= 3 else 30
    font_val = ImageFont.truetype(FONT_BOLD, val_size)
    val_color = brighten(T['ACCENT_3'], 1.2) if active else T['TEXT_PRIMARY']
    draw.text((x + w // 2, y + 8), value, fill=val_color, font=font_val,
              anchor="mt")

    # Label — uppercase monospace
    font_label = ImageFont.truetype(FONT_MONO, 13)
    draw.text((x + w // 2, y + h - 30), label, fill=T['TEXT_MUTED'],
              font=font_label, anchor="mm")

    # Sublabel — small, dim
    font_sub = ImageFont.truetype(FONT_REGULAR, 10)
    draw.text((x + w // 2, y + h - 14), sublabel, fill=T['TEXT_DIM'],
              font=font_sub, anchor="mm")


def draw_code_prompt(draw, x, y, frame_idx, n_frames):
    """Draw the iconic 'Read packetqc/knowledge' code prompt with cursor blink."""
    font_prompt = ImageFont.truetype(FONT_MONO, 22)
    prompt_text = "$ Read packetqc/knowledge"
    bbox = font_prompt.getbbox(prompt_text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad_x, pad_y = 16, 10

    # Pulsing border
    pulse = 0.5 + 0.5 * math.sin(2 * math.pi * frame_idx / n_frames)
    border_c = lerp_color(T['ACCENT_2'], brighten(T['ACCENT_3'], 1.3), pulse)

    draw.rounded_rectangle(
        [x, y, x + tw + pad_x * 2, y + th + pad_y * 2],
        radius=6, fill=T['CODE_BG'], outline=border_c, width=2)

    # "$" in accent, rest in primary
    font_dollar = ImageFont.truetype(FONT_MONO, 22)
    dollar_bbox = font_dollar.getbbox("$ ")
    dollar_w = dollar_bbox[2] - dollar_bbox[0]
    draw.text((x + pad_x, y + pad_y), "$ ", fill=T['ACCENT_2'],
              font=font_dollar)
    draw.text((x + pad_x + dollar_w, y + pad_y), "Read packetqc/knowledge",
              fill=T['TEXT_PRIMARY'], font=font_prompt)

    # Blinking cursor
    if frame_idx % 2 == 0:
        cursor_x = x + pad_x + tw + 4
        draw.rectangle([cursor_x, y + pad_y + 2, cursor_x + 10, y + pad_y + th],
                       fill=T['ACCENT_3'])

    return tw + pad_x * 2, th + pad_y * 2


def draw_qualities_strip(draw, y, frame_idx, n_frames, right_edge=None):
    """Draw bilingual qualities in 2 rows, right-aligned.

    Row 1: All French qualities
    Row 2: All English qualities
    One quality highlights per frame (same index in both rows).
    Right-aligned to right_edge.
    """
    if right_edge is None:
        right_edge = W - 50

    font_q = ImageFont.truetype(FONT_REGULAR, 15)
    font_q_active = ImageFont.truetype(FONT_BOLD, 15)
    sep = "  ·  "
    sep_w = font_q.getbbox(sep)[2] - font_q.getbbox(sep)[0]
    row_height = 22

    active_idx = frame_idx % len(QUALITIES_FR)

    # Row 1: French | Row 2: English
    for row_num, words in enumerate([QUALITIES_FR, QUALITIES_EN]):
        row_y = y - row_height + row_num * row_height

        # Color scheme per row
        if row_num == 0:
            # French row — accent 3 for active
            active_color = brighten(T['ACCENT_3'], 1.4)
            normal_color = T['TEXT_DIM']
        else:
            # English row — accent 2 for active
            active_color = brighten(T['ACCENT_2'], 1.2)
            normal_color = dim(T['TEXT_DIM'], 0.7)

        # Measure total width
        widths = []
        for w in words:
            bb = font_q.getbbox(w)
            widths.append(bb[2] - bb[0])
        total_w = sum(widths) + sep_w * (len(words) - 1)

        # Right-align
        cx = right_edge - total_w

        for i, (word, ww) in enumerate(zip(words, widths)):
            is_active = (i == active_idx)
            fnt = font_q_active if is_active else font_q
            clr = active_color if is_active else normal_color

            draw.text((cx, row_y), word, fill=clr, font=fnt, anchor="lm")
            cx += ww

            if i < len(words) - 1:
                draw.text((cx, row_y), sep, fill=dim(T['TEXT_DIM'], 0.4),
                          font=font_q, anchor="lm")
                cx += sep_w


def draw_scanline(draw, frame_idx, n_frames, region_x, region_y, region_w, region_h):
    """Draw a faint horizontal scanline that moves through the metric region."""
    t = frame_idx / n_frames
    scan_y = region_y + int(region_h * t)
    # Faint horizontal line
    scan_c = lerp_color(T['BG_TOP'], T['ACCENT_3'], 0.15)
    draw.line([(region_x, scan_y), (region_x + region_w, scan_y)],
              fill=scan_c, width=1)


# ---------------------------------------------------------------------------
# Banner generator
# ---------------------------------------------------------------------------

def generate_banner(theme='midnight'):
    """Generate modernist LinkedIn banner with actual project telemetry.

    All content right-aligned. Left side is clean gradient + grid —
    LinkedIn's profile photo sits there (bottom-left, ~170px circle).
    No duplicate photo in the banner.

    Layout:
      ┌────────────────────────────────────────────────────────────────┐
      │ ▓▓▓▓ gradient accent bar ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │
      │                                                                │
      │                  MARTIN PAQUET         ┌────┐ ┌────┐ ┌────┐   │
      │     (profile     Network Security ·    │v25 │ │ 12 │ │  6 │   │
      │      photo        Embedded · AI        │KNOW│ │PUBS│ │MIND│   │
      │      here)                             └────┘ └────┘ └────┘   │
      │                  $ Read packetqc/      ┌────┐ ┌────┐ ┌────┐   │
      │                    knowledge           │ 40 │ │  9 │ │  5 │   │
      │                  github / pages URLs   │WEBC│ │SESS│ │DAYS│   │
      │                                        └────┘ └────┘ └────┘   │
      │   autosuffisant · autonome · concordant · concis · ...        │
      │ ▓▓▓▓ gradient accent bar ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │
      └────────────────────────────────────────────────────────────────┘
    """
    set_theme(theme)
    n_frames = 10
    frames = []

    # Right margin for metric blocks
    right_margin = 50
    block_w = 108
    block_h = 138
    gap_x = 12
    gap_y = 16
    # Grid of 3 cols from right edge
    grid_x0 = W - right_margin - 3 * block_w - 2 * gap_x
    grid_y0 = 28

    # Text column — right-aligned, between profile photo zone and metric grid
    # Profile photo zone: 0-280px (bottom-left)
    # Text starts at ~350px (safe), right-aligns to sep line
    text_right = grid_x0 - 40   # right edge of text column
    sep_x = grid_x0 - 20        # vertical separator

    for fi in range(n_frames):
        img = build_base()
        draw = ImageDraw.Draw(img)
        frame_t = fi / n_frames

        # ── Scanline effect through metrics area ──
        draw_scanline(draw, fi, n_frames,
                      grid_x0 - 10, grid_y0 - 10,
                      3 * block_w + 2 * gap_x + 20,
                      2 * block_h + gap_y + 20)

        # ── Define column positions ──
        col_left = 440   # left edge of center column
        left_col_right = col_left - 30  # right edge of left column

        # ── LEFT COLUMN: Name + title (left-aligned) ──

        font_name = ImageFont.truetype(FONT_BOLD, 48)
        draw.text((40, 38), "Martin Paquet", fill=T['TEXT_PRIMARY'],
                  font=font_name, anchor="lm")

        font_role = ImageFont.truetype(FONT_REGULAR, 20)
        draw.text((42, 86),
                  "Network Security  ·  Embedded Systems",
                  fill=T['TEXT_MUTED'], font=font_role, anchor="lm")

        font_sub = ImageFont.truetype(FONT_REGULAR, 15)
        draw.text((42, 116),
                  "AI Engineering  ·  Quebec, Canada  ·  30 years",
                  fill=T['TEXT_DIM'], font=font_sub, anchor="lm")

        # ── CENTER COLUMN: Code prompt + URLs + tagline ──
        # Top-aligned, right-aligned (flush toward metric grid)
        # Bigger impact fonts throughout
        col_right = sep_x - 16  # right edge of center column

        # Code prompt — top-aligned, BIG impact, right-aligned
        code_y = 24
        font_prompt = ImageFont.truetype(FONT_MONO, 34)
        prompt_text = "$ Read packetqc/knowledge"
        bbox = font_prompt.getbbox(prompt_text)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        pad_x, pad_y = 22, 16
        code_w = tw + pad_x * 2
        code_h = th + pad_y * 2
        code_x = col_right - code_w  # right-aligned

        # Pulsing border
        pulse = 0.5 + 0.5 * math.sin(2 * math.pi * fi / n_frames)
        border_c = lerp_color(T['ACCENT_2'], brighten(T['ACCENT_3'], 1.3), pulse)

        draw.rounded_rectangle(
            [code_x, code_y, code_x + code_w, code_y + code_h],
            radius=8, fill=T['CODE_BG'], outline=border_c, width=3)

        # "$" in accent, rest in primary
        dollar_bbox = font_prompt.getbbox("$ ")
        dollar_w = dollar_bbox[2] - dollar_bbox[0]
        draw.text((code_x + pad_x, code_y + pad_y), "$ ", fill=T['ACCENT_2'],
                  font=font_prompt)
        draw.text((code_x + pad_x + dollar_w, code_y + pad_y),
                  "Read packetqc/knowledge",
                  fill=T['TEXT_PRIMARY'], font=font_prompt)

        # Blinking cursor
        if fi % 2 == 0:
            cursor_x = code_x + pad_x + tw + 4
            draw.rectangle([cursor_x, code_y + pad_y + 2,
                           cursor_x + 14, code_y + pad_y + th],
                          fill=T['ACCENT_3'])

        # URLs + email — right-aligned, large monospace
        font_url = ImageFont.truetype(FONT_MONO, 20)
        font_email = ImageFont.truetype(FONT_MONO, 17)
        url_y = code_y + code_h + 22
        draw.text((col_right, url_y),
                  "github.com/packetqc/knowledge",
                  fill=T['ACCENT_1'], font=font_url, anchor="rm")
        draw.text((col_right, url_y + 28),
                  "packetqc.github.io/knowledge",
                  fill=T['ACCENT_2'], font=font_url, anchor="rm")
        draw.text((col_right, url_y + 56),
                  "packetqcca@gmail.com",
                  fill=T['TEXT_MUTED'], font=font_email, anchor="rm")

        # Tagline — right-aligned, prominent serif
        font_tag = ImageFont.truetype(FONT_SERIF, 20)
        draw.text((col_right, url_y + 92),
                  "Self-evolving AI engineering intelligence",
                  fill=T['TEXT_MUTED'], font=font_tag, anchor="rm")

        # Tech stack — right-aligned
        font_tech = ImageFont.truetype(FONT_MONO, 16)
        draw.text((col_right, url_y + 124),
                  "STM32 · ThreadX · PQC · SQLite",
                  fill=T['TEXT_DIM'], font=font_tech, anchor="rm")

        # ── METRIC BLOCKS: 2x3 grid, far right ──
        active_metric = fi % len(METRICS)
        for idx, (val, label, sub) in enumerate(METRICS):
            row = idx // 3
            col = idx % 3
            bx = grid_x0 + col * (block_w + gap_x)
            by = grid_y0 + row * (block_h + gap_y)
            is_active = (idx == active_metric)
            draw_metric_block(draw, bx, by, block_w, block_h,
                              val, label, sub,
                              active=is_active, frame_t=frame_t)

        # ── Vertical separator line ──
        sep_c = lerp_color(T['BG_TOP'], T['BORDER'], 0.35)
        draw.line([(sep_x, 16), (sep_x, H - 16)], fill=sep_c, width=1)

        # ── BOTTOM: Bilingual qualities strip (right-aligned, center+right cols) ──
        metrics_right = grid_x0 + 3 * block_w + 2 * gap_x
        draw_qualities_strip(draw, H - 22, fi, n_frames,
                             right_edge=metrics_right)

        frames.append(img)

    return frames


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def save_gif(frames, fname, duration=800):
    """Save animated GIF with quantization."""
    gif_frames = []
    for f in frames:
        rgb = f.convert('RGB')
        q = rgb.quantize(colors=256, method=Image.Quantize.MEDIANCUT,
                         dither=Image.Dither.FLOYDSTEINBERG)
        gif_frames.append(q)

    path = os.path.join(OUT_DIR, fname)
    gif_frames[0].save(
        path, format='GIF', save_all=True,
        append_images=gif_frames[1:],
        duration=duration, loop=0, optimize=True
    )
    size_kb = os.path.getsize(path) / 1024
    print(f"  Generated {fname}  ({len(frames)} frames, {size_kb:.0f} KB)")


def save_png(frame, fname):
    """Save static PNG from a single frame."""
    path = os.path.join(OUT_DIR, fname)
    frame.save(path, format='PNG', optimize=True)
    size_kb = os.path.getsize(path) / 1024
    print(f"  Generated {fname}  ({size_kb:.0f} KB)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Generate LinkedIn profile banner')
    parser.add_argument('--theme', choices=['cayman', 'midnight', 'both'],
                        default='both', help='Theme to generate')
    args = parser.parse_args()

    themes = ['cayman', 'midnight'] if args.theme == 'both' else [args.theme]

    for theme in themes:
        print(f"\n=== LinkedIn Banner ({theme}) ===")
        frames = generate_banner(theme)
        save_gif(frames, f"linkedin-banner-{theme}.gif", duration=800)
        save_png(frames[0], f"linkedin-banner-{theme}.png")

    print(f"\nOutput directory: {OUT_DIR}")
    print("Done!")
