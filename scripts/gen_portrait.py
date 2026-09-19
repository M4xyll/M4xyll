#!/usr/bin/env python3
"""
Turn a photo into monochrome ASCII art that types itself in row by row,
then freezes (no looping).

Pipeline, in order, and why each step exists:
  1. rembg removes the background, so the crop and contrast steps only
     ever look at the face/subject, not room clutter.
  2. Crop is measured from the ALPHA SILHOUETTE, never the graded image.
     Dark hair carries almost no luminance, so a brightness-based crop
     clips the top of the head. Head width is the MEDIAN row width
     across the upper ~60% of the silhouette; the max would catch a
     shoulder and leave the face adrift in empty panel space.
  3. OpenCV CLAHE boosts local contrast — a flatly-lit face converts to
     one undifferentiated blob without it.
  4. A levels curve crushes the low end so clothing/background falls to
     pure black (glyph = space) instead of muddying the portrait.
  5. Brightness -> glyph ramp. Panel is dark, ink is light, so the ramp
     runs dark->bright ('a black pixel picks the space glyph'), which is
     the OPPOSITE polarity from the usual white-bg ASCII pipeline.
  6. Rows are emitted as runs of non-space characters at explicit x
     positions with textLength, because renderers collapse runs of
     literal space characters inside <text> even under white-space:pre.

STATIC=1 emits the fully-typed frame instead of animating.
"""
import os
import sys

import numpy as np
import cv2
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from chrome import svg_open, svg_close, panel_frame, text_run_elements, FG_BRIGHT, TITLEBAR_H

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "ascii-portrait.svg")
STATIC = os.environ.get("STATIC") == "1"

# Dark->bright ramp: index 0 (darkest) -> space, so background pixels
# vanish into the panel instead of picking a dense glyph.
RAMP = " .`:-=+*csS#%@"

COLS = 80          # ascii grid width in characters
FONT_SIZE = 7
CHAR_W = FONT_SIZE * 0.6
CHAR_H = FONT_SIZE * 1.0
PAD = 16


def load_and_cutout(path: str) -> Image.Image:
    from rembg import remove, new_session
    # u2netp: a small (~4.6MB) session, plenty for a foreground/background
    # split on a single portrait, and avoids OOM on constrained hosts
    # that the default 1GB general-purpose model can trigger.
    session = new_session("u2netp")
    with open(path, "rb") as f:
        input_bytes = f.read()
    out_bytes = remove(input_bytes, session=session)
    img = Image.open(__import__("io").BytesIO(out_bytes)).convert("RGBA")
    return img


def clean_mask(img: Image.Image) -> Image.Image:
    """Keep only the largest connected alpha region, so a stray sliver of
    background the matting model half-removed (a chair edge, a strap)
    doesn't survive as a disconnected fleck outside the subject."""
    arr = np.array(img)
    alpha = arr[:, :, 3]
    binary = (alpha > 10).astype(np.uint8)
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    if n_labels <= 1:
        return img
    # label 0 is background; keep the largest non-background component.
    largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    keep = (labels == largest).astype(np.uint8)
    arr[:, :, 3] = arr[:, :, 3] * keep
    return Image.fromarray(arr)


def crop_to_silhouette(img: Image.Image) -> Image.Image:
    """Crop using the ALPHA channel's silhouette, not pixel brightness."""
    img = clean_mask(img)
    arr = np.array(img)
    alpha = arr[:, :, 3]
    mask = alpha > 10

    rows = np.where(mask.any(axis=1))[0]
    cols = np.where(mask.any(axis=0))[0]
    if len(rows) == 0 or len(cols) == 0:
        return img  # nothing detected; fall back to the original frame

    top, bottom = rows[0], rows[-1]
    # Median row width across the upper 60% of the silhouette height,
    # not the max (a raised shoulder would widen the crop and shrink
    # the face inside the panel).
    upper_bound = top + int((bottom - top) * 0.6)
    row_widths = []
    for y in range(top, upper_bound + 1):
        xs = np.where(mask[y])[0]
        if len(xs):
            row_widths.append(xs[-1] - xs[0])
    head_width = int(np.median(row_widths)) if row_widths else (cols[-1] - cols[0])

    left, right = cols[0], cols[-1]
    center_x = (left + right) // 2
    half_w = max(head_width, right - left) // 2
    # Small margin so the crop doesn't hug the silhouette edge.
    margin = int(half_w * 0.18)
    crop_left = max(0, center_x - half_w - margin)
    crop_right = min(arr.shape[1], center_x + half_w + margin)
    crop_top = max(0, top - int((bottom - top) * 0.06))
    # Stop a bit above the full silhouette bottom (shoulders/chest), so
    # the panel isn't mostly empty canvas below the subject — a headshot
    # framing, not a waist-up one.
    crop_bottom = min(arr.shape[0], top + int((bottom - top) * 0.82))

    return img.crop((crop_left, crop_top, crop_right, crop_bottom))


def to_ascii_grid(img: Image.Image, cols: int) -> list[str]:
    arr = np.array(img.convert("RGBA"))
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3]

    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

    # CLAHE: boost local contrast so a flatly-lit face doesn't collapse
    # into one undifferentiated blob of mid-gray.
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # Levels curve: crush the low end to pure black so background/
    # clothing remnants map to the space glyph instead of muddy dots.
    black_point = 60
    white_point = 235
    gray = np.clip((gray.astype(np.float32) - black_point) * 255.0 / (white_point - black_point), 0, 255).astype(np.uint8)

    # Cells outside the alpha silhouette are forced to black (space).
    gray[alpha < 10] = 0

    h, w = gray.shape
    # Character cells are taller than wide, so sample rows more sparsely
    # than columns to keep the portrait's proportions correct.
    aspect_correction = 0.55
    rows = max(1, int(cols * (h / w) * aspect_correction))

    small = cv2.resize(gray, (cols, rows), interpolation=cv2.INTER_AREA)

    ramp_len = len(RAMP)
    lines = []
    for r in range(rows):
        line_chars = []
        for c in range(cols):
            v = small[r, c] / 255.0
            idx = min(ramp_len - 1, int(v * ramp_len))
            line_chars.append(RAMP[idx])
        lines.append("".join(line_chars))
    return lines


def render(lines: list[str]):
    n_rows = len(lines)
    n_cols = max(len(l) for l in lines) if lines else 0
    grid_w = n_cols * CHAR_W
    grid_h = n_rows * CHAR_H

    width = int(grid_w + PAD * 2)
    height = int(grid_h + PAD * 2 + TITLEBAR_H)

    total_anim = 2.4  # seconds to type in every row
    per_row = total_anim / max(n_rows, 1)

    parts = [svg_open(width, height)]
    parts.append(panel_frame(width, height, "ascii-portrait.svg"))

    top = TITLEBAR_H + PAD
    for r, line in enumerate(lines):
        y = top + (r + 1) * CHAR_H
        x = PAD
        row_svg = text_run_elements(x, y, line, FONT_SIZE, FG_BRIGHT, CHAR_W)
        if not row_svg:
            continue
        if STATIC:
            parts.append(row_svg)
        else:
            delay = r * per_row
            parts.append(
                f'<g opacity="0">{row_svg}'
                f'<animate attributeName="opacity" from="0" to="1" begin="{delay:.3f}s" dur="0.08s" fill="freeze"/></g>'
            )

    parts.append(svg_close())
    return "\n".join(parts), width, height


def main():
    if len(sys.argv) != 2:
        print("usage: gen_portrait.py <path-to-photo>", file=sys.stderr)
        sys.exit(1)
    photo_path = sys.argv[1]

    img = load_and_cutout(photo_path)
    img = crop_to_silhouette(img)
    lines = to_ascii_grid(img, COLS)
    svg, width, height = render(lines)

    with open(OUT_PATH, "w") as f:
        f.write(svg)
    print(f"wrote {OUT_PATH} ({width}x{height}), {len(lines)} rows x {COLS} cols")


if __name__ == "__main__":
    main()
