"""
Renders the site from data/matchups.json (after build_data.py has run).

Outputs:
  site/index.html     -- Page 0: the week's matchup grid (Jason's Framer design)
  site/raw.html       -- the old v0 unstyled data dump, kept for debugging
  site/helmets/*.svg  -- team-colored helmets used by Page 0 (see helmets.py)

Run with: python render_html.py

Page 0 design (revised 2026-09-16, layout modeled on Apple Sports' NFL
"Upcoming" tab, using Jason's helmets, no betting lines):
  - white background and black text (as in the Framer design), "Week N" title at the top
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
   sizes 11px (date/time labels), 16px (week label, records), 20px (team abbreviations). */
body{min-height:100vh;color:var(--text);font-family:Inter,system-ui,-apple-system,sans-serif;font-weight:400;
  -webkit-font-smoothing:antialiased;background:var(--bg)}
.week{text-align:center;font-size:16px;font-weight:400;line-height:19px;padding:24px 16px 8px}
main{max-width:600px;margin:0 16px 64px}
@media (min-width:632px){main{margin:0 auto 64px}}
.day{text-align:center;font-size:16px;font-weight:400;line-height:19px;padding:24px 0 12px}
.games{list-style:none;display:flex;flex-direction:column;gap:10px}
.game{display:grid;grid-template-columns:84px 1fr minmax(96px,auto) 1fr 84px;align-items:center;
  padding:16px 8px;color:inherit;text-decoration:none;
  background:var(--tile);border:1px solid var(--tile-border);border-radius:20px;
  transition:transform .16s ease,background-color .16s ease,border-color .16s ease}
.game:hover,.game:focus-visible{transform:scale(1.03);background:var(--tile-hover);border-color:var(--tile-border-hover)}
.game:focus-visible{outline:2px solid #000;outline-offset:2px}
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
@media (max-width:420px){
  .game{grid-template-columns:72px 1fr auto 1fr 72px;padding:14px 4px}
  .team img{width:42px;height:42px}
  .center{padding:0 4px}
}
.error{background:#fee;color:#000;padding:8px;font-size:11px;white-space:pre-wrap;border-radius:8px}
.empty{text-align:center;padding:40px 0;color:var(--text-2);font-size:16px}
"""


def time_html(time_text):
    """ "1:00 PM ET" -> "1:00 PM<span class=tz>ET</span>" so the timezone can be smaller."""
    if time_text.endswith(" ET"):
        return f'{esc(time_text[:-3])}<span class="tz">ET</span>'
    return esc(time_text)


def render_team(snapshot, mirrored):
    team = (snapshot or {}).get("team") or "?"
    src = "helmets/" + helmets.helmet_filename(team, mirrored=mirrored)
    return (
        '<div class="team">'
        f'<img src="{esc(src)}" alt="" width="48" height="48">'
        f'<span class="abbr">{esc(team)}</span>'
        "</div>"
    )


def render_game(m):
    away, home = m.get("away") or {}, m.get("home") or {}
    time_text = format_time(m.get("gametime"))
    network = format_network(m.get("networks"))
    away_name = TEAM_NAMES.get(away.get("team"), away.get("team", "?"))
    home_name = TEAM_NAMES.get(home.get("team"), home.get("team", "?"))
    label = f"{away_name} at {home_name}, {time_text}"
    # href is a placeholder until Page 1 exists; game_id is the stable key for it.
    return (
        f'<a class="game" href="#{esc(m.get("game_id") or "")}" aria-label="{esc(label)}">'
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


def group_by_day(matchups):
    """Sorted [(date_or_None, [matchups...]), ...] -- one group per calendar day, TBD dates last."""
    groups = {}
    for m in matchups:
        groups.setdefault(parse_gameday(m.get("gameday")), []).append(m)
    ordered = sorted(groups.items(), key=lambda kv: (kv[0] is None, kv[0] or date.max))
    return [(d, sorted(ms, key=lambda m: str(m.get("gametime") or "99:99"))) for d, ms in ordered]


def render_page0(data):
    week = data.get("week")
    sections = []
    for d, games in group_by_day(data.get("matchups") or []):
        rows = []
        for m in games:
            try:
                rows.append(f"<li>{render_game(m)}</li>")
            except Exception:
                rows.append(f'<li><div class="error">Failed to render one matchup\n{esc(traceback.format_exc())}</div></li>')
        sections.append(
            f'<section><h2 class="day">{esc(format_day_header(d))}</h2>'
            f'<ul class="games">{"".join(rows)}</ul></section>'
        )
    if not sections:
        sections.append('<p class="empty">No matchups this week.</p>')

    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<meta name='theme-color' content='#ffffff'>"
        "<title>At A Glance</title>"
        "<meta name='description' content='Pro Football Upcoming Game Information'>"
        "<link rel='preconnect' href='https://fonts.googleapis.com'>"
        "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap' rel='stylesheet'>"
        f"<style>{PAGE0_CSS}</style></head><body>"
        f"<header class='week'>Week {esc(week) if week is not None else '–'}</header>"
        f"<main>{''.join(sections)}</main>"
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

    print(f"Wrote {INDEX_PATH}, {RAW_PATH} and helmets to {HELMET_DIR}")


if __name__ == "__main__":
    main()
