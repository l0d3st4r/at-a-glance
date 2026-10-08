"""
Stat Leaders -- site/leaders.html (Jason, 2026-10-07; worked out in mockups/build_stat_leaders_mockup.py,
_v2_ and _v3_). The league's leaders in every player stat the site tracks (player_stats.py), a page of
its own beside Standings, reached from the bottom bar's menu (theme.menu_html).

Two views on the +/- toggle in the bottom bar's right corner, like Page 0 / Page 1 (opens expanded):

EXPANDED -- like Player Stats' expanded view: one card per category (Passing, Rushing, Receiving,
Defense, Kicking, Returns) in a deck that snaps up / down, the category icons down the right side as
its nav, the cards above and below named on their slivers. Inside a card, swipe left / right between
that category's stats (small tabs under the title say which is showing and jump to one):
  Passing: Pass Yds, Pass TD, Y/A          Rushing: Rush Yds, Rush TD, Y/C
  Receiving: Rec, Rec Yds, Rec TD          Defense: Tackles, Sacks, TFL, INT, PD, FF
  Kicking: FG, Punt Avg                    Returns: KR Avg, PR Avg
  (FG Long and Inside 20 were their own stats until Jason dropped them, 2026-10-07 -- each kicker's
  long is on his FG row's stat line, and punts inside the 20 on the punting line)
Each stat:
  * the race -- the top 5 week by week, each line named
    at its end, a crosshair + tooltip on touch. Not for the averages (Y/A, Y/C, punt and return
    averages), whose list gets the whole card (Jason, 2026-10-07). A Total | Behind switch over it
    (Jason, 2026-10-07; opens on Behind, remembered on the device): Total draws the running totals from
    zero; Behind draws each line as his total minus that week's best among the five, so the leader rides
    the top line and the gaps keep their real size as the totals climb. Each line is in its player's team
    colors, picked separately for the light and dark grounds so the five stay visible and tell apart
    (higher-ranked players pick first; team_line_colors.py has the rules), and its end dot is ringed in
    a second team color
  * the ranked list -- place (the chart's five underlined in their line's color), the team pill, the
    full name and position (Jason, 2026-10-07), the number, a faint bar behind the row as long as the number (from zero) so the gaps show,
    and the rest of the player's stat line in small type under the name (wrapping whole stats at a
    time, balanced, when it's long). It scrolls inside the card and grows with "Show 10 more" (to each
    stat's top 100), then "Show fewer"

CONDENSED -- every stat on one screen, a row of tiles a category under its icon and name (picked as
"A, Category rows" in mockups/build_leaders_condensed_mockup.py): three across for passing, rushing
and receiving, defense in two rows of three, kicking and returns side by side as half-width columns of
two. The three-across tiles are centered: the stat's name over a big number, then the leader -- the
small team pill and his last name; two when they're tied for first (their pills lined up over each
other), "+N more tied" past that. Kicking and returns (half-width) stack the stat's name over its number,
the pill and first initial + last name beside them. The categories' names are centered over their rows in the pill
outline (Jason, 2026-10-07). On a phone too short for one
screen the tiles keep a minimum height and the view scrolls. Tapping a tile opens the expanded view on
that category's card, turned to that stat.

Leaders are the regular season to date (every week in player_weeks, which is regular season only).
Rate stats count qualified players only, as the NFL does: Y/A 14 attempts a team game
(player_stats.YPA_ATTEMPTS_PER_GAME), Y/C 6.25 carries, punt average 2.5 punts; kick / punt return
averages 1.25 returns a team game (the minimum Pro-Football-Reference publishes for kick and punt
returns, about 21-22 over a 17-game season; was 1 until 2026-10-07). Ties share a place.

The numbers ride in the page once as JSON and the page's script draws the lists, so 100 players a stat
doesn't make the file huge. #defense opens on that card, #defense-2 on its third stat, #condensed on
the condensed view.

Data: data/matchups.json -> "player_weeks" (player_stats.build_player_weeks), nothing new fetched.
"""

import html
import json
import os
from collections import defaultdict

import helmets
import logo
import player_stats
import team_line_colors
import render_standings
import theme
from divisions import DIVISIONS
from render_page1 import DOWN, MINUS, PLUS, UP
from render_page2players import PS_ICONS

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


# Each category's stat line: (column, value -> text). The ranked stat's own column is left out of a
# row's second line (its number is already on the right).
LINES = {
    "passing": [("C/A", lambda r: ma(r["cmp"], r["att"])), ("YDS", lambda r: f0(r["pyds"])), ("TD", lambda r: f0(r["ptd"])),
                ("INT", lambda r: f0(r["int"])), ("Y/A", lambda r: f1(_div(r["pyds"], r["att"]))), ("SK", lambda r: f0(r["sk"]))],
    "rushing": [("CAR", lambda r: f0(r["car"])), ("YDS", lambda r: f0(r["ryds"])), ("Y/C", lambda r: f1(_div(r["ryds"], r["car"]))),
                ("TD", lambda r: f0(r["rtd"])), ("1D", lambda r: f0(r["r1d"])), ("FUM", lambda r: f0(r["rfum"]))],
    "receiving": [("REC", lambda r: f0(r["rec"])), ("TGT", lambda r: f0(r["tgt"])), ("YDS", lambda r: f0(r["reyds"])),
                  ("Y/R", lambda r: f1(_div(r["reyds"], r["rec"]))), ("TD", lambda r: f0(r["retd"])), ("1D", lambda r: f0(r["re1d"]))],
    "defense": [("TKL", lambda r: f0(r["solo"] + r["ast"])), ("TFL", lambda r: f0(r["tfl"])),
                ("SK", lambda r: f1(r["dsk"]) if r["dsk"] % 1 else f0(r["dsk"])),
                ("INT", lambda r: f0(r["dint"])), ("PD", lambda r: f0(r["pd"])), ("FF", lambda r: f0(r["ff"]))],
    "fg": [("FG", lambda r: ma(r["fgm"], r["fga"])), ("PCT", lambda r: f"{_div(r['fgm'], r['fga']) * 100:.0f}%" if r["fga"] else "—"),
           ("LNG", lambda r: f0(r["fglng"])), ("XP", lambda r: ma(r["xpm"], r["xpa"]))],
    "punt": [("P", lambda r: f0(r["p"])), ("YDS", lambda r: f0(r["pyd"])), ("AVG", lambda r: f1(_div(r["pyd"], r["p"]))),
             ("NET", lambda r: f1(_div(r["pnet"], r["p"]))), ("IN20", lambda r: f0(r["p20"]))],
    "kr": [("KR", lambda r: f0(r["kr"])), ("YDS", lambda r: f0(r["kryds"])), ("AVG", lambda r: f1(_div(r["kryds"], r["kr"])))],
    "pr": [("PR", lambda r: f0(r["pr"])), ("YDS", lambda r: f0(r["pryds"])), ("AVG", lambda r: f1(_div(r["pryds"], r["pr"])))],
}

# (key, category, name, short name, value, decimals, qualifier per team game, stat line, its column, race chart)
STATS = [
    ("pyds", "passing", "Passing Yards", "Pass Yds", lambda r: r["pyds"], 0, None, "passing", "YDS", True),
    ("ptd", "passing", "Passing TDs", "Pass TD", lambda r: r["ptd"], 0, None, "passing", "TD", True),
    ("ypa", "passing", "Yards per Attempt", "Y/A", lambda r: _div(r["pyds"], r["att"]), 1,
     ("att", player_stats.YPA_ATTEMPTS_PER_GAME, "attempts"), "passing", "Y/A", False),
    ("ryds", "rushing", "Rushing Yards", "Rush Yds", lambda r: r["ryds"], 0, None, "rushing", "YDS", True),
    ("rtd", "rushing", "Rushing TDs", "Rush TD", lambda r: r["rtd"], 0, None, "rushing", "TD", True),
    ("ypc", "rushing", "Yards per Carry", "Y/C", lambda r: _div(r["ryds"], r["car"]), 1, ("car", 6.25, "carries"), "rushing", "Y/C", False),
    ("rec", "receiving", "Receptions", "Rec", lambda r: r["rec"], 0, None, "receiving", "REC", True),
    ("reyds", "receiving", "Receiving Yards", "Rec Yds", lambda r: r["reyds"], 0, None, "receiving", "YDS", True),
    ("retd", "receiving", "Receiving TDs", "Rec TD", lambda r: r["retd"], 0, None, "receiving", "TD", True),
    ("tkl", "defense", "Tackles", "Tackles", lambda r: r["solo"] + r["ast"], 0, None, "defense", "TKL", True),
    ("dsk", "defense", "Sacks", "Sacks", lambda r: r["dsk"], 1, None, "defense", "SK", True),
    ("tfl", "defense", "Tackles for Loss", "TFL", lambda r: r["tfl"], 0, None, "defense", "TFL", True),
    ("dint", "defense", "Interceptions", "INT", lambda r: r["dint"], 0, None, "defense", "INT", True),
    ("pd", "defense", "Passes Defended", "PD", lambda r: r["pd"], 0, None, "defense", "PD", True),
    ("ff", "defense", "Forced Fumbles", "FF", lambda r: r["ff"], 0, None, "defense", "FF", True),
    ("fgm", "kicking", "Field Goals Made", "FG", lambda r: r["fgm"], 0, None, "fg", "FG", True),
    ("pavg", "kicking", "Punting Average", "Punt Avg", lambda r: _div(r["pyd"], r["p"]), 1, ("p", 2.5, "punts"), "punt", "AVG", False),
    ("kravg", "returns", "Kick Return Average", "KR Avg", lambda r: _div(r["kryds"], r["kr"]), 1, ("kr", 1.25, "kick returns"), "kr", "AVG", False),
    ("pravg", "returns", "Punt Return Average", "PR Avg", lambda r: _div(r["pryds"], r["pr"]), 1, ("pr", 1.25, "punt returns"), "pr", "AVG", False),
]
CATS = [("passing", "Passing"), ("rushing", "Rushing"), ("receiving", "Receiving"),
        ("defense", "Defense"), ("kicking", "Kicking"), ("returns", "Returns")]


def short(name):
    """"Bryce Young" -> "B. Young"."""
    parts = (name or "").split()
    return f"{parts[0][0]}. {' '.join(parts[1:])}" if len(parts) > 1 else (name or "")


def _qual_text(qual):
    if not qual:
        return ""
    stat, per_game, word = qual
    return f"Qualified: {per_game:g} {word} a team game"


def build(player_weeks):
    """Everything the page's script draws: players (short name, full name, position, team) once, then
    each stat's ranked rows -- [place, player, number, stat line, running totals by week (race stats)]."""
    pw = player_weeks or {}
    games = {t: len({r["wk"] for r in rows}) for t, rows in pw.items()}
    through = max((r["wk"] for rows in pw.values() for r in rows), default=0)
    totals = []
    for team in pw:
        for r in player_stats.season_totals(pw, team, None):
            r["team"] = team
            totals.append(r)
    weekly = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))   # (team, id) -> week -> stat -> n
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
    for key, cat, name, sh, fn, dec, qual, line, col, race in STATS:
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
            if race and i < 5:
                run, acc = [], defaultdict(int)
                for wk in range(1, through + 1):
                    for k, x in weekly[(r["team"], r["id"])].get(wk, {}).items():
                        acc[k] = max(acc[k], x) if k in player_stats.MAX_STATS else acc[k] + x
                    run.append(round(fn(defaultdict(int, acc)), 1))
                row.append(run)
            rows.append(row)
        if race:   # the chart's five lines in their players' team colors (team_line_colors.py)
            for row, colors in zip(rows[:5], team_line_colors.for_both([players[row[1]][3] for row in rows[:5]])):
                row.append(colors)
        stats.append({"key": key, "cat": cat, "name": name, "short": sh, "dec": dec, "line": line,
                      "col": [c for c, _f in LINES[line]].index(col), "count": len(vals),
                      "qual": _qual_text(qual), "race": race and through > 1, "rows": rows})
    return {"through": through, "players": players, "stats": stats,
            "lines": {k: [c for c, _f in v] for k, v in LINES.items()},
            "cats": CATS, "icons": {c: PS_ICONS.get(c, "") for c, _n in CATS},
            "pills": {t: helmets.pill_html(t, t) for t in DIVISIONS}}


def render(data):
    season = data.get("season") or ""
    d = build(data.get("player_weeks"))
    thru = f"Through Week {d['through']}" if d["through"] else "No games played yet"
    slots, dots = [], []
    for cat, name in CATS:
        stats = [s for s in d["stats"] if s["cat"] == cat]
        ic = f'<span class="t-ic">{d["icons"].get(cat, "")}</span>'
        title = f'<span class="ttl">{ic}<span>{esc(name)}</span></span>'
        tabs = "".join(f'<button class="tab{" on" if j == 0 else ""}" type="button" data-i="{j}">{esc(s["short"])}</button>'
                       for j, s in enumerate(stats))
        panes = "".join(f'<section class="stat" data-stat="{s["key"]}" aria-label="{esc(s["name"])}"></section>' for s in stats)
        slots.append(
            f'<section class="slot" data-cat="{cat}"><div class="card">'
            f'<div class="peek peek-top">{DOWN}{title}</div>'
            f'<div class="body"><div class="tabs" role="tablist">{tabs}</div><div class="strack">{panes}</div></div>'
            f'<div class="peek peek-bot">{UP}{title}</div></div></section>')
        dots.append(f'<button class="dot" type="button" aria-label="{esc(name)}">{d["icons"].get(cat, "")}</button>')
    bar = ("<nav class='bottombar' aria-label='Page controls'><div class='bar-in'>"
           + theme.menu_html("", "leaders") + render_standings._back(data)
           + f'<button class="toggle" type="button" aria-label="Switch to condensed view"><span class="i-plus">{PLUS}</span>'
           + f'<span class="i-minus">{MINUS}</span></button></div></nav>')
    blob = json.dumps(d, separators=(",", ":")).replace("</", "<\\/")
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'>"
        "<meta name='theme-color' content='#F3F3EE'>"
        f"<script>{theme.THEME_HEAD_JS}</script>"
        f"<title>{esc(season)} Stat Leaders · At A Glance</title>"
        "<meta name='description' content='Pro Football Stat Leaders'>"
        f"{logo.favicon_links()}"
        "<link rel='preconnect' href='https://fonts.googleapis.com'>"
        "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;700;900&display=swap' rel='stylesheet'>"
        "<link href='https://fonts.googleapis.com/css2?family=Saira:ital,wdth,wght@1,50..125,400..900&family=Teko:wght@400..700&display=swap' rel='stylesheet'>"
        f"<style>{theme.THEME_CSS}{theme.MENU_CSS}{CSS}</style></head><body data-view='expanded'>"
        f"<header class='top'><span class='yr abbr'>{esc(season)}</span><span class='rs-line'><span class='rs'>Stat Leaders</span>"
        f"<span class='thru'>{esc(thru)}</span></span></header>"
        f"<main class='deck'>{''.join(slots)}</main>"
        "<section class='cview' aria-label='Every stat, condensed'></section>"
        f"<nav class='ic-dots' aria-label='Categories'>{''.join(dots)}</nav>{bar}"
        f"<script type='application/json' id='data'>{blob}</script>"
        f"<script>{theme.THEME_JS}</script><script>{JS}</script>"
        "</body></html>"
    )


def write(data, site_dir):
    path = os.path.join(site_dir, "leaders.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(render(data))
    return path


CSS = """
:root{--bbar:""" + theme.BBAR_HEIGHT + """;--text:var(--aag-text);--text-2:var(--aag-text-2);--text-3:var(--aag-text-3);
  --line:var(--aag-tile-border);--line-soft:var(--aag-tile-border-soft);--gold:#D4A20A;--silver:#A2A7AD;--bronze:#B5702F;
  --peek:40px;--gap:12px;--col:600px;--top-h:72px}
*{box-sizing:border-box;margin:0;padding:0}
/* the page itself never scrolls -- the deck (or the condensed grid) does, under the header */
html,body{height:100%;overflow:hidden;background:var(--aag-bg)}
body{color:var(--text);font-family:Inter,system-ui,-apple-system,sans-serif;-webkit-font-smoothing:antialiased}
button{font:inherit;color:inherit}
.abbr{line-height:1;font-family:Saira,Inter,system-ui,sans-serif;font-weight:800;font-style:italic;font-variation-settings:'wdth' 95;letter-spacing:.02em}
.t-ic{display:inline-flex;align-items:center;flex:none}
.t-ic svg{display:block;width:auto;height:1em}
.empty{text-align:center;font-size:12px;color:var(--text-3);padding:24px 0}

/* the header: the year over "STAT LEADERS · Through Week N" */
.top{display:flex;flex-direction:column;align-items:center;gap:2px;padding:max(10px,env(safe-area-inset-top)) 16px 6px;height:var(--top-h)}
.yr{font-size:34px}
.rs-line{display:flex;gap:6px;align-items:baseline;font-size:11px;white-space:nowrap}
.rs{letter-spacing:.12em;text-transform:uppercase;color:var(--text-2);font-weight:700}
.thru{color:var(--text-3)}
.thru::before{content:"·";margin-right:6px}

/* EXPANDED: the deck -- one category card in the middle, slivers of its neighbours above and below,
   named like Page 1's (.slot / .peek there) */
.deck{height:calc(100vh - var(--top-h) - var(--bbar));height:calc(100dvh - var(--top-h) - var(--bbar));overflow-y:auto;
  scroll-snap-type:y mandatory;padding:calc(var(--peek) + var(--gap)) 0;scrollbar-width:none;overscroll-behavior-y:contain}
.deck::-webkit-scrollbar{display:none}
.slot{height:100%;max-width:var(--col);margin:0 auto var(--gap);padding:0 28px 0 16px;scroll-snap-align:center;scroll-snap-stop:always}
.slot:last-child{margin-bottom:0}
.card{position:relative;height:100%;display:flex;flex-direction:column;transition:transform .2s cubic-bezier(.22,1,.36,1)}
.slot:not(.active) .card{transform:scale(.96)}
.slot.below .card{transform:translateY(-2%) scale(.96)}
.slot.above .card{transform:translateY(2%) scale(.96)}
.body{flex:1;min-height:0;display:flex;flex-direction:column;transition:opacity .15s}
.slot:not(.active) .body{opacity:0}
.peek{display:flex;align-items:center;justify-content:center;gap:7px;font-size:11px;font-weight:700;letter-spacing:.12em;
  text-transform:uppercase;color:var(--text-2);height:calc(var(--peek) - 1px);flex:none}
.peek-top{position:relative}
.peek-bot{position:absolute;left:0;right:0;bottom:0;opacity:0;pointer-events:none}
.slot.above .peek-bot{opacity:1}
.slot.above .peek-top{opacity:0}
.peek-top>svg{display:none}
.slot.below .peek-top>svg{display:block}
.slot.active .peek-top{font-size:13px;color:var(--text)}
.ttl{display:inline-flex;align-items:center;gap:6px}
.slot.active .peek-top .ttl{border:1px solid var(--line);border-radius:999px;padding:4px calc(11px - .12em) 4px 11px;line-height:1.1}

/* the category icons down the right side -- placed and sized like Page 1 / Page 2's .ic-dots */
.ic-dots{position:fixed;right:calc((max(0px, 50% - var(--col) / 2) + 8px) / 2);
  top:calc(var(--top-h) + (100dvh - var(--top-h) - var(--bbar)) / 2);transform:translateY(-50%);z-index:10;
  display:flex;flex-direction:column;align-items:center;gap:36px}
.dot{width:20px;height:20px;border:0;background:none;opacity:.4;display:flex;align-items:center;justify-content:center;cursor:pointer;padding:0;transition:opacity .2s}
.dot svg{display:block;width:20px;height:auto;color:var(--text);transition:transform .2s}
.dot.on{opacity:1}.dot.on svg{transform:scale(1.15)}
.dot:not(.on):hover{opacity:.7}
.dot:focus-visible{outline:2px solid var(--aag-focus);outline-offset:2px}

/* inside a card: the stat tabs, then the stats side by side (swipe left / right) */
.tabs{display:flex;justify-content:center;gap:2px;flex:none;margin:2px 0 4px;overflow-x:auto;scrollbar-width:none}
.tabs::-webkit-scrollbar{display:none}
.tab{background:none;border:1px solid transparent;border-radius:999px;padding:3px 10px;font-size:12px;font-weight:700;opacity:.45;cursor:pointer;white-space:nowrap}
.tab.on{opacity:1;border-color:var(--line)}
.tab:focus-visible{outline:2px solid var(--aag-focus);outline-offset:2px}
.strack{flex:1;min-height:0;display:flex;overflow-x:auto;overflow-y:hidden;scroll-snap-type:x mandatory;scrollbar-width:none;overscroll-behavior-x:contain}
.strack::-webkit-scrollbar{display:none}
.stat{flex:0 0 100%;min-width:0;scroll-snap-align:start;scroll-snap-stop:always;display:flex;flex-direction:column}
.qual{text-align:center;font-size:10px;color:var(--text-3);flex:none;height:13px}

/* the race */
.e-chart{position:relative;flex:none}
/* Total | Behind, on its own line over the chart's right edge (the leader's end label sits in the corner) */
.mode-sw{width:max-content;margin:0 0 2px auto;display:flex;gap:1px;padding:1px;border:1px solid var(--line);border-radius:999px}
.mode-sw button{background:none;border:0;border-radius:999px;padding:1px 7px;font-size:9px;font-weight:700;letter-spacing:.06em;
  text-transform:uppercase;color:var(--text-3);cursor:pointer}
.mode-sw button.on{background:var(--text);color:var(--aag-bg)}
.mode-sw button:focus-visible{outline:2px solid var(--aag-focus);outline-offset:1px}
.race{width:100%;height:auto;display:block;overflow:visible}
.gl{stroke:var(--line-soft);stroke-width:1}
.ax{font-size:9px;fill:var(--text-3)}
.ln{fill:none;stroke-width:2;stroke-linejoin:round;stroke-linecap:round}
.lb{font-size:10px;font-weight:700;fill:var(--text)}
/* each line in its player's team colors, one set for each ground (team_line_colors.py): --lc / --dc the
   line, --lr / --dr the end dot's ring, --ld / --dd the dash (a fallback gray line is dashed) */
.tl{--c:var(--lc);--r:var(--lr);--d:var(--ld)}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]) .tl{--c:var(--dc);--r:var(--dr);--d:var(--dd)}}
:root[data-theme=dark] .tl{--c:var(--dc);--r:var(--dr);--d:var(--dd)}
.ln.tl{stroke:var(--c);stroke-dasharray:var(--d)}
.dt.tl{fill:var(--c);stroke:var(--r);stroke-width:2}
.xh{stroke:var(--text-3);stroke-width:1;stroke-dasharray:2 3;opacity:0}
.race.hover .xh{opacity:1}
.tip{position:absolute;top:0;pointer-events:none;background:var(--aag-bg);border:1px solid var(--line);border-radius:8px;
  padding:5px 8px;font-size:11px;box-shadow:0 4px 14px rgba(0,0,0,.15);white-space:nowrap;z-index:2}
.tip b{display:block;margin-bottom:2px}

/* the ranked list: place, team pill, name over the rest of the stat line, the number -- a faint bar
   behind each row as long as the number. --lead is where the bar starts (after the place and pill). */
.list{flex:1;min-height:0;overflow-y:auto;margin-top:4px;scrollbar-width:none;--lead:76px}
.list::-webkit-scrollbar{display:none}
.list ol{list-style:none}
.tpill{display:inline-flex;align-items:center;justify-content:center;height:18px;min-width:44px;padding:0 5px;border-radius:999px;
  border:2px solid transparent;color:var(--pl);font-size:10px;white-space:nowrap;
  background:linear-gradient(var(--pf1),var(--pf2)) padding-box,linear-gradient(var(--pr1),var(--pr2)) border-box}
.list li{position:relative;display:grid;grid-template-columns:20px 44px minmax(0,1fr) 54px;gap:6px;align-items:center;
  padding:5px 4px;border-bottom:1px solid var(--line-soft)}
.list li:last-child{border-bottom:0}
.list .fill{position:absolute;left:var(--lead);top:3px;bottom:3px;background:var(--aag-tile-hover);border-radius:0 4px 4px 0;z-index:0}
.list li>*:not(.fill){position:relative;z-index:1}
.pl{font-size:11px;font-weight:700;color:var(--text-3);text-align:right;font-variant-numeric:tabular-nums}
.pk{display:inline-block;padding-bottom:1px;border-bottom:3px solid transparent}
.pk.tl{border-color:var(--c)}
.who{min-width:0}
.nm{display:block;font-size:13px;font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
/* the player's position after his name (Jason, 2026-10-07) */
.nm .pos{font-size:10px;font-weight:700;letter-spacing:.04em;color:var(--text-3);margin-left:5px}
/* the rest of the stat line wraps to a second line rather than losing its end -- whole stats at a
   time, the two lines balanced */
.ln2{display:block;font-size:10px;line-height:1.3;color:var(--text-3);font-variant-numeric:tabular-nums;text-wrap:balance}
.ln2 .it{white-space:nowrap}
.ln2 b{font-weight:700;color:var(--text-2)}
/* the stat being ranked, a size up from the rest of the row (Jason, 2026-10-07; was 14px) */
.v{font-variant-numeric:tabular-nums;font-weight:700;text-align:right;font-size:17px}
.more-row{display:flex;justify-content:center;align-items:center;gap:10px;padding:8px 0 4px}
.more{background:none;border:1px solid var(--line);border-radius:999px;padding:4px 12px;font-size:12px;font-weight:700;cursor:pointer}
.more:focus-visible{outline:2px solid var(--aag-focus);outline-offset:2px}
.cnt{font-size:10px;color:var(--text-3)}

/* CONDENSED (body[data-view=condensed]): every stat's leader on one screen, a row of tiles a category
   (picked as "A" in mockups/build_leaders_condensed_mockup.py, 2026-10-07) -- its name over the row; three
   across for passing / rushing / receiving, defense in two rows of three, kicking and returns side by side
   as half-width columns, their two stats stacked. A row's share of the height is its rows of tiles; on a
   phone too short for one screen the tiles keep a minimum height and the view scrolls. */
.cview{display:none;height:calc(100vh - var(--top-h) - var(--bbar));height:calc(100dvh - var(--top-h) - var(--bbar));
  max-width:var(--col);margin:0 auto;padding:2px 16px 8px;overflow-y:auto;flex-direction:column;scrollbar-width:none}
.cview::-webkit-scrollbar{display:none}
body[data-view=condensed] .cview{display:flex}
body[data-view=condensed] .deck,body[data-view=condensed] .ic-dots{display:none}
.crow{flex:1;min-height:0;display:grid;grid-template-columns:repeat(12,minmax(0,1fr));grid-template-rows:auto;
  grid-auto-rows:minmax(54px,1fr);gap:3px 4px;margin-top:4px}
.crow:first-child{margin-top:0}
/* the category's name centered over its row, in the pill outline every card title on the site wears */
.ch{display:flex;justify-content:center;padding:1px 0 0}
.ch .ttl{display:inline-flex;align-items:center;gap:5px;font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;
  border:1px solid var(--line);border-radius:999px;padding:2px calc(9px - .12em) 2px 9px;line-height:1.2}
.ct{display:flex;flex-direction:column;gap:1px;min-width:0;text-align:left;background:var(--aag-tile-hover);
  border:0;border-radius:10px;padding:4px 7px;cursor:pointer}
.ct:focus-visible{outline:2px solid var(--aag-focus);outline-offset:1px}
/* the three-across tiles (picked as "A, Hero" in mockups/build_leaders_tiles_mockup.py, 2026-10-07):
   everything centered -- the stat's name over a big number, then the leader */
.ct:not(.one){align-items:center;justify-content:center;text-align:center}
.ct-top{display:flex;flex-direction:column;align-items:center;gap:1px}
.ct-l{font-size:9px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--text-2)}
.ct-v{font-family:Teko,Inter,sans-serif;font-size:30px;line-height:.85;font-weight:600}
/* the leaders as a two-column grid -- pills in one column, names in the other -- so two tied
   leaders' pills line up over each other; the grid itself is centered in the tile */
.ct-ls{display:grid;grid-template-columns:auto minmax(0,auto);column-gap:4px;row-gap:2px;align-items:center;
  justify-content:center;min-width:0;margin-top:2px}
.ld{display:contents;font-size:11px;line-height:12px}
.ct .nm{text-align:left}
.ct-more{grid-column:1/-1}
.ct .tpill{height:12px;min-width:30px;padding:0 3px;border-width:1.5px;font-size:7.5px;flex:none}
/* last names; a long one wraps to a second line rather than being cut */
.ct .nm{min-width:0;font-size:11px;font-weight:600;white-space:normal;overflow:visible}
.ct-more{font-size:9px;color:var(--text-3)}
/* kicking and returns (half-width, Jason, 2026-10-07): the stat's name stacked over its number on the
   left; to their right the pill and the leader's first initial + last name */
.crow.pair{grid-auto-rows:minmax(40px,1fr)}
.ct.one{flex-direction:row;align-items:center;gap:8px}
.ct.one .ct-top{flex:none;flex-direction:column;align-items:flex-start;justify-content:center;gap:1px}
.ct.one .ct-v{font-size:21px;line-height:.9}
.ct.one .ct-ls{flex:1;min-width:0;justify-content:start;margin-top:0}

/* bottom bar: the menu on the left, "< Week N" back to Page 0 in the middle, +/- on the right */
.bottombar{position:fixed;left:0;right:0;bottom:0;z-index:16;height:var(--bbar);padding-bottom:env(safe-area-inset-bottom);
  background:var(--aag-bar-bg);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px)}
.bar-in{position:relative;max-width:600px;height:52px;margin:0 auto;display:flex;align-items:flex-start;justify-content:center;padding-top:10px}
.week{color:inherit;text-decoration:none;display:inline-flex;align-items:center;gap:6px;font-size:16px;line-height:19px;
  padding:6px 12px;border-radius:999px;transition:background-color .16s}
.week:hover{background:var(--aag-pill-hover)}
.week:focus-visible{outline:2px solid var(--aag-focus);outline-offset:2px}
.week .chev{width:12px;height:12px}
.toggle{position:absolute;right:16px;top:9px;width:34px;height:34px;border:0;background:none;padding:0;display:flex;
  align-items:center;justify-content:center;cursor:pointer;color:var(--text);transition:transform .2s cubic-bezier(.22,1,.36,1)}
.toggle:hover{transform:scale(1.09)}
.toggle:active{transform:scale(1.3)}
.toggle:focus-visible{outline:2px solid var(--aag-focus);outline-offset:2px;border-radius:50%}
.toggle .i-plus{display:none}
body[data-view=condensed] .toggle .i-plus{display:block}
body[data-view=condensed] .toggle .i-minus{display:none}
@media (min-width:780px){
  .ic-dots{right:calc(50% - var(--col) / 2 + 16px - 24px - 48px);gap:28px}
  .dot{width:48px;height:48px}.dot svg{width:44px}
}
"""

JS = r"""
(function () {
  var D = JSON.parse(document.getElementById('data').textContent), P = D.players, S = {};
  D.stats.forEach(function (s) { S[s.key] = s; });
  var deck = document.querySelector('.deck'), slots = [].slice.call(deck.querySelectorAll('.slot')),
      dots = [].slice.call(document.querySelectorAll('.dot')), active = -1, shown = {};
  function esc(t) { return String(t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function num(t) { return parseFloat(String(t).replace(/,/g, '')) || 0; }
  function fmt(s, v) { return s.dec ? v.toFixed(1) : Math.round(v).toLocaleString(); }
  // a line's end label: the last name, no Jr. / Sr. / II, short enough to stay inside the chart
  function endName(nm) { return nm.split('. ').pop().replace(/\s+(Jr\.?|Sr\.?|II|III|IV|V)$/, '').slice(0, 10); }

  // a race line's team colors, light and dark (team_line_colors.py), as the custom properties .tl reads
  function tl(r) { var c = r[5]; return '--lc:' + c.lc + ';--lr:' + c.lr + ';--ld:' + c.ld + ';--dc:' + c.dc + ';--dr:' + c.dr + ';--dd:' + c.dd; }
  // ---- the race: the top 5's running totals, week by week
  var W = 330, H = 150, PL = 30, PR = 62, PT = 8, PB = 18;
  // Total | Behind (Jason, 2026-10-07): "behind" draws each line as his total minus that week's best total
  // among the five, so the leader rides the top line and the gaps keep their real size all season (on
  // an axis from zero they shrink to a sliver as the totals climb -- mockups/build_race_scale_mockup.py).
  // One choice for every chart, remembered on this device; it opens on Behind.
  var mode = 'behind';
  try { if (localStorage.getItem('aag-race') === 'total') mode = 'total'; } catch (e) {}
  function plotted(s) {
    var top = s.rows.slice(0, 5), n = D.through, best = [];
    for (var i = 0; i < n; i++) best.push(Math.max.apply(null, top.map(function (r) { return r[4][i]; })));
    return top.map(function (r) { return r[4].map(function (v, i) { return mode === 'behind' ? v - best[i] : v; }); });
  }
  function signed(s, v) { return v === 0 ? '0' : '−' + fmt(s, -v); }
  function chart(s) {
    var top = s.rows.slice(0, 5), n = D.through, pts = plotted(s), lo = 0, hi = 0;
    pts.forEach(function (p) { p.forEach(function (v) { hi = Math.max(hi, v); lo = Math.min(lo, v); }); });
    if (mode === 'behind') { hi = 0; lo = lo || -1; } else { lo = 0; hi = hi || 1; }
    var x = function (i) { return PL + (W - PL - PR) * i / Math.max(1, n - 1); },
        y = function (v) { return PT + (H - PT - PB) * (1 - (v - lo) / (hi - lo)); };
    var g = [lo, (lo + hi) / 2, hi].map(function (t) {
      var label = mode === 'behind' ? (t === 0 ? 'Leader' : signed(s, t)) : fmt(s, t);
      return '<line class="gl" x1="' + PL + '" x2="' + (W - PR) + '" y1="' + y(t) + '" y2="' + y(t) + '"/><text class="ax" x="' + (PL - 6) + '" y="' + (y(t) + 3) + '" text-anchor="end">' + label + '</text>';
    }).join('');
    for (var i = 0; i < n; i++) g += '<text class="ax" x="' + x(i) + '" y="' + (H - 4) + '" text-anchor="middle">Wk ' + (i + 1) + '</text>';
    // end labels nudged apart so they don't collide
    var ends = pts.map(function (p, i) { return [y(p[n - 1]), i]; }).sort(function (a, b) { return a[0] - b[0]; }), placed = {}, prev = -99;
    ends.forEach(function (e) { var ly = Math.max(e[0], prev + 11); placed[e[1]] = ly; prev = ly; });
    var lines = top.map(function (r, i) {
      var p = pts[i];
      return '<polyline class="ln tl" style="' + tl(r) + '" points="' + p.map(function (v, j) { return x(j) + ',' + y(v); }).join(' ') + '"/>'
        + '<circle class="dt tl" style="' + tl(r) + '" cx="' + x(n - 1) + '" cy="' + y(p[n - 1]) + '" r="4.5"/>'
        + '<text class="lb" x="' + (x(n - 1) + 8) + '" y="' + (placed[i] + 3) + '">' + esc(endName(P[r[1]][0])) + '</text>';
    }).join('');
    var sw = '<div class="mode-sw" role="group" aria-label="Chart shows">'
      + ['total', 'behind'].map(function (m) { return '<button type="button" data-mode="' + m + '"' + (m === mode ? ' class="on" aria-pressed="true"' : ' aria-pressed="false"') + '>' + (m === 'total' ? 'Total' : 'Behind') + '</button>'; }).join('') + '</div>';
    var what = mode === 'behind' ? ': how far each of the top five trails the leader, week by week' : ': running totals by week for the top five';
    return '<div class="e-chart">' + sw + '<svg class="race" viewBox="0 0 ' + W + ' ' + H + '" data-stat="' + s.key + '" role="img" aria-label="' + esc(s.name)
      + what + '">' + g + lines + '<line class="xh" y1="' + PT + '" y2="' + (H - PB) + '"/></svg><div class="tip" hidden></div></div>';
  }
  function hook(svg) {
    var s = S[svg.getAttribute('data-stat')], top = s.rows.slice(0, 5), n = D.through, tip = svg.parentNode.querySelector('.tip'), xh = svg.querySelector('.xh');
    function show(ev) {
      var b = svg.getBoundingClientRect(), px = (ev.clientX - b.left) / b.width * W,
          i = Math.max(0, Math.min(n - 1, Math.round((px - PL) / ((W - PL - PR) / Math.max(1, n - 1))))), x = PL + (W - PL - PR) * i / Math.max(1, n - 1);
      xh.setAttribute('x1', x); xh.setAttribute('x2', x); svg.classList.add('hover');
      var pts = plotted(s);
      tip.innerHTML = '<b>Through week ' + (i + 1) + '</b>' + top.map(function (r, k) {
        return esc(P[r[1]][1]) + ' &nbsp;' + fmt(s, r[4][i]) + (mode === 'behind' && pts[k][i] < 0 ? ' (' + signed(s, pts[k][i]) + ')' : '');
      }).join('<br>');
      tip.hidden = false;
      var left = x / W * b.width + 10; if (left + 150 > b.width) left = x / W * b.width - 160; tip.style.left = left + 'px';
    }
    svg.addEventListener('pointermove', show); svg.addEventListener('pointerdown', show);
    svg.addEventListener('pointerleave', function () { svg.classList.remove('hover'); tip.hidden = true; });
  }
  // ---- the ranked list, each row's stat line under the name
  function line2(s, r) {
    return D.lines[s.line].map(function (c, i) { return i === s.col ? '' : '<span class="it">' + c + ' <b>' + r[3][i] + '</b></span>'; }).filter(Boolean).join(' · ');
  }
  function list(s) {
    if (!s.rows.length) return '<p class="empty">No ' + (s.qual ? 'qualified ' : '') + 'players yet</p>';
    var n = shown[s.key] || (shown[s.key] = 10), hi = num(s.rows[0][2]) || 1, total = s.rows.length;
    var rows = s.rows.slice(0, n).map(function (r, i) {
      var p = P[r[1]], w = Math.max(1, num(r[2]) / hi * 100);
      return '<li title="' + esc(p[1]) + ' (' + p[3] + '): ' + r[2] + '"><span class="fill" style="width:calc((100% - var(--lead)) * ' + (w / 100).toFixed(3) + ')"></span>'
        + '<span class="pl"><span class="pk' + (s.race && r[5] ? ' tl" style="' + tl(r) : '') + '">' + r[0] + '</span></span>' + D.pills[p[3]]
        + '<span class="who"><span class="nm">' + esc(p[1]) + '<span class="pos">' + esc(p[2]) + '</span></span><span class="ln2">' + line2(s, r) + '</span></span>'
        + '<span class="v">' + r[2] + '</span></li>';
    }).join('');
    var ctl = total > 10 ? '<div class="more-row">' + (n < total ? '<button class="more" type="button" data-more="' + s.key + '">Show ' + Math.min(10, total - n) + ' more</button>' : '')
      + (n > 10 ? '<button class="more" type="button" data-fewer="' + s.key + '">Show fewer</button>' : '')
      + '<span class="cnt">' + Math.min(n, total) + ' of ' + total + (s.count > total ? ' (top ' + total + ' of ' + s.count + ')' : '') + '</span></div>' : '';
    return '<ol>' + rows + '</ol>' + ctl;
  }
  function drawStat(el) {
    var s = S[el.getAttribute('data-stat')], race = s.race && s.rows.length;
    // averages have no race chart -- their list gets the whole card
    el.innerHTML = '<div class="qual">' + (s.qual || '') + '</div>' + (race ? chart(s) : '') + '<div class="list">' + list(s) + '</div>';
    if (race) hook(el.querySelector('.race'));
  }
  // flip every chart between Total and Behind (only the charts redraw -- the lists keep their place)
  function setMode(m) {
    mode = m;
    try { localStorage.setItem('aag-race', m); } catch (e) {}
    document.querySelectorAll('.e-chart').forEach(function (c) {
      var k = c.querySelector('.race').getAttribute('data-stat'), wrap = document.createElement('div');
      wrap.innerHTML = chart(S[k]); c.replaceWith(wrap.firstChild);
      hook(document.querySelector('.stat[data-stat="' + k + '"] .race'));
    });
  }
  function redraw(k) {
    var l = document.querySelector('.stat[data-stat="' + k + '"] .list'), y = l.scrollTop;
    l.innerHTML = list(S[k]); l.scrollTop = y;
  }
  document.querySelectorAll('.stat').forEach(drawStat);

  // ---- the deck: which card is in the middle, its neighbours as slivers, the icons following
  function setActive(i) {
    if (i === active) return;
    active = i;
    slots.forEach(function (s, k) { s.classList.toggle('active', k === i); s.classList.toggle('above', k < i); s.classList.toggle('below', k > i); });
    dots.forEach(function (d, k) { d.classList.toggle('on', k === i); d.setAttribute('aria-current', k === i ? 'true' : 'false'); });
  }
  function current() {
    var mid = deck.scrollTop + deck.clientHeight / 2, best = 0, bd = Infinity;
    slots.forEach(function (s, k) { var c = s.offsetTop + s.offsetHeight / 2 - deck.offsetTop, d = Math.abs(c - mid); if (d < bd) { bd = d; best = k; } });
    return best;
  }
  function go(i, smooth) {
    var s = slots[i]; if (!s) return;
    deck.scrollTo({ top: s.offsetTop - deck.offsetTop - (deck.clientHeight - s.offsetHeight) / 2, behavior: smooth ? 'smooth' : 'auto' });
  }
  var tick = false;
  deck.addEventListener('scroll', function () { if (!tick) { tick = true; requestAnimationFrame(function () { setActive(current()); tick = false; }); } }, { passive: true });
  dots.forEach(function (d, k) { d.addEventListener('click', function () { go(k, true); }); });
  slots.forEach(function (s, k) { s.querySelector('.card').addEventListener('click', function (e) { if (k !== active && !e.target.closest('button')) go(k, true); }); });

  // ---- inside a card: the tabs follow the sideways swipe, and jump to a stat
  function tabsFollow(card) {
    var tr = card.querySelector('.strack'), i = Math.round(tr.scrollLeft / tr.clientWidth);
    card.querySelectorAll('.tab').forEach(function (t, k) { t.classList.toggle('on', k === i); t.setAttribute('aria-selected', k === i ? 'true' : 'false'); });
  }
  document.querySelectorAll('.card').forEach(function (card) {
    var tr = card.querySelector('.strack'), settle;
    tr.addEventListener('scroll', function () { clearTimeout(settle); settle = setTimeout(function () { tabsFollow(card); }, 80); }, { passive: true });
  });
  document.addEventListener('click', function (e) {
    var t;
    if ((t = e.target.closest('.tab'))) {
      var tr = t.closest('.card').querySelector('.strack');
      tr.scrollTo({ left: +t.getAttribute('data-i') * tr.clientWidth, behavior: 'smooth' }); return;
    }
    if ((t = e.target.closest('[data-mode]'))) { if (t.getAttribute('data-mode') !== mode) setMode(t.getAttribute('data-mode')); return; }
    if ((t = e.target.closest('[data-more]'))) { var k = t.getAttribute('data-more'); shown[k] += 10; redraw(k); return; }
    if ((t = e.target.closest('[data-fewer]'))) { var k2 = t.getAttribute('data-fewer'); shown[k2] = 10; redraw(k2); }
  });

  // ---- condensed: a row of tiles a category, first place only (up to three tied, last names)
  var cv = document.querySelector('.cview'), byCat = {};
  D.stats.forEach(function (s) { (byCat[s.cat] = byCat[s.cat] || []).push(s); });
  function lastName(full) {
    var t = full.replace(/\s+(Jr\.?|Sr\.?|II|III|IV|V)$/, ''), i = t.indexOf(' ');
    return i < 0 ? t : t.slice(i + 1);
  }
  function tile(s, span) {
    // first place: two tied at most, "+N more tied" past that (Jason, 2026-10-07; was three)
    var first = s.rows.filter(function (r) { return r[0] === 1; }), extra = first.length - 2;
    return '<button class="ct' + (span === 6 ? ' one' : '') + '" type="button" style="grid-column:span ' + span + '" data-open="' + s.key + '">'
      + '<span class="ct-top"><span class="ct-l">' + esc(s.short) + '</span><span class="ct-v">' + (first.length ? first[0][2] : '—') + '</span></span><span class="ct-ls">'
      // names: the last name, or first initial + last name in the half-width tiles (kicking, returns)
      + first.slice(0, 2).map(function (r) { var p = P[r[1]]; return '<span class="ld">' + D.pills[p[3]] + '<span class="nm">' + esc(span === 6 ? p[0] : lastName(p[1])) + '</span></span>'; }).join('')
      + (extra > 0 ? '<span class="ct-more">+' + extra + ' more tied</span>' : '') + '</span></button>';
  }
  function row(cats) {
    var heads = cats.map(function (c) { return '<div class="ch" style="grid-column:span ' + (12 / cats.length) + '"><span class="ttl"><span class="t-ic">' + (D.icons[c[0]] || '') + '</span>' + esc(c[1]) + '</span></div>'; }).join('');
    var stats = [], span = 4;
    if (cats.length > 1) {   // two small categories side by side, each a half-width column of its stats
      span = 6;
      var lists = cats.map(function (c) { return byCat[c[0]] || []; }), most = Math.max.apply(null, lists.map(function (l) { return l.length; }));
      for (var i = 0; i < most; i++) lists.forEach(function (l) { stats.push(l[i] || null); });
    } else stats = byCat[cats[0][0]] || [];
    var tiles = stats.map(function (s) { return s ? tile(s, span) : '<span style="grid-column:span ' + span + '"></span>'; }).join('');
    // a row's share of the height: its rows of tiles (the one-line half-width tiles count a row between them)
    var share = span === 6 ? 1 : Math.ceil(stats.length * span / 12);
    return '<section class="crow' + (span === 6 ? ' pair' : '') + '" style="flex:' + share + '">' + heads + tiles + '</section>';
  }
  // a category with three or more stats gets its own row; two-stat categories pair up side by side
  var rowsHtml = '', pend = null;
  D.cats.forEach(function (c) {
    var n = (byCat[c[0]] || []).length;
    if (n > 2) { if (pend) { rowsHtml += row([pend]); pend = null; } rowsHtml += row([c]); }
    else if (pend) { rowsHtml += row([pend, c]); pend = null; }
    else pend = c;
  });
  if (pend) rowsHtml += row([pend]);
  cv.innerHTML = rowsHtml;
  function setView(v) {
    document.body.setAttribute('data-view', v);
    document.querySelector('.toggle').setAttribute('aria-label', v === 'condensed' ? 'Switch to expanded view' : 'Switch to condensed view');
    if (v === 'expanded') go(active, false);
  }
  // open the expanded view at a stat: its category's card, turned to it
  function openStat(key) {
    var s = S[key], i = slots.findIndex(function (x) { return x.getAttribute('data-cat') === s.cat; }), slot = slots[i];
    setView('expanded'); setActive(i); go(i, false);
    var tr = slot.querySelector('.strack'), j = [].slice.call(tr.children).findIndex(function (x) { return x.getAttribute('data-stat') === key; });
    tr.scrollLeft = j * tr.clientWidth; tabsFollow(slot.querySelector('.card'));
  }
  document.querySelector('.toggle').addEventListener('click', function () { setView(document.body.getAttribute('data-view') === 'condensed' ? 'expanded' : 'condensed'); });
  cv.addEventListener('click', function (e) { var t = e.target.closest('[data-open]'); if (t) openStat(t.getAttribute('data-open')); });

  // #defense opens on that card; #defense-2 on its third stat; #condensed on the condensed view
  var h = location.hash.slice(1).split('-'), start = Math.max(0, slots.findIndex(function (s) { return s.getAttribute('data-cat') === h[0]; }));
  setActive(start); go(start, false);
  if (h[1]) { var tr0 = slots[start].querySelector('.strack'); tr0.scrollLeft = +h[1] * tr0.clientWidth; tabsFollow(slots[start].querySelector('.card')); }
  if (h[0] === 'condensed') setView('condensed');
  window.addEventListener('resize', function () { go(active, false); });
})();
"""
