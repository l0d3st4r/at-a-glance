"""
Renders the site from data/matchups.json (after build_data.py has run).

Outputs:
  site/index.html     -- Page 0: the week's matchup grid (Jason's Framer design)
  site/raw.html       -- the old v0 unstyled data dump, kept for debugging
  site/helmets/*.svg  -- team-colored helmets used by Page 0 (see helmets.py)

Run with: python render_html.py

Page 0 design (from Framer, 2026-09-16):
  - "Week N" label centered at the top
  - grid of matchup cards: 6 across on desktop, 4 on tablet, 2 on phone
  - each card: date/time (Inter 11px), away helmet + home helmet side by side
    (48px, home helmet mirrored so they face each other), team abbreviation
    (Inter 20px Bold), record (Inter 16px Regular)
  - away team on the left, home team on the right
  - date format: "SUN 9/20 · 1:00 PM ET"

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

def format_kickoff(gameday, gametime):
    """
    nflverse gameday = "YYYY-MM-DD", gametime = "HH:MM" (24h, US Eastern).
    -> "SUN 9/20 · 1:00 PM ET". Missing time -> "SUN 9/20 · TBD".
    """
    try:
        d = date.fromisoformat(str(gameday)[:10])
    except (TypeError, ValueError):
        return "Date TBD"
    day_part = f"{WEEKDAYS[d.weekday()]} {d.month}/{d.day}"

    try:
        hh, mm = (int(x) for x in str(gametime).split(":")[:2])
    except (TypeError, ValueError):
        return f"{day_part} · TBD"
    suffix = "AM" if hh < 12 else "PM"
    h12 = hh % 12 or 12
    return f"{day_part} · {h12}:{mm:02d} {suffix} ET"


def format_record(record):
    record = record or {}
    w, l, t = record.get("wins", 0), record.get("losses", 0), record.get("ties", 0)
    return f"{w}-{l}-{t}" if t else f"{w}-{l}"


# ---------------------------------------------------------------- page 0

PAGE0_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#fff;color:#000;font-family:Inter,system-ui,-apple-system,sans-serif;
  -webkit-font-smoothing:antialiased}
.week{text-align:center;font-size:16px;font-weight:400;padding:20px 16px 0}
.grid{display:grid;grid-template-columns:repeat(6,1fr);row-gap:26px;
  max-width:1440px;margin:0 auto;padding:22px 16px 64px}
@media (max-width:1199px){.grid{grid-template-columns:repeat(4,1fr)}}
@media (max-width:809px){.grid{grid-template-columns:repeat(2,1fr)}}
.card{display:flex;flex-direction:column;align-items:center;text-decoration:none;color:inherit}
.card:focus-visible{outline:2px solid #000;outline-offset:4px;border-radius:4px}
.kickoff{font-size:11px;font-weight:400;line-height:13px;white-space:nowrap}
.teams{display:flex;gap:20px;margin-top:8px}
.team{display:flex;flex-direction:column;align-items:center;width:48px}
.team img{width:48px;height:48px;display:block}
.abbr{font-size:20px;font-weight:700;line-height:24px;margin-top:4px}
.record{font-size:16px;font-weight:400;line-height:19px;margin-top:4px}
.error{grid-column:1/-1;background:#fee;padding:8px;font-size:12px;white-space:pre-wrap}
.empty{grid-column:1/-1;text-align:center;padding:40px 0}
"""


def render_team(snapshot, mirrored):
    team = (snapshot or {}).get("team") or "?"
    src = "helmets/" + helmets.helmet_filename(team, mirrored=mirrored)
    return (
        '<div class="team">'
        f'<img src="{esc(src)}" alt="" width="48" height="48">'
        f'<span class="abbr">{esc(team)}</span>'
        f'<span class="record">{esc(format_record((snapshot or {}).get("record")))}</span>'
        "</div>"
    )


def render_card(m):
    away, home = m.get("away") or {}, m.get("home") or {}
    kickoff = format_kickoff(m.get("gameday"), m.get("gametime"))
    label = f"{away.get('team', '?')} at {home.get('team', '?')}, {kickoff}"
    # href is a placeholder until Page 1 exists; game_id is the stable key for it.
    return (
        f'<a class="card" href="#{esc(m.get("game_id") or "")}" aria-label="{esc(label)}">'
        f'<span class="kickoff">{esc(kickoff)}</span>'
        '<div class="teams">'
        f"{render_team(away, mirrored=False)}"
        f"{render_team(home, mirrored=True)}"
        "</div></a>"
    )


def render_page0(data):
    matchups = sorted(
        data.get("matchups") or [],
        key=lambda m: (str(m.get("gameday") or ""), str(m.get("gametime") or "")),
    )
    week = data.get("week")
    cards = []
    for m in matchups:
        try:
            cards.append(render_card(m))
        except Exception:
            cards.append(f'<div class="error">Failed to render one matchup\n{esc(traceback.format_exc())}</div>')
    if not cards:
        cards.append('<p class="empty">No matchups this week.</p>')

    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>At A Glance</title>"
        "<meta name='description' content='Pro Football Upcoming Game Information'>"
        "<link rel='preconnect' href='https://fonts.googleapis.com'>"
        "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap' rel='stylesheet'>"
        f"<style>{PAGE0_CSS}</style></head><body>"
        f"<header class='week'>Week {esc(week) if week is not None else '–'}</header>"
        f"<main class='grid'>{''.join(cards)}</main>"
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
