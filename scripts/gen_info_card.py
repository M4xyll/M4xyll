#!/usr/bin/env python3
"""
Render a neofetch-style info panel: a label/value line per fact, fading
in on a stagger. No GitHub stats here — the heatmap panel covers those.

STATIC=1 emits the fully-revealed frame instead of animating.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from chrome import (
    svg_open, svg_close, panel_frame, text_run_elements,
    FG_BRIGHT, FG_DIM, ACCENT, PROMPT_GREEN, TITLEBAR_H,
)

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "info-card.svg")
STATIC = os.environ.get("STATIC") == "1"

# ---------------------------------------------------------------------
# Edit these to change what the card shows. Each is (label, value).
USERNAME = "M4xyll"
LINES = [
    ("role", "Fullstack Developer & Founder"),
    ("building", "Ryvord Hosting"),
    ("", "Atacq — AI-driven cybersecurity"),
    ("stack", "React / Next.js / Node.js / Fastify"),
    ("infra", "Proxmox, Docker, self-hosted"),
    ("location", "Paris, France"),
]
# ---------------------------------------------------------------------

FONT_SIZE = 13
LINE_H = 22
CHAR_W = FONT_SIZE * 0.6
PAD_X = 20
TOP_PAD = TITLEBAR_H + 28
LABEL_W_CHARS = 9  # widest label ("building") + gutter, in characters


def render():
    header = f"{USERNAME}@github"
    width = 380
    n_lines = 1 + len(LINES) + 1  # header + fields + separator row
    height = TOP_PAD + n_lines * LINE_H + 18

    stagger = 0.12  # seconds between each line's fade-in
    fade_dur = 0.35

    parts = [svg_open(width, height)]
    parts.append(panel_frame(width, height, "info-card.svg"))

    y = TOP_PAD
    row = 0

    def fade_wrap(inner_svg, delay):
        if STATIC:
            return inner_svg
        return (
            f'<g opacity="0">{inner_svg}'
            f'<animate attributeName="opacity" from="0" to="1" begin="{delay:.3f}s" '
            f'dur="{fade_dur}s" fill="freeze"/></g>'
        )

    # Header: "user@github"
    header_svg = text_run_elements(PAD_X, y, header, FONT_SIZE + 1, ACCENT, CHAR_W)
    parts.append(fade_wrap(header_svg, row * stagger))
    row += 1

    # Separator rule, sitting in its own slim row between the header and
    # the first field so it never crosses through either line's glyphs.
    rule_y = y + LINE_H * 0.32
    rule_delay = row * stagger
    rule = f'<line x1="{PAD_X}" y1="{rule_y:.2f}" x2="{width - PAD_X}" y2="{rule_y:.2f}" stroke="#30363d" stroke-width="1"/>'
    parts.append(rule if STATIC else f'<g opacity="0">{rule}<animate attributeName="opacity" from="0" to="1" begin="{rule_delay:.3f}s" dur="{fade_dur}s" fill="freeze"/></g>')
    row += 1
    y += LINE_H

    # Fields
    for label, value in LINES:
        delay = row * stagger
        line_parts = []
        if label:
            label_svg = text_run_elements(PAD_X, y, f"{label}:", FONT_SIZE, ACCENT, CHAR_W)
            line_parts.append(label_svg)
        value_x = PAD_X + LABEL_W_CHARS * CHAR_W
        value_svg = text_run_elements(value_x, y, value, FONT_SIZE, FG_BRIGHT, CHAR_W)
        line_parts.append(value_svg)
        parts.append(fade_wrap("\n".join(line_parts), delay))
        y += LINE_H
        row += 1

    parts.append(svg_close())
    return "\n".join(parts), width, height


def main():
    svg, width, height = render()
    with open(OUT_PATH, "w") as f:
        f.write(svg)
    print(f"wrote {OUT_PATH} ({width}x{height})")


if __name__ == "__main__":
    main()
