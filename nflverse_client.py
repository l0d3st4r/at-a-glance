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
