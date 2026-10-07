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
                  treatment already on the site, then the team's injured reserve (top three,
                  starters first) and man-games lost -- IR comes from the weekly rosters, the
                  report itself has no IR status (reserve.py)
  3. Offense/Defense -- an expanded stat card: the big number IS the actual value (not the
                  rank, unlike Page 1's own cards), colored and ranked underneath with Page 1's
                  exact green-to-red scale (render_page1.rank_color/ordinal, unchanged).
                  3rd Down % (2026-10-03, in place of Red Zone %) comes from play-by-play.
                  Time of Possession shows as unavailable -- not in nflverse's
                  weekly team stats (confirmed live, see the Items to Address doc), not guessed.
  4. Schedule  -- full regular season, results with scores, upcoming games with kickoff time,
                  bye week marked, running record after each game

Data: data/matchups.json -> game_details[<id>][away|home]["team_page"] (page1_data.py).
Defensive like the rest of the site: a missing value shows "—", and a missing side's whole
page becomes "" (render_p1_block already treats an empty page2-shaped block as "nothing to
open here").
"""

import html

from render_page2players import esc_name

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
        f'<li class="ov-coach"><b class="ov-coach-name">{esc_name(name)}</b>'
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

# A row's name and status share one line on a phone (2026-10-03): when both won't fit, the status
# steps down -- "No Practice · Not injury related" -> "DNP · Not injury related" -> "DNP" -- rather
# than the name being cut to "J..". Widths are estimated from the card's fonts, measured on a 375px
# screen: the bold name about 8.5px a character, the status 7.4px, and 232px for the two together.
NAME_PX, STATUS_PX, ROW_PX = 8.5, 7.4, 232


def _fit_status(name, choices):
    """The first of `choices` (longest first) that fits beside `name`, else the last."""
    for label in choices:
        if NAME_PX * len(name) + STATUS_PX * len(label) <= ROW_PX:
            return label
    return choices[-1]


def _inj_items(rows, cls_map, ir_tag=True, cut=None, more_base=0, more_fmt="+{n} more"):
    """ir_tag=False for the Injured Reserve list itself, where every row already says IR.
    cut(row) -> the step at which P1_JS's injFit may hide that row on a short screen (None: never,
    short of its last resort); the line after the list then counts what's hidden, on top of
    more_base players the list already leaves out."""
    items = []
    for r in rows:
        status = r.get("status") or ""
        short = r.get("status_short") or status
        if r.get("kind"):   # a game-day absence: its short status, plus the quarter / starter note
            extra = [x for x in (r.get("designation"), "Starter" if r.get("kind") == "ina" and r.get("starter") else None) if x]
            choices = [f"{short} · {' · '.join(extra)}"] if extra else []
            choices.append(short)
        elif r.get("designation"):
            choices = [f"{status} · {r['designation']}", f"{short} · {r['designation']}", short]
        else:
            choices = [status, short]
        tag_text = (" · R" if r.get("rookie") else "") + (" · IR" if ir_tag and r.get("ir") else "")
        status = _fit_status((r.get("name") or "") + tag_text, choices)
        tags = (" · <span class=rk>R</span>" if r.get("rookie") else "") + (" · <span class=ir>IR</span>" if ir_tag and r.get("ir") else "")
        step = cut(r) if cut else None
        items.append(
            f'<li{f" data-cut={step}" if step else ""}><span class="inj-who"><span class="inj-pos">{esc(r.get("position") or "")}</span>'
            f'<span class="inj-name">{esc_name(r.get("name"))}</span>'
            f'{f"<span class=inj-rk>{tags}</span>" if tags else ""}</span>'
            f'<span class="inj-s"><i class="inj-dot inj-{cls_map.get(r.get("status"), "ques")}"></i>{esc(status)}</span></li>'
        )
    return (f'<ul class="l-inj full-inj">{"".join(items)}</ul>'
            f'<p class="ov-empty inj-more" data-base="{more_base}" data-fmt="{esc(more_fmt)}"'
            f'{"" if more_base else " hidden"}>{esc(more_fmt.format(n=more_base))}</p>')


IR_SHOWN = 3   # the IR list's top three, starters first (reserve.py sorts); the rest are counted

# What gives way, in order, when the card won't fit its screen (Jason, 2026-10-07) -- it never
# scrolls. P1_JS's injFit first tightens the spacing, then hides each step in turn until it fits:
CUT_INACTIVE_BACKUPS = 1   # inactive non-starters with no injury (healthy scratches) -> "+N more"
CUT_IR_BACKUPS = 2         # the IR list's non-starters
CUT_IR_LIST = 3            # the IR section down to one line: how many, and the man-games lost
CUT_QUESTIONABLE = 4       # Questionable / Limited players on the report
# "Left the Game" and Out / Doubtful players are in no step; only injFit's last resort (a screen
# too short even for them, like a phone on its side) hides those, from the bottom up.


def _ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def _ir_section(team_page, cls_map):
    """The team's injured reserve (2026-10-03): three players, starters first, a count of the rest,
    then its man-games lost this season with the league rank (reserve.man_games_lost). On a short
    screen it shrinks to its starters, then to one line (.inj-irline) in place of all of it."""
    ir = team_page.get("injured_reserve") or []
    mgl = team_page.get("man_games_lost") or {}
    if not ir and not mgl.get("games"):
        return ""
    parts = ['<h3 class="ov-h inj-h">Injured Reserve</h3>']
    if ir:
        parts.append(_inj_items(ir[:IR_SHOWN], cls_map, ir_tag=False,
                                cut=lambda r: None if r.get("starter") else CUT_IR_BACKUPS,
                                more_base=max(0, len(ir) - IR_SHOWN), more_fmt=f"+{{n}} more · {len(ir)} on IR"))
    else:
        parts.append('<p class="ov-empty">Nobody on IR</p>')
    if mgl.get("games"):
        parts.append(f'<div class="inj-mgl"><span>Man-Games Lost</span><span><b>{mgl["games"]}</b>'
                     f' · {_ordinal(mgl["rank"])} most</span></div>')
    line = [f"<b>{len(ir)}</b> on IR" if ir else "Nobody on IR"]
    if mgl.get("games"):
        line.append(f'{mgl["games"]} games lost')
    return (f'<div class="inj-ir"><div data-cut={CUT_IR_LIST}>{"".join(parts)}</div>'
            f'<div class="inj-mgl inj-irline" data-show={CUT_IR_LIST} hidden><span>Injured Reserve</span>'
            f'<span>{" · ".join(line)}</span></div></div>')


def _cut_report(r):
    return CUT_QUESTIONABLE if r.get("status") in ("Questionable", "Limited") else None


def _cut_inactive(r):
    return None if r.get("starter") or r.get("designation") else CUT_INACTIVE_BACKUPS


def _after_game(rows, inactive):
    """A finished game's pre-game report, cleaned up (Jason, 2026-10-07): a player who ended up
    inactive is listed there instead, the injury added to that row ("INA · Knee") rather than
    twice, and a Questionable player who played is dropped -- that status no longer matters."""
    by_name = {r.get("name"): r for r in rows}
    inactive = [dict(r, designation=r.get("designation") or (by_name.get(r.get("name")) or {}).get("designation"))
                for r in inactive]
    out = {r.get("name") for r in inactive}
    return [r for r in rows if r.get("name") not in out and r.get("status") != "Questionable"], inactive


def injuries_body(team_page, game_absences=None):
    """Status reads as a colored dot (matching Page 1's cards), plus nflverse's injury
    designation (Knee, Ankle, ...) where it's reported. A finished game (2026-09-30) leads
    with who left injured and didn't return (DNR, red, with the quarter) and its full
    inactive list (INA, gray, starters noted), then what's left of the pre-game report.
    The team's injured reserve (2026-10-03, _ir_section) closes every version of the card under its
    own heading -- IR players are off the weekly report, so this is the one place they're listed.
    The card never scrolls (2026-10-07): it all sits in .inj-fit, which P1_JS's injFit trims to
    the screen (the CUT_ steps above)."""
    cls_map = {"Out": "out", "Doubtful": "doubt", "Questionable": "ques", "Inactive": "ina", "Did Not Return": "out",
               "No Practice": "doubt", "Limited": "ques", "IR": "out"}
    rows = team_page.get("injuries_full") or []
    ir_part = _ir_section(team_page, cls_map)
    ga = game_absences or {}
    if not ga.get("available"):
        if not rows and not ir_part:
            return '<p class="ov-empty">No injuries reported</p>'
        practice = bool(rows) and rows[0].get("practice")   # no game designations yet: the practice report stands in (page1_data)
        if not ir_part and not practice:
            return f'<div class="inj-sections inj-fit">{_inj_items(rows, cls_map, cut=_cut_report)}</div>'
        report = _inj_items(rows, cls_map, cut=_cut_report) if rows else '<p class="ov-empty">No injuries reported</p>'
        note = '<p class="ov-empty">Game statuses not out yet</p>' if practice else ""
        return (f'<div class="inj-sections inj-fit"><h3 class="ov-h inj-h">{"Practice Report" if practice else "Injury Report"}</h3>'
                f'{report}{note}{ir_part}</div>')
    report, inactive = _after_game(rows, ga.get("inactive") or [])
    parts = ['<h3 class="ov-h inj-h">Left the Game</h3>',
             _inj_items(ga["left"], cls_map) if ga.get("left") else '<p class="ov-empty">Nobody left injured</p>',
             '<h3 class="ov-h inj-h">Inactive</h3>',
             _inj_items(inactive, cls_map, cut=_cut_inactive) if inactive else '<p class="ov-empty">No inactives listed</p>']
    if report or not rows:   # a report that all folded into the lists above leaves nothing to head
        parts.append('<h3 class="ov-h inj-h">Pre-game Injury Report</h3>')
        parts.append(_inj_items(report, cls_map, cut=_cut_report) if report else '<p class="ov-empty">No injuries reported</p>')
    parts.append(ir_part)
    return f'<div class="inj-sections inj-fit">{"".join(parts)}</div>'


# ---------------------------------------------------------------- offense/defense card

STAT_ROWS = [
    ("points", "Points", "per game", True),
    ("pass_tds", "Total Passing TDs", None, True),
    ("rush_tds", "Total Rushing TDs", None, True),
    ("all_yards", "All Yards", "per game", True),
    ("pass_yards", "Passing Yards", "per game", True),
    ("rush_yards", "Rushing Yards", "per game", True),
    ("third_down_pct", "3rd Down %", None, True),
]
SINGLE_STATS = [
    ("turnover_margin", "TO Diff."),
    ("top", "ToP"),
    ("sacks", "D. Sacks"),
    ("def_ints", "Def. INTs"),
]


PCT_STATS = {"third_down_pct"}   # shown as a percentage, "42%"


def _stat_cell(value, rank, signed=False, pct=False):
    from render_page1 import rank_color, ordinal
    if value is None or rank is None:
        return f'<div class="stat"><span class="stat-v na">{DASH}</span></div>'
    c = rank_color(rank)
    disp = _fmt_signed(value) if signed else f"{_fmt_int(value)}%" if pct else _fmt_int(value)
    # Only the rank carries the tier color -- the raw value stays plain so it doesn't compete
    # with it (Jason, 2026-09-24).
    return (f'<div class="stat">'
            f'<span class="stat-v">{disp}</span><span class="stat-rank" style="color:{c}">{rank}{esc(ordinal(rank))}</span></div>')


def _stat_row(label, sub, left_html, right_html):
    sub_html = f'<span class="stat-sub">{esc(sub)}</span>' if sub else ""
    return (f'<div class="stat-row">{left_html}'
            f'<div class="stat-lbl">{esc(label)}{sub_html}</div>{right_html}</div>')


def _stat_row_singles(cells):
    """Turnover diff., ToP, sacks, INTs aren't offense- or defense-specific, so they don't get
    a paired column each (Jason, 2026-09-24). All four share one line, each value+rank over its
    title (2026-10-07) -- four rows of their own ran the card past the bottom of a phone screen."""
    tiles = "".join(f'<div class="stat-tile">{cell}<div class="stat-lbl">{esc(label)}</div></div>'
                    for label, cell in cells)
    return f'<div class="stat-row stat-row-singles">{tiles}</div>'


def offense_defense_body(team_stats):
    stats = team_stats or {}
    rows = []
    for key, label, sub, _hb in STAT_ROWS:
        s = stats.get(key) or {}
        left = _stat_cell(s.get("off_value"), s.get("off_rank"), pct=key in PCT_STATS)
        right = _stat_cell(s.get("def_value"), s.get("def_rank"), pct=key in PCT_STATS)
        rows.append(_stat_row(label, sub, left, right))
    singles = []
    for key, label in SINGLE_STATS:
        s = stats.get(key)
        singles.append((label, _stat_cell((s or {}).get("value"), (s or {}).get("rank"), signed=(key == "turnover_margin"))))
    rows.append(_stat_row_singles(singles))
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
    The W/L and the score each sit centered in their own column so they stack down the card,
    an upcoming game's kickoff time spanning both; the record only runs through the last
    finished game -- the rows after it leave it blank (Jason, 2026-10-03).
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
        rec = _fmt_record(e.get("record_after") or {}) if e.get("final") else ""
        rows.append(
            '<li class="sc-row">'
            f'<span class="sc-wk">{wk}</span>{date_html}'
            f'<span class="sc-vs">{vs}</span>{helmet_img(opp, 20, prefix=prefix)}<span class="sc-opp abbr">{esc(opp or "")}</span>'
            f'{mid}<span class="sc-rec">{esc(rec)}</span>'
            "</li>"
        )
    # --n: the row count, so the CSS can share the card's height out among them (2026-10-03)
    return f'<ul class="sc-list" style="--n:{len(rows)}">{"".join(rows)}</ul>'


# Each card's icon (Jason's icons, 2026-10-04), working like Page 1's NAV_ICONS: in front of the
# card's title and as its nav dot. Cropped to each drawing's bounds (measured with getBBox()).
# The Overview and Team Stats files also carried a few colored paths the drawing app left off the
# canvas -- invisible in the original, so only the black paths that draw the icon are kept.
TEAM_ICONS = {
    "overview": (
        '<svg viewBox="-1763 -1302 3200 2616" fill="currentColor" aria-hidden="true">'
        '<path d="M-526.405,-1241.3 C93.5862,-1384.63 664.432,-440.212 1430.12,-921.409 C1431.64,-473.095 1436.29,889.527 '
        '1436.29,889.527 C1436.29,889.527 1276.78,1122.72 627.474,1272.83 C119.004,1390.37 -698.649,513.575 -1276.06,898.77 '
        'C-1298.37,104.75 -1282.23,-912.166 -1282.23,-912.166 C-1282.23,-912.166 -832.168,-1170.62 -526.405,-1241.3 Z '
        'M-655.971,-424.313 L-286.882,-212.893 C-272.83,-224.298 -252.598,-226.58 -236.002,-217.073 L-177.744,-183.702 '
        'L-166.598,-203.161 C-154.263,-224.695 -126.609,-232.206 -105.076,-219.871 C-83.5427,-207.536 -76.0318,-179.883 '
        '-88.3665,-158.349 L-99.5129,-138.89 L-40.9381,-105.338 L-29.7917,-124.797 C-17.457,-146.33 10.1967,-153.841 '
        '31.73,-141.506 C53.2634,-129.172 60.7743,-101.518 48.4396,-79.9846 L37.2931,-60.5256 L95.8679,-26.973 '
        'L107.014,-46.4321 C119.349,-67.9654 147.003,-75.4763 168.536,-63.1417 C190.069,-50.807 197.58,-23.1533 '
        '185.246,-1.61992 L174.099,17.8391 L232.674,51.3917 L243.82,31.9326 C256.155,10.3992 283.809,2.88836 305.342,15.223 '
        'C326.875,27.5576 334.386,55.2114 322.052,76.7447 L310.905,96.2037 L367.226,128.465 C383.822,137.971 392.088,156.578 '
        '389.36,174.468 L803.594,411.748 C872.442,264.18 682.734,-225.495 318.094,-434.688 C-47.7127,-644.55 -562.441,-570.431 '
        '-655.971,-424.313 Z M-670.069,-393.107 C-723.152,-219.74 -533.028,228.211 -171.177,435.804 C184.171,639.666 '
        '652.442,569.18 778.161,446.314 C780.307,444.217 784.298,439.977 784.298,439.977 L774.328,434.266 L371.789,203.685 '
        'C357.823,214.067 338.426,215.869 322.413,206.696 L266.093,174.435 L254.947,193.894 C242.612,215.427 214.958,222.938 '
        '193.425,210.604 C171.892,198.269 164.381,170.615 176.715,149.082 L187.862,129.623 L129.287,96.0704 L118.141,115.529 '
        'C105.806,137.063 78.1523,144.574 56.6189,132.239 C35.0856,119.904 27.5747,92.2506 39.9094,70.7173 L51.0558,51.2583 '
        'L-7.51893,17.7057 L-18.6654,37.1647 C-31.0001,58.6981 -58.6537,66.209 -80.1871,53.8743 C-101.72,41.5397 '
        '-109.231,13.886 -96.8967,-7.64735 L-85.7502,-27.1064 L-144.325,-60.6589 L-155.471,-41.1999 C-167.806,-19.6665 '
        '-195.46,-12.1556 -216.993,-24.4903 C-238.526,-36.825 -246.037,-64.4787 -233.703,-86.012 L-222.556,-105.471 '
        'L-280.814,-138.842 C-296.827,-148.014 -305.085,-165.658 -303.195,-182.956 L-670.069,-393.107 Z M-1761.01,-796.43 '
        'L-1762.14,-1128.96 C-1762.46,-1223.68 -1685.39,-1301.29 -1590.66,-1301.61 C-1495.94,-1301.93 -1418.34,-1224.85 '
        '-1418.02,-1130.13 L-1416.88,-797.603 L-1416.26,-614.809 C-1416.26,-614.809 -1416.26,-614.808 -1416.26,-614.808 '
        'L-1411.41,807.702 L-1410.28,1140.26 C-1409.96,1234.99 -1487.03,1312.59 -1581.76,1312.91 C-1676.48,1313.24 '
        '-1754.08,1236.16 -1754.41,1141.44 L-1755.54,808.875 L-1755.54,808.875 L-1761.01,-796.43 Z"/>'
        '</svg>'
    ),
    "injuries": (
        '<svg viewBox="-1946 -1946 3892 3892" fill="currentColor" aria-hidden="true">'
        '<path d="M757.765,1945.72 C1412.92,1945.72 1945.72,1412.92 1945.72,757.765 L1945.72,-757.765 C1945.72,-1412.92 1412.92,-1945.72 '
        '757.765,-1945.72 L-757.765,-1945.72 C-1412.92,-1945.72 -1945.72,-1412.92 -1945.72,-757.765 L-1945.72,757.765 '
        'C-1945.72,1412.92 -1412.92,1945.72 -757.765,1945.72 L757.765,1945.72 Z M677.332,1739.19 L-677.332,1739.19 '
        'C-1262.94,1739.19 -1739.19,1262.94 -1739.19,677.331 L-1739.19,-677.332 C-1739.19,-1262.94 -1262.94,-1739.19 '
        '-677.332,-1739.19 L677.332,-1739.19 C1262.94,-1739.19 1739.19,-1262.94 1739.19,-677.332 L1739.19,677.331 '
        'C1739.19,1262.94 1262.94,1739.19 677.332,1739.19 Z"/>'
        '<path d="M-553.251,1375.79 L542.865,1375.79 L542.865,-1373.79 L-553.251,-1373.79 L-553.251,1375.79 Z M-1373.79,542.865 '
        'L1375.79,542.865 L1375.79,-553.251 L-1373.79,-553.251 L-1373.79,542.865 Z"/>'
        '</svg>'
    ),
    "stats": (
        '<svg viewBox="-1831 -1540 3663 3080" fill="currentColor" aria-hidden="true">'
        '<path d="M-545.127,1539.44 L-521.452,1539.44 C-495.364,1539.44 -473.89,1519.73 -470.103,1494.9 L482.547,1494.9 C486.118,1519.93 '
        '507.546,1539.44 533.957,1539.44 L863.534,1539.44 C889.623,1539.44 911.097,1519.73 914.883,1494.9 L915.026,1494.9 '
        'L1105.83,-284.748 L1111.5,-281.29 C1111.5,-281.29 1757.79,-526.467 1767.01,-535.68 C1830.52,-866.761 1908.69,-996.998 '
        '1657.16,-1248.52 C1556.46,-1349.22 1430.81,-1409.61 1300.18,-1429.68 C1300.53,-1429.75 1300.87,-1429.82 '
        '1301.22,-1429.88 C959.123,-1496.66 496.988,-1539.44 -1.15767,-1539.44 C-505.305,-1539.44 -958.437,-1499.25 '
        '-1303.54,-1429.88 C-1303.08,-1429.8 -1302.62,-1429.71 -1302.17,-1429.62 C-1432.66,-1409.49 -1558.16,-1349.12 '
        '-1658.76,-1248.52 C-1910.29,-996.998 -1833.29,-848.049 -1753.97,-535.68 C-1744.75,-526.467 -1098.46,-281.29 '
        '-1098.46,-281.29 L-1093.46,-284.34 L-902.7,1494.9 L-902.439,1494.9 C-898.869,1519.93 -877.44,1539.44 -851.029,1539.44 '
        'L-545.127,1539.44 L689.541,1539.44 L689.541,1323.49 L-568.801,1323.49 L-568.801,1539.44 L-545.127,1539.44 Z '
        'M-1755.23,-290.62 L-1118.84,-44.6789 L-1118.84,-228.643 L-1755.23,-474.584 L-1755.23,-290.62 Z M1767.01,-290.62 '
        'L1767.01,-474.584 L1130.62,-228.643 L1130.62,-44.6789 L1767.01,-290.62 Z M552.756,-1285.99 L24.2568,-917.793 '
        'L-502.511,-1287.34 C-508.542,-1290.98 -511.696,-1294.74 -511.696,-1298.58 C-511.696,-1332.16 -273.061,-1403.76 '
        '24.2568,-1403.76 C321.575,-1403.76 564.311,-1332.16 564.311,-1298.58 C564.311,-1294.27 560.329,-1290.05 '
        '552.756,-1285.99 Z M278.047,761.932 L278.047,-111.959 L209.098,-43.0107 L9.91899,-242.19 L278.047,-510.318 '
        'L278.047,-510.463 L559.729,-510.463 L559.729,761.932 L749.014,761.932 L749.014,1043.61 L88.7618,1043.61 '
        'L88.7618,761.932 L278.047,761.932 Z M-468.559,761.932 L-468.559,-111.959 L-537.508,-43.0107 L-736.687,-242.19 '
        'L-468.559,-510.318 L-468.559,-510.463 L-186.877,-510.463 L-186.877,761.932 L2.40781,761.932 L2.40781,1043.61 '
        'L-657.844,1043.61 L-657.844,761.932 L-468.559,761.932 Z"/>'
        '</svg>'
    ),
    "schedule": (
        '<svg viewBox="-1460 -1743 2920 3202" fill="currentColor" aria-hidden="true">'
        '<path d="M-401.037,-1457.16 L-401.037,-1500.74 C-401.037,-1634.89 -509.012,-1742.87 -643.164,-1742.87 C-777.316,-1742.87 '
        '-885.292,-1634.89 -885.292,-1500.74 L-885.292,-1457.16 L-1109.42,-1457.16 C-1301.05,-1457.16 -1459.05,-1302.52 '
        '-1459.05,-1107.53 L-1459.05,1107.95 C-1459.05,1299.58 -1304.41,1457.58 -1109.42,1457.58 L1109.42,1457.58 '
        'C1301.05,1457.58 1455.69,1299.58 1459.05,1111.31 L1459.05,-1107.53 C1459.05,-1299.15 1304.41,-1457.16 1109.42,-1457.16 '
        'L890.583,-1457.16 L890.583,-1457.16 L890.583,-1500.74 C890.583,-1634.89 782.607,-1742.87 648.456,-1742.87 '
        'C514.304,-1742.87 406.328,-1634.89 406.328,-1500.74 L406.328,-1457.16 L-401.037,-1457.16 L-401.037,-1457.16 Z '
        'M-1352.6,-585.374 L1352.6,-582.257 L1352.6,1030.03 C1349.49,1204.56 1206.12,1351.04 1028.48,1351.04 L-1028.48,1351.04 '
        'C-1209.24,1351.04 -1352.6,1204.56 -1352.6,1026.92 L-1352.6,-585.374 L-1352.6,-585.374 Z"/>'
        '<path d="M-1170.92,360.337 L-578.739,360.337 C-569.655,336.835 -546.793,320.078 -520.165,320.078 L-426.694,320.078 '
        'L-426.694,288.857 C-426.694,254.308 -398.484,226.098 -363.935,226.098 C-329.386,226.098 -301.176,254.308 '
        '-301.176,288.857 L-301.176,320.078 L-301.176,320.078 L-207.196,320.078 L-207.196,288.857 C-207.196,254.308 '
        '-178.986,226.098 -144.437,226.098 C-109.888,226.098 -81.6777,254.308 -81.6777,288.857 L-81.6777,320.078 '
        'L12.3025,320.078 L12.3025,288.857 C12.3025,254.308 40.5124,226.098 75.0615,226.098 C109.611,226.098 137.821,254.308 '
        '137.821,288.857 L137.821,320.079 L231.801,320.079 L231.801,288.857 C231.801,254.308 260.011,226.098 294.56,226.098 '
        'C329.109,226.098 357.319,254.308 357.319,288.857 L357.319,320.079 L447.682,320.079 C474.31,320.079 497.172,336.835 '
        '506.256,360.337 L1170.87,360.337 C1151.93,134.423 583.896,-325.858 -1.3719,-326.246 C-588.513,-326.636 '
        '-1159.05,119.096 -1170.92,360.337 L-1170.92,360.337 Z M-1166.36,407.792 C-1110.52,653.963 -570.855,1063.55 '
        '9.93563,1063.94 C580.291,1064.31 1097.21,655.12 1164.07,419.694 C1165.21,415.675 1167.1,407.792 1167.1,407.792 '
        'L1151.1,407.792 L505.247,407.792 C495.559,429.997 473.373,445.597 447.682,445.597 L357.319,445.597 L357.319,476.818 '
        'C357.319,511.367 329.109,539.577 294.56,539.577 C260.011,539.577 231.801,511.367 231.801,476.818 L231.801,445.597 '
        'L231.801,445.597 L137.821,445.597 L137.821,476.818 C137.821,511.367 109.611,539.577 75.0615,539.577 C40.5124,539.577 '
        '12.3025,511.367 12.3025,476.818 L12.3025,445.597 L12.3025,445.597 L-81.6777,445.597 L-81.6777,476.818 '
        'C-81.6777,511.367 -109.888,539.577 -144.437,539.577 C-178.986,539.577 -207.196,511.367 -207.196,476.818 '
        'L-207.196,445.597 L-207.196,445.597 L-301.176,445.597 L-301.176,476.818 C-301.176,511.367 -329.386,539.577 '
        '-363.935,539.577 C-398.484,539.577 -426.694,511.367 -426.694,476.818 L-426.694,445.597 L-520.165,445.597 '
        'C-545.857,445.597 -568.043,429.997 -577.73,407.792 L-1166.36,407.792 L-1166.36,407.792 Z"/>'
        '</svg>'
    ),
}


def _title(cid, name):
    """A card's title: its icon (TEAM_ICONS) in front of its name, like Page 1's render_page1.title_icon."""
    icon = TEAM_ICONS.get(cid)
    return f'<span class="ttl">{f"<span class=t-ic>{icon}</span>" if icon else ""}{esc(name)}</span>'


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
        ("injuries", "Injuries", injuries_body(team_page, side.get("game_absences"))),
        ("stats", "Team Stats", offense_defense_body(team_page.get("stats"))),
        ("schedule", "Schedule", schedule_body(team_page, prefix)),
    ]
    slots = "".join(
        f'<section class="slot"><a class="card p2k p2k-{cid}" tabindex="-1" aria-label="{esc(name)}">'
        f'<span class="peek peek-top">{DOWN}{_title(cid, name)}</span><div class="body">{body}</div>'
        f'<span class="peek peek-bot">{UP}{_title(cid, name)}</span></a></section>'
        for cid, name, body in cards
    )
    dots = "".join(f'<button class="dot" type="button" aria-label="{esc(name)}">{TEAM_ICONS.get(cid, "")}</button>' for cid, name, _b in cards)
    label = f'{esc(side.get("team") or "Team")} team info'
    return (f'<div class="p2 p2-team" data-page="{esc(which)}-team" aria-label="{label}" role="region">'
            f'<div class="p2-view p2-l deck">{slots}</div><nav class="dots p2-dots ic-dots" aria-label="Cards">{dots}</nav></div>')


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
/* the helmet matches Game Info's bar in size and place (Jason, 2026-10-07): P1_JS's syncTeamHeads
   measures that bar and sets these; the fallbacks are an upcoming game's (2.4 x 17px, 16px in) */
.tp-head{position:absolute;inset:0;align-items:center;gap:10px;padding:0 16px 0 var(--tp-inset,16px)}
.tp-home{padding:0 var(--tp-inset,16px) 0 16px}   /* the opponent's side keeps the bar's usual 16px */
.tp-head img{width:var(--tp-size,40.8px);height:var(--tp-size,40.8px);flex:none;display:block;--hs:var(--tp-size,40.8px)}
.tp-name{font-family:Saira,Inter,system-ui,sans-serif;font-weight:800;font-style:italic;font-variation-settings:'wdth' 95;
  font-size:20px;letter-spacing:.01em;text-transform:uppercase;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
.tp-rec{font-size:16px;font-weight:700;margin-left:10px;font-variant-numeric:tabular-nums;flex:none}
.tp-opp{margin-left:auto;padding-left:10px;color:var(--text-3);font-size:16px;white-space:nowrap;flex:none}
.tp-opp .abbr{font-size:20px}
@media (max-width:344px){.tp-name,.tp-opp .abbr{font-size:17px}}   /* the same size as every top bar's team names (render_page1) */
/* phones: the helmet, name, record and opponent closer together, so a long city ("San Francisco")
   still fits beside a finished game's helmet, which sits further in */
@media (max-width:400px){.bar .tp-head{gap:6px}.bar .tp-rec{margin-left:2px}.bar .tp-opp{padding-left:6px}
  .bar .tp-home .tp-rec{margin-left:0;margin-right:2px}.bar .tp-home .tp-opp{padding-left:0;padding-right:6px}}
.tp-home{flex-direction:row-reverse}
.tp-home .tp-rec{margin-left:0;margin-right:10px}
.tp-home .tp-opp{margin-left:0;margin-right:auto;padding-left:0;padding-right:10px}
.p2-team .p2-l{padding-top:0}
/* Overview stacks from the top (2026-09-28): the shared .p2 rule spreads a card's sections
   evenly, which opened a gap above the division table; now it sits right under recent games */
.p2 .slot .p2k-overview .body{justify-content:flex-start}
/* (The card in the middle of the deck links nowhere -- its hover is switched off for every Page 2
   deck in render_page2gameinfo.P2_CSS.) */
/* The card opens with the coaching staff (left) and the bye week as a big number (right) --
   Jason, 2026-09-28; the helmet/abbreviation/record header that used to lead moved to the bar */
.ov-lead{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:4px 4px 14px}
.ov-byebig{display:flex;flex-direction:column;align-items:center;flex:none;margin-left:auto}
.ov-byebig b{font-family:Teko,Inter,system-ui,sans-serif;font-weight:700;font-size:46px;line-height:1;color:var(--text-2)}
.ov-byebig span{font-size:11px;font-weight:700;letter-spacing:.08em;color:var(--text-2)}
.ov-top{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:14px 4px;
  border-top:1px solid var(--tile-border-soft);border-bottom:1px solid var(--tile-border-soft);margin:0 0 12px}
.ov-next{display:flex;align-items:center;gap:10px;min-width:0}
.ov-next img{width:40px;height:40px;display:block;flex:none;--hs:40px}
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
.st-row img{width:22px;height:22px;--hs:22px}
.st-w,.st-l,.st-t{text-align:center;color:var(--text-2)}
.st-pct{text-align:right;color:var(--text-2);font-variant-numeric:tabular-nums}
.full-inj{gap:2px}
/* a finished game's Injuries card has three lists, each under its own heading (2026-09-30). It
   never scrolls (Jason, 2026-10-07): .inj-fit takes the height the card has and P1_JS's injFit
   trims to it -- .t1/.t2 tighten the spacing first, then whole steps of rows go (data-cut, see
   injuries_body), each list's .inj-more line counting what's hidden. */
.p2 .slot .p2k-injuries .body{min-height:0}
.inj-sections{width:100%}
.inj-fit{flex:0 1 auto;min-height:0;overflow:hidden}
.inj-fit .inj-cut,.inj-fit [hidden]{display:none}
.inj-sections .full-inj li{padding:5px 2px}
.inj-sections .inj-h{padding-top:14px}
.inj-sections .inj-h:first-child,.inj-sections .inj-ir:first-child .inj-h{padding-top:0}
.inj-more{padding:4px 2px 0;font-size:12px}
.inj-mgl.inj-irline{padding-top:12px;white-space:nowrap;font-size:12px}
.inj-mgl.inj-irline b{font-size:14px}
.inj-fit.t1 .full-inj li{padding:3px 2px}
.inj-fit.t1 .inj-h{padding-top:9px;padding-bottom:4px}
.inj-fit.t1 .ov-empty{padding:4px}
.inj-fit.t2 .full-inj{font-size:14px;gap:0}
.inj-fit.t2 .full-inj li{padding:2px}
.inj-fit.t2 .inj-h{padding-top:6px;padding-bottom:2px;font-size:12px}
.inj-fit.t2 .inj-more{padding-top:2px}
.full-inj li{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:7px 2px;
  border-bottom:1px solid var(--tile-border-soft)}
.full-inj .inj-name{font-weight:700}
/* man-games lost under the IR list (2026-10-03): label left, the count and its league rank right */
.inj-mgl{display:flex;justify-content:space-between;align-items:baseline;gap:10px;padding:8px 2px 0;
  font-size:13px;color:var(--text-2)}
.inj-mgl b{font-size:16px;color:var(--ink)}
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
   otherwise a short value ("0") wouldn't be centered on the same axis as a wide one ("263").
   The rank sits centered against its value's height, not on its baseline (Jason, 2026-10-07). */
.stat{display:flex;flex-direction:row;align-items:center;justify-content:center;gap:3px;width:100%}
/* Rank sits on the outside of its value, away from the label between them, on both sides
   (2026-09-24) -- the offense column is first in the DOM (value then rank, left to right), so
   reversing just that one puts its rank on the card's outer edge to match the defense column,
   which already reads that way without changing anything. */
.stat-row:not(.stat-row-singles) > .stat:first-child{flex-direction:row-reverse}
/* Turnover diff./ToP/sacks/INTs aren't offense- or defense-specific, so they get their own
   plainer row instead of the two aligned value columns above (2026-09-24). All four share one
   line, each value+rank over its title (2026-10-07): a row each ran the card past the bottom of
   a phone screen and cut off Sacks/INTs. */
.stat-row.stat-row-singles{grid-template-columns:repeat(4,1fr);align-items:start;gap:4px;padding-top:10px;border-bottom:0}
.stat-tile{display:flex;flex-direction:column;align-items:center;gap:3px;min-width:0}
.stat-tile .stat-lbl{font-size:11px;color:var(--text-2);white-space:nowrap}
.stat-v{font-family:Teko,Inter,system-ui,sans-serif;font-weight:700;font-size:var(--vfs);line-height:1;font-variant-numeric:tabular-nums}
.stat-v.na{color:var(--text-3);font-family:Inter,sans-serif;font-size:20px}
/* Teko's digits sit high in their line box, so a rank centered on the box reads low; lift it by
   the gap between the box's middle and the digits' middle (about a tenth of the value's size) */
.stat{--vfs:28px}
.stat-rank{font-size:11px;font-weight:700;transform:translateY(calc(var(--vfs) * -.095))}
.stat-lbl{text-align:center;font-size:12px;color:var(--ink);display:flex;flex-direction:column;
  align-items:center;justify-content:center;line-height:1.25}
.stat-sub{font-size:10px;font-weight:400;color:var(--text-2)}
/* Compact by design -- every week has to be visible on the card with no scrolling
   (Jason, 2026-09-20), so this trades some size for fitting all ~18 rows at once. */
.sc-row{display:grid;grid-template-columns:16px 58px 14px 20px 1fr 14px 50px 42px;align-items:center;gap:6px;
  padding:4px 3px;border-bottom:1px solid var(--tile-border-soft);font-size:11.5px;line-height:1.15}
.sc-wk{color:var(--text-2);text-align:right;font-size:11px}
.sc-date{color:var(--text-2);white-space:nowrap;font-size:10.5px}
.sc-date.na{color:var(--text-3)}
.sc-vs{color:var(--text-3);text-align:center}
.sc-row img{width:20px;height:20px;--hs:20px}
.sc-opp{font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
/* result | score as two fixed columns, each centered, so they line up row to row; a kickoff
   time takes both */
.sc-res{font-weight:700;text-align:center}
.sc-win{color:var(--win)}.sc-loss{color:var(--loss)}.sc-tie{color:var(--tie)}
.sc-score{color:var(--text-2);font-variant-numeric:tabular-nums;text-align:center;white-space:nowrap}
.sc-time{grid-column:span 2;font-weight:700;white-space:nowrap;text-align:center}
.sc-rec{color:var(--text-2);text-align:right;font-variant-numeric:tabular-nums;font-size:11px}
.sc-row.sc-bye{grid-template-columns:16px 1fr;color:var(--text-2)}
.sc-bye-lbl{letter-spacing:.06em;font-size:10px;font-weight:700}
/* The whole season always fits (2026-10-03): fixed-height rows ran past the bottom of the card on
   shorter screens and cut off week 18 and more. The list takes whatever height the card has
   left and each row gets an equal share of it, up to its usual 28px -- a short screen shrinks
   every row (helmet and text with it) rather than dropping the last weeks. On a tall screen the
   rows keep their usual size, centered in the spare room (auto margins, so an overflowing list
   still starts at week 1). Rows stop shrinking at 17px, where the text is still readable; a
   screen too short even for that (a phone on its side) scrolls the list inside the card --
   P1_JS's detailAtTop lets it scroll back up before a pull-down closes the page. */
.p2 .slot .p2k-schedule .body{justify-content:flex-start}
.p2k-schedule .sc-list{flex:1 1 0;min-height:0;container-type:size;overflow-y:auto;-webkit-overflow-scrolling:touch;
  --row:clamp(17px,calc(100cqh / var(--n)),28px)}
.p2k-schedule .sc-row{flex:none}
.p2k-schedule .sc-row:first-child{margin-top:auto}
.p2k-schedule .sc-row:last-child{margin-bottom:auto}
/* each size below is the row's usual one (--fs-*, smaller on a narrow screen) until the row
   gets too short for it, then shrinks with the row */
.p2k-schedule{--fs-row:11.5px;--fs-wk:11px;--fs-date:10.5px;--fs-bye:10px;--img:20px}
.p2k-schedule .sc-row{height:var(--row);min-height:0;padding-top:0;padding-bottom:0;
  font-size:min(var(--fs-row),calc(var(--row) * .5))}
.p2k-schedule .sc-row img{width:min(var(--img),calc(var(--row) - 4px));height:min(var(--img),calc(var(--row) - 4px));--hs:min(var(--img),calc(var(--row) - 4px))}
.p2k-schedule .sc-wk,.p2k-schedule .sc-rec{font-size:min(var(--fs-wk),calc(var(--row) * .48))}
.p2k-schedule .sc-date{font-size:min(var(--fs-date),calc(var(--row) * .46))}
.p2k-schedule .sc-bye-lbl{font-size:min(var(--fs-bye),calc(var(--row) * .44));white-space:nowrap}
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
  .stat{--vfs:23px}
  .stat-head{grid-template-columns:62px 1fr 62px}
  .stat-row{grid-template-columns:62px 1fr 62px}
  .ov-facts{gap:10px}
  .st-row,.st-headrow{grid-template-columns:20px 1fr 20px 20px 20px 46px}
  .sc-row{grid-template-columns:14px 53px 12px 18px 1fr 12px 50px 30px;gap:4px;font-size:11px;padding:3px 2px}
  .p2k-schedule{--fs-row:11px;--fs-date:10px;--img:18px}
  .sc-row.sc-bye{grid-template-columns:14px 1fr}
}
"""
