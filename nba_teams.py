"""
The 30 NBA teams, keyed by ESPN team id (2026-10-08).

Every NBA file nba_client.py reads (sportsdataverse's ESPN-sourced releases and ESPN's
own scoreboard) identifies teams by ESPN's numeric id, so that's the key here. ESPN's
abbreviations differ from the ones the NBA itself uses for six teams (GS, NY, NO, SA,
UTAH, WSH); the site shows the NBA's (GSW, NYK, NOP, SAS, UTA, WAS), listed below as
"abbr" with ESPN's kept as "espn_abbr".

Conferences and divisions are the 2026-27 alignment, checked against sportsdataverse's
nba_groups release (nba_team_group_seasons_2027), which agrees with stats.nba.com.
Kept by hand like divisions.py on the NFL side: realignment is rare and announced
months ahead.
"""

# espn_id: (abbr, espn_abbr, conference, division)
_TEAMS = {
    1: ("ATL", "ATL", "East", "Southeast"),
    2: ("BOS", "BOS", "East", "Atlantic"),
    3: ("NOP", "NO", "West", "Southwest"),
    4: ("CHI", "CHI", "East", "Central"),
    5: ("CLE", "CLE", "East", "Central"),
    6: ("DAL", "DAL", "West", "Southwest"),
    7: ("DEN", "DEN", "West", "Northwest"),
    8: ("DET", "DET", "East", "Central"),
    9: ("GSW", "GS", "West", "Pacific"),
    10: ("HOU", "HOU", "West", "Southwest"),
    11: ("IND", "IND", "East", "Central"),
    12: ("LAC", "LAC", "West", "Pacific"),
    13: ("LAL", "LAL", "West", "Pacific"),
    14: ("MIA", "MIA", "East", "Southeast"),
    15: ("MIL", "MIL", "East", "Central"),
    16: ("MIN", "MIN", "West", "Northwest"),
    17: ("BKN", "BKN", "East", "Atlantic"),
    18: ("NYK", "NY", "East", "Atlantic"),
    19: ("ORL", "ORL", "East", "Southeast"),
    20: ("PHI", "PHI", "East", "Atlantic"),
    21: ("PHX", "PHX", "West", "Pacific"),
    22: ("POR", "POR", "West", "Northwest"),
    23: ("SAC", "SAC", "West", "Pacific"),
    24: ("SAS", "SA", "West", "Southwest"),
    25: ("OKC", "OKC", "West", "Northwest"),
    26: ("UTA", "UTAH", "West", "Northwest"),
    27: ("WAS", "WSH", "East", "Southeast"),
    28: ("TOR", "TOR", "East", "Atlantic"),
    29: ("MEM", "MEM", "West", "Southwest"),
    30: ("CHA", "CHA", "East", "Southeast"),
}

TEAMS = {
    tid: {"team_id": tid, "abbr": a, "espn_abbr": e, "conference": c, "division": d}
    for tid, (a, e, c, d) in _TEAMS.items()
}
_BY_ABBR = {t["abbr"]: t for t in TEAMS.values()}
_BY_ABBR.update({t["espn_abbr"]: t for t in TEAMS.values()})

CONFERENCES = ("East", "West")
DIVISIONS = {
    "East": ("Atlantic", "Central", "Southeast"),
    "West": ("Northwest", "Pacific", "Southwest"),
}


def team(team_id):
    """ESPN team id (int or numeric string) -> team dict, or None (All-Star teams, bad ids)."""
    try:
        return TEAMS.get(int(team_id))
    except (TypeError, ValueError):
        return None


def abbr(team_id):
    """ESPN team id -> the NBA's abbreviation ("GSW"), or None if it isn't one of the 30."""
    t = team(team_id)
    return t["abbr"] if t else None


def by_abbr(code):
    """Either abbreviation, the NBA's or ESPN's ("GSW" or "GS") -> team dict, or None."""
    return _BY_ABBR.get((code or "").upper())
