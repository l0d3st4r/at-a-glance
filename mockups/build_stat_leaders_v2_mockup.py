"""
Stat Leaders page mockup, round 2 (2026-10-07) -- NOT part of the live build.

Round 1 (build_stat_leaders_mockup.py) tried five ideas; Jason kept A, B, C and E (D, the medal
table, is out) and asked for two things in all of them:

  * the full stats -- every list has "Show 10 more" (to each stat's top 100), then "Show fewer"
  * a condensed and an expanded view, on the +/- toggle in the bottom bar's right corner like
    Page 0 / Page 1 (opens expanded, as they do). Condensed keeps to the leaders and their number;
    expanded gives each player his full stat line for the category (passing: C/A, YDS, TD, INT, Y/A,
    SK ...), the column being ranked highlighted like Player Stats' sorted column

  A "Leaderboards"  -- condensed: each stat's top 3 on single lines, a small "+10" on its title line.
                       Expanded: the leader big, then a stat-line table of the top 5. Both grow.
  B "One stat deep" -- pick a category, then a stat. Condensed: the top 20 with a bar each.
                       Expanded: the same order as a stat-line table. Both grow.
  C "At a glance"   -- condensed: every leader on one screen. Expanded: each tile lists its top 3.
                       Tapping any tile opens that stat's full list (a sheet over the page): the
                       stat-line table, growing with "Show 10 more".
  E "The race"      -- the chart of the top 5's running totals stays. Condensed: the top 5 under it.
                       Expanded: a week-by-week table (Wk 1 .. Wk N, then the total), growing past
                       the five on the chart.

Same data rules as round 1: regular season to date; rate stats only count qualified players
(Y/A 14 attempts a team game, Y/C 6.25 carries, punt average 2.5 punts); ties share a place.
The race lines keep round 1's validated palette (dataviz reference slots 1-5, light and dark steps).

The numbers ride in the page once as JSON and the lists are drawn by the page's script, so 100
players a stat doesn't make the file huge.

Run after build_data.py (needs data/matchups.json):
    python mockups/build_stat_leaders_v2_mockup.py [out.html]
Writes mockups/stat-leaders-2.html. stat-leaders-2.html#c opens on layout C, #c-c condensed.
"""

import html
import json
import os
import sys
import urllib.parse
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import helmets  # noqa: E402
import player_stats  # noqa: E402
import theme  # noqa: E402
from divisions import DIVISIONS  # noqa: E402
from render_page1 import CHEV, MINUS, PLUS  # noqa: E402
from render_page2players import PS_ICONS  # noqa: E402

SEASON = 2026
TOP = 100


def esc(v):
    return html.escape(str(v), quote=True)


def _div(a, b):
    return a / b if b else 0


def f0(v):
    return f"{int(round(v)):,}"


def f1(v):
    return f"{v:.1f}"


def ma(m, a):
    return f"{m}/{a}" if a else "—"


# Each category's stat line: (column, value -> text)
LINES = {
    "passing": [("C/A", lambda r: ma(r["cmp"], r["att"])), ("YDS", lambda r: f0(r["pyds"])), ("TD", lambda r: f0(r["ptd"])),
                ("INT", lambda r: f0(r["int"])), ("Y/A", lambda r: f1(_div(r["pyds"], r["att"]))), ("SK", lambda r: f0(r["sk"]))],
    "rushing": [("CAR", lambda r: f0(r["car"])), ("YDS", lambda r: f0(r["ryds"])), ("Y/C", lambda r: f1(_div(r["ryds"], r["car"]))),
                ("TD", lambda r: f0(r["rtd"])), ("1D", lambda r: f0(r["r1d"])), ("FUM", lambda r: f0(r["rfum"]))],
    "receiving": [("REC", lambda r: f0(r["rec"])), ("TGT", lambda r: f0(r["tgt"])), ("YDS", lambda r: f0(r["reyds"])),
                  ("Y/R", lambda r: f1(_div(r["reyds"], r["rec"]))), ("TD", lambda r: f0(r["retd"])), ("1D", lambda r: f0(r["re1d"]))],
    "defense": [("TKL", lambda r: f0(r["solo"] + r["ast"])), ("TFL", lambda r: f0(r["tfl"])), ("SK", lambda r: f1(r["dsk"]) if r["dsk"] % 1 else f0(r["dsk"])),
                ("INT", lambda r: f0(r["dint"])), ("PD", lambda r: f0(r["pd"])), ("FF", lambda r: f0(r["ff"]))],
    "fg": [("FG", lambda r: ma(r["fgm"], r["fga"])), ("PCT", lambda r: f"{_div(r['fgm'], r['fga']) * 100:.0f}%" if r["fga"] else "—"),
           ("LNG", lambda r: f0(r["fglng"])), ("XP", lambda r: ma(r["xpm"], r["xpa"]))],
    "punt": [("P", lambda r: f0(r["p"])), ("YDS", lambda r: f0(r["pyd"])), ("AVG", lambda r: f1(_div(r["pyd"], r["p"]))),
             ("NET", lambda r: f1(_div(r["pnet"], r["p"]))), ("IN20", lambda r: f0(r["p20"]))],
    "kr": [("KR", lambda r: f0(r["kr"])), ("YDS", lambda r: f0(r["kryds"])), ("AVG", lambda r: f1(_div(r["kryds"], r["kr"])))],
    "pr": [("PR", lambda r: f0(r["pr"])), ("YDS", lambda r: f0(r["pryds"])), ("AVG", lambda r: f1(_div(r["pryds"], r["pr"])))],
}

# (key, category, name, short, value, decimals, qualifier per team game, stat line, its column)
STATS = [
    ("pyds", "passing", "Passing Yards", "Pass Yds", lambda r: r["pyds"], 0, None, "passing", "YDS"),
    ("ptd", "passing", "Passing TDs", "Pass TD", lambda r: r["ptd"], 0, None, "passing", "TD"),
    ("ypa", "passing", "Yards per Attempt", "Y/A", lambda r: _div(r["pyds"], r["att"]), 1, ("att", 14), "passing", "Y/A"),
    ("ryds", "rushing", "Rushing Yards", "Rush Yds", lambda r: r["ryds"], 0, None, "rushing", "YDS"),
    ("rtd", "rushing", "Rushing TDs", "Rush TD", lambda r: r["rtd"], 0, None, "rushing", "TD"),
    ("ypc", "rushing", "Yards per Carry", "Y/C", lambda r: _div(r["ryds"], r["car"]), 1, ("car", 6.25), "rushing", "Y/C"),
    ("rec", "receiving", "Receptions", "Rec", lambda r: r["rec"], 0, None, "receiving", "REC"),
    ("reyds", "receiving", "Receiving Yards", "Rec Yds", lambda r: r["reyds"], 0, None, "receiving", "YDS"),
    ("retd", "receiving", "Receiving TDs", "Rec TD", lambda r: r["retd"], 0, None, "receiving", "TD"),
    ("tkl", "defense", "Tackles", "Tackles", lambda r: r["solo"] + r["ast"], 0, None, "defense", "TKL"),
    ("dsk", "defense", "Sacks", "Sacks", lambda r: r["dsk"], 1, None, "defense", "SK"),
    ("tfl", "defense", "Tackles for Loss", "TFL", lambda r: r["tfl"], 0, None, "defense", "TFL"),
    ("dint", "defense", "Interceptions", "INT", lambda r: r["dint"], 0, None, "defense", "INT"),
    ("pd", "defense", "Passes Defended", "PD", lambda r: r["pd"], 0, None, "defense", "PD"),
    ("ff", "defense", "Forced Fumbles", "FF", lambda r: r["ff"], 0, None, "defense", "FF"),
    ("fgm", "kicking", "Field Goals Made", "FG", lambda r: r["fgm"], 0, None, "fg", "FG"),
    ("fglng", "kicking", "Longest Field Goal", "FG Long", lambda r: r["fglng"], 0, None, "fg", "LNG"),
    ("pavg", "kicking", "Punting Average", "Punt Avg", lambda r: _div(r["pyd"], r["p"]), 1, ("p", 2.5), "punt", "AVG"),
    ("p20", "kicking", "Punts Inside the 20", "Inside 20", lambda r: r["p20"], 0, None, "punt", "IN20"),
    ("kryds", "returns", "Kick Return Yards", "KR Yds", lambda r: r["kryds"], 0, None, "kr", "YDS"),
    ("pryds", "returns", "Punt Return Yards", "PR Yds", lambda r: r["pryds"], 0, None, "pr", "YDS"),
]
CATS = [("passing", "Passing"), ("rushing", "Rushing"), ("receiving", "Receiving"),
        ("defense", "Defense"), ("kicking", "Kicking"), ("returns", "Returns")]
RACE_KEYS = ["pyds", "ptd", "ryds", "rtd", "rec", "reyds", "retd", "tkl", "dsk", "dint", "fgm", "kryds"]
QUAL_WORD = {"att": "attempts", "car": "carries", "p": "punts"}


def short(name):
    parts = (name or "").split()
    return f"{parts[0][0]}. {' '.join(parts[1:])}" if len(parts) > 1 else (name or "")


def build_data():
    with open(os.path.join(ROOT, "data", "matchups.json"), encoding="utf-8") as f:
        pw = json.load(f).get("player_weeks") or {}
    games = {t: len({r["wk"] for r in rows}) for t, rows in pw.items()}
    through = max((r["wk"] for rows in pw.values() for r in rows), default=0)
    totals = []
    for team in pw:
        for r in player_stats.season_totals(pw, team, None):
            r["team"] = team
            totals.append(r)
    weekly = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))   # (team, id) -> wk -> stat -> n
    for team, rows in pw.items():
        for r in rows:
            for k in player_stats.STATS:
                if r.get(k):
                    weekly[(team, r["id"])][r["wk"]][k] += r[k]

    players, index = [], {}

    def pid(r):
        k = (r["team"], r["id"])
        if k not in index:
            index[k] = len(players)
            players.append([short(r["name"]), r["name"], r["pos"], r["team"]])
        return index[k]

    stats = []
    for key, cat, name, sh, fn, dec, qual, line, col in STATS:
        vals = []
        for r in totals:
            if qual and r[qual[0]] < qual[1] * games.get(r["team"], 0):
                continue
            v = fn(r)
            if v and v > 0:
                vals.append((v, r))
        vals.sort(key=lambda x: (-x[0], x[1]["name"]))
        rows = []
        for i, (v, r) in enumerate(vals[:TOP]):
            place = 1 + sum(1 for w, _ in vals[:i] if w > v)
            row = [place, pid(r), f1(v) if dec else f0(v), [f(r) for _c, f in LINES[line]]]
            if key in RACE_KEYS:
                run, acc = [], defaultdict(int)
                for wk in range(1, through + 1):
                    for k, x in weekly[(r["team"], r["id"])].get(wk, {}).items():
                        acc[k] = max(acc[k], x) if k in player_stats.MAX_STATS else acc[k] + x
                    run.append(round(fn(defaultdict(int, acc)), 1))
                row.append(run)
            rows.append(row)
        stats.append({"key": key, "cat": cat, "name": name, "short": sh, "dec": dec, "line": line,
                      "col": [c for c, _f in LINES[line]].index(col), "count": len(vals),
                      "qual": f"Qualified: {qual[1]:g} {QUAL_WORD[qual[0]]} a team game" if qual else "",
                      "race": key in RACE_KEYS, "rows": rows})
    return {"through": through, "players": players, "stats": stats,
            "lines": {k: [c for c, _f in v] for k, v in LINES.items()},
            "cats": CATS, "icons": {c: PS_ICONS.get(c, "") for c, _n in CATS}}


def helmet_css():
    return "".join(f'.h-{t}{{background-image:url("data:image/svg+xml,'
                   f'{urllib.parse.quote(helmets.helmet_svg(t, id_prefix="h" + t))}")}}' for t in DIVISIONS)


CSS = """
:root{--bbar:""" + theme.BBAR_HEIGHT + """;--text:var(--aag-text);--text-2:var(--aag-text-2);--text-3:var(--aag-text-3);
  --line:var(--aag-tile-border);--line-soft:var(--aag-tile-border-soft);--gold:#D4A20A;--silver:#A2A7AD;--bronze:#B5702F;
  --s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--s5:#e87ba4}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181}}
:root[data-theme=dark]{--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:var(--aag-bg)}
body{min-height:100vh;color:var(--text);font-family:Inter,system-ui,-apple-system,sans-serif;-webkit-font-smoothing:antialiased}
button{font:inherit;color:inherit}
.abbr{line-height:1;font-family:Saira,Inter,system-ui,sans-serif;font-weight:800;font-style:italic;font-variation-settings:'wdth' 95;letter-spacing:.02em}
.hl{display:inline-block;flex:none;vertical-align:middle;background-position:center;background-size:contain;background-repeat:no-repeat}
.ic svg{height:1em;width:auto;display:block}
.ic{display:inline-flex;margin-right:6px}

.mock{position:sticky;top:0;z-index:20;display:flex;flex-wrap:wrap;justify-content:center;gap:6px;padding:8px 12px;
  background:var(--aag-bar-bg);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);border-bottom:1px dashed var(--line);font-size:12px}
.mock b{font-size:10px;letter-spacing:.06em;text-transform:uppercase;color:var(--text-3);align-self:center}
.mock button{background:none;border:1px solid var(--line);border-radius:999px;padding:3px 10px;cursor:pointer}
.mock button.on{background:var(--text);color:var(--aag-bg);border-color:var(--text)}
.mock .why{flex-basis:100%;text-align:center;color:var(--text-2);font-size:11px}

.wrap{max-width:600px;margin:0 auto;padding:10px 16px calc(28px + var(--bbar))}
.variant{display:none}.variant.on{display:block}
.top{display:flex;flex-direction:column;align-items:center;gap:2px;padding:4px 0 12px}
.yr{font-size:36px}
.rs-line{display:flex;gap:6px;align-items:baseline;font-size:11px;white-space:nowrap}
.rs{letter-spacing:.12em;text-transform:uppercase;color:var(--text-2);font-weight:700}
.thru{color:var(--text-3)}
.thru::before{content:"·";margin-right:6px}
.chip{display:inline-flex;align-items:center;background:none;border:1px solid transparent;border-radius:999px;padding:5px 12px;
  font-size:14px;font-weight:700;cursor:pointer;opacity:.45;white-space:nowrap}
.chip.on{opacity:1;border-color:var(--line)}
.chip.sm{font-size:12px;padding:4px 10px}
.hint{text-align:center;font-size:11px;color:var(--text-3);margin-top:10px}
.cat-h{display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:900;letter-spacing:.1em;text-transform:uppercase;margin:22px 0 4px}
.cat-h:first-child{margin-top:4px}
.st-row{display:flex;justify-content:space-between;align-items:center}
.mi{display:flex;gap:4px}
.mi button{background:none;border:1px solid var(--line);border-radius:999px;padding:1px 8px;font-size:10px;font-weight:700;
  letter-spacing:.04em;cursor:pointer;color:var(--text-2)}
.st-h{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--text-2)}
.qual{font-size:10px;color:var(--text-3);margin-top:1px}

/* compact rows: place, helmet, name, team, value */
.cr{list-style:none}
.cr li{display:grid;grid-template-columns:18px 18px minmax(0,1fr) 34px 48px;gap:6px;align-items:center;padding:3px 0;font-size:13px}
.pl{font-size:11px;font-weight:700;color:var(--text-3);text-align:right;font-variant-numeric:tabular-nums}
.pl.m1,.pl.m2,.pl.m3{border-bottom:3px solid;padding-bottom:1px;justify-self:end}
.pk.m1,.pk.m2,.pk.m3{display:inline-block;border-bottom:3px solid;padding-bottom:1px}
:is(.pl,.pk).m1{border-color:var(--gold)}:is(.pl,.pk).m2{border-color:var(--silver)}:is(.pl,.pk).m3{border-color:var(--bronze)}
.nm{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tm{font-size:12px;color:var(--text-2)}
.v{font-variant-numeric:tabular-nums;font-weight:700;text-align:right}

/* stat-line tables (expanded) */
.lt{width:100%;border-collapse:collapse;font-size:12px;font-variant-numeric:tabular-nums}
.lt th{font-size:9.5px;font-weight:700;letter-spacing:.04em;color:var(--text-3);text-align:right;padding:0 3px 3px;white-space:nowrap}
.lt td{text-align:right;padding:5px 3px;white-space:nowrap;border-top:1px solid var(--line-soft)}
.lt td.pl{padding-left:0}
.lt td.who{text-align:left;max-width:0;width:100%;overflow:hidden;text-overflow:ellipsis}
.lt td.who .hl{margin-right:5px}
.lt .on{background:var(--aag-tile-hover);font-weight:700;color:var(--text)}
.lt th.on{color:var(--text);border-radius:6px 6px 0 0}

/* show more */
.more-row{display:flex;justify-content:center;align-items:center;gap:10px;margin-top:6px}
.more{background:none;border:1px solid var(--line);border-radius:999px;padding:4px 12px;font-size:12px;font-weight:700;cursor:pointer}
.more-row .cnt{font-size:10px;color:var(--text-3)}

/* A */
.a-card{padding:12px 4px 12px;border-bottom:1px solid var(--line-soft)}
.a-lead{display:flex;align-items:center;gap:10px;margin:8px 0 6px}
.a-who{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px}
.a-who b{font-size:16px}
.a-who span{font-size:11px;color:var(--text-2)}
.a-v{font-family:Teko,Inter,sans-serif;font-size:40px;line-height:.9;font-weight:600}
[data-view=condensed] .a-card{padding:8px 4px}
[data-view=condensed] .a-card .st-h{margin-bottom:2px}

/* B */
.b-pick{position:sticky;top:76px;z-index:5;background:var(--aag-bg);padding:0 16px 6px;margin:0 -16px}
.b-cats,.b-stats{display:flex;gap:2px;overflow-x:auto;scrollbar-width:none}
.b-cats::-webkit-scrollbar,.b-stats::-webkit-scrollbar{display:none}
.b-stats{justify-content:center;margin-top:4px}
.b-h{text-align:center;font-size:15px;font-weight:900;letter-spacing:.1em;text-transform:uppercase;margin-top:10px}
.b-q{text-align:center;font-size:11px;color:var(--text-3);margin:2px 0 6px}
.bars{list-style:none}
.bars li{display:grid;grid-template-columns:18px 18px 104px minmax(0,1fr) 44px;gap:8px;align-items:center;padding:4px 0;
  border-bottom:1px solid var(--line-soft);font-size:13px}
.bars small{display:block;font-size:10px;color:var(--text-3)}
.bar{height:8px;display:block}
.bar i{display:block;height:100%;background:var(--text-2);border-radius:0 4px 4px 0}
.bars li:first-child .bar i{background:var(--text)}

/* C */
.c-grid{display:grid;grid-template-columns:1fr 1fr;gap:5px}
.c-tile{display:flex;flex-direction:column;gap:2px;text-align:left;background:var(--aag-tile-hover);border:0;border-radius:12px;padding:5px 9px;cursor:pointer;min-width:0}
.c-lbl{display:flex;align-items:center;font-size:10px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--text-2)}
.c-lbl .ic{margin-right:4px}
.c-lead{display:flex;align-items:center;gap:5px;min-width:0}
.c-nm{flex:1;min-width:0;font-size:12px;font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.c-v{font-family:Teko,Inter,sans-serif;font-size:21px;line-height:1;font-weight:600}
.c-top{list-style:none;margin-top:2px}
.c-top li{display:grid;grid-template-columns:12px minmax(0,1fr) auto;gap:5px;font-size:11.5px;padding:1px 0}
.c-top .v{font-weight:700}
[data-view=condensed] .c-top{display:none}
[data-view=expanded] .c-lead{display:none}
.sheet{position:fixed;left:0;right:0;top:0;bottom:var(--bbar);z-index:25;background:var(--aag-bg);overflow-y:auto;
  padding:14px 16px 20px;display:none}
.sheet.open{display:block}
.sheet-in{max-width:600px;margin:0 auto}
.sheet-h{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px}
.sheet-h b{font-size:15px;font-weight:900;letter-spacing:.1em;text-transform:uppercase;display:flex;align-items:center}
.x{background:none;border:0;font-size:22px;line-height:1;cursor:pointer;padding:2px 6px}

/* E */
.e-chips{display:flex;gap:2px;overflow-x:auto;scrollbar-width:none;margin:0 -16px 6px;padding:0 16px}
.e-chips::-webkit-scrollbar{display:none}
.e-track{display:flex;align-items:flex-start;overflow-x:auto;scroll-snap-type:x mandatory;scrollbar-width:none;margin:0 -16px;overscroll-behavior-x:contain}
.e-track::-webkit-scrollbar{display:none}
.e-card{flex:0 0 100%;scroll-snap-align:start;padding:0 16px}
.e-card h3{display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:900;letter-spacing:.1em;text-transform:uppercase;margin:6px 0 4px}
.e-chart{position:relative}
.race{width:100%;height:auto;display:block;overflow:visible}
.gl{stroke:var(--line-soft);stroke-width:1}
.ax{font-size:9px;fill:var(--text-3)}
.ln{fill:none;stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.dt{stroke:var(--aag-bg);stroke-width:2}
.lb{font-size:10px;font-weight:700;fill:var(--text)}
.s1{stroke:var(--s1)}.s2{stroke:var(--s2)}.s3{stroke:var(--s3)}.s4{stroke:var(--s4)}.s5{stroke:var(--s5)}
circle.s1,i.s1{fill:var(--s1);background:var(--s1)}circle.s2,i.s2{fill:var(--s2);background:var(--s2)}
circle.s3,i.s3{fill:var(--s3);background:var(--s3)}circle.s4,i.s4{fill:var(--s4);background:var(--s4)}circle.s5,i.s5{fill:var(--s5);background:var(--s5)}
.xh{stroke:var(--text-3);stroke-width:1;stroke-dasharray:2 3;opacity:0}
.race.hover .xh{opacity:1}
.tip{position:absolute;top:0;pointer-events:none;background:var(--aag-bg);border:1px solid var(--line);border-radius:8px;
  padding:5px 8px;font-size:11px;box-shadow:0 4px 14px rgba(0,0,0,.15);white-space:nowrap}
.tip b{display:block;margin-bottom:2px}
.sw{display:inline-block;width:12px;height:3px;border-radius:2px}
.e-leg li{grid-template-columns:18px 12px 18px minmax(0,1fr) 34px 48px}

/* bottom bar: menu left, back pill middle, +/- right */
.bottombar{position:fixed;left:0;right:0;bottom:0;z-index:16;height:var(--bbar);padding-bottom:env(safe-area-inset-bottom);
  background:var(--aag-bar-bg);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px)}
.bar-in{position:relative;max-width:600px;height:52px;margin:0 auto;display:flex;align-items:flex-start;justify-content:center;padding-top:10px}
.week{color:inherit;text-decoration:none;display:inline-flex;align-items:center;gap:6px;font-size:16px;line-height:19px;padding:6px 12px}
.week .chev{width:12px;height:12px}
.toggle{position:absolute;right:16px;top:9px;width:34px;height:34px;border:0;background:none;padding:0;display:flex;
  align-items:center;justify-content:center;cursor:pointer}
.toggle .i-plus{display:none}
[data-view=condensed] .toggle .i-plus{display:block}
[data-view=condensed] .toggle .i-minus{display:none}
""" + theme.MENU_CSS + theme.HELMET_SHADOW_CSS

JS = r"""
(function () {
  var D = JSON.parse(document.getElementById('data').textContent), P = D.players, body = document.body;
  var S = {}; D.stats.forEach(function (s) { S[s.key] = s; });
  var shown = {};   // block id -> rows showing
  function view() { return body.getAttribute('data-view'); }
  function esc(t) { return String(t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function helmet(team, n) { n = n || 18; return '<i class="hm hl h-' + team + '" style="--hs:' + n + 'px;width:' + n + 'px;height:' + n + 'px"></i>'; }
  function icon(cat) { return '<span class="ic">' + (D.icons[cat] || '') + '</span>'; }
  function med(p) { return p <= 3 ? ' m' + p : ''; }
  // a list's rows: the first n, and the controls to show more
  function count(id, start) { if (!(id in shown)) shown[id] = start; return shown[id]; }
  function more(id, s, n, start) {
    var total = s.rows.length;
    if (total <= start) return '';
    var next = Math.min(10, total - n);
    return '<div class="more-row">' + (n < total ? '<button class="more" data-more="' + id + '">Show ' + next + ' more</button>' : '')
      + (n > start ? '<button class="more" data-fewer="' + id + '" data-start="' + start + '">Show fewer</button>' : '')
      + '<span class="cnt">' + Math.min(n, total) + ' of ' + total + (s.count > total ? ' (top ' + total + ' of ' + s.count + ')' : '') + '</span></div>';
  }
  // condensed: the same controls, small, on the stat's title line
  function moreInline(id, s, n, start) {
    var total = s.rows.length;
    if (total <= start) return '';
    return '<span class="mi">' + (n > start ? '<button data-fewer="' + id + '" data-start="' + start + '">Less</button>' : '')
      + (n < total ? '<button data-more="' + id + '">+' + Math.min(10, total - n) + '</button>' : '') + '</span>';
  }
  function compact(s, n) {
    return '<ol class="cr">' + s.rows.slice(0, n).map(function (r) {
      var p = P[r[1]];
      return '<li><span class="pl' + med(r[0]) + '">' + r[0] + '</span>' + helmet(p[3]) + '<span class="nm">' + esc(p[0])
        + '</span><span class="tm abbr">' + p[3] + '</span><span class="v">' + r[2] + '</span></li>';
    }).join('') + '</ol>';
  }
  function table(s, n, from) {
    var cols = D.lines[s.line];
    return '<table class="lt"><thead><tr><th></th><th></th>' + cols.map(function (c, i) { return '<th class="' + (i === s.col ? 'on' : '') + '">' + c + '</th>'; }).join('')
      + '</tr></thead><tbody>' + s.rows.slice(from || 0, n).map(function (r) {
        var p = P[r[1]];
        return '<tr><td class="pl"><span class="pk' + med(r[0]) + '">' + r[0] + '</span></td><td class="who">' + helmet(p[3], 16) + esc(p[0]) + '</td>'
          + r[3].map(function (v, i) { return '<td class="' + (i === s.col ? 'on' : '') + '">' + v + '</td>'; }).join('') + '</tr>';
      }).join('') + '</tbody></table>';
  }
  function qual(s) { return s.qual ? '<div class="qual">' + s.qual + '</div>' : ''; }

  // ---- A
  function blockA(s) {
    var c = view() === 'condensed', id = 'a-' + s.key + (c ? '-c' : '-x'), start = c ? 3 : 5, n = count(id, start);
    if (c) return '<div class="st-h st-row"><span>' + esc(s.name) + '</span>' + moreInline(id, s, n, start) + '</div>' + compact(s, n);
    var r1 = s.rows[0], p = P[r1[1]];
    return '<div class="st-h">' + esc(s.name) + '</div>' + qual(s)
      + '<div class="a-lead">' + helmet(p[3], 40) + '<div class="a-who"><b>' + esc(p[1]) + '</b><span>' + esc(p[2]) + ' · <span class="abbr">' + p[3] + '</span></span></div>'
      + '<span class="a-v">' + r1[2] + '</span></div>' + table(s, n) + more(id, s, n, start);
  }
  // ---- B
  var bStat = 'pyds';
  function blockB() {
    var s = S[bStat], c = view() === 'condensed', id = 'b-' + s.key + (c ? '-c' : '-x'), n = count(id, 20);
    var head = '<h3 class="b-h">' + esc(s.name) + '</h3><div class="b-q">' + (s.qual || '&nbsp;') + '</div>';
    if (!c) return head + table(s, n) + more(id, s, n, 20);
    var hi = parseFloat(String(s.rows[0][2]).replace(/,/g, '')) || 1;
    return head + '<ol class="bars">' + s.rows.slice(0, n).map(function (r) {
      var p = P[r[1]], v = parseFloat(String(r[2]).replace(/,/g, ''));
      return '<li title="' + esc(p[1]) + ' (' + p[3] + '): ' + r[2] + '"><span class="pl' + med(r[0]) + '">' + r[0] + '</span>' + helmet(p[3])
        + '<span class="nm">' + esc(p[0]) + '<small>' + esc(p[2]) + ' · <span class="abbr">' + p[3] + '</span></small></span>'
        + '<span class="bar"><i style="width:' + Math.max(2, v / hi * 100).toFixed(1) + '%"></i></span><span class="v">' + r[2] + '</span></li>';
    }).join('') + '</ol>' + more(id, s, n, 20);
  }
  // ---- C
  function tileC(s) {
    var r1 = s.rows[0], p = P[r1[1]];
    return '<button class="c-tile" type="button" data-sheet="' + s.key + '"><span class="c-lbl">' + icon(s.cat) + esc(s.short) + '</span>'
      + '<span class="c-lead">' + helmet(p[3], 22) + '<span class="c-nm">' + esc(p[0]) + '</span><span class="c-v">' + r1[2] + '</span></span>'
      + '<ol class="c-top">' + s.rows.slice(0, 3).map(function (r) {
        return '<li><span class="pl' + med(r[0]) + '">' + r[0] + '</span><span class="nm">' + esc(P[r[1]][0]) + '</span><span class="v">' + r[2] + '</span></li>';
      }).join('') + '</ol></button>';
  }
  var sheetStat = null;
  function sheet() {
    var s = S[sheetStat], id = 'c-' + s.key, n = count(id, 20);
    return '<div class="sheet-in"><div class="sheet-h"><b>' + icon(s.cat) + esc(s.name) + '</b><button class="x" data-close aria-label="Close">×</button></div>'
      + qual(s) + table(s, n) + more(id, s, n, 20) + '</div>';
  }
  // ---- E
  var W = 343, H = 190, PL = 30, PR = 64, PT = 10, PB = 22;
  function chart(s) {
    var top = s.rows.slice(0, 5), n = D.through, hi = 0;
    top.forEach(function (r) { hi = Math.max(hi, r[4][n - 1]); }); hi = hi || 1;
    var x = function (i) { return PL + (W - PL - PR) * i / Math.max(1, n - 1); }, y = function (v) { return PT + (H - PT - PB) * (1 - v / hi); };
    var g = [0, hi / 2, hi].map(function (t) { return '<line class="gl" x1="' + PL + '" x2="' + (W - PR) + '" y1="' + y(t) + '" y2="' + y(t) + '"/><text class="ax" x="' + (PL - 6) + '" y="' + (y(t) + 3) + '" text-anchor="end">' + Math.round(t).toLocaleString() + '</text>'; }).join('');
    for (var i = 0; i < n; i++) g += '<text class="ax" x="' + x(i) + '" y="' + (H - 6) + '" text-anchor="middle">Wk ' + (i + 1) + '</text>';
    var ends = top.map(function (r, i) { return [y(r[4][n - 1]), i]; }).sort(function (a, b) { return a[0] - b[0]; }), placed = {}, last = -99;
    ends.forEach(function (e) { var ly = Math.max(e[0], last + 11); placed[e[1]] = ly; last = ly; });
    var lines = top.map(function (r, i) {
      return '<polyline class="ln s' + (i + 1) + '" points="' + r[4].map(function (v, j) { return x(j) + ',' + y(v); }).join(' ') + '"/>'
        + '<circle class="dt s' + (i + 1) + '" cx="' + x(n - 1) + '" cy="' + y(r[4][n - 1]) + '" r="4"/>'
        + '<text class="lb" x="' + (x(n - 1) + 8) + '" y="' + (placed[i] + 3) + '">' + esc(P[r[1]][0].split('. ').pop().slice(0, 10)) + '</text>';
    }).join('');
    return '<div class="e-chart"><svg class="race" viewBox="0 0 ' + W + ' ' + H + '" data-stat="' + s.key + '" role="img" aria-label="' + esc(s.name)
      + ': running totals by week for the top five">' + g + lines + '<line class="xh" y1="' + PT + '" y2="' + (H - PB) + '"/></svg><div class="tip" hidden></div></div>';
  }
  function blockE(s) {
    var c = view() === 'condensed', id = 'e-' + s.key + (c ? '-c' : '-x'), n = count(id, 5), wk = D.through;
    var out = '<h3>' + icon(s.cat) + esc(s.name) + '</h3>' + chart(s);
    if (c) return out + '<ol class="cr e-leg">' + s.rows.slice(0, n).map(function (r, i) {
      var p = P[r[1]];
      return '<li><span class="pl' + med(r[0]) + '">' + r[0] + '</span>' + (i < 5 ? '<i class="sw s' + (i + 1) + '"></i>' : '<i></i>') + helmet(p[3])
        + '<span class="nm">' + esc(p[0]) + '</span><span class="tm abbr">' + p[3] + '</span><span class="v">' + r[2] + '</span></li>';
    }).join('') + '</ol>' + more(id, s, n, 5);
    var head = '<tr><th></th><th></th>'; for (var i = 1; i <= wk; i++) head += '<th>WK ' + i + '</th>'; head += '<th class="on">TOT</th></tr>';
    return out + '<table class="lt"><thead>' + head + '</thead><tbody>' + s.rows.slice(0, n).map(function (r, i) {
      var p = P[r[1]], prev = 0, cells = r[4].map(function (v) { var d = v - prev; prev = v; return '<td>' + (s.dec ? d.toFixed(1) : Math.round(d).toLocaleString()) + '</td>'; }).join('');
      return '<tr><td class="pl"><span class="pk' + med(r[0]) + '">' + r[0] + '</span></td><td class="who">' + (i < 5 ? '<i class="sw s' + (i + 1) + '" style="margin-right:5px"></i>' : '') + helmet(p[3], 16) + esc(p[0]) + '</td>' + cells + '<td class="on">' + r[2] + '</td></tr>';
    }).join('') + '</tbody></table>' + more(id, s, n, 5);
  }

  // ---- drawing
  function drawA() { document.querySelectorAll('[data-a]').forEach(function (el) { el.innerHTML = blockA(S[el.getAttribute('data-a')]); }); }
  function drawB() { document.getElementById('b-body').innerHTML = blockB(); }
  function drawC() { document.getElementById('c-grid').innerHTML = D.stats.map(tileC).join(''); if (sheetStat) document.getElementById('sheet').innerHTML = sheet(); }
  function drawE() { document.querySelectorAll('[data-e]').forEach(function (el) { el.innerHTML = blockE(S[el.getAttribute('data-e')]); }); hookCharts(); }
  function drawAll() { drawA(); drawB(); drawC(); drawE(); }
  function redrawBlock(id) {
    var k = id.split('-')[1];
    if (id[0] === 'a') { var el = document.querySelector('[data-a="' + k + '"]'); el.innerHTML = blockA(S[k]); }
    else if (id[0] === 'b') drawB();
    else if (id[0] === 'c') document.getElementById('sheet').innerHTML = sheet();
    else { var e = document.querySelector('[data-e="' + k + '"]'); e.innerHTML = blockE(S[k]); hookCharts(); }
  }
  function hookCharts() {
    document.querySelectorAll('.race:not([data-hooked])').forEach(function (svg) {
      svg.setAttribute('data-hooked', '');
      var s = S[svg.getAttribute('data-stat')], top = s.rows.slice(0, 5), n = D.through, tip = svg.parentNode.querySelector('.tip'), xh = svg.querySelector('.xh');
      function show(ev) {
        var b = svg.getBoundingClientRect(), px = (ev.clientX - b.left) / b.width * W,
            i = Math.max(0, Math.min(n - 1, Math.round((px - PL) / ((W - PL - PR) / Math.max(1, n - 1))))), x = PL + (W - PL - PR) * i / Math.max(1, n - 1);
        xh.setAttribute('x1', x); xh.setAttribute('x2', x); svg.classList.add('hover');
        tip.innerHTML = '<b>Through week ' + (i + 1) + '</b>' + top.map(function (r) { return esc(P[r[1]][0]) + ' &nbsp;' + (s.dec ? r[4][i].toFixed(1) : Math.round(r[4][i]).toLocaleString()); }).join('<br>');
        tip.hidden = false;
        var left = x / W * b.width + 10; if (left + 150 > b.width) left = x / W * b.width - 160; tip.style.left = left + 'px';
      }
      svg.addEventListener('pointermove', show); svg.addEventListener('pointerdown', show);
      svg.addEventListener('pointerleave', function () { svg.classList.remove('hover'); tip.hidden = true; });
    });
  }

  document.addEventListener('click', function (e) {
    var t;
    if ((t = e.target.closest('[data-pick-variant]'))) {
      var v = t.getAttribute('data-pick-variant');
      document.querySelectorAll('[data-pick-variant]').forEach(function (x) { x.classList.toggle('on', x === t); });
      document.querySelectorAll('.variant').forEach(function (x) { x.classList.toggle('on', x.getAttribute('data-variant') === v); });
      document.querySelector('.why').textContent = t.getAttribute('data-why');
      scrollTo(0, 0); return;
    }
    if ((t = e.target.closest('.toggle'))) {
      var c = view() === 'condensed';
      body.setAttribute('data-view', c ? 'expanded' : 'condensed');
      t.setAttribute('aria-label', c ? 'Switch to condensed view' : 'Switch to expanded view');
      drawAll(); return;
    }
    if ((t = e.target.closest('[data-more]'))) { var id = t.getAttribute('data-more'); shown[id] += 10; redrawBlock(id); return; }
    if ((t = e.target.closest('[data-fewer]'))) {
      var id2 = t.getAttribute('data-fewer'), blk = t.closest('[data-a],[data-e],#b-body,#sheet');
      shown[id2] = +t.getAttribute('data-start'); redrawBlock(id2);
      if (blk && blk.id !== 'sheet') { var r = blk.getBoundingClientRect(); if (r.top < 0) scrollBy(0, r.top - 90); }
      return;
    }
    if ((t = e.target.closest('[data-bcat]'))) {
      var cat = t.getAttribute('data-bcat');
      document.querySelectorAll('[data-bcat]').forEach(function (x) { x.classList.toggle('on', x === t); });
      bStat = D.stats.filter(function (s) { return s.cat === cat; })[0].key; drawBStats(); drawB(); return;
    }
    if ((t = e.target.closest('[data-bstat]'))) { bStat = t.getAttribute('data-bstat'); drawBStats(); drawB(); return; }
    if ((t = e.target.closest('[data-sheet]'))) { sheetStat = t.getAttribute('data-sheet'); var sh = document.getElementById('sheet'); sh.innerHTML = sheet(); sh.classList.add('open'); sh.scrollTop = 0; return; }
    if (e.target.closest('[data-close]')) { document.getElementById('sheet').classList.remove('open'); sheetStat = null; return; }
    if ((t = e.target.closest('[data-ego]'))) { var tr = document.querySelector('.e-track'); tr.scrollTo({ left: +t.getAttribute('data-ego') * tr.clientWidth, behavior: 'smooth' }); }
  });
  function drawBStats() {
    var cat = S[bStat].cat;
    document.getElementById('b-stats').innerHTML = D.stats.filter(function (s) { return s.cat === cat; }).map(function (s) {
      return '<button class="chip sm' + (s.key === bStat ? ' on' : '') + '" data-bstat="' + s.key + '">' + esc(s.short) + '</button>';
    }).join('');
  }
  var tr = document.querySelector('.e-track'), chips = [].slice.call(document.querySelectorAll('[data-ego]')), settle;
  tr.addEventListener('scroll', function () {
    clearTimeout(settle);
    settle = setTimeout(function () {
      var i = Math.round(tr.scrollLeft / tr.clientWidth);
      chips.forEach(function (c, j) { c.classList.toggle('on', j === i); });
      if (chips[i]) chips[i].scrollIntoView({ block: 'nearest', inline: 'center', behavior: 'smooth' });
    }, 90);
  }, { passive: true });

  // #a .. #e opens on that layout; "-c" on the end opens it condensed (for screenshots)
  var h = location.hash.slice(1).split('-');
  if (h[1] === 'c') { body.setAttribute('data-view', 'condensed'); }
  drawBStats(); drawAll();
  var start = document.querySelector('[data-pick-variant="' + h[0] + '"]'); if (start) start.click();
})();
"""

WHY = {
    "a": "The reference book. Condensed: each stat's top 3. Expanded: the leader big + a stat-line table. Show more on every list.",
    "b": "The deep dive. Condensed: the top 20 with bars. Expanded: the same order as a stat-line table. Show more.",
    "c": "At a glance. Condensed: every leader on one screen. Expanded: each tile's top 3. Tap a tile for the full list.",
    "e": "The race. Condensed: the top 5 under the chart. Expanded: a week-by-week table. Show more past the chart's five.",
}
NAMES = {"a": "A · Leaderboards", "b": "B · One stat deep", "c": "C · At a glance", "e": "E · The race"}


def page(data):
    stats = data["stats"]
    by_cat = defaultdict(list)
    for s in stats:
        by_cat[s["cat"]].append(s)
    icon = lambda c: f'<span class="ic">{data["icons"].get(c, "")}</span>'
    a = "".join(f'<h2 class="cat-h">{icon(c)}{n}</h2>' + "".join(f'<article class="a-card" data-a="{s["key"]}"></article>' for s in by_cat[c])
                for c, n in CATS)
    b = ('<div class="b-pick"><div class="b-cats">'
         + "".join(f'<button class="chip{" on" if c == "passing" else ""}" data-bcat="{c}">{icon(c)}{n}</button>' for c, n in CATS)
         + '</div><div class="b-stats" id="b-stats"></div></div><div id="b-body"></div>')
    c = '<div class="c-grid" id="c-grid"></div><p class="hint">Tap a tile for the full list</p>'
    race = [s for s in stats if s["race"]]
    e = ('<div class="e-chips">' + "".join(f'<button class="chip sm{" on" if i == 0 else ""}" data-ego="{i}">{esc(s["short"])}</button>' for i, s in enumerate(race))
         + '</div><div class="e-track">' + "".join(f'<article class="e-card" data-e="{s["key"]}"></article>' for s in race) + '</div>')
    top = (f'<header class="top"><span class="yr abbr">{SEASON}</span><span class="rs-line"><span class="rs">Stat Leaders</span>'
           f'<span class="thru">Through Week {data["through"]}</span></span></header>')
    variants = "".join(f'<div class="variant v-{k}{" on" if k == "a" else ""}" data-variant="{k}">{top}{body}</div>'
                       for k, body in (("a", a), ("b", b), ("c", c), ("e", e)))
    mock = ('<div class="mock"><b>Mockup</b>'
            + "".join(f'<button class="{"on" if k == "a" else ""}" data-pick-variant="{k}" data-why="{esc(WHY[k])}">{n}</button>' for k, n in NAMES.items())
            + f'<div class="why">{esc(WHY["a"])}</div></div>')
    menu = theme.menu_html("", None).replace('<a href="standings.html">Standings</a>',
                                             '<a href="standings.html">Standings</a><a href="#" aria-current="page">Stat Leaders</a>')
    bar = ('<nav class="bottombar"><div class="bar-in">' + menu
           + f'<a class="week" href="#">{CHEV}<span>Week {data["through"] + 1}</span></a>'
           + f'<button class="toggle" type="button" aria-label="Switch to condensed view"><span class="i-plus">{PLUS}</span><span class="i-minus">{MINUS}</span></button>'
           + '</div></nav>')
    blob = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'>"
        f"<title>{SEASON} Stat Leaders mockup 2</title><script>{theme.THEME_HEAD_JS}</script>"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;700;900&display=swap' rel='stylesheet'>"
        "<link href='https://fonts.googleapis.com/css2?family=Saira:ital,wdth,wght@1,50..125,400..900&family=Teko:wght@400..700&display=swap' rel='stylesheet'>"
        f"<style>{theme.THEME_CSS}{CSS}{helmet_css()}</style></head><body data-view='expanded'>"
        f"{mock}<main class='wrap'>{variants}</main><div class='sheet' id='sheet'></div>{bar}"
        f"<script type='application/json' id='data'>{blob}</script>"
        f"<script>{theme.THEME_JS}</script><script>{JS}</script></body></html>"
    )


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "mockups", "stat-leaders-2.html")
    data = build_data()
    with open(out, "w", encoding="utf-8") as f:
        f.write(page(data))
    print(f"Wrote {out} ({len(data['players'])} players across {len(data['stats'])} stats, through week {data['through']})")


if __name__ == "__main__":
    main()
