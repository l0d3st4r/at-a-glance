"""
Injured reserve (added 2026-10-03): every player on IR gets a small "IR" after his position
wherever his name shows -- Player Stats, the Leaders card, the injury lists -- like rookies.py's R.
Each team's Page 2 Injuries card also lists its IR (attach), since a player drops off the weekly
injury report once he's placed there and may otherwise show nowhere at all: starters first (the
card shows three and counts the rest), with the team's man-games lost this season and its league rank.

Who counts: nflverse's weekly rosters carry the NFL's own roster code for every player
(status_description_abbr). A player is on IR when his latest week's row has status "RES" and
one of IR_CODES -- so a player cut or activated since then loses the tag on the next build.
That is the league's injured reserve, not "out for the season": the NFL doesn't mark season-ending
IR apart from the rest, and any IR player may come back after missing four games (R48, the
21-day return window, is still IR until he's activated).

Matched by gsis id where the data carries one, otherwise by full name -- only for names no
other rostered player shares, as in rookies.py.
"""

import rookies
from divisions import normalize_abbr

# R01 Reserve/Injured, R48 Reserve/Injured; Designated for Return. PUP (R04), NFI (R05) and the
# other reserve lists aren't IR, so they're left out.
IR_CODES = {"R01", "R48"}
IR_STATUS_SHORT = {"R48": "Return Window"}   # opened his 21-day practice window, can be activated any day
# Man-games lost also counts PUP (R04): out injured since camp, the same as IR for a game missed.
MISSED_CODES = IR_CODES | {"R04"}

# The team's IR list runs offense, defense, then specialists (weekly rosters use these broad groups)
POSITION_ORDER = {p: i for i, p in enumerate(["QB", "RB", "FB", "WR", "TE", "OL", "T", "G", "C",
                                              "DL", "DE", "DT", "LB", "OLB", "ILB", "DB", "CB", "S", "SAF",
                                              "K", "P", "LS"])}


def build(rosters_weekly, warnings, is_starter=None):
    """{"ids": set of gsis ids, "names": set of name keys, "teams": {team: [player rows]}} for players
    on IR as of the latest roster week. is_starter(team, gsis_id, name) (page1_data.season_starters)
    marks who started for his team this season; they lead the team's list."""
    latest = {}   # player -> his latest week's row
    for r in rosters_weekly or []:
        who = r.get("gsis_id") or rookies._key(r.get("full_name"))
        try:
            wk = int(r.get("week"))
        except (TypeError, ValueError):
            continue
        if who and (who not in latest or wk >= latest[who][0]):
            latest[who] = (wk, r)
    ids, names, other_names, teams = set(), set(), set(), {}
    for _, r in latest.values():
        key = rookies._key(r.get("full_name"))
        code = r.get("status_description_abbr")
        if r.get("status") == "RES" and code in IR_CODES:
            team = normalize_abbr(r.get("team"))
            teams.setdefault(team, []).append(
                {"name": r.get("full_name") or "", "gsis_id": r.get("gsis_id"), "position": r.get("position") or "",
                 "status": "IR", "designation": IR_STATUS_SHORT.get(code),
                 "starter": bool(is_starter and is_starter(team, r.get("gsis_id"), r.get("full_name")))})
            if r.get("gsis_id"):
                ids.add(r["gsis_id"])
            if key:
                names.add(key)
        elif key:
            other_names.add(key)
    if rosters_weekly and "status_description_abbr" not in rosters_weekly[0]:
        warnings.append("reserve: weekly rosters have no status_description_abbr -- no IR tags")
    for rows in teams.values():
        rows.sort(key=lambda r: (not r["starter"], POSITION_ORDER.get(r["position"], len(POSITION_ORDER)), r["name"]))
    return {"ids": ids, "names": names - other_names, "teams": teams}


def man_games_lost(rosters_weekly, injury_rows, game_details):
    """{team: {"games": n, "rank": league rank, most first}} -- player-games missed through injury in
    the team's finished regular-season games: on IR or PUP that week, or inactive while on that week's
    injury report. A healthy scratch, or an absence the report calls "not injury related" (rest, a
    personal matter), doesn't count."""
    played = set()   # (team, week) of every finished regular-season game
    for d in (game_details or {}).values():
        if d.get("final") and d.get("game_type") == "REG":
            for which in ("away", "home"):
                played.add(((d.get(which) or {}).get("team"), d.get("week")))
    hurt = set()   # (team, week, gsis id) on that week's injury report for an injury
    for r in injury_rows or []:
        reasons = " ".join(str(r.get(k) or "") for k in ("report_primary_injury", "report_secondary_injury",
                                                          "practice_primary_injury", "practice_secondary_injury")).lower()
        if r.get("gsis_id") and "not injury related" not in reasons:
            try:
                hurt.add((normalize_abbr(r.get("team")), int(r.get("week")), r["gsis_id"]))
            except (TypeError, ValueError):
                pass
    games = {team: 0 for team, _ in played}
    for r in rosters_weekly or []:
        try:
            team, week = normalize_abbr(r.get("team")), int(r.get("week"))
        except (TypeError, ValueError):
            continue
        if (team, week) not in played:
            continue
        if ((r.get("status") == "RES" and r.get("status_description_abbr") in MISSED_CODES)
                or (r.get("status") == "INA" and (team, week, r.get("gsis_id")) in hurt)):
            games[team] += 1
    return {team: {"games": n, "rank": 1 + sum(m > n for m in games.values())} for team, n in games.items()}


def attach(game_details, ir, man_games=None):
    """Each side's team_page gets "injured_reserve" (its team's IR list) and "man_games_lost", in place."""
    for d in (game_details or {}).values():
        for which in ("away", "home"):
            side = d.get(which) or {}
            if isinstance(side.get("team_page"), dict):
                side["team_page"]["injured_reserve"] = (ir or {}).get("teams", {}).get(side.get("team"), [])
                side["team_page"]["man_games_lost"] = (man_games or {}).get(side.get("team"))


def mark(game_details, player_weeks, ir):
    """Sets "ir": True on every IR player's player-stats rows, leaders and injury rows, in place."""
    if not ir or not (ir["ids"] or ir["names"]):
        return
    rookies.flag(game_details, player_weeks, "ir",
                 lambda gsis_id, name: bool(gsis_id and gsis_id in ir["ids"])
                 or bool(name and rookies._key(name) in ir["names"]))
