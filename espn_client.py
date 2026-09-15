"""
Thin client around ESPN's public (undocumented) NFL endpoints.

IMPORTANT CONTEXT FOR WHOEVER DEBUGS THIS FIRST RUN:
This script was written without the ability to execute live HTTP requests
against these endpoints (the environment it was authored in blocks
outbound calls to non-package-registry hosts by policy). The endpoint
URLs and general JSON shape below were confirmed via a fetch-and-summarize
tool against live ESPN responses, but exact key paths for a few fields
(marked TODO/VERIFY below) are best-effort based on ESPN's typical response
patterns and may need small fixes once this runs somewhere with real
network access (e.g. GitHub Actions). Every parser below uses .get() with
defaults rather than direct key access, specifically so a wrong guess
produces a None/missing value instead of crashing the whole run -- check
the "warnings" list in the output JSON after the first real run to see
what needs adjusting.

No API key is required for any of these. They are unofficial -- ESPN could
change or remove them without notice.
"""

import requests

BASE_SITE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"
BASE_CORE = "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl"

TIMEOUT = 15
HEADERS = {"User-Agent": "at-a-glance-app/0.1 (personal project)"}


def _get(url, params=None):
    """GET with basic error handling. Returns (json_or_none, error_or_none)."""
    try:
        resp = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json(), None
    except Exception as e:
        return None, f"{url} -> {e}"


def get_teams():
    """All 32 teams with ESPN team id, abbreviation, display name."""
    data, err = _get(f"{BASE_SITE}/teams", params={"limit": 40})
    if err:
        return [], err
    teams = []
    for entry in data.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", []):
        t = entry.get("team", {})
        teams.append({
            "id": t.get("id"),
            "abbreviation": t.get("abbreviation"),
            "displayName": t.get("displayName"),
        })
    return teams, None


def get_scoreboard(week=None, seasontype=2, year=None):
    """
    Current (or specified) week's games: date/time, venue, broadcast, teams.
    seasontype: 1=preseason, 2=regular, 3=postseason
    """
    params = {}
    if week:
        params["week"] = week
    if seasontype:
        params["seasontype"] = seasontype
    if year:
        params["dates"] = year
    data, err = _get(f"{BASE_SITE}/scoreboard", params=params)
    if err:
        return [], err

    games = []
    for event in data.get("events", []):
        competition = (event.get("competitions") or [{}])[0]
        venue = competition.get("venue", {})
        address = venue.get("address", {})
        broadcasts = competition.get("broadcasts", [])
        networks = []
        for b in broadcasts:
            networks.extend(b.get("names", []))

        competitors = competition.get("competitors", [])
        home = next((c for c in competitors if c.get("homeAway") == "home"), {})
        away = next((c for c in competitors if c.get("homeAway") == "away"), {})

        games.append({
            "event_id": event.get("id"),
            "date_utc": event.get("date"),  # ISO 8601 UTC
            "name": event.get("name"),
            "venue_name": venue.get("fullName"),
            "city": address.get("city"),
            "state": address.get("state"),
            "indoor": venue.get("indoor"),  # bool, may be None -> cross-check stadiums.py
            "networks": networks,
            "home_team_abbr": (home.get("team") or {}).get("abbreviation"),
            "home_team_id": (home.get("team") or {}).get("id"),
            "away_team_abbr": (away.get("team") or {}).get("abbreviation"),
            "away_team_id": (away.get("team") or {}).get("id"),
        })
    return games, None


def get_team_record(team_id, year, seasontype=2):
    """Overall / home / away / division / conference records for a team."""
    url = f"{BASE_CORE}/seasons/{year}/types/{seasontype}/teams/{team_id}/record"
    data, err = _get(url)
    if err:
        return {}, err

    out = {}
    for item in data.get("items", []):
        name = item.get("name") or item.get("type")  # e.g. "overall", "Home", "vs. Div."
        stats = {s.get("name"): s.get("value") for s in item.get("stats", [])}
        out[name] = {
            "summary": item.get("summary"),  # usually "W-L" or "W-L-T" string
            "wins": stats.get("wins"),
            "losses": stats.get("losses"),
            "ties": stats.get("ties"),
        }
    return out, None


def get_standings(year, seasontype=2):
    """
    Full league standings (both conferences), including division groupings
    and each team's division rank. Returns a dict keyed by team abbreviation.
    TODO/VERIFY: division rank field name -- ESPN sometimes calls this
    'playoffSeed' or a stat named 'divisionRank'; check both.
    """
    out = {}
    for conf_id in (7, 8):  # NFC=7, AFC=8 -- TODO/VERIFY these ids on first run
        url = f"{BASE_CORE}/seasons/{year}/types/{seasontype}/groups/{conf_id}/standings"
        data, err = _get(url)
        if err:
            continue
        for entry in data.get("standings", {}).get("entries", []):
            team = entry.get("team", {})
            abbr = team.get("abbreviation")
            stats = {s.get("name"): s.get("value") for s in entry.get("stats", [])}
            out[abbr] = {
                "division_rank": stats.get("divisionRank") or stats.get("playoffSeed"),
                "division_record": stats.get("divisionRecord") or stats.get("vs. Div."),
                "overall_wins": stats.get("wins"),
                "overall_losses": stats.get("losses"),
            }
    return out, None


def get_team_statistics(team_id):
    """
    Offense + defense splits: points, total/pass/rush yards, red zone, TDs.
    Raw + per-game values. Returns a flat dict of {stat_name: value}.
    League rank is computed separately in ranks.py (not reliably present here).
    """
    url = f"{BASE_SITE}/teams/{team_id}/statistics"
    data, err = _get(url)
    if err:
        return {}, err

    flat = {}
    splits = data.get("splits", {}).get("categories", [])
    for category in splits:  # e.g. "passing", "rushing", "scoring", "miscellaneous"
        for stat in category.get("stats", []):
            flat[stat.get("name")] = {
                "value": stat.get("value"),
                "displayValue": stat.get("displayValue"),
                "perGameValue": stat.get("perGameValue"),
            }
    return flat, None


def get_team_injuries(team_id):
    url = f"{BASE_CORE}/teams/{team_id}/injuries"
    data, err = _get(url, params={"limit": 100})
    if err:
        return [], err

    injuries = []
    for item in data.get("items", []):
        # Each item is often a reference ($ref) rather than inline data on
        # this endpoint -- if so, a second GET per item is needed.
        if "$ref" in item and "status" not in item:
            detail, derr = _get(item["$ref"])
            if derr:
                continue
            item = detail
        athlete = item.get("athlete", {})
        injuries.append({
            "player": athlete.get("displayName") or item.get("longComment"),
            "status": item.get("status"),
            "designation": item.get("type", {}).get("abbreviation") if isinstance(item.get("type"), dict) else item.get("type"),
        })
    return injuries, None


def get_team_schedule(team_id, year, seasontype=2):
    """Full season schedule with results, used to derive last-5 record."""
    url = f"{BASE_SITE}/teams/{team_id}/schedule"
    data, err = _get(url, params={"season": year, "seasontype": seasontype})
    if err:
        return [], err

    games = []
    for event in data.get("events", []):
        competition = (event.get("competitions") or [{}])[0]
        completed = (competition.get("status", {}).get("type", {}) or {}).get("completed", False)
        if not completed:
            continue
        competitors = competition.get("competitors", [])
        this_team = next((c for c in competitors if str(c.get("id")) == str(team_id) or c.get("team", {}).get("id") == str(team_id)), {})
        winner = this_team.get("winner")
        games.append({
            "date": event.get("date"),
            "won": winner,
        })
    # sort by date ascending, most recent last
    games.sort(key=lambda g: g.get("date") or "")
    return games, None


def get_team_roster(team_id):
    url = f"{BASE_SITE}/teams/{team_id}/roster"
    data, err = _get(url)
    if err:
        return [], err

    players = []
    for group in data.get("athletes", []):
        for athlete in group.get("items", []):
            players.append({
                "id": athlete.get("id"),
                "name": athlete.get("displayName"),
                "position": (athlete.get("position") or {}).get("abbreviation"),
                "espn_link": next((l.get("href") for l in athlete.get("links", []) if l.get("rel") and "playercard" in l.get("rel", [])), None),
            })
    return players, None
