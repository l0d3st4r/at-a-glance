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
  - "Week N" title at the top is a dropdown (native <select> under the hood)
    listing every week of the season plus Wild Card, Divisional Round,
    Conference Championships and Super Bowl; it stays pinned while scrolling
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
.topbar{position:sticky;top:0;z-index:10;display:flex;justify-content:center;padding:14px 16px 6px;
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
.week-inner{max-width:600px;margin:0 auto;padding:0 16px 64px}
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
@media (prefers-reduced-motion:reduce){.game{transition:background-color .16s ease,border-color .16s ease}
  .game:hover,.game:focus-visible{transform:none}}
.team{display:flex;flex-direction:column;align-items:center;gap:4px;min-width:0}
.team img{width:48px;height:48px;display:block}
.abbr{font-size:20px;font-weight:700;line-height:24px}
.record{font-size:16px;font-weight:400;line-height:19px;color:var(--text-2);text-align:center;margin-bottom:28px}
.center{display:flex;flex-direction:column;align-items:center;gap:4px;padding:0 8px}
.time{font-size:20px;font-weight:700;line-height:24px;white-space:nowrap;margin-top:-6px}
.tz{font-size:11px;font-weight:400;margin-left:3px;color:var(--text-2)}
.network{font-size:11px;font-weight:400;line-height:13px;color:var(--text-3);white-space:nowrap}
/* Finished games */
.result{display:flex;flex-direction:column;align-items:center;gap:4px}
.team-record{font-size:16px;font-weight:400;line-height:19px;color:var(--text-2)}
.score{font-size:60px;font-weight:900;line-height:1;text-align:center;font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.score.lose{opacity:.3}
.final-label{font-size:16px;font-weight:700;line-height:19px;letter-spacing:.04em}
@media (max-width:420px){
  .game{grid-template-columns:72px 1fr auto 1fr 72px;padding:14px 4px}
  .team img{width:42px;height:42px}
  .center{padding:0 4px}
  .score{font-size:46px}.final-label{font-size:11px;line-height:13px}
}
.error{background:#fee;color:#000;padding:8px;font-size:11px;white-space:pre-wrap;border-radius:8px}
.empty{text-align:center;padding:40px 0;color:var(--text-2);font-size:16px}
/* Page 1 opens on top of Page 0: the clicked tile grows into this full-screen sheet
   (see PAGE1_OVERLAY_JS). Page 1's own styles live inside a shadow root. */
.p1-overlay{position:fixed;z-index:100;box-sizing:border-box;background:var(--tile);
  border:1px solid var(--tile-border);border-radius:20px;overflow:hidden}
.p1-overlay.is-open{inset:0;border-radius:0;border-color:transparent;overflow-y:auto;overscroll-behavior:contain;
  touch-action:pan-x pan-y}  /* two-finger pinch is ours: pinch in to close */
.p1-host{min-height:100%}
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
    label = f"Final: {away_name} {_score_text(a_score)}, {home_name} {_score_text(h_score)}"
    return (
        f'<a class="game final" href="#game-{esc(m.get("game_id") or "")}" aria-label="{esc(label)}">'
        f"{team_block(away, mirrored=False)}"
        '<div class="result">'
        f'<span class="{a_cls}">{esc(_score_text(a_score))}</span>'
        f'<span class="team-record">{esc(format_record(away.get("record")))}</span>'
        "</div>"
        '<div class="center"><span class="final-label">FINAL</span></div>'
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


def weeks_for_page0(data):
    """
    [(key, label, games), ...] for every week in the dropdown, plus the key of
    the week to show first. Falls back to just the current week's matchups if
    build_data.py didn't produce season_weeks (older data file or a failed run).
    """
    season = data.get("season")
    weeks = []
    for w in data.get("season_weeks") or []:
        key, label = str(w.get("key")), w.get("label") or f"Week {w.get('key')}"
        games = w.get("games") or []
        if not games and w.get("game_type") in PLAYOFF_GAME_COUNTS:
            games = placeholder_games(w["game_type"], season)
        weeks.append((key, label, games))

    if not weeks:
        wk = data.get("week")
        weeks = [(str(wk), f"Week {wk}" if wk is not None else "This Week", data.get("matchups") or [])]

    keys = [k for k, _, _ in weeks]
    current = data.get("current_week_key")
    if current is None and data.get("week") is not None:
        current = str(data.get("week"))
    if current not in keys:
        current = keys[0]
    return weeks, current


def render_week_panel(key, label, games, is_current):
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
  var topbar = document.querySelector('.topbar');
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
      var top = track.getBoundingClientRect().top + window.scrollY - topbar.offsetHeight;
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

PAGE1_OVERLAY_JS = """
(function () {
  if (!window.fetch || !Element.prototype.attachShadow || !window.AAG_P1) return;  // old browsers: plain links
  var docEl = document.documentElement, cache = {}, state = null;
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
  var EASE = 'cubic-bezier(.2,.8,.2,1)';
  var PINCH_CLOSE = 0.8;  // let go below 80% size and Page 1 closes

  function idFromHash(h) { var m = (h || '').match(/^#game-(.+)$/); return m ? decodeURIComponent(m[1]) : null; }
  function tileFor(id) {
    var tiles = document.querySelectorAll('a.game[href^="#game-"]');
    for (var i = 0; i < tiles.length; i++) if (idFromHash(tiles[i].getAttribute('href')) === id) return tiles[i];
    return null;
  }
  function pageUrl(id) { return 'game/' + encodeURIComponent(id) + '.html'; }
  function load(id) {
    if (!cache[id]) {
      cache[id] = fetch(pageUrl(id)).then(function (r) { if (!r.ok) throw new Error(r.status); return r.text(); });
      cache[id].catch(function () { delete cache[id]; });
    }
    return cache[id];
  }
  function box(r) { return { left: r.left + 'px', top: r.top + 'px', width: r.width + 'px', height: r.height + 'px' }; }
  function screenBox() { return box({ left: 0, top: 0, width: innerWidth, height: innerHeight }); }
  function frame(b, radius, border) { return Object.assign({ borderRadius: radius, borderColor: border }, b); }
  function visibleRect(el) {
    if (!el) return null;
    var r = el.getBoundingClientRect();
    return (r.width && r.bottom > 0 && r.top < innerHeight && r.right > 0 && r.left < innerWidth) ? r : null;
  }

  function open(id, opts) {
    opts = opts || {};
    if (state) return;
    var tile = tileFor(id), overlay = document.createElement('div');
    var start = opts.animate === false || reduce.matches ? null : visibleRect(tile);
    overlay.className = 'p1-overlay';
    Object.assign(overlay.style, start ? box(start) : screenBox());
    document.body.appendChild(overlay);
    pinchToClose(overlay);
    docEl.classList.add('p1-open');
    state = { id: id, overlay: overlay, pushed: !!opts.push, title: document.title, scrollY: window.scrollY };
    if (opts.push) history.pushState({ p1: id }, '', '#game-' + encodeURIComponent(id));

    var grow = start
      ? overlay.animate([frame(box(start), '20px', 'rgba(0,0,0,.12)'), frame(screenBox(), '0px', 'rgba(0,0,0,0)')],
                        { duration: 440, easing: EASE, fill: 'forwards' }).finished
      : Promise.resolve();
    Promise.all([grow, load(id)]).then(function (res) {
      if (!state || state.id !== id || state.closing) return;
      overlay.style.cssText = '';
      overlay.classList.add('is-open');
      overlay.getAnimations().forEach(function (a) { a.cancel(); });
      mount(res[1]);
    }).catch(function () { location.href = pageUrl(id); });
  }

  function mount(text) {
    var page = new DOMParser().parseFromString(text, 'text/html');
    var css = page.getElementById('p1-css'), block = page.querySelector('.p1');
    if (!block) { location.href = pageUrl(state.id); return; }
    var host = document.createElement('div'), root = host.attachShadow({ mode: 'open' });
    host.className = 'p1-host';
    root.innerHTML = '<style>' + (css ? css.textContent : '') + '</style>' +
      block.outerHTML.replace(/(src|href)="\\.\\.\\//g, '$1="');
    state.overlay.appendChild(host);
    state.host = host;
    if (!reduce.matches) host.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 220, easing: 'ease-out' });
    state.inst = window.AAG_P1.init(root, { onBack: requestClose });
    if (page.title) document.title = page.title;
  }

  // Pinch in to close (phones): the sheet follows your fingers as it shrinks;
  // let go small enough and it closes back into its tile, otherwise it springs back.
  function pinchToClose(overlay) {
    var d0 = 0, scale = 1;
    function dist(t) { return Math.hypot(t[0].clientX - t[1].clientX, t[0].clientY - t[1].clientY); }
    overlay.addEventListener('touchstart', function (e) {
      if (!state || state.closing || !overlay.classList.contains('is-open') || e.touches.length !== 2) return;
      d0 = dist(e.touches); scale = 1;
      overlay.style.transformOrigin = ((e.touches[0].clientX + e.touches[1].clientX) / 2) + 'px ' +
                                      ((e.touches[0].clientY + e.touches[1].clientY) / 2) + 'px';
    }, { passive: true });
    overlay.addEventListener('touchmove', function (e) {
      if (!d0 || e.touches.length !== 2) return;
      e.preventDefault();  // keep the browser from zooming instead
      scale = Math.max(0.4, Math.min(1, dist(e.touches) / d0));
      overlay.style.transform = 'scale(' + scale + ')';
      overlay.style.borderRadius = (20 / scale) + 'px';
      overlay.style.borderColor = 'rgba(0,0,0,.12)';
      overlay.style.overflow = 'hidden';
    }, { passive: false });
    function release(e) {
      if (!d0 || (e.touches && e.touches.length >= 2)) return;
      d0 = 0;
      if (scale < PINCH_CLOSE && state && !state.closing) { state.pinchRect = overlay.getBoundingClientRect(); requestClose(); return; }
      var from = overlay.style.transform || 'scale(1)';
      overlay.style.transform = overlay.style.borderRadius = overlay.style.borderColor = overlay.style.overflow = '';
      if (from !== 'scale(1)' && !reduce.matches) overlay.animate([{ transform: from }, { transform: 'scale(1)' }], { duration: 220, easing: EASE });
    }
    overlay.addEventListener('touchend', release);
    overlay.addEventListener('touchcancel', release);
  }
  document.addEventListener('gesturestart', function (e) { if (state) e.preventDefault(); });  // iOS Safari zoom

  function requestClose() {
    if (!state) return;
    if (state.pushed && history.state && history.state.p1 === state.id) history.back();  // popstate closes it
    else close();
  }

  function close() {
    if (!state || state.closing) return;
    var s = state; s.closing = true;
    if (s.inst) s.inst.destroy();
    // Going back to "#week-N" makes the browser jump to that week's top; keep the list where it was.
    function pin() { if (Math.abs(window.scrollY - s.scrollY) > 1) window.scrollTo(0, s.scrollY); }
    pin();
    window.addEventListener('scroll', pin);
    var end = reduce.matches ? null : visibleRect(tileFor(s.id));
    var fade = s.host && !reduce.matches
      ? s.host.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 140, fill: 'forwards' }).finished
      : Promise.resolve();
    fade.then(function () {
      if (s.host) s.host.remove();
      if (!end) return s.overlay.animate([{ opacity: 1 }, { opacity: 0 }], { duration: reduce.matches ? 1 : 180, fill: 'forwards' }).finished;
      var from = s.pinchRect ? box(s.pinchRect) : screenBox();
      s.overlay.classList.remove('is-open');
      s.overlay.style.transform = '';
      Object.assign(s.overlay.style, from);
      return s.overlay.animate([frame(from, s.pinchRect ? '20px' : '0px', s.pinchRect ? 'rgba(0,0,0,.12)' : 'rgba(0,0,0,0)'), frame(box(end), '20px', 'rgba(0,0,0,.12)')],
                               { duration: 380, easing: EASE, fill: 'forwards' }).finished;
    }).then(function () {
      s.overlay.remove();
      pin();
      window.removeEventListener('scroll', pin);
      docEl.classList.remove('p1-open');
      document.title = s.title;
      if (idFromHash(location.hash) && window.AAG_P0) history.replaceState(null, '', window.AAG_P0.weekHash());
      state = null;
    });
  }

  document.addEventListener('click', function (e) {
    var tile = e.target.closest && e.target.closest('a.game[href^="#game-"]');
    if (!tile || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    open(idFromHash(tile.getAttribute('href')), { push: true });
  });
  // Start downloading a game's page as soon as someone points at or touches its tile.
  ['mouseover', 'touchstart', 'focusin'].forEach(function (type) {
    document.addEventListener(type, function (e) {
      var tile = e.target.closest && e.target.closest('a.game[href^="#game-"]');
      if (tile) load(idFromHash(tile.getAttribute('href')));
    }, { passive: true });
  });
  window.addEventListener('popstate', function () {
    var id = idFromHash(location.hash);
    if (state && id !== state.id) close();
    else if (!state && id) open(id, {});
  });

  // Shared link straight to a game (index.html#game-...): show its week underneath, open without the grow.
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
    current_label = next(label for key, label, _ in weeks if key == current)
    options = "".join(
        f'<option value="{esc(k)}"{" selected" if k == current else ""}>{esc(label)}</option>'
        for k, label, _ in weeks
    )
    panels = "".join(render_week_panel(k, label, games, k == current) for k, label, games in weeks)

    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<meta name='theme-color' content='#ffffff'>"
        f"<title>{esc(current_label)} · At A Glance</title>"
        "<meta name='description' content='Pro Football Upcoming Game Information'>"
        "<link rel='preconnect' href='https://fonts.googleapis.com'>"
        "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;700;900&display=swap' rel='stylesheet'>"
        f"<style>{PAGE0_CSS}</style></head><body>"
        "<header class='topbar'>"
        "<label class='week-picker'>"
        f"<span id='week-label'>{esc(current_label)}</span>"
        "<svg class='chevron' viewBox='0 0 12 12' aria-hidden='true'><path d='M2.5 4.5 6 8l3.5-3.5' fill='none' stroke='currentColor' stroke-width='1.6' stroke-linecap='round' stroke-linejoin='round'/></svg>"
        f"<select id='week-select' aria-label='Choose week'>{options}</select>"
        "</label></header>"
        f"<main class='track' id='track'>{panels}</main>"
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
