"""
sportsdataverse-data files for the NFL pages (2026-10-10) -- the NFL counterpart of the part of
nba_client.py that reads them. The NFL pages' own data comes from nflverse (nflverse_client.py);
this adds what nflverse doesn't publish.

  nfl_defense_vs_position   what each defense allows to each kind of player -- quarterbacks,
                            running backs, wide receivers, tight ends -- season to date, one small
                            file a season (defense_vs_position_<season>.parquet), refreshed weekly.
                            The Matchup card (matchup.py) sets it against the other team's offense.

Same pattern as the other clients: every get_* function returns (value, error) and never raises, so
a missing file just leaves the card out. Before a season's first games the file doesn't exist yet,
and that comes back as an error saying so.
"""

import io

import requests

RELEASES = "https://github.com/sportsdataverse/sportsdataverse-data/releases/download"
TIMEOUT = 60

# the file's team abbreviations where they differ from nflverse's (the site's)
TEAM_FIX = {"LA": "LAR"}


def _parquet(tag, name):
    import polars as pl
    r = requests.get(f"{RELEASES}/{tag}/{name}", timeout=TIMEOUT)
    if r.status_code == 404:
        raise FileNotFoundError(f"{tag}/{name} isn't published yet")
    r.raise_for_status()
    return pl.read_parquet(io.BytesIO(r.content))


def get_defense_vs_position(season):
    """One dict per team and position group ("QB", "RB", "WR", "TE"): team (the site's abbreviation),
    position_group, games, and what the defense allowed -- sack_rate_allowed (sacks a dropback, vs
    QBs), rush_yards_per_carry_allowed (vs RBs), yards_per_target_allowed (vs WRs and TEs)."""
    try:
        df = _parquet("nfl_defense_vs_position", f"defense_vs_position_{season}.parquet")
        keep = ("position_group", "games", "sack_rate_allowed", "rush_yards_per_carry_allowed", "yards_per_target_allowed")
        rows = []
        for r in df.iter_rows(named=True):
            team = TEAM_FIX.get(r.get("pos_team"), r.get("pos_team"))
            if team:
                rows.append(dict({k: r.get(k) for k in keep}, team=team))
        return rows, None
    except Exception as e:
        return [], str(e)
