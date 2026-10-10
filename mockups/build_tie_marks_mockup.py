"""
Matchups card: tie marks -- mockup (2026-10-10), NOT part of the live build.

On the Matchups card's chart (matchup.py) an offense is an O and a defense an X on a 32-to-1 track.
When both teams hold the same rank the two marks land on the same spot, so they need one mark that
still says "both". Jason didn't like the first try (the O's left half beside an X's right half, "(x"),
so here are other ways, each on a track at its real size and blown up, on the dark and the light
card, in LV (offense) and NE (defense) colors:

  A  O with an x inside     the offense's ring, a small x in the defense's color in its middle
  B  X with an o on it      the defense's X, a small ring in the offense's color on its crossing
  C  stacked                the O sitting on top of the line and the X hanging under it, same spot
  D  side by side           O and X nudged apart, touching, centered on the shared spot ("OX")
  E  split dot              one solid dot, its left half the offense's color, its right the defense's
  F  first try              the O's left half and an X's right half, for comparison

Run: py mockups/build_tie_marks_mockup.py -> mockups/tie-marks.html (self-contained).
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import team_line_colors  # noqa: E402
import theme  # noqa: E402

SW = 2.4   # the marks' stroke, as on the card
X = "M3.4 3.4l7.2 7.2M10.6 3.4l-7.2 7.2"


def opt_a(oc, dc, bg):
    return (f'<circle cx="7" cy="7" r="5.2" fill="{bg}" stroke="{oc}" stroke-width="{SW}"/>'
            f'<path d="M5.1 5.1l3.8 3.8M8.9 5.1l-3.8 3.8" stroke="{dc}" stroke-width="2"/>')


def opt_b(oc, dc, bg):
    return (f'<path d="{X}" stroke="{bg}" stroke-width="5"/><path d="{X}" stroke="{dc}" stroke-width="{SW}"/>'
            f'<circle cx="7" cy="7" r="2.6" fill="{bg}" stroke="{oc}" stroke-width="2"/>')


def opt_c(oc, dc, bg):
    # the O above the line, the X below, both a size smaller
    return (f'<circle cx="7" cy="1.6" r="3.2" fill="{bg}" stroke="{oc}" stroke-width="2"/>'
            f'<path d="M4.6 10l4.8 4.8M9.4 10l-4.8 4.8" stroke="{bg}" stroke-width="4.4"/>'
            f'<path d="M4.6 10l4.8 4.8M9.4 10l-4.8 4.8" stroke="{dc}" stroke-width="2"/>')


def opt_d(oc, dc, bg):
    return (f'<circle cx="2.6" cy="7" r="4.2" fill="{bg}" stroke="{oc}" stroke-width="{SW}"/>'
            f'<path d="M8.4 2.8l7.2 7.8M15.6 2.8l-7.2 7.8" stroke="{bg}" stroke-width="5"/>'
            f'<path d="M8.4 2.8l7.2 7.8M15.6 2.8l-7.2 7.8" stroke="{dc}" stroke-width="{SW}"/>')


def opt_e(oc, dc, bg):
    return (f'<circle cx="7" cy="7" r="5.6" fill="{bg}"/>'
            f'<path d="M7 1.8A5.2 5.2 0 0 0 7 12.2Z" fill="{oc}"/><path d="M7 1.8A5.2 5.2 0 0 1 7 12.2Z" fill="{dc}"/>')


def opt_f(oc, dc, bg):
    arc = "M7 2.4A4.6 4.6 0 0 0 7 11.6"
    hx = "M5.2 5.2l5.4 5.4M5.2 8.8l5.4-5.4"
    return (f'<path d="{arc}Z" fill="{bg}"/><path d="{hx}" stroke="{bg}" stroke-width="5"/>'
            f'<path d="{arc}" stroke="{oc}" stroke-width="{SW}"/><path d="{hx}" stroke="{dc}" stroke-width="{SW}"/>')


OPTIONS = [("A", "O with an x inside", opt_a), ("B", "X with an o on it", opt_b), ("C", "Stacked", opt_c),
           ("D", "Side by side", opt_d), ("E", "Split dot", opt_e), ("F", "First try", opt_f)]


def svg(body, size):
    return (f'<svg viewBox="0 0 14 14" width="{size}" height="{size}" fill="none" stroke-linecap="round" '
            f'style="overflow:visible;display:block">{body}</svg>')


def panel(name, tokens, oc, dc):
    bg, line, text, text3 = tokens["tile"], tokens["tile-border"], tokens["text"], tokens["text-3"]
    cells = []
    for key, label, fn in OPTIONS:
        body = fn(oc, dc, bg)
        cells.append(
            f'<div class="opt"><div class="big" style="--line:{line}">{svg(body, 84)}</div>'
            f'<div class="lbl" style="color:{text}"><b>{key}</b> {label}</div>'
            f'<div class="row"><div class="tk" style="color:{text3}">32</div><div class="nm" style="color:{text}">Run game</div>'
            f'<div class="tk" style="color:{text3}">1</div></div>'
            f'<div class="track" style="background:{line}"><span class="mk" style="left:62%">{svg(body, 14)}</span></div></div>')
    return f'<section class="panel" style="background:{bg}"><h2 style="color:{text}">{name}</h2><div class="grid">{"".join(cells)}</div></section>'


def page():
    lv, ne = team_line_colors.for_both(["LV", "NE"])
    dark = panel("Dark", theme.DARK, lv["dc"], ne["dc"])
    light = panel("Light", theme.LIGHT, lv["lc"], ne["lc"])
    css = """
*{box-sizing:border-box;margin:0}
body{font-family:Inter,system-ui,sans-serif;background:#888;padding:16px;display:flex;flex-direction:column;gap:16px;align-items:center}
.panel{border-radius:20px;padding:16px;width:100%;max-width:400px}
h2{font-size:12px;letter-spacing:.12em;text-transform:uppercase;margin-bottom:12px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px 16px}
.big{height:110px;display:flex;align-items:center;justify-content:center;position:relative}
.big:before{content:"";position:absolute;left:0;right:0;top:50%;height:18px;margin-top:-9px;background:var(--line)}
.big svg{position:relative}
.lbl{font-size:12px;margin:4px 0 8px}
.row{display:grid;grid-template-columns:20px 1fr 20px;align-items:baseline;margin-bottom:6px}
.tk{font-size:8.5px;font-weight:700}.tk:last-child{text-align:right}
.nm{text-align:center;font-size:12px;font-weight:700}
.track{position:relative;height:3px;border-radius:2px;margin:0 2px 10px}
.mk{position:absolute;top:50%;margin:-7px 0 0 -7px}
"""
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>Tie Marks Mockup</title><link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap' rel='stylesheet'>"
            f"<style>{css}</style></head><body>{dark}{light}</body></html>")


if __name__ == "__main__":
    out = os.path.join(ROOT, "mockups", "tie-marks.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page())
    print("Wrote", out)
