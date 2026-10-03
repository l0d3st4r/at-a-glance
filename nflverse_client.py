"""
Data client built on nflreadpy (https://github.com/nflverse/nflreadpy),
replacing the earlier ESPN-based client after ESPN's API turned out to be
behind Akamai bot-detection that blocks any scripted request regardless of
source IP (confirmed 2026-09-16 -- failed identically from GitHub Actions
and from a home internet connection).

nflreadpy pulls community-maintained NFL data that's published as plain
data files on GitHub (nflverse-data releases) -- there's no live API to
get blocked, which is exactly why this is a more durable foundation for
an automated pipeline than scraping ESPN's undocumented endpoints.

IMPORTANT CONTEXT FOR WHOEVER DEBUGS THE FIRST RUN OF *THIS* VERSION:
Same caveat as before -- this was written without live execution (sandbox
network policy), so exact column names for load_team_stats() in particular
are a best guess based on nflverse's typical naming (e.g. "passing_yards",
"rushing_yards") and may need small fixes. To make that easy, build_data.py
dumps the actual column names it finds into the output JSON's "warnings"/
"debug_columns" so mismatches are visible immediately rather than silently
producing empty fields.

KNOWN GAPS vs. the ESPN-based version (flagged honestly, not hidden):
- No TV network / broadcast field found in nflverse's schedule data --
  that's the one field this switch doesn't recover. Needs a separate
  small source later (out of scope for this pass).
- No direct red-zone stat columns confirmed -- would need to be computed
  from play-by-play data (nfl.load_pbp_data), which is heavier and left
  as a follow-up rather than blocking this rebuild.
- No dedicated division-rank/standings function -- computed ourselves in
  build_data.py from schedule results + divisions.py, same approach as
  the last-5-games record.
"""

import nflreadpy as nfl


def _to_dicts(df):
    """Polars DataFrame -> list of plain dicts, defensively."""
    try:
        return df.to_dicts()
    except Exception as e:
        return []


def get_current_season_and_week():
    try:
        season = nfl.get_current_season()
        week = nfl.get_current_week()
        return season, week, None
    except Exception as e:
        return None, None, str(e)


def get_schedules(season):
    try:
        df = nfl.load_schedules(seasons=[season])
        return _to_dicts(df), None
    except Exception as e:
        return [], str(e)


def get_team_stats(season):
    """
    Season-to-date team stats. summary_level="reg" is a guess at the
    param value that returns one row per team for the season so far
    (vs. one row per team per week) -- flagged for verification on
    first real run.
    """
    try:
        df = nfl.load_team_stats(seasons=[season], summary_level="reg")
        return _to_dicts(df), None
    except Exception as e:
        # Fall back to default args in case summary_level isn't accepted
        # the way we guessed.
        try:
            df = nfl.load_team_stats(seasons=[season])
            return _to_dicts(df), f"used fallback call (no summary_level) after: {e}"
        except Exception as e2:
            return [], str(e2)


def get_injuries(season):
    try:
        df = nfl.load_injuries(seasons=[season])
        return _to_dicts(df), None
    except Exception as e:
        return [], str(e)


def get_rosters(season):
    try:
        df = nfl.load_rosters(seasons=[season])
        return _to_dicts(df), None
    except Exception as e:
        return [], str(e)


# ---------------------------------------------------------------- Page 1 (added 2026-09-16)
# Week-by-week data so Page 1 can show each game "as of kickoff": ranks and
# season leaders use only the weeks before that game. Same defensive pattern
# as above -- every call returns (rows, error) and never raises.

def get_team_stats_weekly(season):
    """One row per team per game (columns match the season rows seen on the live site, plus week/opponent)."""
    try:
        df = nfl.load_team_stats(seasons=[season], summary_level="week")
        return _to_dicts(df), None
    except Exception as e:
        return [], str(e)


def get_player_stats_weekly(season):
    """One row per player per game: passing/rushing/receiving yards, def_interceptions, def_sacks, ..."""
    try:
        df = nfl.load_player_stats(seasons=[season], summary_level="week")
        return _to_dicts(df), None
    except Exception as e:
        try:
            df = nfl.load_player_stats(seasons=[season])
            return _to_dicts(df), f"used fallback call (no summary_level) after: {e}"
        except Exception as e2:
            return [], str(e2)


def get_snap_counts(season):
    """Snap share per player per game -- used to tell starters from backups on the injury report."""
    try:
        df = nfl.load_snap_counts(seasons=[season])
        return _to_dicts(df), None
    except Exception as e:
        return [], str(e)


def get_depth_charts(season):
    """Team depth charts -- first-string players count as starters on Page 1's injury report."""
    try:
        df = nfl.load_depth_charts(seasons=[season])
        return _to_dicts(df), None
    except Exception as e:
        return [], str(e)


# ---------------------------------------------------------------- Page 2 (added 2026-09-19)

def get_schedules_all():
    """Every season's schedule (1999 on) -- Page 2 looks up the last time two teams met."""
    try:
        df = nfl.load_schedules(seasons=True)
        return _to_dicts(df), None
    except Exception as e:
        return [], str(e)


# ---------------------------------------------------------------- scoring by quarter (added 2026-09-29)

_PBP = {}


def _pbp(season):
    """This season's play-by-play, downloaded once per run and shared by the functions below."""
    if season not in _PBP:
        _PBP[season] = nfl.load_pbp(seasons=[season])
    return _PBP[season]


def get_team_downs(season):
    """First downs and third-down conversions per team per game, from play-by-play (nflverse's
    weekly team stats have neither the third downs nor the first downs gained by penalty): one
    row per (game_id, posteam) with defteam, week, season_type, "first_downs" (rush + pass +
    penalty), "conv" (third downs converted) and "att" (converted + failed). The defense's side
    is the same rows read by defteam."""
    try:
        import polars as pl
        n = lambda c: pl.col(c).fill_null(0)
        df = (_pbp(season)
              .filter(pl.col("posteam").is_not_null() & pl.col("defteam").is_not_null())
              .group_by(["game_id", "season_type", "week", "posteam", "defteam"])
              .agg((n("first_down_rush") + n("first_down_pass") + n("first_down_penalty")).sum().alias("first_downs"),
                   n("third_down_converted").sum().alias("conv"),
                   (n("third_down_converted") + n("third_down_failed")).sum().alias("att")))
        return _to_dicts(df), None
    except Exception as e:
        return [], str(e)


def get_quarter_scores(season):
    """Running score at the end of each quarter, from play-by-play: one row per game and quarter
    with the highest total_home_score / total_away_score reached in it (qtr 5 = overtime).
    Only the four columns the page needs are kept -- the full play-by-play is ~370 columns."""
    try:
        import polars as pl
        df = _pbp(season)
        df = (df.select(["game_id", "qtr", "total_home_score", "total_away_score"])
                .group_by(["game_id", "qtr"])
                .agg(pl.col("total_home_score").max(), pl.col("total_away_score").max()))
        return _to_dicts(df), None
    except Exception as e:
        return [], str(e)


# ---------------------------------------------------------------- game-day absences (added 2026-09-30)

_INJ_RE = None


def get_injury_events(season):
    """In-game injuries from play-by-play descriptions, in play order: "CHI-70-B.Jones was injured
    during the play." and, if he comes back, "** Injury Update: CHI-70-B.Jones has returned to the
    game." Returns (events, game_ids): events are {"game_id", "seq", "qtr", "event": "injured" |
    "returned", "team", "jersey", "name"}; game_ids is every game play-by-play covers, so a game
    with no injuries still counts as checked."""
    global _INJ_RE
    try:
        import re
        if _INJ_RE is None:
            _INJ_RE = re.compile(r"\b([A-Z]{2,3})-(\d{1,2})-([A-Za-z][A-Za-z.'\- ]*?) "
                                 r"(was injured during the play|has returned to the game)")
        df = _pbp(season).select(["game_id", "play_id", "qtr", "desc"])
        events, games = [], set()
        for r in df.sort(["game_id", "play_id"]).iter_rows(named=True):
            games.add(r["game_id"])
            for team, jersey, name, what in _INJ_RE.findall(r["desc"] or ""):
                events.append({"game_id": r["game_id"], "seq": r["play_id"], "qtr": r["qtr"],
                               "event": "injured" if what.startswith("was") else "returned",
                               "team": team, "jersey": jersey, "name": name.strip()})
        return (events, sorted(games)), None
    except Exception as e:
        return ([], []), str(e)


def get_rosters_weekly(season):
    """Each week's roster with every player's status that week -- "INA" marks a game's inactives;
    status_description_abbr is the NFL's finer code ("R01" Reserve/Injured, reserve.py).
    Trimmed to the columns the pages use."""
    try:
        cols = ["team", "week", "game_type", "status", "status_description_abbr", "jersey_number", "gsis_id",
                "full_name", "position"]
        df = nfl.load_rosters_weekly(seasons=[season])
        return _to_dicts(df.select([c for c in cols if c in df.columns])), None
    except Exception as e:
        return [], str(e)
