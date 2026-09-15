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
        stadium = STADIUMS.get(home_abbr, {})

        roof = g.get("roof")  # nflverse: "outdoors" | "dome" | "closed" | "open" (best guess at values)
        is_indoor = roof in ("dome", "closed") if roof else stadium.get("indoor")

        weather = {"available": False, "reason": "indoor stadium"}
        if not is_indoor and stadium.get("lat") and g.get("gameday") and g.get("gametime"):
            kickoff_iso = f"{g['gameday']}T{g['gametime']}:00Z"  # best-effort combine; verify TZ handling on first run
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

    output = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "season": season,
        "week": week,
        "warnings": warnings,
        "matchups": matchups,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"Wrote {len(matchups)} matchups to {OUTPUT_PATH}")
    if warnings:
        print(f"{len(warnings)} warning(s):")
        for w in warnings:
            print(f"  - {w}")


if __name__ == "__main__":
    main()
