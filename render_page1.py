"""
Page 1 -- the matchup page. One standalone file per game: site/game/<game_id>.html

Design = Jason's approved v8 preview (2026-09-16):
  - two views of the same page, switched with the +/− button in the top bar
      * expanded (default every time the page opens): pinned top bar with
        mini helmets + AWAY @ HOME, and a pinned bottom bar with "‹ Week N"
        and the +/− toggle (moved to the bottom 2026-09-17); one card per screen that
        snaps while scrolling, slivers of the cards above/below with a label,
        position dots on the right
      * condensed: every card on one screen, same top bar
  - finished games: final score in the top bar next to each abbreviation (loser
    faded), and the Leaders card shows each team's leaders in THAT game, no crowns
  - cards: Game Info, away team, home team, Leaders
  - team cards: last-game arrow (green up = W, red down = L, yellow line = T),
    record, top 3 injuries (starters first), offense/defense ranks
  - leaders: each team's leader in 5 stats, crown when top 3 in the league
  - cards, borders, hover, top bar, week pill, 600px column, Bold abbreviations
    all match Page 0

How it opens from Page 0: render_html.py adds a script to index.html that zooms
into the tapped tile, flies its helmets/abbreviations/scores up into this page's
top bar, then brings the cards in. It fetches this file and shows its .p1 block
inside a shadow root (so Page 0's CSS and Page 1's CSS can't clash). Swiping
left/right moves between the week's games; pinching in minimizes back into the tile.
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

def fmt_when(d):
    """Two lines for the expanded header: ('MON OCT 19', '8:15 PM ET')."""
    t, ampm = fmt_time(d.get("gametime"))
    try:
        day = date.fromisoformat(str(d.get("gameday"))[:10])
        when = f"{DAY_NAMES[day.weekday()][:3].upper()} {MONTHS_UPPER[day.month - 1]} {day.day}"
    except (TypeError, ValueError):
        when = "DATE TBD"
    return when, (f"{t} {ampm}".strip() if t != "TBD" else "TIME TBD")


def game_body(d, hero=""):
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
    return (
        '<div class="game-top">'
        f'<div>{headline}<div class="date">{esc(fmt_date(d.get("gameday")))}</div></div>'
        f'{corner}</div>'
        f'{hero}'
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


# Offense/defense rank colors (Jason, 2026-09-17, revised): green #1E8A3C for 1st through grey
# #6E6E6E to red #A00000 for 32nd, weighted instead of even steps. Top 5 / bottom 5 carry almost
# the full green / red, ranks 6-10 and 23-27 a clearly lighter tint, and the middle 12 (11-22)
# stay close to grey with only small differences. Blended in OKLab; every color is 4.4:1 or
# better on white.
RANK_COLORS = [
    "#1E8A3C", "#27893F", "#2E8842", "#348645", "#3A8548",   # 1-5
    "#498052", "#4F7E55", "#537C59", "#577B5C", "#5B795E",   # 6-10
    "#637565", "#657466", "#677268", "#69716A", "#6B706C", "#6D6F6D",   # 11-16
    "#706D6C", "#736A69", "#766865", "#786562", "#7B635E", "#7E605B",   # 17-22
    "#86564F", "#895149", "#8C4D44", "#8F473D", "#924136",   # 23-27
    "#992D23", "#9B261D", "#9D1E15", "#9E130C", "#A00000",   # 28-32
]


def rank_color(n):
    return RANK_COLORS[max(1, min(len(RANK_COLORS), n)) - 1]


def big_rank(n, label):
    """Rank number + ordinal colored on the green-to-red scale; POINTS/YARDS label stays black.
    Used on the expanded team cards and (smaller, via CSS) on the condensed ones."""
    if not isinstance(n, int):
        return f'<div class="rank"><span class="rank-n na">{DASH}</span><span class="rank-sfx"></span><span class="rank-lbl">{label}</span></div>'
    c = rank_color(n)
    return (f'<div class="rank"><span class="rank-n" style="color:{c}">{n}</span>'
            f'<span class="rank-sfx" style="color:{c}">{ordinal(n)}</span><span class="rank-lbl">{label}</span></div>')


def record_block(side, final):
    """
    Record with its last-game indicator (Jason, 2026-09-17):
      - finished game: the indicator sits on the column this game changed -- green
        chevron above the wins, red chevron under the losses, yellow bar under the
        ties -- and that number takes the same color
      - upcoming game: the current streak length, colored like its indicator, beside
        the record; green chevron above the number for a win streak, red chevron /
        yellow bar below it for a losing / tie streak
    """
    rec = side.get("record") or {}
    text = fmt_record(rec)
    size = record_size(text)
    last = side.get("last")
    if final and last in TREND:
        col = {"W": 0, "L": 1, "T": 2}[last]
        vals = [rec.get("wins", 0), rec.get("losses", 0)] + ([rec.get("ties", 0)] if rec.get("ties") else [])
        parts = []
        for i, v in enumerate(vals):
            if i:
                parts.append('<span class="rc-dash">-</span>')
            if i == col:
                where = "above" if last == "W" else "below"
                parts.append(f'<span class="rc rc-hit t-{last.lower()}">{v}<span class="rc-mark {where}">{TREND[last]}</span></span>')
            else:
                parts.append(f'<span class="rc">{v}</span>')
        return f'<span class="record rec-split{size}" aria-label="Record {esc(text)}">{"".join(parts)}</span>'
    streak = side.get("streak") or 0
    if last in TREND and streak:
        mark = TREND[last]
        inner = f'{mark}<b>{streak}</b>' if last == "W" else f'<b>{streak}</b>{mark}'
        word = {"W": "win", "L": "losing", "T": "tie"}[last]
        return (f'<span class="streak t-{last.lower()}" role="img" aria-label="{streak}-game {word} streak">{inner}</span>'
                f'<span class="record{size}">{esc(text)}</span>')
    return f'<span class="record{size}">{esc(text)}</span>'


def record_size(record_text):
    """Longer records ("10-6", "2-2-1", "10-6-1") get a smaller size class so they fit next to the helmet."""
    n = len(record_text)
    return "" if n <= 3 else " rec-4" if n == 4 else " rec-5" if n == 5 else " rec-6"


def team_pill(team):
    """A flat pill in the team's helmet-shell color (the PRIMARY color in helmets.py, no gradient)."""
    primary, _secondary = helmets.TEAM_COLORS.get(team, helmets.FALLBACK_COLORS)
    return f'<span class="pill" style="background:{primary}" role="img" aria-label="{esc(TEAM_NAMES.get(team, team))}"></span>'


def pill_row(a, h):
    """Leaders card column heads: away team's pill over the left column, home team's over the right."""
    return f'<div class="cmp-row cmp-head">{team_pill(a)}<div></div>{team_pill(h)}</div>'


def card_title(name):
    """The card's name at the top center of the card -- the same label its peeking sliver shows."""
    return f'<span class="card-title">{esc(name)}</span>'


def c_team(side, label, final=False):
    r = side.get("ranks") or {}
    team = side.get("team")
    rec = fmt_record(side.get("record"))
    return (
        f'<a class="card c-team" tabindex="0" data-detail="{label}-team" aria-label="{esc(team)} team">'
        f'{card_title(team)}'
        '<div class="l-top">'
        f'<div class="l-id">{helmet_img(team, 40)}</div>'
        f'<div class="l-rec">{record_block(side, final)}</div>'
        "</div>"
        f'<ul class="injuries c-inj">{injuries_html(side, full=False)}</ul>'
        '<div class="ranks">'
        f'<div class="rank-col"><h3>Offense</h3>{big_rank(r.get("off_points"), "PTS")}{big_rank(r.get("off_yards"), "YDS")}</div>'
        f'<div class="rank-col"><h3>Defense</h3>{big_rank(r.get("def_points"), "PTS")}{big_rank(r.get("def_yards"), "YDS")}</div>'
        "</div></a>"
    )


def l_team(side, final=False):
    r = side.get("ranks") or {}
    team = side.get("team")
    return (
        '<div class="l-top">'
        f'<div class="l-id">{helmet_img(team, 84)}</div>'
        f'<div class="l-rec">{record_block(side, final)}</div>'
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
        f'<div class="ldr"><div class="ldr-v"><span>{esc(fmt_value(p.get("value"))).replace(",", "<i class=cm>,</i>")}</span>{crown(p.get("league_rank"))}</div>'
        f'<div class="ldr-n"><span class="nm">{esc(p.get("name") or "")}</span><span class="pos">{esc(p.get("position") or "")}</span></div></div>'
    )


def leader_rows(d):
    return "".join(
        f'<div class="cmp-row">{leader_cell(row.get("away"))}'
        f'<div class="cmp-lbl">{esc(row.get("label", "")).replace(" ", "<br>")}</div>'
        f'{leader_cell(row.get("home"))}</div>'
        for row in d.get("leaders") or []
    )


# ---------------------------------------------------------------- page

def header_scores(d):
    """Finished game -> (away_html, home_html) score spans for the header, loser faded like Page 0. Else ('', '')."""
    score = d.get("score") if d.get("final") else None
    if not score:
        return "", ""
    a_s, h_s = score.get("away"), score.get("home")
    a_cls = h_cls = "hscore"
    try:
        if float(a_s) > float(h_s):
            h_cls += " lose"
        elif float(h_s) > float(a_s):
            a_cls += " lose"
    except (TypeError, ValueError):
        pass
    return (f'<span class="{a_cls}">{esc(fmt_value(a_s))}</span>', f'<span class="{h_cls}">{esc(fmt_value(h_s))}</span>')


def render_p1_block(d, prefix="../"):
    """The <div class="p1"> block (shared by the standalone page and the Page 0 overlay)."""
    away, home = d.get("away") or {}, d.get("home") or {}
    a, h = away.get("team") or "TBD", home.get("team") or "TBD"
    week_href = f"{prefix}index.html#week-{d.get('week_key')}"
    week_label = d.get("week_label") or ""
    rows = leader_rows(d)
    img = lambda team, size, mir=False: helmet_img(team, size, mir, prefix)
    a_score, h_score = header_scores(d)
    game_scope = d.get("leaders_scope") == "game"
    final = bool(d.get("final"))
    leaders_name = "Game Leaders" if game_scope else "Leaders"

    when_day, when_time = fmt_when(d)
    # One header row, drawn twice (top bar + the middle of the Game Info card) and morphed between the two.
    # Each team is a unit: helmet plus its abbreviation (and final score) — side by side when condensed,
    # stacked and pushed to the edges of the screen in the expanded view (2026-09-17).
    row = (
        f'<div class="side away">{img(a, 44)}<span class="abbr">{esc(a)}</span>{a_score}</div>'
        f'<div class="mid"><span class="at">@</span>'
        f'<span class="when"><span>{esc(when_day)}</span><span>{esc(when_time)}</span></span>'
        f'<span class="final-lbl">{"FINAL/OT" if d.get("overtime") else "FINAL"}</span></div>'
        f'<div class="side home">{h_score}<span class="abbr">{esc(h)}</span>{img(h, 44, True)}</div>'
    )
    hero = f'<div class="hero" aria-hidden="true"><div class="teams">{row}</div></div>'
    bar = (
        '<header class="bar"><div class="bar-in">'
        f'<div class="teams" aria-label="{esc(TEAM_NAMES.get(a, a))} at {esc(TEAM_NAMES.get(h, h))}">{row}</div>'
        "</div></header>"
        # back button + view toggle live at the bottom of the screen (2026-09-17)
        '<nav class="bbar" aria-label="Page controls"><div class="bbar-in">'
        f'<a class="week" href="{esc(week_href)}">{CHEV}<span>{esc(week_label)}</span></a>'
        f'<button class="toggle" type="button"><span class="i-plus">{PLUS}</span><span class="i-minus">{MINUS}</span></button>'
        "</div></nav>"
    )
    condensed = (
        '<div class="view view-c" aria-label="Condensed matchup">'
        f'<a class="card c-game" tabindex="0" data-detail="game-info" aria-label="Game info">{card_title("Game Info")}{game_body(d)}</a>'
        f'<div class="c-teams">{c_team(away, "away", final)}{c_team(home, "home", final)}</div>'
        f'<a class="card c-cmp" tabindex="0" data-detail="leaders" aria-label="{leaders_name}">{card_title(leaders_name)}<div class="c-cmp-in">{pill_row(a, h)}{rows}</div></a>'
        "</div>"
    )
    cmp_head = pill_row(a, h)  # team-color pills replace the helmets + abbreviations (2026-09-17)
    cards = [("game-info", "Game Info", "game", game_body(d, hero)),
             ("away-team", a, "team", l_team(away, final)),
             ("home-team", h, "team", l_team(home, final)),
             ("leaders", leaders_name, "compare", cmp_head + rows)]
    slots = "".join(
        f'<section class="slot"><a class="card {kind}" tabindex="-1" data-detail="{cid}" aria-label="{esc(name)}">'
        f'<span class="peek peek-top">{DOWN}<span>{esc(name)}</span></span><div class="body">{body}</div>'
        f'<span class="peek peek-bot">{UP}<span>{esc(name)}</span></span></a></section>'
        for cid, name, kind, body in cards
    )
    dots = "".join(f'<button class="dot" type="button" aria-label="{esc(name)}"></button>' for _c, name, _k, _b in cards)
    large = f'<div class="view view-l deck" aria-label="Expanded matchup">{slots}</div><nav class="dots" aria-label="Cards">{dots}</nav>'
    return (f'<div class="p1" data-view="large" data-head="card"{" data-final" if final else ""} '
            f'data-game="{esc(d.get("game_id"))}">{bar}{condensed}{large}</div>')


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
      week = root.querySelector('.week'), active = -1, bound = [], morphing = false;
  // Motion always plays, whatever the device's Reduce Motion setting (Jason, 2026-09-17).
  // Speed/easing taken from yeezy.com: 200-300ms moves on cubic-bezier(.22,1,.36,1), 150ms fades.
  var reduce = false;
  var smooth = 'smooth', EASE = 'cubic-bezier(.22,1,.36,1)';
  var lastCard = Math.max(0, Math.min(slots.length - 1, opts.card || 0));  // expanded card to return to
  function on(t, type, fn, o) { t.addEventListener(type, fn, o); bound.push([t, type, fn, o]); }
  function large() { return wrap.getAttribute('data-view') === 'large'; }
  function setActive(i) {
    if (i === active) return; active = i; lastCard = i;
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
  // ---- header: in the Game Info card on the first card, condensing into the top bar as you scroll on (2026-09-17).
  // Every piece travels on its own (helmets, abbreviations, scores), because the three layouts arrange them
  // differently; the middle crossfades between the card's "@" and the bar's date and time.
  var barRow = root.querySelector('.bar .teams'), heroRow = root.querySelector('.hero .teams');
  var flyBox = null, flyAtoms = [], flyAt = null, flyWhen = null;
  function atoms(row) { return [].slice.call(row.querySelectorAll('img, .abbr, .hscore')); }
  function shown(el) { return !!(el && el.getClientRects().length); }
  function sizeOf(el) { return el.tagName === 'IMG' ? el.offsetWidth : parseFloat(getComputedStyle(el).fontSize) || 1; }
  function rectOf(el) { return el.getBoundingClientRect(); }
  function park(el, r) { Object.assign(el.style, { left: r.left + 'px', top: r.top + 'px', width: r.width + 'px', height: r.height + 'px' }); }
  function toward(el, r, from, e, scale) {
    // el is parked on its own rect r; put its centre e of the way from "from" to r, at the given scale
    var cx = from.left + from.width / 2 + (r.left + r.width / 2 - (from.left + from.width / 2)) * e;
    var cy = from.top + from.height / 2 + (r.top + r.height / 2 - (from.top + from.height / 2)) * e;
    el.style.transform = 'translate(' + (cx - r.left - r.width * scale / 2) + 'px,' + (cy - r.top - r.height * scale / 2) + 'px) scale(' + scale + ')';
  }
  function copyOf(src) {
    var c = src.cloneNode(true), cs = getComputedStyle(src);
    c.className = (src.className || '') + ' hf';
    c.style.fontSize = cs.fontSize;
    if (src.tagName === 'IMG') { c.style.width = src.offsetWidth + 'px'; c.style.height = src.offsetHeight + 'px'; }
    else c.style.display = src.classList.contains('when') ? 'flex' : 'block';   // the date keeps its two stacked lines
    return c;
  }
  if (barRow && heroRow) {
    flyBox = document.createElement('div');
    flyBox.className = 'teams head-fly';   // .teams so the copies keep the header's own styling
    flyBox.setAttribute('aria-hidden', 'true');
    atoms(barRow).forEach(function (el) { var c = copyOf(el); flyBox.appendChild(c); flyAtoms.push(c); });
    flyAt = copyOf(heroRow.querySelector('.at'));
    flyWhen = copyOf(barRow.querySelector(wrap.hasAttribute('data-final') ? '.final-lbl' : '.when'));
    flyBox.appendChild(flyAt);
    flyBox.appendChild(flyWhen);
    wrap.appendChild(flyBox);
  }
  function centerTop(s) { return s.offsetTop - (deck.clientHeight - s.offsetHeight) / 2; }
  function headProgress() {  // 0 with the Game Info card in the middle, 1 once the next card is
    if (slots.length < 2) return 0;
    var a = centerTop(slots[0]), step = centerTop(slots[1]) - a;
    return step > 0 ? Math.max(0, Math.min(1, (deck.scrollTop - a) / step)) : 0;
  }
  function setHead(mode) { if (wrap.getAttribute('data-head') !== mode) wrap.setAttribute('data-head', mode); }
  function updateHead() {
    if (!flyBox || !large()) return;
    var p = headProgress(), e = 1 - (1 - p) * (1 - p);  // ease-out: the header settles before the next card does
    if (p <= 0.001) { setHead('card'); return; }
    if (p >= 0.999) { setHead('bar'); return; }
    var ba = atoms(barRow), ha = atoms(heroRow);
    if (!ba.length || rectOf(ba[0]).width === 0) return;
    ba.forEach(function (el, k) {
      var f = flyAtoms[k], src = ha[k];
      if (!f || !src) return;
      var r = rectOf(el), sc = sizeOf(src) / sizeOf(el);
      park(f, r);
      toward(f, r, rectOf(src), e, sc + (1 - sc) * e);
    });
    var at = heroRow.querySelector('.at'), when = barRow.querySelector(wrap.hasAttribute('data-final') ? '.final-lbl' : '.when');
    var scale = sizeOf(ha[0]) / sizeOf(ba[0]), mid = rectOf(barRow.querySelector('.mid'));
    if (shown(at)) {
      var ar = rectOf(at);
      park(flyAt, ar);
      toward(flyAt, ar, mid, 1 - e, 1 - (1 - 1 / scale) * e);   // shrinks with the units as it fades out
      flyAt.style.opacity = Math.max(0, 1 - e / 0.5);
      flyAt.style.display = 'block';
    } else flyAt.style.display = 'none';
    if (shown(when)) {
      var wr = rectOf(when);
      park(flyWhen, wr);
      toward(flyWhen, wr, mid, e, 1 + (scale - 1) * (1 - e));
      flyWhen.style.opacity = Math.max(0, (e - 0.6) / 0.4);
      flyWhen.style.display = when.classList.contains('when') ? 'flex' : 'block';
    } else flyWhen.style.display = 'none';
    setHead('moving');
  }
  function midPiece(row, mode) {  // the middle shows "@" in the card and when condensed, the date or FINAL in the expanded bar
    if (mode === 'card') return row.querySelector('.at');
    var el = row.querySelector(wrap.hasAttribute('data-final') ? '.final-lbl' : '.when');
    return shown(el) ? el : row.querySelector('.at');
  }
  function headShot() {  // where every header piece is right now, and which middle piece is showing
    var mode = large() ? wrap.getAttribute('data-head') : 'cond';
    var row = mode === 'card' ? heroRow : barRow;
    if (mode === 'moving') {
      var mv = flyAtoms.map(function (el) { return { rect: rectOf(el), size: sizeOf(el) * (el.tagName === 'IMG' ? 1 : 1) }; });
      return { mode: mode, row: barRow, list: mv, midEl: shown(flyAt) ? flyAt : flyWhen, mid: rectOf(shown(flyAt) ? flyAt : flyWhen) };
    }
    var mid = midPiece(row, mode);
    return {
      mode: mode, row: row,
      list: atoms(row).map(function (el) { return { rect: rectOf(el), size: sizeOf(el) }; }),
      midEl: shown(mid) ? mid : null, mid: shown(mid) ? rectOf(mid) : null
    };
  }
  function ghost(el, r) {  // a free copy of one piece, parked exactly on top of it
    var box = document.createElement('div'), c = copyOf(el);
    box.className = 'teams hf-box';
    Object.assign(box.style, { position: 'fixed', left: r.left + 'px', top: r.top + 'px', width: r.width + 'px', height: r.height + 'px',
      margin: '0', display: 'block', zIndex: '12', pointerEvents: 'none', transformOrigin: '0 0', fontSize: getComputedStyle(el).fontSize });
    Object.assign(c.style, { position: 'absolute', left: '0', top: '0' });
    box.appendChild(c);
    wrap.appendChild(box);
    return box;
  }
  function slide(g, from, to, scale, D, fade) {
    var a = { transform: 'translate(' + (from.left + from.width / 2 - to.left - to.width * scale / 2) + 'px,' +
                (from.top + from.height / 2 - to.top - to.height * scale / 2) + 'px) scale(' + scale + ')' },
        b = { transform: 'none' };
    if (fade) { a.opacity = fade[0]; b.opacity = fade[1]; }
    return g.animate([a, b], { duration: D, easing: EASE, fill: 'forwards' });
  }
  function flipHead(from, D) {  // the pieces fly between two header layouts when the view changes
    var to = headShot(), out = [];
    if (!from || !to.list.length || from.mode === to.mode) return out;
    atoms(to.row).forEach(function (el, k) {
      var r = to.list[k], f = from.list[k];
      if (!r || !f || !r.rect.width || !f.rect.width) return;
      var g = ghost(el, r.rect);
      el.style.visibility = 'hidden';
      out.push({ el: el, g: g, anim: slide(g, f.rect, r.rect, f.size / r.size, D) });
    });
    var ratio = to.list[0].size / from.list[0].size;
    if (to.midEl && to.mid) {   // the middle swaps content, so the new copy fades in on the way
      var gIn = ghost(to.midEl, to.mid);
      to.midEl.style.visibility = 'hidden';
      out.push({ el: to.midEl, g: gIn, anim: slide(gIn, from.mid || to.mid, to.mid, 1 / ratio, D, [0, 1]) });
    }
    if (from.midEl && from.mid) {   // ...and the old one fades out
      var gOut = ghost(from.midEl, from.mid);
      gOut.style.left = from.mid.left + 'px'; gOut.style.top = from.mid.top + 'px';
      var target = to.mid || from.mid;
      out.push({ g: gOut, anim: gOut.animate([{ transform: 'none', opacity: 1 },
        { transform: 'translate(' + (target.left + target.width / 2 - from.mid.left - from.mid.width * ratio / 2) + 'px,' +
          (target.top + target.height / 2 - from.mid.top - from.mid.height * ratio / 2) + 'px) scale(' + ratio + ')', opacity: 0 }],
        { duration: Math.round(D * 0.6), easing: EASE, fill: 'forwards' }) });
    }
    return out;
  }
  function endFlip(list) { list.forEach(function (o) { if (o.el) o.el.style.visibility = ''; o.g.remove(); }); }
  function visibleHead() { return large() && flyBox ? (wrap.getAttribute('data-head') === 'card' ? heroRow : wrap.getAttribute('data-head') === 'moving' ? flyBox : barRow) : barRow; }

  var ticking = false;
  on(deck, 'scroll', function () { if (!ticking && large() && !morphing) { ticking = true; requestAnimationFrame(function () { if (large()) { setActive(current()); updateHead(); } ticking = false; }); } }, { passive: true });
  // Tapping a peeking card brings it in; tapping the active card will open Page 2 later.
  slots.forEach(function (s, k) { on(s.querySelector('a.card'), 'click', function (e) { e.preventDefault(); if (k !== active) go(k); }); });
  dots.forEach(function (d, k) { on(d, 'click', function () { go(k); }); });

  // Condensed card for each expanded card: game info, away team, home team, leaders
  function condensedCards() { return [root.querySelector('.c-game')].concat([].slice.call(root.querySelectorAll('.c-team')), [root.querySelector('.c-cmp')]); }
  function labelToggle(v) {
    toggle.setAttribute('aria-label', v === 'large' ? 'Switch to condensed view' : 'Switch to expanded view');
    toggle.setAttribute('aria-pressed', v === 'large' ? 'true' : 'false');
  }
  function place(v, card) {
    wrap.setAttribute('data-view', v);
    labelToggle(v);
    if (v === 'large') { active = -1; go(card, true); setActive(card); updateHead(); }
  }
  // A plain card-shaped box holding a frozen copy of a card, used to morph between the two views.
  function morphFrom(el) {
    var r = el.getBoundingClientRect(), box = document.createElement('div'), copy = el.cloneNode(true);
    box.className = 'morph';
    Object.assign(box.style, { left: r.left + 'px', top: r.top + 'px', width: r.width + 'px', height: r.height + 'px' });
    copy.removeAttribute('tabindex');
    var h = copy.querySelector('.hero .teams'); if (h) h.style.visibility = 'hidden';
    Object.assign(copy.style, { width: r.width + 'px', height: r.height + 'px' });
    box.appendChild(copy);
    wrap.appendChild(box);
    return { box: box, copy: copy, r: r };
  }
  function geo(r) { return { left: r.left + 'px', top: r.top + 'px', width: r.width + 'px', height: r.height + 'px' }; }
  function fin(a) { return a.finished.catch(function () {}); }

  function switchView(v) {
    if (morphing || v === wrap.getAttribute('data-view')) return;
    var card = lastCard;
    if (reduce || !Element.prototype.animate) { place(v, card); return; }
    morphing = true;
    var toLarge = v === 'large', D = 300;
    var headFrom = headShot();
    var fromEl = toLarge ? condensedCards()[card] : slots[card].querySelector('a.card');
    var others = toLarge ? condensedCards().filter(function (_, k) { return k !== card; }) : [];
    var ghosts = others.map(function (el) { return morphFrom(el); });   // condensed neighbours zoom past and fade
    var m = morphFrom(fromEl);
    place(v, card);
    var toEl = toLarge ? slots[card].querySelector('a.card') : condensedCards()[card];
    var r1 = toEl.getBoundingClientRect();
    toEl.style.opacity = '0';
    var flips = flipHead(headFrom, D), anims = flips.map(function (o) { return o.anim; });
    anims.push(m.box.animate([geo(m.r), geo(r1)], { duration: D, easing: EASE, fill: 'forwards' }));
    m.copy.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 120, fill: 'forwards' });
    ghosts.forEach(function (g) {
      g.box.animate([{ transform: 'scale(1)', opacity: 1 }, { transform: 'scale(1.12)', opacity: 0 }], { duration: 160, easing: EASE, fill: 'forwards' });
    });
    if (toLarge) {
      // the peeking neighbours and dots arrive once the card has nearly filled its spot
      [slots[card - 1], slots[card + 1]].forEach(function (s) {
        if (s) s.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 150, delay: D - 90, easing: 'ease-out', fill: 'backwards' });
      });
      dots.forEach(function (d) { d.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 150, delay: D - 90, fill: 'backwards' }); });
    } else {
      // the other condensed cards settle into place from slightly larger, as if zooming out
      condensedCards().forEach(function (el, k) {
        if (k === card) return;
        el.animate([{ transform: 'scale(1.08)', opacity: 0 }, { transform: 'none', opacity: 1 }], { duration: 240, delay: 50, easing: EASE, fill: 'backwards' });
      });
    }
    Promise.all(anims.map(fin)).then(function () {
      toEl.style.opacity = '';
      var inAnim = toEl.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 120, easing: 'ease-out' });
      m.box.remove();
      ghosts.forEach(function (g) { g.box.remove(); });
      morphing = false;
      // the header copies stay put until the card around them has faded in
      fin(inAnim).then(function () { endFlip(flips); });
    });
  }
  on(toggle, 'click', function () { switchView(large() ? 'condensed' : 'large'); });
  function back() { if (opts.onBack) opts.onBack(); else location.href = week.href; }
  on(week, 'click', function (e) { if (opts.onBack) { e.preventDefault(); opts.onBack(); } });
  on(window, 'keydown', function (e) {
    if (e.key === 'Escape') { back(); return; }
    if (!large()) return;
    if (e.key === 'ArrowDown' || e.key === 'PageDown') { e.preventDefault(); go(active + 1); }
    else if (e.key === 'ArrowUp' || e.key === 'PageUp') { e.preventDefault(); go(active - 1); }
  });
  on(window, 'resize', function () { if (large()) { go(active, true); updateHead(); } });
  // Opens expanded unless told otherwise; opts.card keeps the same card when swiping between games.
  var startView = opts.view === 'condensed' ? 'condensed' : 'large';
  wrap.setAttribute('data-view', startView);
  labelToggle(startView);
  if (startView === 'large') { setHead(lastCard === 0 ? 'card' : 'bar'); requestAnimationFrame(function () { go(lastCard, true); setActive(lastCard); updateHead(); }); }
  return {
    view: function () { return wrap.getAttribute('data-view'); },
    card: function () { return lastCard; },
    head: visibleHead,
    destroy: function () { bound.forEach(function (b) { b[0].removeEventListener(b[1], b[2], b[3]); }); bound = []; }
  };
} };
"""

# ---------------------------------------------------------------- styles (ported 1:1 from the approved v8 preview)

P1_CSS = r"""
:host{display:block}
.p1{--ink:#000;--tile:#fff;--tile-border:rgba(0,0,0,.12);--tile-border-soft:rgba(0,0,0,.07);--tile-hover:rgba(0,0,0,.03);--tile-border-hover:rgba(0,0,0,.28);--text-2:rgba(0,0,0,.62);--text-3:rgba(0,0,0,.4);
  --out:#A00000;--doubt:#A52800;--ques:#B58900;--win:#1E8A3C;--loss:#A00000;--tie:#B58900;--gold:#D4A20A;--silver:#A2A7AD;--bronze:#B5702F;--bar:64px;--bbar:calc(52px + env(safe-area-inset-bottom));--peek:40px;--gap:12px;--col:600px;--ctitle:clamp(22px,3.2vh,30px)}
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
/* Bottom bar (2026-09-17): "‹ Week N" back button centered + the +/− toggle on the right, in the same
   spot and size as Page 0's bottom week picker */
.bbar{position:fixed;inset:auto 0 0;height:var(--bbar);padding-bottom:env(safe-area-inset-bottom);z-index:10;background:rgba(255,255,255,.94);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px)}
.bbar-in{position:relative;max-width:var(--col);height:52px;margin:0 auto;display:flex;align-items:flex-start;justify-content:center;padding-top:10px}
.week{color:inherit;text-decoration:none;display:inline-flex;align-items:center;gap:6px;font-size:16px;font-weight:400;line-height:19px;padding:6px 12px;border-radius:999px;transition:background-color .16s}
.week:hover{background:rgba(0,0,0,.05)}
.week:focus-visible{outline:2px solid #000;outline-offset:2px}
.week .chev{width:12px;height:12px}
/* The header row is sized in em so the same row can be drawn at any size and scale cleanly between them:
   20px in the condensed bar (44px helmets, unchanged), smaller in the expanded bar, larger in the Game Info card. */
.teams{display:flex;align-items:center;gap:.4em;font-size:20px}
.side,.mid{display:flex;align-items:center;gap:.4em}
.teams .abbr{font-size:1em}
.teams .at{font-size:.8em;padding:0 .25em}
.teams img{display:block;width:2.2em;height:2.2em}
.bar .teams{pointer-events:none}
.when{display:none;flex-direction:column;align-items:center;font-size:11px;font-weight:700;letter-spacing:.1em;line-height:1.35;color:var(--text-2);white-space:nowrap}
.final-lbl{display:none;font-size:16px;font-weight:700;letter-spacing:.04em;line-height:1.2;white-space:nowrap}   /* same as Page 0's FINAL */
/* ===== Expanded view header (2026-09-17) =====
   Game Info card: each team stacks — final score on top, then the helmet, then the abbreviation.
   Top bar, game still to come: helmet + abbreviation (abbreviation on the inside) at opposite edges of
   the screen, with the date and time in the middle.
   Top bar, game final: one line — away helmet, abbreviation, score, then the home score, abbreviation,
   helmet; the date and time aren't needed once a game is over. */
.p1[data-view=large] .hero .side{flex-direction:column;gap:.08em}
.p1[data-view=large] .hero .side img{order:2;width:2.6em;height:2.6em}
.p1[data-view=large] .hero .side .hscore{order:1;font-size:1.6em;margin-bottom:.14em}   /* the score sits high above the helmet */
.p1[data-view=large] .hero .side .abbr{order:3}
.p1[data-view=large] .bar .teams{font-size:17px;width:100%;padding:0 16px;justify-content:space-between}
.p1[data-view=large] .bar .side img{width:2.4em;height:2.4em}
.p1[data-view=large] .bar .at{display:none}
.p1[data-view=large]:not([data-final]) .bar .when{display:flex}
.p1[data-view=large][data-final] .bar .final-lbl{display:block}
/* which copy of the header shows in the expanded view: in the card (data-head=card), in the bar (bar),
   or neither while the moving copies (.head-fly) travel between them (moving) */
.p1[data-view=large][data-head=card] .bar .teams,.p1[data-view=large][data-head=card] .when{visibility:hidden}
.p1[data-view=large][data-head=bar] .hero .teams,.p1[data-view=large][data-head=moving] .hero .teams,.p1[data-view=large][data-head=moving] .bar .teams{visibility:hidden}
.head-fly{position:fixed;inset:0;display:block;margin:0;z-index:12;pointer-events:none}
.head-fly .hf{position:fixed;margin:0;transform-origin:0 0;will-change:transform,opacity}
.p1:not([data-view=large]) .head-fly,.p1[data-view=large]:not([data-head=moving]) .head-fly{display:none}
.toggle{position:absolute;right:16px;top:10px;width:32px;height:32px;border-radius:50%;border:1px solid var(--tile-border);background:#fff;color:#000;
  display:flex;align-items:center;justify-content:center;cursor:pointer;transition:transform .16s,background-color .16s,border-color .16s}
.toggle:hover{transform:scale(1.03);background:rgba(0,0,0,.05);border-color:var(--tile-border-hover)}
.toggle:focus-visible{outline:2px solid #000;outline-offset:2px}
.toggle .i-minus,.p1[data-view=large] .toggle .i-plus{display:none}
.p1[data-view=large] .toggle .i-minus{display:block}

/* ===== Condensed view: everything on one screen ===== */
.view-c{max-width:var(--col);margin:0 auto;height:100dvh;min-height:720px;padding:calc(var(--bar) + 12px) 16px calc(var(--bbar) + 12px);gap:12px;
  grid-template-rows:minmax(0,.74fr) minmax(0,1.3fr) minmax(0,1.38fr)}
.view-c a.card:hover,.view-c a.card:focus-visible{transform:scale(1.03);background:var(--tile-hover);border-color:var(--tile-border-hover);z-index:1}

/* Game info: content pulled in from the edges, centered vertically */
a.card.c-game{padding:var(--ctitle) clamp(22px,7%,32px) 6px;display:flex;flex-direction:column;justify-content:center;gap:clamp(10px,1.6vh,20px);overflow:hidden}
.c-game .time{font-size:clamp(32px,4.6vh,46px)} .c-game .time small{font-size:13px}
.c-game .date{font-size:clamp(18px,2.6vh,25px);margin-top:3px}
.c-game .network{font-size:13px;margin-top:8px}
.c-game .city{font-size:14px;padding-left:0}
.c-game .temp{font-size:clamp(26px,3.8vh,32px)}
.c-game .weather{gap:8px} .c-game .weather svg{width:36px;height:27px}

/* Team cards: centered column — trend + record, 3 injuries, spaced ranks */
.c-teams{display:grid;grid-template-columns:1fr 1fr;gap:12px;min-height:0}
a.card.c-team{padding:var(--ctitle) 10px clamp(8px,1.4vh,14px);display:flex;flex-direction:column;align-items:center;justify-content:space-evenly;text-align:center;overflow:hidden;min-width:0;container-type:inline-size}
/* helmet + abbreviation left, last-game arrow + record right -- same as the expanded card (2026-09-17) */
.c-team .l-top{width:100%;display:flex;align-items:center;justify-content:center;gap:10px;padding:0 2px}
.c-team .l-id{gap:1px}
.c-team .l-id img{width:clamp(28px,4.2vh,40px);height:clamp(28px,4.2vh,40px);display:block}
.c-team .l-id .abbr{font-size:12px}
.c-team .l-rec{gap:6px;min-width:0}
.c-team .streak{gap:1px}
.c-team .streak b{font-size:clamp(12px,1.7vh,15px)}
.c-team .streak .trend{width:12px;height:8px}
.c-team .l-top{padding-top:10px;padding-bottom:8px}
.c-team .record{font-weight:900;line-height:1;letter-spacing:-.01em;white-space:nowrap;
  font-size:clamp(28px,4.4vh,42px);font-size:min(clamp(28px,4.4vh,42px),calc((100cqi - 92px) / 1.8))}
.c-team .record.rec-4{font-size:30px;font-size:min(clamp(24px,4vh,38px),calc((100cqi - 92px) / 2.4))}
.c-team .record.rec-5{font-size:26px;font-size:min(clamp(22px,3.6vh,34px),calc((100cqi - 92px) / 2.85))}
.c-team .record.rec-6{font-size:22px;font-size:min(clamp(20px,3.2vh,30px),calc((100cqi - 92px) / 3.5))}
.trend{flex:none;display:block}
.t-w{color:var(--win)} .t-l{color:var(--loss)} .t-t{color:var(--tie)}
.rc-hit.t-w,.rc-hit.t-l,.rc-hit.t-t{font:inherit}
.c-inj{font-size:12px;line-height:1.45;max-width:100%}
.c-inj li{justify-content:center}
/* condensed ranks use the expanded layout: ordinal top-right of the number, PTS/YDS under it */
.c-team .ranks{column-gap:clamp(12px,4cqi,26px)}
.c-team .rank-col{gap:clamp(2px,.7vh,7px)}
.c-team .rank-col h3{font-size:13px}
.c-team .rank{width:auto;column-gap:2px}
.c-team .rank-n{font-size:clamp(21px,2.9vh,27px);min-width:1.25em}
.c-team .rank-sfx{font-size:10px;padding-top:1px}
.c-team .rank-lbl{font-size:9px;padding-bottom:2px;letter-spacing:.05em}

/* Leaders: bigger numbers, columns pulled toward the center, league-rank crowns */
a.card.c-cmp{display:flex;align-items:center;justify-content:center;padding:var(--ctitle) 0 clamp(8px,1.4vh,14px);overflow:hidden}
.c-cmp-in{width:84%;height:100%;display:flex;flex-direction:column;justify-content:space-evenly}
.c-cmp .cmp-row{grid-template-columns:1fr 76px 1fr}
.c-cmp .ldr-v{position:relative;display:inline-block;font-size:clamp(18px,2.65vh,26px);font-weight:700;line-height:1}
.c-cmp .ldr-n{font-size:11.5px;line-height:1.1;margin-top:-1px}   /* the name hugs its own stat; the gap to the next row stays larger */
.cm{font-style:normal}
.c-cmp .cm{position:relative;top:-.1em}   /* lift thousands commas so their tails clear the name below */
.c-cmp .cmp-lbl{font-size:10px}
.crown{position:absolute;left:100%;top:50%;transform:translate(4px,-62%);overflow:visible}

/* ===== Large view: one card per screen ===== */
.deck{position:fixed;inset:var(--bar) 0 var(--bbar);overflow-y:auto;overscroll-behavior:contain;scroll-snap-type:y mandatory;scrollbar-width:none;padding:calc(var(--peek) + var(--gap)) 0}
.deck::-webkit-scrollbar{display:none}
.slot{height:100%;min-height:520px;max-width:var(--col);margin:0 auto var(--gap);padding:0 16px;scroll-snap-align:center;scroll-snap-stop:always}
.slot:last-child{margin-bottom:0}
.slot a.card{height:100%;overflow:hidden;transition:transform .2s cubic-bezier(.22,1,.36,1),border-color .15s,background-color .15s}
.body{height:100%;display:flex;flex-direction:column;transition:opacity .15s}
.slot.active a.card{transition:transform .16s,background-color .16s,border-color .16s}
.slot.active a.card:hover,.slot.active a.card:focus-visible{transform:scale(1.03);background:var(--tile-hover);border-color:var(--tile-border-hover)}
.slot:not(.active) a.card{border-color:var(--tile-border-soft);transform:scale(.96)}
.slot:not(.active) .body{opacity:0}
.peek{position:absolute;left:0;right:0;height:calc(var(--peek) - 1px);display:flex;align-items:center;justify-content:center;gap:7px;font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--text-2);opacity:0;transition:opacity .15s;pointer-events:none}
.peek-top{top:0}.peek-bot{bottom:0}
.slot.below .peek-top,.slot.above .peek-bot{opacity:1}
/* the card in the middle keeps its name at the top, where its sliver showed it (no arrow) */
.slot.active .peek-top{opacity:1}
.slot.active .peek-top svg{display:none}
.slot.below a.card:hover,.slot.above a.card:hover{border-color:var(--tile-border-hover);background:var(--tile-hover)}
.slot.below a.card:hover .peek,.slot.above a.card:hover .peek{color:#000}
.dots{display:none;position:fixed;right:calc(max(16px,(100vw - var(--col)) / 2 + 16px) / 2 - 3px);top:calc(var(--bar) + (100% - var(--bar) - var(--bbar)) / 2);transform:translateY(-50%);z-index:10}
.dots{flex-direction:column;align-items:center;gap:8px}
.p1[data-view=large] .dots{display:flex}
.dot{width:6px;height:6px;border-radius:3px;border:0;background:#CFCFCF;cursor:pointer;padding:0;transition:height .2s,background-color .2s}
.dot.on{height:18px;background:#000}
@media (min-width:680px){.dots{right:calc(50% - 300px - 22px)}}

.game .body{padding:44px 24px 32px;justify-content:space-between;container-type:inline-size}
/* the header, big, in the middle of the Game Info card; sized to fit the card (a final-score row is ~15.5em wide) */
.hero{display:flex;justify-content:center}
.hero .teams{gap:.5em;font-size:min(38px,12cqi)}   /* the stacked row is ~7.5em wide, so it can fill the card */
.game-top{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}
.time{white-space:nowrap;font-size:63px;font-weight:700;line-height:1;letter-spacing:-.01em}
.time small{font-size:16px;font-weight:400;letter-spacing:0;margin-left:6px}
.date{white-space:nowrap;font-size:34px;font-weight:700;line-height:1.15;margin-top:4px}
.network{font-size:16px;margin-top:40px;text-align:right;min-width:0}
.game-bottom{display:flex;justify-content:space-between;align-items:center}
.city{font-size:18px;padding-left:8px}
.weather{display:flex;align-items:center;gap:14px}
.temp{font-size:43px;font-weight:700;line-height:1}

.team .body{padding:44px 0 30px;justify-content:space-evenly;align-items:center}
.team .body>*{width:min(272px,calc(100% - 80px))}
.l-top{display:flex;align-items:center;justify-content:center;gap:28px}
.l-id{display:flex;flex-direction:column;align-items:center;gap:2px}
.l-id .abbr{font-size:30px}
.l-id img,.l-id-s img{display:block}
.l-rec{display:flex;align-items:center;gap:12px}
.l-rec .trend{width:28px;height:19px}
/* upcoming: streak number with its indicator (chevron above a win streak, chevron/bar below the others) */
.streak{display:flex;flex-direction:column;align-items:center;gap:2px;flex:none;line-height:1}
.streak b{font-size:22px;font-weight:900;line-height:1;font-variant-numeric:tabular-nums}
.streak .trend{width:18px;height:12px}
/* finished: indicator sits on the column this game changed, and that number takes its color */
.rec-split{display:inline-flex;align-items:baseline}
.rc{position:relative;display:inline-block}
.rc-mark{position:absolute;left:50%;transform:translateX(-50%);line-height:0}
/* the same clear ~.12em gap above or below the digit (the line box leaves .115em of space above the numerals and .145em below) */
.rc-mark.above{bottom:calc(100% + .005em)}
.rc-mark.below{top:calc(100% - .025em)}
.rc-mark .trend.t-t{margin-top:-.06em}   /* the tie bar is drawn mid-box, so pull it up to match */
.rc-mark .trend{width:.26em;height:.17em;min-width:11px;min-height:7px}
.team .record{font-size:70px;font-weight:900;line-height:1;letter-spacing:-.01em;white-space:nowrap}
.team .record.rec-4{font-size:52px}.team .record.rec-5{font-size:46px}.team .record.rec-6{font-size:38px}
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

.compare .body{padding:46px 0 20px;justify-content:space-evenly;align-items:center}
.compare .body>.cmp-row{width:90%}
.compare .cmp-row{grid-template-columns:1fr 84px 1fr}
.cmp-row{display:grid;grid-template-columns:1fr 104px 1fr;align-items:center}
.cmp-head{justify-items:center}
.pill{display:block;width:56px;height:14px;border-radius:999px}
.c-cmp .pill{width:36px;height:9px}
.c-cmp .cmp-head{padding-bottom:4px}
.ldr{text-align:center;min-width:0}
.ldr-v{font-size:20px;font-weight:700;line-height:1.2}
.compare .ldr-v{position:relative;display:inline-block;font-size:clamp(28px,8.2vw,36px);line-height:1.05}
.compare .ldr-v .crown{width:20px;height:16px;transform:translate(5px,-64%)}
/* home column: crown in front of the number, so crowns sit toward the middle of the chart */
.cmp-row>.ldr:last-child .crown{left:auto;right:100%;transform:translate(-4px,-62%)}
.compare .cmp-row>.ldr:last-child .ldr-v .crown{transform:translate(-5px,-64%)}
.compare .ldr-n{margin-top:2px}
.ldr-n{font-size:14px;white-space:nowrap;display:flex;justify-content:center;min-width:0}
.ldr-n .nm{overflow:hidden;text-overflow:ellipsis;min-width:0}
.ldr-n .pos{font-weight:200;flex:none;margin-left:.28em}   /* position never gets cut off */
.cmp-lbl{font-size:12px;text-align:center;line-height:1.2}

@media (max-width:400px){.final-lbl{font-size:11px}.view-l .time{font-size:54px}.view-l .date{font-size:29px}.team .record{font-size:62px}.team .record.rec-4{font-size:48px}.team .record.rec-5{font-size:42px}.team .record.rec-6{font-size:35px}
  .game .body{padding-left:16px;padding-right:16px}.team .body>*{width:min(272px,calc(100% - 64px))}}
@media (max-height:700px){.p1{--peek:28px}.l-id img{width:64px;height:64px}}
/* no prefers-reduced-motion override: motion always plays (Jason, 2026-09-17) */
/* ===== Production additions (not in the preview) ===== */
/* Finished games: final score sits in the header next to each abbreviation */
.teams .hscore{font-size:1em;font-weight:900;line-height:1;font-variant-numeric:tabular-nums;letter-spacing:-.01em;padding:0 .1em}
.teams .hscore.lose{opacity:.3}
a.card{cursor:pointer}
/* condensed cards: name at the top center, same type as the expanded slivers */
.card-title{position:absolute;left:0;right:0;top:0;height:var(--ctitle);display:flex;align-items:center;justify-content:center;
  font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--text-2);pointer-events:none;line-height:1}
/* view toggle: a card-shaped box that grows/shrinks between the two views */
.morph{position:fixed;z-index:9;background:var(--tile);border:1px solid var(--tile-border);border-radius:20px;overflow:hidden;pointer-events:none}
.morph>.card{position:absolute;left:0;top:0;border:0;border-radius:0;background:transparent;transform:none;transition:none}
.temp-word{font-size:26px}
.c-game .temp-word{font-size:clamp(18px,2.6vh,22px)}
.temp-na,.rank-n.na,.crank b.na,.ldr-v.na{color:var(--text-3)}
.inj-none{color:var(--text-2)}
.l-inj .inj-none{font-weight:400}

"""
