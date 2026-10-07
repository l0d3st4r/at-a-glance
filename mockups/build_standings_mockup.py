"""
Standings page mockup (2026-10-07) -- NOT part of the live build.

A page that lives outside Page 0 / 1 / 2, reached from a menu and from tapping a team page's
division title (Jason, 2026-10-07). Title: the year, then "Regular Season". Three buttons --
Division / Conference / League -- styled like the Player Stats switch (chosen one at full
strength, the others faded). Every row is one line: W, L, T, PCT, DIV, CONF, STRK. Conference
shows the playoff picture (seeds 1-7, a line under the 7th); League is 1-32. A legend at the
bottom covers the columns and the clinch marks, which follow the NFL's own letters:
x = playoff berth, y = division, z = first-round bye, * = home field throughout.

Three looks, same data, picked with the mockup-only strip at the top:
  A "Team page table" -- the team page's division table, extended: helmet + abbreviation, Inter
                         numbers, quiet column heads. Clinch letter in its own slot at the left.
  B "Team pills"      -- the team's pill in place of helmet + abbreviation, Teko numbers, the
                         streak in win / loss colors, DIV and CONF stepped back in gray.
  C "Grouped cards"   -- each group on a soft panel with banded rows; Conference splits into
                         Division leaders / Wild card / In the hunt instead of a plain line.

"Clinch example" (mockup only) sprinkles made-up x / y / z / * marks on a few teams so they
can be seen in place -- nobody has clinched anything in October.

Order is win pct, then conference pct, then division pct, then wins -- not the NFL's real
tiebreakers (head-to-head, common games, strength of victory...), which are out of scope here.

Data: nflverse's 2026 schedule (every finished regular-season game). Run:
    python mockups/build_standings_mockup.py [out.html]
Writes mockups/standings.html by default -- one self-contained file (helmets inlined).
"""

import html
import os
import sys
import urllib.parse

import nflreadpy as nfl
import polars as pl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import helmets  # noqa: E402
import theme  # noqa: E402
from divisions import DIVISIONS, normalize_abbr  # noqa: E402

SEASON = 2026
CONFS = ("AFC", "NFC")
DIV_NAMES = ("East", "North", "South", "West")

# Made-up clinch marks for the "Clinch example" toggle, chosen at build time from the real order
# so they look plausible: each conference's 1 seed "*", 2 seed "z", 3-4 seeds "y", 5 seed "x".
EXAMPLE_MARKS = {1: "*", 2: "z", 3: "y", 4: "y", 5: "x"}


def esc(v):
    return html.escape(str(v), quote=True)


# ---------------------------------------------------------------- data

def blank():
    return {"w": 0, "l": 0, "t": 0, "dw": 0, "dl": 0, "dt": 0, "cw": 0, "cl": 0, "ct": 0, "results": []}


def standings():
    s = nfl.load_schedules(seasons=[SEASON])
    s = s.filter((pl.col("game_type") == "REG") & pl.col("home_score").is_not_null()).sort(["gameday", "gametime"])
    rec = {t: blank() for t in DIVISIONS}
    week = 0
    for g in s.iter_rows(named=True):
        week = max(week, g["week"])
        a, h = normalize_abbr(g["away_team"]), normalize_abbr(g["home_team"])
        for me, opp, mine, theirs in ((a, h, g["away_score"], g["home_score"]), (h, a, g["home_score"], g["away_score"])):
            r = rec[me]
            res = "w" if mine > theirs else "l" if mine < theirs else "t"
            r[res] += 1
            r["results"].append(res.upper())
            if DIVISIONS[me] == DIVISIONS[opp]:
                r["d" + res] += 1
            if DIVISIONS[me][:3] == DIVISIONS[opp][:3]:
                r["c" + res] += 1
    rows = []
    for t, r in rec.items():
        streak = ""
        if r["results"]:
            last, n = r["results"][-1], 0
            for x in reversed(r["results"]):
                if x != last:
                    break
                n += 1
            streak = f"{last}{n}"
        rows.append({"team": t, "div": DIVISIONS[t], "conf": DIVISIONS[t][:3], **r, "streak": streak,
                     "pct": pct(r["w"], r["l"], r["t"]), "cpct": pct(r["cw"], r["cl"], r["ct"]),
                     "dpct": pct(r["dw"], r["dl"], r["dt"])})
    return rows, week


def pct(w, l, t):
    gp = w + l + t
    return (w + 0.5 * t) / gp if gp else 0.0


def order(rows):
    return sorted(rows, key=lambda r: (-r["pct"], -r["cpct"], -r["dpct"], -r["w"], r["team"]))


def seeds(rows, conf):
    """Division leaders take 1-4, everyone else from 5 down."""
    mine = [r for r in rows if r["conf"] == conf]
    leaders = [order([r for r in mine if r["div"] == f"{conf} {d}"])[0] for d in DIV_NAMES]
    rest = [r for r in mine if r not in leaders]
    return order(leaders) + order(rest)


# ---------------------------------------------------------------- markup

def helmet_uri(team):
    return "data:image/svg+xml," + urllib.parse.quote(helmets.helmet_svg(team, id_prefix=f"h{team}"))


def helmet_css():
    return "".join(f'.h-{t}{{background-image:url("{helmet_uri(t)}")}}' for t in DIVISIONS)


def fmt_pct(p, gp):
    if not gp:
        return ".000"
    return f"{p:.3f}".lstrip("0") if p < 1 else "1.000"


def rec(w, l, t):
    return f"{w}-{l}-{t}" if t else f"{w}-{l}"


def team_bits(r):
    team = r["team"]
    return {
        "helmet": f'<i class="hm hl h-{team}"></i>',
        "abbr": f'<span class="abbr">{esc(team)}</span>',
        "pill": helmets.pill_html(team, team),
        "mark": f'<span class="mk" data-team="{team}"></span>',
    }


HEADS = ("W", "L", "T", "PCT", "DIV", "CONF", "STRK")


def stat_cells(r):
    gp = r["w"] + r["l"] + r["t"]
    sk = r["streak"][:1].lower()
    return (f'<span class="n w">{r["w"]}</span><span class="n l">{r["l"]}</span><span class="n t">{r["t"]}</span>'
            f'<span class="n pct">{fmt_pct(r["pct"], gp)}</span>'
            f'<span class="n sub">{rec(r["dw"], r["dl"], r["dt"])}</span>'
            f'<span class="n sub">{rec(r["cw"], r["cl"], r["ct"])}</span>'
            f'<span class="n stk stk-{sk}">{esc(r["streak"]) or "—"}</span>')


def head_row(label, seeded):
    lead = '<span></span>' if seeded else ''
    return (f'<div class="row head">{lead}<span class="grp">{esc(label)}</span>'
            + "".join(f'<span class="n">{h}</span>' for h in HEADS) + "</div>")


def row(r, variant, seed=None, cut=False, even=False, end=False):
    b = team_bits(r)
    lead = f'<span class="seed">{seed}</span>' if seed is not None else ""
    if variant == "b":
        who = f'<span class="who">{b["pill"]}{b["mark"]}</span>'
    elif variant in ("a", "d"):
        who = f'<span class="who">{b["mark"]}{b["helmet"]}{b["abbr"]}</span>'
    else:
        who = f'<span class="who">{b["helmet"]}{b["abbr"]}{b["mark"]}</span>'
    cls = "row" + (" cut" if cut else "") + (" even" if even else "") + (" end" if end else "")
    return f'<div class="{cls}" data-team="{r["team"]}">{lead}{who}{stat_cells(r)}</div>'


def group(label, rows, variant, seeded=False, cut_after=None, bands=None):
    bands = dict(bands or {})
    if variant == "d" and 1 in bands:
        # D: the first section's name goes on the column-heads line, like a division's name does
        # in the Division view -- no empty line between the conference title and the first team
        # (Jason, 2026-10-07)
        label = bands.pop(1)
    body = []
    for i, r in enumerate(rows, 1):
        if i in bands:
            body.append(f'<div class="band">{esc(bands[i])}</div>')
        # "end": the last team in the group or in a section -- no line under it on D
        end = i == len(rows) or (i + 1) in bands
        body.append(row(r, variant, seed=i if seeded else None, cut=(cut_after == i), even=(i % 2 == 0), end=end))
    return (f'<section class="grp-box{" seeded" if seeded else ""}">'
            f'{head_row(label, seeded)}{"".join(body)}</section>')


def view_division(rows, variant):
    """AFC, then its four divisions (titled just East / North ...), then NFC (Jason, 2026-10-07)."""
    out = []
    for c in CONFS:
        out.append(f'<h2 class="conf-h">{c}</h2>')
        for d in DIV_NAMES:
            name = f"{c} {d}"
            out.append(group(d, order([r for r in rows if r["div"] == name]), variant))
    return "".join(out)


def view_conference(rows, variant):
    out = []
    for c in CONFS:
        if variant == "d":
            # D: the same AFC / NFC heading as the Division view, over the column heads (Jason, 2026-10-07)
            out.append(f'<h2 class="conf-h">{c}</h2>')
            out.append(group("", seeds(rows, c), variant, seeded=True,
                             bands={1: "Division leaders", 5: "Wild card", 8: "In the hunt"}))
        elif variant == "c":
            out.append(group(c, seeds(rows, c), variant, seeded=True,
                             bands={1: "Division leaders", 5: "Wild card", 8: "In the hunt"}))
        else:
            out.append(group(c, seeds(rows, c), variant, seeded=True, cut_after=7))
    return "".join(out)


def view_league(rows, variant):
    # D: no "NFL" over the 1-32 list, just the column heads (Jason, 2026-10-07)
    return group("" if variant == "d" else "NFL", order(rows), variant, seeded=True)


LEGEND = (
    ("W", "Wins"), ("L", "Losses"), ("T", "Ties"), ("PCT", "Win percentage, ties count as half a win"),
    ("DIV", "Record against division opponents"), ("CONF", "Record against conference opponents"),
    ("STRK", "Current streak: W3 = three wins in a row"),
)
CLINCH = (("x", "Clinched a playoff berth"), ("y", "Clinched the division"),
          ("z", "Clinched a first-round bye"), ("*", "Clinched the division and home field throughout the playoffs"))


def legend_html():
    cols = "".join(f'<div><dt>{k}</dt><dd>{esc(v)}</dd></div>' for k, v in LEGEND)
    marks = "".join(f'<div><dt class="mkk">{k}</dt><dd>{esc(v)}</dd></div>' for k, v in CLINCH)
    return (f'<footer class="legend"><h3>Key</h3><dl>{cols}</dl>'
            f'<h3>Clinched</h3><dl>{marks}</dl>'
            f'<p class="note">Seeds 1–4 go to the division winners; 5–7 are the wild cards.</p></footer>')


def variant_html(rows, v, week):
    title = {
        "a": f'<h1 class="title"><span class="ttl"><span class="yr">{SEASON}</span> Regular Season</span></h1>',
        "b": f'<h1 class="title stack"><span class="yr-big">{SEASON}</span><span class="rs">Regular Season</span></h1>',
        "c": f'<h1 class="title"><span class="yr abbr">{SEASON}</span> <span class="rs">Regular Season</span></h1>',
    }
    title["d"] = f'<h1 class="title stack"><span class="yr-big abbr">{SEASON}</span><span class="rs">Regular Season</span></h1>'
    title = title[v]
    tabs = "".join(f'<button class="sw-tab{" on" if k == "division" else ""}" type="button" data-view="{k}">{k.title()}</button>'
                   for k in ("division", "conference", "league"))
    panes = (f'<div class="pane on" data-pane="division">{view_division(rows, v)}</div>'
             f'<div class="pane" data-pane="conference">{view_conference(rows, v)}</div>'
             f'<div class="pane" data-pane="league">{view_league(rows, v)}</div>')
    return (f'<div class="variant v-{v}{" on" if v == "a" else ""}" data-variant="{v}">'
            f'<header class="top">{title}<div class="thru">Through Week {week}</div>'
            f'<div class="sw" role="tablist">{tabs}</div></header>'
            f'{panes}{legend_html()}</div>')


def example_marks(rows):
    out = {}
    for c in CONFS:
        for i, r in enumerate(seeds(rows, c), 1):
            if i in EXAMPLE_MARKS:
                out[r["team"]] = EXAMPLE_MARKS[i]
    return out


CSS = """
:root{--bg:var(--aag-bg);--text:var(--aag-text);--text-2:var(--aag-text-2);--text-3:var(--aag-text-3);
  --line:var(--aag-tile-border);--line-soft:var(--aag-tile-border-soft);--bbar:""" + theme.BBAR_HEIGHT + """}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:var(--bg)}
body{min-height:100vh;color:var(--text);font-family:Inter,system-ui,-apple-system,sans-serif;-webkit-font-smoothing:antialiased}
.abbr{line-height:1;font-family:Saira,Inter,system-ui,sans-serif;font-weight:800;font-style:italic;
  font-variation-settings:'wdth' 95;letter-spacing:.02em}
.tpill{display:inline-flex;align-items:center;justify-content:center;height:20px;min-width:48px;padding:0 6px;
  border-radius:999px;border:2px solid transparent;color:var(--pl);font-size:11px;white-space:nowrap;
  background:linear-gradient(var(--pf1),var(--pf2)) padding-box,linear-gradient(var(--pr1),var(--pr2)) border-box}

/* mockup-only strip */
.mock{position:sticky;top:0;z-index:20;display:flex;flex-wrap:wrap;justify-content:center;gap:6px 12px;
  padding:8px 16px;background:var(--aag-bar-bg);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);
  border-bottom:1px dashed var(--line);font-size:12px;color:var(--text-2)}
.mock b{font-weight:700;color:var(--text-3);text-transform:uppercase;letter-spacing:.06em;font-size:10px;align-self:center}
.mock button{font:inherit;color:var(--text);background:none;border:1px solid var(--line);border-radius:999px;padding:3px 10px;cursor:pointer}
.mock button.on{background:var(--text);color:var(--bg);border-color:var(--text)}
.mock label{display:inline-flex;align-items:center;gap:5px;cursor:pointer}

.wrap{max-width:600px;margin:0 auto;padding:12px 16px calc(24px + var(--bbar))}
.variant{display:none}.variant.on{display:block}

/* title + switch */
.top{display:flex;flex-direction:column;align-items:center;gap:6px;padding:6px 0 10px}
.title{font-size:13px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;text-align:center}
.ttl{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);border-radius:999px;padding:5px 13px;line-height:1.1}
.thru{font-size:11px;color:var(--text-3)}
.sw{display:flex;justify-content:center;gap:4px;margin-top:4px}
.sw-tab{font:inherit;font-size:14px;font-weight:700;color:var(--text);background:none;border:1px solid transparent;
  border-radius:999px;padding:5px 13px;cursor:pointer;opacity:.45;transition:opacity .16s}
.sw-tab.on{opacity:1;border-color:var(--line)}
.sw-tab:hover{opacity:.8}.sw-tab.on:hover{opacity:1}
.pane{display:none}.pane.on{display:block}

/* rows: one line each -- [seed] team W L T PCT DIV CONF STRK */
.grp-box{margin-top:18px}
.row{display:grid;grid-template-columns:minmax(0,1fr) 20px 20px 16px 38px 34px 34px 28px;align-items:center;
  column-gap:4px;padding:5px 4px;font-size:13px;font-variant-numeric:tabular-nums}
.seeded .row{grid-template-columns:16px minmax(0,1fr) 20px 20px 16px 38px 34px 34px 28px}
.row.head{padding:0 4px 4px;font-size:10px;font-weight:700;letter-spacing:.04em;color:var(--text-3)}
.row.head .grp{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--text-2);white-space:nowrap}
.seeded .row.head .grp{grid-column:1/3}
.seeded .row.head>span:first-child{display:none}
.n{text-align:center}
.pct{text-align:right}
.sub{color:var(--text-2);font-size:12px}
.who{display:flex;align-items:center;gap:6px;min-width:0}
.who .hl{display:block;width:22px;height:22px;flex:none;--hs:22px;background-position:center;background-size:contain;background-repeat:no-repeat}
.who .abbr{font-size:14px}
.seed{font-size:11px;font-weight:700;color:var(--text-3);text-align:right}
.row.cut{border-bottom:1px dashed var(--line);padding-bottom:7px;margin-bottom:2px}
.mk{font-size:11px;font-weight:700;color:var(--text-2)}
.mk:empty{display:none}
.hm{filter:drop-shadow(0 calc(var(--hs,48px) * .0455) calc(var(--hs,48px) * .078) var(--aag-helmet-shadow))}

/* A: clinch letter in a fixed slot to the left so helmets line up */
:is(.v-a,.v-d) .mk{display:inline-block;width:8px;text-align:center}
:is(.v-a,.v-d) .row:not(.head){border-bottom:1px solid var(--line-soft)}
:is(.v-a,.v-d) .row.cut{border-bottom:1px dashed var(--line)}
:is(.v-a,.v-d) .yr{font-weight:900}

/* B: pills, Teko numbers, colored streak */
.v-b .title.stack{display:flex;flex-direction:column;align-items:center;gap:0}
.v-b .yr-big{font-family:Teko,Inter,sans-serif;font-size:40px;line-height:.9;font-weight:600;letter-spacing:.02em}
.v-b .rs{font-size:11px;letter-spacing:.12em;color:var(--text-2)}
.v-b .row:not(.head){padding:4px 4px;font-family:Teko,Inter,sans-serif;font-size:18px;line-height:1}
.v-b .row:not(.head) .sub{font-size:16px}
.v-b .w,.v-b .l{font-weight:600}
.v-b .t{color:var(--text-2)}
.v-b .stk-w{color:var(--aag-win)}.v-b .stk-l{color:var(--aag-loss)}.v-b .stk-t{color:var(--aag-tie)}
.v-b .who{gap:3px}
.v-b .mk{font-family:Inter,sans-serif;align-self:flex-start;font-size:10px}
.v-b .seed{font-family:Teko,Inter,sans-serif;font-size:15px;font-weight:500}
.v-b .row.cut{border-bottom:2px solid var(--line)}

/* C: soft panels, banded rows, section bands in Conference */
.v-c .title{display:flex;align-items:baseline;gap:8px;font-size:13px}
.v-c .yr{font-size:26px;letter-spacing:.02em;text-transform:none}
.v-c .rs{color:var(--text-2)}
.v-c .grp-box{background:var(--aag-tile-hover);border-radius:16px;padding:10px 8px 6px}
.v-c .row.even{background:var(--aag-tile-hover);border-radius:8px}
.v-c .pct{font-weight:700}
.v-c .mk{margin-left:-2px;align-self:flex-start;font-size:10px}
.v-c .band{font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--text-3);
  padding:8px 4px 2px}
.v-c .band:first-of-type{padding-top:2px}

/* D: C's layout (Conference split into Division leaders / Wild card / In the hunt) with A's look
   (thin row lines, plain PCT, clinch letter in the left slot) -- no panels behind the groups. Title
   stacked like B's, the year in C's Saira italic (Jason, 2026-10-07). */
.v-d .title.stack{display:flex;flex-direction:column;align-items:center;gap:2px}
.v-d .yr-big{font-size:36px;letter-spacing:.02em}
.v-d .rs{font-size:11px;letter-spacing:.12em;color:var(--text-2)}
/* no line under the last team of a group or a section (Jason, 2026-10-07) */
.v-d .row.end{border-bottom:0}
/* the Wild card / In the hunt labels look like the first section's label on the column-heads line */
.v-d .band{font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--text-2);
  padding:10px 4px 2px}
.v-d .band:first-of-type{padding-top:2px}

/* Division view: AFC / NFC over their four divisions */
.conf-h{font-size:15px;font-weight:900;letter-spacing:.1em;margin:22px 0 -6px;padding:0 4px}
.pane>.conf-h:first-child{margin-top:8px}
.v-b .conf-h{font-family:Teko,Inter,sans-serif;font-size:24px;font-weight:600;letter-spacing:.04em;line-height:1}
.v-c .conf-h{font-family:Saira,Inter,sans-serif;font-style:italic;font-weight:800;font-size:18px;letter-spacing:.02em}

/* legend */
.legend{margin-top:28px;padding-top:14px;border-top:1px solid var(--line)}
.legend h3{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--text-2);margin:0 0 6px}
.legend dl{display:grid;grid-template-columns:1fr 1fr;gap:4px 14px;margin-bottom:14px}
.legend dl>div{display:flex;gap:8px;font-size:12px;align-items:baseline}
.legend dt{flex:none;width:34px;font-weight:700;font-size:11px}
.legend dt.mkk{width:14px;text-align:center;font-size:13px}
.legend dd{color:var(--text-2)}
.legend .note{font-size:11px;color:var(--text-3)}
@media (max-width:420px){.legend dl{grid-template-columns:1fr}}
@media (max-width:359px){
  .row,.seeded .row{column-gap:2px;font-size:12px}
  .row{grid-template-columns:minmax(0,1fr) 17px 17px 13px 34px 30px 30px 25px}
  .seeded .row{grid-template-columns:13px minmax(0,1fr) 17px 17px 13px 34px 30px 30px 25px}
  .who .hl{display:none}
}

/* bottom bar: menu left (where the light/dark switch was), back pill middle; the light/dark
   switch is now a line in the menu (Jason, 2026-10-07) */
.bottombar{position:fixed;left:0;right:0;bottom:0;z-index:10;height:var(--bbar);padding-bottom:env(safe-area-inset-bottom);
  background:var(--aag-bar-bg);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px)}
.bar-in{position:relative;max-width:600px;height:52px;margin:0 auto;display:flex;align-items:flex-start;justify-content:center;padding-top:10px}
.back{display:inline-flex;align-items:center;gap:6px;padding:6px 12px;border-radius:999px;font-size:16px;line-height:19px;color:var(--text)}
.menu-btn{position:absolute;left:7px;top:9px;width:34px;height:34px;border:0;background:none;color:var(--text);
  display:flex;align-items:center;justify-content:center;cursor:pointer}
.menu{position:absolute;left:10px;bottom:56px;min-width:190px;padding:6px;border-radius:14px;background:var(--aag-bg);
  border:1px solid var(--line);box-shadow:0 8px 30px rgba(0,0,0,.18);display:none}
.menu.open{display:block}
.menu a{display:flex;justify-content:space-between;padding:8px 10px;border-radius:9px;font-size:14px;color:var(--text);text-decoration:none}
.menu a.on{font-weight:700;background:var(--aag-tile-hover)}
.menu a.later{color:var(--text-3)}
.menu a.later i{font-style:normal;font-size:11px}
.menu hr{border:0;border-top:1px solid var(--line-soft);margin:6px 4px}
.menu .ts-btn{width:100%;height:auto;justify-content:flex-start;gap:10px;padding:8px 10px;border-radius:9px;
  font:inherit;font-size:14px;text-align:left}
.menu .ts-btn svg{width:17px;height:17px}
.menu .ts-btn:hover,.menu a:hover{transform:none;opacity:1;background:var(--aag-pill-hover)}
""" + theme.SWITCH_CSS

JS = """
(function(){
  var marks = %s;
  document.addEventListener('click', function(e){
    var t = e.target.closest('.sw-tab');
    if (t) {
      var v = t.closest('.variant'), k = t.getAttribute('data-view');
      v.querySelectorAll('.sw-tab').forEach(function(b){b.classList.toggle('on', b === t)});
      v.querySelectorAll('.pane').forEach(function(p){p.classList.toggle('on', p.getAttribute('data-pane') === k)});
      try { localStorage.setItem('st-view', k); } catch (err) {}
      return;
    }
    var m = e.target.closest('[data-pick-variant]');
    if (m) {
      var want = m.getAttribute('data-pick-variant');
      document.querySelectorAll('[data-pick-variant]').forEach(function(b){b.classList.toggle('on', b === m)});
      document.querySelectorAll('.variant').forEach(function(v){v.classList.toggle('on', v.getAttribute('data-variant') === want)});
      return;
    }
    if (e.target.closest('.menu-btn')) { document.querySelector('.menu').classList.toggle('open'); return; }
    if (!e.target.closest('.menu')) document.querySelector('.menu').classList.remove('open');
  });
  document.getElementById('clinch').addEventListener('change', function(){
    var on = this.checked;
    document.querySelectorAll('.mk').forEach(function(s){ s.textContent = on ? (marks[s.getAttribute('data-team')] || '') : ''; });
  });
})();
"""

MENU_ICON = ('<svg viewBox="0 0 20 20" width="19" height="19" fill="none" stroke="currentColor" stroke-width="2.2" '
             'stroke-linecap="round" aria-hidden="true"><path d="M3 5h14M3 10h14M3 15h14"/></svg>')
CHEV = ('<svg viewBox="0 0 10 16" width="9" height="14" fill="none" stroke="currentColor" stroke-width="2.2" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 2 2 8l6 6"/></svg>')


# the sun and moon from the bottom bar's switch (theme.SWITCH_HTML), reused on the menu's light/dark line
SWITCH_SVGS = [x.split("</svg>")[0].join(("<svg", "</svg>")) for x in theme.SWITCH_HTML.split("<svg")[1:]]


def page(rows, week):
    import json
    variants = "".join(variant_html(rows, v, week) for v in ("a", "b", "c", "d"))
    mock = ('<div class="mock"><b>Mockup</b>'
            '<button class="on" data-pick-variant="a">A · Team page table</button>'
            '<button data-pick-variant="b">B · Team pills</button>'
            '<button data-pick-variant="c">C · Grouped cards</button>'
            '<button data-pick-variant="d">D · C layout, A look</button>'
            '<label><input type="checkbox" id="clinch"> Clinch example</label></div>')
    sun, moon = SWITCH_SVGS
    bar = ('<nav class="bottombar"><div class="bar-in">'
           + f'<button class="menu-btn" type="button" aria-label="Menu">{MENU_ICON}</button>'
           + f'<span class="back">{CHEV}<span>Week {week + 1}</span></span>'
           + '<div class="menu"><a href="#">Games<i></i></a><a class="on" href="#">Standings</a>'
             '<a class="later" href="#">League Leaders <i>later</i></a><hr>'
             f'<button class="ts-btn ts-sun" type="button" data-pick="light">{sun}<span>Light mode</span></button>'
             f'<button class="ts-btn ts-moon" type="button" data-pick="dark">{moon}<span>Dark mode</span></button></div>'
           + '</div></nav>')
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'>"
        "<meta name='theme-color' content='#F3F3EE'>"
        f"<title>{SEASON} Standings mockup</title>"
        f"<script>{theme.THEME_HEAD_JS}</script>"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;700;900&display=swap' rel='stylesheet'>"
        "<link href='https://fonts.googleapis.com/css2?family=Saira:ital,wdth,wght@1,50..125,400..900&family=Teko:wght@400..700&display=swap' rel='stylesheet'>"
        f"<style>{theme.THEME_CSS}{CSS}{helmet_css()}</style></head><body>"
        f"{mock}<main class='wrap'>{variants}</main>{bar}"
        f"<script>{theme.THEME_JS}</script><script>{JS % json.dumps(example_marks(rows))}</script>"
        "</body></html>"
    )


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "mockups", "standings.html")
    rows, week = standings()
    with open(out, "w", encoding="utf-8") as f:
        f.write(page(rows, week))
    print(f"Wrote {out} (through week {week})")


if __name__ == "__main__":
    main()
