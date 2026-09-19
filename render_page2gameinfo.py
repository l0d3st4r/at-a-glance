"""
Page 2 -- Game Info deep dive (Jason's Framer page "page2gameinfo", 2026-09-19).

Opened by tapping the Game Info card on Page 1 (either view). It is not a separate file:
the markup lives inside each game's Page 1 block (site/game/<game_id>.html) as a hidden
layer, so it opens instantly and works the same in the Page 0 overlay and on the standalone
game page. The open/close motion and gestures live in render_page1.P1_JS (search "Page 2")

File name: render_page2gameinfo.py -- one file per Page 2 deep dive (render_page2<name>.py).

Three cards, in Framer's order, restyled to the site's standards (Jason: "defer to the
standards already on the site about fonts, layout, interaction"):
  1. Kickoff  -- time, date, weekday; live countdown (FINAL once the game is over);
                 head referee; last meeting with its score; TV network
  2. Weather  -- actual + feels-like temperature, condition icon, precipitation chance
                 and amount, wind range + direction, humidity. NOT shown for indoor games
                 (domes, and retractable roofs recorded as closed).
  3. Stadium  -- name, city + state (or country), playing surface, and the roof status
                 ONLY for retractable roofs (Open / Closed, "TBD" before the game).

Site standards applied instead of the Framer mock's literal values: 600px column with
16px gutters, Page 1's card tokens (white, 1px rgba(0,0,0,.12) border, 20px radius),
the small uppercase card titles, Saira italic for team abbreviations, Teko for scores,
Inter everywhere else (times, temperatures and labels stay Inter per typography-2026-09-18),
secondary text rgba(0,0,0,.62), "—" placeholders at rgba(0,0,0,.4).

Data: data/matchups.json -> game_details[<id>]["info"] (page1_data.game_info).
"""

import html
from datetime import date, datetime, timezone

DASH = "—"
MONTHS_UPPER = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def esc(v):
    return html.escape(str(v), quote=True)


# A generic open bowl with two flags -- drawn for this page, same line weight as the weather icons.
STADIUM_ICON = (
    '<svg class="st-icon" viewBox="0 0 64 48" width="88" height="66" fill="none" stroke="currentColor" stroke-width="2.6" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<ellipse cx="32" cy="22" rx="24" ry="7"/>'
    '<path d="M8 22v12c0 4 10.7 7 24 7s24-3 24-7V22"/>'
    '<path d="M14 28v8M22 30v9M32 30.5v10M42 30v9M50 28v8"/>'
    '<path d="M27 41v-6h10v6"/>'
    '<path d="M24 15V4l6 2.5-6 2.5M40 15V4l6 2.5-6 2.5"/>'
    "</svg>"
)


# ---------------------------------------------------------------- formatting

def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def fmt_int(v):
    n = _num(v)
    return DASH if n is None else f"{int(round(n))}"


def fmt_inches(v):
    """0.5 -> '0.5', 0.25 -> '0.25', 0 -> '0'."""
    n = _num(v)
    if n is None:
        return None
    return f"{n:.2f}".rstrip("0").rstrip(".") or "0"


def fmt_meeting_date(iso):
    try:
        d = date.fromisoformat(str(iso)[:10])
    except (TypeError, ValueError):
        return ""
    return f"{MONTHS_UPPER[d.month - 1]} {d.day}, {d.year}"


def countdown_parts(kickoff_iso, now=None):
    """Build-time value for the countdown (the page script keeps it live) -> (days, hours, minutes) or None."""
    try:
        ko = datetime.fromisoformat(str(kickoff_iso).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    secs = (ko - (now or datetime.now(timezone.utc))).total_seconds()
    if secs <= 0:
        return None
    mins = int(secs // 60)
    return mins // 1440, (mins % 1440) // 60, mins % 60


def _unit(n, word):
    return word if n == 1 else word + "S"


# ---------------------------------------------------------------- cards

def kickoff_card(d, info, time_html):
    try:
        day = date.fromisoformat(str(d.get("gameday"))[:10])
        date_line, weekday = f"{MONTHS_UPPER[day.month - 1]} {day.day}", DAY_NAMES[day.weekday()]
    except (TypeError, ValueError):
        date_line, weekday = "Date TBD", ""

    if d.get("final"):
        clock = f'<div class="cd cd-done"><span class="cd-status">{"FINAL/OT" if d.get("overtime") else "FINAL"}</span></div>'
    else:
        parts = countdown_parts(info.get("kickoff_utc"))
        rows = []
        for key, word, n in zip(("d", "h", "m"), ("DAY", "HOUR", "MINUTE"), parts or (None, None, None)):
            rows.append(f'<div class="cd-row"><b class="cd-n" data-u="{key}">{DASH if n is None else n}</b>'
                        f'<span class="cd-u" data-w="{word}">{_unit(n, word)}</span></div>')
        clock = (f'<div class="cd" data-kickoff="{esc(info.get("kickoff_utc") or "")}" role="timer" aria-label="Time until kickoff">'
                 f'{"".join(rows)}<span class="cd-status" hidden></span></div>')

    ref = info.get("referee")
    ref_html = f'<span>{esc(ref)}</span>' if ref else '<span class="na">TBA</span>'

    a = (d.get("away") or {}).get("team") or "TBD"
    h = (d.get("home") or {}).get("team") or "TBD"
    m = info.get("last_meeting")
    if m and isinstance(m.get("score"), dict):
        sa, sh = _num(m["score"].get(a)), _num(m["score"].get(h))
        ca = "sc" + (" lose" if sa is not None and sh is not None and sa < sh else "")
        ch = "sc" + (" lose" if sa is not None and sh is not None and sh < sa else "")
        meeting = (
            f'<p class="ko-line">Last matchup <span class="ko-date-sm">{esc(fmt_meeting_date(m.get("date")))}</span></p>'
            f'<div class="ko-meet" aria-label="{esc(a)} {fmt_int(sa)}, {esc(h)} {fmt_int(sh)}">'
            f'<span class="abbr">{esc(a)}</span><span class="{ca}">{fmt_int(sa)}</span>'
            f'<span class="{ch}">{fmt_int(sh)}</span><span class="abbr">{esc(h)}</span></div>'
        )
    else:
        meeting = '<p class="ko-line na">First meeting</p>'

    names = info.get("broadcasters") or []
    network = d.get("networks")
    net = network.strip() if isinstance(network, str) and network.strip() else "TV TBD"
    crew = "".join(f"<span>{esc(n)}</span>" for n in names)
    tv = (f'<div class="ko-tv{" has-crew" if crew else ""}"><span class="ko-net">{esc(net)}</span>'
          f'{f"<span class=ko-crew>{crew}</span>" if crew else ""}</div>')

    return (
        '<section class="p2-card ko" aria-label="Kickoff">'
        '<span class="card-title">Kickoff</span>'
        '<div class="ko-top">'
        f'<div class="ko-when">{time_html}<div class="ko-date">{esc(date_line)}</div><div class="ko-date">{esc(weekday)}</div></div>'
        f"{clock}</div>"
        f'<div class="ko-lines"><p class="ko-line">Head Referee: {ref_html}</p>{meeting}</div>'
        f"{tv}</section>"
    )


def _wx_row(value_html, label, extra_html=""):
    return (f'<div class="wx-row"><div class="wx-v">{value_html}</div><div class="wx-l">{esc(label)}</div>'
            f'<div class="wx-x">{extra_html}</div></div>')


def _val(n, unit=""):
    if n is None:
        return f'<span class="na">{DASH}</span>'
    return f"{esc(n)}<small>{esc(unit)}</small>" if unit else esc(n)


def weather_card(d, w, icons):
    """None for indoor games -- the card is left out entirely (Jason, 2026-09-19)."""
    if w.get("indoor"):
        return None
    ok = w.get("available")
    g = (lambda k: w.get(k)) if ok else (lambda k: None)
    temp, feels = g("temp_f"), g("feels_f")
    icon = icons.get(g("condition"), "") if ok else ""

    precip_pct, precip_in = g("precip_pct"), fmt_inches(g("precip_in"))
    if d.get("final"):   # after the game: how much actually fell
        precip = _wx_row(_val(precip_in, "IN") if precip_in is not None else _val(None), "Precip")
    else:
        precip = _wx_row(_val(fmt_int(precip_pct) if precip_pct is not None else None, "%"), "Precip",
                         f"{esc(precip_in)}&quot;" if precip_in is not None else "")
    lo, hi = g("wind_min_mph"), g("wind_max_mph")
    if lo is None and hi is None:
        speed = None
    elif lo is None or hi is None or int(lo) == int(hi):
        speed = fmt_int(hi if hi is not None else lo)
    else:
        speed = f"{fmt_int(lo)}-{fmt_int(hi)}"
    wind = _wx_row(_val(speed, "MPH"), "Wind", esc(g("wind_dir") or ""))
    hum = g("humidity_pct")
    humidity = _wx_row(_val(fmt_int(hum) if hum is not None else None, "%"), "Humidity")

    note = ""
    if not ok:
        days = w.get("window_days")
        note = (f'<p class="wx-note">Forecast posts {esc(days)} days before kickoff</p>' if w.get("reason") == "forecast_window"
                else '<p class="wx-note">Weather not available</p>')
    t = lambda v: f'{esc(fmt_int(v))}°' if v is not None else f'<span class="na">{DASH}°</span>'
    return (
        '<section class="p2-card wxc" aria-label="Weather">'
        '<span class="card-title">Weather</span>'
        '<div class="wx-top">'
        f'<div class="wx-t"><b>{t(temp)}</b><span>Actual</span></div>'
        f'<div class="wx-t"><b>{t(feels)}</b><span>Feels Like</span></div>'
        f'<div class="wx-ic">{icon}</div></div>'
        f'<div class="wx-rows">{precip}{wind}{humidity}</div>{note}</section>'
    )


def stadium_card(st):
    name = st.get("name") or "Stadium TBD"
    city, region = st.get("city"), st.get("region")
    place = ""
    if city and region:
        place = f'<span class="nb">{esc(city)},</span> <span class="nb">{esc(region)}</span>'
    elif city or region:
        place = f'<span class="nb">{esc(city or region)}</span>'
    facts = [f'<div class="fact"><b>{esc(st.get("surface") or DASH)}</b><span>Playing Surface</span></div>']
    if st.get("roof_type") == "retractable":   # only stadiums that can open or close show it (Jason)
        status = {"open": "Open", "closed": "Closed"}.get(st.get("roof_status"), "TBD")
        facts.append(f'<div class="fact"><b{" class=na" if status == "TBD" else ""}>{status}</b><span>Roof</span></div>')
    return (
        '<section class="p2-card st" aria-label="Stadium">'
        '<span class="card-title">Stadium</span>'
        f'<div class="st-head"><h2 class="st-name">{esc(name)}</h2>{STADIUM_ICON}</div>'
        f'{f"<div class=st-city>{place}</div>" if place else ""}'
        f'<div class="st-facts{" one" if len(facts) == 1 else ""}">{"".join(facts)}</div></section>'
    )


def render_p2_block(d, time_html, icons):
    """The hidden Page 2 layer inside Page 1's .p1 block. Empty string if the game has no info."""
    info = d.get("info")
    if not isinstance(info, dict):
        return ""
    cards = [kickoff_card(d, info, time_html), weather_card(d, info.get("weather") or {}, icons),
             stadium_card(info.get("stadium") or {})]
    return ('<div class="p2" data-page="game-info" aria-label="Game info" role="region">'
            f'<div class="p2-col">{"".join(c for c in cards if c)}</div></div>')


# ---------------------------------------------------------------- styles
# Appended to Page 1's stylesheet (same <style id="p1-css">), so it also lands in the Page 0
# overlay's shadow root. Everything below .p2-col is scoped by its own class names (not by the
# .p2 parent) so the close animation can carry a snapshot of the column in a plain box.

P2_CSS = r"""
/* ===== Page 2: Game Info deep dive (2026-09-19) ===== */
.p2{display:none;position:fixed;inset:var(--bar) 0 var(--bbar);z-index:9;overflow-x:hidden;overflow-y:auto;overscroll-behavior:contain;
  background:#fff;scrollbar-width:none;transform-origin:50% 50%}
.p2::-webkit-scrollbar{display:none}
.p1[data-detail] .p2{display:block}
.p1[data-detail] .view,.p1[data-detail] .dots{visibility:hidden}
.p1[data-detail][data-pulling] .view{visibility:visible}   /* pulling Page 2 down shows Page 1 behind it */
.p1[data-detail] .bbar .week:not(.p2-back),.p1[data-detail] .toggle{display:none}
.p2-back{display:none}
.p1[data-detail] .p2-back{display:inline-flex}
.p2-col{max-width:var(--col);margin:0 auto;padding:12px 16px 28px;display:flex;flex-direction:column;gap:12px}
.p2-card{position:relative;background:var(--tile);border:1px solid var(--tile-border);border-radius:20px;
  padding:calc(var(--ctitle) + 18px) 24px 30px;color:var(--ink)}
.p2-card .na{color:var(--text-3)}

/* Kickoff */
.ko-top{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}
.ko-when .time{font-size:58px}
.ko-date{font-size:30px;font-weight:700;line-height:1.12;white-space:nowrap}
.ko-when .time+.ko-date{margin-top:8px}
.cd{display:flex;flex-direction:column;gap:7px;padding-top:4px}
.cd-row{display:flex;align-items:baseline;gap:5px;white-space:nowrap}
.cd-n{font-size:36px;font-weight:700;line-height:1;font-variant-numeric:tabular-nums;min-width:1.25em;text-align:right;letter-spacing:-.01em}
.cd-u{font-size:13px;font-weight:700;letter-spacing:.04em}
.cd-status{font-size:16px;font-weight:700;letter-spacing:.04em;line-height:1.2;white-space:nowrap}   /* same as Page 0's FINAL */
.cd-done{padding-top:10px}
.ko-lines{margin-top:30px;text-align:center}
.ko-line{font-size:15px;line-height:1.5}
.ko-line+.ko-line{margin-top:2px}
.ko-meet{display:flex;justify-content:center;align-items:center;gap:.45em;font-size:28px;margin-top:10px}
.ko-meet .sc{font-family:Teko,Inter,system-ui,sans-serif;font-weight:700;font-size:1.25em;line-height:1;min-width:1.2em;text-align:center;
  font-variant-numeric:tabular-nums}
.ko-meet .sc.lose{opacity:.3}
.ko-meet .sc+.sc{margin-left:.4em}
.ko-tv{margin-top:26px;display:flex;justify-content:center;align-items:center;gap:24px;font-size:16px}
.ko-tv.has-crew{justify-content:space-between}
.ko-crew{display:flex;flex-direction:column;text-align:right;line-height:1.25}

/* Weather */
.wx-top{display:flex;align-items:flex-end;gap:24px}
.wx-t b{display:block;font-size:52px;font-weight:700;line-height:1;letter-spacing:-.01em;white-space:nowrap}
.wx-t>span{display:block;font-size:14px;color:var(--text-2);margin-top:6px}
.wx-ic{margin-left:auto;align-self:center}
.wx-ic svg{width:68px;height:51px;display:block}
.wx-rows{margin-top:30px;display:flex;flex-direction:column;gap:20px}
.wx-row{display:grid;grid-template-columns:minmax(104px,auto) 1fr auto;align-items:baseline;gap:14px}
.wx-v{font-size:40px;font-weight:700;line-height:1;white-space:nowrap;letter-spacing:-.01em}
.wx-v small{font-size:14px;font-weight:700;letter-spacing:.04em;margin-left:3px}
.wx-l{font-size:15px;color:var(--text-2)}
.wx-x{font-size:30px;font-weight:700;line-height:1;white-space:nowrap}
.wx-note{margin-top:22px;font-size:13px;color:var(--text-2);text-align:center}

/* Stadium */
.st-head{display:flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:12px 20px;text-align:center}
.st-name{font-size:34px;font-weight:700;line-height:1.1;letter-spacing:-.01em}
.st-icon{display:block;flex:none}
.st-city{margin-top:24px;font-size:28px;font-weight:700;line-height:1.15;text-align:center}
.st-city .nb{display:inline-block}
.st-facts{margin-top:30px;display:grid;grid-template-columns:1fr 1fr;gap:16px;text-align:center}
.st-facts.one{grid-template-columns:1fr}
.fact b{display:block;font-size:34px;font-weight:700;line-height:1.05}
.fact span{display:block;font-size:14px;color:var(--text-2);margin-top:6px}

@media (max-width:400px){
  .p2-card{padding-left:18px;padding-right:18px}
  .ko-when .time{font-size:50px}.ko-date{font-size:26px}
  .cd-n{font-size:31px}.cd-u{font-size:12px}
  .wx-t b{font-size:46px}.wx-top{gap:18px}
  .wx-v{font-size:36px}.wx-x{font-size:27px}.wx-row{grid-template-columns:minmax(92px,auto) 1fr auto;gap:12px}
  .st-name{font-size:30px}.st-city{font-size:25px}.fact b{font-size:30px}
}
@media (max-width:344px){
  .p2-card{padding-left:14px;padding-right:14px}
  .ko-when .time{font-size:40px}.ko-date{font-size:22px}.cd-n{font-size:25px}.cd-u{font-size:10px;letter-spacing:.02em}
  .wx-t b{font-size:40px}.wx-v{font-size:31px}.wx-x{font-size:23px}
}
@media (min-width:601px){
  .ko-when .time{font-size:63px}.ko-date{font-size:34px}.cd-n{font-size:40px}.cd-u{font-size:14px}
}
"""
