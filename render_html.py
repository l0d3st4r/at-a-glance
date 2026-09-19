"""
Renders the site from data/matchups.json (after build_data.py has run).

Outputs:
  site/index.html     -- Page 0: every week's games, with a week dropdown + swipe
  site/raw.html       -- the old v0 unstyled data dump, kept for debugging
  site/helmets/*.svg  -- team-colored helmets used by Page 0 and Page 1 (see helmets.py)
  site/game/*.html    -- Page 1: one matchup page per game (see render_page1.py)

Run with: python render_html.py

Page 0 design (revised 2026-09-16, layout modeled on Apple Sports' NFL
"Upcoming" tab, using Jason's helmets, no betting lines):
  - white background and black text (as in the Framer design)
  - "Week N" dropdown (native <select> under the hood) listing every week of
    the season plus Wild Card, Divisional Round, Conference Championships and
    Super Bowl; it sits in a bar pinned to the BOTTOM of the screen (2026-09-17)
  - regular-season weeks with teams on bye end with a "Teams on Bye" section
    (helmet over abbreviation); no section when nobody is on bye
  - finished games that went to overtime read "FINAL/OT"
  - all weeks are rendered into one page side by side: swipe left/right on a
    phone (or trackpad), use the dropdown, or the arrow keys to move between
    weeks; the URL updates to #week-5 / #week-SB so a week can be linked
  - playoff rounds show gray "TBD" placeholder tiles until nflverse has the
    real games (see PLAYOFF_PLACEHOLDER_DAYS)
  - finished games use a FINAL tile: "FINAL" in the middle, big Inter Black
    scores beside the helmets (loser's score faded, ties both full), and each
    team's record right under its score -- frozen at what it was right after
    that game (computed in build_data.py)
  - one centered column (max 600px wide); games grouped under day headers
    like "Thursday, Sep 17"; each game is its own outlined tile
  - each tile: away helmet + abbreviation | away record | kickoff time
    ("1:00 PM" + small "ET") with TV network under it ("TV TBD" until we
    have a source) | home record | home helmet (mirrored) + abbreviation
  - tiles scale up slightly with a brighter outline on hover/keyboard focus,
    so they read as clickable
  - fonts match the Framer design exactly: Inter Regular 400 / Bold 700 at
    11px, 16px and 20px only
  - a +/- toggle sits at the right of the bottom bar (2026-09-17), in the same
    spot and at the same size as Page 1's. Condensed shows "+" (tap to expand),
    expanded shows "-" (tap to condense). Page 0 opens expanded every time,
    the same way Page 1 does.
  - CONDENSED VIEW (body[data-view=condensed]): the whole week on one screen,
    nothing scrolls -- the same philosophy as Page 1's condensed view. The TV
    network line is cut, the abbreviation moves off the helmet and sits over
    the record, and the tiles share whatever height is left (flex:1 1 0), so a
    16-game week and a 1-game week both fill the screen exactly. Both
    placements of the abbreviation are in the markup (see render_stack) and
    CSS shows one of them; the Page 1 flight picks whichever is on screen.

Defensive on purpose (same reasoning as the 2026-09-16 KeyError fix):
every field is read with .get(), and each matchup is rendered inside
try/except so one bad matchup shows an inline error instead of crashing
the whole page.
"""

import html
import json
import os
import traceback
from datetime import date

import helmets
import render_page1
from divisions import DIVISIONS

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(ROOT, "data", "matchups.json")
SITE_DIR = os.path.join(ROOT, "site")
INDEX_PATH = os.path.join(SITE_DIR, "index.html")
RAW_PATH = os.path.join(SITE_DIR, "raw.html")
HELMET_DIR = os.path.join(SITE_DIR, "helmets")

WEEKDAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


def esc(value):
    return html.escape(str(value), quote=True)


# ---------------------------------------------------------------- formatting

TEAM_NAMES = {
    "ARI": "Cardinals", "ATL": "Falcons", "BAL": "Ravens", "BUF": "Bills",
    "CAR": "Panthers", "CHI": "Bears", "CIN": "Bengals", "CLE": "Browns",
    "DAL": "Cowboys", "DEN": "Broncos", "DET": "Lions", "GB": "Packers",
    "HOU": "Texans", "IND": "Colts", "JAX": "Jaguars", "KC": "Chiefs",
    "LAC": "Chargers", "LAR": "Rams", "LV": "Raiders", "MIA": "Dolphins",
    "MIN": "Vikings", "NE": "Patriots", "NO": "Saints", "NYG": "Giants",
    "NYJ": "Jets", "PHI": "Eagles", "PIT": "Steelers", "SEA": "Seahawks",
    "SF": "49ers", "TB": "Buccaneers", "TEN": "Titans", "WAS": "Commanders",
}

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def parse_gameday(gameday):
    try:
        return date.fromisoformat(str(gameday)[:10])
    except (TypeError, ValueError):
        return None


def format_day_header(d):
    """date -> "Thursday, Sep 17". None -> "Date TBD"."""
    if d is None:
        return "Date TBD"
    return f"{DAY_NAMES[d.weekday()]}, {MONTHS[d.month - 1]} {d.day}"


def format_time(gametime):
    """nflverse gametime "HH:MM" (24h, US Eastern) -> "1:00 PM ET". Missing -> "TBD"."""
    try:
        hh, mm = (int(x) for x in str(gametime).split(":")[:2])
    except (TypeError, ValueError):
        return "TBD"
    suffix = "AM" if hh < 12 else "PM"
    return f"{hh % 12 or 12}:{mm:02d} {suffix} ET"


def format_network(networks):
    """
    Placeholder until a TV network source exists. build_data.py currently
    sends {"status": "pending"}; once a real source is wired up, send a
    string (e.g. "CBS") or a list of strings and it will show here.
    """
    if isinstance(networks, str) and networks.strip():
        return networks.strip()
    if isinstance(networks, list) and networks:
        return " / ".join(str(n) for n in networks)
    return "TV TBD"


# Winner arrow on a finished tile (Jason, 2026-09-18): a small black triangle between the
# score and the word FINAL, pointing at the team that won. Ties get none.
WIN_TRI = ('<svg viewBox="0 0 8 10" aria-hidden="true"><path d="M8 0 0 5l8 5z" fill="currentColor"/></svg>')


def format_record(record):
    record = record or {}
    w, l, t = record.get("wins", 0), record.get("losses", 0), record.get("ties", 0)
    return f"{w}-{l}-{t}" if t else f"{w}-{l}"


# ---------------------------------------------------------------- page 0

PAGE0_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#fff;
  --tile:#fff; --tile-border:rgba(0,0,0,.12);
  --tile-hover:rgba(0,0,0,.03); --tile-border-hover:rgba(0,0,0,.28);
  --text:#000; --text-2:rgba(0,0,0,.62); --text-3:rgba(0,0,0,.4);
}
html{background:var(--bg)}
/* Type follows the Framer design: Inter only, Regular 400 / Bold 700,
   sizes 11px (date/time labels), 16px (week label, records), 20px (team abbreviations),
   plus Inter Black 900 for the big final scores (the Framer type spec's "big numbers" weight). */
body{min-height:100vh;color:var(--text);font-family:Inter,system-ui,-apple-system,sans-serif;font-weight:400;
  -webkit-font-smoothing:antialiased;background:var(--bg)}
/* Week picker lives in a bar pinned to the bottom of the screen (Page 1 puts its "‹ Week N" back
   button and +/− toggle in the same spot, same size). --bbar = bar height incl. the iPhone home-indicator area. */
:root{--bbar:calc(52px + env(safe-area-inset-bottom))}
.bottombar{position:fixed;left:0;right:0;bottom:0;z-index:10;height:var(--bbar);padding-bottom:env(safe-area-inset-bottom);
  background:rgba(255,255,255,.94);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px)}
/* Same inner column as Page 1's .bbar-in, so the week pill and the +/- toggle sit in the same
   spot on both pages. */
.bar-in{position:relative;max-width:600px;height:52px;margin:0 auto;display:flex;align-items:flex-start;justify-content:center;padding-top:10px}
/* +/- toggle (2026-09-17): no circle and no hover fill -- hovering or pressing only enlarges it.
   Condensed shows "+" (tap to expand); expanded shows "-" (tap to condense), same as Page 1. */
.toggle{position:absolute;right:16px;top:9px;width:34px;height:34px;border:0;background:none;color:#000;padding:0;
  display:flex;align-items:center;justify-content:center;cursor:pointer;-webkit-tap-highlight-color:transparent;
  transition:transform .2s cubic-bezier(.22,1,.36,1)}
.toggle:hover{transform:scale(1.18)}
.toggle:active{transform:scale(1.30)}
.toggle:focus-visible{outline:2px solid #000;outline-offset:2px;border-radius:50%}
.toggle .i-plus{display:none}
.toggle .i-minus{display:block}
[data-view=condensed] .toggle .i-minus{display:none}
[data-view=condensed] .toggle .i-plus{display:block}
.week-picker{position:relative;display:inline-flex;align-items:center;gap:6px;padding:6px 12px;border-radius:999px;
  font-size:16px;font-weight:400;line-height:19px;cursor:pointer;transition:background-color .16s ease}
.week-picker:hover{background:rgba(0,0,0,.05)}
.week-picker:focus-within{outline:2px solid #000;outline-offset:2px}
.chevron{width:12px;height:12px;flex:none}
/* The real <select> sits invisibly on top, so phones get their native week picker. */
.week-picker select{position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:pointer;
  font-size:16px;-webkit-appearance:none;appearance:none;border:0}
/* Weeks sit side by side; swipe (or the dropdown) snaps between them. */
.track{display:flex;align-items:flex-start;overflow-x:auto;overflow-y:hidden;scroll-snap-type:x mandatory;
  overscroll-behavior-x:contain;scrollbar-width:none;-webkit-overflow-scrolling:touch}
.track::-webkit-scrollbar{display:none}
.week-panel{flex:0 0 100%;min-width:0;scroll-snap-align:start;scroll-snap-stop:always}
.week-inner{max-width:600px;margin:0 auto;padding:max(6px,env(safe-area-inset-top)) 16px calc(64px + var(--bbar))}
.day{text-align:center;font-size:16px;font-weight:400;line-height:19px;padding:18px 0 12px}
.games{list-style:none;display:flex;flex-direction:column;gap:10px}
.game{display:grid;grid-template-columns:84px 1fr minmax(96px,auto) 1fr 84px;align-items:center;
  padding:16px 8px;color:inherit;text-decoration:none;
  background:var(--tile);border:1px solid var(--tile-border);border-radius:20px;
  transition:transform .16s ease,background-color .16s ease,border-color .16s ease}
/* (2026-09-17, Jason) hover/press scales the tile and brightens its outline -- no fill */
.game:hover,.game:focus-visible{transform:scale(1.03);border-color:var(--tile-border-hover)}
.game:focus-visible{outline:2px solid #000;outline-offset:2px}
.game.placeholder{color:var(--text-2)}
.game.placeholder:hover{transform:none;border-color:var(--tile-border)}
/* no prefers-reduced-motion override: motion always plays (Jason, 2026-09-17) */
.team{display:flex;flex-direction:column;align-items:center;gap:4px;min-width:0}
.team img{width:48px;height:48px;display:block}
/* Team abbreviations: Saira italic, width 95, weight 800, 20 tracking (Jason, 2026-09-18).
   Everything else on the page stays Inter -- records, kickoff times, the week picker, day headers. */
.abbr{font-size:20px;line-height:24px;font-family:Saira,Inter,system-ui,sans-serif;font-weight:800;
  font-style:italic;font-variation-settings:'wdth' 95;letter-spacing:.02em}
.stack{display:flex;flex-direction:column;align-items:center;min-width:0}
.abbr-c{display:none}   /* the condensed view's copy of the abbreviation, over the record */
.record{font-size:16px;font-weight:400;line-height:19px;color:var(--text-2);text-align:center}  /* vertically centered in the tile */
.center{display:flex;flex-direction:column;align-items:center;gap:4px;padding:0 8px}
.time{font-size:20px;font-weight:700;line-height:24px;white-space:nowrap;margin-top:-6px}
.tz{font-size:11px;font-weight:400;margin-left:3px;color:var(--text-2)}
.network{font-size:11px;font-weight:400;line-height:13px;color:var(--text-3);white-space:nowrap}
/* Finished games */
.result{display:flex;flex-direction:column;align-items:center;gap:4px}
.team-record{font-size:16px;font-weight:400;line-height:19px;color:var(--text-2)}
/* Final scores: Teko (Jason, 2026-09-18). Records and kickoff times deliberately stay Inter. */
.score{font-size:60px;line-height:1;text-align:center;font-variant-numeric:tabular-nums;letter-spacing:-.02em;
  font-family:Teko,Inter,system-ui,sans-serif;font-weight:700}
.score.lose{opacity:.3}
.final-label{font-size:16px;font-weight:700;line-height:19px;letter-spacing:.04em;white-space:nowrap}
/* Winner arrow: a slot sits on each side of FINAL and only the winner's shows, so the word stays
   centred in the tile whoever won. A tie shows neither. */
.final-row{display:flex;align-items:center;justify-content:center;gap:5px}
.tri{display:flex;visibility:hidden;color:#000;flex:none}
.tri svg{display:block;width:8px;height:10px}
.tri-h svg{transform:scaleX(-1)}
.game.final[data-win=away] .tri-a,.game.final[data-win=home] .tri-h{visibility:visible}
.game.final .center{min-width:100px}  /* same width for FINAL and FINAL/OT, so scores line up tile to tile */
@media (max-width:420px){
  .game{grid-template-columns:72px 1fr auto 1fr 72px;padding:14px 4px}
  .team img{width:42px;height:42px}
  .center{padding:0 4px}
  .score{font-size:42px}.final-label{font-size:11px;line-height:13px}
  .final-row{gap:4px}.tri svg{width:6px;height:8px}
  .game.final .center{min-width:68px}
}
/* Teams on bye: one outlined (not clickable) card under the week's last day */
.bye-list{list-style:none;display:flex;flex-wrap:wrap;justify-content:center;gap:14px 18px;padding:16px 12px;
  background:var(--tile);border:1px solid var(--tile-border);border-radius:20px}
.bye-team{display:flex;flex-direction:column;align-items:center;gap:4px;width:56px}
.bye-team img{width:48px;height:48px;display:block}
@media (max-width:420px){.bye-list{display:grid;grid-template-columns:repeat(var(--bye-cols),56px);justify-content:center;gap:12px 14px;padding:14px 8px}
  .bye-team img{width:42px;height:42px}}
/* ===== Condensed view (2026-09-17) -- the whole week on one screen =====
   Same philosophy as Page 1's condensed view: nothing scrolls. The coverage line is cut, the
   abbreviation moves off the helmet and sits over the record, and the tiles share whatever
   height is left over (flex:1 1 0), so a 16-game week and a 1-game week both fill the screen. */
body[data-view=condensed]{height:100dvh;overflow:hidden}
[data-view=condensed] .track{height:100dvh}
[data-view=condensed] .week-panel{height:100dvh}
[data-view=condensed] .week-inner{height:100dvh;display:flex;flex-direction:column;gap:4px;
  padding:max(6px,env(safe-area-inset-top)) 12px calc(6px + var(--bbar))}
/* day sections and their lists fall away, so every tile is a flex child of the week column
   and they all share the leftover height evenly */
[data-view=condensed] .week-inner>section,[data-view=condensed] .games{display:contents}
[data-view=condensed] .games>li{flex:1 1 0;min-height:0;display:flex}
[data-view=condensed] .day{font-size:11px;line-height:13px;padding:5px 0 2px;color:var(--text-2);flex:none}
[data-view=condensed] .game{flex:1;min-height:0;border-radius:12px;padding:2px 6px;
  grid-template-columns:34px 1fr minmax(60px,auto) 1fr 34px}
[data-view=condensed] .game:hover,[data-view=condensed] .game:focus-visible{transform:scale(1.02)}
[data-view=condensed] .team img{width:30px;height:30px}
/* A helmet can never be taller than the tile holding it. The tile is its own size container,
   so when a long week squeezes the tiles the helmets scale down with them instead of poking
   out of the rounded edges. The fixed 30px above stays as the fallback. */
[data-view=condensed] .game{container-type:size}
[data-view=condensed] .team img{width:auto;height:min(30px,80cqh)}
[data-view=condensed] .team{overflow:hidden}
[data-view=condensed] .team .abbr{display:none}
[data-view=condensed] .abbr-c{display:block}
/* (2026-09-17, Jason) the abbreviation sits on the same line as the helmet and the record,
   packed against its own helmet, and a size up from the record */
[data-view=condensed] .stack,[data-view=condensed] .result{min-width:0}
[data-view=condensed] .stack{flex-direction:row;align-items:center;gap:8px}
[data-view=condensed] .stack.away{justify-content:flex-start;padding-left:6px}
[data-view=condensed] .stack.home{flex-direction:row-reverse;justify-content:flex-start;padding-right:6px}
[data-view=condensed] .abbr{font-size:16px;line-height:19px}
/* a fixed width for the abbreviation keeps it flush to its helmet while the records still
   line up tile to tile, whether the abbreviation is 2 or 3 letters (GB vs WAS) */
[data-view=condensed] .abbr-c{min-width:2.7em}
[data-view=condensed] .stack.away .abbr-c{text-align:left}
[data-view=condensed] .stack.home .abbr-c{text-align:right}
[data-view=condensed] .result.away .abbr-c{text-align:left}
[data-view=condensed] .result.home .abbr-c{text-align:right}
[data-view=condensed] .record{font-size:11px;line-height:13px;white-space:nowrap}
[data-view=condensed] .team-record{white-space:nowrap}
[data-view=condensed] .time{font-size:13px;line-height:15px;margin-top:0}
[data-view=condensed] .tz{font-size:8px;margin-left:2px}
[data-view=condensed] .network{display:none}          /* coverage is cut */
[data-view=condensed] .center{gap:0;padding:0 4px}
[data-view=condensed] .score{font-size:22px}
[data-view=condensed] .team-record{font-size:10px;line-height:11px}
[data-view=condensed] .final-label{font-size:9px;line-height:11px}
[data-view=condensed] .final-row{gap:4px}
[data-view=condensed] .tri svg{width:6px;height:8px}
[data-view=condensed] .game.final .center{min-width:60px}
/* narrow phones: a finished tile carries abbreviation + record + score per side, so it gets
   its own sizes rather than wrapping the record onto two lines */
@media (max-width:400px){
  [data-view=condensed] .game.final .center{min-width:48px}
  [data-view=condensed] .result{gap:5px}
  [data-view=condensed] .result .abbr-c{min-width:2.5em;font-size:15px}
  [data-view=condensed] .result .team-record{font-size:10px}
  [data-view=condensed] .score{font-size:20px}
  [data-view=condensed] .final-row{gap:3px}
  [data-view=condensed] .tri svg{width:5px;height:7px}
}
/* very narrow phones (iPhone SE 1st gen and similar): a finished tile still has to hold
   abbreviation + record + score on each side without pushing the helmets past the edge */
@media (max-width:344px){
  [data-view=condensed] .game{grid-template-columns:30px 1fr minmax(40px,auto) 1fr 30px;padding:2px 4px}
  [data-view=condensed] .game.final .center{min-width:40px}
  [data-view=condensed] .result{gap:4px}
  [data-view=condensed] .result .abbr-c{min-width:2.3em;font-size:13px}
  [data-view=condensed] .result .team-record{font-size:9px}
  [data-view=condensed] .score{font-size:17px}
  [data-view=condensed] .final-row{gap:2px}
  [data-view=condensed] .tri svg{width:4px;height:6px}
  [data-view=condensed] .stack{gap:6px;padding-left:4px;padding-right:4px}
  [data-view=condensed] .abbr{font-size:14px}
}
/* finished tiles: abbreviation over record, with the score on the inside next to FINAL */
[data-view=condensed] .result{flex-direction:row;align-items:center;gap:7px}
[data-view=condensed] .result.away{justify-content:flex-start;padding-left:6px}
[data-view=condensed] .result.home{flex-direction:row-reverse;justify-content:flex-start;padding-right:6px}
[data-view=condensed] .result .abbr-c{order:1}
[data-view=condensed] .result .team-record{order:2}
[data-view=condensed] .result .score{order:3}
/* teams on bye: one compact row that keeps its own height */
[data-view=condensed] .byes{display:contents}
[data-view=condensed] .bye-list{display:flex;flex-wrap:wrap;justify-content:center;gap:4px 10px;padding:6px 8px;border-radius:12px;flex:none}
[data-view=condensed] .bye-team{width:38px;gap:1px}
[data-view=condensed] .bye-team img{width:24px;height:24px}
[data-view=condensed] .bye-team .abbr{display:block;font-size:9px;line-height:11px}
@media (min-width:601px){
  [data-view=condensed] .game{padding:4px 10px;border-radius:14px;grid-template-columns:44px 1fr minmax(76px,auto) 1fr 44px}
  [data-view=condensed] .team img{width:38px;height:38px}
  [data-view=condensed] .team img{width:auto;height:min(38px,80cqh)}
  [data-view=condensed] .abbr{font-size:19px;line-height:23px}
  [data-view=condensed] .record,[data-view=condensed] .team-record{font-size:12px;line-height:14px}
  [data-view=condensed] .stack{gap:10px}
  [data-view=condensed] .result{gap:9px}
  [data-view=condensed] .time{font-size:15px;line-height:18px}
  [data-view=condensed] .score{font-size:26px}
  [data-view=condensed] .final-label{font-size:11px;line-height:13px}
  [data-view=condensed] .day{font-size:12px;line-height:14px;padding:7px 0 3px}
  [data-view=condensed] .bye-team img{width:30px;height:30px}
}
.error{background:#fee;color:#000;padding:8px;font-size:11px;white-space:pre-wrap;border-radius:8px}
.empty{text-align:center;padding:40px 0;color:var(--text-2);font-size:16px}
/* Page 1 opens on top of Page 0 (see PAGE1_OVERLAY_JS): tapping a tile zooms into it, its helmets,
   abbreviations and scores fly up into Page 1's top bar, then Page 1's cards come in. Page 1's own
   styles live inside a shadow root on .p1-host. Swipe sideways for the week's other games; swipe
   down from the top, or pinch in, to minimize back into the tile. */
.p1-overlay{position:fixed;z-index:100;box-sizing:border-box;background:var(--tile);
  border:1px solid var(--tile-border);border-radius:20px;overflow:hidden}
.p1-overlay.is-open{inset:0;border-radius:0;border-color:transparent;
  touch-action:pan-y}  /* sideways swipes, pull-down-to-close and two-finger pinches are handled by the script */
.p1-host{position:absolute;inset:0;overflow-x:hidden;overflow-y:auto;overscroll-behavior:contain;background:#fff}
.p1-shell{position:fixed;box-sizing:border-box;background:var(--tile);border:1px solid var(--tile-border);border-radius:20px;pointer-events:none}
html.p1-open{overflow:hidden}
"""


def time_html(time_text):
    """ "1:00 PM ET" -> "1:00 PM<span class=tz>ET</span>" so the timezone can be smaller."""
    if time_text.endswith(" ET"):
        return f'{esc(time_text[:-3])}<span class="tz">ET</span>'
    return esc(time_text)


def render_team(snapshot, mirrored):
    team = (snapshot or {}).get("team") or None
    src = "helmets/" + helmets.helmet_filename(team, mirrored=mirrored)
    return (
        '<div class="team">'
        f'<img src="{esc(src)}" alt="" width="48" height="48" loading="lazy">'
        f'<span class="abbr">{esc(team or "TBD")}</span>'
        "</div>"
    )


def render_stack(team, record, side):
    """
    The record column. The condensed view moves the abbreviation off the helmet and sets it
    on the same line as the helmet and the record, packed against its own helmet, so both
    placements are in the markup and CSS shows one of them: .team .abbr under the helmet
    (expanded), .abbr-c beside the record (condensed). `side` is "away" or "home" -- it flips
    the row so each abbreviation sits next to its own helmet.
    """
    return (
        f'<span class="stack {side}">'
        f'<span class="abbr abbr-c" aria-hidden="true">{esc(team or "TBD")}</span>'
        f'<span class="record">{esc(record)}</span>'
        "</span>"
    )


def render_game(m):
    away, home = m.get("away") or {}, m.get("home") or {}
    if m.get("placeholder"):
        # Playoff game whose teams aren't known yet: gray helmets, not clickable.
        return (
            '<div class="game placeholder" aria-label="Matchup to be determined">'
            f"{render_team(None, mirrored=False)}"
            f"{render_stack(None, '', 'away')}"
            '<div class="center"><span class="time">TBD</span>'
            f'<span class="network">{esc(format_network(None))}</span></div>'
            f"{render_stack(None, '', 'home')}"
            f"{render_team(None, mirrored=True)}"
            "</div>"
        )
    if m.get("final"):
        return render_final_game(m)
    time_text = format_time(m.get("gametime"))
    network = format_network(m.get("networks"))
    away_name = TEAM_NAMES.get(away.get("team"), away.get("team", "?"))
    home_name = TEAM_NAMES.get(home.get("team"), home.get("team", "?"))
    label = f"{away_name} at {home_name}, {time_text}"
    # "#game-<id>" opens Page 1 (PAGE1_OVERLAY_JS); the week switcher ignores these hashes.
    return (
        f'<a class="game" href="#game-{esc(m.get("game_id") or "")}" aria-label="{esc(label)}">'
        f"{render_team(away, mirrored=False)}"
        f"{render_stack(away.get('team'), format_record(away.get('record')), 'away')}"
        '<div class="center">'
        f'<span class="time">{time_html(time_text)}</span>'
        f'<span class="network">{esc(network)}</span>'
        "</div>"
        f"{render_stack(home.get('team'), format_record(home.get('record')), 'home')}"
        f"{render_team(home, mirrored=True)}"
        "</a>"
    )


def _score_text(score):
    try:
        return str(int(score))
    except (TypeError, ValueError):
        return "–"


def render_final_game(m):
    """
    Finished game: "FINAL" replaces the kickoff time, a big Inter Black score
    sits beside each helmet, and each team's record sits right under its score.
    Winner's score is full strength; loser's is faded; a tie shows both full.
    """
    away, home = m.get("away") or {}, m.get("home") or {}
    a_score, h_score = away.get("score"), home.get("score")
    a_cls = h_cls = "score"
    win = ""   # "away" | "home" | "" (tie, or no score yet)
    try:
        if float(a_score) > float(h_score):
            h_cls += " lose"
            win = "away"
        elif float(h_score) > float(a_score):
            a_cls += " lose"
            win = "home"
    except (TypeError, ValueError):
        pass

    def team_block(snapshot, mirrored):
        team = snapshot.get("team") or None
        src = "helmets/" + helmets.helmet_filename(team, mirrored=mirrored)
        return (
            '<div class="team">'
            f'<img src="{esc(src)}" alt="" width="48" height="48" loading="lazy">'
            f'<span class="abbr">{esc(team or "TBD")}</span>'
            "</div>"
        )

    away_name = TEAM_NAMES.get(away.get("team"), away.get("team", "?"))
    home_name = TEAM_NAMES.get(home.get("team"), home.get("team", "?"))
    final_text = "FINAL/OT" if m.get("overtime") else "FINAL"
    label = f"{'Final in overtime' if m.get('overtime') else 'Final'}: {away_name} {_score_text(a_score)}, {home_name} {_score_text(h_score)}"
    return (
        f'<a class="game final" data-win="{win}" href="#game-{esc(m.get("game_id") or "")}" aria-label="{esc(label)}">'
        f"{team_block(away, mirrored=False)}"
        '<div class="result away">'
        f'<span class="abbr abbr-c" aria-hidden="true">{esc(away.get("team") or "TBD")}</span>'
        f'<span class="{a_cls}">{esc(_score_text(a_score))}</span>'
        f'<span class="team-record">{esc(format_record(away.get("record")))}</span>'
        "</div>"
        '<div class="center"><span class="final-row">'
        f'<span class="tri tri-a">{WIN_TRI}</span>'
        f'<span class="final-label">{final_text}</span>'
        f'<span class="tri tri-h">{WIN_TRI}</span>'
        "</span></div>"
        '<div class="result home">'
        f'<span class="abbr abbr-c" aria-hidden="true">{esc(home.get("team") or "TBD")}</span>'
        f'<span class="{h_cls}">{esc(_score_text(h_score))}</span>'
        f'<span class="team-record">{esc(format_record(home.get("record")))}</span>'
        "</div>"
        f"{team_block(home, mirrored=True)}"
        "</a>"
    )


def group_by_day(matchups):
    """Sorted [(date_or_None, [matchups...]), ...] -- one group per calendar day, TBD dates last."""
    groups = {}
    for m in matchups:
        groups.setdefault(parse_gameday(m.get("gameday")), []).append(m)
    ordered = sorted(groups.items(), key=lambda kv: (kv[0] is None, kv[0] or date.max))
    return [(d, sorted(ms, key=lambda m: str(m.get("gametime") or "99:99"))) for d, ms in ordered]


# ---------------------------------------------------------------- weeks + playoff placeholders

PLAYOFF_GAME_COUNTS = {"WC": 6, "DIV": 4, "CON": 2, "SB": 1}

# Days used for placeholder tiles until nflverse publishes the real playoff
# games. Round dates are from the league schedule for the 2026 season
# (Wild Card Jan 16-18, Divisional Jan 23-24, Conference Jan 31, Super Bowl
# LXI Feb 14, 2027); the games-per-day split is the recent usual pattern, not
# an official announcement. Update for a new season, or placeholders show "Date TBD".
PLAYOFF_PLACEHOLDER_DAYS = {
    2026: {
        "WC": [("2027-01-16", 2), ("2027-01-17", 3), ("2027-01-18", 1)],
        "DIV": [("2027-01-23", 2), ("2027-01-24", 2)],
        "CON": [("2027-01-31", 2)],
        "SB": [("2027-02-14", 1)],
    },
}


def placeholder_games(code, season):
    days = PLAYOFF_PLACEHOLDER_DAYS.get(season, {}).get(code) or [(None, PLAYOFF_GAME_COUNTS.get(code, 1))]
    games = []
    for day, count in days:
        for _ in range(count):
            games.append({"placeholder": True, "gameday": day, "game_id": f"{code}-tbd-{len(games) + 1}"})
    return games


def bye_teams(games):
    """Regular-season week -> every team (divisions.py's 32) with no game that week, alphabetical."""
    playing = set()
    for m in games:
        for side in ("away", "home"):
            team = (m.get(side) or {}).get("team")
            if team:
                playing.add(team)
    return sorted(t for t in DIVISIONS if t not in playing)


def weeks_for_page0(data):
    """
    [(key, label, games, byes), ...] for every week in the dropdown, plus the
    key of the week to show first. byes = teams on bye (regular-season weeks
    only; empty list = no "Teams on Bye" section). Falls back to just the
    current week's matchups if build_data.py didn't produce season_weeks
    (older data file or a failed run).
    """
    season = data.get("season")
    weeks = []
    for w in data.get("season_weeks") or []:
        key, label = str(w.get("key")), w.get("label") or f"Week {w.get('key')}"
        games = w.get("games") or []
        byes = bye_teams(games) if w.get("game_type") == "REG" and games else []
        if not games and w.get("game_type") in PLAYOFF_GAME_COUNTS:
            games = placeholder_games(w["game_type"], season)
        weeks.append((key, label, games, byes))

    if not weeks:
        wk = data.get("week")
        weeks = [(str(wk), f"Week {wk}" if wk is not None else "This Week", data.get("matchups") or [], [])]

    keys = [w[0] for w in weeks]
    current = data.get("current_week_key")
    if current is None and data.get("week") is not None:
        current = str(data.get("week"))
    if current not in keys:
        current = keys[0]
    return weeks, current


def render_byes(byes):
    """The "Teams on Bye" section under a week's last day: helmet over abbreviation for each team."""
    if not byes:
        return ""
    teams = "".join(
        '<li class="bye-team">'
        f'<img src="helmets/{esc(helmets.helmet_filename(t))}" alt="" width="48" height="48" loading="lazy">'
        f'<span class="abbr">{esc(t)}</span></li>'
        for t in byes
    )
    # On phones the helmets wrap in even rows (6 teams -> 3 + 3, not 5 + 1); bye counts are always even.
    phone_cols = len(byes) if len(byes) <= 4 else (len(byes) + 1) // 2
    return (f'<section class="byes" aria-label="Teams on bye"><h2 class="day">Teams on Bye</h2>'
            f'<ul class="bye-list" style="--bye-cols:{phone_cols}">{teams}</ul></section>')


def render_week_panel(key, label, games, is_current, byes=None):
    sections = []
    for d, day_games in group_by_day(games):
        rows = []
        for m in day_games:
            try:
                rows.append(f"<li>{render_game(m)}</li>")
            except Exception:
                rows.append(f'<li><div class="error">Failed to render one matchup\n{esc(traceback.format_exc())}</div></li>')
        sections.append(
            f'<section><h2 class="day">{esc(format_day_header(d))}</h2>'
            f'<ul class="games">{"".join(rows)}</ul></section>'
        )
    if not sections:
        sections.append('<p class="empty">No games this week.</p>')
    sections.append(render_byes(byes))
    return (
        f'<div class="week-panel" id="week-{esc(key)}" data-key="{esc(key)}" data-label="{esc(label)}"'
        f' data-current="{"true" if is_current else "false"}" role="group" aria-label="{esc(label)}">'
        f'<div class="week-inner">{"".join(sections)}</div></div>'
    )


PAGE0_JS = """
(function () {
  var track = document.getElementById('track');
  var select = document.getElementById('week-select');
  var label = document.getElementById('week-label');
  if (!track || !select) return;
  var panels = Array.prototype.slice.call(track.querySelectorAll('.week-panel'));
  var idx = Math.max(0, panels.findIndex(function (p) { return p.dataset.current === 'true'; }));

  function keyIndex(k) { return panels.findIndex(function (p) { return p.dataset.key === k; }); }
  function hashIndex() {
    var m = location.hash.match(/^#week-(.+)$/);
    return m ? keyIndex(decodeURIComponent(m[1])) : -1;
  }
  // Track height = tallest of the current week and its neighbours, so a short
  // week (e.g. the Super Bowl) doesn't leave a long blank page, and nothing is
  // cut off while swiping to the next week.
  function sizeTrack() {
    // The condensed view is exactly one screen tall, so the track sizes itself.
    if (document.body.dataset.view === 'condensed') { track.style.height = ''; return; }
    var h = 0;
    for (var i = idx - 1; i <= idx + 1; i++) if (panels[i]) h = Math.max(h, panels[i].offsetHeight);
    track.style.height = h + 'px';
  }
  function setActive(i, opts) {
    opts = opts || {};
    if (!panels[i]) return;
    idx = i;
    var p = panels[i];
    select.value = p.dataset.key;
    label.textContent = p.dataset.label;
    document.title = p.dataset.label + ' · At A Glance';
    if (opts.scroll) track.scrollTo({ left: i * track.clientWidth, behavior: opts.smooth ? 'smooth' : 'auto' });
    sizeTrack();
    if (opts.updateHash !== false && !document.documentElement.classList.contains('p1-open')) history.replaceState(null, '', '#week-' + encodeURIComponent(p.dataset.key));
  }

  select.addEventListener('change', function () {
    var i = keyIndex(select.value);
    if (i >= 0) setActive(i, { scroll: true, smooth: Math.abs(i - idx) === 1 });
  });

  var settle;
  track.addEventListener('scroll', function () {
    clearTimeout(settle);
    settle = setTimeout(function () {
      var i = Math.round(track.scrollLeft / track.clientWidth);
      if (i !== idx) setActive(i);
    }, 90);
  }, { passive: true });

  document.addEventListener('keydown', function (e) {
    if (e.target === select || e.altKey || e.metaKey || e.ctrlKey) return;
    if (document.documentElement.classList.contains('p1-open')) return;  // Page 1 has its own keys
    if (e.key === 'ArrowRight') setActive(idx + 1, { scroll: true, smooth: true });
    if (e.key === 'ArrowLeft') setActive(idx - 1, { scroll: true, smooth: true });
  });

  window.addEventListener('hashchange', function () {
    var i = hashIndex();
    if (i >= 0 && i !== idx) setActive(i, { scroll: true, updateHash: false });
  });
  window.addEventListener('resize', function () {
    track.scrollLeft = idx * track.clientWidth;
    sizeTrack();
  });
  if ('ResizeObserver' in window) new ResizeObserver(sizeTrack).observe(track);

  var fromHash = hashIndex();
  if (fromHash >= 0) idx = fromHash;
  track.scrollLeft = idx * track.clientWidth;
  setActive(idx, { updateHash: false });

  // +/- toggle: expanded (the scrolling week) <-> condensed (the whole week on one screen).
  // Page 0 opens expanded every time, the same way Page 1 opens expanded every time.
  var toggle = document.getElementById('view-toggle');
  if (toggle) {
    var setView = function (v) {
      document.body.dataset.view = v;
      toggle.setAttribute('aria-label', v === 'condensed' ? 'Switch to expanded view' : 'Switch to condensed view');
      toggle.setAttribute('aria-pressed', v === 'condensed' ? 'true' : 'false');
      if (v === 'condensed') window.scrollTo(0, 0);
      sizeTrack();
      track.scrollLeft = idx * track.clientWidth;
    };
    toggle.addEventListener('click', function () {
      setView(document.body.dataset.view === 'condensed' ? 'expanded' : 'condensed');
    });
    setView(document.body.dataset.view || 'expanded');
  }

  // Used by the Page 1 overlay: jump to the week a game belongs to, and the hash to return to.
  window.AAG_P0 = {
    showTile: function (tile) {
      var i = panels.indexOf(tile.closest('.week-panel'));
      if (i >= 0 && i !== idx) setActive(i, { scroll: true, updateHash: false });
    },
    weekHash: function () { return '#week-' + encodeURIComponent(panels[idx].dataset.key); }
  };
})();
"""

PAGE1_OVERLAY_JS = r"""
(function () {
  if (!window.fetch || !Element.prototype.attachShadow || !Element.prototype.animate || !window.AAG_P1) return;  // old browsers: plain links
  var docEl = document.documentElement, cache = {}, state = null;
  // Motion always plays, whatever the device's Reduce Motion setting (Jason, 2026-09-17).
  // Speed/easing taken from yeezy.com: 200-300ms moves on cubic-bezier(.22,1,.36,1), 150ms fades.
  var reduce = { matches: false };
  var EASE = 'cubic-bezier(.22,1,.36,1)';
  var TILE = 'a.game[href^="#game-"]';
  var PINCH_CLOSE = 0.8;     // let go of a pinch below 80% size and Page 1 closes
  var SWIPE_COMMIT = 0.22;   // drag a quarter of the screen (or flick) to change games
  var PULL_CLOSE = 0.16;     // pull down a sixth of the screen (or flick down) and Page 1 closes
  var PULL_FULL = 0.55;      // how far a pull has to go for the page to reach its smallest size
  var PULL_FLICK = 0.5;      // px/ms downward that counts as a flick (needs PULL_MIN travel too)
  var PULL_MIN = 70;         // a flick still has to move this far, so a nudge never closes the page
  var PULL_BOUNCE = 64;      // Safari rubber-bands the deck instead of firing a cancelable pull;
                             // this many px of overscroll at the top of the deck closes the page

  // ------------------------------------------------------------ helpers
  // "#game-<id>" is Page 1; "#game-<id>/game-info" is that game's Page 2 (2026-09-19)
  function idFromHash(h) { var m = (h || '').match(/^#game-([^\/]+)(?:\/.*)?$/); return m ? decodeURIComponent(m[1]) : null; }
  function detailFromHash(h) { return /\/game-info$/.test(h || ''); }
  function detailOn(s) { return !!(s && s.inst && s.inst.detail && s.inst.detail()); }
  function tileId(t) { return idFromHash(t.getAttribute('href')); }
  function tileFor(id) {
    var tiles = document.querySelectorAll(TILE);
    for (var i = 0; i < tiles.length; i++) if (tileId(tiles[i]) === id) return tiles[i];
    return null;
  }
  function neighborId(id, dir) {  // the next/previous game in the same week, in Page 0's order
    var t = tileFor(id), panel = t && t.closest('.week-panel');
    if (!panel) return null;
    var ids = [].map.call(panel.querySelectorAll(TILE), tileId), i = ids.indexOf(id);
    return i < 0 ? null : ids[i + dir] || null;
  }
  function pageUrl(id) { return 'game/' + encodeURIComponent(id) + '.html'; }
  function load(id) {
    if (!id) return Promise.reject(new Error('no game'));
    if (!cache[id]) {
      cache[id] = fetch(pageUrl(id)).then(function (r) { if (!r.ok) throw new Error(r.status); return r.text(); });
      cache[id].catch(function () { delete cache[id]; });
    }
    return cache[id];
  }
  function box(r) { return { left: r.left + 'px', top: r.top + 'px', width: r.width + 'px', height: r.height + 'px' }; }
  function screenRect() { return { left: 0, top: 0, width: innerWidth, height: innerHeight }; }
  function frame(r, radius, border) { return Object.assign({ borderRadius: radius, borderColor: border }, box(r)); }
  function visibleRect(el) {
    if (!el) return null;
    var r = el.getBoundingClientRect();
    return (r.width && r.bottom > 0 && r.top < innerHeight && r.right > 0 && r.left < innerWidth) ? r : null;
  }
  function done(anim) { return anim ? anim.finished.catch(function () {}) : Promise.resolve(); }
  function all(list) { return [].slice.call(list); }

  // ------------------------------------------------------------ Page 1 content
  function mount(s, text, opts) {
    var page = new DOMParser().parseFromString(text, 'text/html');
    var css = page.getElementById('p1-css'), block = page.querySelector('.p1');
    if (!block) throw new Error('bad page');
    var host = document.createElement('div'), root = host.attachShadow({ mode: 'open' });
    host.className = 'p1-host';
    root.innerHTML = '<style>' + (css ? css.textContent : '') + '</style>' + block.outerHTML.replace(/(src|href)="\.\.\//g, '$1="');
    if (opts.view) root.querySelector('.p1').setAttribute('data-view', opts.view);
    if (opts.hidden) host.style.visibility = 'hidden';
    if (opts.dx) host.style.transform = 'translateX(' + opts.dx + 'px)';
    s.overlay.appendChild(host);
    var m = { host: host, root: root, title: page.title };
    if (opts.preview) {  // a neighbour shown while swiping: same card as the current game, no listeners yet
      var slots = root.querySelectorAll('.view-l > .slot'), i = Math.max(0, Math.min(slots.length - 1, opts.card || 0));
      if (slots[i]) slots[i].classList.add('active');
      if (slots[i - 1]) slots[i - 1].classList.add('above');
      if (slots[i + 1]) slots[i + 1].classList.add('below');
      root.querySelector('.p1').setAttribute('data-head', i === 0 ? 'card' : 'bar');
      var deck = root.querySelector('.view-l');
      if (deck && slots[i] && opts.view !== 'condensed') deck.scrollTop = slots[i].offsetTop - (deck.clientHeight - slots[i].offsetHeight) / 2;
    } else {
      m.inst = window.AAG_P1.init(root, { onBack: requestClose, view: opts.view, card: opts.card, detail: !!opts.detail });
      if (m.title) document.title = m.title;
    }
    return m;
  }

  // touch-action on the overlay follows the view: the script owns vertical gestures in the
  // condensed view (nothing there scrolls), and the browser keeps them in the expanded one,
  // whose deck scrolls natively. Without this, Safari treats a downward drag as a pan it owns
  // and our touchmove is never cancelable -- the pull just doesn't happen.
  function syncTouchAction(s) {
    if (!s || !s.overlay || !s.root) return;
    var p1 = s.root.querySelector('.p1');
    s.overlay.style.touchAction = p1 && p1.getAttribute('data-view') === 'large' ? '' : 'none';   // Page 2 follows the same views
  }

  // Wire the pull-to-close helpers onto whichever page is currently mounted: called on open and
  // again after swiping to another game.
  function armPull(s) {
    if (!s || !s.root) return;
    if (s.viewWatch) { s.viewWatch.disconnect(); s.viewWatch = null; }
    syncTouchAction(s);
    var p1 = s.root.querySelector('.p1');
    if (p1 && window.MutationObserver) {   // the +/- toggle lives inside the shadow root
      s.viewWatch = new MutationObserver(function () { syncTouchAction(s); });
      s.viewWatch.observe(p1, { attributes: true, attributeFilter: ['data-view', 'data-detail'] });
    }
    // Safari answers a downward drag at the top of the deck by rubber-banding it, which makes our
    // touchmove non-cancelable. That overscroll shows up as a negative scrollTop, so a deep enough
    // bounce counts as the same gesture. Chrome doesn't overscroll inner scrollers, so there the
    // touch handler below is what runs.
    var dk = s.root.querySelector('.view-l');
    if (dk) dk.addEventListener('scroll', function () {
      if (state !== s || s.closing || !s.touching || dk.scrollTop > -PULL_BOUNCE || detailOn(s)) return;
      s.pinchScale = 1;
      s.pinchRect = s.host.getBoundingClientRect();
      requestClose();
    }, { passive: true });
    // same Safari bounce on Page 2's deck: closes Page 2 back into its card (not Page 1)
    var p2 = s.root.querySelector('.p2-l');
    if (p2) p2.addEventListener('scroll', function () {
      if (state !== s || s.closing || !s.touching || p2.scrollTop > -PULL_BOUNCE || !detailOn(s)) return;
      s.inst.closeDetail();
    }, { passive: true });
  }
  function tileParts(tile) {  // pieces of a Page 0 tile that travel to Page 1's top bar
    var out = {}, teams = tile.querySelectorAll('.team'), scores = tile.querySelectorAll('.score');
    // The abbreviation sits under the helmet in the expanded view and over the record in the
    // condensed one; both are in the markup, so fly whichever copy is actually on screen.
    var abbrs = all(tile.querySelectorAll('.abbr')).filter(function (e) { return e.offsetWidth; });
    [0, 1].forEach(function (i) {
      var t = teams[i];
      if (t && t.querySelector('img')) out['img' + i] = t.querySelector('img');
      if (abbrs[i]) out['abbr' + i] = abbrs[i];
      if (scores[i]) out['score' + i] = scores[i];
    });
    return out;
  }
  function headerRow(root) {  // the copy of Page 1's header row on screen: in the Game Info card, moving, or in the top bar
    var p1 = root.querySelector('.p1'), mode = p1 && p1.getAttribute('data-view') === 'large' ? p1.getAttribute('data-head') : 'bar';
    return root.querySelector(mode === 'card' ? '.hero .teams' : mode === 'moving' ? '.head-fly' : '.bar .teams');
  }
  function headerParts(root) {
    var out = {}, row = headerRow(root);
    if (!row) return out;
    all(row.querySelectorAll('img')).forEach(function (e, i) { out['img' + i] = e; });
    all(row.querySelectorAll('.abbr')).forEach(function (e, i) { out['abbr' + i] = e; });
    all(row.querySelectorAll('.hscore')).forEach(function (e, i) { out['score' + i] = e; });
    return out;
  }
  function drawnScale(el) {  // how much transforms enlarge/shrink an element on screen
    var w = el.offsetWidth;
    return w ? el.getBoundingClientRect().width / w : 1;
  }
  function flyer(src) {  // a free-floating copy of an element, sitting exactly on top of it
    var r = src.getBoundingClientRect(), cs = getComputedStyle(src), c = src.cloneNode(true);
    c.removeAttribute('class');
    Object.assign(c.style, {
      position: 'fixed', left: r.left + 'px', top: r.top + 'px', width: r.width + 'px', height: r.height + 'px',
      margin: '0', padding: '0', boxSizing: 'border-box', zIndex: '120', pointerEvents: 'none', transformOrigin: '0 0',
      display: 'block', textAlign: 'center', whiteSpace: 'nowrap', lineHeight: r.height + 'px',
      fontFamily: cs.fontFamily, fontSize: (parseFloat(cs.fontSize) * drawnScale(src)) + 'px', fontWeight: cs.fontWeight, letterSpacing: cs.letterSpacing,
      fontVariantNumeric: cs.fontVariantNumeric, color: cs.color, opacity: cs.opacity
    });
    document.body.appendChild(c);
    return { el: c, r: r, fs: (parseFloat(cs.fontSize) * drawnScale(src)) || 1, img: src.tagName === 'IMG' };
  }
  function flyTo(f, target, duration, delay) {
    var t = target.getBoundingClientRect();
    var sc = f.img ? t.width / f.r.width : ((parseFloat(getComputedStyle(target).fontSize) * drawnScale(target)) || f.fs) / f.fs;
    var dx = (t.left + t.width / 2) - (f.r.left + f.r.width * sc / 2);
    var dy = (t.top + t.height / 2) - (f.r.top + f.r.height * sc / 2);
    return f.el.animate([{ transform: 'none' }, { transform: 'translate(' + dx + 'px,' + dy + 'px) scale(' + sc + ')' }],
                        { duration: duration, delay: delay || 0, easing: EASE, fill: 'forwards' });
  }
  function reveal(m) {  // Page 1's cards come in after the header pieces land
    m.host.style.visibility = '';
    if (reduce.matches) return;
    all(m.root.querySelectorAll('.bbar .week, .bbar .toggle, .bar .at, .dots')).forEach(function (el) {
      el.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 150, delay: 40, easing: 'ease-out', fill: 'backwards' });
    });
    var large = m.root.querySelector('.p1').getAttribute('data-view') === 'large';
    // (large view: animate the cards, not their snap slots, so the deck's scroll-snap doesn't chase the motion)
    all(m.root.querySelectorAll(large ? '.view-l > .slot > a.card' : '.view-c > .card, .c-teams > .card')).forEach(function (el, i) {
      el.animate([{ opacity: 0, transform: 'translateY(56px) scale(.96)' }, { opacity: 1, transform: 'none' }],
                 { duration: 300, delay: 20 + i * 35, easing: EASE, fill: 'backwards' });
    });
  }

  // ------------------------------------------------------------ open: zoom into the tile
  function open(id, opts) {
    opts = opts || {};
    if (state || !id) return;
    var tile = tileFor(id), overlay = document.createElement('div');
    var start = opts.animate === false || reduce.matches ? null : visibleRect(tile);
    overlay.className = 'p1-overlay';
    Object.assign(overlay.style, box(start || screenRect()));
    document.body.appendChild(overlay);
    attachGestures(overlay);
    docEl.classList.add('p1-open');
    var s = state = { id: id, overlay: overlay, pushed: !!opts.push, title: document.title, scrollY: window.scrollY, extras: [] };
    if (opts.push) history.pushState({ p1: id }, '', '#game-' + encodeURIComponent(id));

    var grow, flyers = [];
    if (start) {
      // 1 · the tile's own content zooms up and fades while its card grows to fill the screen
      var ghost = tile.cloneNode(true), parts = tileParts(tile);
      ghost.removeAttribute('href');
      Object.assign(ghost.style, { position: 'fixed', left: start.left + 'px', top: start.top + 'px', width: start.width + 'px',
        height: start.height + 'px', margin: '0', zIndex: '110', pointerEvents: 'none', background: 'transparent',
        borderColor: 'transparent', transform: 'none', transition: 'none' });
      var gp = tileParts(ghost);
      Object.keys(gp).forEach(function (k) { gp[k].style.visibility = 'hidden'; });
      document.body.appendChild(ghost);
      s.extras.push(ghost);
      ghost.animate([{ transform: 'scale(1)', opacity: 1 }, { transform: 'scale(1.3)', opacity: 0 }],
                    { duration: 200, easing: EASE, fill: 'forwards' });
      Object.keys(parts).forEach(function (k) { var f = flyer(parts[k]); f.key = k; flyers.push(f); s.extras.push(f.el); });
      grow = overlay.animate([frame(start, '20px', 'rgba(0,0,0,.12)'), frame(screenRect(), '0px', 'rgba(0,0,0,0)')],
                             { duration: 300, easing: EASE, fill: 'forwards' });
    } else {
      grow = overlay.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 150, fill: 'forwards' });
    }

    load(id).then(function (text) {
      if (state !== s || s.closing) throw 0;
      var m = mount(s, text, { hidden: true, detail: opts.detail });
      s.host = m.host; s.root = m.root; s.inst = m.inst;
      armPull(s);
      // 2 · helmets, abbreviations (and final scores) fly from the tile up into Page 1's top bar
      var targets = headerParts(m.root);
      s.landInCard = !!(targets.img0 && targets.img0.closest('.hero'));
      var landed = flyers.map(function (f) {
        return targets[f.key] ? done(flyTo(f, targets[f.key], 320))
                              : done(f.el.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 150, fill: 'forwards' }));
      });
      return Promise.all([done(grow)].concat(landed)).then(function () { return m; });
    }).then(function (m) {
      if (state !== s || s.closing) return;
      overlay.style.cssText = '';
      overlay.classList.add('is-open');
      overlay.getAnimations().forEach(function (a) { a.cancel(); });
      reveal(m);  // 3 · cards come in
      var extras = s.extras, row = s.landInCard && headerRow(m.root);
      function clearExtras() { extras.forEach(function (el) { el.remove(); }); if (s.extras === extras) s.extras = []; }
      if (row && extras.length) {
        // the pieces landed in the middle of the Game Info card: hold them there while the card comes in around them
        row.style.visibility = 'hidden';
        var card = row.closest('a.card'), coming = card && card.getAnimations ? card.getAnimations() : [];
        Promise.all(coming.map(done)).then(function () {
          row.style.visibility = '';
          clearExtras();
          var mid = row.querySelector('.mid');   // the "@" has nothing to fly from, so it just fades in
          if (mid && !reduce.matches) mid.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 150, easing: 'ease-out' });
        });
      } else clearExtras();
      load(neighborId(id, 1)).catch(function () {});
      load(neighborId(id, -1)).catch(function () {});
    }).catch(function (e) {
      s.extras.forEach(function (el) { el.remove(); });
      if (e !== 0 && state === s && !s.closing) location.href = pageUrl(id);
    });
  }

  // ------------------------------------------------------------ close: minimize back into the tile
  function requestClose() {
    if (!state) return;
    if (state.pushed && history.state && history.state.p1 === state.id) history.back();  // popstate closes it
    else close();
  }

  function close() {
    if (!state || state.closing) return;
    var s = state; s.closing = true;
    if (s.viewWatch) { s.viewWatch.disconnect(); s.viewWatch = null; }
    s.extras.forEach(function (el) { el.remove(); });
    if (s.inst) s.inst.destroy();
    var tile = tileFor(s.id);
    if (tile && !visibleRect(tile) && s.host) {  // e.g. after swiping to another game: bring its tile into view underneath
      var r = tile.getBoundingClientRect();
      s.scrollY = Math.max(0, window.scrollY + r.top - innerHeight / 2 + r.height / 2);
    }
    // Going back to "#week-N" makes the browser jump to that week's top; keep the list where it should be.
    function pin() { if (Math.abs(window.scrollY - s.scrollY) > 1) window.scrollTo(0, s.scrollY); }
    pin();
    window.addEventListener('scroll', pin);
    var end = reduce.matches || !s.host ? null : visibleRect(tile);
    var finished = end ? minimize(s, tile, end)
      : done(s.overlay.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 150, fill: 'forwards' }));
    finished.then(function () {
      s.overlay.remove();
      pin();
      window.removeEventListener('scroll', pin);
      docEl.classList.remove('p1-open');
      document.title = s.title;
      if (idFromHash(location.hash) && window.AAG_P0) history.replaceState(null, '', window.AAG_P0.weekHash());
      state = null;
    });
  }

  function minimize(s, tile, end) {
    var host = s.host, overlay = s.overlay, cx = end.left + end.width / 2, cy = end.top + end.height / 2;
    var s0 = s.pinchScale || 1, from = s.pinchRect || screenRect();
    // header pieces fly back to their places on the tile
    var dest = tileParts(tile), heads = headerParts(s.root), flights = [], hidden = [];
    Object.keys(heads).forEach(function (k) {
      if (!dest[k]) return;
      var f = flyer(heads[k]);
      heads[k].style.visibility = 'hidden';
      dest[k].style.visibility = 'hidden';
      hidden.push(dest[k]);
      flights.push(f);
      f.anim = flyTo(f, dest[k], 280, 0);
    });
    // a card outline shrinks from the page to the tile...
    var shell = document.createElement('div');
    shell.className = 'p1-shell';
    overlay.insertBefore(shell, host);
    overlay.style.background = 'transparent';
    overlay.style.borderColor = 'transparent';
    var shellAnim = shell.animate([frame(from, s0 < 1 ? '20px' : '0px', 'rgba(0,0,0,.12)'), frame(end, '20px', 'rgba(0,0,0,.12)')],
                                  { duration: 280, easing: EASE, fill: 'forwards' });
    // ...while the cards minimize into it and fade
    host.style.transformOrigin = cx + 'px ' + cy + 'px';
    var hostAnim = host.animate([{ transform: 'scale(' + s0 + ')', opacity: 1 },
                                 { transform: 'scale(' + Math.max(0.15, end.width / innerWidth * 0.6) + ')', opacity: 0 }],
                                { duration: 220, easing: EASE, fill: 'forwards' });
    return Promise.all([done(shellAnim), done(hostAnim)].concat(flights.map(function (f) { return done(f.anim); }))).then(function () {
      hidden.forEach(function (el) { el.style.visibility = ''; });
      flights.forEach(function (f) { f.el.remove(); });
      return done(shell.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 100, fill: 'forwards' }));
    });
  }

  // ------------------------------------------------------------ gestures: pull down or pinch in to close, swipe sideways to change games
  function dist(t) { return Math.hypot(t[0].clientX - t[1].clientX, t[0].clientY - t[1].clientY); }

  function setPinch(s, scale) {
    var h = s.host;
    h.style.transform = 'scale(' + scale + ')';
    h.style.borderRadius = (20 / scale) + 'px';
    h.style.overflow = 'hidden';
    h.style.boxShadow = '0 0 0 ' + (1 / scale) + 'px rgba(0,0,0,.12)';
    s.overlay.style.background = 'transparent';
  }
  // Pull down to close: same shrinking-card look as a pinch, but travelling down the screen,
  // so the release can hand straight over to minimize() through pinchScale/pinchRect.
  function setPull(s, dy, scale) {
    var h = s.host;
    h.style.transformOrigin = '50% 50%';
    h.style.transform = 'translateY(' + dy + 'px) scale(' + scale + ')';
    h.style.borderRadius = (20 / scale) + 'px';
    h.style.overflow = 'hidden';
    h.style.boxShadow = '0 0 0 ' + (1 / scale) + 'px rgba(0,0,0,.12)';
    s.overlay.style.background = 'transparent';
  }
  function clearPinch(s) {
    ['transform', 'borderRadius', 'overflow', 'boxShadow', 'transformOrigin'].forEach(function (p) { s.host.style[p] = ''; });
    s.overlay.style.background = '';
  }

  function goTo(s, dir, fromDx, velocityHint) {
    var nid = neighborId(s.id, dir), w = innerWidth;
    if (!nid || s.busy || detailOn(s)) return Promise.resolve(false);
    s.busy = true;
    var view = s.inst ? s.inst.view() : 'large', card = s.inst && s.inst.card ? s.inst.card() : 0;  // stay on the same card
    return load(nid).then(function (text) {
      if (state !== s || s.closing) throw 0;
      var n = s.swipeHost && s.swipeHost.dir === dir ? s.swipeHost.m : mount(s, text, { preview: true, view: view, card: card, dx: dir * w + (fromDx || 0) });
      var oldHost = s.host, dur = velocityHint ? 160 : 220;
      var a1 = oldHost.animate([{ transform: 'translateX(' + (fromDx || 0) + 'px)' }, { transform: 'translateX(' + (-dir * w) + 'px)' }], { duration: dur, easing: EASE, fill: 'forwards' });
      var a2 = n.host.animate([{ transform: 'translateX(' + (dir * w + (fromDx || 0)) + 'px)' }, { transform: 'translateX(0)' }], { duration: dur, easing: EASE, fill: 'forwards' });
      return Promise.all([done(a1), done(a2)]).then(function () {
        if (state !== s || s.closing) return false;
        if (s.inst) s.inst.destroy();
        oldHost.remove();
        n.host.style.transform = '';
        n.host.getAnimations().forEach(function (a) { a.cancel(); });
        var slots = n.root.querySelectorAll('.view-l > .slot');
        all(slots).forEach(function (el) { el.classList.remove('active', 'below', 'above'); });
        s.host = n.host; s.root = n.root; s.id = nid; s.swipeHost = null;
        s.inst = window.AAG_P1.init(n.root, { onBack: requestClose, view: view, card: card });
        armPull(s);
        if (n.title) document.title = n.title;
        history.replaceState(s.pushed ? { p1: nid } : null, '', '#game-' + encodeURIComponent(nid));
        load(neighborId(nid, dir)).catch(function () {});
        return true;
      });
    }).catch(function () { return false; }).then(function (ok) { s.busy = false; return ok; });
  }

  // Is everything under the finger already scrolled to the top? Only then does a downward
  // drag mean "close" rather than "scroll".
  function scrolledDown(n) {
    if (!n || n.nodeType !== 1 || n.scrollHeight <= n.clientHeight + 1) return false;
    var oy = getComputedStyle(n).overflowY;
    return (oy === 'auto' || oy === 'scroll') && n.scrollTop > 1;
  }
  function atScrollTop(e) {
    var s = state;
    // Page 1's own scrollers: the expanded card deck, and the condensed view on short phones
    // (it has a min-height, so it can overflow). Checked directly, because a touch that starts
    // on the host rather than a shadow node wouldn't show them in the path.
    if (s && s.root) {
      var scrollers = s.root.querySelectorAll(detailOn(s) ? '.p2-l' : '.view-l, .view-c, .p1');
      for (var j = 0; j < scrollers.length; j++) if (scrolledDown(scrollers[j])) return false;
    }
    if (s && s.host && scrolledDown(s.host)) return false;
    var path = e.composedPath ? e.composedPath() : [];
    for (var i = 0; i < path.length; i++) {
      var n = path[i];
      if (scrolledDown(n)) return false;
      if (n === document.body) break;
    }
    return true;
  }

  function attachGestures(overlay) {
    var mode = null, x0 = 0, y0 = 0, dx = 0, dy = 0, t0 = 0, d0 = 0, scale = 1, canPull = false;
    overlay.addEventListener('touchstart', function (e) {
      var s = state;
      if (!s || s.closing || s.busy || !s.inst) return;
      if (e.touches.length === 2) {
        if (mode === 'swipe' || mode === 'pull' || detailOn(s)) { if (detailOn(s)) mode = null; return; }   // no pinch on Page 2
        mode = 'pinch'; d0 = dist(e.touches); scale = 1;
        var tile = tileFor(s.id);
        if (tile && !visibleRect(tile)) {
          var r = tile.getBoundingClientRect();
          s.scrollY = Math.max(0, window.scrollY + r.top - innerHeight / 2 + r.height / 2);
          window.scrollTo(0, s.scrollY);
        }
        var tr = visibleRect(tile);
        s.host.style.transformOrigin = tr ? (tr.left + tr.width / 2) + 'px ' + (tr.top + tr.height / 2) + 'px'
          : ((e.touches[0].clientX + e.touches[1].clientX) / 2) + 'px ' + ((e.touches[0].clientY + e.touches[1].clientY) / 2) + 'px';
      } else if (e.touches.length === 1) {
        mode = 'pending'; x0 = e.touches[0].clientX; y0 = e.touches[0].clientY; dx = 0; dy = 0; t0 = Date.now();
        canPull = detailOn(s) ? s.inst.detailAtTop() : atScrollTop(e);   // Page 2: first card, or condensed
        s.touching = true;   // a bounce only counts as a pull while a finger is down
      }
    }, { passive: true });

    overlay.addEventListener('touchmove', function (e) {
      var s = state;
      if (!s || !mode || s.closing) return;
      if (mode === 'pinch') {
        if (e.touches.length !== 2) return;
        e.preventDefault();  // keep the browser from zooming instead
        scale = Math.max(0.35, Math.min(1, dist(e.touches) / d0));
        setPinch(s, scale);
        return;
      }
      if (e.touches.length !== 1) return;
      var mx = e.touches[0].clientX - x0, my = e.touches[0].clientY - y0;
      if (mode === 'pending') {
        if (Math.abs(mx) > 10 && Math.abs(mx) > Math.abs(my) * 1.2) { if (detailOn(s)) { mode = null; return; } mode = 'swipe'; }   // no game swipe on Page 2
        // pulling down from the top closes the page; anything else vertical is a normal scroll
        else if (my > 10 && my > Math.abs(mx) * 1.2 && canPull) { mode = 'pull'; t0 = Date.now(); }
        else if (Math.abs(my) > 10) { mode = null; return; }
        else return;
      }
      if (mode === 'pull') {
        if (e.cancelable) e.preventDefault();   // if the browser already claimed the gesture, just follow it
        dy = Math.max(0, my);
        if (detailOn(s)) { s.inst.pullDetail(dy); return; }   // on Page 2 the pull closes Page 2
        var pp = Math.min(1, dy / (innerHeight * PULL_FULL));
        setPull(s, dy * 0.55, 1 - 0.25 * pp);
        return;
      }
      e.preventDefault();
      var dir = mx < 0 ? 1 : -1, nid = neighborId(s.id, dir), w = innerWidth;
      dx = nid ? mx : mx * 0.3;  // rubber band at the first/last game
      s.host.style.transform = 'translateX(' + dx + 'px)';
      if (nid && (!s.swipeHost || s.swipeHost.dir !== dir)) {
        if (s.swipeHost) { s.swipeHost.m.host.remove(); s.swipeHost = null; }
        var want = { dir: dir, id: nid };
        s.swipeWant = want;
        load(nid).then(function (text) {
          if (state !== s || s.swipeWant !== want || s.swipeHost || mode !== 'swipe') return;
          s.swipeHost = { dir: dir, m: mount(s, text, { preview: true, view: s.inst.view(), card: s.inst.card ? s.inst.card() : 0, dx: dir * w + dx }) };
        }).catch(function () {});
      }
      if (s.swipeHost) s.swipeHost.m.host.style.transform = 'translateX(' + (s.swipeHost.dir * w + dx) + 'px)';
    }, { passive: false });

    function release(e) {
      var s = state;
      if (s) s.touching = !!(e.touches && e.touches.length);
      if (!s || !mode) return;
      if (mode === 'pinch') {
        if (e.touches && e.touches.length >= 2) return;
        mode = null;
        if (scale < PINCH_CLOSE && !s.closing) {
          s.pinchScale = scale;
          s.pinchRect = s.host.getBoundingClientRect();
          clearPinchLook(s);
          requestClose();
          return;
        }
        var from = s.host.style.transform || 'none';
        var back = reduce.matches ? null : s.host.animate([{ transform: from }, { transform: 'none' }], { duration: 180, easing: EASE });
        done(back).then(function () { if (state === s && !s.closing) clearPinch(s); });
        s.host.style.transform = '';
        return;
      }
      if (mode === 'pull') {
        if (e.touches && e.touches.length) return;
        mode = null;
        var pv = dy / Math.max(1, Date.now() - t0);
        if (detailOn(s)) {
          if (dy > innerHeight * PULL_CLOSE || (pv > PULL_FLICK && dy > PULL_MIN)) s.inst.closeDetail();
          else s.inst.pullDetail(0, true);
          return;
        }
        if (!s.closing && (dy > innerHeight * PULL_CLOSE || (pv > PULL_FLICK && dy > PULL_MIN))) {
          s.pinchScale = (s.host.getBoundingClientRect().width || innerWidth) / innerWidth;
          s.pinchRect = s.host.getBoundingClientRect();
          clearPinchLook(s);
          requestClose();
          return;
        }
        var back0 = s.host.style.transform || 'none';
        var springs = reduce.matches ? null : s.host.animate([{ transform: back0 }, { transform: 'none' }], { duration: 200, easing: EASE });
        done(springs).then(function () { if (state === s && !s.closing) clearPinch(s); });
        s.host.style.transform = '';
        return;
      }
      if (mode === 'swipe') {
        mode = null;
        var dir = dx < 0 ? 1 : -1, v = Math.abs(dx) / Math.max(1, Date.now() - t0);
        var go = neighborId(s.id, dir) && (Math.abs(dx) > innerWidth * SWIPE_COMMIT || v > 0.5);
        if (go) { goTo(s, dir, dx, v > 0.5); return; }
        var cur = s.host, sh = s.swipeHost, w = innerWidth, startDx = dx;
        s.swipeHost = null; s.swipeWant = null;
        cur.animate([{ transform: 'translateX(' + startDx + 'px)' }, { transform: 'none' }], { duration: 180, easing: EASE });
        cur.style.transform = '';
        if (sh) done(sh.m.host.animate([{ transform: 'translateX(' + (sh.dir * w + startDx) + 'px)' }, { transform: 'translateX(' + (sh.dir * w) + 'px)' }],
                                       { duration: 180, easing: EASE, fill: 'forwards' })).then(function () { sh.m.host.remove(); });
        return;
      }
      mode = null;
    }
    function clearPinchLook(s) { s.host.style.boxShadow = ''; }
    overlay.addEventListener('touchend', release);
    overlay.addEventListener('touchcancel', release);

    // Trackpads / mice with sideways scrolling
    var acc = 0, idle = 0, locked = false;
    overlay.addEventListener('wheel', function (e) {
      var s = state;
      if (!s || s.closing || Math.abs(e.deltaX) <= Math.abs(e.deltaY)) return;
      e.preventDefault();  // no browser back/forward swipe while Page 1 is open
      clearTimeout(idle); idle = setTimeout(function () { acc = 0; locked = false; }, 180);
      if (locked) return;
      acc += e.deltaX;
      if (Math.abs(acc) > 40) { locked = true; goTo(s, acc > 0 ? 1 : -1); acc = 0; }
    }, { passive: false });
  }

  // ------------------------------------------------------------ wiring
  document.addEventListener('click', function (e) {
    var tile = e.target.closest && e.target.closest(TILE);
    if (!tile || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    open(tileId(tile), { push: true });
  });
  // Start downloading a game's page as soon as someone points at or touches its tile.
  ['mouseover', 'touchstart', 'focusin'].forEach(function (type) {
    document.addEventListener(type, function (e) {
      var tile = !state && e.target.closest && e.target.closest(TILE);
      if (tile) load(tileId(tile)).catch(function () {});
    }, { passive: true });
  });
  window.addEventListener('keydown', function (e) {
    if (!state || state.closing || e.altKey || e.metaKey || e.ctrlKey) return;
    if (e.key === 'ArrowRight') { e.preventDefault(); goTo(state, 1); }
    if (e.key === 'ArrowLeft') { e.preventDefault(); goTo(state, -1); }
  });
  document.addEventListener('gesturestart', function (e) { if (state) e.preventDefault(); });  // iOS Safari zoom
  window.addEventListener('popstate', function () {
    var id = idFromHash(location.hash);
    if (state && id !== state.id) close();
    else if (!state && id) open(id, { detail: detailFromHash(location.hash) });   // Page 1 itself handles Page 2 coming and going
  });

  // Shared link straight to a game (index.html#game-...): show its week underneath, open without the zoom.
  var first = idFromHash(location.hash);
  if (first) {
    var t = tileFor(first);
    if (t && window.AAG_P0) window.AAG_P0.showTile(t);
    open(first, { animate: false, detail: detailFromHash(location.hash) });
  }

})();
"""


def render_page0(data):
    weeks, current = weeks_for_page0(data)
    current_label = next(label for key, label, _g, _b in weeks if key == current)
    options = "".join(
        f'<option value="{esc(k)}"{" selected" if k == current else ""}>{esc(label)}</option>'
        for k, label, _g, _b in weeks
    )
    panels = "".join(render_week_panel(k, label, games, k == current, byes) for k, label, games, byes in weeks)

    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'>"
        "<meta name='theme-color' content='#ffffff'>"
        f"<title>{esc(current_label)} · At A Glance</title>"
        "<meta name='description' content='Pro Football Upcoming Game Information'>"
        "<link rel='preconnect' href='https://fonts.googleapis.com'>"
        "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;700;900&display=swap' rel='stylesheet'>"
        # Saira (italic) for the team abbreviations, Teko for scores and stats. Kept on their
        # own link so a bad request here can never take Inter down with it.
        "<link href='https://fonts.googleapis.com/css2?family=Saira:ital,wdth,wght@1,50..125,400..900&family=Teko:wght@400..700&display=swap' rel='stylesheet'>"
        f"<style>{PAGE0_CSS}</style></head><body data-view='expanded'>"
        f"<main class='track' id='track'>{panels}</main>"
        "<nav class='bottombar' aria-label='Week'>"
        "<div class='bar-in'>"
        "<label class='week-picker'>"
        f"<span id='week-label'>{esc(current_label)}</span>"
        "<svg class='chevron' viewBox='0 0 12 12' aria-hidden='true'><path d='M2.5 7.5 6 4l3.5 3.5' fill='none' stroke='currentColor' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'/></svg>"
        f"<select id='week-select' aria-label='Choose week'>{options}</select>"
        "</label>"
        "<button class='toggle' id='view-toggle' type='button' aria-label='Switch to condensed view' aria-pressed='false'>"
        f"<span class='i-plus'>{render_page1.PLUS}</span><span class='i-minus'>{render_page1.MINUS}</span>"
        "</button>"
        "</div></nav>"
        f"<script>{PAGE0_JS}</script>"
        f"<script>{render_page1.P1_JS}</script>"
        f"<script>{PAGE1_OVERLAY_JS}</script>"
        "</body></html>"
    )


# ---------------------------------------------------------------- raw dump (old v0)

def dict_to_html(d):
    if isinstance(d, dict):
        return "<ul>" + "".join(f"<li><b>{esc(k)}:</b> {dict_to_html(v)}</li>" for k, v in d.items()) + "</ul>"
    if isinstance(d, list):
        if not d:
            return "<i>(none)</i>"
        return "<ol>" + "".join(f"<li>{dict_to_html(i)}</li>" for i in d) + "</ol>"
    return esc(d)


def render_raw(data):
    parts = [
        "<!doctype html><html><head><meta charset='utf-8'><title>At a Glance -- raw data</title></head><body>",
        f"<p><i>Generated {esc(data.get('generated_at_utc'))} -- season {esc(data.get('season'))}, week {esc(data.get('week'))}</i></p>",
    ]
    if data.get("warnings"):
        parts.append(f"<div style='background:#fee;padding:8px'><b>{len(data['warnings'])} warning(s):</b><ul>")
        parts.extend(f"<li>{esc(w)}</li>" for w in data["warnings"])
        parts.append("</ul></div>")
    for m in data.get("matchups") or []:
        try:
            away = (m.get("away") or {}).get("team", "?")
            home = (m.get("home") or {}).get("team", "?")
            parts.append(f"<hr><h2>{esc(away)} @ {esc(home)}</h2>")
            parts.append(dict_to_html({k: m.get(k) for k in
                         ("gameday", "gametime", "venue", "roof", "indoor", "surface", "networks", "weather")}))
            parts.append("<h3>Away</h3>" + dict_to_html(m.get("away") or {}))
            parts.append("<h3>Home</h3>" + dict_to_html(m.get("home") or {}))
        except Exception:
            parts.append(f"<hr><pre style='background:#fee'>{esc(traceback.format_exc())}</pre>")
    parts.append("</body></html>")
    return "".join(parts)


# ---------------------------------------------------------------- main

def main():
    with open(DATA_PATH) as f:
        data = json.load(f)

    os.makedirs(SITE_DIR, exist_ok=True)
    helmets.write_all(HELMET_DIR)

    with open(INDEX_PATH, "w") as f:
        f.write(render_page0(data))
    with open(RAW_PATH, "w") as f:
        f.write(render_raw(data))

    warnings = []
    pages = render_page1.write_all(data, SITE_DIR, warnings)

    print(f"Wrote {INDEX_PATH}, {RAW_PATH}, {pages} game pages and helmets to {HELMET_DIR}")
    for w in warnings:
        print(f"  - {w}")


if __name__ == "__main__":
    main()
