"""
NBA data build (2026-10-08), the NBA counterpart of build_data.py. Run with:

    python build_nba_data.py                       -> data/nba.json for the current season
    python build_nba_data.py --season 2026 --today 2026-03-15
                                                   -> a past season, as if it were that day
                                                      (for previewing the pages mid-season)

render_nba.py turns data/nba.json into site/nba/. Everything comes through nba_client.py:
sportsdataverse's ESPN-sourced season files, plus ESPN's scoreboard for preseason games and
for scores newer than the files (optional -- the build works without it).

The output follows build_data.py's shape wherever the NFL pages have the same thing, so the NBA
pages can use the same layout:
  days          Page 0, one entry per day with games (the NFL's season_weeks, by day instead of
                by week). Records on each tile are frozen the way the NFL's are: a finished game
                shows each team's record right after it, an upcoming one the current record.
  game_details  every game, "as of tip-off" like page1_data.py's: records, last result and
                streak, injuries, offense/defense ranks and team stats from games before this
                one, the last 5 meetings, recent games, the schedule around the game, the
                division table, rest and travel. Finished games add their box score.
  player_games  every player's line in every game, by team -- render_nba.py totals these into
                the Leaders card, Player Stats and the Stat Leaders page (like player_weeks).
  standings     every team's regular-season record, splits, last 10 and streak, plus ESPN's
                clinch marks once its standings file for the season is out.

Season types (ESPN's): 1 preseason, 2 regular season, 3 playoffs, 5 play-in. The NBA Cup final
(type "CC") is played in the regular season but doesn't count in the standings, so it's kept out
of records and stats like a preseason game.

Defensive like build_data.py: each piece is wrapped so one failure becomes a warning in the
output, not a failed build.
"""

import argparse
import datetime
import json
import math
import os
from collections import defaultdict
from zoneinfo import ZoneInfo

import nba_client
import nba_teams

ROOT = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(ROOT, "data", "nba.json")
ET = ZoneInfo("America/New_York")
HISTORY_SEASONS = 3          # earlier seasons searched for the last 5 meetings
PRESEASON_DAYS = 25          # how far before opening night to ask ESPN for preseason games
WINDOW = 10                  # the team page's schedule: this many games before and after

PRE, REG, POST, PLAYIN = 1, 2, 3, 5
PHASE = {PRE: "PRE", REG: "REG", POST: "POST", PLAYIN: "PLAYIN"}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


# ---------------------------------------------------------------- small helpers

def _et(start):
    """"2026-10-20T23:00Z" -> datetime in US Eastern, or None."""
    try:
        return datetime.datetime.fromisoformat(str(start).replace("Z", "+00:00")).astimezone(ET)
    except (TypeError, ValueError):
        return None


def day_label(d, long=False):
    """date -> "Tue, Oct 20" (the day picker) or "Tuesday, Oct 20" (the day's header)."""
    name = DAYS[d.weekday()] if long else DAYS[d.weekday()][:3]
    return f"{name}, {MONTHS[d.month - 1]} {d.day}"


def _pct(w, l):
    return w / (w + l) if w + l else 0.0


def _miles(a, b):
    """Great-circle miles between two (lat, lon) points."""
    (la1, lo1), (la2, lo2) = a, b
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = p2 - p1, math.radians(lo2 - lo1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))


def _gb(leader, row):
    """Games behind: half the difference in wins plus half the difference in losses."""
    return ((leader["w"] - row["w"]) + (row["l"] - leader["l"])) / 2


# ---------------------------------------------------------------- games

def phase_of(g):
    """REG / PRE / POST / PLAYIN, or CUP for the NBA Cup final (regular season, but not counted)."""
    if g.get("type") == "CC":
        return "CUP"
    if g.get("type") == "ALLSTAR":
        return None
    return PHASE.get(g.get("season_type"))


def counts(g):
    """Whether a game goes into regular-season records, standings and team stats."""
    return g["phase"] == "REG"


def _unplay(g):
    """A finished game as it looked before tip-off (--as-of previews)."""
    g = dict(g, state="pre", status="STATUS_SCHEDULED", status_detail=None, period=0, clock=None)
    for side in ("home", "away"):
        g[side] = dict(g[side], score=None, winner=None, linescores=[])
    return g


def load_games(season, today, warnings, as_of=None):
    """Every game of the season: the schedule file, plus ESPN's preseason and today's scores.
    as_of: pretend nothing from that day on has been played (a preview of a past season mid-way)."""
    games, err = nba_client.get_games(season)
    if err:
        warnings.append(f"get_games({season}): {err}")
    live = []
    reg_starts = sorted(g["date_et"] for g in games if g.get("season_type") == REG and g.get("date_et"))
    if reg_starts:
        opener = datetime.date.fromisoformat(reg_starts[0])
        # one request a day: ESPN turns down a date range here (400, seen 2026-10-08), single days are fine
        first_pre = opener - datetime.timedelta(days=PRESEASON_DAYS)
        pre, err = nba_client.get_scoreboard([first_pre + datetime.timedelta(days=i) for i in range(PRESEASON_DAYS)])
        if err:
            warnings.append(f"preseason scoreboard: {err}")
        live += [g for g in pre if g.get("season_type") == PRE]
    first = reg_starts[0] if reg_starts else None
    last = max((g["date_et"] for g in games if g.get("date_et")), default=None)
    if first and last and (datetime.date.fromisoformat(first) - datetime.timedelta(days=PRESEASON_DAYS)
                           <= today <= datetime.date.fromisoformat(last) + datetime.timedelta(days=1)):
        now, err = nba_client.get_scoreboard([today - datetime.timedelta(days=1), today])
        if err:
            warnings.append(f"scoreboard: {err}")
        live += now
    merged = nba_client.merge_live(games, live)
    if as_of:
        merged = [_unplay(g) if (g.get("date_et") or "") >= as_of.isoformat() else g for g in merged]
    out = []
    for g in merged:
        if g.get("season") not in (None, season):
            continue
        g = dict(g, phase=phase_of(g))
        if not g["phase"] or not (g.get("home") and g.get("away")):
            continue
        status = g.get("status") or ""
        g["postponed"] = status in ("STATUS_POSTPONED", "STATUS_CANCELED", "STATUS_SUSPENDED")
        g["final"] = g.get("state") == "post" and not g["postponed"]
        g["live"] = g.get("state") == "in"
        lines = max(len(g["home"].get("linescores") or []), len(g["away"].get("linescores") or []))
        g["ot"] = max(0, max(lines, int(g.get("period") or 0)) - 4) if g["final"] else 0
        ko = _et(g.get("start"))
        g["gameday"] = g.get("date_et") or (ko.date().isoformat() if ko else None)
        g["gametime"] = ko.strftime("%H:%M") if ko and g.get("time_valid") is not False else None
        out.append(g)
    out.sort(key=lambda g: (g.get("start") or "", g["game_id"]))
    return out


def _result(g, side):
    me, opp = g[side].get("score"), g["away" if side == "home" else "home"].get("score")
    if me is None or opp is None:
        return None
    return "W" if me > opp else "L" if me < opp else "T"


def walk_records(games):
    """Each game's teams as of tip-off and right after: record (wins/losses in that game's own
    phase -- preseason counts separately; playoff games carry the regular-season record), last
    result and current streak (any phase but preseason). Returns {game_id: {side: {...}}}."""
    rec = defaultdict(lambda: {"wins": 0, "losses": 0})
    streak = defaultdict(lambda: (None, 0))   # (team, kind) -> (last result, run length)
    out = {}
    for g in games:
        kind = "PRE" if g["phase"] == "PRE" else "REAL"
        bucket = "PRE" if g["phase"] == "PRE" else "REG"
        entry = {}
        for side in ("away", "home"):
            team = g[side]["abbr"]
            before = dict(rec[(team, bucket)])
            last, run = streak[(team, kind)]
            entry[side] = {"before": before, "last_before": last, "streak_before": run}
            res = _result(g, side) if g["final"] else None
            if res:
                if g["phase"] in ("PRE", "REG"):
                    rec[(team, bucket)]["wins" if res == "W" else "losses"] += 1
                run = run + 1 if res == last else 1
                streak[(team, kind)] = (res, run)
                last = res
            entry[side].update(after=dict(rec[(team, bucket)]), last_after=last if res else None,
                               streak_after=run if res else 0, result=res)
        out[g["game_id"]] = entry
    return out


def day_tiles(games, records):
    """Page 0's days: [{key, label, long_label, games: [tile]}], plus the day it should open on."""
    by_day = defaultdict(list)
    for g in games:
        if not g.get("gameday"):
            continue
        r = records.get(g["game_id"], {})
        tile = {
            "game_id": g["game_id"], "game_type": g["phase"], "note": g.get("note"),
            "gameday": g["gameday"], "gametime": g["gametime"], "final": g["final"], "live": g["live"],
            "postponed": g["postponed"], "status_detail": g.get("status_detail"), "ot": g["ot"],
            "networks": g.get("tv"),
        }
        for side in ("away", "home"):
            s = r.get(side) or {}
            tile[side] = {"team": g[side]["abbr"], "nba": g[side].get("nba", True),
                          "record": s.get("after") if g["final"] else s.get("before"),
                          "score": g[side].get("score") if (g["final"] or g["live"]) else None}
        by_day[g["gameday"]].append(tile)
    days = []
    for key in sorted(by_day):
        d = datetime.date.fromisoformat(key)
        days.append({"key": key, "label": day_label(d), "long_label": day_label(d, long=True),
                     "games": sorted(by_day[key], key=lambda t: (t["gametime"] or "99:99", t["game_id"]))})
    return days


def current_day(days, today):
    """Today if it has games, else the next day that does, else the last day of the season."""
    keys = [d["key"] for d in days]
    if not keys:
        return None
    t = today.isoformat()
    return next((k for k in keys if k >= t), keys[-1])


# ---------------------------------------------------------------- team stats, ranks, standings

# (key, from the team box row: value for this game) -- totals summed across games, then per game
_BOX = {
    "pts": "team_score", "opp_pts": "opponent_team_score", "fgm": "field_goals_made", "fga": "field_goals_attempted",
    "tpm": "three_point_field_goals_made", "tpa": "three_point_field_goals_attempted",
    "ftm": "free_throws_made", "fta": "free_throws_attempted", "oreb": "offensive_rebounds",
    "dreb": "defensive_rebounds", "reb": "total_rebounds", "ast": "assists", "stl": "steals", "blk": "blocks",
    "tov": "total_turnovers", "pf": "fouls",
}


def _n(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def team_box_index(team_box):
    """{game_id: {abbr: {stat: value, plus opp_<stat> for the other team}}} from the team box rows."""
    rows = defaultdict(dict)
    for r in team_box:
        if r.get("abbr"):
            rows[str(r["game_id"])][r["abbr"]] = {k: _n(r.get(col)) for k, col in _BOX.items()} | {
                "paint": r.get("points_in_paint"), "fast": r.get("fast_break_points"), "lead": r.get("largest_lead")}
    out = {}
    for gid, teams in rows.items():
        if len(teams) != 2:
            continue
        (a, ra), (b, rb) = teams.items()
        out[gid] = {a: dict(ra, **{f"opp_{k}": v for k, v in rb.items() if k in _BOX}),
                    b: dict(rb, **{f"opp_{k}": v for k, v in ra.items() if k in _BOX})}
    return out


def _poss(t):
    return t["fga"] - t["oreb"] + t["tov"] + 0.44 * t["fta"]


# (key, label, value from a team's totals, higher is better) -- per game unless it's a rate
TEAM_STATS = {
    "points": (lambda t, g: t["pts"] / g, lambda t, g: t["opp_pts"] / g),
    "fg_pct": (lambda t, g: 100 * t["fgm"] / t["fga"] if t["fga"] else None,
               lambda t, g: 100 * t["opp_fgm"] / t["opp_fga"] if t["opp_fga"] else None),
    "three_pct": (lambda t, g: 100 * t["tpm"] / t["tpa"] if t["tpa"] else None,
                  lambda t, g: 100 * t["opp_tpm"] / t["opp_tpa"] if t["opp_tpa"] else None),
    "threes": (lambda t, g: t["tpm"] / g, lambda t, g: t["opp_tpm"] / g),
    "rebounds": (lambda t, g: t["reb"] / g, lambda t, g: t["opp_reb"] / g),
    "assists": (lambda t, g: t["ast"] / g, lambda t, g: t["opp_ast"] / g),
    "turnovers": (lambda t, g: t["tov"] / g, lambda t, g: t["opp_tov"] / g),
}
# for the offense column (a team's own number) and the defense column (its opponents'):
# True = more is better. A defense is better the less it allows -- except turnovers, where forcing
# more is better, and the offense's own turnovers, where fewer is better.
OFF_HIGH = {"points": True, "fg_pct": True, "three_pct": True, "threes": True, "rebounds": True,
            "assists": True, "turnovers": False}
DEF_HIGH = {"points": False, "fg_pct": False, "three_pct": False, "threes": False, "rebounds": False,
            "assists": False, "turnovers": True}
SINGLES = {
    "diff": (lambda t, g: (t["pts"] - t["opp_pts"]) / g, True),
    "pace": (lambda t, g: (_poss(t) + _poss({k[4:]: v for k, v in t.items() if k.startswith("opp_")})) / 2 / g, True),
    "steals": (lambda t, g: t["stl"] / g, True),
    "blocks": (lambda t, g: t["blk"] / g, True),
}


def _rank(values, high):
    """{team: value} -> {team: rank}, ties sharing the better place; None values get no rank."""
    have = {t: v for t, v in values.items() if v is not None}
    return {t: 1 + sum(1 for o in have.values() if (o > v if high else o < v)) for t, v in have.items()}


def team_snapshot(totals):
    """{team: {stat: {off_value, off_rank, def_value, def_rank} | {value, rank}}, plus "games"}"""
    played = {t: x["g"] for t, x in totals.items() if x["g"]}
    out = {t: {"games": n} for t, n in played.items()}
    for key, (off, dfn) in TEAM_STATS.items():
        ov = {t: off(totals[t], n) for t, n in played.items()}
        dv = {t: dfn(totals[t], n) for t, n in played.items()}
        orank, drank = _rank(ov, OFF_HIGH[key]), _rank(dv, DEF_HIGH[key])
        for t in played:
            out[t][key] = {"off_value": ov[t], "off_rank": orank.get(t), "def_value": dv[t], "def_rank": drank.get(t)}
    for key, (fn, high) in SINGLES.items():
        vals = {t: fn(totals[t], n) for t, n in played.items()}
        ranks = _rank(vals, high)
        for t in played:
            out[t][key] = {"value": vals[t], "rank": ranks.get(t)}
    return out


def standings_rows(results):
    """results: [(team, opponent, "W"/"L", home bool)] in date order -> {team: row}."""
    rows = {}
    for t in nba_teams.TEAMS.values():
        rows[t["abbr"]] = {"team": t["abbr"], "conf": t["conference"], "div": t["division"], "w": 0, "l": 0,
                           "hw": 0, "hl": 0, "rw": 0, "rl": 0, "cw": 0, "cl": 0, "dw": 0, "dl": 0, "seq": []}
    for team, opp, res, home in results:
        r, o = rows.get(team), nba_teams.by_abbr(opp)
        if not r or not o:
            continue
        k = "w" if res == "W" else "l"
        r[k] += 1
        r[("h" if home else "r") + k] += 1
        if o["conference"] == r["conf"]:
            r["c" + k] += 1
            if o["division"] == r["div"]:
                r["d" + k] += 1
        r["seq"].append(res)
    for r in rows.values():
        seq = r.pop("seq")
        r["pct"], r["cpct"], r["dpct"] = _pct(r["w"], r["l"]), _pct(r["cw"], r["cl"]), _pct(r["dw"], r["dl"])
        last10 = seq[-10:]
        r["l10"] = f'{last10.count("W")}-{last10.count("L")}'
        run = 0
        for x in reversed(seq):
            if x != seq[-1]:
                break
            run += 1
        r["streak"] = f"{seq[-1]}{run}" if seq else ""
    return rows


def order(rows):
    """Win pct, then conference pct, then division pct, then wins -- not the NBA's real tiebreakers
    (head-to-head, division winner, ...), the same simplification as the NFL standings."""
    return sorted(rows, key=lambda r: (-r["pct"], -r["cpct"], -r["dpct"], -r["w"], r["team"]))


# ---------------------------------------------------------------- players and injuries

_PLAYER_COLS = {"min": "minutes", "pts": "points", "fgm": "field_goals_made", "fga": "field_goals_attempted",
                "tpm": "three_point_field_goals_made", "tpa": "three_point_field_goals_attempted",
                "ftm": "free_throws_made", "fta": "free_throws_attempted", "oreb": "offensive_rebounds",
                "dreb": "defensive_rebounds", "reb": "rebounds", "ast": "assists", "stl": "steals",
                "blk": "blocks", "tov": "turnovers", "pf": "fouls"}


def player_games(player_box, gameday_by_id, warnings):
    """{team: [one row per player per game]} -- who played, with every box-score number; and who
    didn't (dnp, with the reason when it isn't the coach's decision)."""
    out = defaultdict(list)
    for r in player_box:
        team = r.get("abbr")
        if not team or r.get("season_type") not in (REG, POST, PLAYIN):
            continue
        gid = str(r["game_id"])
        row = {"id": str(r.get("athlete_id")), "name": r.get("athlete_display_name") or "",
               "pos": r.get("athlete_position_abbreviation") or "", "jersey": r.get("athlete_jersey"),
               "gid": gid, "date": gameday_by_id.get(gid) or str(r.get("game_date") or "")[:10],
               "st": r.get("season_type"), "starter": bool(r.get("starter")), "dnp": bool(r.get("did_not_play"))}
        if row["dnp"]:
            reason = (r.get("reason") or "").strip()
            row["reason"] = None if reason.upper() in ("", "COACH'S DECISION", "DNP-COACH'S DECISION") else reason
        else:
            for k, col in _PLAYER_COLS.items():
                row[k] = _n(r.get(col))
            try:
                row["pm"] = int(str(r.get("plus_minus") or "0").replace("+", ""))
            except ValueError:
                row["pm"] = 0
        out[team].append(row)
    for rows in out.values():
        rows.sort(key=lambda x: (x["date"], x["gid"]))
    if not out:
        warnings.append("player box: no rows yet for this season")
    return out


def starters_before(pg, team, date):
    """Players who started at least half of the games they played for this team before date."""
    starts, games = defaultdict(int), defaultdict(int)
    for r in pg.get(team) or []:
        if r["date"] >= date or r["dnp"]:
            continue
        games[r["id"]] += 1
        starts[r["id"]] += r["starter"]
    return {p for p, n in games.items() if starts[p] * 2 >= n and n}, {r["name"]: r["id"] for r in pg.get(team) or []}


INJURY_ORDER = {"Out": 0, "Doubtful": 1, "Questionable": 2, "Day-To-Day": 3, "Probable": 4}
INJURY_SHORT = {"Out": "O", "Day-To-Day": "DTD", "Doubtful": "D", "Questionable": "Q", "Probable": "P"}


def _short(name):
    parts = (name or "").split()
    return f"{parts[0][0]}. {' '.join(parts[1:])}" if len(parts) > 1 else (name or "")


def injury_index(rows):
    """{(team, as_of_date): [rows]} and the sorted list of snapshot dates."""
    idx = defaultdict(list)
    for r in rows:
        if r.get("abbr"):
            idx[(r["abbr"], str(r.get("as_of_date"))[:10])].append(r)
    return idx, sorted({k[1] for k in idx})


def injuries_for(idx, dates, team, gameday, starters, ids):
    """That day's injury report for one team, starters first, then Out before Day-To-Day: the latest
    snapshot on or before the game -- at most 3 days old for a game that's been played, while every
    game still to come gets the newest one (it's the report as it stands)."""
    snap = next((d for d in reversed(dates) if d <= gameday), None)
    current = bool(dates) and snap == dates[-1]
    if not snap or (not current and (datetime.date.fromisoformat(gameday) - datetime.date.fromisoformat(snap)).days > 3):
        return [], False
    out = []
    for r in idx.get((team, snap)) or []:
        status = r.get("status") or ""
        name = r.get("athlete_display_name") or ""
        pid = str(r.get("athlete_id"))
        detail = " ".join(x for x in (r.get("detail_side") if r.get("detail_side") not in (None, "Not Specified") else None,
                                      r.get("detail_type")) if x) or None
        out.append({"name": name, "short": r.get("athlete_short_name") or _short(name),
                    "position": r.get("athlete_position") or "", "status": status,
                    "status_short": INJURY_SHORT.get(status, status[:3].upper()),
                    "starter": pid in starters or ids.get(name) in starters, "designation": detail,
                    "returns": r.get("detail_return_date"), "comment": r.get("short_comment")})
    out.sort(key=lambda x: (not x["starter"], INJURY_ORDER.get(x["status"], 9), x["name"]))
    return out, True


def absences_for(pg, team, gid, starters):
    """A finished game's players who sat out for anything but the coach's decision (injury, illness,
    rest, suspension), from its box score."""
    rows = [r for r in pg.get(team) or [] if r["gid"] == gid]
    if not rows:
        return {"available": False}
    out = [{"name": r["name"], "short": _short(r["name"]), "position": r["pos"], "status": "Did Not Play",
            "status_short": "DNP", "starter": r["id"] in starters,
            "designation": (r.get("reason") or "").title() or None, "kind": "dnp"}
           for r in rows if r["dnp"] and r.get("reason")]
    out.sort(key=lambda x: (not x["starter"], x["name"]))
    return {"available": True, "top": [r for r in out if r["starter"]][:3] or out[:3], "dnp": out}


# ---------------------------------------------------------------- per game

def _game_stats(box):
    if not box:
        return None
    return {k: box.get(k) for k in ("fgm", "fga", "tpm", "tpa", "ftm", "fta", "reb", "oreb", "ast", "tov", "stl", "blk",
                                    "pts", "paint", "fast", "lead")}


def _schedule_entry(g, team):
    side = "home" if g["home"]["abbr"] == team else "away"
    other = g["away" if side == "home" else "home"]
    entry = {"game_id": g["game_id"], "phase": g["phase"], "opponent": other["abbr"], "home": side == "home",
             "gameday": g["gameday"], "gametime": g["gametime"], "final": g["final"], "postponed": g["postponed"]}
    if g["final"]:
        entry["score"] = {"team": g[side].get("score"), "opp": other.get("score")}
        entry["result"] = _result(g, side)
    return entry


def build(season, today, warnings, as_of=None):
    games = load_games(season, today, warnings, as_of)
    by_id = {g["game_id"]: g for g in games}
    records = walk_records(games)
    days = day_tiles(games, records)
    gameday_by_id = {g["game_id"]: g["gameday"] for g in games}

    team_box, err = nba_client.get_team_box(season)
    if err:
        warnings.append(f"get_team_box: {err}")
    player_box, err = nba_client.get_player_box(season)
    if err:
        warnings.append(f"get_player_box: {err}")
    if as_of:
        played = {g["game_id"] for g in games if g["final"]}
        team_box = [r for r in team_box if str(r["game_id"]) in played]
        player_box = [r for r in player_box if str(r["game_id"]) in played]
    box = team_box_index(team_box)
    pg = player_games(player_box, gameday_by_id, warnings)
    officials, err = nba_client.get_officials(season)
    if err:
        warnings.append(f"get_officials: {err}")
    injury_rows, err = nba_client.get_injuries(season, every_day=True)
    if err:
        warnings.append(f"get_injuries: {err}")
    inj_idx, inj_dates = injury_index(injury_rows)

    history = []
    for s in range(season - HISTORY_SEASONS, season):
        rows, err = nba_client.get_games(s)
        if err:
            warnings.append(f"get_games({s}) for past meetings: {err}")
        history += [dict(g, phase=phase_of(g), final=g.get("state") == "post") for g in rows]
    history += games
    history = [g for g in history if g.get("phase") in ("REG", "POST", "PLAYIN", "CUP") and g.get("final")
               and g["home"].get("abbr") and g["away"].get("abbr")]
    history.sort(key=lambda g: g.get("start") or "")

    # team totals and standings, snapshotted before each game day (regular season only)
    reg = [g for g in games if counts(g) and g["final"]]
    dates = sorted({g["gameday"] for g in games if g.get("gameday")})
    totals = defaultdict(lambda: defaultdict(float))
    snapshots, standings_by_day, results = {}, {}, []
    gi = 0
    full = None
    for d in dates + ["9999-12-31"]:
        while gi < len(reg) and reg[gi]["gameday"] < d:
            g = reg[gi]
            gi += 1
            for side in ("away", "home"):
                team = g[side]["abbr"]
                other = g["away" if side == "home" else "home"]["abbr"]
                results.append((team, other, _result(g, side), side == "home"))
                b = (box.get(g["game_id"]) or {}).get(team)
                if b:
                    t = totals[team]
                    t["g"] += 1
                    for k, v in b.items():
                        if isinstance(v, float):
                            t[k] += v
        snapshots[d] = team_snapshot({t: dict(v) for t, v in totals.items()})
        standings_by_day[d] = standings_rows(list(results))
        full = d
    season_end = full   # the "9999" snapshot: every regular-season game so far

    def snap_for(g):
        if g["phase"] in ("POST", "PLAYIN"):
            return snapshots[season_end], standings_by_day[season_end]
        if g["phase"] == "PRE":
            return {}, standings_by_day[dates[0]] if dates else {}
        return snapshots[g["gameday"]], standings_by_day[g["gameday"]]

    team_games = defaultdict(list)
    for g in games:
        for side in ("away", "home"):
            team_games[g[side]["abbr"]].append(g)

    details = {}
    for g in games:
        try:
            details[g["game_id"]] = game_detail(g, records, snap_for(g), team_games, box, pg, officials,
                                                inj_idx, inj_dates, history, by_id)
        except Exception as e:   # one bad game never costs the others their pages
            warnings.append(f"game {g['game_id']}: {type(e).__name__}: {e}")

    # the standings page: every regular-season game so far, plus ESPN's clinch marks when published
    final_rows = standings_by_day[season_end] if dates else standings_rows([])
    clinch, err = ([], None) if as_of else nba_client.get_standings(season)   # a preview can't know them yet
    if err and reg:
        warnings.append(f"get_standings (clinch marks): {err}")
    for t in clinch or []:
        if t.get("abbr") in final_rows and t.get("clincher"):
            final_rows[t["abbr"]]["clinch"] = t["clincher"]
    through = max((g["gameday"] for g in reg), default=None)

    return {
        "season": season, "season_label": nba_client.season_label(season), "today": today.isoformat(),
        "current_day_key": current_day(days, today), "days": days, "game_details": details,
        "player_games": pg, "standings": list(final_rows.values()), "standings_through": through,
        "reg_games": len(reg),
    }


def game_detail(g, records, snap, team_games, box, pg, officials, inj_idx, inj_dates, history, by_id):
    stats_snap, standings = snap
    r = records.get(g["game_id"]) or {}
    gid = g["game_id"]
    ko = _et(g.get("start"))
    day = datetime.date.fromisoformat(g["gameday"])
    d = {
        "game_id": gid, "game_type": g["phase"], "season_type": g.get("season_type"), "note": g.get("note"),
        "week_key": g["gameday"], "week_label": day_label(day), "gameday": g["gameday"], "gametime": g["gametime"],
        "final": g["final"], "live": g["live"], "postponed": g["postponed"], "ot": g["ot"],
        "overtime": g["ot"] > 0, "status_detail": g.get("status_detail"), "networks": g.get("tv"),
        "score": {"away": g["away"].get("score"), "home": g["home"].get("score")} if (g["final"] or g["live"]) else None,
    }
    lines = {s: g[s].get("linescores") or [] for s in ("away", "home")}
    n = max(len(lines["away"]), len(lines["home"]))
    if (g["final"] or g["live"]) and n:
        d["linescore"] = {"labels": [str(i + 1) if i < 4 else ("OT" if n == 5 else f"OT{i - 3}") for i in range(n)],
                          "away": lines["away"], "home": lines["home"]}
    d["info"] = {
        "tipoff_utc": (datetime.datetime.fromisoformat(g["start"].replace("Z", "+00:00"))
                       .strftime("%Y-%m-%dT%H:%M:%SZ") if g.get("start") else None),
        "referee": officials.get(gid) if g["final"] else None,
        "arena": {"name": g.get("venue"), "city": g.get("city"), "neutral": bool(g.get("neutral_site"))},
        "meetings": meetings(g, history),
    }
    for side in ("away", "home"):
        team = g[side]["abbr"]
        other = g["away" if side == "home" else "home"]["abbr"]
        rr = r.get(side) or {}
        final = g["final"] and rr.get("result")
        starters, ids = starters_before(pg, team, g["gameday"])
        injuries, report = injuries_for(inj_idx, inj_dates, team, g["gameday"], starters, ids)
        st = stats_snap.get(team) or {}
        s = {
            "team": team, "nba": g[side].get("nba", True),
            "record": rr.get("after") if final else rr.get("before"),
            "last": rr.get("last_after") if final else rr.get("last_before"),
            "streak": rr.get("streak_after") if final else rr.get("streak_before"),
            "injuries": injuries[:3], "injury_report_out": report,
            "ranks": {"off_pts": (st.get("points") or {}).get("off_rank"), "off_fg": (st.get("fg_pct") or {}).get("off_rank"),
                      "def_pts": (st.get("points") or {}).get("def_rank"), "def_fg": (st.get("fg_pct") or {}).get("def_rank")},
        }
        if g["final"]:
            s["game_stats"] = _game_stats((box.get(gid) or {}).get(team))
            s["game_absences"] = absences_for(pg, team, gid, starters)
        s["team_page"] = team_page(g, team, other, side, injuries, st, standings, team_games, by_id)
        d[side] = s
    return d


def meetings(g, history):
    """The last 5 times these two teams met before this game (any of the last few seasons; preseason
    left out), newest first."""
    a, h = g["away"]["abbr"], g["home"]["abbr"]
    out = []
    for m in reversed(history):
        if m["game_id"] == g["game_id"] or (m.get("start") or "") >= (g.get("start") or "~"):
            continue
        teams = {m["away"]["abbr"], m["home"]["abbr"]}
        if teams != {a, h}:
            continue
        out.append({"date": m.get("date_et"), "season": m.get("season"), "phase": m.get("phase"),
                    "note": m.get("note"), "home": m["home"]["abbr"],
                    "score": {m["away"]["abbr"]: m["away"].get("score"), m["home"]["abbr"]: m["home"].get("score")}})
        if len(out) == 5:
            break
    return out


def team_page(g, team, other, side, injuries, st, standings, team_games, by_id):
    mine = [x for x in team_games.get(team) or [] if x["phase"]]
    i = next((k for k, x in enumerate(mine) if x["game_id"] == g["game_id"]), 0)
    # game numbers count the regular season (the Cup final and preseason get a label instead)
    number, numbers = 0, {}
    for x in mine:
        if x["postponed"]:
            numbers[x["game_id"]] = "PPD"   # its makeup date is a game of its own
        elif x["phase"] == "REG":
            number += 1
            numbers[x["game_id"]] = str(number)
        else:
            numbers[x["game_id"]] = {"PRE": "PRE", "CUP": "CUP", "PLAYIN": "PI", "POST": "PO"}[x["phase"]]
    window = mine[max(0, i - WINDOW): i + WINDOW + 1]
    schedule = [dict(_schedule_entry(x, team), number=numbers[x["game_id"]], this=x["game_id"] == g["game_id"])
                for x in window]
    # running record after each finished game in the window (regular season: wins and losses so far)
    w = l = 0
    for x in mine:
        if x["phase"] == "REG" and x["final"]:
            res = _result(x, "home" if x["home"]["abbr"] == team else "away")
            w, l = w + (res == "W"), l + (res == "L")
        for e in schedule:
            if e["game_id"] == x["game_id"] and x["final"]:
                e["record_after"] = {"wins": w, "losses": l}
    before = [x for x in mine[:i] if x["final"]]
    recent = [_schedule_entry(x, team) for x in before[-5:]][::-1]

    # rest and travel for this game: days off since the last game, miles from where it was
    prev = mine[i - 1] if i else None
    rest = None
    miles = None
    if prev and prev.get("gameday"):
        rest = (datetime.date.fromisoformat(g["gameday"]) - datetime.date.fromisoformat(prev["gameday"])).days - 1
        if not g.get("neutral_site") and not prev.get("neutral_site"):
            a = nba_teams.HOME_COORDS.get(prev["home"]["abbr"])
            b = nba_teams.HOME_COORDS.get(g["home"]["abbr"])
            if a and b:
                miles = round(_miles(a, b))

    row = (standings or {}).get(team)
    division = []
    if row:
        group = order([x for x in standings.values() if x["div"] == row["div"]])
        lead = group[0]
        division = [{"team": x["team"], "wins": x["w"], "losses": x["l"], "pct": x["pct"], "gb": _gb(lead, x)}
                    for x in group]
    return {
        "injuries_full": injuries,
        "stats": st,
        "schedule": schedule,
        "recent": recent,
        "standings": {"division": f'{row["conf"]} · {row["div"]}' if row else "", "div": row["div"] if row else "",
                      "rows": division} if row else None,
        "splits": {"home": f'{row["hw"]}-{row["hl"]}', "road": f'{row["rw"]}-{row["rl"]}', "l10": row["l10"]} if row else None,
        "next": {"opponent": other, "gameday": g["gameday"], "gametime": g["gametime"], "rest_days": rest,
                 "miles_traveled": miles, "home": side == "home"},
    }


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, help="season by its ending year (2027 = 2026-27); default: the current one")
    ap.add_argument("--today", help="YYYY-MM-DD to build as if it were that day (default: today, ET)")
    ap.add_argument("--as-of", help="YYYY-MM-DD: also hide every result from that day on, so a past season "
                                    "previews as it looked then (implies --today)")
    ap.add_argument("--out", default=OUTPUT_PATH)
    args = ap.parse_args()
    as_of = datetime.date.fromisoformat(args.as_of) if args.as_of else None
    today = as_of or (datetime.date.fromisoformat(args.today) if args.today else datetime.datetime.now(ET).date())
    season = args.season or nba_client.current_season(today)
    warnings = []
    try:
        out = build(season, today, warnings, as_of)
    except Exception as e:   # still write a file the renderer can show an empty season from
        warnings.append(f"build: {type(e).__name__}: {e}")
        out = {"season": season, "season_label": nba_client.season_label(season), "today": today.isoformat(),
               "days": [], "game_details": {}, "player_games": {}, "standings": []}
    out["generated_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    out["warnings"] = warnings
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, separators=(",", ":"), default=str)
    print(f"Wrote {len(out.get('days') or [])} days and {len(out.get('game_details') or {})} games' details "
          f"for {out['season_label']} to {args.out}")
    for w in warnings:
        print(f"  - {w}")


if __name__ == "__main__":
    main()
