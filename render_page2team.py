"""
Page 2 -- Team deep dive (away-team / home-team), reached by tapping either team's card on
Page 1. One shared module for both sides -- they're the same page, just for a different team
(Jason, 2026-09-20): render_team_block(side, opponent, which) is called once for "away" and
once for "home" from render_page1.render_p1_block.

Not a separate file: like Page 2 Game Info, the markup lives inside each game's Page 1 block
(site/game/<game_id>.html) as a hidden layer, using the exact same <div class="p2"> shell
(distinguished by data-page="away-team" / "home-team"), so it reuses Page 2's positioning CSS
wholesale. The open/close motion, gestures and hash routing live in render_page1.P1_JS,
generalized to look up whichever detail's data-page the tapped card asked for (search "detail
registry" in P1_JS) rather than being hardcoded to Game Info alone.

Expanded view only, no condensed alternative (Jason: these pages are information-heavy enough
that condensing them into one screen isn't worth it) -- so this file only builds the .p2-l
deck, not a .p2-c layer, and the +/- toggle is hidden by CSS while one of these is open.

Four cards, in Framer's order (from the "page2awayteam"/"page2hometeam" mocks, 2026-09-20),
restyled to the site's standards the same way Page 2 Game Info was:
  1. Overview  -- head coach + offensive/defensive play-callers (coaches.py) beside a big
                  bye-week number; this matchup's rest days / miles traveled; last 4 games;
                  division standings with W / L / T headings. The team's helmet, location
                  name and record live in the top bar while the page is open (team_bar_heads)
  2. Injuries  -- the full report (not Page 1's top-3), same Out/Doubtful/Questionable
                  treatment already on the site (nflverse's report has no "IR" status to
                  show -- see the Items to Address doc)
  3. Offense/Defense -- an expanded stat card: the big number IS the actual value (not the
                  rank, unlike Page 1's own cards), colored and ranked underneath with Page 1's
                  exact green-to-red scale (render_page1.rank_color/ordinal, unchanged).
                  Red Zone % and Time of Possession show as unavailable -- not in nflverse's
                  weekly team stats (confirmed live, see the Items to Address doc), not guessed.
  4. Schedule  -- full regular season, results with scores, upcoming games with kickoff time,
                  bye week marked, running record after each game

Data: data/matchups.json -> game_details[<id>][away|home]["team_page"] (page1_data.py).
Defensive like the rest of the site: a missing value shows "—", and a missing side's whole
page becomes "" (render_p1_block already treats an empty page2-shaped block as "nothing to
open here").
"""

import html

DASH = "—"


def esc(v):
    return html.escape(str(v), quote=True)


# ---------------------------------------------------------------- formatting

def _fmt_int(v):
    if v is None:
        return DASH
    return f"{int(round(v)):,}"


def _fmt_signed(v):
    if v is None:
        return DASH
    return f"{int(round(v)):+d}"


def _fmt_pct(rec):
    gp = rec["wins"] + rec["losses"] + rec.get("ties", 0)
    pct = (rec["wins"] + 0.5 * rec.get("ties", 0)) / gp if gp else 0.0
    return f"{pct:.3f}".lstrip("0") if pct < 1 else "1.000"


def _fmt_record(rec):
    w, l, t = rec.get("wins", 0), rec.get("losses", 0), rec.get("ties", 0)
    return f"{w}-{l}-{t}" if t else f"{w}-{l}"


def _fmt_date(gameday):
    from render_page1 import MONTHS_UPPER, DAY_NAMES
    from datetime import date
    try:
        d = date.fromisoformat(str(gameday)[:10])
    except (TypeError, ValueError):
        return "Date TBD", ""
    return f"{MONTHS_UPPER[d.month - 1]} {d.day}", DAY_NAMES[d.weekday()]


def _fmt_time(gametime):
    try:
        hh, mm = (int(x) for x in str(gametime).split(":")[:2])
    except (TypeError, ValueError):
        return "TBD"
    suffix = "AM" if hh < 12 else "PM"
    return f"{hh % 12 or 12}:{mm:02d} {suffix} ET"


# ---------------------------------------------------------------- overview card

def _next_block(team_page, which, prefix):
    """which = "away" | "home" -- decides whether this team's next line reads "@ OPP" or "vs OPP"."""
    from render_page1 import helmet_img
    nxt = team_page.get("next") or {}
    opp = nxt.get("opponent")
    date_line, weekday = _fmt_date(nxt.get("gameday"))
    vs = "@" if which == "away" else "vs"
    facts = [
        ("REST", f'{nxt["rest_days"]}<small> DAYS</small>' if nxt.get("rest_days") is not None else DASH),
        ("TRAVELED", f'{_fmt_int(nxt.get("miles_traveled"))}<small> MI</small>' if nxt.get("miles_traveled") is not None else DASH),
    ]
    fact_html = "".join(f'<div class="ov-fact"><b>{v}</b><span>{esc(k)}</span></div>' for k, v in facts)
    opp_html = (
        '<div class="ov-next">'
        f'{helmet_img(opp, 40, prefix=prefix)}<div class="ov-next-txt">'
        f'<span class="ov-next-lbl">NEXT</span><span class="ov-next-vs">{vs} <span class="abbr">{esc(opp or "TBD")}</span></span>'
        f'<span class="ov-next-date">{esc(date_line)} {esc(weekday).upper()}</span></div></div>'
    )
    return f'<div class="ov-top">{opp_html}<div class="ov-facts">{fact_html}</div></div>'


# Full location names for the team page's top bar (Jason, 2026-09-28). The two Los Angeles and two
# New York teams share a city, so each gets its initial. Keys are nflverse abbreviations (the
# Rams are "LA"; "LAR" kept as an alias).
LOCATION_NAMES = {
    "ARI": "Arizona", "ATL": "Atlanta", "BAL": "Baltimore", "BUF": "Buffalo", "CAR": "Carolina", "CHI": "Chicago",
    "CIN": "Cincinnati", "CLE": "Cleveland", "DAL": "Dallas", "DEN": "Denver", "DET": "Detroit", "GB": "Green Bay",
    "HOU": "Houston", "IND": "Indianapolis", "JAX": "Jacksonville", "KC": "Kansas City", "LV": "Las Vegas",
    "LA": "Los Angeles R", "LAR": "Los Angeles R", "LAC": "Los Angeles C", "MIA": "Miami", "MIN": "Minnesota",
    "NE": "New England", "NO": "New Orleans", "NYG": "New York G", "NYJ": "New York J", "PHI": "Philadelphia",
    "PIT": "Pittsburgh", "SEA": "Seattle", "SF": "San Francisco", "TB": "Tampa Bay", "TEN": "Tennessee",
    "WAS": "Washington",
}


def _team_bar_head(side, opp, which, prefix):
    """One team page's version of the top bar: helmet, location name, record, opponent faded.
    An away team reads left to right (helmet NEW ENGLAND 1-2 ... @ BUF); a home team's is the
    mirror image (NE @ ... 3-0 BUFFALO helmet), its helmet facing in as home helmets do."""
    from render_page1 import helmet_img
    team = side.get("team")
    rec = _fmt_record(side.get("record") or {})
    opp_abbr = f'<span class="abbr">{esc(opp or "TBD")}</span>'
    opp_html = f"@ {opp_abbr}" if which == "away" else f"{opp_abbr} @"
    return (f'<div class="tp-head tp-{which}" aria-hidden="true">{helmet_img(team, 46, which == "home", prefix)}'
            f'<span class="tp-name">{esc(LOCATION_NAMES.get(team, team or "TBD"))}</span>'
            f'<span class="tp-rec">{esc(rec)}</span><span class="tp-opp">{opp_html}</span></div>')


def team_bar_heads(away, home, prefix="../"):
    """Both teams' bar headers, spliced into Page 1's top bar; CSS shows the one whose team page
    is open (Jason, 2026-09-28 -- the bar used to show the matchup with the other team faded)."""
    return (_team_bar_head(away or {}, (home or {}).get("team"), "away", prefix)
            + _team_bar_head(home or {}, (away or {}).get("team"), "home", prefix))


def _recent_games_block(schedule, team, prefix):
    played = [e for e in schedule if e.get("final")]
    recent = list(reversed(played[-4:]))
    if not recent:
        return '<p class="ov-empty">No games played yet</p>'
    rows = []
    for e in recent:
        date_line, _wd = _fmt_date(e.get("gameday"))
        vs = "@" if not e.get("home") else "vs"
        res = e.get("result") or ""
        cls = {"W": "win", "L": "loss", "T": "tie"}.get(res, "")
        rows.append(
            '<li class="rg-row">'
            f'<span class="rg-date">{esc(date_line)}</span><span class="rg-vs">{vs}</span>'
            f'<span class="rg-opp abbr">{esc(e.get("opponent") or "")}</span>'
            f'<span class="rg-res rg-{cls}">{esc(res)}</span>'
            f'<span class="rg-score">{esc(_fmt_int(e["score"]["team"]))}-{esc(_fmt_int(e["score"]["opp"]))}</span>'
            "</li>"
        )
    return f'<ul class="rg-list">{"".join(rows)}</ul>'


def _standings_block(standings, team):
    from render_page1 import helmet_img
    if not standings or not standings.get("rows"):
        return ""
    rows = "".join(
        f'<li class="st-row{" is-you" if r["team"] == team else ""}">'
        f'{helmet_img(r["team"], 22, prefix="../")}<span class="st-team abbr">{esc(r["team"])}</span>'
        f'<span class="st-w">{r["wins"]}</span><span class="st-l">{r["losses"]}</span><span class="st-t">{r["ties"]}</span>'
        f'<span class="st-pct">{esc(_fmt_pct(r))}</span></li>'
        for r in standings["rows"]
    )
    head = ('<div class="st-headrow" aria-hidden="true"><span></span><span></span>'
            '<span>W</span><span>L</span><span>T</span><span></span></div>')
    return (f'<div class="ov-standings"><h3>{esc(standings["division"])}</h3>'
            f'{head}<ul class="st-list">{rows}</ul></div>')


def _staff_block(coaches):
    """Head coach plus whoever calls each side's plays (coaches.py), one row per person --
    name first, then everything that person does (Jason, 2026-09-28: no name listed twice).
    So a play-calling head coach is one row, "HC, Off. plays", and a coordinator who calls
    his side just shows his title, "OC" / "DC" (Jason, 2026-09-28)."""
    if not coaches:
        return ""
    people = []   # [name, [roles]] in order: head coach, offense, defense

    def add(name, role):
        if not name:
            return
        for p in people:
            if p[0] == name:
                if role not in p[1]:
                    p[1].append(role)
                return
        people.append([name, [role]])

    add(coaches.get("head_coach"), "HC")
    for key, duty in (("off_caller", "Off. plays"), ("def_caller", "Def. plays")):
        c = coaches.get(key) or {}
        # A coordinator only makes this list by calling his side's plays, so his title says it
        # all ("OC"); only a head coach needs the duty spelled out ("HC, Off. plays").
        if c.get("role") and c.get("role") != "HC":
            add(c.get("name"), c["role"])
        else:
            add(c.get("name"), duty)
    if not people:
        return ""
    rows = "".join(
        f'<li class="ov-coach"><b class="ov-coach-name">{esc(name)}</b>'
        f'<span class="ov-coach-role">{esc(", ".join(roles))}</span></li>'
        for name, roles in people
    )
    return f'<ul class="ov-staff">{rows}</ul>'


def overview_body(side, team_page, which, prefix):
    """(Jason, 2026-09-28) the team's helmet, name and record moved up into the top bar
    (team_bar_heads), so the card opens with the coaching staff and a big bye-week number."""
    team = side.get("team")
    bye_week = (team_page.get("next") or {}).get("bye_week")
    bye_html = f'<div class="ov-byebig"><b>{esc(bye_week)}</b><span>BYE WK</span></div>' if bye_week else ""
    lead = _staff_block(team_page.get("coaches")) + bye_html
    return (
        (f'<div class="ov-lead">{lead}</div>' if lead else "")
        + _next_block(team_page, which, prefix)
        + '<h3 class="ov-h">Recent Games</h3>'
        + _recent_games_block(team_page.get("schedule") or [], team, prefix)
        + _standings_block(team_page.get("standings"), team)
    )


# ---------------------------------------------------------------- injuries card

def injuries_body(team_page):
    """Status reads as a colored dot (matching Page 1's cards), plus nflverse's injury
    designation (Knee, Ankle, ...) where it's reported."""
    rows = team_page.get("injuries_full") or []
    if not rows:
        return '<p class="ov-empty">No injuries reported</p>'
    cls_map = {"Out": "out", "Doubtful": "doubt", "Questionable": "ques"}
    items = []
    for r in rows:
        status = r.get("status") or ""
        if r.get("designation"):
            status = f"{status} · {r['designation']}"
        items.append(
            f'<li><span class="inj-who"><span class="inj-pos">{esc(r.get("position") or "")}</span>'
            f'<span class="inj-name">{esc(r.get("name") or "")}</span></span>'
            f'<span class="inj-s"><i class="inj-dot inj-{cls_map.get(r.get("status"), "ques")}"></i>{esc(status)}</span></li>'
        )
    return f'<ul class="l-inj full-inj">{"".join(items)}</ul>'


# ---------------------------------------------------------------- offense/defense card

STAT_ROWS = [
    ("points", "Points", "per game", True),
    ("pass_tds", "Total Passing TDs", None, True),
    ("rush_tds", "Total Rushing TDs", None, True),
    ("all_yards", "All Yards", "per game", True),
    ("pass_yards", "Passing Yards", "per game", True),
    ("rush_yards", "Rushing Yards", "per game", True),
    ("red_zone_pct", "Red Zone %", None, True),
]
SINGLE_STAT_ROWS = [
    ("turnover_margin", "Turnover Diff."),
    ("top", "ToP"),
    ("sacks", "D. Sacks"),
    ("def_ints", "Defensive INTs"),
]


def _stat_cell(value, rank, signed=False):
    from render_page1 import rank_color, ordinal
    if value is None or rank is None:
        return f'<div class="stat"><span class="stat-v na">{DASH}</span></div>'
    c = rank_color(rank)
    disp = _fmt_signed(value) if signed else _fmt_int(value)
    # Only the rank carries the tier color -- the raw value stays plain so it doesn't compete
    # with it (Jason, 2026-09-24).
    return (f'<div class="stat">'
            f'<span class="stat-v">{disp}</span><span class="stat-rank" style="color:{c}">{rank}{esc(ordinal(rank))}</span></div>')


def _stat_row(label, sub, left_html, right_html):
    sub_html = f'<span class="stat-sub">{esc(sub)}</span>' if sub else ""
    return (f'<div class="stat-row">{left_html}'
            f'<div class="stat-lbl">{esc(label)}{sub_html}</div>{right_html}</div>')


def _stat_row_solo(label, cell_html):
    """Turnover diff., ToP, sacks, INTs aren't offense- or defense-specific, so they don't get
    a paired column each -- just their one value+rank next to the title, not aligned to the
    Offense/Defense columns above (Jason, 2026-09-24)."""
    return f'<div class="stat-row stat-row-solo">{cell_html}<div class="stat-lbl">{esc(label)}</div></div>'


def offense_defense_body(team_stats):
    stats = team_stats or {}
    rows = []
    for key, label, sub, _hb in STAT_ROWS:
        s = stats.get(key) or {}
        left = _stat_cell(s.get("off_value"), s.get("off_rank"))
        right = _stat_cell(s.get("def_value"), s.get("def_rank"))
        rows.append(_stat_row(label, sub, left, right))
    for key, label in SINGLE_STAT_ROWS:
        s = stats.get(key)
        cell = _stat_cell((s or {}).get("value"), (s or {}).get("rank"), signed=(key == "turnover_margin"))
        rows.append(_stat_row_solo(label, cell))
    return (
        '<div class="stat-head"><span>Offense</span><span></span><span>Defense</span></div>'
        f'<div class="stat-list">{"".join(rows)}</div>'
    )


# ---------------------------------------------------------------- schedule card

def _fmt_date_short(gameday):
    """'2026-10-19' -> ('MON', '10/19') -- matches Framer's "MON, 10/19" schedule rows."""
    from datetime import date
    from render_page1 import DAY_NAMES
    try:
        d = date.fromisoformat(str(gameday)[:10])
    except (TypeError, ValueError):
        return None, None
    return DAY_NAMES[d.weekday()][:3].upper(), f"{d.month}/{d.day}"


def schedule_body(team_page, prefix):
    """
    One line per week, Framer's order (week, date, opponent, result-or-time, running record).
    Every week has to be on screen with no scrolling inside the card (Jason, 2026-09-20), so
    rows stay compact -- one line each, no stacked sub-rows, network dropped (it's always "TV
    TBD" right now anyway, see the Items to Address doc on that gap).
    """
    from render_page1 import helmet_img
    schedule = team_page.get("schedule") or []
    rows = []
    for e in schedule:
        wk = e.get("week")
        if e.get("bye"):
            rows.append(f'<li class="sc-row sc-bye"><span class="sc-wk">{wk}</span><span class="sc-bye-lbl">BYE WEEK</span></li>')
            continue
        day, num_date = _fmt_date_short(e.get("gameday"))
        date_html = f'<span class="sc-date">{esc(day)} {esc(num_date)}</span>' if day else '<span class="sc-date na">DATE TBD</span>'
        opp = e.get("opponent")
        vs = "@" if not e.get("home") else "vs"
        if e.get("final"):
            res = e.get("result") or ""
            cls = {"W": "win", "L": "loss", "T": "tie"}.get(res, "")
            mid = (f'<span class="sc-res sc-{cls}">{esc(res)}</span>'
                   f'<span class="sc-score">{esc(_fmt_int(e["score"]["team"]))}-{esc(_fmt_int(e["score"]["opp"]))}</span>')
        else:
            mid = f'<span class="sc-time">{esc(_fmt_time(e.get("gametime")))}</span>'
        rec = _fmt_record(e.get("record_after") or {})
        rows.append(
            '<li class="sc-row">'
            f'<span class="sc-wk">{wk}</span>{date_html}'
            f'<span class="sc-vs">{vs}</span>{helmet_img(opp, 20, prefix=prefix)}<span class="sc-opp abbr">{esc(opp or "")}</span>'
            f'<span class="sc-mid">{mid}</span><span class="sc-rec">{esc(rec)}</span>'
            "</li>"
        )
    return f'<ul class="sc-list">{"".join(rows)}</ul>'


# ---------------------------------------------------------------- the layer

def render_team_block(side, which, prefix="../"):
    """
    The hidden .p2-shaped layer for one team, spliced into Page 1's .p1 block.
    which = "away" | "home" (matches the data-detail value Page 1's team cards already
    carry, and becomes this layer's data-page). Empty string if the team has no page data.
    """
    team_page = side.get("team_page")
    if not isinstance(team_page, dict):
        return ""
    from render_page1 import UP, DOWN
    cards = [
        ("overview", "Overview", overview_body(side, team_page, which, prefix)),
        ("injuries", "Injuries", injuries_body(team_page)),
        ("stats", "Team Stats", offense_defense_body(team_page.get("stats"))),
        ("schedule", "Schedule", schedule_body(team_page, prefix)),
    ]
    slots = "".join(
        f'<section class="slot"><a class="card p2k p2k-{cid}" tabindex="-1" aria-label="{esc(name)}">'
        f'<span class="peek peek-top">{DOWN}<span>{esc(name)}</span></span><div class="body">{body}</div>'
        f'<span class="peek peek-bot">{UP}<span>{esc(name)}</span></span></a></section>'
        for cid, name, body in cards
    )
    dots = "".join(f'<button class="dot" type="button" aria-label="{esc(name)}"></button>' for _c, name, _b in cards)
    label = f'{esc(side.get("team") or "Team")} team info'
    return (f'<div class="p2 p2-team" data-page="{esc(which)}-team" aria-label="{label}" role="region">'
            f'<div class="p2-view p2-l deck">{slots}</div><nav class="dots p2-dots" aria-label="Cards">{dots}</nav></div>')


# ---------------------------------------------------------------- styles
# Appended to Page 1's stylesheet (same <style id="p1-css">), same as Page 2 Game Info's P2_CSS.

P3_CSS = r"""
/* ===== Team pages: away-team / home-team deep dive (2026-09-20) =====
   Reuses Page 2's .p2 shell (position/inset/background) via the shared class; data-page
   tells the detail-open CSS below which layer to show. Expanded view only, no condensed
   layer -- see render_page1.P1_JS's detail registry and the .toggle hiding rule below. */
.p1[data-detail="away-team"] .p2[data-page="away-team"],
.p1[data-detail="home-team"] .p2[data-page="home-team"]{display:block}
/* No condensed view for these two -- hide the +/- toggle rather than let it switch to a
   layout that doesn't exist. */
.p1[data-detail="away-team"] .toggle,
.p1[data-detail="home-team"] .toggle{display:none}
/* The top bar names the team whose page is open (Jason, 2026-09-28, was the matchup with the
   other team faded): helmet, location name, record, and the opponent faded at the far side.
   The away team's reads left to right; the home team's is its mirror image, helmet at the
   right edge facing in (markup: team_bar_heads). */
.bar .tp-head{display:none}
.p1[data-detail="away-team"] .bar .teams,.p1[data-detail="home-team"] .bar .teams{visibility:hidden}
.p1[data-detail="away-team"] .bar .tp-away,.p1[data-detail="home-team"] .bar .tp-home{display:flex}
.bar-in{position:relative}
.tp-head{position:absolute;inset:0;align-items:center;gap:10px;padding:0 4px}
.tp-head img{width:46px;height:46px;flex:none;display:block}
.tp-name{font-family:Saira,Inter,system-ui,sans-serif;font-weight:800;font-style:italic;font-variation-settings:'wdth' 95;
  font-size:18px;letter-spacing:.01em;text-transform:uppercase;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
.tp-rec{font-size:16px;font-weight:700;margin-left:10px;font-variant-numeric:tabular-nums;flex:none}
.tp-opp{margin-left:auto;padding-left:10px;color:var(--text-3);font-size:16px;white-space:nowrap;flex:none}
.tp-opp .abbr{font-size:17px}
.tp-home{flex-direction:row-reverse}
.tp-home .tp-rec{margin-left:0;margin-right:10px}
.tp-home .tp-opp{margin-left:0;margin-right:auto;padding-left:0;padding-right:10px}
.p2-team .p2-l{padding-top:0}
/* Overview stacks from the top (2026-09-28): the shared .p2 rule spreads a card's sections
   evenly, which opened a gap above the division table; now it sits right under recent games */
.p2 .slot .p2k-overview .body{justify-content:flex-start}
/* Cards inside the team pages don't link anywhere (yet) -- no hover/focus affordance
   suggesting otherwise (Jason, 2026-09-20). The swipe-between-cards gesture and dots
   still work; only the pointer/hover/focus-ring styling is suppressed. */
.p2-team a.card{cursor:default}
.p2-team a.card:focus-visible{outline:none}
.p2-team .slot.active a.card:hover,.p2-team .slot.active a.card:focus-visible{transform:none;border-color:var(--tile-border)}
.p2-team .slot.below a.card:hover,.p2-team .slot.above a.card:hover{border-color:var(--tile-border-soft)}
/* The card opens with the coaching staff (left) and the bye week as a big number (right) --
   Jason, 2026-09-28; the helmet/abbreviation/record header that used to lead moved to the bar */
.ov-lead{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:4px 4px 14px}
.ov-byebig{display:flex;flex-direction:column;align-items:center;flex:none;margin-left:auto}
.ov-byebig b{font-family:Teko,Inter,system-ui,sans-serif;font-weight:700;font-size:46px;line-height:1;color:var(--text-2)}
.ov-byebig span{font-size:11px;font-weight:700;letter-spacing:.08em;color:var(--text-2)}
.ov-top{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:14px 4px;
  border-top:1px solid var(--tile-border-soft);border-bottom:1px solid var(--tile-border-soft);margin:0 0 12px}
.ov-next{display:flex;align-items:center;gap:10px;min-width:0}
.ov-next img{width:40px;height:40px;display:block;flex:none}
.ov-next-txt{display:flex;flex-direction:column;min-width:0}
.ov-next-lbl{font-size:10px;font-weight:700;letter-spacing:.08em;color:var(--text-2)}
.ov-next-vs{font-size:16px;font-weight:700;white-space:nowrap}
.ov-next-vs .abbr{font-size:1em}
.ov-next-date{font-size:12px;color:var(--text-2);white-space:nowrap}
.ov-facts{display:flex;gap:14px;flex:none}
.ov-fact{display:flex;flex-direction:column;align-items:center;gap:1px}
.ov-fact b{font-size:15px;font-family:Teko,Inter,system-ui,sans-serif;font-weight:700}
.ov-fact b small{font-size:9px;font-weight:400;font-family:Inter,sans-serif}
.ov-fact span{font-size:9px;color:var(--text-2);letter-spacing:.04em}
/* Coaching staff: one row per person (Jason, 2026-09-28), names in one column and roles
   lined up in the next, at the top of the card beside the bye week */
.ov-staff{list-style:none;display:grid;grid-template-columns:auto auto;column-gap:22px;row-gap:6px;padding:0;margin:0;min-width:0}
.ov-coach{display:contents}
.ov-coach-name{font-size:15px;font-weight:700}
.ov-coach-role{font-size:12px;color:var(--text-2);white-space:nowrap;letter-spacing:.04em;align-self:center}
.ov-h{font-size:13px;font-weight:700;padding:4px 4px 6px;text-transform:uppercase;letter-spacing:.04em;color:var(--text-2)}
.ov-empty{padding:8px 4px;color:var(--text-2);font-size:13px}
.rg-list,.st-list,.sc-list{list-style:none;display:flex;flex-direction:column}
/* Recent games (2026-09-28): no helmets, tighter rows, and the result and score each in a
   fixed-width column at the right so W/L and the scores line up down the list */
.rg-row{display:flex;align-items:center;gap:8px;padding:3px 4px;border-bottom:1px solid var(--tile-border-soft);font-size:13px}
.rg-date{color:var(--text-2);width:48px;flex:none}
.rg-vs{color:var(--text-3);width:18px;text-align:center;flex:none}
.rg-opp{flex:1}
.rg-res{font-weight:700;width:18px;text-align:center;flex:none;margin-left:auto}
.rg-win{color:var(--win)}.rg-loss{color:var(--loss)}.rg-tie{color:var(--tie)}
.rg-score{color:var(--text-2);width:44px;text-align:right;flex:none;font-variant-numeric:tabular-nums}
.ov-standings{margin-top:16px}
.ov-standings h3{font-size:13px;font-weight:700;padding:0 4px 6px;text-transform:uppercase;letter-spacing:.04em;color:var(--text-2)}
/* W / L / T headings over the standings columns (2026-09-28); same grid as .st-row */
.st-headrow{display:grid;grid-template-columns:22px 1fr 24px 24px 24px 52px;gap:6px;padding:0 4px 2px;font-size:11px;
  font-weight:700;letter-spacing:.04em;color:var(--text-3)}
.st-headrow span{text-align:center}
.st-row{display:grid;grid-template-columns:22px 1fr 24px 24px 24px 52px;align-items:center;gap:6px;padding:5px 4px;font-size:13px}
.st-row.is-you{background:var(--tile-hover);border-radius:8px;font-weight:700}
.st-row img{width:22px;height:22px}
.st-w,.st-l,.st-t{text-align:center;color:var(--text-2)}
.st-pct{text-align:right;color:var(--text-2);font-variant-numeric:tabular-nums}
.full-inj{gap:2px}
.full-inj li{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:7px 2px;
  border-bottom:1px solid var(--tile-border-soft)}
.full-inj .inj-name{font-weight:700}
/* Status reads as a colored dot, not colored text (Jason, 2026-09-20) -- shared .inj-dot/.inj-s
   rules live in render_page1.P1_CSS so Page 1's own cards match. */
/* Team Stats card (renamed from "Offense/Defense", Jason, 2026-09-20): titles centered over
   their own column, matching the value columns below rather than pushed to the edges.
   Fixed-width side columns, not 1fr (2026-09-24): each row is its own independent grid, and
   the middle "auto" label column is a different width per row ("Points" vs "Total Passing
   TDs" vs "D. Sacks"), so with 1fr sides the leftover space split between them -- and thus
   where a centered value actually landed -- also changed row to row, drifting out of line
   instead of stacking in one straight column under "Offense"/"Defense". Fixed side columns
   pin that value column to the same x on every row (and in the header); the label column
   goes 1fr instead, absorbing whatever's left and centering its own text within it. */
.stat-head{display:grid;grid-template-columns:72px 1fr 72px;padding:4px 2px 10px;font-size:13px;font-weight:700;
  text-transform:uppercase;letter-spacing:.04em;color:var(--text-2)}
.stat-head span{text-align:center}
.stat-list{display:flex;flex-direction:column}
/* Value + rank share one line, not two (2026-09-24) -- 11 rows stacked at the old two-line
   height ran past the bottom of the card on a short phone screen, hiding Sacks/INTs below the
   fold with no scroll to reach them. One line per row buys back enough height for all of them
   to fit. */
.stat-row{display:grid;grid-template-columns:72px 1fr 72px;align-items:center;gap:8px;padding:6px 2px;
  min-height:44px;border-bottom:1px solid var(--tile-border-soft)}
/* width:100% so this fills its fixed-width column instead of shrinking to its own content --
   otherwise a short value ("0") wouldn't be centered on the same axis as a wide one ("263"). */
.stat{display:flex;flex-direction:row;align-items:baseline;justify-content:center;gap:3px;width:100%}
/* Rank sits on the outside of its value, away from the label between them, on both sides
   (2026-09-24) -- the offense column is first in the DOM (value then rank, left to right), so
   reversing just that one puts its rank on the card's outer edge to match the defense column,
   which already reads that way without changing anything. */
.stat-row:not(.stat-row-solo) > .stat:first-child{flex-direction:row-reverse}
/* Turnover diff./ToP/sacks/INTs aren't offense- or defense-specific, so they get their own
   plainer row instead of the two aligned value columns above: just the value+rank next to its
   title, sized to its own content rather than pinned to the 72px columns (2026-09-24). */
.stat-row-solo{display:flex;align-items:baseline;justify-content:flex-start;gap:12px;padding:6px 2px 6px 6px}
.stat-row-solo .stat{width:auto;justify-content:flex-start}
.stat-row-solo .stat-lbl{display:block;text-align:left}
.stat-v{font-family:Teko,Inter,system-ui,sans-serif;font-weight:700;font-size:28px;line-height:1;font-variant-numeric:tabular-nums}
.stat-v.na{color:var(--text-3);font-family:Inter,sans-serif;font-size:20px}
.stat-rank{font-size:11px;font-weight:700}
.stat-lbl{text-align:center;font-size:12px;color:var(--ink);display:flex;flex-direction:column;
  align-items:center;justify-content:center;line-height:1.25}
.stat-sub{font-size:10px;font-weight:400;color:var(--text-2)}
/* Compact by design -- every week has to be visible on the card with no scrolling
   (Jason, 2026-09-20), so this trades some size for fitting all ~18 rows at once. */
.sc-row{display:grid;grid-template-columns:16px 50px 12px 20px 1fr auto 42px;align-items:center;gap:6px;
  padding:4px 3px;border-bottom:1px solid var(--tile-border-soft);font-size:11.5px;line-height:1.15}
.sc-wk{color:var(--text-2);text-align:right;font-size:11px}
.sc-date{color:var(--text-2);white-space:nowrap;font-size:10.5px}
.sc-date.na{color:var(--text-3)}
.sc-vs{color:var(--text-3);text-align:center}
.sc-row img{width:20px;height:20px}
.sc-opp{font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.sc-mid{display:flex;align-items:baseline;justify-content:flex-end;gap:5px;white-space:nowrap}
.sc-res{font-weight:700}
.sc-win{color:var(--win)}.sc-loss{color:var(--loss)}.sc-tie{color:var(--tie)}
.sc-score{color:var(--text-2);font-variant-numeric:tabular-nums}
.sc-time{font-weight:700;white-space:nowrap}
.sc-rec{color:var(--text-2);text-align:right;font-variant-numeric:tabular-nums;font-size:11px}
.sc-bye{grid-template-columns:16px 1fr;color:var(--text-2)}
.sc-bye-lbl{letter-spacing:.06em;font-size:10px;font-weight:700}
/* Short screens (iPhone SE-class heights and similar): the card's own height is whatever's
   left between the top/bottom bars, so a shorter phone leaves less room for it regardless of
   width -- tighten the row height further so all 11 rows still fit without scrolling. */
@media (max-height:700px){
  .ov-lead{padding:0 4px 8px}
  .ov-byebig b{font-size:38px}
  .ov-top{padding:8px 4px;margin:0 0 8px}
  .ov-staff{row-gap:4px}
  .rg-row{padding:2px 4px}
  .ov-standings{margin-top:6px}
  .st-row{padding:3px 4px}
  .stat-head{padding:4px 2px 6px}
  .stat-row{min-height:36px;padding:4px 2px}
}
@media (max-width:400px){
  .stat-v{font-size:23px}
  .stat-head{grid-template-columns:62px 1fr 62px}
  .stat-row{grid-template-columns:62px 1fr 62px}
  .ov-facts{gap:10px}
  .st-row,.st-headrow{grid-template-columns:20px 1fr 20px 20px 20px 46px}
  .sc-row{grid-template-columns:14px 44px 10px 18px 1fr auto 38px;gap:4px;font-size:11px;padding:3px 2px}
}
"""
