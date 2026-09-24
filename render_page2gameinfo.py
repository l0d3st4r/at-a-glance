"""
Page 2 -- Game Info deep dive (Jason's Framer page "page2gameinfo", 2026-09-19).

Two views, like Page 1 (Jason, 2026-09-19, v4): the expanded view is a deck with one card per
screen (Page 1's .deck / .slot / .peek / .dots), and the condensed view puts every card on one
screen, each as a headline plus a strip of small labelled facts. Both views share Page 1's
data-view attribute, so Page 2 opens in whichever view Page 1 is in and the +/− button flips both.

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
    """Build-time value for the countdown (the page script keeps it live) -> (days, hours, minutes,
    seconds) or None once kickoff has passed."""
    try:
        ko = datetime.fromisoformat(str(kickoff_iso).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    secs = int((ko - (now or datetime.now(timezone.utc))).total_seconds())
    if secs <= 0:
        return None
    return secs // 86400, secs % 86400 // 3600, secs % 3600 // 60, secs % 60


COUNTDOWN_UNITS = (("d", "DAY"), ("h", "HOUR"), ("m", "MINUTE"), ("s", "SECOND"))


def _countdown_pair(days, hours, minutes, seconds):
    """Only two units show at a time: days+hours with more than a day to go, hours+minutes with
    less than a day but more than an hour, minutes+seconds inside the final hour."""
    if days >= 1:
        return {"d": days, "h": hours}
    if hours >= 1:
        return {"h": hours, "m": minutes}
    return {"m": minutes, "s": seconds}


def _unit(n, word):
    return word if n == 1 else word + "S"


# ---------------------------------------------------------------- shared pieces

def _meeting(d, info):
    """(away, home, meeting dict or None, away score, home score)."""
    a = (d.get("away") or {}).get("team") or "TBD"
    h = (d.get("home") or {}).get("team") or "TBD"
    m = info.get("last_meeting")
    if not (m and isinstance(m.get("score"), dict)):
        return a, h, None, None, None
    return a, h, m, _num(m["score"].get(a)), _num(m["score"].get(h))


def _lose(mine, theirs):
    return " lose" if mine is not None and theirs is not None and mine < theirs else ""


def _countdown(d, info, cls):
    if d.get("final"):
        return f'<div class="{cls} cd-done"><span class="cd-status">{"FINAL/OT" if d.get("overtime") else "FINAL"}</span></div>'
    kickoff = info.get("kickoff_utc")
    parts = countdown_parts(kickoff)
    if parts is None:
        # Kickoff has already passed as of this build. There's no live score feed to poll, so
        # this just reads LIVE until the next scheduled rebuild picks up the final score and
        # renders the "final" branch above instead -- the page script leaves a plain LIVE alone
        # (no data-kickoff to tick against).
        return f'<div class="{cls} cd-done"><span class="cd-status">LIVE</span></div>'
    active = _countdown_pair(*parts)
    rows = "".join(
        f'<div class="cd-row" data-u="{key}"{"" if key in active else " hidden"}>'
        f'<b class="cd-n">{active.get(key, 0)}</b>'
        f'<span class="cd-u" data-w="{word}">{_unit(active.get(key, 0), word)}</span></div>'
        for key, word in COUNTDOWN_UNITS)
    return (f'<div class="{cls}" data-kickoff="{esc(kickoff or "")}" role="timer" aria-label="Time until kickoff">'
            f'{rows}<span class="cd-status" hidden></span></div>')


def _date_parts(d):
    try:
        day = date.fromisoformat(str(d.get("gameday"))[:10])
        return f"{MONTHS_UPPER[day.month - 1]} {day.day}", DAY_NAMES[day.weekday()]
    except (TypeError, ValueError):
        return "Date TBD", ""


def _weather_values(d, w):
    """Formatted weather numbers shared by both views; every value may be None."""
    ok = bool(w.get("available"))
    g = (lambda k: w.get(k)) if ok else (lambda k: None)
    lo, hi = g("wind_min_mph"), g("wind_max_mph")
    if lo is None and hi is None:
        speed = None
    elif lo is None or hi is None or int(lo) == int(hi):
        speed = fmt_int(hi if hi is not None else lo)
    else:
        speed = f"{fmt_int(lo)}-{fmt_int(hi)}"
    pct, hum = g("precip_pct"), g("humidity_pct")
    return {
        "ok": ok, "temp": g("temp_f"), "feels": g("feels_f"), "condition": g("condition"),
        "description": g("description"),
        "pct": None if d.get("final") or pct is None else fmt_int(pct),   # a chance of rain means nothing after the game
        "inches": fmt_inches(g("precip_in")), "speed": speed, "dir": g("wind_dir"),
        "humidity": None if hum is None else fmt_int(hum),
    }


def _temp(v):
    return f'{esc(fmt_int(v))}°' if v is not None else f'<span class="na">{DASH}°</span>'


def _roof(st):
    """'Open' / 'Closed' / 'TBD' for retractable roofs only (Jason), else None."""
    if st.get("roof_type") != "retractable":
        return None
    return {"open": "Open", "closed": "Closed"}.get(st.get("roof_status"), "TBD")


def _place(st):
    city, region = st.get("city"), st.get("region")
    if city and region:
        return f'<span class="nb">{esc(city)},</span> <span class="nb">{esc(region)}</span>'
    return f'<span class="nb">{esc(city or region)}</span>' if (city or region) else ""


# ---------------------------------------------------------------- expanded view: one card per screen

def kickoff_body(d, info, time_html):
    date_line, weekday = _date_parts(d)
    ref = info.get("referee")
    ref_html = f'<span>{esc(ref)}</span>' if ref else '<span class="na">TBA</span>'
    a, h, m, sa, sh = _meeting(d, info)
    if m:
        meeting = (
            f'<p class="ko-line">Last matchup <span class="ko-date-sm">{esc(fmt_meeting_date(m.get("date")))}</span></p>'
            f'<div class="ko-meet" aria-label="{esc(a)} {fmt_int(sa)}, {esc(h)} {fmt_int(sh)}">'
            f'<span class="abbr">{esc(a)}</span><span class="sc{_lose(sa, sh)}">{fmt_int(sa)}</span>'
            f'<span class="sc{_lose(sh, sa)}">{fmt_int(sh)}</span><span class="abbr">{esc(h)}</span></div>'
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
        '<div class="ko-top">'
        f'<div class="ko-when">{time_html}<div class="ko-date">{esc(date_line)}</div><div class="ko-date">{esc(weekday)}</div></div>'
        f'{_countdown(d, info, "cd")}</div>'
        f'<div class="ko-lines"><p class="ko-line">Head Referee: {ref_html}</p>{meeting}</div>{tv}'
    )


def _wx_row(value_html, label, extra_html=""):
    return (f'<div class="wx-row"><div class="wx-v">{value_html}</div><div class="wx-l">{esc(label)}</div>'
            f'<div class="wx-x">{extra_html}</div></div>')


def _val(n, unit=""):
    if n is None:
        return f'<span class="na">{DASH}</span>'
    return f"{esc(n)}<small>{esc(unit)}</small>" if unit else esc(n)


def weather_body(d, w, icons):
    """None for indoor games -- the card is left out entirely (Jason, 2026-09-19)."""
    if w.get("indoor"):
        return None
    v = _weather_values(d, w)
    if d.get("final"):   # after the game: how much actually fell
        precip = _wx_row(_val(v["inches"], "IN"), "Precip")
    else:
        precip = _wx_row(_val(v["pct"], "%"), "Precip", f'{esc(v["inches"])}&quot;' if v["inches"] is not None else "")
    note = ""
    if not v["ok"]:
        note = (f'<p class="wx-note">Forecast posts {esc(w.get("window_days"))} days before kickoff</p>'
                if w.get("reason") == "forecast_window" else '<p class="wx-note">Weather not available</p>')
    desc = f'<p class="wx-desc">{esc(v["description"])}</p>' if v["description"] else ""
    return (
        f'{desc}<div class="wx-top">'
        f'<div class="wx-t"><b>{_temp(v["temp"])}</b><span>Actual</span></div>'
        f'<div class="wx-t"><b>{_temp(v["feels"])}</b><span>Feels Like</span></div>'
        f'<div class="wx-ic">{icons.get(v["condition"], "")}</div></div>'
        f'<div class="wx-rows">{precip}{_wx_row(_val(v["speed"], "MPH"), "Wind", esc(v["dir"] or ""))}'
        f'{_wx_row(_val(v["humidity"], "%"), "Humidity")}</div>{note}'
    )


def stadium_body(st):
    facts = [f'<div class="fact"><b>{esc(st.get("surface") or DASH)}</b><span>Playing Surface</span></div>']
    roof = _roof(st)
    if roof:
        facts.append(f'<div class="fact"><b{" class=na" if roof == "TBD" else ""}>{roof}</b><span>Roof</span></div>')
    place = _place(st)
    return (
        f'<div class="st-head"><h2 class="st-name">{esc(st.get("name") or "Stadium TBD")}</h2>{STADIUM_ICON}</div>'
        f'{f"<div class=st-city>{place}</div>" if place else ""}'
        f'<div class="st-facts{" one" if len(facts) == 1 else ""}">{"".join(facts)}</div>'
    )


# ---------------------------------------------------------------- condensed view: everything on one screen

def _fact(label, value_html, sub=""):
    return f'<div class="sf"><span>{esc(label)}</span><b>{value_html}</b>{f"<i>{sub}</i>" if sub else ""}</div>'


def _na(text=DASH):
    return f'<span class="na">{esc(text)}</span>'


def kickoff_condensed(d, info, time_html):
    date_line, weekday = _date_parts(d)
    a, h, m, sa, sh = _meeting(d, info)
    if m:
        meet = (f'<span class="mm"><span class="abbr">{esc(a)}</span><span class="sc{_lose(sa, sh)}">{fmt_int(sa)}</span>'
                f'<span class="sc{_lose(sh, sa)}">{fmt_int(sh)}</span><span class="abbr">{esc(h)}</span></span>')
        meet_sub = esc(fmt_meeting_date(m.get("date")))
    else:
        meet, meet_sub = _na("First meeting"), ""
    network = d.get("networks")
    tv = esc(network.strip()) if isinstance(network, str) and network.strip() else "TBD"
    ref = info.get("referee")
    return (
        f'<div class="cc-top"><div>{time_html}<div class="cc-date">{esc(date_line)} {esc(weekday)}</div></div>'
        f'{_countdown(d, info, "cd-c")}</div>'
        f'<div class="strip">{_fact("Head Referee", esc(ref) if ref else _na("TBA"))}'
        f'{_fact("Last Matchup", meet, meet_sub)}{_fact("TV", tv)}</div>'
    )


def weather_condensed(d, w, icons):
    if w.get("indoor"):
        return None
    v = _weather_values(d, w)
    if d.get("final"):
        precip = f'{esc(v["inches"])}<small>IN</small>' if v["inches"] is not None else _na()
    elif v["pct"] is not None:
        precip = f'{esc(v["pct"])}<small>%</small>' + (f' <em>{esc(v["inches"])}&quot;</em>' if v["inches"] is not None else "")
    else:
        precip = _na()
    wind = (f'{esc(v["speed"])}<small>MPH</small>' + (f' <em>{esc(v["dir"])}</em>' if v["dir"] else "")) if v["speed"] is not None else _na()
    hum = f'{esc(v["humidity"])}<small>%</small>' if v["humidity"] is not None else _na()
    desc = f'<p class="wx-desc">{esc(v["description"])}</p>' if v["description"] else ""
    return (
        f'{desc}<div class="cc-top"><div class="cc-temps"><div class="wx-t"><b>{_temp(v["temp"])}</b><span>Actual</span></div>'
        f'<div class="wx-t"><b>{_temp(v["feels"])}</b><span>Feels Like</span></div></div>'
        f'<div class="wx-ic">{icons.get(v["condition"], "")}</div></div>'
        f'<div class="strip">{_fact("Precip", precip)}{_fact("Wind", wind)}{_fact("Humidity", hum)}</div>'
    )


def stadium_condensed(st):
    facts = _fact("Surface", esc(st.get("surface")) if st.get("surface") else _na())
    roof = _roof(st)
    if roof:
        facts += _fact("Roof", _na("TBD") if roof == "TBD" else roof)
    place = _place(st)
    return (
        f'<div class="cc-top"><div class="cc-stn"><div class="st-name">{esc(st.get("name") or "Stadium TBD")}</div>'
        f'{f"<div class=cc-city>{place}</div>" if place else ""}</div>{STADIUM_ICON}</div>'
        f'<div class="strip">{facts}</div>'
    )


# ---------------------------------------------------------------- the layer

def render_p2_block(d, time_html, icons):
    """The hidden Page 2 layer inside Page 1's .p1 block. Empty string if the game has no info."""
    info = d.get("info")
    if not isinstance(info, dict):
        return ""
    w, st = info.get("weather") or {}, info.get("stadium") or {}
    cards = [("kickoff", "Kickoff", kickoff_body(d, info, time_html), kickoff_condensed(d, info, time_html)),
             ("weather", "Weather", weather_body(d, w, icons), weather_condensed(d, w, icons)),
             ("stadium", "Stadium", stadium_body(st), stadium_condensed(st))]
    cards = [c for c in cards if c[2]]
    from render_page1 import UP, DOWN
    slots = "".join(
        f'<section class="slot"><a class="card p2k p2k-{cid}" tabindex="-1" aria-label="{name}">'
        f'<span class="peek peek-top">{DOWN}<span>{name}</span></span><div class="body">{body}</div>'
        f'<span class="peek peek-bot">{UP}<span>{name}</span></span></a></section>'
        for cid, name, body, _c in cards)
    dots = "".join(f'<button class="dot" type="button" aria-label="{name}"></button>' for _i, name, _b, _c in cards)
    condensed = "".join(
        f'<a class="card cc cc-{cid}" tabindex="0" aria-label="{name}"><span class="card-title">{name}</span>{c}</a>'
        for cid, name, _b, c in cards)
    return ('<div class="p2" data-page="game-info" aria-label="Game info" role="region">'
            f'<div class="p2-view p2-l deck">{slots}</div><nav class="dots p2-dots" aria-label="Cards">{dots}</nav>'
            f'<div class="p2-view p2-c n{len(cards)}">{condensed}</div></div>')


# ---------------------------------------------------------------- styles
# Appended to Page 1's stylesheet (same <style id="p1-css">), so it also lands in the Page 0
# overlay's shadow root. The deck reuses Page 1's .deck / .slot / .peek / .dots rules as they are.

P2_CSS = r"""
/* ===== Page 2: Game Info deep dive (2026-09-19; deck + condensed views v4) ===== */
.p2{display:none;position:fixed;inset:var(--bar) 0 var(--bbar);z-index:9;overflow:hidden;background:var(--aag-bg);transform-origin:50% 50%}
/* Up to three of these can exist per game (game-info, away-team, home-team) -- only the one
   matching data-detail's value shows (render_page2team.py adds the other two data-page values). */
.p1[data-detail="game-info"] .p2[data-page="game-info"]{display:block}
.p1[data-detail]>.view,.p1[data-detail]>.dots{visibility:hidden}
.p1[data-detail][data-pulling]>.view,.p1[data-detail][data-closing]>.view{visibility:visible}   /* Page 1 shows behind a pull / the close */
.p1[data-detail] .bbar .week:not(.p2-back){display:none}
.p2-back{display:none}
.p1[data-detail] .p2-back{display:inline-flex}
.p2-view{display:none}
.p1[data-view=large] .p2-l{display:block}
.p1[data-view=large] .p2-dots{display:flex}
.p1[data-view=condensed] .p2-c{display:grid}
.p2 .na{color:var(--text-3)}

/* ---- expanded: Page 1's deck, one Page 2 card per screen ---- */
/* positioned inside .p2 rather than fixed to the screen, so the deck moves with Page 2 when it is pulled down */
.p2 .deck{position:absolute;inset:0}
.p2 .dots{position:absolute;top:50%}
.p2 .slot .body{padding:46px 26px 30px;justify-content:space-evenly}
.ko-top{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}
.ko-when .time{font-size:58px}
.ko-date{font-size:30px;font-weight:700;line-height:1.12;white-space:nowrap}
.ko-when .time+.ko-date{margin-top:8px}
.cd{display:flex;flex-direction:column;gap:7px;padding-top:4px}
.cd-row{display:flex;align-items:baseline;gap:5px;white-space:nowrap}
.cd-row[hidden]{display:none}   /* an author display:flex above would otherwise beat the UA [hidden] default */
.cd-n{font-size:36px;font-weight:700;line-height:1;font-variant-numeric:tabular-nums;min-width:1.25em;text-align:right;letter-spacing:-.01em}
.cd-u{font-size:13px;font-weight:700;letter-spacing:.04em}
.cd-status{font-size:16px;font-weight:700;letter-spacing:.04em;line-height:1.2;white-space:nowrap}   /* same as Page 0's FINAL */
.cd-done{padding-top:10px}
.ko-lines{text-align:center}
.ko-line{font-size:15px;line-height:1.5}
.ko-line+.ko-line{margin-top:2px}
.ko-meet{display:flex;justify-content:center;align-items:center;gap:.45em;font-size:32px;margin-top:10px}
.sc{font-family:Teko,Inter,system-ui,sans-serif;font-weight:700;font-size:1.25em;line-height:1;min-width:1.2em;text-align:center;font-variant-numeric:tabular-nums}
.sc.lose{opacity:.3}
.ko-meet .sc+.sc{margin-left:.4em}
.ko-tv{display:flex;justify-content:center;align-items:center;gap:24px;font-size:16px}
.ko-tv.has-crew{justify-content:space-between}
.ko-crew{display:flex;flex-direction:column;text-align:right;line-height:1.25}
.wx-desc{font-size:20px;font-weight:700;line-height:1.2;margin-bottom:10px;text-align:center}
.wx-top{display:flex;align-items:flex-end;gap:24px}
.wx-t b{display:block;font-size:58px;font-weight:700;line-height:1;letter-spacing:-.01em;white-space:nowrap}
.wx-t>span{display:block;font-size:14px;color:var(--text-2);margin-top:6px}
.wx-ic{margin-left:auto;align-self:center}
.wx-ic svg{width:68px;height:51px;display:block}
.wx-rows{display:flex;flex-direction:column;gap:20px}
.wx-row{display:grid;grid-template-columns:minmax(104px,auto) 1fr auto;align-items:baseline;gap:14px}
.wx-v{font-size:44px;font-weight:700;line-height:1;white-space:nowrap;letter-spacing:-.01em}
.wx-v small{font-size:14px;font-weight:700;letter-spacing:.04em;margin-left:3px}
.wx-l{font-size:15px;color:var(--text-2)}
.wx-x{font-size:30px;font-weight:700;line-height:1;white-space:nowrap}
.wx-note{font-size:13px;color:var(--text-2);text-align:center}
.st-head{display:flex;flex-wrap:wrap;align-items:center;justify-content:center;gap:12px 20px;text-align:center}
.st-name{font-size:38px;font-weight:700;line-height:1.1;letter-spacing:-.01em}
.st-icon{display:block;flex:none}
.p2-l .st-icon{width:104px;height:78px}
.st-city{font-size:30px;font-weight:700;line-height:1.15;text-align:center}
.nb{display:inline-block}
.st-facts{display:grid;grid-template-columns:1fr 1fr;gap:16px;text-align:center}
.st-facts.one{grid-template-columns:1fr}
.fact b{display:block;font-size:38px;font-weight:700;line-height:1.05}
.fact span{display:block;font-size:14px;color:var(--text-2);margin-top:6px}

/* ---- condensed: every card on one screen; a headline, then a strip of small labelled facts ---- */
.p2-c{max-width:var(--col);margin:0 auto;height:100%;padding:12px 16px;gap:12px}
.p2-c.n3{grid-template-rows:minmax(0,1.12fr) minmax(0,1fr) minmax(0,.92fr)}
.p2-c.n2{grid-template-rows:minmax(0,1.15fr) minmax(0,1fr)}
a.card.cc{display:flex;flex-direction:column;justify-content:space-evenly;gap:6px;padding:var(--ctitle) 20px clamp(8px,1.4vh,14px);overflow:hidden;min-height:0}
.p2-c a.card.cc:hover,.p2-c a.card.cc:focus-visible{transform:scale(1.03);border-color:var(--tile-border-hover);z-index:1}
.cc-top{display:flex;justify-content:space-between;align-items:center;gap:12px}
.cc .time{font-size:clamp(30px,5.2vh,46px)}
.cc .time small{font-size:13px}
.cc-date{font-size:clamp(15px,2.2vh,19px);font-weight:700;margin-top:4px;white-space:nowrap}
.cd-c{display:flex;flex-direction:column;gap:clamp(0px,.4vh,3px)}
.cd-c .cd-n{font-size:clamp(17px,2.8vh,26px)}
.cd-c .cd-u{font-size:10px}
.cd-c.cd-done{padding-top:0}
.strip{display:grid;grid-auto-flow:column;grid-auto-columns:1fr;gap:10px;text-align:center;align-items:start}
.sf>span{display:block;font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--text-2);margin-bottom:4px}
.sf b{display:block;font-size:clamp(14px,2vh,17px);font-weight:700;line-height:1.2}
.sf b small{font-size:.6em;letter-spacing:.04em;margin-left:1px}
.sf b em{font-style:normal;font-weight:400}
.sf i{display:block;font-style:normal;font-size:11px;color:var(--text-2);margin-top:2px}
.mm{display:inline-flex;align-items:center;gap:.3em;white-space:nowrap}
.mm .sc{min-width:0}
.cc .wx-desc{font-size:14px;margin-bottom:4px}
.cc-temps{display:flex;gap:20px}
.cc .wx-t b{font-size:clamp(34px,5.6vh,48px)}
.cc .wx-t>span{font-size:12px;margin-top:3px}
.cc .wx-ic svg{width:54px;height:40px}
.cc-stn{min-width:0}
.cc .st-name{font-size:clamp(20px,3vh,26px);line-height:1.1}
.cc-city{font-size:14px;margin-top:4px}
.cc .st-icon{width:64px;height:48px}

@media (max-width:400px){
  .p2 .slot .body{padding-left:18px;padding-right:18px}
  .ko-when .time{font-size:50px}.ko-date{font-size:26px}
  .cd-n{font-size:31px}.cd-u{font-size:12px}
  .wx-desc{font-size:18px}.wx-t b{font-size:50px}.wx-top{gap:18px}
  .wx-v{font-size:38px}.wx-x{font-size:27px}.wx-row{grid-template-columns:minmax(92px,auto) 1fr auto;gap:12px}
  .st-name{font-size:33px}.st-city{font-size:26px}.fact b{font-size:32px}
  a.card.cc{padding-left:16px;padding-right:16px}
}
@media (max-width:344px){
  .ko-when .time{font-size:40px}.ko-date{font-size:22px}.cd-n{font-size:25px}.cd-u{font-size:10px;letter-spacing:.02em}
  .wx-desc{font-size:16px}.wx-t b{font-size:40px}.wx-v{font-size:31px}.wx-x{font-size:23px}
  .sf>span{font-size:9px;letter-spacing:.06em}
}
@media (max-width:344px){.fact b{font-size:26px}.p2 .st-facts{gap:8px}}
/* short screens (iPhone SE size): tighter condensed cards so all of them still fit without scrolling */
@media (max-height:620px){
  .p2-c{gap:8px;padding-top:8px;padding-bottom:8px}
  a.card.cc{gap:2px;padding-bottom:5px;--ctitle:22px}
  .cc .time{font-size:28px}.cc-date{font-size:14px;margin-top:2px}.cd-c .cd-n{font-size:16px}
  .cc .wx-t b{font-size:30px}.cc .wx-ic svg{width:44px;height:33px}
  .cc .st-name{font-size:18px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
  .cc-city{font-size:12px;margin-top:2px}.cc .st-icon{width:48px;height:36px}
  .sf b{font-size:13px}.sf>span{margin-bottom:2px}
}
@media (min-width:601px){
  .ko-when .time{font-size:63px}.ko-date{font-size:34px}.cd-n{font-size:40px}.cd-u{font-size:14px}
  .cc-date,.cd-c .cd-n{white-space:nowrap}
}
"""
