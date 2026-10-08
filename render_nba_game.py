"""
NBA game pages (2026-10-08): site/nba/game/<game_id>.html, one per game -- the NFL's Page 1 and its
Page 2 deep dives (render_page1.py, render_page2gameinfo.py, render_page2team.py,
render_page2players.py), built for basketball.

Same page, same markup, same stylesheet and script: the NFL modules' CSS (P1_CSS, P2_CSS, P3_CSS,
P4_CSS) and P1_JS are used as they are, so the deck, the condensed view, the header flight, the deep
dives' open and close, swiping between games and every gesture behave exactly as on the NFL pages.
The NFL card icons stay as placeholders. Only the contents change:

  Page 1   Game Info -- tip-off time and date, national TV (or "Local TV"), the arena where the NFL
           card has its weather; a finished game's line score by quarter (OT1, OT2... when it went
           to overtime). Team cards -- record with the last-game arrow or streak, the top 3 injuries,
           and offense / defense ranks in points and field goal % (a finished game: its box score).
           Leaders -- each team's leader in points, rebounds, assists, steals and blocks per game,
           crowned when top 3 in the league (a finished game: that game's leaders).
  Tip-Off  time, countdown, TV, the last 5 meetings (the NFL page has the last one), crew chief.
  Arena    name, city, the home team (the NFL's Venue card, no surface or roof).
  Team     Overview -- home / road / last-10 records where the NFL has the bye week; rest days
           ("B2B" for a back-to-back) and miles traveled; the last 5 games (the NFL shows 4); the
           division with games behind. Injuries -- the full report (a finished game: who didn't play
           and why, then the pre-game report). Team Stats -- offense and defense per game with league
           ranks. Schedule -- the 10 games before this one, this one, and the 10 after.
  Player Stats  Scoring, Rebounding, Playmaking, Defense: per-game averages for the season to date
           (a finished game: its box score), sortable, top-3-in-the-league bars.

Data: data/nba.json -> game_details (build_nba_data.py) and player_games (nba_stats.py).
Defensive like the NFL pages: a missing value is "—", a failing deep dive is left out, a failing
game is skipped with a warning.
"""

import html
import os
import re
import shutil
import traceback
from datetime import date

import nba_helmets
import nba_stats
import nba_teams
import render_page1 as p1
import render_page2gameinfo as gi
import render_page2players as ps
import render_page2team as tp
import stadium_icons
import theme

DASH = "—"
MONTHS_UPPER = p1.MONTHS_UPPER
DAY_NAMES = p1.DAY_NAMES


def esc(v):
    return html.escape(str(v), quote=True)


def img(team, size, mirrored=False, prefix="../", large=False):
    return nba_helmets.helmet_img(team, size, mirrored, prefix, large)


def loc(team):
    return nba_teams.LOCATION_NAMES.get(team, team or "TBD")


def fmt_record(r):
    r = r or {}
    return f'{r.get("wins", 0)}-{r.get("losses", 0)}'


def f1(v):
    return DASH if v is None else f"{v:.1f}"


def f0(v):
    return DASH if v is None else f"{int(round(v)):,}"


def final_text(d):
    ot = d.get("ot") or 0
    return "FINAL" + ("/OT" if ot == 1 else f"/{ot}OT" if ot > 1 else "")


def mid_text(d):
    """FINAL / FINAL/OT / FINAL/2OT, or a live game's clock ("4:12 - 3rd")."""
    if d.get("live"):
        return (d.get("status_detail") or "LIVE").upper()
    return final_text(d)


def tv(d):
    return d.get("networks") or "Local TV"


# ---------------------------------------------------------------- Page 1: game info card

def game_body_compact(d):
    t, ampm = p1.fmt_time(d.get("gametime"))
    small = f"<small>{ampm}</small>" if ampm else ""
    day, _time = p1.fmt_when(d)
    city = ((d.get("info") or {}).get("arena") or {}).get("city") or ""
    return (
        p1.linescore_html(d, mini=True) +
        '<div class="gc-row gc-1"><div class="gc-when">'
        f'<div class="time">{esc(t)}{small}</div><div class="date">{esc(day)}</div></div>'
        f'<div class="network">{esc(tv(d))}</div></div>'
        # the arena takes the second line, beside the city, rather than the weather's spot up top --
        # it's longer than a temperature, and there it crowded the date
        f'<div class="gc-row gc-2"><div class="city">{esc(city)}</div>'
        f'<div class="network nba-arena-c">{esc(((d.get("info") or {}).get("arena") or {}).get("name") or "")}</div></div>'
    )


def game_body(d, hero=""):
    t, ampm = p1.fmt_time(d.get("gametime"))
    small = f"<small>{ampm}</small>" if ampm else ""
    final = bool(d.get("final") or d.get("live"))
    note = f'<div class="date nba-note">{esc(d["note"])}</div>' if d.get("note") else ""
    top = (f'<div class="game-top{" final-top" if final else ""}">'
           f'<div><div class="time">{esc(t)}{small}</div><div class="date">{esc(p1.fmt_date(d.get("gameday")))}</div>{note}</div>'
           f'<div class="network">{esc(tv(d))}</div></div>')
    lead = hero + p1.linescore_html(d) + top if final else top + hero
    city = ((d.get("info") or {}).get("arena") or {}).get("city") or ""
    arena = ((d.get("info") or {}).get("arena") or {}).get("name") or ""
    return (f'{lead}<div class="game-bottom"><div class="city">{esc(city)}</div>'
            f'<div class="weather"><span class="temp temp-word temp-word-long nba-arena">{esc(arena)}</span></div></div>')


# ---------------------------------------------------------------- Page 1: team cards

INJ_CLASS = {"Out": "out", "Doubtful": "doubt", "Questionable": "ques", "Day-To-Day": "ques", "Probable": "ques",
             "Did Not Play": "out"}


def injuries_html(side, full):
    """Page 1's injury list: the top 3, starters first. A finished game lists who didn't play instead
    (injury, illness, rest -- not the coach's decision), from its box score."""
    ga = side.get("game_absences") or {}
    if ga.get("available"):
        rows = ga.get("top") or []
        if not rows:
            return '<li class="inj-none">Everyone available played</li>'
    else:
        rows = side.get("injuries") or []
        if not rows:
            text = "No injuries reported" if side.get("injury_report_out") else "Injury report not available"
            return f'<li class="inj-none">{text}</li>'
    out = []
    for r in rows[:3]:
        status = r.get("status") or ""
        name = r.get("name") if full else r.get("short")
        label = status if full and not r.get("kind") else (r.get("status_short") or status)
        out.append(f'<li>{p1.inj_who_html(r.get("position"), name, r)}'
                   f'<span class="inj-s"><i class="inj-dot inj-{INJ_CLASS.get(status, "ques")}"></i>'
                   f'<span class="inj-status">{esc(label)}</span></span></li>')
    return "".join(out)


def game_stats_html(gs):
    """A finished game's box score for one team, three lines of two like the NFL card's."""
    def ma(m, a):
        return DASH if m is None or a is None else f"{f0(m)}-{f0(a)}"

    def pct(m, a):
        return DASH if not a else f"{100 * m / a:.0f}%"
    cell = lambda label, val: f"<div><dt>{label}</dt><dd><b>{val}</b></dd></div>"
    return (
        '<div class="gstats">'
        f'<dl class="gs-line">{cell("Field Goals", ma(gs.get("fgm"), gs.get("fga")))}{cell("FG %", pct(gs.get("fgm") or 0, gs.get("fga")))}</dl>'
        f'<dl class="gs-line">{cell("3-Pointers", ma(gs.get("tpm"), gs.get("tpa")))}{cell("Rebounds", f0(gs.get("reb")))}</dl>'
        f'<dl class="gs-line">{cell("Assists", f0(gs.get("ast")))}{cell("Turnovers", f0(gs.get("tov")))}</dl>'
        "</div>")


def _ranks_html(r, pts_label, fg_label):
    return ('<div class="ranks">'
            f'<div class="rank-col"><h3>Offense</h3>{p1.big_rank(r.get("off_pts"), pts_label)}{p1.big_rank(r.get("off_fg"), fg_label)}</div>'
            f'<div class="rank-col"><h3>Defense</h3>{p1.big_rank(r.get("def_pts"), pts_label)}{p1.big_rank(r.get("def_fg"), fg_label)}</div>'
            "</div>")


def c_team(side, label, final=False):
    team = side.get("team")
    gs = side.get("game_stats") if final else None
    bottom = game_stats_html(gs) if gs else _ranks_html(side.get("ranks") or {}, "PTS", "FG%")
    return (
        f'<a class="card c-team" tabindex="0" data-detail="{label}-team" aria-label="{esc(team)} team">'
        f'{p1.card_title(team, abbr=True, cid=f"{label}-team")}'
        f'<div class="l-top"><div class="l-id">{img(team, 40)}</div><div class="l-rec">{p1.record_block(side, final)}</div></div>'
        f'<ul class="injuries c-inj">{injuries_html(side, full=False)}</ul>{bottom}</a>'
    )


def l_team(side, final=False):
    team = side.get("team")
    gs = side.get("game_stats") if final else None
    bottom = game_stats_html(gs) if gs else _ranks_html(side.get("ranks") or {}, "POINTS", "FG %")
    return (
        f'<div class="l-top"><div class="l-id">{img(team, 84, large=True)}</div>'
        f'<div class="l-rec">{p1.record_block(side, final)}</div></div>'
        f'<ul class="l-inj">{injuries_html(side, full=True)}</ul>{bottom}'
    )


# ---------------------------------------------------------------- Page 1: leaders card

LEADER_STATS = (("pts", "Points"), ("reb", "Rebounds"), ("ast", "Assists"), ("stl", "Steals"), ("blk", "Blocks"))


def _leader_extra(x, stat, scope):
    """The small line under a leader's name: the rest of the story behind the number."""
    if scope == "game":
        if stat == "pts":
            return f'{f0(x["fgm"])}-{f0(x["fga"])} FG · {f0(x["tpm"])}-{f0(x["tpa"])} 3PT'
        if stat == "reb":
            return f'{f0(x["oreb"])} OFF · {f0(x["dreb"])} DEF'
        if stat == "ast":
            return f'{f0(x["tov"])} TO'
        return f'{f0(x["min"])} MIN'
    if stat == "pts":
        fg = f'{x["fg_pct"]:.0f}% FG · ' if x.get("fg_pct") is not None else ""
        return f'{fg}{f1(x["min"])} MIN'
    if stat == "reb":
        return f'{f1(x["oreb"])} OFF · {f1(x["dreb"])} DEF'
    if stat == "ast":
        return f'{f1(x["tov"])} TO'
    return f'{x["gp"]} GP'


def leaders(lines_by_side, scope, tops, teams, team_games):
    """[{label, away, home}] -- each team's best in each stat (per game for the season, totals for a
    game). Season leaders need 40% of the team's games, so a cameo doesn't top the list."""
    out = []
    for stat, label in LEADER_STATS:
        row = {"key": stat, "label": label}
        for side in ("away", "home"):
            pool = lines_by_side.get(side) or []
            if scope == "season":
                n = team_games.get(side) or 0
                pool = [x for x in pool if x["gp"] >= 0.4 * n] or pool
            best = max(pool, key=lambda x: (x[stat], x["min"]), default=None)
            if not best or best[stat] <= 0:
                row[side] = None
                continue
            first, last = ps.split_name(best["name"])
            row[side] = {"name": f"{first[0]}. {last}" if first else last, "position": best["pos"],
                         "value": f0(best[stat]) if scope == "game" else f1(best[stat]),
                         "league_rank": (tops.get((teams[side], best["id"])) or {}).get(stat) if scope == "season" else None,
                         "extra": _leader_extra(best, stat, scope)}
        out.append(row)
    return out


def leader_cell(p):
    if not p:
        return f'<div class="ldr"><div class="ldr-v na"><span>{DASH}</span></div><div class="ldr-n">&nbsp;</div></div>'
    return (f'<div class="ldr"><div class="ldr-v"><span>{esc(p["value"])}</span>{p1.crown(p.get("league_rank"))}</div>'
            f'<div class="ldr-n"><span class="nm">{ps.esc_name(p["name"])}</span><span class="pos">{esc(p.get("position") or "")}</span></div>'
            f'<div class="ldr-x">{esc(p["extra"])}</div></div>')


def leader_rows(rows):
    return "".join(f'<div class="cmp-row">{leader_cell(r.get("away"))}<div class="cmp-lbl">{esc(r["label"])}</div>'
                   f'{leader_cell(r.get("home"))}</div>' for r in rows)


def pill_row(a, h):
    return (f'<div class="cmp-row cmp-head">{nba_helmets.pill_html(a, nba_teams.full_name(a))}<div></div>'
            f'{nba_helmets.pill_html(h, nba_teams.full_name(h))}</div>')


# ---------------------------------------------------------------- Page 2: Tip-Off and Arena

def _countdown(d, info, cls):
    if d.get("final"):
        return f'<div class="{cls} cd-done"><span class="cd-status">{esc(final_text(d))}</span></div>'
    if d.get("live"):
        return f'<div class="{cls} cd-done"><span class="cd-status">LIVE</span></div>'
    if d.get("postponed"):
        return f'<div class="{cls} cd-done"><span class="cd-status">PPD</span></div>'
    return gi._countdown(d, {"kickoff_utc": info.get("tipoff_utc")}, cls)


def _lose(mine, theirs):
    return " lose" if mine is not None and theirs is not None and mine < theirs else ""


def _meeting_row(a, h, m):
    sa, sh = (m.get("score") or {}).get(a), (m.get("score") or {}).get(h)
    tag = {"POST": "Playoffs", "PLAYIN": "Play-In", "CUP": "NBA Cup"}.get(m.get("phase"), "")
    where = f'@ {m.get("home")}'
    return (f'<li class="mt-row"><span class="mt-date">{esc(gi.fmt_meeting_date(m.get("date")))}'
            f'<small>{esc(where)}{" · " + esc(tag) if tag else ""}</small></span>'
            f'<span class="abbr{_lose(sa, sh)}">{esc(a)}</span><span class="sc{_lose(sa, sh)}">{f0(sa)}</span>'
            f'<span class="sc{_lose(sh, sa)}">{f0(sh)}</span><span class="abbr{_lose(sh, sa)}">{esc(h)}</span></li>')


def _series(a, h, ms):
    """"OKC leads 3-2" over the meetings listed."""
    wa = sum(1 for m in ms if ((m.get("score") or {}).get(a) or 0) > ((m.get("score") or {}).get(h) or 0))
    wh = len(ms) - wa
    if wa == wh:
        return f"Split {wa}-{wh}"
    return f"{a if wa > wh else h} leads {max(wa, wh)}-{min(wa, wh)}"


def tipoff_body(d, info, time_html):
    date_line, weekday = gi._date_parts(d)
    a, h = d["away"]["team"], d["home"]["team"]
    ms = info.get("meetings") or []
    if ms:
        meetings = (f'<p class="ko-line">Last {len(ms)} meeting{"s" if len(ms) > 1 else ""} '
                    f'<span class="ko-date-sm">{esc(_series(a, h, ms))}</span></p>'
                    f'<ul class="mt-list">{"".join(_meeting_row(a, h, m) for m in ms)}</ul>')
    else:
        meetings = '<p class="ko-line na">First meeting</p>'
    ref = info.get("referee")
    ref_html = f'<span>{esc(ref)}</span>' if ref else '<span class="na">TBA</span>'
    return ('<div class="ko-top">'
            f'<div class="ko-when">{time_html}<div class="ko-date">{esc(date_line)}</div><div class="ko-date">{esc(weekday)}</div></div>'
            f'{_countdown(d, info, "cd")}</div>'
            f'<div class="ko-lines"><div class="ko-tv"><span class="ko-net">{esc(tv(d))}</span></div>{meetings}</div>'
            f'<p class="ko-line ko-ref">Crew Chief: {ref_html}</p>')


def tipoff_condensed(d, info, time_html):
    date_line, weekday = gi._date_parts(d)
    a, h = d["away"]["team"], d["home"]["team"]
    ms = info.get("meetings") or []
    if ms:
        m = ms[0]
        sa, sh = (m.get("score") or {}).get(a), (m.get("score") or {}).get(h)
        meet = (f'<span class="mm"><span class="abbr{_lose(sa, sh)}">{esc(a)}</span><span class="sc{_lose(sa, sh)}">{f0(sa)}</span>'
                f'<span class="sc{_lose(sh, sa)}">{f0(sh)}</span><span class="abbr{_lose(sh, sa)}">{esc(h)}</span></span>')
        sub = f'{esc(gi.fmt_meeting_date(m.get("date")))} · {esc(_series(a, h, ms))}'
    else:
        meet, sub = gi._na("First meeting"), ""
    ref = info.get("referee")
    return (f'<div class="cc-top"><div>{time_html}<div class="cc-date">{esc(date_line)} {esc(weekday)}</div></div>'
            f'{_countdown(d, info, "cd-c")}</div>'
            f'<div class="strip">{gi._fact("TV", esc(tv(d)))}{gi._fact("Last Meeting", meet, sub)}'
            f'{gi._fact("Crew Chief", esc(ref) if ref else gi._na("TBA"))}</div>')


def _home_fact(d, a):
    if a.get("neutral"):
        return "Neutral Site", "Yes"
    return "Home Team", nba_teams.full_name(d["home"]["team"])


def arena_body(d):
    a = (d.get("info") or {}).get("arena") or {}
    label, value = _home_fact(d, a)
    return (f'<div class="st-head"><h2 class="st-name">{esc(a.get("name") or "Arena TBD")}</h2>{stadium_icons.svg("dome", "st-icon")}</div>'
            + (f'<div class="st-city"><span class="nb">{esc(a["city"])}</span></div>' if a.get("city") else "") +
            f'<div class="st-facts one"><div class="fact"><b class="nba-fact">{esc(value)}</b><span>{esc(label)}</span></div></div>')


def arena_condensed(d):
    a = (d.get("info") or {}).get("arena") or {}
    label, value = _home_fact(d, a)
    city = f'<div class="cc-city"><span class="nb">{esc(a.get("city"))}</span></div>' if a.get("city") else ""
    return (f'<div class="cc-top"><div class="cc-stn"><div class="st-name">{esc(a.get("name") or "Arena TBD")}</div>{city}</div>'
            f'{stadium_icons.svg("dome", "st-icon")}</div><div class="strip">{gi._fact(label, esc(value))}</div>')


def render_gameinfo_block(d, time_html):
    info = d.get("info")
    if not isinstance(info, dict):
        return ""
    cards = [("kickoff", "Tip-Off", tipoff_body(d, info, time_html), tipoff_condensed(d, info, time_html)),
             ("stadium", "Arena", arena_body(d), arena_condensed(d))]
    slots = "".join(
        f'<section class="slot"><a class="card p2k p2k-{cid}" tabindex="-1" aria-label="{name}">'
        f'<span class="peek peek-top">{p1.DOWN}{gi._title(cid, name)}</span><div class="body">{body}</div>'
        f'<span class="peek peek-bot">{p1.UP}{gi._title(cid, name)}</span></a></section>'
        for cid, name, body, _c in cards)
    dots = "".join(f'<button class="dot" type="button" aria-label="{name}">{gi.P2_ICONS.get(cid, "")}</button>'
                   for cid, name, _b, _c in cards)
    condensed = "".join(f'<a class="card cc cc-{cid}" tabindex="0" aria-label="{name}"><span class="card-title">'
                        f'{gi._title(cid, name)}</span>{c}</a>' for cid, name, _b, c in cards)
    return ('<div class="p2" data-page="game-info" aria-label="Game info" role="region">'
            f'<div class="p2-view p2-l deck">{slots}</div><nav class="dots p2-dots ic-dots" aria-label="Cards">{dots}</nav>'
            f'<div class="p2-view p2-c n{len(cards)}">{condensed}</div></div>')


# ---------------------------------------------------------------- Page 2: team pages

def _fmt_day(gameday):
    try:
        d = date.fromisoformat(str(gameday)[:10])
    except (TypeError, ValueError):
        return "Date TBD", ""
    return f"{MONTHS_UPPER[d.month - 1]} {d.day}", DAY_NAMES[d.weekday()]


def _fmt_time(gametime):
    t, ampm = p1.fmt_time(gametime)
    return "TBD" if t == "TBD" else f"{t} {ampm}"


def team_bar_head(side, opp, which, prefix):
    team = side.get("team")
    opp_abbr = f'<span class="abbr">{esc(opp or "TBD")}</span>'
    opp_html = f"@ {opp_abbr}" if which == "away" else f"{opp_abbr} @"
    return (f'<div class="tp-head tp-{which}" aria-hidden="true">{img(team, 46, which == "home", prefix)}'
            f'<span class="tp-name">{esc(loc(team))}</span>'
            f'<span class="tp-rec">{esc(fmt_record(side.get("record")))}</span><span class="tp-opp">{opp_html}</span></div>')


def _next_block(tpage, which, prefix):
    nxt = tpage.get("next") or {}
    opp = nxt.get("opponent")
    date_line, weekday = _fmt_day(nxt.get("gameday"))
    rest = nxt.get("rest_days")
    rest_html = DASH if rest is None else "B2B" if rest <= 0 else f'{rest}<small> DAY{"S" if rest != 1 else ""}</small>'
    miles = nxt.get("miles_traveled")
    facts = [("REST", rest_html), ("TRAVELED", DASH if miles is None else f"{miles:,}<small> MI</small>")]
    fact_html = "".join(f'<div class="ov-fact"><b>{v}</b><span>{esc(k)}</span></div>' for k, v in facts)
    vs = "@" if which == "away" else "vs"
    return ('<div class="ov-top"><div class="ov-next">'
            f'{img(opp, 40, prefix=prefix)}<div class="ov-next-txt"><span class="ov-next-lbl">THIS GAME</span>'
            f'<span class="ov-next-vs">{vs} <span class="abbr">{esc(opp or "TBD")}</span></span>'
            f'<span class="ov-next-date">{esc(date_line)} {esc(weekday).upper()}</span></div></div>'
            f'<div class="ov-facts">{fact_html}</div></div>')


def _recent(recent):
    if not recent:
        return '<p class="ov-empty">No games played yet</p>'
    rows = []
    for e in recent:
        date_line, _wd = _fmt_day(e.get("gameday"))
        res = e.get("result") or ""
        sc = e.get("score") or {}
        rows.append(f'<li class="rg-row"><span class="rg-date">{esc(date_line)}</span><span class="rg-vs">{"vs" if e.get("home") else "@"}</span>'
                    f'<span class="rg-opp abbr">{esc(e.get("opponent") or "")}</span>'
                    f'<span class="rg-res rg-{"win" if res == "W" else "loss"}">{esc(res)}</span>'
                    f'<span class="rg-score">{f0(sc.get("team"))}-{f0(sc.get("opp"))}</span></li>')
    return f'<ul class="rg-list">{"".join(rows)}</ul>'


def _gb(v):
    return "–" if not v else (f"{v:.1f}".rstrip("0").rstrip(".") if v % 1 == 0 else f"{v:.1f}")


def _pct(v):
    return f"{v:.3f}".lstrip("0") if v < 1 else "1.000"


def _division(standings, team, prefix):
    if not standings or not standings.get("rows"):
        return ""
    rows = "".join(
        f'<li class="st-row{" is-you" if r["team"] == team else ""}">{img(r["team"], 22, prefix=prefix)}'
        f'<span class="st-team abbr">{esc(r["team"])}</span><span class="st-w">{r["wins"]}</span>'
        f'<span class="st-l">{r["losses"]}</span><span class="st-t">{_pct(r["pct"])}</span>'
        f'<span class="st-pct">{esc(_gb(r["gb"]))}</span></li>' for r in standings["rows"])
    head = ('<div class="st-headrow" aria-hidden="true"><span></span><span></span>'
            '<span>W</span><span>L</span><span>PCT</span><span>GB</span></div>')
    conf = standings["division"].split(" · ")[0]
    href = f'{prefix}standings.html#{conf.lower()}-{standings["div"].lower()}'
    return (f'<div class="ov-standings nba-div"><h3><span class="st-link" role="link" tabindex="0" data-href="{esc(href)}">'
            f'{esc(standings["div"])}{tp.STANDINGS_CHEV}</span></h3>{head}<ul class="st-list">{rows}</ul></div>')


def overview_body(side, tpage, which, prefix):
    sp = tpage.get("splits") or {}
    lead = "".join(f'<div class="ov-byebig"><b>{esc(sp[k])}</b><span>{label}</span></div>'
                   for k, label in (("home", "HOME"), ("road", "ROAD"), ("l10", "LAST 10")) if sp.get(k))
    return ((f'<div class="ov-lead nba-lead">{lead}</div>' if lead else "")
            + _next_block(tpage, which, prefix)
            + '<h3 class="ov-h">Last 5 Games</h3>' + _recent(tpage.get("recent"))
            + _division(tpage.get("standings"), side.get("team"), prefix))


def _inj_items(rows):
    items = []
    for r in rows:
        status = r.get("status") or ""
        detail = r.get("designation")
        label = f"{r.get('status_short') or status} · {detail}" if detail else status
        label = tp._fit_status(r.get("name") or "", [f"{status} · {detail}", label, r.get("status_short") or status]
                               if detail else [status, r.get("status_short") or status])
        items.append(f'<li><span class="inj-who"><span class="inj-pos">{esc(r.get("position") or "")}</span>'
                     f'<span class="inj-name">{ps.esc_name(r.get("name"))}</span></span>'
                     f'<span class="inj-s"><i class="inj-dot inj-{INJ_CLASS.get(status, "ques")}"></i>{esc(label)}</span></li>')
    return f'<ul class="l-inj full-inj">{"".join(items)}</ul>'


def injuries_body(tpage, absences=None):
    rows = tpage.get("injuries_full") or []
    report = _inj_items(rows) if rows else '<p class="ov-empty">No injuries reported</p>'
    ga = absences or {}
    if not ga.get("available"):
        return f'<div class="inj-sections inj-fit"><h3 class="ov-h inj-h">Injury Report</h3>{report}</div>'
    dnp = ga.get("dnp") or []
    return ('<div class="inj-sections inj-fit"><h3 class="ov-h inj-h">Did Not Play</h3>'
            + (_inj_items(dnp) if dnp else '<p class="ov-empty">Everyone available played</p>')
            + f'<h3 class="ov-h inj-h">Pre-game Injury Report</h3>{report}</div>')


STAT_ROWS = [("points", "Points", "per game", f1, False), ("fg_pct", "Field Goal %", None, f1, True),
             ("three_pct", "3-Point %", None, f1, True), ("threes", "3-Pointers Made", "per game", f1, False),
             ("rebounds", "Rebounds", "per game", f1, False), ("assists", "Assists", "per game", f1, False),
             ("turnovers", "Turnovers", "per game · forced", f1, False)]
SINGLE_STATS = [("diff", "Point Diff.", True), ("pace", "Pace", False), ("steals", "Steals", False), ("blocks", "Blocks", False)]


def _stat_cell(value, rank, fmt=f1, pct=False, signed=False):
    if value is None or rank is None:
        return f'<div class="stat"><span class="stat-v na">{DASH}</span></div>'
    disp = f"{value:+.1f}" if signed else fmt(value) + ("%" if pct else "")
    return (f'<div class="stat"><span class="stat-v">{esc(disp)}</span>'
            f'<span class="stat-rank" style="color:{p1.rank_color(rank)}">{rank}{esc(p1.ordinal(rank))}</span></div>')


def stats_body(stats):
    stats = stats or {}
    rows = []
    for key, label, sub, fmt, pct in STAT_ROWS:
        s = stats.get(key) or {}
        rows.append(tp._stat_row(label, sub, _stat_cell(s.get("off_value"), s.get("off_rank"), fmt, pct),
                                 _stat_cell(s.get("def_value"), s.get("def_rank"), fmt, pct)))
    singles = [(label, _stat_cell((stats.get(k) or {}).get("value"), (stats.get(k) or {}).get("rank"), signed=sg))
               for k, label, sg in SINGLE_STATS]
    rows.append(tp._stat_row_singles(singles))
    return ('<div class="stat-head"><span>Offense</span><span></span><span>Defense</span></div>'
            f'<div class="stat-list nba-stats">{"".join(rows)}</div>')


def schedule_body(tpage, prefix):
    rows = []
    for e in tpage.get("schedule") or []:
        try:
            d = date.fromisoformat(str(e.get("gameday"))[:10])
            date_html = f'<span class="sc-date">{DAY_NAMES[d.weekday()][:3].upper()} {d.month}/{d.day}</span>'
        except (TypeError, ValueError):
            date_html = '<span class="sc-date na">DATE TBD</span>'
        opp = e.get("opponent")
        if e.get("postponed"):
            mid = '<span class="sc-time">Postponed</span>'
        elif e.get("final"):
            res = e.get("result") or ""
            sc = e.get("score") or {}
            mid = (f'<span class="sc-res sc-{"win" if res == "W" else "loss"}">{esc(res)}</span>'
                   f'<span class="sc-score">{f0(sc.get("team"))}-{f0(sc.get("opp"))}</span>')
        else:
            mid = f'<span class="sc-time">{esc(_fmt_time(e.get("gametime")))}</span>'
        rec = fmt_record(e["record_after"]) if e.get("final") and e.get("record_after") and e.get("phase") == "REG" else ""
        rows.append(f'<li class="sc-row{" sc-this" if e.get("this") else ""}"><span class="sc-wk">{esc(e.get("number") or "")}</span>'
                    f'{date_html}<span class="sc-vs">{"vs" if e.get("home") else "@"}</span>{img(opp, 20, prefix=prefix)}'
                    f'<span class="sc-opp abbr">{esc(opp or "")}</span>{mid}<span class="sc-rec">{esc(rec)}</span></li>')
    return f'<ul class="sc-list" style="--n:{len(rows)}">{"".join(rows)}</ul>'


def render_team_block(side, which, prefix="../"):
    tpage = side.get("team_page")
    if not isinstance(tpage, dict):
        return ""
    cards = [("overview", "Overview", overview_body(side, tpage, which, prefix)),
             ("injuries", "Injuries", injuries_body(tpage, side.get("game_absences"))),
             ("stats", "Team Stats", stats_body(tpage.get("stats"))),
             ("schedule", "Schedule", schedule_body(tpage, prefix))]
    slots = "".join(
        f'<section class="slot"><a class="card p2k p2k-{cid}" tabindex="-1" aria-label="{esc(name)}">'
        f'<span class="peek peek-top">{p1.DOWN}{tp._title(cid, name)}</span><div class="body">{body}</div>'
        f'<span class="peek peek-bot">{p1.UP}{tp._title(cid, name)}</span></a></section>' for cid, name, body in cards)
    dots = "".join(f'<button class="dot" type="button" aria-label="{esc(name)}">{tp.TEAM_ICONS.get(cid, "")}</button>'
                   for cid, name, _b in cards)
    return (f'<div class="p2 p2-team" data-page="{which}-team" aria-label="{esc(side.get("team") or "Team")} team info" role="region">'
            f'<div class="p2-view p2-l deck">{slots}</div><nav class="dots p2-dots ic-dots" aria-label="Cards">{dots}</nav></div>')


# ---------------------------------------------------------------- Page 2: player stats

def _ma(m, a, scope):
    return f"{f0(m)}-{f0(a)}" if scope == "game" else f"{f1(m)}-{f1(a)}"


def _num(scope):
    return f0 if scope == "game" else f1


def _pc(v):
    return DASH if v is None else f"{v:.1f}"


# (label, value text, sort value) per column; scope decides totals (a game) or per-game averages
def scoring_cols(scope):
    """A game: made-attempted for each kind of shot. The season: the percentages -- averaged
    made-attempted pairs ("10.2-20.6") don't fit a phone's width beside the rest; the 3-Pointers
    leaders are on the Stat Leaders page."""
    n = _num(scope)
    if scope == "game":
        return [("MIN", lambda r: n(r["min"]), lambda r: r["min"]), ("PTS", lambda r: n(r["pts"]), lambda r: r["pts"]),
                ("FG", lambda r: _ma(r["fgm"], r["fga"], scope), lambda r: r["fgm"]),
                ("3PT", lambda r: _ma(r["tpm"], r["tpa"], scope), lambda r: r["tpm"]),
                ("FT", lambda r: _ma(r["ftm"], r["fta"], scope), lambda r: r["ftm"]),
                ("+/-", lambda r: f'{r["pm"]:+.0f}', lambda r: r["pm"])]
    return [("GP", lambda r: f0(r["gp"]), lambda r: r["gp"]), ("MIN", lambda r: n(r["min"]), lambda r: r["min"]),
            ("PTS", lambda r: n(r["pts"]), lambda r: r["pts"]), ("FG%", lambda r: _pc(r["fg_pct"]), lambda r: r["fg_pct"]),
            ("3P%", lambda r: _pc(r["tp_pct"]), lambda r: r["tp_pct"]), ("FT%", lambda r: _pc(r["ft_pct"]), lambda r: r["ft_pct"])]


def rebounding_cols(scope):
    n = _num(scope)
    return [("REB", lambda r: n(r["reb"]), lambda r: r["reb"]), ("OREB", lambda r: n(r["oreb"]), lambda r: r["oreb"]),
            ("DREB", lambda r: n(r["dreb"]), lambda r: r["dreb"]), ("MIN", lambda r: n(r["min"]), lambda r: r["min"])]


def playmaking_cols(scope):
    n = _num(scope)
    ratio = lambda r: r["ast_t"] / r["tov_t"] if r["tov_t"] else None
    return [("AST", lambda r: n(r["ast"]), lambda r: r["ast"]), ("TO", lambda r: n(r["tov"]), lambda r: r["tov"]),
            ("A/TO", lambda r: DASH if ratio(r) is None else f"{ratio(r):.1f}", ratio),
            ("MIN", lambda r: n(r["min"]), lambda r: r["min"])]


def defense_cols(scope):
    n = _num(scope)
    pm = (lambda r: f'{r["pm"]:+.0f}') if scope == "game" else (lambda r: f'{r["pm"]:+.1f}')
    return [("STL", lambda r: n(r["stl"]), lambda r: r["stl"]), ("BLK", lambda r: n(r["blk"]), lambda r: r["blk"]),
            ("PF", lambda r: n(r["pf"]), lambda r: r["pf"]), ("+/-", pm, lambda r: r["pm"])]


# (card id -- the NFL's, so its icon and styles come along -- title, columns, starting order,
#  {column: stat that earns a league top-3 bar}, how many the condensed view shows)
PS_CARDS = [
    ("passing", "Scoring", scoring_cols, lambda r: (-r["pts"], -r["min"]), {"PTS": "pts"}, 3),
    ("rushing", "Rebounding", rebounding_cols, lambda r: (-r["reb"], -r["min"]), {"REB": "reb"}, 2),
    ("receiving", "Playmaking", playmaking_cols, lambda r: (-r["ast"], -r["min"]), {"AST": "ast"}, 2),
    ("defense", "Defense", defense_cols, lambda r: (-(r["stl"] + r["blk"]), -r["min"]), {"STL": "stl", "BLK": "blk"}, 2),
]
PLACES = {1: "1st", 2: "2nd", 3: "3rd"}


def _name(r):
    first, last = ps.split_name(r["name"])
    top = f'<span class="ps-fn">{ps.esc_name(first)}</span> ' if first else '<span class="ps-fn"></span>'
    num = f'#{r["jersey"]}' if r.get("jersey") not in (None, "") else ""
    return (f'<span class="ps-nm">{top}<span class="ps-no">{esc(num)}</span>'
            f'<span class="ps-ln"><span class="ps-lt">{"&nbsp;".join(ps.esc_name(w) for w in last.split())}</span></span> '
            f'<span class="ps-pos">{esc(r["pos"])}</span></span>')


def _short_name(r):
    first, last = ps.split_name(r["name"])
    who = f"{esc(first[0])}.&nbsp;{ps.esc_name(last)}" if first else ps.esc_name(last)
    return f'<span class="ps-nm ps-nm1"><span class="ps-ln">{who}</span></span>'


def _meta(r):
    num = f'#{r["jersey"]}' if r.get("jersey") not in (None, "") else ""
    return f'{f"<span class=ps-no>{esc(num)}</span> " if num else ""}<span class="ps-pos">{esc(r["pos"])}</span>'


def _cell(text, value, place):
    inner = (f'<span class="ps-md ps-md{place}" title="{PLACES[place]} in the NBA">{esc(text)}</span>' if place else esc(text))
    return f'<td data-v="{value:g}">{inner}</td>' if isinstance(value, (int, float)) else f"<td>{inner}</td>"


def _table(rows, cols, empty, medals, sortable=True, short=False):
    if not rows:
        return f'<p class="ps-empty">{esc(empty)}</p>'
    head = "".join(f'<th scope="col" aria-sort="none"><button type="button" class="ps-sort">{esc(c[0])}</button></th>' if sortable
                   else f'<th scope="col"><span class="ps-lbl">{esc(c[0])}</span></th>' for c in cols)
    meta_head = '<th scope="col" class="ps-mh"><span class="vh">Number and position</span></th>' if short else ""
    body = "".join(
        f'<tr data-i="{i}"><th scope="row">{_short_name(r) if short else _name(r)}</th>'
        + (f'<td class="ps-meta">{_meta(r)}</td>' if short else "")
        + "".join(_cell(fmt(r), val(r), (r.get("medals") or {}).get(medals.get(label)) if medals.get(label) else None)
                  for label, fmt, val in cols) + "</tr>"
        for i, r in enumerate(rows))
    return (f'<div class="ps-tw"><table class="ps-t"><thead><tr><th scope="col"><span class="vh">Player</span></th>{meta_head}{head}</tr></thead>'
            f"<tbody>{body}</tbody></table></div>")


def render_players_block(d, stats, scope):
    """stats = {abbr: [player lines]} -- the hidden .p2 layer for Player Stats."""
    away, home = d["away"]["team"], d["home"]["team"]
    teams = (away, home)
    empty = "None this game" if scope == "game" else ("No games played yet" if not any(stats.values()) else "None this season")
    scope_lbl = lambda extra="": f'<span class="ps-scope{extra}">{"Game Stats" if scope == "game" else "Season Stats · Per Game"}</span>'
    tabs = "".join(f'<button type="button" class="ps-tab{" on" if i == 0 else ""}" data-team="{esc(t)}" '
                   f'aria-pressed="{"true" if i == 0 else "false"}">{nba_helmets.pill_html(t)}</button>' for i, t in enumerate(teams))
    slots, cards = [], []
    for cid, title, colf, key, medals, n_cond in PS_CARDS:
        cols = colf(scope)
        panes = "".join(f'<div class="ps-pane{" on" if i == 0 else ""}" data-team="{esc(t)}">'
                        f'{_table(sorted(stats.get(t) or [], key=key), cols, empty, medals)}</div>' for i, t in enumerate(teams))
        slots.append(f'<section class="slot"><a class="card p2k p2k-ps p2k-{cid}" tabindex="-1" aria-label="{esc(title)}">'
                     f'<span class="peek peek-top">{p1.DOWN}{ps._title(cid, title)}</span>'
                     f'<div class="body">{scope_lbl()}<div class="ps-sw">{tabs}</div><div class="ps-scroll">{panes}</div></div>'
                     f'<span class="peek peek-bot">{p1.UP}{ps._title(cid, title)}</span></a></section>')
        short_cols = [c for c in cols if c[0] not in ("GP", "MIN")][:6]
        cpanes = "".join(f'<div class="pc-p{" on" if i == 0 else ""}" data-team="{esc(t)}">'
                         f'{_table(sorted(stats.get(t) or [], key=key)[:n_cond], short_cols, empty, medals, sortable=False, short=True)}</div>'
                         for i, t in enumerate(teams))
        cards.append(f'<a class="card cc pc-{cid} pc-row" tabindex="0" aria-label="{esc(title)}">'
                     f'<span class="card-title">{ps._title(cid, title)}</span>{cpanes}</a>')
    dots = "".join(f'<button class="dot" type="button" aria-label="{esc(t)}">{ps.PS_ICONS.get(c, "")}</button>' for c, t, *_ in PS_CARDS)
    return ('<div class="p2 p2-ps" data-page="leaders" aria-label="Player stats" role="region">'
            f'<div class="p2-view p2-l deck">{"".join(slots)}</div><nav class="dots p2-dots ic-dots" aria-label="Cards">{dots}</nav>'
            f'<div class="p2-view p2-c pc"><div class="ps-sw pc-sw">{tabs}</div>{scope_lbl(" pc-scope")}{"".join(cards)}</div></div>')


# ---------------------------------------------------------------- the page

def header_scores(d):
    score = d.get("score") if (d.get("final") or d.get("live")) else None
    if not score:
        return "", ""
    a_s, h_s = score.get("away"), score.get("home")
    a_cls = h_cls = "hscore"
    if d.get("final") and a_s is not None and h_s is not None:
        if a_s > h_s:
            h_cls += " lose"
        elif h_s > a_s:
            a_cls += " lose"
    return f'<span class="{a_cls}">{f0(a_s)}</span>', f'<span class="{h_cls}">{f0(h_s)}</span>'


def win_side(d):
    s = d.get("score") if d.get("final") else None
    if not s or s.get("away") is None or s.get("home") is None:
        return None
    return "away" if s["away"] > s["home"] else "home" if s["home"] > s["away"] else None


def final_label_html(d):
    return f'<span class="tri tri-a">{p1.WIN_TRI}</span>{esc(mid_text(d))}<span class="tri tri-h">{p1.WIN_TRI}</span>'


def render_p1_block(d, stats, scope, tops, team_games, prefix="../", root="../../"):
    """prefix: the path back to site/nba/; root: back to site/ (the menu reaches the NFL pages too)."""
    away, home = d.get("away") or {}, d.get("home") or {}
    a, h = away.get("team") or "TBD", home.get("team") or "TBD"
    final = bool(d.get("final") or d.get("live"))
    a_score, h_score = header_scores(d)
    when_day, when_time = p1.fmt_when(d)
    lead = leaders({"away": stats.get(a) or [], "home": stats.get(h) or []}, scope, tops, {"away": a, "home": h}, team_games)
    rows = leader_rows(lead)
    leaders_name = "Game Leaders" if scope == "game" else "Season Leaders"
    row_html = lambda big: (
        f'<div class="side away">{img(a, 44, large=big, prefix=prefix)}<span class="abbr">{esc(a)}</span>{a_score}</div>'
        f'<div class="mid"><span class="at{" at-final" if final else ""}">{final_label_html(d) if final else "@"}</span>'
        f'<span class="when"><span>{esc(when_day)}</span><span>{esc(when_time)}</span></span>'
        f'<span class="final-lbl">{final_label_html(d)}</span></div>'
        f'<div class="side home">{h_score}<span class="abbr">{esc(h)}</span>{img(h, 44, True, large=big, prefix=prefix)}</div>')
    hero = f'<div class="hero" aria-hidden="true"><div class="teams">{row_html(True)}</div></div>'
    day_href = f"{prefix}index.html#day-{d.get('week_key')}"
    bar = ('<header class="bar"><div class="bar-in">'
           f'<div class="teams" aria-label="{esc(nba_teams.full_name(a))} at {esc(nba_teams.full_name(h))}">{row_html(False)}</div>'
           f'{team_bar_head(away, h, "away", prefix)}{team_bar_head(home, a, "home", prefix)}</div></header>'
           '<nav class="bbar" aria-label="Page controls"><div class="bbar-in">' + theme.menu_html(root, "nba-games")
           + f'<a class="week" href="{esc(day_href)}">{p1.CHEV}<span>{esc(d.get("week_label") or "")}</span></a>'
           f'<a class="week p2-back" href="#" aria-label="Back to {esc(a)} at {esc(h)}">{p1.CHEV}'
           f'<span><span class="abbr">{esc(a)}</span> @ <span class="abbr">{esc(h)}</span></span></a>'
           f'<button class="toggle" type="button"><span class="i-plus">{p1.PLUS}</span><span class="i-minus">{p1.MINUS}</span></button>'
           "</div></nav>")
    condensed = ('<div class="view view-c" aria-label="Condensed matchup">'
                 f'<a class="card c-game" tabindex="0" data-detail="game-info" aria-label="Game info">{p1.card_title("Game Info", cid="game-info")}{game_body_compact(d)}</a>'
                 f'<div class="c-teams">{c_team(away, "away", final and d.get("final"))}{c_team(home, "home", final and d.get("final"))}</div>'
                 f'<a class="card c-cmp" tabindex="0" data-detail="leaders" aria-label="{leaders_name}">{p1.card_title(leaders_name, cid="leaders")}'
                 f'<div class="c-cmp-in">{pill_row(a, h)}{rows}</div></a></div>')
    cards = [("game-info", "Game Info", "game", game_body(d, hero)),
             ("away-team", loc(a), "team", l_team(away, bool(d.get("final")))),
             ("home-team", loc(h), "team", l_team(home, bool(d.get("final")))),
             ("leaders", leaders_name, "compare", pill_row(a, h) + rows)]
    slots = "".join(
        f'<section class="slot"><a class="card {kind}" tabindex="-1" data-detail="{cid}" aria-label="{esc(name)}">'
        f'<span class="peek peek-top">{p1.DOWN}<span class="ttl">{p1.title_icon(cid)}<span class="{"abbr" if kind == "team" else ""}">{esc(name)}</span></span></span>'
        f'<div class="body">{body}</div>'
        f'<span class="peek peek-bot">{p1.UP}<span class="ttl">{p1.title_icon(cid)}<span class="{"abbr" if kind == "team" else ""}">{esc(name)}</span></span></span></a></section>'
        for cid, name, kind, body in cards)
    dots = "".join(f'<button class="dot" type="button" aria-label="{esc(name)}">{p1.NAV_ICONS.get(cid, "")}</button>' for cid, name, _k, _b in cards)
    large = f'<div class="view view-l deck" aria-label="Expanded matchup">{slots}</div><nav class="dots" aria-label="Cards">{dots}</nav>'
    t, ampm = p1.fmt_time(d.get("gametime"))
    time_html = f'<div class="time">{esc(t)}{f"<small>{ampm}</small>" if ampm else ""}</div>'
    blocks = {}
    for key, make in (("game-info", lambda: render_gameinfo_block(d, time_html)),
                      ("away-team", lambda: render_team_block(away, "away", prefix)),
                      ("home-team", lambda: render_team_block(home, "home", prefix)),
                      ("leaders", lambda: render_players_block(d, stats, scope))):
        try:
            blocks[key] = make()
        except Exception:   # a deep dive's trouble never costs the game its page
            blocks[key] = ""
    has = " ".join(k for k, b in blocks.items() if b)
    win = win_side(d)
    attrs = (" data-final" if final else "") + (f' data-win="{win}"' if win else "") + (f' data-has-detail="{has}"' if has else "")
    return (f'<div class="p1" data-view="large" data-head="card"{attrs} data-game="{esc(d.get("game_id"))}">'
            f'{bar}{condensed}{large}{"".join(blocks.values())}</div>')


# NBA-only touches, appended to the NFL stylesheet: the arena's name where the weather was, the
# last 5 meetings, three record splits where the bye week was, this game's row on the schedule
EXTRA_CSS = """
.p1 .weather .nba-arena{display:block;max-width:12em;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  font-size:15px;font-weight:600;line-height:1.2}
.p1 .nba-arena-c{min-width:0;overflow:hidden;text-overflow:ellipsis}
.p1 .game-bottom .weather,.p1 .gc-1 .weather{min-width:0;flex:0 1 auto}
.p1 .game-bottom .city{flex:1 1 auto;min-width:0;margin-right:10px}
.nba-note{font-size:12px;color:var(--aag-text-2);margin-top:2px}
.mt-list{list-style:none;display:flex;flex-direction:column;gap:2px;margin:6px auto 0;max-width:340px}
.mt-row{display:grid;grid-template-columns:1fr 3.2em 2.4em 2.4em 3.2em;align-items:center;gap:4px;font-size:15px}
.mt-row .abbr{font-size:16px;text-align:center}
.mt-row .sc{font-family:Teko,Inter,system-ui,sans-serif;font-weight:700;font-size:20px;text-align:center;font-variant-numeric:tabular-nums}
.mt-row .lose{opacity:.3}
.mt-date{display:flex;flex-direction:column;text-align:left;font-size:12px;line-height:1.15;white-space:nowrap}
.mt-date small{font-size:10px;color:var(--aag-text-3)}
.nba-lead{display:flex;justify-content:space-around;gap:8px}
.nba-lead .ov-byebig{margin-left:0}
.nba-lead .ov-byebig b{font-size:32px}
.sc-row.sc-this{font-weight:700;background:var(--aag-tile-hover);border-radius:6px}
/* three-digit scores and records like 41-26: wider columns than the NFL's */
.p1 .sc-row{grid-template-columns:18px 54px 14px 20px 1fr 12px 58px 40px;gap:5px}
.p1 .sc-rec{white-space:nowrap}
.p1 .rg-score{width:62px;white-space:nowrap}
.p1 .game-bottom .city{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.nba-div .st-row,.nba-div .st-headrow{grid-template-columns:22px 1fr 24px 24px 40px 32px}
.fact b.nba-fact{font-size:22px}
"""


_SVG_RE = re.compile(r"<svg\b([^>]*)>(.*?)</svg>", re.S)
_NUM_RE = re.compile(r"-?\d+\.\d+")
_D_RE = re.compile(r'\bd="([^"]*)"')


def compact_svgs(block, min_len=600):
    """Each game page carries the NFL's card icons several times over (titles, slivers, nav dots) --
    over half its weight. Each big one goes in once, as a group at the top of the block, and every
    use of it becomes a <use> pointing there; their drawings, thousands of units across, lose the
    decimals in their coordinates (a 20px icon can't show them). The block is mounted in a shadow root
    of its own in Page 0's overlay, so the ids never meet another game's."""
    symbols, ids = [], {}

    def swap(m):
        attrs, inner = m.group(1), m.group(2)
        if len(m.group(0)) < min_len or "viewBox" not in attrs:
            return m.group(0)
        inner = _D_RE.sub(lambda d: 'd="' + _NUM_RE.sub(lambda n: str(round(float(n.group(0)))), d.group(1)) + '"', inner)
        key = (attrs, inner)
        if key not in ids:
            ids[key] = f"s{len(ids)}"
            symbols.append(f'<g id="{ids[key]}">{inner}</g>')
        return f'<svg{attrs}><use href="#{ids[key]}"/></svg>'

    body = _SVG_RE.sub(swap, block)
    if not symbols:
        return block
    # plain groups, not <symbol>s: a <use> draws a group in the using <svg>'s own coordinates, so each
    # icon keeps its viewBox exactly as before
    sprite = f'<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>{"".join(symbols)}</defs></svg>'
    i = body.index(">") + 1   # just inside the .p1 block
    return body[:i] + sprite + body[i:]


def p1_css():
    """The stylesheet every game page uses (and Page 0 hands its overlay), the NFL's plus EXTRA_CSS."""
    import temp_colors
    return p1.P1_CSS + gi.P2_CSS + tp.P3_CSS + ps.P4_CSS + temp_colors.TC_CSS + EXTRA_CSS


def render_standalone(d, block):
    a, h = d["away"]["team"], d["home"]["team"]
    title = f"{a} @ {h} · {d.get('week_label') or ''} · NBA · At A Glance"
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'>"
            "<meta name='theme-color' content='#F3F3EE'>"
            f"<script>{theme.THEME_HEAD_JS}</script><title>{esc(title)}</title>"
            f"{nba_helmets.helmets.favicon_links('../../')}"
            "<link rel='preconnect' href='https://fonts.googleapis.com'><link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
            "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@200;300;400;700;900&display=swap' rel='stylesheet'>"
            "<link href='https://fonts.googleapis.com/css2?family=Saira:ital,wdth,wght@1,50..125,400..900&family=Teko:wght@400..700&display=swap' rel='stylesheet'>"
            # the stylesheet and script are shared files here (1,300 games' worth of copies would
            # outweigh the pages); Page 0 hands its overlay the same stylesheet from its own copy
            "<link id='p1-css' rel='stylesheet' href='game.css'>"
            f"<style>{theme.THEME_CSS}html,body{{margin:0;background:var(--aag-bg)}}</style></head><body>"
            f"{block}<script>{theme.THEME_JS}</script><script src='game.js'></script><script>AAG_P1.init(document);</script>"
            "</body></html>")


def write_all(data, site_dir, warnings):
    """site/nba/game/<id>.html for every game, plus the shared game.css / game.js. Returns the count."""
    out_dir = os.path.join(site_dir, "game")
    shutil.rmtree(out_dir, ignore_errors=True)   # no pages left over from a game that's gone (or another season)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "game.css"), "w", encoding="utf-8") as f:
        f.write(p1_css())
    with open(os.path.join(out_dir, "game.js"), "w", encoding="utf-8") as f:
        f.write(p1.P1_JS)
    season = nba_stats.Season(data.get("player_games"))
    pg = data.get("player_games") or {}
    count = 0
    for gid, d in (data.get("game_details") or {}).items():
        try:
            a, h = d["away"]["team"], d["home"]["team"]
            day = d.get("gameday") or "9999-12-31"
            before = day if d.get("game_type") in ("REG", "CUP", "PRE") else "9999-12-31"
            scope = "season"
            stats = {}
            if d.get("final") and d.get("game_type") != "PRE":
                game = {t: nba_stats.game_lines(pg.get(t), gid) for t in (a, h)}
                if any(game.values()):
                    scope, stats = "game", game
            if scope == "season":
                if d.get("game_type") == "PRE":
                    stats = {a: [], h: []}
                else:
                    tops = season.tops(before)
                    stats = {t: season.lines(t, before) for t in (a, h)}
                    for t, lines in stats.items():
                        for x in lines:
                            x["medals"] = tops.get((t, x["id"]), {})
            tops = season.tops(before) if d.get("game_type") != "PRE" else {}
            team_games = {"away": season.team_games(a, before), "home": season.team_games(h, before)}
            block = compact_svgs(render_p1_block(d, stats, scope, tops, team_games))
            safe = "".join(ch for ch in str(gid) if ch.isalnum() or ch in "_-")
            with open(os.path.join(out_dir, f"{safe}.html"), "w", encoding="utf-8") as f:
                f.write(render_standalone(d, block))
            count += 1
        except Exception:
            warnings.append(f"render_nba_game {gid}: {traceback.format_exc(limit=2)}")
    return count
