"""
Stadium icons mockup (2026-09-28) -- NOT part of the live build.

SNAPSHOT: this was the design mockup. The approved version now lives in the real build
(stadium_icons.py, render_page1.weather_html, render_page2gameinfo), with two changes from
what's below: Page 1 says "Dome" / "Roof Closed" instead of "Indoors", and a retractable roof
before kickoff keeps the roof-open icon (approved as mocked). This script only works against
a site/ built from before that change (commit 2153039); kept for reference.

Jason's four stadium icons (assets/dome.svg, "open air.svg", "roof closed.svg",
"roof open.svg") swapped in for today's two generic ones:

  * Page 1's Game Info card, where an indoor game shows "Indoors" instead of a
    forecast: the one generic dome icon becomes the stadium's own -- dome, or roof
    closed (a retractable roof recorded closed for a finished game).
  * Page 2 Game Info's Stadium card (expanded and condensed): the one generic stadium
    drawing becomes the stadium's type -- open air, dome, roof open or roof closed.
    A retractable roof before kickoff (status unknown, "Roof TBD") uses roof open.

The icons as uploaded are one black shape on a 4096x4096 canvas with lots of empty
space. Here they're cropped to the drawing and filled with currentColor so they follow
the light/dark theme. All four share one scale with their bases lined up, so a wider
drawing (roof open's panels) comes out wider rather than the others shrinking.

Writes a copy of site/ with the swap made, into the folder given on the command line, to
serve and screenshot. Nothing in the real build changes. Pass a scratch folder outside the
repo -- the copy is the whole site and shouldn't be committed.

Run after a normal build (so site/ and data/ exist):
    python mockups/build_stadium_icons_mockup.py /path/to/scratch/site-mock
"""

import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import render_page1  # noqa: E402
import render_page2gameinfo  # noqa: E402

SITE = os.path.join(ROOT, "site")

# Each icon's drawing bounds inside its file (measured with the browser's getBBox, in the
# file's own coordinates after its translate(2048 2048)): x, y, width, height.
ICONS = {
    "dome": ("dome.svg", (-1189, -770, 2379, 1181)),
    "open_air": ("open air.svg", (-1316, -466, 2631, 853)),
    "roof_closed": ("roof closed.svg", (-1316, -715, 2631, 1129)),
    "roof_open": ("roof open.svg", (-1723, -569, 3446, 1129)),
}
BOX_H = max(b[3] for _f, b in ICONS.values())   # common height: same scale for all four
PAD = 60


def icon_svg(kind, cls, label):
    fname, (x, y, w, h) = ICONS[kind]
    with open(os.path.join(ROOT, "assets", fname), encoding="utf-8") as f:
        raw = f.read()
    d = re.search(r'<path d="([^"]+)"', raw).group(1)
    bottom = y + h
    vx, vy, vw, vh = x - PAD, bottom - BOX_H - PAD, w + 2 * PAD, BOX_H + 2 * PAD
    return (f'<svg class="{cls} stad stad-{kind}" viewBox="{vx} {vy} {vw} {vh}" '
            f'style="aspect-ratio:{vw}/{vh}" role="img" aria-label="{label}">'
            f'<path d="{d}" fill="currentColor"/></svg>')


LABELS = {"dome": "Dome", "open_air": "Open air", "roof_closed": "Roof closed", "roof_open": "Roof open"}


def stadium_kind(st):
    rt = st.get("roof_type")
    if rt == "dome":
        return "dome"
    if rt == "retractable":
        return "roof_closed" if st.get("roof_status") == "closed" else "roof_open"
    return "open_air"


# Sizes by height; width follows each drawing's own proportions.
MOCK_CSS = """
.weather svg.stad{height:30px;width:auto}
.c-game .weather svg.stad{height:15px;width:auto}
.st-icon.stad{width:auto;height:auto}
.p2-l .st-icon.stad{height:54px;width:auto}
.cc .st-icon.stad{height:34px;width:auto}
@media (max-width:400px){.cc .st-icon.stad{height:28px}}
"""


def dress(html, st):
    kind = stadium_kind(st)
    old_indoor = render_page1.WEATHER_ICONS["indoor"]
    indoor_kind = "roof_closed" if kind == "roof_closed" else "dome"
    html = html.replace(old_indoor, icon_svg(indoor_kind, "wx", "Indoors"))
    html = html.replace(render_page2gameinfo.STADIUM_ICON, icon_svg(kind, "st-icon", LABELS[kind]))
    html, n = re.subn(r"(<style id='p1-css'>.*?)(</style>)", lambda m: m.group(1) + MOCK_CSS + m.group(2),
                      html, count=1, flags=re.S)
    if not n:
        raise SystemExit("game page has no #p1-css -- has the markup changed?")
    return html


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: build_stadium_icons_mockup.py <scratch folder for the mock site>")
    out = sys.argv[1]
    if os.path.exists(out):
        shutil.rmtree(out)
    shutil.copytree(SITE, out)
    with open(os.path.join(ROOT, "data", "matchups.json"), encoding="utf-8") as f:
        details = json.load(f)["game_details"]
    for gid, g in details.items():
        path = os.path.join(out, "game", f"{gid}.html")
        if not os.path.exists(path):
            continue
        st = (g.get("info") or {}).get("stadium") or {}
        with open(path, encoding="utf-8") as f:
            html = f.read()
        with open(path, "w", encoding="utf-8") as f:
            f.write(dress(html, st))
    print(f"Wrote mock site to {out}")


if __name__ == "__main__":
    main()
