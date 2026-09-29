"""
Condensed Game Info + scoring by quarter mockup (2026-09-29) -- NOT part of the live build.

The expanded Game Info card got a finished game's scoring by quarter (render_page1.linescore_html,
Jason's mock). This tries three ways to bring it into the condensed view's Game Info card, which
today is two lines (time + date / weather, then city / TV):

  A "Table added"      -- both lines stay; a small version of the quarter table goes under them.
  B "Table for time"   -- once a game is final its kickoff time matters less: the table takes
                          line 1's place, and the date moves onto the city line.
  C "One-line strip"   -- both lines stay; one short line underneath gives each quarter as
                          away-home (Q1 0-7 · Q2 7-3 ...), in the top bar's away-left order.

Each variant is written as the real game page (render_page1.write_all with game_body_compact
swapped out), into a copy of site/ in the folder given on the command line, as
game/ls-a-<id>.html etc., to serve and screenshot. Nothing in the real build changes.

Run after a normal build (so site/ and data/ exist):
    python mockups/build_linescore_condensed_mockup.py <scratch folder>
"""

import json
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import render_page1 as p1  # noqa: E402

GAMES = ["2026_03_PHI_CHI", "2026_01_NO_DET"]   # a regular final, and an overtime one
esc = p1.esc
ORIGINAL = p1.game_body_compact


def mini_table(d):
    return p1.linescore_html(d).replace('class="ls"', 'class="ls ls-mini"', 1)


def variant_a(d):
    return ORIGINAL(d) + (mini_table(d) if d.get("linescore") else "")


def variant_b(d):
    if not d.get("linescore"):
        return ORIGINAL(d)
    venue = d.get("venue") or {}
    day, _t = p1.fmt_when(d)
    return (mini_table(d)
            + f'<div class="gc-row gc-2"><div class="city">{esc(venue.get("city") or "")} · {esc(day)}</div>'
            f'<div class="gc-right"><div class="weather">{p1.weather_html(d)}</div>'
            f'<div class="network">{esc(p1.fmt_network(d.get("networks")))}</div></div></div>')


def variant_c(d):
    ls = d.get("linescore")
    if not ls:
        return ORIGINAL(d)
    parts = "".join(
        f'<span><i>{"Q" + l if l != "OT" else "OT"}</i> {a}–{h}</span>'
        for l, a, h in zip(ls["labels"], ls["away"], ls["home"]))
    return ORIGINAL(d) + f'<div class="gc-strip">{parts}</div>'


CSS = """
.c-game .ls-mini{margin:4px -6px 0;padding:0 6px 2px;border-bottom:0}
.c-game .ls-mini thead th{font-size:10px;padding-bottom:2px}
.c-game .ls-mini tbody th,.c-game .ls-mini td{font-size:12px;padding:2px 0}
.c-game .ls-mini thead th:first-child{width:3.2em}
.c-game .gc-right{display:flex;align-items:center;gap:12px}
.c-game .gc-strip{display:flex;justify-content:space-between;gap:6px;margin-top:4px;padding-top:4px;
  border-top:1px solid var(--tile-border-soft);font-size:12px;font-variant-numeric:tabular-nums;white-space:nowrap}
.c-game .gc-strip i{font-style:normal;font-size:10px;font-weight:700;letter-spacing:.04em;color:var(--text-3)}
"""


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: build_linescore_condensed_mockup.py <scratch folder>")
    out = sys.argv[1]
    if os.path.exists(out):
        shutil.rmtree(out)
    shutil.copytree(os.path.join(ROOT, "site"), out)
    with open(os.path.join(ROOT, "data", "matchups.json"), encoding="utf-8") as f:
        data = json.load(f)
    p1.P1_CSS += CSS
    for tag, fn in (("a", variant_a), ("b", variant_b), ("c", variant_c)):
        p1.game_body_compact = fn
        details = {f"ls-{tag}-{gid}": data["game_details"][gid] for gid in GAMES}
        warnings = []
        p1.write_all({"game_details": details, "player_weeks": data.get("player_weeks")}, out, warnings)
        if warnings:
            raise SystemExit("\n".join(warnings))
    print(f"Wrote {out}/game/ls-[abc]-<game>.html for {', '.join(GAMES)}")


if __name__ == "__main__":
    main()
