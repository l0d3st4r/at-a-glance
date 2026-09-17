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
.bottombar{position:fixed;left:0;right:0;bottom:0;z-index:10;height:var(--bbar);display:flex;justify-content:center;
  align-items:flex-start;padding:10px 16px env(safe-area-inset-bottom);
  background:rgba(255,255,255,.94);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px)}
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
.game:hover,.game:focus-visible{transform:scale(1.03);background:var(--tile-hover);border-color:var(--tile-border-hover)}
.game:focus-visible{outline:2px solid #000;outline-offset:2px}
.game.placeholder{color:var(--text-2)}
.game.placeholder:hover{transform:none;background:var(--tile);border-color:var(--tile-border)}
/* no prefers-reduced-motion override: motion always plays (Jason, 2026-09-17) */
.team{display:flex;flex-direction:column;align-items:center;gap:4px;min-width:0}
.team img{width:48px;height:48px;display:block}
.abbr{font-size:20px;font-weight:700;line-height:24px}
.record{font-size:16px;font-weight:400;line-height:19px;color:var(--text-2);text-align:center}  /* vertically centered in the tile */
.center{display:flex;flex-direction:column;align-items:center;gap:4px;padding:0 8px}
.time{font-size:20px;font-weight:700;line-height:24px;white-space:nowrap;margin-top:-6px}
.tz{font-size:11px;font-weight:400;margin-left:3px;color:var(--text-2)}
.network{font-size:11px;font-weight:400;line-height:13px;color:var(--text-3);white-space:nowrap}
/* Finished games */
.result{display:flex;flex-direction:column;align-items:center;gap:4px}
.team-record{font-size:16px;font-weight:400;line-height:19px;color:var(--text-2)}
.score{font-size:60px;font-weight:900;line-height:1;text-align:center;font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.score.lose{opacity:.3}
.final-label{font-size:16px;font-weight:700;line-height:19px;letter-spacing:.04em;white-space:nowrap}
.game.final .center{min-width:100px}  /* same width for FINAL and FINAL/OT, so scores line up tile to tile */
@media (max-width:420px){
  .game{grid-template-columns:72px 1fr auto 1fr 72px;padding:14px 4px}
  .team img{width:42px;height:42px}
  .center{padding:0 4px}
  .score{font-size:42px}.final-label{font-size:11px;line-height:13px}
  .game.final .center{min-width:68px}
}
/* Teams on bye: one outlined (not clickable) card under the week's last day */
.bye-list{list-style:none;display:flex;flex-wrap:wrap;justify-content:center;gap:14px 18px;padding:16px 12px;
  background:var(--tile);border:1px solid var(--tile-border);border-radius:20px}
.bye-team{display:flex;flex-direction:column;align-items:center;gap:4px;width:56px}
.bye-team img{width:48px;height:48px;display:block}
@media (max-width:420px){.bye-list{display:grid;grid-template-columns:repeat(var(--bye-cols),56px);justify-content:center;gap:12px 14px;padding:14px 8px}
  .bye-team img{width:42px;height:42px}}
.error{background:#fee;color:#000;padding:8px;font-size:11px;white-space:pre-wrap;border-radius:8px}
.empty{text-align:center;padding:40px 0;color:var(--text-2);font-size:16px}
/* Page 1 opens on top of Page 0 (see PAGE1_OVERLAY_JS): tapping a tile zooms into it, its helmets,
   abbreviations and scores fly up into Page 1's top bar, then Page 1's cards come in. Page 1's own
   styles live inside a shadow root on .p1-host. Swipe sideways for the week's other games; pinch in
   to minimize back into the tile. */
.p1-overlay{position:fixed;z-index:100;box-sizing:border-box;background:var(--tile);
  border:1px solid var(--tile-border);border-radius:20px;overflow:hidden}
.p1-overlay.is-open{inset:0;border-radius:0;border-color:transparent;
  touch-action:pan-y}  /* sideways swipes and two-finger pinches are handled by the script */
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


def render_game(m):
    away, home = m.get("away") or {}, m.get("home") or {}
    if m.get("placeholder"):
        # Playoff game whose teams aren't known yet: gray helmets, not clickable.
        return (
            '<div class="game placeholder" aria-label="Matchup to be determined">'
            f"{render_team(None, mirrored=False)}"
            '<span class="record"></span>'
            '<div class="center"><span class="time">TBD</span>'
            f'<span class="network">{esc(format_network(None))}</span></div>'
            '<span class="record"></span>'
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
        f'<span class="record">{esc(format_record(away.get("record")))}</span>'
        '<div class="center">'
        f'<span class="time">{time_html(time_text)}</span>'
        f'<span class="network">{esc(network)}</span>'
        "</div>"
        f'<span class="record">{esc(format_record(home.get("record")))}</span>'
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
    try:
        if float(a_score) > float(h_score):
            h_cls += " lose"
        elif float(h_score) > float(a_score):
            a_cls += " lose"
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
        f'<a class="game final" href="#game-{esc(m.get("game_id") or "")}" aria-label="{esc(label)}">'
        f"{team_block(away, mirrored=False)}"
        '<div class="result">'
        f'<span class="{a_cls}">{esc(_score_text(a_score))}</span>'
        f'<span class="team-record">{esc(format_record(away.get("record")))}</span>'
        "</div>"
        f'<div class="center"><span class="final-label">{final_text}</span></div>'
        '<div class="result">'
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
    var h = 0;
    for (var i = idx - 1; i <= idx + 1; i++) if (panels[i]) h = Math.max(h, panels[i].offsetHeight);
    track.style.height = h + 'px';
  }
  function setActive(i, opts) {
    opts = opts || {};
    if (!panels[i]) return;
    var changed = i !== idx;
    idx = i;
    var p = panels[i];
    select.value = p.dataset.key;
    label.textContent = p.dataset.label;
    document.title = p.dataset.label + ' · At A Glance';
    if (opts.scroll) track.scrollTo({ left: i * track.clientWidth, behavior: opts.smooth ? 'smooth' : 'auto' });
    sizeTrack();
    if (opts.updateHash !== false && !document.documentElement.classList.contains('p1-open')) history.replaceState(null, '', '#week-' + encodeURIComponent(p.dataset.key));
    if (changed) {
      var top = track.getBoundingClientRect().top + window.scrollY;
      if (window.scrollY > top) window.scrollTo({ top: top });
    }
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

  // ------------------------------------------------------------ helpers
  function idFromHash(h) { var m = (h || '').match(/^#game-(.+)$/); return m ? decodeURIComponent(m[1]) : null; }
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
      var slots = root.querySelectorAll('.slot'), i = Math.max(0, Math.min(slots.length - 1, opts.card || 0));
      if (slots[i]) slots[i].classList.add('active');
      if (slots[i - 1]) slots[i - 1].classList.add('above');
      if (slots[i + 1]) slots[i + 1].classList.add('below');
      var deck = root.querySelector('.deck');
      if (deck && slots[i] && opts.view !== 'condensed') deck.scrollTop = slots[i].offsetTop - (deck.clientHeight - slots[i].offsetHeight) / 2;
    } else {
      m.inst = window.AAG_P1.init(root, { onBack: requestClose, view: opts.view, card: opts.card });
      if (m.title) document.title = m.title;
    }
    return m;
  }
  function tileParts(tile) {  // pieces of a Page 0 tile that travel to Page 1's top bar
    var out = {}, teams = tile.querySelectorAll('.team'), scores = tile.querySelectorAll('.score');
    [0, 1].forEach(function (i) {
      var t = teams[i];
      if (t && t.querySelector('img')) out['img' + i] = t.querySelector('img');
      if (t && t.querySelector('.abbr')) out['abbr' + i] = t.querySelector('.abbr');
      if (scores[i]) out['score' + i] = scores[i];
    });
    return out;
  }
  function headerParts(root) {
    var out = {};
    all(root.querySelectorAll('.bar .teams img')).forEach(function (e, i) { out['img' + i] = e; });
    all(root.querySelectorAll('.bar .teams .abbr')).forEach(function (e, i) { out['abbr' + i] = e; });
    all(root.querySelectorAll('.bar .teams .hscore')).forEach(function (e, i) { out['score' + i] = e; });
    return out;
  }
  function flyer(src) {  // a free-floating copy of an element, sitting exactly on top of it
    var r = src.getBoundingClientRect(), cs = getComputedStyle(src), c = src.cloneNode(true);
    c.removeAttribute('class');
    Object.assign(c.style, {
      position: 'fixed', left: r.left + 'px', top: r.top + 'px', width: r.width + 'px', height: r.height + 'px',
      margin: '0', padding: '0', boxSizing: 'border-box', zIndex: '120', pointerEvents: 'none', transformOrigin: '0 0',
      display: 'block', textAlign: 'center', whiteSpace: 'nowrap', lineHeight: r.height + 'px',
      fontFamily: cs.fontFamily, fontSize: cs.fontSize, fontWeight: cs.fontWeight, letterSpacing: cs.letterSpacing,
      fontVariantNumeric: cs.fontVariantNumeric, color: cs.color, opacity: cs.opacity
    });
    document.body.appendChild(c);
    return { el: c, r: r, fs: parseFloat(cs.fontSize) || 1, img: src.tagName === 'IMG' };
  }
  function flyTo(f, target, duration, delay) {
    var t = target.getBoundingClientRect();
    var sc = f.img ? t.width / f.r.width : (parseFloat(getComputedStyle(target).fontSize) || f.fs) / f.fs;
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
    all(m.root.querySelectorAll(large ? '.slot' : '.view-c > .card, .c-teams > .card')).forEach(function (el, i) {
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
      var m = mount(s, text, { hidden: true });
      s.host = m.host; s.root = m.root; s.inst = m.inst;
      // 2 · helmets, abbreviations (and final scores) fly from the tile up into Page 1's top bar
      var targets = headerParts(m.root);
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
      s.extras.forEach(function (el) { el.remove(); });
      s.extras = [];
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

  // ------------------------------------------------------------ gestures: pinch in to close, swipe to change games
  function dist(t) { return Math.hypot(t[0].clientX - t[1].clientX, t[0].clientY - t[1].clientY); }

  function setPinch(s, scale) {
    var h = s.host;
    h.style.transform = 'scale(' + scale + ')';
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
    if (!nid || s.busy) return Promise.resolve(false);
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
        var slots = n.root.querySelectorAll('.slot');
        all(slots).forEach(function (el) { el.classList.remove('active', 'below', 'above'); });
        s.host = n.host; s.root = n.root; s.id = nid; s.swipeHost = null;
        s.inst = window.AAG_P1.init(n.root, { onBack: requestClose, view: view, card: card });
        if (n.title) document.title = n.title;
        history.replaceState(s.pushed ? { p1: nid } : null, '', '#game-' + encodeURIComponent(nid));
        load(neighborId(nid, dir)).catch(function () {});
        return true;
      });
    }).catch(function () { return false; }).then(function (ok) { s.busy = false; return ok; });
  }

  function attachGestures(overlay) {
    var mode = null, x0 = 0, y0 = 0, dx = 0, t0 = 0, d0 = 0, scale = 1;
    overlay.addEventListener('touchstart', function (e) {
      var s = state;
      if (!s || s.closing || s.busy || !s.inst) return;
      if (e.touches.length === 2) {
        if (mode === 'swipe') return;
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
        mode = 'pending'; x0 = e.touches[0].clientX; y0 = e.touches[0].clientY; dx = 0; t0 = Date.now();
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
        if (Math.abs(mx) > 10 && Math.abs(mx) > Math.abs(my) * 1.2) mode = 'swipe';
        else if (Math.abs(my) > 10) { mode = null; return; }
        else return;
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
    else if (!state && id) open(id, {});
  });

  // Shared link straight to a game (index.html#game-...): show its week underneath, open without the zoom.
  var first = idFromHash(location.hash);
  if (first) {
    var t = tileFor(first);
    if (t && window.AAG_P0) window.AAG_P0.showTile(t);
    open(first, { animate: false });
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
        f"<style>{PAGE0_CSS}</style></head><body>"
        f"<main class='track' id='track'>{panels}</main>"
        "<nav class='bottombar' aria-label='Week'>"
        "<label class='week-picker'>"
        f"<span id='week-label'>{esc(current_label)}</span>"
        "<svg class='chevron' viewBox='0 0 12 12' aria-hidden='true'><path d='M2.5 7.5 6 4l3.5 3.5' fill='none' stroke='currentColor' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'/></svg>"
        f"<select id='week-select' aria-label='Choose week'>{options}</select>"
        "</label></nav>"
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
