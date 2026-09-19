#!/usr/bin/env python3
"""
Assemble README.md. The portrait and info-card panels only line up
visually if their DISPLAYED heights match, so this solves each panel's
display width from its actual rendered aspect ratio rather than
hardcoding pixel widths — re-run any time the card's row count (and
therefore its height) changes.

GitHub strips inline `style` and most `<h1>`/`<h2>` come with a
full-width rule, so this template uses `<h3>` for un-ruled headings and
`<br>` for the only vertical spacing that survives sanitization. A
`<table>` is the one reliable way to place two images side by side.
"""
import os
import re

ROOT = os.path.join(os.path.dirname(__file__), "..")
USERNAME = "M4xyll"
COMBINED_WIDTH = 850


def svg_dims(path):
    with open(path) as f:
        head = f.read(500)
    w = int(re.search(r'width="(\d+)"', head).group(1))
    h = int(re.search(r'height="(\d+)"', head).group(1))
    return w, h


def main():
    portrait_w, portrait_h = svg_dims(os.path.join(ROOT, "ascii-portrait.svg"))
    card_w, card_h = svg_dims(os.path.join(ROOT, "info-card.svg"))

    aspect_p = portrait_w / portrait_h
    aspect_c = card_w / card_h

    display_w_p = round(COMBINED_WIDTH * aspect_p / (aspect_p + aspect_c))
    display_w_c = COMBINED_WIDTH - display_w_p

    readme = f"""<div align="center">

<img src="./contrib-heatmap.svg" alt="{USERNAME}'s contribution heatmap" width="{COMBINED_WIDTH}">

<br>

<table>
<tr>
<td valign="top"><img src="./ascii-portrait.svg" alt="ASCII portrait" width="{display_w_p}"></td>
<td valign="top"><img src="./info-card.svg" alt="Info card" width="{display_w_c}"></td>
</tr>
</table>

</div>

<h3 align="center">Thanks for stopping by 👋</h3>
"""

    out_path = os.path.join(ROOT, "README.md")
    with open(out_path, "w") as f:
        f.write(readme)
    print(f"wrote {out_path}")
    print(f"portrait: {portrait_w}x{portrait_h} -> display width {display_w_p}")
    print(f"card:     {card_w}x{card_h} -> display width {display_w_c}")


if __name__ == "__main__":
    main()
