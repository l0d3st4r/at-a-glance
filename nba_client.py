"""
NBA data client (2026-10-08), the NBA counterpart of nflverse_client.py.

Where the data comes from (see probe_nba_sources.py for how this was chosen):

  sportsdataverse-data releases   ESPN data that the sportsdataverse project (hoopR) scrapes
                                  and posts as plain files on GitHub, one file per season --
                                  the same model as nflverse. Nothing to get blocked, no key.
                                  Updated by their daily_nba workflow at 07:00 UTC from late
                                  October to early July, after the night's games are over;
                                  rosters, injuries and the schedule were also refreshed
                                  through the 2026 offseason.
  ESPN's scoreboard API           Optional, for scores between those daily updates (tonight's
                                  games, live) and for preseason games, which the schedule
                                  file doesn't include. Answered from GitHub Actions on
                                  2026-10-08 even though ESPN blocked the NFL side's scripted
                                  requests on 2026-09-16 -- so treat it as a bonus that may
                                  disappear: everything here works without it.

Seasons are keyed the way sportsdataverse keys them: by the year the season ENDS, so 2027 is
the 2026-27 season (season_label(2027) == "2026-27").

Teams are identified by ESPN's numeric team id throughout; nba_teams.py maps it to the NBA's
own abbreviation (GSW, not ESPN's GS), conference and division.

Same defensive pattern as nflverse_client.py: every get_* function returns (value, error)
and never raises, so one missing file can't take the whole build down. Before a season's
first game, its box score and standings files don't exist yet -- that comes back as an
empty list and an error saying so, not a crash.
"""

import datetime
import io
import re
from zoneinfo import ZoneInfo

import requests

import nba_teams

RELEASES = "https://github.com/sportsdataverse/sportsdataverse-data/releases/download"
SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
ET = ZoneInfo("America/New_York")
TIMEOUT = 60

# ESPN's scoreboard answers plain scripted requests less reliably than browser-like ones
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/129.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

# season_type codes used by ESPN and sportsdataverse
PRESEASON, REGULAR, POSTSEASON, PLAY_IN = 1, 2, 3, 5


def current_season(today=None):
    """The season the site should show: from October on, the one starting this fall (keyed by
    next year); before that, the one that ended this spring. Same rule as hoopR's
    most_recent_nba_season()."""
    today = today or datetime.datetime.now(ET).date()
    return today.year + 1 if today.month >= 10 else today.year


def season_label(season):
    """2027 -> "2026-27"."""
    return f"{season - 1}-{str(season)[-2:]}"


# ---------------------------------------------------------------- downloads

_CACHE = {}


def _release_file(tag, name):
    """One release file as bytes, downloaded once per run. Raises FileNotFoundError on a 404
    (normal for a season that hasn't started yet)."""
    key = (tag, name)
    if key not in _CACHE:
        r = requests.get(f"{RELEASES}/{tag}/{name}", timeout=TIMEOUT)
        if r.status_code == 404:
            raise FileNotFoundError(f"{tag}/{name} isn't published yet")
        r.raise_for_status()
        _CACHE[key] = r.content
    return _CACHE[key]


def _parquet(tag, name):
    import polars as pl
    return pl.read_parquet(io.BytesIO(_release_file(tag, name)))


def _to_dicts(df):
    """Polars DataFrame -> list of plain dicts, with dates and times as ISO strings so the
    result can go straight into JSON."""
    import polars as pl
    temporal = [c for c, t in df.schema.items() if t in (pl.Date, pl.Time) or isinstance(t, pl.Datetime)]
    if temporal:
        df = df.with_columns([pl.col(c).cast(pl.String) for c in temporal])
    return df.to_dicts()


def _with_abbr(rows, id_key="team_id", out_key="abbr"):
    for r in rows:
        r[out_key] = nba_teams.abbr(r.get(id_key)) or r.get("team_abbreviation")
    return rows


def get_release_stamps(tags=("espn_nba_schedules", "espn_nba_team_boxscores", "espn_nba_player_boxscores",
                             "espn_nba_standings", "espn_nba_rosters", "espn_nba_injuries")):
    """When sportsdataverse last refreshed each release: {tag: "2026-10-07 07:47:47 EDT" or None}.
    Small files (timestamp.json) -- cheap enough for an update check to call often."""
    out, errors = {}, []
    for tag in tags:
        try:
            r = requests.get(f"{RELEASES}/{tag}/timestamp.json", timeout=TIMEOUT)
            r.raise_for_status()
            out[tag] = r.json().get("last_updated")
        except (requests.RequestException, ValueError) as e:
            out[tag] = None
            errors.append(f"{tag}: {e}")
    return out, "; ".join(errors) or None


# ---------------------------------------------------------------- games

_DICT_RE = re.compile(r"\{[^{}]*\}")


def _parse_linescores(text):
    """sportsdataverse stores line scores as the text of a Python list, e.g.
    "[{'displayValue': '27', 'period': 1, 'value': 27.0}\\n {...}]" -> [27, ...] in period order
    (overtimes after the 4th quarter)."""
    out = []
    for d in _DICT_RE.findall(text or ""):
        m = re.search(r"'value':\s*(-?[\d.]+)", d)
        if m:
            out.append(int(float(m.group(1))))
    return out


def _parse_records(text):
    """"[{'abbreviation': 'Game', 'name': 'overall', 'summary': '1-0', 'type': 'total'} ...]"
    -> {"total": "1-0", "home": "1-0", "road": "0-0"}."""
    out = {}
    for d in _DICT_RE.findall(text or ""):
        t = re.search(r"'type':\s*'([^']*)'", d)
        s = re.search(r"'summary':\s*'([^']*)'", d)
        if t and s:
            out[t.group(1)] = s.group(1)
    return out


def _side(team_id, abbr, name, score, winner, linescores, records, state):
    played = state != "pre"
    return {
        "team_id": int(team_id) if str(team_id or "").isdigit() else team_id,
        "abbr": nba_teams.abbr(team_id) or abbr,
        "name": name,
        "nba": nba_teams.team(team_id) is not None,  # False for preseason guests and All-Star teams
        "score": int(score) if played and score not in (None, "") else None,
        "winner": winner if played else None,
        "linescores": linescores if played else [],
        "record": (records or {}).get("total"),
    }


def _game_from_schedule_row(r):
    state = r.get("status_type_state") or "pre"
    side = lambda s: _side(r.get(f"{s}_id"), r.get(f"{s}_abbreviation"), r.get(f"{s}_short_display_name"),
                           r.get(f"{s}_score"), r.get(f"{s}_winner"),
                           _parse_linescores(r.get(f"{s}_linescores")), _parse_records(r.get(f"{s}_records")), state)
    return {
        "game_id": str(r["game_id"]),
        "season": r.get("season"),
        "season_type": r.get("season_type"),
        "type": r.get("type_abbreviation"),          # STD, CC (NBA Cup final), RD16, QTR, SEMI, FINAL, ALLSTAR
        "note": r.get("notes_headline") or None,      # "NBA Cup - Group Play", "West 1st Round - Game 1", ...
        "start": r.get("date"),                       # UTC, "2026-10-20T23:00Z"
        "date_et": str(r["game_date"]) if r.get("game_date") else None,
        "time_valid": r.get("time_valid"),            # False while the tip-off time is still TBD
        "state": state,                               # pre / in / post
        "status": r.get("status_type_name"),          # STATUS_SCHEDULED, STATUS_FINAL, STATUS_POSTPONED, ...
        "status_detail": r.get("status_type_short_detail"),  # "Final/2OT", "10/20 - 7:00 PM EDT"
        "period": int(r["status_period"] or 0) if r.get("status_period") is not None else None,
        "clock": r.get("status_display_clock"),
        "tv": r.get("broadcast") or None,             # national TV only; local broadcasts are blank
        "neutral_site": r.get("neutral_site"),
        "venue": r.get("venue_full_name"),
        "city": r.get("venue_address_city"),
        "home": side("home"),
        "away": side("away"),
        "source": "schedule",
    }


def get_games(season, include_all_star=False):
    """Every game in the season's schedule file, normalized (see _game_from_schedule_row),
    sorted by tip-off. Regular season, NBA Cup, play-in and playoffs; NOT preseason (the file
    doesn't have it -- ESPN's scoreboard does, see get_scoreboard). All-Star games are left out
    unless asked for."""
    try:
        df = _parquet("espn_nba_schedules", f"nba_schedule_{season}.parquet")
        games = [_game_from_schedule_row(r) for r in df.iter_rows(named=True)]
        if not include_all_star:
            games = [g for g in games if g["type"] != "ALLSTAR"]
        return sorted(games, key=lambda g: (g["start"] or "", g["game_id"])), None
    except Exception as e:
        return [], str(e)


def _game_from_espn_event(ev):
    comp = (ev.get("competitions") or [{}])[0]
    status = comp.get("status") or ev.get("status") or {}
    stype = status.get("type") or {}
    state = stype.get("state") or "pre"
    sides = {}
    for c in comp.get("competitors") or []:
        t = c.get("team") or {}
        records = {r.get("type"): r.get("summary") for r in c.get("records") or []}
        lines = [int(float(ls.get("value") or 0)) for ls in c.get("linescores") or []]
        sides[c.get("homeAway")] = _side(t.get("id") or c.get("id"), t.get("abbreviation"),
                                          t.get("shortDisplayName") or t.get("displayName"),
                                          c.get("score"), c.get("winner"), lines, records, state)
    national = [n for b in comp.get("broadcasts") or [] if b.get("market") == "national" for n in b.get("names") or []]
    notes = comp.get("notes") or ev.get("notes") or []
    start = ev.get("date") or comp.get("date")
    date_et = None
    if start:
        try:
            date_et = (datetime.datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(ET).date().isoformat())
        except ValueError:
            pass
    venue = comp.get("venue") or {}
    season = ev.get("season") or {}
    return {
        "game_id": str(ev.get("id")),
        "season": season.get("year"),
        "season_type": season.get("type"),
        "type": (comp.get("type") or {}).get("abbreviation"),
        "note": (notes[0].get("headline") if notes else None) or None,
        "start": start,
        "date_et": date_et,
        "time_valid": comp.get("timeValid"),
        "state": state,
        "status": stype.get("name"),
        "status_detail": stype.get("shortDetail"),
        "period": status.get("period"),
        "clock": status.get("displayClock"),
        "tv": "/".join(dict.fromkeys(national)) or None,
        "neutral_site": comp.get("neutralSite"),
        "venue": venue.get("fullName"),
        "city": (venue.get("address") or {}).get("city"),
        "home": sides.get("home"),
        "away": sides.get("away"),
        "source": "scoreboard",
    }


def get_scoreboard(dates=None):
    """ESPN's scoreboard for the given ET dates (datetime.date or "YYYYMMDD"; default yesterday
    and today, ET), normalized exactly like get_games so the two merge with merge_live.
    Includes preseason games. Optional by design: on any failure it returns ([], error) and the
    site carries on with the schedule file."""
    if dates is None:
        today = datetime.datetime.now(ET).date()
        dates = [today - datetime.timedelta(days=1), today]
    games, errors = {}, []
    for d in dates:
        d = d.strftime("%Y%m%d") if hasattr(d, "strftime") else str(d)
        try:
            r = requests.get(SCOREBOARD, params={"dates": d}, headers=BROWSER_HEADERS, timeout=20)
            r.raise_for_status()
            for ev in r.json().get("events") or []:
                g = _game_from_espn_event(ev)
                if g["home"] and g["away"]:
                    games[g["game_id"]] = g
        except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError) as e:
            errors.append(f"{d}: {type(e).__name__}: {e}")
    return sorted(games.values(), key=lambda g: (g["start"] or "", g["game_id"])), "; ".join(errors) or None


# fields the scoreboard is newer on; everything else (TV, notes, venue) the schedule file keeps
_LIVE_FIELDS = ("state", "status", "status_detail", "period", "clock", "start", "date_et", "time_valid")
_LIVE_SIDE_FIELDS = ("score", "winner", "linescores", "record")


def merge_live(games, live):
    """Schedule games overlaid with the scoreboard's newer status and scores (same game_id),
    plus scoreboard games the schedule doesn't have (preseason). Neither list is modified."""
    by_id = {g["game_id"]: g for g in live}
    out = []
    for g in games:
        lv = by_id.pop(g["game_id"], None)
        if lv:
            g = dict(g, **{k: lv[k] for k in _LIVE_FIELDS if lv.get(k) is not None}, source="schedule+scoreboard")
            for s in ("home", "away"):
                if lv.get(s):
                    g[s] = dict(g[s], **{k: lv[s][k] for k in _LIVE_SIDE_FIELDS})
            if not g.get("tv") and lv.get("tv"):
                g["tv"] = lv["tv"]
        out.append(g)
    out += by_id.values()
    return sorted(out, key=lambda g: (g["start"] or "", g["game_id"]))


# ---------------------------------------------------------------- box scores, standings, people

def get_team_box(season):
    """One row per team per game: team_score, field_goals_made/attempted, three_point_*, free_throws_*,
    total_rebounds, assists, steals, blocks, turnovers, fouls, ... plus opponent_team_*. Adds
    "abbr" and "opponent_abbr" (the NBA's abbreviations). Empty until the season's first game."""
    try:
        rows = _to_dicts(_parquet("espn_nba_team_boxscores", f"team_box_{season}.parquet"))
        return _with_abbr(_with_abbr(rows), "opponent_team_id", "opponent_abbr"), None
    except Exception as e:
        return [], str(e)


def get_player_box(season):
    """One row per player per game: minutes, points, rebounds, assists, steals, blocks, turnovers,
    shooting splits, plus_minus, starter, did_not_play / reason, ... Adds "abbr" and
    "opponent_abbr". Empty until the season's first game."""
    try:
        rows = _to_dicts(_parquet("espn_nba_player_boxscores", f"player_box_{season}.parquet"))
        return _with_abbr(_with_abbr(rows), "opponent_team_id", "opponent_abbr"), None
    except Exception as e:
        return [], str(e)


# standings stat_name -> our key; numbers come from "value", the rest from "display_value"
_STANDINGS_NUMBERS = {
    "wins": "wins", "losses": "losses", "winPercent": "win_pct", "gamesBehind": "games_behind",
    "playoffSeed": "seed", "avgPointsFor": "ppg", "avgPointsAgainst": "opp_ppg", "differential": "diff",
}
_STANDINGS_TEXT = {
    "streak": "streak", "clincher": "clincher", "Home": "home", "Road": "road",
    "vs. Div.": "vs_division", "vs. Conf.": "vs_conference", "Last Ten Games": "last_10",
}


def get_standings(season):
    """ESPN's standings, one dict per team: wins, losses, win_pct, games_behind (in the
    conference), seed, streak ("W3"), clincher ("x", "y", "z", "*", ... or None), home, road,
    vs_division, vs_conference, last_10 (all "W-L" text), ppg, opp_ppg, diff, plus team_id, abbr,
    conference and division. sportsdataverse publishes these with the season's other files, so
    expect none for a season that hasn't started."""
    try:
        df = _parquet("espn_nba_standings", f"standings_{season}.parquet")
        teams = {}
        for r in df.iter_rows(named=True):
            t = teams.setdefault(r["team_id"], dict(nba_teams.team(r["team_id"]) or
                                                    {"team_id": r["team_id"], "abbr": r.get("team_abbreviation")}))
            name = r.get("stat_name")
            if name in _STANDINGS_NUMBERS and r.get("value") is not None:
                v = r["value"]
                t[_STANDINGS_NUMBERS[name]] = int(v) if name in ("wins", "losses", "playoffSeed") else v
            elif name in _STANDINGS_TEXT:
                dv = r.get("display_value")
                t[_STANDINGS_TEXT[name]] = dv if dv not in ("", "-") else None
        out = [t for t in teams.values() if t.get("conference")]
        return sorted(out, key=lambda t: (t["conference"], t.get("seed") or 99)), None
    except Exception as e:
        return [], str(e)


_ROSTER_COLUMNS = ["team_id", "athlete_id", "display_name", "short_name", "jersey", "position_abbreviation",
                   "height", "weight", "age", "experience_years", "headshot_href", "status_name"]


def get_rosters(season):
    """Current roster per team, one row per player (columns above, plus "abbr")."""
    try:
        df = _parquet("espn_nba_rosters", f"rosters_{season}.parquet")
        return _with_abbr(_to_dicts(df.select([c for c in _ROSTER_COLUMNS if c in df.columns]))), None
    except Exception as e:
        return [], str(e)


_INJURY_COLUMNS = ["as_of_date", "team_id", "athlete_id", "athlete_display_name", "athlete_short_name",
                   "athlete_position", "status", "injury_date", "detail_type", "detail_detail", "detail_side",
                   "detail_return_date", "short_comment"]


def get_injuries(season):
    """ESPN's injury list as of its latest daily snapshot (the file keeps every day's; only the
    newest is returned): status ("Out", "Day-To-Day", ...), detail_type ("Knee"), detail_side,
    detail_return_date, short_comment, plus "abbr". Only published as Parquet."""
    try:
        import polars as pl
        df = _parquet("espn_nba_injuries", f"injuries_{season}.parquet")
        df = df.filter(pl.col("as_of_date") == pl.col("as_of_date").max())
        return _with_abbr(_to_dicts(df.select([c for c in _INJURY_COLUMNS if c in df.columns]))), None
    except Exception as e:
        return [], str(e)


# ---------------------------------------------------------------- quick look

def _summary(season=None):
    """`python nba_client.py [season]`: what each loader returns right now."""
    season = season or current_season()
    print(f"current season {season} ({season_label(season)})")
    stamps, err = get_release_stamps()
    print("release stamps:", stamps, err or "")

    for s in (season, season - 1):
        games, err = get_games(s)
        states = {}
        for g in games:
            states[g["state"]] = states.get(g["state"], 0) + 1
        print(f"\n== {s}: {len(games)} games {states} {err or ''}")
        if games:
            finals = [g for g in games if g["state"] == "post"]
            for g in ([finals[-1]] if finals else []) + [games[0]]:
                print("  ", {k: g[k] for k in ("game_id", "start", "date_et", "type", "note", "state", "status_detail", "tv")})
                print("     away", g["away"])
                print("     home", g["home"])
        for name, fn in (("team box", get_team_box), ("player box", get_player_box), ("standings", get_standings),
                         ("rosters", get_rosters), ("injuries", get_injuries)):
            rows, err = fn(s)
            print(f"  {name}: {len(rows)} rows {err or ''}")
            if rows and name in ("standings", "injuries"):
                print("    first:", rows[0])

    live, err = get_scoreboard()
    print(f"\n== scoreboard (yesterday + today ET): {len(live)} games {err or ''}")
    for g in live[:3]:
        print("  ", {k: g[k] for k in ("game_id", "season", "season_type", "start", "state", "status_detail", "tv", "note")})
        print("     away", g["away"])
        print("     home", g["home"])
    games, _ = get_games(season)
    merged = merge_live(games, live)
    print(f"merged: {len(merged)} games ({len(merged) - len(games)} only on the scoreboard, "
          f"{sum(1 for g in merged if g['source'] == 'schedule+scoreboard')} overlaid)")


if __name__ == "__main__":
    import sys
    _summary(int(sys.argv[1]) if len(sys.argv) > 1 else None)
