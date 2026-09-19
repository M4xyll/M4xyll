"""
Shared panel chrome (colors, fonts, terminal frame) for the three
GitHub-profile SVG generators. Every generator imports this so the
portrait, info card, and heatmap look like they belong to one terminal
theme.

All panels share:
  - a dark background so the SVG reads identically whether GitHub is
    rendering the README in light or dark mode (an <img>-embedded SVG
    cannot detect host theme)
  - the same border color and corner radius
  - a monospace font *stack* of faces that ship with each major OS,
    never a webfont
  - a titlebar with three "traffic light" dots, like a terminal window
"""

# Background / border -------------------------------------------------
BG = "#0d1117"          # GitHub's own dark bg, so panels blend into dark-mode READMEs
PANEL_BG = "#0d1117"
BORDER = "#21262d"
TITLEBAR_BG = "#161b22"

# Ink colors ------------------------------------------------------------
# Single-color ink for the ASCII portrait (see chrome note in generator);
# a small accent palette for the info card / heatmap text.
FG_BRIGHT = "#c9d1d9"
FG_DIM = "#6e7681"
ACCENT = "#58a6ff"     # blue accent (labels, headings)
ACCENT_GREEN = "#3fb950"
PROMPT_GREEN = "#3fb950"

# Traffic-light dots
DOT_RED = "#ff5f56"
DOT_YELLOW = "#ffbd2e"
DOT_GREEN = "#27c93f"

# GitHub's own 5-step contribution ramp (dark theme), levels 0-4
HEATMAP_LEVELS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]

# Fonts -----------------------------------------------------------------
# A stack of monospace faces that ship with Windows / macOS / major Linux
# distros, so the SVG renders consistently without an embedded webfont.
MONO_STACK = (
    "ui-monospace, 'Cascadia Code', 'SF Mono', 'Consolas', "
    "'Liberation Mono', 'DejaVu Sans Mono', 'Menlo', monospace"
)

TITLEBAR_H = 32
RADIUS = 6


def svg_open(width, height):
    return (
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" font-family="{MONO_STACK}">'
    )


def svg_close():
    return "</svg>"


def panel_frame(width, height, title):
    """Terminal window chrome: rounded panel, titlebar, three dots, title text.
    Returns the SVG fragment; content should be drawn below TITLEBAR_H.
    """
    return f'''
  <clipPath id="panel-clip"><rect x="0" y="0" width="{width}" height="{height}" rx="{RADIUS}" ry="{RADIUS}"/></clipPath>
  <g clip-path="url(#panel-clip)">
    <rect x="0" y="0" width="{width}" height="{height}" fill="{PANEL_BG}"/>
    <rect x="0" y="0" width="{width}" height="{TITLEBAR_H}" fill="{TITLEBAR_BG}"/>
    <circle cx="18" cy="{TITLEBAR_H/2}" r="5" fill="{DOT_RED}"/>
    <circle cx="36" cy="{TITLEBAR_H/2}" r="5" fill="{DOT_YELLOW}"/>
    <circle cx="54" cy="{TITLEBAR_H/2}" r="5" fill="{DOT_GREEN}"/>
    <text x="{width/2}" y="{TITLEBAR_H/2 + 4}" text-anchor="middle" font-size="12" fill="{FG_DIM}">{title}</text>
    <rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="{RADIUS}" ry="{RADIUS}" fill="none" stroke="{BORDER}" stroke-width="1"/>
  </g>
'''


def text_run_elements(x, y, s, font_size, fill, char_w, extra_attrs=""):
    """Emit one or more <text> runs for a string with NO collapsible
    whitespace: split into runs of non-space characters, each placed at
    its own absolute x with an explicit textLength, so spacing survives
    renderers that collapse runs of space characters even under
    `white-space: pre`.
    """
    out = []
    i = 0
    n = len(s)
    while i < n:
        if s[i] == " ":
            i += 1
            continue
        j = i
        while j < n and s[j] != " ":
            j += 1
        run = s[i:j]
        run_x = x + i * char_w
        run_len = len(run) * char_w
        esc = (
            run.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        out.append(
            f'<text x="{run_x:.2f}" y="{y:.2f}" font-size="{font_size}" fill="{fill}" '
            f'textLength="{run_len:.2f}" lengthAdjust="spacingAndGlyphs" {extra_attrs}>{esc}</text>'
        )
        i = j
    return "\n".join(out)
