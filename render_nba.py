"""
Renders the NBA section (2026-10-08) from data/nba.json (after build_nba_data.py has run):

  site/nba/index.html       Page 0: each day's games, a day picker + swipe (the NFL's index.html,
                            by day instead of by week) -- the days around today, not the whole
                            season (build_nba_data.timely)
  site/nba/game/*.html      each game's page and deep dives (render_nba_game.py)
  site/nba/standings.html   Division / Conference / League, with games behind
  site/nba/leaders.html     the league's per-game leaders
  site/nba/balls/*.svg      each team's basketball (nba_balls.py)

Run with: python render_nba.py  (--data to read another file, e.g. one built with --season)

Built as a copy of the NFL pages: the same stylesheets, scripts, layout and gestures, taken from
render_html.py, render_standings.py and render_leaders.py as they are, with the markup written here
for basketball. The differences:
  - Page 0 has a panel per day with games, not per week; the picker lists the week before and the
    two weeks after the day it opens on, and the address is #day-2026-10-20. It opens on today, or
    the next day with games. No "Teams on Bye".
  - tiles: national TV, or "Local TV" when a game has none; a playoff game's round and game number,
    or the NBA Cup round, under it. A game in progress (from ESPN's scoreboard) shows its score
    and clock; a finished one FINAL, FINAL/OT, FINAL/2OT...
  - standings: W, L, PCT, GB, CONF, DIV, L10, STRK. Games behind count from the leader of what's
    shown -- the division on Division, the conference on Conference, the league on League.
    Conference view: 1-6 make the playoffs, 7-10 the Play-In, 11-15 the lottery. Clinch marks come
    from ESPN's standings file once it's out for the season.
  - stat leaders: per game, qualified by the NBA's minimums (nba_stats.py); the race charts follow
    each top five's average week by week.
"""

import argparse
import html
import json
import os
import traceback
from collections import defaultdict
from datetime import date

import local_time
import logo
import names
import nba_balls
import nba_helmets
import nba_stats
import nba_teams
import render_html
import render_leaders
import render_nba_game
import render_page1
import render_page2players
import render_standings
import team_line_colors
import theme

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(ROOT, "data", "nba.json")
SITE_DIR = os.path.join(ROOT, "site", "nba")
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DASH = "—"


def esc(v):
    return html.escape(str(v), quote=True)


def fonts():
    return ("<link rel='preconnect' href='https://fonts.googleapis.com'>"
            "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
            "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;700;900&display=swap' rel='stylesheet'>"
            "<link href='https://fonts.googleapis.com/css2?family=Saira:ital,wdth,wght@1,50..125,400..900&family=Teko:wght@400..700&display=swap' rel='stylesheet'>")


def head(title, description):
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'>"
            "<meta name='theme-color' content='#F3F3EE'>"
            f"<script>{theme.THEME_HEAD_JS}</script><title>{esc(title)}</title>"
            f"<meta name='description' content='{esc(description)}'>{logo.favicon_links('../')}{fonts()}")


def short_day(iso):
    try:
        d = date.fromisoformat(str(iso)[:10])
    except (TypeError, ValueError):
        return ""
    return f"{MONTHS[d.month - 1]} {d.day}"


def back_link(data):
    """"< Tue, Oct 20" back to Page 0's day (the one Page 0 opens on)."""
    key = data.get("current_day_key")
    label = next((d["label"] for d in data.get("days") or [] if d["key"] == key), None)
    href = f"index.html#day-{key}" if key else "index.html"
    return f'<a class="week" href="{esc(href)}">{render_page1.CHEV}<span>{esc(label or "Games")}</span></a>'


# ---------------------------------------------------------------- Page 0

def fmt_record(r):
    return f'{(r or {}).get("wins", 0)}-{(r or {}).get("losses", 0)}' if r else ""


def team_html(side, away):
    team = side.get("team")
    return ('<div class="team">'
            f'<img class="hm" src="balls/{esc(nba_balls.ball_filename(team, away))}" alt="" width="48" height="48" loading="lazy">'
            f'<span class="abbr">{esc(team or "TBD")}</span></div>')


def network_html(m):
    lines = [m.get("networks") or "Local TV"]
    if m.get("note"):   # a playoff game's round, an NBA Cup round, a game abroad
        lines.append(m["note"].replace("NBA Cup - ", "NBA Cup · "))
    return "".join(f'<span class="network">{esc(x)}</span>' for x in lines)


def upcoming_tile(m):
    away, home = m.get("away") or {}, m.get("home") or {}
    t = "PPD" if m.get("postponed") else render_html.format_time(m.get("gametime"))
    names = f'{nba_teams.full_name(away.get("team"))} at {nba_teams.full_name(home.get("team"))}'
    # the tip-off in the viewer's own time zone (local_time.py); a postponed game keeps its PPD
    lt = (lambda mode, aria=None: "") if m.get("postponed") else \
        (lambda mode, aria=None: local_time.attrs(m.get("gameday"), m.get("gametime"), mode, aria))
    return (f'<a class="game" href="#game-{esc(m["game_id"])}" aria-label="{esc(names + ", " + t)}"{lt("a", names + ", {t}")}>{team_html(away, True)}'
            f'{render_html.render_stack(away.get("team"), fmt_record(away.get("record")), "away")}'
            f'<div class="center"><span class="time"{lt("t")}>{render_html.time_html(t)}</span>{network_html(m)}</div>'
            f'{render_html.render_stack(home.get("team"), fmt_record(home.get("record")), "home")}{team_html(home, False)}</a>')


def final_tile(m):
    """Finished (or, from ESPN's scoreboard, still going): the NFL's FINAL tile."""
    away, home = m.get("away") or {}, m.get("home") or {}
    a_s, h_s = away.get("score"), home.get("score")
    a_cls = h_cls = "score"
    win = ""
    live = m.get("live")
    if not live and a_s is not None and h_s is not None:
        if a_s > h_s:
            h_cls += " lose"
            win = "away"
        elif h_s > a_s:
            a_cls += " lose"
            win = "home"
    ot = m.get("ot") or 0
    text = (m.get("status_detail") or "LIVE").upper() if live else "FINAL" + ("/OT" if ot == 1 else f"/{ot}OT" if ot > 1 else "")
    label = (f'{"Live" if live else "Final"}: {nba_teams.full_name(away.get("team"))} {render_html._score_text(a_s)}, '
             f'{nba_teams.full_name(home.get("team"))} {render_html._score_text(h_s)}')
    side = lambda s, cls, score: (f'<div class="result {s}"><span class="abbr abbr-c" aria-hidden="true">{esc((m.get(s) or {}).get("team") or "TBD")}</span>'
                                  f'<span class="{cls}">{esc(render_html._score_text(score))}</span>'
                                  f'<span class="team-record">{esc(fmt_record((m.get(s) or {}).get("record")))}</span></div>')
    return (f'<a class="game final{" live" if live else ""}" data-win="{win}" href="#game-{esc(m["game_id"])}" aria-label="{esc(label)}"'
            f'{local_time.attrs(m.get("gameday"), m.get("gametime"), "k")}>'
            f'{team_html(away, True)}{side("away", a_cls, a_s)}'
            f'<div class="center"><span class="final-row"><span class="tri tri-a">{render_html.WIN_TRI}</span>'
            f'<span class="final-label">{esc(text)}</span><span class="tri tri-h">{render_html.WIN_TRI}</span></span></div>'
            f'{side("home", h_cls, h_s)}{team_html(home, False)}</a>')


def day_panel(day, is_current):
    rows = []
    for i, m in enumerate(day["games"]):
        try:
            rows.append(f'<li style="{render_html.rise_delay(i)}">{final_tile(m) if (m.get("final") or m.get("live")) else upcoming_tile(m)}</li>')
        except Exception:
            rows.append(f'<li style="{render_html.rise_delay(i)}"><div class="error">Failed to render one game\n{esc(traceback.format_exc())}</div></li>')
    return (f'<div class="week-panel" id="day-{esc(day["key"])}" data-key="{esc(day["key"])}" data-label="{esc(day["label"])}"'
            f' data-current="{"true" if is_current else "false"}" role="group" aria-label="{esc(day["long_label"])}">'
            f'<div class="week-inner"><section data-day="{esc(day["key"])}"><h2 class="day"><span class="day-pill">{esc(day["long_label"])}</span></h2>'
            f'<ul class="games">{"".join(rows)}</ul></section></div></div>')


# Page 0's script, its hashes by day; the overlay's, handed the game stylesheet from this page (the
# game pages link to a shared file instead of carrying their own copy -- render_nba_game.py)
PAGE0_JS = render_html.PAGE0_JS.replace("#week-", "#day-")
OVERLAY_JS = render_html.PAGE1_OVERLAY_JS.replace(
    "(css ? css.textContent : '')",
    "((css && css.textContent) || (document.getElementById('p1-css-src') || {}).textContent || '')")
assert PAGE0_JS != render_html.PAGE0_JS and OVERLAY_JS != render_html.PAGE1_OVERLAY_JS

PAGE0_EXTRA_CSS = """
.game.live .final-label{color:var(--aag-loss);letter-spacing:.02em}
.center .network+.network{margin-top:-2px}
/* NBA records run to "41-26" (the NFL's to "3-1"), so on a phone they sit beside their helmets rather
   than halfway to the middle, where they'd run into the tip-off time */
@media (max-width:420px){
  [data-view=expanded] .stack.away,[data-view=expanded] .result.away{align-items:flex-start;padding-left:4px}
  [data-view=expanded] .stack.home,[data-view=expanded] .result.home{align-items:flex-end;padding-right:4px}
  [data-view=expanded] .record,[data-view=expanded] .team-record{font-size:15px}
}
"""


def render_page0(data):
    days = data.get("days") or []
    current = data.get("current_day_key")
    if days and current not in [d["key"] for d in days]:
        current = days[0]["key"]
    panels = "".join(day_panel(d, d["key"] == current) for d in days)
    if not days:
        panels = ('<div class="week-panel" data-key="none" data-label="No games" data-current="true">'
                  '<div class="week-inner"><p class="empty">No games scheduled yet.</p></div></div>')
    options = "".join(f'<option value="{esc(d["key"])}"{" selected" if d["key"] == current else ""}>{esc(d["label"])}</option>'
                      for d in days) or '<option value="none" selected>No games</option>'
    label = next((d["label"] for d in days if d["key"] == current), "No games")
    css_src = render_nba_game.p1_css().replace("</", "<\\/")
    return (head(f"{label} · NBA · At A Glance", "Pro Basketball Game Information")
            + f"<style>{render_html.PAGE0_CSS}{PAGE0_EXTRA_CSS}</style></head><body data-view='expanded'>"
            f"<main class='track' id='track' data-days='day'>{panels}</main>"
            "<nav class='bottombar' aria-label='Day'><div class='bar-in'>"
            f"{theme.menu_html('../', 'nba-games')}"
            f"<label class='week-picker'><span id='week-label'>{esc(label)}</span>"
            "<svg class='chevron' viewBox='0 0 12 12' aria-hidden='true'><path d='M2.5 7.5 6 4l3.5 3.5' fill='none' stroke='currentColor' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'/></svg>"
            f"<select id='week-select' aria-label='Choose day'>{options}</select></label>"
            "<button class='toggle' id='view-toggle' type='button' aria-label='Switch to condensed view' aria-pressed='false'>"
            f"<span class='i-plus'>{render_page1.PLUS}</span><span class='i-minus'>{render_page1.MINUS}</span></button>"
            "</div></nav>"
            f"<script type='text/plain' id='p1-css-src'>{css_src}</script>"
            f"<script>{theme.THEME_JS}</script><script>{local_time.JS}</script><script>{PAGE0_JS}</script>"
            f"<script>{render_page1.P1_JS}</script><script>{OVERLAY_JS}</script></body></html>")


# ---------------------------------------------------------------- standings

CONFS = ("East", "West")
HEADS = ("W", "L", "PCT", "GB", "CONF", "L10", "STRK")
LEGEND = (("W", "Wins"), ("L", "Losses"), ("PCT", "Win percentage"),
          ("GB", "Games behind the leader of the group shown"), ("CONF", "Record against conference opponents"),
          ("L10", "Record in the last 10 games"),
          ("STRK", "Current streak: W3 = three wins in a row"))
# ESPN's marks, as its standings file describes them
CLINCH_KEY = (("x", "Clinched a playoff berth"), ("y", "Clinched the division"), ("z", "Clinched the conference"),
              ("*", "Clinched the best record in the league"), ("pb", "Clinched a Play-In spot"),
              ("xp", "Made the playoffs through the Play-In"), ("e", "Eliminated from the playoffs"))
STANDINGS_CSS = """
.row{grid-template-columns:var(--team-w) repeat(2,minmax(0,.8fr)) minmax(0,1.15fr) minmax(0,.95fr) repeat(2,minmax(0,1.2fr)) minmax(0,.95fr)}
.seeded .row{grid-template-columns:16px var(--team-w) repeat(2,minmax(0,.8fr)) minmax(0,1.15fr) minmax(0,.95fr) repeat(2,minmax(0,1.2fr)) minmax(0,.95fr)}
.mk{width:14px;font-size:10px}
.n.sub{white-space:nowrap}
@media (max-width:400px){:root{--team-w:70px}.row,.seeded .row{column-gap:2px}.who{gap:4px}}
@media (max-width:359px){
  .seeded .row{grid-template-columns:13px var(--team-w) repeat(2,minmax(0,.8fr)) minmax(0,1.15fr) minmax(0,.95fr) repeat(2,minmax(0,1.2fr)) minmax(0,.95fr)}}
"""


def _pct(r):
    return ".000" if not r["w"] + r["l"] else (f'{r["pct"]:.3f}'.lstrip("0") if r["pct"] < 1 else "1.000")


def _gb(lead, r):
    v = ((lead["w"] - r["w"]) + (r["l"] - lead["l"])) / 2
    return "–" if v == 0 else (f"{v:.0f}" if v % 1 == 0 else f"{v:.1f}")


def _row(r, lead, seed=None, end=False):
    lead_html = f'<span class="seed">{seed}</span>' if seed is not None else ""
    return (f'<div class="row{" end" if end else ""}">{lead_html}'
            f'<span class="who"><span class="mk">{esc(r.get("clinch") or "")}</span>{nba_balls.ball_img(r["team"], 18)}'
            f'<span class="abbr">{esc(r["team"])}</span></span>'
            f'<span class="n">{r["w"]}</span><span class="n">{r["l"]}</span><span class="n">{_pct(r)}</span>'
            f'<span class="n">{_gb(lead, r)}</span><span class="n sub">{r["cw"]}-{r["cl"]}</span>'
            f'<span class="n sub">{esc(r["l10"])}</span>'
            f'<span class="n">{esc(r["streak"]) or DASH}</span></div>')


def _group(label, rows, seeded=False, bands=None, gid=None):
    bands = dict(bands or {})
    label = bands.pop(1, label)
    lead = "<span></span>" if seeded else ""
    head_html = (f'<div class="row head">{lead}<span class="grp">{esc(label)}</span>'
                 + "".join(f'<span class="n">{h}</span>' for h in HEADS) + "</div>")
    body = []
    for i, r in enumerate(rows, 1):
        if i in bands:
            body.append(f'<div class="band">{esc(bands[i])}</div>')
        body.append(_row(r, rows[0], seed=i if seeded else None, end=(i == len(rows) or (i + 1) in bands)))
    gid_attr = f' id="{gid}"' if gid else ""
    return (f'<section class="grp-box{" seeded" if seeded else ""}"{gid_attr} style="--n:{len(rows)}">'
            f'{head_html}{"".join(body)}</section>')


def _key_card(prev):
    cols = "".join(f'<div><dt>{k}</dt><dd>{esc(v)}</dd></div>' for k, v in LEGEND)
    marks = "".join(f'<div><dt class="mkk">{k}</dt><dd>{esc(v)}</dd></div>' for k, v in CLINCH_KEY)
    return (f'<article class="pc pc-key">{render_standings._peek(prev, up=True)}'
            f'<footer class="legend"><h3>Key</h3><dl>{cols}</dl><h3>Clinched</h3><dl>{marks}</dl>'
            '<p class="note">Seeds 1–6 make the playoffs; 7–10 meet in the Play-In Tournament for the last two '
            'spots. Ties are broken by win percentage against the conference, then the division -- '
            'not the NBA’s full tiebreakers.</p></footer></article>')


def render_standings_page(data):
    from build_nba_data import order
    rows = data.get("standings") or []
    season = data.get("season_label") or ""
    thru = f"Through {short_day(data.get('standings_through'))}" if data.get("standings_through") else "No games played yet"
    card = render_standings._card
    division = "".join(
        card(c, "".join(_group(dv, order([r for r in rows if r["conf"] == c and r["div"] == dv]), gid=f"{c}-{dv}".lower())
                        for dv in nba_teams.DIVISIONS[c]),
             prev=None if c == "East" else "East", nxt="West" if c == "East" else "Key")
        for c in CONFS) + _key_card("West")
    conference = "".join(
        card(c, _group("", order([r for r in rows if r["conf"] == c]), seeded=True,
                       bands={1: "Playoffs", 7: "Play-In", 11: "Lottery"}),
             prev=None if c == "East" else "East", nxt="West" if c == "East" else "Key")
        for c in CONFS) + _key_card("West")
    league = card("", _group("", order(rows), seeded=True), nxt="Key", long=True) + _key_card("League")
    views = (("division", division), ("conference", conference), ("league", league))
    tabs = "".join(f'<button class="sw-tab{" on" if v == "division" else ""}" type="button" role="tab" '
                   f'aria-selected="{"true" if v == "division" else "false"}" data-view="{v}">{v.title()}</button>' for v, _b in views)
    panes = "".join(f'<section class="pane" data-pane="{v}" role="tabpanel" aria-label="{v.title()}"><div class="pane-in">{b}</div></section>'
                    for v, b in views)
    return (head(f"{season} Standings · NBA · At A Glance", "Pro Basketball Standings")
            + f"<style>{theme.THEME_CSS}{theme.MENU_CSS}{theme.HELMET_SHADOW_CSS}{render_standings.CSS}{STANDINGS_CSS}</style></head><body>"
            f"<header class='top'><div class='top-in'><h1 class='title'><span class='yr abbr'>{esc(season)}</span>"
            f"<span class='rs-line'><span class='rs'>Regular Season</span><span class='thru'>{esc(thru)}</span></span></h1>"
            f"<div class='sw' role='tablist' aria-label='Standings by'>{tabs}</div></div></header>"
            f"<main class='track' id='track'>{panes}</main>"
            "<nav class='bottombar' aria-label='Page controls'><div class='bar-in'>"
            f"{theme.menu_html('../', 'nba-standings')}{back_link(data)}</div></nav>"
            f"<script>{theme.THEME_JS}</script><script>{render_standings.JS}</script></body></html>")


# ---------------------------------------------------------------- stat leaders

TOP = 100


def _f1(v):
    return DASH if v is None else f"{v:.1f}"


def _f0(v):
    return DASH if v is None else f"{int(round(v)):,}"


LINES = {
    "scoring": [("PTS", lambda r: _f1(r["pts"])), ("FG%", lambda r: _f1(r["fg_pct"])), ("3P%", lambda r: _f1(r["tp_pct"])),
                ("FT%", lambda r: _f1(r["ft_pct"])), ("MIN", lambda r: _f1(r["min"])), ("GP", lambda r: _f0(r["gp"]))],
    "rebounding": [("REB", lambda r: _f1(r["reb"])), ("OREB", lambda r: _f1(r["oreb"])), ("DREB", lambda r: _f1(r["dreb"])),
                   ("MIN", lambda r: _f1(r["min"])), ("GP", lambda r: _f0(r["gp"]))],
    "threes": [("3PM", lambda r: _f1(r["tpm"])), ("3PA", lambda r: _f1(r["tpa"])), ("3P%", lambda r: _f1(r["tp_pct"])),
               ("GP", lambda r: _f0(r["gp"]))],
    "playmaking": [("AST", lambda r: _f1(r["ast"])), ("TO", lambda r: _f1(r["tov"])),
                   ("A/TO", lambda r: _f1(r["ast_t"] / r["tov_t"]) if r["tov_t"] else DASH), ("GP", lambda r: _f0(r["gp"]))],
    "defense": [("STL", lambda r: _f1(r["stl"])), ("BLK", lambda r: _f1(r["blk"])), ("PF", lambda r: _f1(r["pf"])),
                ("GP", lambda r: _f0(r["gp"]))],
    "minutes": [("MIN", lambda r: _f1(r["min"])), ("GP", lambda r: _f0(r["gp"])), ("GS", lambda r: _f0(r["gs"])),
                ("DD", lambda r: _f0(r["dd"]))],
}
# (key, category, name, short name, value, decimals, qualifying stat, stat line, its column, race chart)
STATS = [
    ("pts", "scoring", "Points per Game", "PTS", lambda r: r["pts"], 1, None, "scoring", "PTS", True),
    ("fg_pct", "scoring", "Field Goal %", "FG%", lambda r: r["fg_pct"], 1, "fg_pct", "scoring", "FG%", False),
    ("ft_pct", "scoring", "Free Throw %", "FT%", lambda r: r["ft_pct"], 1, "ft_pct", "scoring", "FT%", False),
    ("reb", "rebounding", "Rebounds per Game", "REB", lambda r: r["reb"], 1, None, "rebounding", "REB", True),
    ("oreb", "rebounding", "Offensive Rebounds", "OREB", lambda r: r["oreb"], 1, None, "rebounding", "OREB", True),
    ("dreb", "rebounding", "Defensive Rebounds", "DREB", lambda r: r["dreb"], 1, None, "rebounding", "DREB", True),
    ("tpm", "threes", "3-Pointers Made per Game", "3PM", lambda r: r["tpm"], 1, None, "threes", "3PM", True),
    ("tp_pct", "threes", "3-Point %", "3P%", lambda r: r["tp_pct"], 1, "tp_pct", "threes", "3P%", False),
    ("ast", "playmaking", "Assists per Game", "AST", lambda r: r["ast"], 1, None, "playmaking", "AST", True),
    ("ato", "playmaking", "Assist-to-Turnover Ratio", "A/TO", lambda r: r["ast_t"] / r["tov_t"] if r["tov_t"] else None,
     1, None, "playmaking", "A/TO", False),
    ("stl", "defense", "Steals per Game", "STL", lambda r: r["stl"], 1, None, "defense", "STL", True),
    ("blk", "defense", "Blocks per Game", "BLK", lambda r: r["blk"], 1, None, "defense", "BLK", True),
    ("min", "minutes", "Minutes per Game", "MIN", lambda r: r["min"], 1, None, "minutes", "MIN", True),
    ("dd", "minutes", "Double-Doubles", "DD", lambda r: r["dd"], 0, "games", "minutes", "DD", True),
]
CATS = [("scoring", "Scoring"), ("rebounding", "Rebounding"), ("threes", "3-Pointers"), ("playmaking", "Playmaking"),
        ("defense", "Defense"), ("minutes", "Minutes")]
# each category's (placeholder) icon: the NFL Stat Leaders' category icons, in the same order
CAT_ICONS = {"scoring": "passing", "rebounding": "rushing", "threes": "receiving", "playmaking": "kicking",
             "defense": "defense", "minutes": "returns"}


def _double(r):
    return sum(1 for k in ("pts", "reb", "ast", "stl", "blk") if (r.get(k) or 0) >= 10) >= 2


def leaders_data(data):
    """render_leaders.build's output shape, from player_games: players once, then each stat's
    ranked rows [place, player, number, stat line, (race: running average by week, colors)]."""
    pg = data.get("player_games") or {}
    rows = sorted((dict(r, team=t) for t, rs in pg.items() for r in rs if r["st"] == 2), key=lambda r: (r["date"], r["gid"]))
    if not rows:
        return {"through": 0, "through_day": None, "players": [], "stats": [], "lines": {k: [c for c, _f in v] for k, v in LINES.items()},
                "cats": CATS, "icons": {c: render_page2players.PS_ICONS.get(CAT_ICONS[c], "") for c, _n in CATS}, "pills": {}}
    opener = date.fromisoformat(rows[0]["date"])
    week = lambda iso: (date.fromisoformat(iso) - opener).days // 7 + 1
    through = week(rows[-1]["date"])
    team_games = defaultdict(set)
    tot = defaultdict(lambda: defaultdict(float))      # player -> stat -> season total
    weekly = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))   # player -> week -> stat -> total
    info, latest_team = {}, {}
    for r in rows:
        team_games[r["team"]].add(r["gid"])
        if r["dnp"]:
            continue
        p = r["id"]
        info[p], latest_team[p] = r, r["team"]
        w = week(r["date"])
        for k in nba_stats.COUNTING:
            tot[p][k] += r.get(k) or 0
            weekly[p][w][k] += r.get(k) or 0
        for bucket in (tot[p], weekly[p][w]):
            bucket["gp"] += 1
            bucket["gs"] += r["starter"]
            bucket["dd"] += _double(r)
    lines = {}
    for p, t in tot.items():
        line = nba_stats._line(p, info[p], int(t["gp"]), t, int(t["gs"]), latest_team[p])
        line["dd"] = int(t["dd"])
        lines[p] = line
    n_games = {t: len(g) for t, g in team_games.items()}
    players, index = [], {}

    def pid(r):
        if r["id"] not in index:
            index[r["id"]] = len(players)
            players.append([names.short_name(r["name"]), r["name"], r["pos"], r["team"], names.bare_last(r["name"])])
        return index[r["id"]]

    stats = []
    for key, cat, name, sh, fn, dec, qual, line, col, race in STATS:
        vals = []
        for p, r in lines.items():
            n = n_games.get(r["team"], 0)
            if qual != "games" and not nba_stats.qualified(r, n, qual):
                continue
            v = fn(r)
            if v is not None and v > 0:
                vals.append((v, r))
        vals.sort(key=lambda x: (-x[0], x[1]["name"]))
        out = []
        for i, (v, r) in enumerate(vals[:TOP]):
            place = 1 + sum(1 for w, _ in vals[:i] if w > v)
            row = [place, pid(r), f"{v:.1f}" if dec else f"{int(round(v)):,}", [f(r) for _c, f in LINES[line]]]
            if race and i < 5:
                run, acc = [], defaultdict(float)
                for w in range(1, through + 1):
                    for k, x in weekly[r["id"]].get(w, {}).items():
                        acc[k] += x
                    g = acc["gp"]
                    run.append(round(acc[key] if key == "dd" else (acc[key] / g if g else 0), 1))
                row.append(run)
            out.append(row)
        if race:
            with nba_helmets.nba_colors():
                colors = team_line_colors.for_both([players[x[1]][3] for x in out[:5]])
            for row, c in zip(out[:5], colors):
                row.append(c)
        n_q = len(vals)
        stats.append({"key": key, "cat": cat, "name": name, "short": sh, "dec": dec, "line": line,
                      "col": [c for c, _f in LINES[line]].index(col), "count": n_q,
                      "qual": "Qualified: 70% of team games" + (" and the NBA's made-shot minimum" if qual in nba_stats.PCT_MINIMUMS else "")
                      if qual != "games" else "",
                      "race": race and through > 1, "rows": out})
    return {"through": through, "through_day": rows[-1]["date"], "players": players, "stats": stats,
            "lines": {k: [c for c, _f in v] for k, v in LINES.items()}, "cats": CATS,
            "icons": {c: render_page2players.PS_ICONS.get(CAT_ICONS[c], "") for c, _n in CATS},
            "pills": {t["abbr"]: nba_helmets.pill_html(t["abbr"], t["abbr"]) for t in nba_teams.TEAMS.values()}}


# The race charts' x axis: the NFL's labels every week ("Wk 1" ... "Wk 18"); an NBA season runs 25-odd
# weeks, so about six labels spread across it
LEADERS_JS = render_leaders.JS.replace(
    "for (var i = 0; i < n; i++) g += '<text class=\"ax\"",
    "for (var i = 0; i < n; i += Math.max(1, Math.ceil(n / 6))) g += '<text class=\"ax\"")
assert LEADERS_JS != render_leaders.JS


def render_leaders_page(data):
    season = data.get("season_label") or ""
    d = leaders_data(data)
    thru = f"Through {short_day(d['through_day'])}" if d.get("through_day") else "No games played yet"
    slots, dots = [], []
    for cat, name in CATS:
        stats = [s for s in d["stats"] if s["cat"] == cat]
        title = f'<span class="ttl"><span class="t-ic">{d["icons"].get(cat, "")}</span><span>{esc(name)}</span></span>'
        tabs = "".join(f'<button class="tab{" on" if j == 0 else ""}" type="button" data-i="{j}">{esc(s["short"])}</button>'
                       for j, s in enumerate(stats))
        panes = "".join(f'<section class="stat" data-stat="{s["key"]}" aria-label="{esc(s["name"])}"></section>' for s in stats)
        slots.append(f'<section class="slot" data-cat="{cat}"><div class="card">'
                     f'<div class="peek peek-top">{render_page1.DOWN}{title}</div>'
                     f'<div class="body"><div class="tabs" role="tablist">{tabs}</div><div class="strack">{panes}</div></div>'
                     f'<div class="peek peek-bot">{render_page1.UP}{title}</div></div></section>')
        dots.append(f'<button class="dot" type="button" aria-label="{esc(name)}">{d["icons"].get(cat, "")}</button>')
    bar = ("<nav class='bottombar' aria-label='Page controls'><div class='bar-in'>"
           + theme.menu_html("../", "nba-leaders") + back_link(data)
           + f'<button class="toggle" type="button" aria-label="Switch to condensed view"><span class="i-plus">{render_page1.PLUS}</span>'
           + f'<span class="i-minus">{render_page1.MINUS}</span></button></div></nav>')
    blob = json.dumps(d, separators=(",", ":")).replace("</", "<\\/")
    return (head(f"{season} Stat Leaders · NBA · At A Glance", "Pro Basketball Stat Leaders")
            + f"<style>{theme.THEME_CSS}{theme.MENU_CSS}{render_leaders.CSS}</style></head><body data-view='expanded'>"
            f"<header class='top'><span class='yr abbr'>{esc(season)}</span><span class='rs-line'><span class='rs'>Stat Leaders</span>"
            f"<span class='thru'>{esc(thru)}</span></span></header>"
            f"<main class='deck'>{''.join(slots)}</main>"
            "<section class='cview' aria-label='Every stat, condensed'></section>"
            f"<nav class='ic-dots' aria-label='Categories'>{''.join(dots)}</nav>{bar}"
            f"<script type='application/json' id='data'>{blob}</script>"
            f"<script>{theme.THEME_JS}</script><script>{LEADERS_JS}</script></body></html>")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=DATA_PATH)
    ap.add_argument("--out", default=SITE_DIR)
    args = ap.parse_args()
    with open(args.data, encoding="utf-8") as f:
        data = json.load(f)
    os.makedirs(args.out, exist_ok=True)
    # the site's icons live at its root (args.out's parent), where every page's links point; written here
    # too so the NBA pages have them even if the NFL build failed
    logo.write_icons(os.path.dirname(os.path.abspath(args.out)))
    nba_balls.write_all(os.path.join(args.out, "balls"))
    warnings = []
    with open(os.path.join(args.out, "index.html"), "w", encoding="utf-8") as f:
        f.write(render_page0(data))
    pages = render_nba_game.write_all(data, args.out, warnings)
    for name, render in (("standings.html", render_standings_page), ("leaders.html", render_leaders_page)):
        try:   # a problem here never costs the section its other pages
            with open(os.path.join(args.out, name), "w", encoding="utf-8") as f:
                f.write(render(data))
        except Exception:
            warnings.append(f"{name}: {traceback.format_exc(limit=3)}")
    print(f"Wrote the NBA section to {args.out}: {len(data.get('days') or [])} days, {pages} game pages, standings, stat leaders")
    for w in (data.get("warnings") or []) + warnings:
        print(f"  - {w}")
    if warnings and not pages:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
