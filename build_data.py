"""
Orchestrator, v2 -- rebuilt on nflreadpy/nflverse after ESPN's API turned
out to be behind Akamai bot-detection (see nflverse_client.py docstring
for the full story). Run with: python build_data.py

KNOWN GAPS in this pass (flagged, not hidden -- see field-by-field notes
below and in the output JSON's "warnings" list):
  - TV network / "where to watch" -- no field found in nflverse's data.
    Left as "pending". Needs a separate small source, follow-up work.
  - Red zone stats specifically -- not confirmed as direct columns in
    nflverse's team stats. The FULL raw team-stats row is included per
    team in the output regardless, so once we can see real column names
    from a live run, wiring up red zone (and confirming which of the
    many stat columns map to points/yards/etc.) is a quick follow-up
    rather than a re-fetch.
  - Season leaders (passing/rushing/receiving yards, sacks, tackles,
    interceptions per team) -- still not wired up, same "pending" stub
    as the ESPN-based version. nflverse's load_seasonal_data/weekly
    player stats could likely answer this; deferred to keep this
    rebuild focused on parity with what was already working.
"""

import json
import os
from datetime import datetime, timezone

import nflverse_client
from divisions import get_division, normalize_abbr
from stadiums import STADIUMS
from weather import get_kickoff_weather
from ranks import compute_ranks
import page1_data

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "data", "matchups.json")

# Candidate key names nflverse might use for "team abbreviation" and
# "player name" columns -- tried in order, first match wins. Defensive
# against not knowing the exact schema for certain until a live run.
TEAM_KEY_CANDIDATES = ["team", "team_abbr", "recent_team", "posteam"]
PLAYER_NAME_CANDIDATES = ["player_name", "full_name", "player_display_name", "name"]


def _first_present_key(row, candidates):
    for c in candidates:
        if c in row:
            return c
    return None


def index_by_team(rows):
    """List of dicts -> {team_abbr: row}, using whichever key name is present."""
    if not rows:
        return {}
    key = _first_present_key(rows[0], TEAM_KEY_CANDIDATES)
    if not key:
        return {}
    return {normalize_abbr(r.get(key)): r for r in rows if r.get(key)}


def team_results_from_schedules(schedules, team_abbr):
    """
    Completed games involving team_abbr, sorted by date, each as
    {"opponent": ..., "won": bool, "division_game": bool}.
    """
    results = []
    for g in schedules:
        home = normalize_abbr(g.get("home_team"))
        away = normalize_abbr(g.get("away_team"))
        if team_abbr not in (home, away):
            continue
        home_score = g.get("home_score")
        away_score = g.get("away_score")
        if home_score is None or away_score is None:
            continue  # not yet played
        is_home = team_abbr == home
        opponent = away if is_home else home
        team_score = home_score if is_home else away_score
        opp_score = away_score if is_home else home_score
        won = team_score > opp_score if team_score != opp_score else None  # None = tie
        results.append({
            "date": g.get("gameday"),
            "opponent": opponent,
            "won": won,
            "division_game": get_division(team_abbr) == get_division(opponent),
        })
    results.sort(key=lambda r: r.get("date") or "")
    return results


def record_summary(results):
    wins = sum(1 for r in results if r["won"] is True)
    losses = sum(1 for r in results if r["won"] is False)
    ties = sum(1 for r in results if r["won"] is None)
    return {"wins": wins, "losses": losses, "ties": ties}


# ---------------------------------------------------------------- full season (Page 0 week switcher)

# nflverse game_type values -> display label, in bracket order.
PLAYOFF_ROUNDS = [
    ("WC", "Wild Card"),
    ("DIV", "Divisional Round"),
    ("CON", "Conference Championships"),
    ("SB", "Super Bowl"),
]
# Fallback when a week number is past the regular season but no games for it
# are in the schedule yet (nflverse numbering since the 2021 season).
PLAYOFF_WEEK_NUMBERS = {19: "WC", 20: "DIV", 21: "CON", 22: "SB", 23: "SB"}


def _score(value):
    return value if isinstance(value, (int, float)) else None


def _overtime(value):
    """nflverse schedules 'overtime' column: 1 = went to OT, 0 = didn't, missing for unplayed games."""
    try:
        return int(float(value)) == 1
    except (TypeError, ValueError):
        return False


def build_season_weeks(schedules, current_week):
    """
    Every week of the season for the Page 0 week dropdown, built only from
    the schedule (cheap -- no per-team injuries/rosters/stats here).

    Returns (weeks, current_key):
      weeks = [{"key": "1", "label": "Week 1", "game_type": "REG", "games": [...]}, ...,
               {"key": "WC", "label": "Wild Card", "game_type": "WC", "games": [...]}, ...]
      Playoff rounds are always included; their "games" list stays empty until
      nflverse adds those games (render_html.py shows placeholder tiles meanwhile).

    Records are FROZEN per game (added 2026-09-16):
      - finished regular-season game -> each team's record right after that game
        (so Week 1 keeps showing 1-0 / 0-1 all season)
      - game not played yet, or any playoff game -> each team's current
        regular-season record
    A game counts as finished ("final": true) once nflverse has both scores;
    "overtime": true when nflverse marks that finished game as going to OT.
    """
    blank = lambda: {"wins": 0, "losses": 0, "ties": 0}

    def is_final(g):
        return _score(g.get("home_score")) is not None and _score(g.get("away_score")) is not None

    # Walk finished regular-season games in kickoff order, keeping a running
    # record per team and snapshotting it after each game.
    running = {}
    frozen = {}  # game_id -> {team: record after that game}
    finished_reg = sorted(
        (g for g in schedules if g.get("game_type") == "REG" and is_final(g)),
        key=lambda g: (str(g.get("gameday") or ""), str(g.get("gametime") or ""), str(g.get("game_id") or "")),
    )
    for g in finished_reg:
        home, away = normalize_abbr(g.get("home_team")), normalize_abbr(g.get("away_team"))
        hs, as_ = _score(g.get("home_score")), _score(g.get("away_score"))
        snapshot = {}
        for team, mine, theirs in ((home, hs, as_), (away, as_, hs)):
            r = running.setdefault(team, blank())
            r["wins" if mine > theirs else "losses" if mine < theirs else "ties"] += 1
            snapshot[team] = dict(r)
        frozen[g.get("game_id")] = snapshot

    def record_for(g, team):
        at_game = frozen.get(g.get("game_id"), {}).get(team)
        return at_game if at_game is not None else dict(running.get(team, blank()))

    def game_entry(g):
        home, away = normalize_abbr(g.get("home_team")), normalize_abbr(g.get("away_team"))
        return {
            "game_id": g.get("game_id"),
            "game_type": g.get("game_type"),
            "week": g.get("week"),
            "gameday": g.get("gameday"),
            "gametime": g.get("gametime"),
            "final": is_final(g),
            "overtime": is_final(g) and _overtime(g.get("overtime")),
            "networks": {"status": "pending"},
            "away": {"team": away, "record": record_for(g, away), "score": _score(g.get("away_score"))},
            "home": {"team": home, "record": record_for(g, home), "score": _score(g.get("home_score"))},
        }

    reg_weeks = {}
    playoff_games = {code: [] for code, _ in PLAYOFF_ROUNDS}
    week_to_type = {}
    for g in schedules:
        gtype, wk = g.get("game_type"), g.get("week")
        if wk is not None:
            week_to_type.setdefault(wk, gtype)
        if gtype == "REG" and wk is not None:
            reg_weeks.setdefault(int(wk), []).append(game_entry(g))
        elif gtype in playoff_games:
            playoff_games[gtype].append(game_entry(g))

    weeks = [{"key": str(wk), "label": f"Week {wk}", "game_type": "REG", "games": reg_weeks[wk]}
             for wk in sorted(reg_weeks)]
    weeks += [{"key": code, "label": label, "game_type": code, "games": playoff_games[code]}
              for code, label in PLAYOFF_ROUNDS]

    current_key = None
    if current_week is not None:
        wtype = week_to_type.get(current_week)
        if wtype == "REG" or (wtype is None and int(current_week) <= 18):
            current_key = str(current_week)
        else:
            current_key = wtype if wtype in playoff_games else PLAYOFF_WEEK_NUMBERS.get(int(current_week))
    return weeks, current_key


def build_team_snapshot(team_abbr, schedules, team_stats_by_team, ranks_by_team, rosters_by_team_raw, injuries_by_team_raw, warnings):
    team_abbr = normalize_abbr(team_abbr)
    all_results = team_results_from_schedules(schedules, team_abbr)
    division_results = [r for r in all_results if r["division_game"]]
    last5 = all_results[-5:]

    stats = team_stats_by_team.get(team_abbr, {})
    ranks = ranks_by_team.get(team_abbr, {})

    roster_rows = rosters_by_team_raw.get(team_abbr, [])
    name_key = _first_present_key(roster_rows[0], PLAYER_NAME_CANDIDATES) if roster_rows else None
    roster = [{"name": r.get(name_key), "position": r.get("position")} for r in roster_rows] if name_key else []
    if roster_rows and not name_key:
        warnings.append(f"roster[{team_abbr}]: none of {PLAYER_NAME_CANDIDATES} found as a column -- check real column names")

    injuries = injuries_by_team_raw.get(team_abbr, [])

    return {
        "team": team_abbr,
        "division": get_division(team_abbr),
        "record": record_summary(all_results),
        "division_record": record_summary(division_results),
        "last_5": record_summary(last5),
        "injuries": injuries,  # raw rows, schema TBD on first real run
        "roster": roster,
        "season_leaders": {"status": "pending", "note": "Not yet wired up -- see build_data.py docstring."},
        "stats_raw": stats,     # full raw row from nflverse, all columns, until we confirm exact names
        "stats_ranks": ranks,   # rank per numeric column found in stats_raw
    }


def main():
    warnings = []

    season, week, err = nflverse_client.get_current_season_and_week()
    if err:
        warnings.append(f"get_current_season_and_week: {err}")
    if season is None:
        season = datetime.now(timezone.utc).year

    schedules, err = nflverse_client.get_schedules(season)
    if err:
        warnings.append(f"get_schedules: {err}")

    team_stats_rows, err = nflverse_client.get_team_stats(season)
    if err:
        warnings.append(f"get_team_stats: {err}")
    team_stats_by_team = index_by_team(team_stats_rows)
    ranks_by_team = compute_ranks(team_stats_by_team)

    injury_rows, err = nflverse_client.get_injuries(season)
    if err:
        warnings.append(f"get_injuries: {err}")
    injuries_by_team_raw = {}
    if injury_rows:
        key = _first_present_key(injury_rows[0], TEAM_KEY_CANDIDATES)
        if key:
            for row in injury_rows:
                abbr = normalize_abbr(row.get(key))
                injuries_by_team_raw.setdefault(abbr, []).append(row)
        else:
            warnings.append(f"injuries: none of {TEAM_KEY_CANDIDATES} found as a team column -- check real column names")

    roster_rows, err = nflverse_client.get_rosters(season)
    if err:
        warnings.append(f"get_rosters: {err}")
    rosters_by_team_raw = {}
    if roster_rows:
        key = _first_present_key(roster_rows[0], TEAM_KEY_CANDIDATES)
        if key:
            for row in roster_rows:
                abbr = normalize_abbr(row.get(key))
                rosters_by_team_raw.setdefault(abbr, []).append(row)
        else:
            warnings.append(f"rosters: none of {TEAM_KEY_CANDIDATES} found as a team column -- check real column names")

    # Filter to this week's games. Fall back to "next games with no score
    # yet" if the week number doesn't line up with what we expect.
    this_week_games = [g for g in schedules if g.get("week") == week] if week else []
    if not this_week_games:
        this_week_games = [g for g in schedules if g.get("home_score") is None][:16]
        if this_week_games:
            warnings.append("week filter didn't match any games -- fell back to 'next unplayed games'; check get_current_week() and schedules['week'] alignment")

    matchups = []
    for g in this_week_games:
        home_abbr = normalize_abbr(g.get("home_team"))
        away_abbr = normalize_abbr(g.get("away_team"))
        stadium = page1_data.stadium_for(home_abbr)  # handles WAS (stadiums.py uses ESPN's WSH)

        roof = g.get("roof")  # nflverse: "outdoors" | "dome" | "closed" | "open" (best guess at values)
        is_indoor = roof in ("dome", "closed") if roof else stadium.get("indoor")

        weather = {"available": False, "reason": "indoor stadium"}
        if not is_indoor and stadium.get("lat") and g.get("gameday") and g.get("gametime"):
            # nflverse gametime is US Eastern -- convert to UTC before asking NWS (fixed 2026-09-16)
            ko = page1_data.kickoff_utc(g["gameday"], g["gametime"])
            kickoff_iso = ko.strftime("%Y-%m-%dT%H:%M:00Z") if ko else f"{g['gameday']}T{g['gametime']}:00Z"
            weather = get_kickoff_weather(stadium["lat"], stadium["lon"], kickoff_iso)

        matchups.append({
            "game_id": g.get("game_id"),
            "gameday": g.get("gameday"),
            "gametime": g.get("gametime"),
            "venue": g.get("stadium") or stadium.get("name"),
            "roof": roof,
            "indoor": is_indoor,
            "surface": g.get("surface"),
            "networks": {"status": "pending", "note": "No TV network field found in nflverse schedule data -- needs a separate source, see build_data.py docstring."},
            "weather": weather,
            "home": build_team_snapshot(home_abbr, schedules, team_stats_by_team, ranks_by_team, rosters_by_team_raw, injuries_by_team_raw, warnings),
            "away": build_team_snapshot(away_abbr, schedules, team_stats_by_team, ranks_by_team, rosters_by_team_raw, injuries_by_team_raw, warnings),
        })

    # Full season for the Page 0 week dropdown. Wrapped so a problem here can
    # never break the existing current-week data above.
    season_weeks, current_week_key = [], None
    try:
        season_weeks, current_week_key = build_season_weeks(schedules, week)
    except Exception as e:
        warnings.append(f"build_season_weeks: {e}")

    # Page 1 (matchup page) data for every game of the season. Wrapped so a
    # problem here can never break Page 0's data above.
    game_details = {}
    try:
        team_weekly, err = nflverse_client.get_team_stats_weekly(season)
        if err:
            warnings.append(f"get_team_stats_weekly: {err}")
        player_weekly, err = nflverse_client.get_player_stats_weekly(season)
        if err:
            warnings.append(f"get_player_stats_weekly: {err}")
        snaps, err = nflverse_client.get_snap_counts(season)
        if err:
            warnings.append(f"get_snap_counts: {err}")
        depth, err = nflverse_client.get_depth_charts(season)
        if err:
            warnings.append(f"get_depth_charts: {err}")
        history, err = nflverse_client.get_schedules_all()  # Page 2's "last matchup" (2026-09-19)
        if err:
            warnings.append(f"get_schedules_all: {err} -- last matchup limited to this season")
        game_details = page1_data.build_game_details(schedules, team_weekly, player_weekly, injury_rows, snaps, warnings,
                                                     depth=depth, history=history or None)
    except Exception as e:
        warnings.append(f"build_game_details: {e}")

    output = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "season": season,
        "week": week,
        "current_week_key": current_week_key,
        "warnings": warnings,
        "matchups": matchups,
        "season_weeks": season_weeks,
        "game_details": game_details,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"Wrote {len(matchups)} matchups and {len(game_details)} game pages' data to {OUTPUT_PATH}")
    if warnings:
        print(f"{len(warnings)} warning(s):")
        for w in warnings:
            print(f"  - {w}")


if __name__ == "__main__":
    main()
