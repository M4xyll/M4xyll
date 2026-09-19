#!/usr/bin/env python3
"""
Render the 53-week contribution calendar as a self-contained animated
SVG. Cells reveal diagonally (by week+day-of-week order), then a
Less->More legend and a stats footer fade in.

STATIC=1 env var emits the fully-revealed frame (last animation state)
instead of animating — useful for previewing a layout without waiting.
"""
import json
import os
import sys
from datetime import datetime, date
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from chrome import (
    svg_open, svg_close, panel_frame, HEATMAP_LEVELS, FG_DIM, FG_BRIGHT,
    ACCENT, TITLEBAR_H, BORDER,
)

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "contributions.json")
OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "contrib-heatmap.svg")

CELL = 11
GAP = 3
STEP = CELL + GAP
LEFT_PAD = 34   # room for day-of-week labels
TOP_PAD = TITLEBAR_H + 22  # room for month labels under the titlebar
STATIC = os.environ.get("STATIC") == "1"

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DOW_LABELS = {1: "Mon", 3: "Wed", 5: "Fri"}  # Python weekday(): Mon=0..Sun=6 -> we index 0..6 with Sun=0 like GitHub


def load_data():
    with open(DATA_PATH) as f:
        return json.load(f)


def build_grid(days):
    """Bucket days into GitHub's week columns (Sun-Sat rows), oldest first."""
    parsed = []
    for d in days:
        dt = datetime.strptime(d["date"], "%Y-%m-%d").date()
        parsed.append((dt, d["level"], d["count"]))
    parsed.sort(key=lambda t: t[0])

    if not parsed:
        return [], []

    first_dt = parsed[0][0]
    # Align first column to the Sunday on/before the first day, like GitHub.
    first_sunday_offset = (first_dt.weekday() + 1) % 7  # Mon=0..Sun=6 -> Sun=0..Sat=6
    weeks = defaultdict(dict)
    for dt, level, count in parsed:
        dow = (dt.weekday() + 1) % 7  # 0=Sun .. 6=Sat
        days_since_first_sunday = (dt - first_dt).days + first_sunday_offset
        week_idx = days_since_first_sunday // 7
        weeks[week_idx][dow] = (dt, level, count)

    n_weeks = max(weeks.keys()) + 1
    grid = [[weeks[w].get(d) for d in range(7)] for w in range(n_weeks)]

    # Month label per week column: label the week that contains a day-1.
    month_labels = []
    seen_months = set()
    for w in range(n_weeks):
        label = ""
        for d in range(7):
            cell = grid[w][d]
            if cell and cell[0].day <= 7 and cell[0].month not in seen_months and d == 0:
                pass
        for d in range(7):
            cell = grid[w][d]
            if cell and cell[0].day <= 7:
                key = (cell[0].year, cell[0].month)
                if key not in seen_months:
                    seen_months.add(key)
                    label = MONTHS[cell[0].month - 1]
                break
        month_labels.append(label)

    return grid, month_labels


def render(data):
    grid, month_labels = build_grid(data["days"])
    n_weeks = len(grid)
    grid_w = n_weeks * STEP - GAP
    grid_h = 7 * STEP - GAP

    width = LEFT_PAD + grid_w + 24
    height = TOP_PAD + grid_h + 56  # + legend/footer band

    # Diagonal reveal order: sort cells by (week + day_of_week), i.e. an
    # anti-diagonal sweep across the grid rather than row-by-row.
    cells = []
    for w in range(n_weeks):
        for d in range(7):
            cell = grid[w][d]
            if cell is None:
                continue
            dt, level, count = cell
            cells.append((w, d, dt, level, count))
    cells.sort(key=lambda c: (c[0] + c[1], c[0]))
    max_diag = max((w + d for w, d, *_ in cells), default=1)

    total_anim = 2.2  # seconds for the full diagonal sweep
    per_step = total_anim / max(max_diag, 1)

    parts = [svg_open(width, height)]
    parts.append(panel_frame(width, height, f"{data['username']}@github — contributions"))

    # Month labels
    for w, label in enumerate(month_labels):
        if not label:
            continue
        x = LEFT_PAD + w * STEP
        parts.append(f'<text x="{x}" y="{TOP_PAD - 8}" font-size="10" fill="{FG_DIM}">{label}</text>')

    # Day-of-week labels (Mon/Wed/Fri, GitHub's convention)
    for dow, label in DOW_LABELS.items():
        y = TOP_PAD + dow * STEP + CELL - 2
        parts.append(f'<text x="8" y="{y}" font-size="9" fill="{FG_DIM}">{label}</text>')

    # Cells
    for w, d, dt, level, count in cells:
        x = LEFT_PAD + w * STEP
        y = TOP_PAD + d * STEP
        color = HEATMAP_LEVELS[max(0, min(level, 4))]
        delay = (w + d) * per_step
        title = f"{count} contribution{'s' if count != 1 else ''} on {dt.strftime('%B %-d, %Y') if hasattr(dt, 'strftime') else dt}"
        if STATIC:
            parts.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" ry="2" fill="{color}">'
                f'<title>{title}</title></rect>'
            )
        else:
            parts.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" ry="2" fill="{HEATMAP_LEVELS[0]}" opacity="0">'
                f'<title>{title}</title>'
                f'<animate attributeName="fill" to="{color}" begin="{delay:.3f}s" dur="0.01s" fill="freeze"/>'
                f'<animate attributeName="opacity" from="0" to="1" begin="{delay:.3f}s" dur="0.25s" fill="freeze"/>'
                f'</rect>'
            )

    # Legend: Less [4 swatches] More, bottom-left, fades in after the sweep
    legend_y = TOP_PAD + grid_h + 26
    legend_x = LEFT_PAD
    legend_delay = total_anim + 0.1
    legend_group_attrs = "" if STATIC else f'opacity="0"'
    parts.append(f'<g {legend_group_attrs}>' if not STATIC else '<g>')
    if not STATIC:
        parts.append(f'<animate attributeName="opacity" from="0" to="1" begin="{legend_delay:.3f}s" dur="0.4s" fill="freeze"/>')
    parts.append(f'<text x="{legend_x}" y="{legend_y+9}" font-size="10" fill="{FG_DIM}">Less</text>')
    sx = legend_x + 32
    for i, color in enumerate(HEATMAP_LEVELS):
        parts.append(f'<rect x="{sx + i*STEP}" y="{legend_y}" width="{CELL}" height="{CELL}" rx="2" ry="2" fill="{color}"/>')
    parts.append(f'<text x="{sx + len(HEATMAP_LEVELS)*STEP + 6}" y="{legend_y+9}" font-size="10" fill="{FG_DIM}">More</text>')
    parts.append('</g>')

    # Stats footer, fades in slightly after the legend
    footer_y = legend_y + 26
    footer_delay = legend_delay + 0.25
    active_days = sum(1 for c in cells if c[4] > 0)
    footer_text = f"{data['header_text']} &#183; {active_days} active days"
    if STATIC:
        parts.append(f'<text x="{legend_x}" y="{footer_y}" font-size="11" fill="{ACCENT}">{footer_text}</text>')
    else:
        parts.append(
            f'<text x="{legend_x}" y="{footer_y}" font-size="11" fill="{ACCENT}" opacity="0">{footer_text}'
            f'<animate attributeName="opacity" from="0" to="1" begin="{footer_delay:.3f}s" dur="0.4s" fill="freeze"/>'
            f'</text>'
        )

    parts.append(svg_close())
    return "\n".join(parts), width, height


def main():
    data = load_data()
    svg, width, height = render(data)
    with open(OUT_PATH, "w") as f:
        f.write(svg)
    print(f"wrote {OUT_PATH} ({width}x{height})")


if __name__ == "__main__":
    main()
