"""
Stat Leaders condensed view -- layout mockup (2026-10-07), NOT part of the live build.

The condensed view (render_leaders.py) shows each stat's leader (first place only, up to three tied)
in a two-a-row grid that ignores the categories, so Passing's third stat shares a row with Rushing's
first. Jason asked for better ways to lay it out around the real grouping: 3 passing, 3 rushing,
3 receiving, 6 defense, 2 kicking, 2 returns. Four ideas, plus the current grid to compare:

  A "Category rows"  -- one row of tiles a category, its name over the row: 3 across for passing,
                        rushing and receiving, defense in two rows of 3, kicking + returns sharing a
                        2 x 2 (each a half-width column). Last names in the narrow tiles.
  B "Category cards" -- like Player Stats' condensed view: each category under its pill title (icon +
                        name), its stats as columns, no tile backgrounds; kicking and returns side by
                        side as half-width cards, their two stats stacked.
  C "Leader list"    -- one column, a line a stat under category headings: stat, pill, full name,
                        number. Reads like a box score.
  D "Two columns"    -- offense down the left (passing, rushing, receiving: 9 stats), defense and
                        special teams down the right (defense, kicking, returns: 10). Each stat is
                        its name and number over the pill and full name.

Every layout fills the screen between the header and the bottom bar (a 375 x 812 phone), like the
real condensed view. Data is render_leaders.build's, so it's the real page's numbers.

Run after build_data.py:
    python mockups/build_leaders_condensed_mockup.py [out.html]
Writes mockups/leaders-condensed.html (self-contained). #b opens on layout B.
"""

import html
import json
import re
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import render_leaders as rl  # noqa: E402
import theme  # noqa: E402
from render_page1 import CHEV, MINUS, PLUS  # noqa: E402

esc = rl.esc


def load():
    with open(os.path.join(ROOT, "data", "matchups.json"), encoding="utf-8") as f:
        data = json.load(f)
    return data, rl.build(data.get("player_weeks"))


def firsts(s):
    return [r for r in s["rows"] if r[0] == 1]


def icon(d, cat):
    return f'<span class="ic">{d["icons"].get(cat, "")}</span>'


SUFFIX = re.compile(r"\s+(Jr\.?|Sr\.?|II|III|IV|V)$")


def name_for(p, form):
    """form: "full" (Bryce Young), "short" (B. Young) or "last" (Young -- no Jr. / III)."""
    if form == "full":
        return p[1]
    if form == "short":
        return p[0]
    return SUFFIX.sub("", p[1]).split(" ", 1)[-1]


def leaders_html(d, s, form="full", cls="ld"):
    """The tied-for-first rows: pill + name, at most three, then "+N more tied"."""
    f = firsts(s)
    rows = "".join(f'<span class="{cls}">{d["pills"][d["players"][r[1]][3]]}'
                   f'<span class="nm">{esc(name_for(d["players"][r[1]], form))}</span></span>' for r in f[:3])
    if len(f) > 3:
        rows += f'<span class="more">+{len(f) - 3} more tied</span>'
    return rows or '<span class="nm none">—</span>'


def value(s):
    f = firsts(s)
    return f[0][2] if f else "—"


def by_cat(d):
    out = {}
    for s in d["stats"]:
        out.setdefault(s["cat"], []).append(s)
    return out


CATS = dict(rl.CATS)


# ---------------------------------------------------------------- A: category rows

def variant_a(d):
    c = by_cat(d)

    def tile(s):
        return (f'<div class="a-t"><span class="a-l">{esc(s["short"])}</span><span class="a-v">{value(s)}</span>'
                f'<span class="a-ls">{leaders_html(d, s, form="last")}</span></div>')

    def row(cats):
        heads = "".join(f'<div class="a-h" style="grid-column:span {12 // len(cats) if len(cats) > 1 else 12}">{icon(d, k)}{CATS[k]}</div>'
                        for k in cats)
        stats = [s for k in cats for s in c[k]]
        span = 4
        if len(cats) > 1:   # kicking + returns: each a half-width column, its two stats stacked
            stats = [s for pair in zip(*(c[k] for k in cats)) for s in pair]
            span = 6
        tiles = "".join(f'<div style="grid-column:span {span}">{tile(s)}</div>' for s in stats)
        rows = -(-len(stats) * span // 12)   # rows of tiles: the row's share of the height
        return f'<section class="a-row" style="flex:{rows}">{heads}{tiles}</section>'

    return (row(["passing"]) + row(["rushing"]) + row(["receiving"]) + row(["defense"])
            + row(["kicking", "returns"]))


# ---------------------------------------------------------------- B: category cards

def variant_b(d):
    c = by_cat(d)

    def card(k, cols, half=False):
        stats = "".join(f'<div class="b-s"><span class="b-l">{esc(s["short"])}</span><span class="b-v">{value(s)}</span>'
                        f'<span class="b-ls">{leaders_html(d, s, form="short")}</span></div>' for s in c[k])
        return (f'<section class="b-card{" half" if half else ""}"><span class="ttl">{icon(d, k)}{CATS[k]}</span>'
                f'<div class="b-grid" style="grid-template-columns:repeat({cols},minmax(0,1fr))">{stats}</div></section>')

    return (card("passing", 3) + card("rushing", 3) + card("receiving", 3) + card("defense", 3)
            + f'<div class="b-pair">{card("kicking", 1, True)}{card("returns", 1, True)}</div>')


# ---------------------------------------------------------------- C: leader list

def variant_c(d):
    out = []
    for k, name in rl.CATS:
        out.append(f'<div class="c-h">{icon(d, k)}{name}</div>')
        for s in by_cat(d)[k]:
            f = firsts(s)
            if not f:
                out.append(f'<div class="c-r"><span class="c-l">{esc(s["short"])}</span><span></span><span class="nm none">—</span><span class="c-v">—</span></div>')
                continue
            for i, r in enumerate(f[:3]):
                p = d["players"][r[1]]
                out.append(f'<div class="c-r{" tie" if i else ""}"><span class="c-l">{esc(s["short"]) if not i else ""}</span>'
                           f'{d["pills"][p[3]]}<span class="nm">{esc(p[1])}</span><span class="c-v">{r[2] if not i else ""}</span></div>')
            if len(f) > 3:
                out.append(f'<div class="c-r tie"><span></span><span></span><span class="more">+{len(f) - 3} more tied</span><span></span></div>')
    return "".join(out)


# ---------------------------------------------------------------- D: two columns

def variant_d(d):
    c = by_cat(d)

    def col(cats):
        parts = []
        for k in cats:
            parts.append(f'<div class="d-h">{icon(d, k)}{CATS[k]}</div>')
            parts += [f'<div class="d-s"><div class="d-top"><span class="d-l">{esc(s["short"])}</span><span class="d-v">{value(s)}</span></div>'
                      f'{leaders_html(d, s)}</div>' for s in c[k]]
        return f'<div class="d-col">{"".join(parts)}</div>'

    return col(["passing", "rushing", "receiving"]) + col(["defense", "kicking", "returns"])


# ---------------------------------------------------------------- now: the current grid

def variant_now(d):
    tiles = []
    for s in d["stats"]:
        tiles.append(f'<div class="n-t"><span class="n-l">{icon(d, s["cat"])}<span class="n-s">{esc(s["short"])}</span>'
                     f'<span class="n-v">{value(s)}</span></span>{leaders_html(d, s)}</div>')
    return "".join(tiles)


CSS = """
:root{--bbar:""" + theme.BBAR_HEIGHT + """;--text:var(--aag-text);--text-2:var(--aag-text-2);--text-3:var(--aag-text-3);
  --line:var(--aag-tile-border);--line-soft:var(--aag-tile-border-soft);--top-h:72px;--mock-h:58px}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;overflow:hidden;background:var(--aag-bg)}
body{color:var(--text);font-family:Inter,system-ui,-apple-system,sans-serif;-webkit-font-smoothing:antialiased}
button{font:inherit;color:inherit}
.abbr{line-height:1;font-family:Saira,Inter,system-ui,sans-serif;font-weight:800;font-style:italic;font-variation-settings:'wdth' 95;letter-spacing:.02em}
.ic{display:inline-flex;align-items:center;flex:none;margin-right:5px}
.ic svg{display:block;width:auto;height:1em}
.tpill{display:inline-flex;align-items:center;justify-content:center;height:12px;min-width:30px;padding:0 3px;border-radius:999px;
  border:1.5px solid transparent;color:var(--pl);font-size:7.5px;white-space:nowrap;flex:none;
  background:linear-gradient(var(--pf1),var(--pf2)) padding-box,linear-gradient(var(--pr1),var(--pr2)) border-box}
.nm{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:600}
.none{color:var(--text-3)}
.more{font-size:9px;color:var(--text-3)}
.num{font-family:Teko,Inter,sans-serif;font-weight:600;line-height:.9}

.mock{height:var(--mock-h);display:flex;flex-wrap:wrap;justify-content:center;align-content:center;gap:4px;padding:4px 8px;
  border-bottom:1px dashed var(--line);font-size:11px}
.mock b{font-size:9px;letter-spacing:.06em;text-transform:uppercase;color:var(--text-3);align-self:center}
.mock button{background:none;border:1px solid var(--line);border-radius:999px;padding:2px 8px;cursor:pointer}
.mock button.on{background:var(--text);color:var(--aag-bg);border-color:var(--text)}
.top{display:flex;flex-direction:column;align-items:center;gap:2px;padding:8px 16px 6px;height:var(--top-h)}
.yr{font-size:34px}
.rs-line{display:flex;gap:6px;align-items:baseline;font-size:11px;white-space:nowrap}
.rs{letter-spacing:.12em;text-transform:uppercase;color:var(--text-2);font-weight:700}
.thru{color:var(--text-3)}.thru::before{content:"·";margin-right:6px}
/* each layout gets the space the real condensed view has (header to bottom bar) -- minus the mock strip */
.v{display:none;height:calc(100dvh - var(--mock-h) - var(--top-h) - var(--bbar));max-width:600px;margin:0 auto;padding:2px 16px 8px;overflow-y:auto;scrollbar-width:none}
.v::-webkit-scrollbar{display:none}
.v.on{display:flex;flex-direction:column}

/* A: category rows */
.a-row{flex:1;min-height:0;display:grid;grid-template-columns:repeat(12,minmax(0,1fr));grid-template-rows:auto;grid-auto-rows:1fr;gap:3px 4px;margin-top:4px}
.a-row:first-child{margin-top:0}
.a-h{display:flex;align-items:center;font-size:10px;font-weight:900;letter-spacing:.1em;text-transform:uppercase;padding:2px 2px 0}
.a-t{height:100%;display:flex;flex-direction:column;gap:1px;background:var(--aag-tile-hover);border-radius:10px;padding:4px 7px;min-width:0}
.a-l{font-size:9px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--text-2)}
.a-v{font-family:Teko,Inter,sans-serif;font-size:22px;line-height:.95;font-weight:600}
.a-ls{display:flex;flex-direction:column;gap:2px;min-width:0}
.ld{display:flex;align-items:center;gap:4px;min-width:0;font-size:11px;line-height:13px}
/* in the narrow columns (A, B) a long name wraps to a second line rather than being cut */
:is(.a-t,.b-s) .nm{white-space:normal;overflow:visible;line-height:12px}
.b-s .ld{text-align:left}

/* B: category cards -- pill titles like every card on the site, stats as columns */
.b-card{flex:1;display:flex;flex-direction:column;align-items:center;min-height:0}
.v-b .b-card:nth-child(4){flex:1.6}
.ttl{display:inline-flex;align-items:center;font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;
  border:1px solid var(--line);border-radius:999px;padding:2px 9px;line-height:1.2;flex:none}
.b-grid{flex:1;width:100%;display:grid;gap:4px 8px;align-content:center;margin-top:3px}
.b-s{display:flex;flex-direction:column;align-items:center;min-width:0;text-align:center}
.b-l{font-size:9px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--text-2)}
.b-v{font-family:Teko,Inter,sans-serif;font-size:24px;line-height:.95;font-weight:600}
.b-ls{display:flex;flex-direction:column;align-items:center;gap:2px;max-width:100%}
.b-ls .ld{max-width:100%}
.b-pair{flex:1.5;display:flex;gap:10px}
.b-pair .b-card{flex:1}

/* C: leader list */
.c-h{display:flex;align-items:center;font-size:10px;font-weight:900;letter-spacing:.1em;text-transform:uppercase;
  padding:5px 2px 1px;border-bottom:1px solid var(--line-soft);flex:none}
.c-h:first-child{padding-top:0}
.c-r{flex:1 1 0;min-height:17px;display:grid;grid-template-columns:62px 30px minmax(0,1fr) 46px;gap:6px;align-items:center;font-size:12px}
.c-l{font-size:9.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--text-2)}
.c-v{text-align:right;font-weight:700;font-variant-numeric:tabular-nums;font-size:13px}

/* D: two columns -- offense left, defense + special teams right */
.v-d.on{flex-direction:row;gap:10px}
.d-col{flex:1;min-width:0;display:flex;flex-direction:column}
.d-h{display:flex;align-items:center;font-size:10px;font-weight:900;letter-spacing:.1em;text-transform:uppercase;padding:6px 2px 1px;flex:none;
  border-bottom:1px solid var(--line-soft)}
.d-h:first-child{padding-top:0}
.d-s{flex:1 1 0;display:flex;flex-direction:column;justify-content:center;gap:1px;padding:2px 2px;min-height:0}
.d-top{display:flex;align-items:baseline;justify-content:space-between;gap:4px}
.d-l{font-size:9px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--text-2)}
.d-v{font-family:Teko,Inter,sans-serif;font-size:18px;line-height:.9;font-weight:600}

/* now: the current grid */
.v-now.on{display:grid;grid-template-columns:1fr 1fr;grid-auto-rows:minmax(48px,1fr);gap:4px}
.n-t{display:flex;flex-direction:column;justify-content:center;gap:1px;min-width:0;background:var(--aag-tile-hover);border-radius:10px;padding:2px 7px}
.n-l{display:flex;align-items:center;gap:0;font-size:9.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--text-2)}
.n-s{flex:1}
.n-v{font-family:Teko,Inter,sans-serif;font-size:19px;line-height:.9;font-weight:600;color:var(--text)}

.bottombar{position:fixed;left:0;right:0;bottom:0;z-index:16;height:var(--bbar);padding-bottom:env(safe-area-inset-bottom);
  background:var(--aag-bar-bg);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px)}
.bar-in{position:relative;max-width:600px;height:52px;margin:0 auto;display:flex;align-items:flex-start;justify-content:center;padding-top:10px}
.week{color:inherit;text-decoration:none;display:inline-flex;align-items:center;gap:6px;font-size:16px;line-height:19px;padding:6px 12px}
.week .chev{width:12px;height:12px}
.toggle{position:absolute;right:16px;top:9px;width:34px;height:34px;border:0;background:none;display:flex;align-items:center;justify-content:center}
.toggle .i-minus{display:none}
""" + theme.MENU_CSS

NAMES = {"a": "A · Category rows", "b": "B · Category cards", "c": "C · Leader list", "d": "D · Two columns", "now": "Now"}

JS = r"""
(function () {
  function pick(k) {
    document.querySelectorAll('[data-v]').forEach(function (b) { b.classList.toggle('on', b.getAttribute('data-v') === k); });
    document.querySelectorAll('.v').forEach(function (v) { v.classList.toggle('on', v.classList.contains('v-' + k)); });
  }
  document.querySelectorAll('[data-v]').forEach(function (b) { b.addEventListener('click', function () { pick(b.getAttribute('data-v')); }); });
  pick(location.hash.slice(1) || 'a');
})();
"""


def page(data, d):
    bodies = {"a": variant_a(d), "b": variant_b(d), "c": variant_c(d), "d": variant_d(d), "now": variant_now(d)}
    mock = '<div class="mock"><b>Mockup</b>' + "".join(f'<button data-v="{k}">{n}</button>' for k, n in NAMES.items()) + "</div>"
    top = (f"<header class='top'><span class='yr abbr'>{esc(data.get('season') or '')}</span><span class='rs-line'>"
           f"<span class='rs'>Stat Leaders</span><span class='thru'>Through Week {d['through']}</span></span></header>")
    views = "".join(f'<section class="v v-{k}">{b}</section>' for k, b in bodies.items())
    bar = ("<nav class='bottombar'><div class='bar-in'>" + theme.menu_html("", "leaders")
           + f"<a class='week' href='#'>{CHEV}<span>Week {d['through'] + 1}</span></a>"
           + f"<button class='toggle' type='button'><span class='i-plus'>{PLUS}</span><span class='i-minus'>{MINUS}</span></button></div></nav>")
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'>"
            f"<title>Stat Leaders condensed mockup</title><script>{theme.THEME_HEAD_JS}</script>"
            "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;700;900&display=swap' rel='stylesheet'>"
            "<link href='https://fonts.googleapis.com/css2?family=Saira:ital,wdth,wght@1,50..125,400..900&family=Teko:wght@400..700&display=swap' rel='stylesheet'>"
            f"<style>{theme.THEME_CSS}{CSS}</style></head><body>{mock}{top}{views}{bar}"
            f"<script>{theme.THEME_JS}</script><script>{JS}</script></body></html>")


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "mockups", "leaders-condensed.html")
    data, d = load()
    with open(out, "w", encoding="utf-8") as f:
        f.write(page(data, d))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
