"""
Orchestrator: pulls everything needed for the current week's matchups and
writes it out as data/matchups.json. This is the whole "v0" pipeline --
raw data, no presentation.

Run with: python build_data.py

SEASON LEADERS NOTE (passing/rushing/receiving yards, sacks, tackles,
interceptions per team): getting these as *season* totals (not single-game)
does not have a confirmed clean endpoint yet -- see product-spec.md's
"Open questions". Computing it properly means either (a) finding a working
league-wide season leaderboard endpoint and filtering per team, or
(b) pulling every roster player's individual season stats and taking the
max per category, which is 50+ extra calls per team and probably too slow
to run every scheduled refresh. For v0 this field is left as a clearly
marked "pending" stub rather than block the rest of the pipeline --
same call Jason made on historical head-to-head data. Worth a follow-up
pass once the rest of the pipeline is confirmed working end to end.
"""

import json
import os
from datetime import datetime, timezone

import espn_client
from stadiums import STADIUMS
from weather import get_kickoff_weather
from ranks import compute_ranks

CURRENT_YEAR = datetime.now(timezone.utc).year
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "data", "matchups.json")

OFFENSE_STAT_KEYS = [
    "totalPointsPerGame", "totalYards", "yardsPerGame",
    "netPassingYards", "netPassingYardsPerGame",
    "rushingYards", "rushingYardsPerGame",
    "totalTouchdowns", "redzoneScoringPct", "redzoneTouchdownPct",
]


def build_team_snapshot(team_id, team_abbr, year, all_team_stats, league_ranks, warnings):
    record, err = espn_client.get_team_record(team_id, year)
    if err:
        warnings.append(f"record[{team_abbr}]: {err}")

    injuries, err = espn_client.get_team_injuries(team_id)
    if err:
        warnings.append(f"injuries[{team_abbr}]: {err}")

    schedule, err = espn_client.get_team_schedule(team_id, year)
    if err:
        warnings.append(f"schedule[{team_abbr}]: {err}")
    last5 = schedule[-5:] if schedule else []
    last5_wins = sum(1 for g in last5 if g.get("won") is True)
    last5_losses = sum(1 for g in last5 if g.get("won") is False)

    roster, err = espn_client.get_team_roster(team_id)
    if err:
        warnings.append(f"roster[{team_abbr}]: {err}")

    stats = all_team_stats.get(team_abbr, {})
    ranks = league_ranks.get(team_abbr, {})
    stats_with_rank = {
        key: {
            "value": stats.get(key, {}).get("value"),
            "per_game": stats.get(key, {}).get("perGameValue"),
            "display": stats.get(key, {}).get("displayValue"),
            "league_rank": ranks.get(key),
        }
        for key in OFFENSE_STAT_KEYS
    }

    return {
        "team": team_abbr,
        "record": record.get("overall") or record.get("total"),
        "division_record": record.get("vs. Div.") or record.get("Division"),
        "last_5": {"wins": last5_wins, "losses": last5_losses, "games_found": len(last5)},
        "injuries": injuries,
        "roster": roster,
        "season_leaders": {
            "status": "pending",
            "note": "Season-long team leaders not yet wired up -- see build_data.py docstring.",
        },
        "stats": stats_with_rank,
    }


def main():
    warnings = []

    teams, err = espn_client.get_teams()
    if err:
        warnings.append(f"get_teams: {err}")

    games, err = espn_client.get_scoreboard()
    if err:
        warnings.append(f"get_scoreboard: {err}")

    # Pull raw stats for every team once, used both for each matchup's own
    # numbers and for computing league-wide ranks.
    all_team_stats = {}
    for t in teams:
        stats, err = espn_client.get_team_statistics(t["id"])
        if err:
            warnings.append(f"statistics[{t['abbreviation']}]: {err}")
        all_team_stats[t["abbreviation"]] = stats

    league_ranks = compute_ranks(all_team_stats, OFFENSE_STAT_KEYS, higher_is_better=True)

    matchups = []
    for game in games:
        home_abbr = game["home_team_abbr"]
        away_abbr = game["away_team_abbr"]

        stadium = STADIUMS.get(home_abbr, {})
        is_indoor = game.get("indoor")
        if is_indoor is None:
            is_indoor = stadium.get("indoor")

        weather = {"available": False, "reason": "indoor stadium"}
        if not is_indoor and stadium.get("lat") and game.get("date_utc"):
            weather = get_kickoff_weather(stadium["lat"], stadium["lon"], game["date_utc"])

        matchups.append({
            "event_id": game["event_id"],
            "date_utc": game["date_utc"],
            "venue": game["venue_name"] or stadium.get("name"),
            "city": game["city"] or stadium.get("city"),
            "state": game["state"] or stadium.get("state"),
            "indoor": is_indoor,
            "networks": game["networks"],
            "weather": weather,
            "home": build_team_snapshot(game["home_team_id"], home_abbr, CURRENT_YEAR, all_team_stats, league_ranks, warnings),
            "away": build_team_snapshot(game["away_team_id"], away_abbr, CURRENT_YEAR, all_team_stats, league_ranks, warnings),
        })

    output = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "warnings": warnings,
        "matchups": matchups,
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Wrote {len(matchups)} matchups to {OUTPUT_PATH}")
    if warnings:
        print(f"{len(warnings)} warning(s) -- see output JSON's 'warnings' list:")
        for w in warnings:
            print(f"  - {w}")


if __name__ == "__main__":
    main()
