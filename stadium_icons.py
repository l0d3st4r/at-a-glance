"""
Stadium icons (added 2026-09-28): Jason's four drawings in assets/ -- "dome.svg",
"open air.svg", "roof closed.svg", "roof open.svg" -- as inline SVG for the pages.

Used in two places:
  * Page 1's Game Info card, where an indoor game shows the stadium instead of a forecast:
    "Dome" + the dome icon, or "Roof Closed" + the roof-closed icon (render_page1.weather_html).
  * Page 2 Game Info's Venue card, expanded and condensed: the icon for the stadium's type
    (render_page2gameinfo). A retractable roof reads as roof open unless it's recorded closed --
    including before kickoff ("Roof TBD"), because that's also when the page shows a forecast,
    so the open roof matches the weather being there (Jason, 2026-09-28).

The files are read at build time, so replacing one in assets/ (same name, same kind of
drawing) is all it takes to update it. They come out of the drawing app as one black path on
a 4096x4096 canvas with a lot of empty space; here each is cropped to its drawing and filled
with currentColor, so it follows the light/dark theme. All four share one scale with their
bases lined up (a common viewBox height), so a wider drawing -- roof open's panels -- comes out
wider rather than the others shrinking. Pages size them by height only.
"""

import html
import os
import re

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")

# Each drawing's bounds inside its file (x, y, width, height), in the file's own coordinates
# (the path sits inside translate(2048 2048)). Measured with a browser's getBBox() -- re-measure
# if a file is replaced with a differently shaped drawing, or it'll be cropped wrong.
ICONS = {
    "dome": ("dome.svg", (-1189, -770, 2379, 1181), "Dome"),
    "open_air": ("open air.svg", (-1316, -466, 2631, 853), "Open air"),
    "roof_closed": ("roof closed.svg", (-1316, -715, 2631, 1129), "Roof closed"),
    "roof_open": ("roof open.svg", (-1723, -569, 3446, 1129), "Roof open"),
}
_BOX_H = max(box[3] for _f, box, _l in ICONS.values())
_PAD = 60

_cache = {}


def _path(kind):
    if kind not in _cache:
        with open(os.path.join(ASSETS, ICONS[kind][0]), encoding="utf-8") as f:
            _cache[kind] = re.search(r'<path d="([^"]+)"', f.read()).group(1)
    return _cache[kind]


def kind_for(stadium):
    """Page 2's stadium dict (roof_type / roof_status) -> an ICONS key."""
    st = stadium or {}
    roof = st.get("roof_type")
    if roof == "dome":
        return "dome"
    if roof == "retractable":
        return "roof_closed" if st.get("roof_status") == "closed" else "roof_open"
    return "open_air"


def svg(kind, cls):
    _f, (x, y, w, h), label = ICONS[kind]
    vx, vy = x - _PAD, y + h - _BOX_H - _PAD
    vw, vh = w + 2 * _PAD, _BOX_H + 2 * _PAD
    return (f'<svg class="{cls} stad stad-{kind.replace("_", "-")}" viewBox="{vx} {vy} {vw} {vh}" '
            f'style="aspect-ratio:{vw}/{vh}" role="img" aria-label="{html.escape(label)}">'
            f'<path d="{_path(kind)}" fill="currentColor"/></svg>')
