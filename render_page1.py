"""
Page 1 -- the matchup page. One standalone file per game: site/game/<game_id>.html

Design = Jason's approved v8 preview (2026-09-16):
  - two views of the same page, switched with the +/− button in the top bar
      * expanded (default every time the page opens): pinned top bar with
        "‹ Week N" over mini helmets + AWAY @ HOME; one card per screen that
        snaps while scrolling, slivers of the cards above/below with a label,
        position dots on the right
      * condensed: "‹ Week N" only in the top bar; every card on one screen
  - cards: Game Info, away team, home team, Leaders
  - team cards: last-game arrow (green up = W, red down = L, yellow line = T),
    record, top 3 injuries (starters first), offense/defense ranks
  - leaders: each team's leader in 5 stats, crown when top 3 in the league
  - cards, borders, hover, top bar, week pill, 600px column, Bold abbreviations
    all match Page 0

How it opens from Page 0: render_html.py adds a small script to index.html that
expands the clicked tile to full screen, fetches this file, and shows its
.p1 block inside a shadow root (so Page 0's CSS and Page 1's CSS can't clash).
Opened directly (shared link), the file works on its own too.

Data comes from data/matchups.json -> "game_details" (see page1_data.py).
Defensive like render_html.py: a missing value shows "—", and a game that
fails to render is skipped with a warning instead of breaking the build.
"""

import html
import os
import traceback
from datetime import date

import helmets

MONTHS_UPPER = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
TEAM_NAMES = {
    "ARI": "Cardinals", "ATL": "Falcons", "BAL": "Ravens", "BUF": "Bills", "CAR": "Panthers", "CHI": "Bears",
    "CIN": "Bengals", "CLE": "Browns", "DAL": "Cowboys", "DEN": "Broncos", "DET": "Lions", "GB": "Packers",
    "HOU": "Texans", "IND": "Colts", "JAX": "Jaguars", "KC": "Chiefs", "LAC": "Chargers", "LAR": "Rams",
    "LV": "Raiders", "MIA": "Dolphins", "MIN": "Vikings", "NE": "Patriots", "NO": "Saints", "NYG": "Giants",
    "NYJ": "Jets", "PHI": "Eagles", "PIT": "Steelers", "SEA": "Seahawks", "SF": "49ers", "TB": "Buccaneers",
    "TEN": "Titans", "WAS": "Commanders",
}
DASH = "—"


def esc(v):
    return html.escape(str(v), quote=True)


# ---------------------------------------------------------------- icons

CHEV = ('<svg class="chev" viewBox="0 0 10 16" width="9" height="14" fill="none" stroke="currentColor" stroke-width="2.2" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M8 2 2 8l6 6"/></svg>')
UP = ('<svg viewBox="0 0 12 8" width="10" height="7" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
      'stroke-linejoin="round" aria-hidden="true"><path d="M1 6.5 6 1.5l5 5"/></svg>')
DOWN = ('<svg viewBox="0 0 12 8" width="10" height="7" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true"><path d="M1 1.5 6 6.5l5-5"/></svg>')
PLUS = ('<svg viewBox="0 0 14 14" width="14" height="14" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'aria-hidden="true"><path d="M7 1.5v11M1.5 7h11"/></svg>')
MINUS = ('<svg viewBox="0 0 14 14" width="14" height="14" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
         'aria-hidden="true"><path d="M1.5 7h11"/></svg>')

TREND = {
    "W": ('<svg class="trend t-w" viewBox="0 0 18 12" width="18" height="12" fill="none" stroke="currentColor" stroke-width="3" '
          'stroke-linecap="round" stroke-linejoin="round" role="img" aria-label="Won last game"><path d="M2.5 10 9 3.5l6.5 6.5"/></svg>'),
    "L": ('<svg class="trend t-l" viewBox="0 0 18 12" width="18" height="12" fill="none" stroke="currentColor" stroke-width="3" '
          'stroke-linecap="round" stroke-linejoin="round" role="img" aria-label="Lost last game"><path d="M2.5 2 9 8.5 15.5 2"/></svg>'),
    "T": ('<svg class="trend t-t" viewBox="0 0 18 12" width="18" height="12" fill="none" stroke="currentColor" stroke-width="3" '
          'stroke-linecap="round" role="img" aria-label="Tied last game"><path d="M3 6h12"/></svg>'),
}

MEDALS = {1: ("gold", "1st"), 2: ("silver", "2nd"), 3: ("bronze", "3rd")}


def crown(rank):
    if rank not in MEDALS:
        return ""
    key, word = MEDALS[rank]
    return (f'<svg class="crown" viewBox="0 0 20 16" width="17" height="14" role="img" aria-label="{word} in the league">'
            f'<path d="M1.5 14.5 1 3.5l5.2 4.2L10 1l3.8 6.7L19 3.5l-.5 11z" fill="var(--{key})"/></svg>')


def _wx(paths, label):
    return (f'<svg class="wx" viewBox="0 0 64 48" width="60" height="45" fill="none" stroke="currentColor" stroke-width="3.5" '
            f'stroke-linecap="round" stroke-linejoin="round" role="img" aria-label="{label}">{paths}</svg>')


_CLOUD = '<path d="M17 40a9 9 0 0 1-1-17.9A13 13 0 0 1 41 18.5 10.5 10.5 0 1 1 47 40z"/>'
_CLOUD_HIGH = '<path d="M17 32a9 9 0 0 1-1-17.9A13 13 0 0 1 41 10.5 10.5 10.5 0 1 1 47 32z"/>'
WEATHER_ICONS = {
    "sun": _wx('<circle cx="32" cy="24" r="9"/><path d="M32 5v5M32 38v5M13 24h5M46 24h5M18.6 10.6l3.5 3.5M41.9 33.9l3.5 3.5'
               'M18.6 37.4l3.5-3.5M41.9 14.1l3.5-3.5"/>', "Sunny"),
    "partly": _wx('<circle cx="22" cy="17" r="7"/><path d="M22 3v3M8 17h3M12.1 7.1l2.1 2.1M31.9 7.1l-2.1 2.1"/>'
                  '<path d="M23 42a8 8 0 0 1-.8-16A12 12 0 0 1 45 23a9.5 9.5 0 1 1 5 19z"/>', "Partly cloudy"),
    "cloud": _wx(_CLOUD, "Cloudy"),
    "rain": _wx(_CLOUD_HIGH + '<path d="M22 38l-3 6M33 38l-3 6M44 38l-3 6"/>', "Rain"),
    "snow": _wx(_CLOUD_HIGH + '<path d="M21 40h.01M32 43h.01M43 40h.01" stroke-width="5"/>', "Snow"),
    "storm": _wx(_CLOUD_HIGH + '<path d="M34 34l-6 8h8l-5 6"/>', "Thunderstorms"),
    "fog": _wx('<path d="M8 16h40M16 26h40M8 36h36"/>', "Fog"),
    "wind": _wx('<path d="M4 14h34a7 7 0 1 0-7-7"/><path d="M4 24h48a7 7 0 1 1-7 7"/><path d="M4 34h26a6 6 0 1 1-6 6"/>', "Windy"),
    "indoor": _wx('<path d="M8 38a24 24 0 0 1 48 0M4 38h56M32 14v24M20 18l4 20M44 18l-4 20"/>', "Indoors"),
}


# ---------------------------------------------------------------- formatting

def fmt_time(gametime):
    """'20:15' -> ('8:15', 'PM ET'); missing -> ('TBD', '')."""
    try:
        hh, mm = (int(x) for x in str(gametime).split(":")[:2])
    except (TypeError, ValueError):
        return "TBD", ""
    return f"{hh % 12 or 12}:{mm:02d}", ("AM ET" if hh < 12 else "PM ET")


def fmt_date(gameday):
    """'2026-10-19' -> 'OCT 19 Monday'."""
    try:
        d = date.fromisoformat(str(gameday)[:10])
    except (TypeError, ValueError):
        return "Date TBD"
    return f"{MONTHS_UPPER[d.month - 1]} {d.day} {DAY_NAMES[d.weekday()]}"


def fmt_network(networks):
    if isinstance(networks, str) and networks.strip():
        return networks.strip()
    if isinstance(networks, list) and networks:
        return ", ".join(str(n) for n in networks)
    return "TV TBD"


def fmt_record(r):
    r = r or {}
    w, l, t = r.get("wins", 0), r.get("losses", 0), r.get("ties", 0)
    return f"{w}-{l}-{t}" if t else f"{w}-{l}"


def fmt_value(v):
    if v is None:
        return DASH
    if float(v).is_integer():
        return f"{int(v):,}"
    return f"{v:,.1f}"


def ordinal(n):
    return "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def helmet_img(team, size, mirrored=False, prefix="../"):
    src = prefix + "helmets/" + helmets.helmet_filename(team, mirrored=mirrored)
    return f'<img src="{esc(src)}" alt="" width="{size}" height="{size}">'


# ---------------------------------------------------------------- pieces

def game_body(d):
    t, ampm = fmt_time(d.get("gametime"))
    w, venue = d.get("weather") or {}, d.get("venue") or {}
    if w.get("indoor"):
        weather = f'<span class="temp temp-word">Indoors</span>{WEATHER_ICONS["indoor"]}'
    elif w.get("available") and w.get("temp_f") is not None:
        weather = f'<span class="temp">{esc(w["temp_f"])}°</span>{WEATHER_ICONS.get(w.get("condition"), "")}'
    else:
        weather = f'<span class="temp temp-na" title="Forecast not available yet">{DASH}°</span>'
    small = f"<small>{ampm}</small>" if ampm else ""
    headline = f'<div class="time">{esc(t)}{small}</div>'
    corner = f'<div class="network">{esc(fmt_network(d.get("networks")))}</div>'
    score = d.get("score") if d.get("final") else None
    if score:
        # Finished game: final score (away – home, loser faded like Page 0's FINAL tiles) and "FINAL".
        a_s, h_s = score.get("away"), score.get("home")
        a_cls = h_cls = "sc"
        try:
            if float(a_s) > float(h_s):
                h_cls += " lose"
            elif float(h_s) > float(a_s):
                a_cls += " lose"
        except (TypeError, ValueError):
            pass
        headline = (f'<div class="time final-score"><span class="{a_cls}">{esc(fmt_value(a_s))}</span>'
                    f'<span class="sc-dash">–</span><span class="{h_cls}">{esc(fmt_value(h_s))}</span></div>')
        corner = '<div class="network final-label">FINAL</div>'
    return (
        '<div class="game-top">'
        f'<div>{headline}<div class="date">{esc(fmt_date(d.get("gameday")))}</div></div>'
        f'{corner}</div>'
        f'<div class="game-bottom"><div class="city">{esc(venue.get("city") or "")}</div><div class="weather">{weather}</div></div>'
    )


def injuries_html(side, full):
    rows = side.get("injuries") or []
    if not rows:
        text = "No injuries reported" if side.get("injury_report_out") else "Injury report not available"
        return f'<li class="inj-none">{text}</li>'
    out = []
    for r in rows[:3]:
        status = r.get("status") or ""
        cls = {"Out": "out", "Doubtful": "doubt", "Questionable": "ques"}.get(status, "ques")
        name = r.get("name") if full else r.get("short")
        label = status if full else r.get("status_short") or status
        out.append(f'<li><span class="inj-name">{esc(name or "")}</span><span class="inj-s inj-{cls}">{esc(label)}</span></li>')
    return "".join(out)


def big_rank(n, label):
    if not isinstance(n, int):
        return f'<div class="rank"><span class="rank-n na">{DASH}</span><span class="rank-sfx"></span><span class="rank-lbl">{label}</span></div>'
    return f'<div class="rank"><span class="rank-n">{n}</span><span class="rank-sfx">{ordinal(n)}</span><span class="rank-lbl">{label}</span></div>'


def small_rank(n, label):
    if not isinstance(n, int):
        return f'<div class="crank"><b class="na">{DASH}</b><span>{label}</span></div>'
    return f'<div class="crank"><b>{n}<sup>{ordinal(n)}</sup></b><span>{label}</span></div>'


def c_team(side, label):
    r = side.get("ranks") or {}
    return (
        f'<a class="card c-team" tabindex="0" data-detail="{label}-team" aria-label="{esc(side.get("team"))} team">'
        f'<div class="c-rec">{TREND.get(side.get("last"), "")}<span class="record">{esc(fmt_record(side.get("record")))}</span></div>'
        f'<ul class="injuries c-inj">{injuries_html(side, full=False)}</ul>'
        '<div class="cranks">'
        f'<div class="ccol"><h3>Offense</h3>{small_rank(r.get("off_points"), "PTS")}{small_rank(r.get("off_yards"), "YDS")}</div>'
        f'<div class="ccol"><h3>Defense</h3>{small_rank(r.get("def_points"), "PTS")}{small_rank(r.get("def_yards"), "YDS")}</div>'
        "</div></a>"
    )


def l_team(side):
    r = side.get("ranks") or {}
    team = side.get("team")
    return (
        '<div class="l-top">'
        f'<div class="l-id">{helmet_img(team, 84)}<span class="abbr">{esc(team)}</span></div>'
        f'<div class="l-rec">{TREND.get(side.get("last"), "")}<span class="record">{esc(fmt_record(side.get("record")))}</span></div>'
        "</div>"
        f'<ul class="l-inj">{injuries_html(side, full=True)}</ul>'
        '<div class="ranks">'
        f'<div class="rank-col"><h3>Offense</h3>{big_rank(r.get("off_points"), "POINTS")}{big_rank(r.get("off_yards"), "YARDS")}</div>'
        f'<div class="rank-col"><h3>Defense</h3>{big_rank(r.get("def_points"), "POINTS")}{big_rank(r.get("def_yards"), "YARDS")}</div>'
        "</div>"
    )


def leader_cell(p):
    if not p:
        return f'<div class="ldr"><div class="ldr-v na"><span>{DASH}</span></div><div class="ldr-n">&nbsp;</div></div>'
    return (
        f'<div class="ldr"><div class="ldr-v"><span>{esc(fmt_value(p.get("value")))}</span>{crown(p.get("league_rank"))}</div>'
        f'<div class="ldr-n"><span class="nm">{esc(p.get("name") or "")}</span> <span class="pos">{esc(p.get("position") or "")}</span></div></div>'
    )


def leader_rows(d):
    return "".join(
        f'<div class="cmp-row">{leader_cell(row.get("away"))}'
        f'<div class="cmp-lbl">{esc(row.get("label", "")).replace(" ", "<br>")}</div>'
        f'{leader_cell(row.get("home"))}</div>'
        for row in d.get("leaders") or []
    )


# ---------------------------------------------------------------- page

def render_p1_block(d, prefix="../"):
    """The <div class="p1"> block (shared by the standalone page and the Page 0 overlay)."""
    away, home = d.get("away") or {}, d.get("home") or {}
    a, h = away.get("team") or "TBD", home.get("team") or "TBD"
    week_href = f"{prefix}index.html#week-{d.get('week_key')}"
    week_label = d.get("week_label") or ""
    rows = leader_rows(d)
    img = lambda team, size, mir=False: helmet_img(team, size, mir, prefix)

    bar = (
        '<header class="bar"><div class="bar-in">'
        f'<a class="week" href="{esc(week_href)}">{CHEV}<span>{esc(week_label)}</span></a>'
        f'<div class="teams" aria-label="{esc(TEAM_NAMES.get(a, a))} at {esc(TEAM_NAMES.get(h, h))}">'
        f'{img(a, 44)}<span class="abbr">{esc(a)}</span><span class="at">@</span><span class="abbr">{esc(h)}</span>{img(h, 44, True)}</div>'
        f'<button class="toggle" type="button"><span class="i-plus">{PLUS}</span><span class="i-minus">{MINUS}</span></button>'
        "</div></header>"
    )
    condensed = (
        '<div class="view view-c" aria-label="Condensed matchup">'
        '<div class="c-matchup">'
        f'<div class="c-side">{img(a, 48)}<span class="abbr">{esc(a)}</span></div>'
        f'<div class="c-side"><span class="abbr">{esc(h)}</span>{img(h, 48, True)}</div></div>'
        f'<a class="card c-game" tabindex="0" data-detail="game-info" aria-label="Game info">{game_body(d)}</a>'
        f'<div class="c-teams">{c_team(away, "away")}{c_team(home, "home")}</div>'
        f'<a class="card c-cmp" tabindex="0" data-detail="leaders" aria-label="Season leaders"><div class="c-cmp-in">{rows}</div></a>'
        "</div>"
    )
    cmp_head = (
        '<div class="cmp-row cmp-head">'
        f'<div class="l-id-s">{img(a, 52)}<span class="abbr">{esc(a)}</span></div><div></div>'
        f'<div class="l-id-s">{img(h, 52, True)}<span class="abbr">{esc(h)}</span></div></div>'
    )
    cards = [("game-info", "Game Info", "game", game_body(d)),
             ("away-team", a, "team", l_team(away)),
             ("home-team", h, "team", l_team(home)),
             ("leaders", "Leaders", "compare", cmp_head + rows)]
    slots = "".join(
        f'<section class="slot"><a class="card {kind}" tabindex="-1" data-detail="{cid}" aria-label="{esc(name)}">'
        f'<span class="peek peek-top">{DOWN}<span>{esc(name)}</span></span><div class="body">{body}</div>'
        f'<span class="peek peek-bot">{UP}<span>{esc(name)}</span></span></a></section>'
        for cid, name, kind, body in cards
    )
    dots = "".join(f'<button class="dot" type="button" aria-label="{esc(name)}"></button>' for _c, name, _k, _b in cards)
    large = f'<div class="view view-l deck" aria-label="Expanded matchup">{slots}</div><nav class="dots" aria-label="Cards">{dots}</nav>'
    return f'<div class="p1" data-view="large" data-game="{esc(d.get("game_id"))}">{bar}{condensed}{large}</div>'


def render_standalone(d):
    a = (d.get("away") or {}).get("team") or "TBD"
    h = (d.get("home") or {}).get("team") or "TBD"
    title = f"{a} @ {h} · {d.get('week_label') or ''} · At A Glance"
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'>"
        "<meta name='theme-color' content='#ffffff'>"
        f"<title>{esc(title)}</title>"
        "<link rel='preconnect' href='https://fonts.googleapis.com'><link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;700;900&display=swap' rel='stylesheet'>"
        f"<style id='p1-css'>{P1_CSS}</style><style>html,body{{margin:0;background:#fff}}</style></head><body>"
        f"{render_p1_block(d)}"
        f"<script>{P1_JS}</script><script>AAG_P1.init(document);</script>"
        "</body></html>"
    )


def write_all(data, site_dir, warnings=None):
    """Write site/game/<game_id>.html for every game in data['game_details']. Returns the count."""
    details = data.get("game_details") or {}
    out_dir = os.path.join(site_dir, "game")
    os.makedirs(out_dir, exist_ok=True)
    count = 0
    for gid, d in details.items():
        try:
            safe = "".join(ch for ch in str(gid) if ch.isalnum() or ch in "_-")
            with open(os.path.join(out_dir, f"{safe}.html"), "w") as f:
                f.write(render_standalone(d))
            count += 1
        except Exception:
            if warnings is not None:
                warnings.append(f"render_page1 {gid}: {traceback.format_exc(limit=1)}")
    return count


# ---------------------------------------------------------------- script (shared with the Page 0 overlay)

P1_JS = r"""
window.AAG_P1 = window.AAG_P1 || { init: function (root, opts) {
  opts = opts || {};
  var wrap = root.querySelector('.p1'); if (!wrap) return { destroy: function () {} };
  var deck = root.querySelector('.deck'), slots = [].slice.call(root.querySelectorAll('.slot')),
      dots = [].slice.call(root.querySelectorAll('.dot')), toggle = root.querySelector('.toggle'),
      week = root.querySelector('.week'), active = -1, bound = [];
  var smooth = matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';
  function on(t, type, fn, o) { t.addEventListener(type, fn, o); bound.push([t, type, fn, o]); }
  function large() { return wrap.getAttribute('data-view') === 'large'; }
  function setActive(i) {
    if (i === active) return; active = i;
    slots.forEach(function (s, k) {
      s.classList.toggle('active', k === i); s.classList.toggle('above', k === i - 1); s.classList.toggle('below', k === i + 1);
      var c = s.querySelector('a.card'); c.tabIndex = k === i ? 0 : -1; c.setAttribute('aria-hidden', k === i ? 'false' : 'true');
    });
    dots.forEach(function (d, k) { d.classList.toggle('on', k === i); });
  }
  function current() {
    var mid = deck.scrollTop + deck.clientHeight / 2, best = 0, bd = 1e9;
    slots.forEach(function (s, k) { var d = Math.abs(s.offsetTop + s.offsetHeight / 2 - mid); if (d < bd) { bd = d; best = k; } });
    return best;
  }
  function go(i, instant) {
    i = Math.max(0, Math.min(slots.length - 1, i)); var s = slots[i];
    deck.scrollTo({ top: s.offsetTop - (deck.clientHeight - s.offsetHeight) / 2, behavior: instant ? 'auto' : smooth });
  }
  var ticking = false;
  on(deck, 'scroll', function () { if (!ticking) { ticking = true; requestAnimationFrame(function () { setActive(current()); ticking = false; }); } }, { passive: true });
  // Tapping a peeking card brings it in; tapping the active card will open Page 2 later.
  slots.forEach(function (s, k) { on(s.querySelector('a.card'), 'click', function (e) { e.preventDefault(); if (k !== active) go(k); }); });
  dots.forEach(function (d, k) { on(d, 'click', function () { go(k); }); });
  function setView(v) {
    wrap.setAttribute('data-view', v);
    toggle.setAttribute('aria-label', v === 'large' ? 'Switch to condensed view' : 'Switch to expanded view');
    toggle.setAttribute('aria-pressed', v === 'large' ? 'true' : 'false');
    if (v === 'large') requestAnimationFrame(function () { go(active < 0 ? 0 : active, true); setActive(current()); });
  }
  on(toggle, 'click', function () { setView(large() ? 'condensed' : 'large'); });
  function back() { if (opts.onBack) opts.onBack(); else location.href = week.href; }
  on(week, 'click', function (e) { if (opts.onBack) { e.preventDefault(); opts.onBack(); } });
  on(window, 'keydown', function (e) {
    if (e.key === 'Escape') { back(); return; }
    if (!large()) return;
    if (e.key === 'ArrowDown' || e.key === 'PageDown') { e.preventDefault(); go(active + 1); }
    else if (e.key === 'ArrowUp' || e.key === 'PageUp') { e.preventDefault(); go(active - 1); }
  });
  on(window, 'resize', function () { if (large()) go(active, true); });
  setView('large');  // always opens expanded
  return { destroy: function () { bound.forEach(function (b) { b[0].removeEventListener(b[1], b[2], b[3]); }); bound = []; } };
} };
"""

# ---------------------------------------------------------------- styles (ported 1:1 from the approved v8 preview)

P1_CSS = r"""
:host{display:block}
.p1{--ink:#000;--tile:#fff;--tile-border:rgba(0,0,0,.12);--tile-border-soft:rgba(0,0,0,.07);--tile-hover:rgba(0,0,0,.03);--tile-border-hover:rgba(0,0,0,.28);--text-2:rgba(0,0,0,.62);--text-3:rgba(0,0,0,.4);
  --out:#A00000;--doubt:#A52800;--ques:#B58900;--win:#1E8A3C;--loss:#A00000;--tie:#B58900;--gold:#D4A20A;--silver:#A2A7AD;--bronze:#B5702F;--bar:52px;--peek:40px;--gap:12px;--col:600px}
.p1[data-view=large]{--bar:96px}
*{box-sizing:border-box;margin:0;padding:0}
.p1{min-height:100%;background:#fff;color:var(--ink);font-family:Inter,system-ui,-apple-system,sans-serif;font-weight:400;-webkit-font-smoothing:antialiased}
.view{display:none}
.p1[data-view=condensed] .view-c{display:grid}
.p1[data-view=large] .view-l,.p1[data-view=large] .dots{display:block}
.abbr{font-weight:700;line-height:1}
a.card{position:relative;display:block;color:inherit;text-decoration:none;background:var(--tile);border:1px solid var(--tile-border);border-radius:20px;
  transition:transform .16s,background-color .16s,border-color .16s}
a.card:focus-visible{outline:2px solid #000;outline-offset:2px}

/* ===== Top bar ===== */
.bar{position:fixed;inset:0 0 auto;height:var(--bar);z-index:10;background:rgba(255,255,255,.94);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px)}
.bar-in{position:relative;max-width:var(--col);height:100%;margin:0 auto;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px}
.week{color:inherit;text-decoration:none;display:inline-flex;align-items:center;gap:6px;font-size:16px;font-weight:400;line-height:19px;padding:6px 12px;border-radius:999px;transition:background-color .16s}
.week:hover{background:rgba(0,0,0,.05)}
.week:focus-visible{outline:2px solid #000;outline-offset:2px}
.week .chev{width:12px;height:12px}
.teams{display:none;align-items:center;gap:8px}
.p1[data-view=large] .teams{display:flex}
.teams .abbr{font-size:20px}
.teams .at{font-size:16px;padding:0 4px}
.teams img{display:block}
.toggle{position:absolute;right:16px;top:10px;width:32px;height:32px;border-radius:50%;border:1px solid var(--tile-border);background:#fff;color:#000;
  display:flex;align-items:center;justify-content:center;cursor:pointer;transition:transform .16s,background-color .16s,border-color .16s}
.toggle:hover{transform:scale(1.03);background:rgba(0,0,0,.05);border-color:var(--tile-border-hover)}
.toggle:focus-visible{outline:2px solid #000;outline-offset:2px}
.toggle .i-minus,.p1[data-view=large] .toggle .i-plus{display:none}
.p1[data-view=large] .toggle .i-minus{display:block}

/* ===== Condensed view: everything on one screen ===== */
.view-c{max-width:var(--col);margin:0 auto;height:100dvh;min-height:720px;padding:calc(var(--bar) + 12px) 16px 16px;gap:12px;
  grid-template-rows:auto minmax(0,.74fr) minmax(0,1.3fr) minmax(0,1.38fr)}
.view-c a.card:hover,.view-c a.card:focus-visible{transform:scale(1.03);background:var(--tile-hover);border-color:var(--tile-border-hover);z-index:1}
.c-matchup{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.c-side{display:flex;align-items:center;justify-content:center;gap:8px}
.c-side .abbr{font-size:24px}
.c-side img{display:block}

/* Game info: content pulled in from the edges, centered vertically */
a.card.c-game{padding:0 clamp(22px,7%,32px);display:flex;flex-direction:column;justify-content:center;gap:clamp(10px,1.6vh,20px);overflow:hidden}
.c-game .time{font-size:clamp(32px,4.6vh,46px)} .c-game .time small{font-size:13px}
.c-game .date{font-size:clamp(18px,2.6vh,25px);margin-top:3px}
.c-game .network{font-size:13px;margin-top:8px}
.c-game .city{font-size:14px;padding-left:0}
.c-game .temp{font-size:clamp(26px,3.8vh,32px)}
.c-game .weather{gap:8px} .c-game .weather svg{width:36px;height:27px}

/* Team cards: centered column — trend + record, 3 injuries, spaced ranks */
.c-teams{display:grid;grid-template-columns:1fr 1fr;gap:12px;min-height:0}
a.card.c-team{padding:clamp(12px,2vh,20px) 10px;display:flex;flex-direction:column;align-items:center;justify-content:space-evenly;text-align:center;overflow:hidden;min-width:0}
.c-rec{display:flex;align-items:center;gap:9px}
.c-team .record{font-size:clamp(38px,5.4vh,46px);font-weight:900;line-height:1;letter-spacing:-.01em}
.trend{flex:none;display:block}
.t-w{color:var(--win)} .t-l{color:var(--loss)} .t-t{color:var(--tie)}
.c-inj{font-size:12px;line-height:1.45;max-width:100%}
.c-inj li{justify-content:center}
.cranks{display:grid;grid-template-columns:auto auto;column-gap:clamp(16px,5vw,34px)}
.ccol{display:grid;grid-template-columns:auto auto;column-gap:4px;row-gap:clamp(3px,.8vh,8px);align-items:baseline}
.ccol h3{grid-column:1/-1;font-size:13px;font-weight:700;margin-bottom:1px;text-align:center}
.crank{display:contents}
.crank b{font-size:clamp(21px,2.9vh,27px);font-weight:900;line-height:1;text-align:right}
.crank sup{font-size:10px;font-weight:900;vertical-align:top;position:relative;top:.15em;margin-left:1px}
.crank span{font-size:9px;font-weight:300;letter-spacing:.05em;text-align:left}

/* Leaders: bigger numbers, columns pulled toward the center, league-rank crowns */
a.card.c-cmp{display:flex;align-items:center;justify-content:center;padding:clamp(10px,1.6vh,16px) 0;overflow:hidden}
.c-cmp-in{width:84%;height:100%;display:flex;flex-direction:column;justify-content:space-evenly}
.c-cmp .cmp-row{grid-template-columns:1fr 76px 1fr}
.c-cmp .ldr-v{position:relative;display:inline-block;font-size:clamp(18px,2.65vh,26px);font-weight:700;line-height:1.05}
.c-cmp .ldr-n{font-size:11.5px;margin-top:1px}
.c-cmp .cmp-lbl{font-size:10px}
.crown{position:absolute;left:100%;top:50%;transform:translate(4px,-62%);overflow:visible}

/* ===== Large view: one card per screen ===== */
.deck{position:fixed;inset:var(--bar) 0 0;overflow-y:auto;overscroll-behavior:contain;scroll-snap-type:y mandatory;scrollbar-width:none;padding:calc(var(--peek) + var(--gap)) 0}
.deck::-webkit-scrollbar{display:none}
.slot{height:100%;min-height:520px;max-width:var(--col);margin:0 auto var(--gap);padding:0 16px;scroll-snap-align:center;scroll-snap-stop:always}
.slot:last-child{margin-bottom:0}
.slot a.card{height:100%;overflow:hidden;transition:transform .35s cubic-bezier(.2,.7,.2,1),border-color .25s,background-color .25s}
.body{height:100%;display:flex;flex-direction:column;transition:opacity .25s}
.slot.active a.card{transition:transform .16s,background-color .16s,border-color .16s}
.slot.active a.card:hover,.slot.active a.card:focus-visible{transform:scale(1.03);background:var(--tile-hover);border-color:var(--tile-border-hover)}
.slot:not(.active) a.card{border-color:var(--tile-border-soft);transform:scale(.96)}
.slot:not(.active) .body{opacity:0}
.peek{position:absolute;left:0;right:0;height:calc(var(--peek) - 1px);display:flex;align-items:center;justify-content:center;gap:7px;font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--text-2);opacity:0;transition:opacity .25s;pointer-events:none}
.peek-top{top:0}.peek-bot{bottom:0}
.slot.below .peek-top,.slot.above .peek-bot{opacity:1}
.slot.below a.card:hover,.slot.above a.card:hover{border-color:var(--tile-border-hover);background:var(--tile-hover)}
.slot.below a.card:hover .peek,.slot.above a.card:hover .peek{color:#000}
.dots{display:none;position:fixed;right:10px;top:calc(var(--bar) + (100% - var(--bar)) / 2);transform:translateY(-50%);z-index:10}
.dots{flex-direction:column;gap:8px}
.p1[data-view=large] .dots{display:flex}
.dot{width:6px;height:6px;border-radius:3px;border:0;background:#CFCFCF;cursor:pointer;padding:0;transition:height .25s,background-color .25s}
.dot.on{height:18px;background:#000}
@media (min-width:680px){.dots{right:calc(50% - 300px - 22px)}}

.game .body{padding:40px 24px 32px;justify-content:space-between}
.game-top{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}
.time{white-space:nowrap;font-size:63px;font-weight:700;line-height:1;letter-spacing:-.01em}
.time small{font-size:16px;font-weight:400;letter-spacing:0;margin-left:6px}
.date{white-space:nowrap;font-size:34px;font-weight:700;line-height:1.15;margin-top:4px}
.network{font-size:16px;margin-top:40px;text-align:right;min-width:0}
.game-bottom{display:flex;justify-content:space-between;align-items:center}
.city{font-size:18px;padding-left:8px}
.weather{display:flex;align-items:center;gap:14px}
.temp{font-size:43px;font-weight:700;line-height:1}

.team .body{padding:28px 0 30px;justify-content:space-evenly;align-items:center}
.team .body>*{width:min(272px,calc(100% - 80px))}
.l-top{display:flex;align-items:center;justify-content:space-between;gap:12px}
.l-id{display:flex;flex-direction:column;align-items:center;gap:2px}
.l-id .abbr{font-size:30px}
.l-id img,.l-id-s img{display:block}
.l-rec{display:flex;align-items:center;gap:12px}
.l-rec .trend{width:28px;height:19px}
.team .record{font-size:70px;font-weight:900;line-height:1;letter-spacing:-.01em}
.l-inj{list-style:none;display:flex;flex-direction:column;gap:9px;font-size:15px;line-height:1.2}
.l-inj li{display:flex;justify-content:space-between;align-items:baseline;gap:12px;white-space:nowrap}
.l-inj .inj-name{font-weight:700;overflow:hidden;text-overflow:ellipsis}
.l-inj .inj-s{font-weight:700;flex:none}
.l-inj .inj-none{font-weight:400;justify-content:center}
.injuries{list-style:none;font-weight:700;min-width:0}
.team .injuries{font-size:16px;line-height:1.3}
.injuries li{display:flex;gap:5px;white-space:nowrap}
.inj-name{overflow:hidden;text-overflow:ellipsis}
.inj-s{flex:none}
.inj-out{color:var(--out)}.inj-doubt{color:var(--doubt)}.inj-ques{color:var(--ques)}
.inj-none{font-weight:400}
.ranks{display:grid;grid-template-columns:1fr 1fr}
.rank-col{display:flex;flex-direction:column;align-items:center;gap:12px}
.rank-col h3{font-size:24px;font-weight:700;line-height:1.2}
.rank{display:grid;grid-template-columns:auto auto;grid-template-rows:auto auto;column-gap:3px;align-items:start;width:112px}
.rank-n{grid-row:1/3;font-size:44px;font-weight:900;line-height:1;text-align:right;min-width:52px}
.rank-sfx{font-size:16px;font-weight:900;line-height:1;padding-top:3px}
.rank-lbl{font-size:12px;font-weight:300;line-height:1;align-self:end;padding-bottom:4px;letter-spacing:.02em}

.compare .body{padding:18px 0 20px;justify-content:space-evenly;align-items:center}
.compare .body>.cmp-row{width:90%}
.compare .cmp-row{grid-template-columns:1fr 84px 1fr}
.cmp-row{display:grid;grid-template-columns:1fr 104px 1fr;align-items:center}
.cmp-head .l-id-s{display:flex;flex-direction:column;align-items:center;gap:2px}
.cmp-head .abbr{font-size:20px}
.ldr{text-align:center;min-width:0}
.ldr-v{font-size:20px;font-weight:700;line-height:1.2}
.compare .ldr-v{position:relative;display:inline-block;font-size:clamp(28px,8.2vw,36px);line-height:1.05}
.compare .ldr-v .crown{width:20px;height:16px;transform:translate(5px,-64%)}
.compare .ldr-n{margin-top:2px}
.ldr-n{font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ldr-n .pos{font-weight:200}
.cmp-lbl{font-size:12px;text-align:center;line-height:1.2}

@media (max-width:400px){.view-l .time{font-size:54px}.view-l .date{font-size:29px}.team .record{font-size:62px}
  .game .body{padding-left:16px;padding-right:16px}.team .body>*{width:min(272px,calc(100% - 64px))}}
@media (max-height:700px){.p1{--peek:28px}.l-id img{width:64px;height:64px}}
@media (prefers-reduced-motion:reduce){a.card,.slot.active a.card{transition:background-color .16s,border-color .16s!important}.body,.peek,.dot,.toggle{transition:none!important}
  .view-c a.card:hover,.slot.active a.card:hover,.slot:not(.active) a.card{transform:none}}
/* ===== Production additions (not in the preview) ===== */
/* Finished games: final score replaces the kickoff time (Inter Black like Page 0's scores) */
.final-score{font-weight:900;letter-spacing:-.02em;font-variant-numeric:tabular-nums;display:flex;align-items:baseline}
.final-score .sc.lose{opacity:.3}
.final-score .sc-dash{padding:0 .12em;font-weight:400;opacity:.35}
.final-label{font-weight:700;letter-spacing:.04em}
a.card{cursor:pointer}
.temp-word{font-size:26px}
.c-game .temp-word{font-size:clamp(18px,2.6vh,22px)}
.temp-na,.rank-n.na,.crank b.na,.ldr-v.na{color:var(--text-3)}
.inj-none{color:var(--text-2)}
.l-inj .inj-none{font-weight:400}

"""
