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


# Names (2026-10-08). LOCATION_NAMES heads a team page's top bar and its card titles, the way
# render_page2team.LOCATION_NAMES does on the NFL side: the two Los Angeles teams get an initial.
LOCATION_NAMES = {
    "ATL": "Atlanta", "BOS": "Boston", "BKN": "Brooklyn", "CHA": "Charlotte", "CHI": "Chicago",
    "CLE": "Cleveland", "DAL": "Dallas", "DEN": "Denver", "DET": "Detroit", "GSW": "Golden State",
    "HOU": "Houston", "IND": "Indiana", "LAC": "Los Angeles C", "LAL": "Los Angeles L", "MEM": "Memphis",
    "MIA": "Miami", "MIL": "Milwaukee", "MIN": "Minnesota", "NOP": "New Orleans", "NYK": "New York",
    "OKC": "Oklahoma City", "ORL": "Orlando", "PHI": "Philadelphia", "PHX": "Phoenix", "POR": "Portland",
    "SAC": "Sacramento", "SAS": "San Antonio", "TOR": "Toronto", "UTA": "Utah", "WAS": "Washington",
}
NICKNAMES = {
    "ATL": "Hawks", "BOS": "Celtics", "BKN": "Nets", "CHA": "Hornets", "CHI": "Bulls", "CLE": "Cavaliers",
    "DAL": "Mavericks", "DEN": "Nuggets", "DET": "Pistons", "GSW": "Warriors", "HOU": "Rockets", "IND": "Pacers",
    "LAC": "Clippers", "LAL": "Lakers", "MEM": "Grizzlies", "MIA": "Heat", "MIL": "Bucks", "MIN": "Timberwolves",
    "NOP": "Pelicans", "NYK": "Knicks", "OKC": "Thunder", "ORL": "Magic", "PHI": "76ers", "PHX": "Suns",
    "POR": "Trail Blazers", "SAC": "Kings", "SAS": "Spurs", "TOR": "Raptors", "UTA": "Jazz", "WAS": "Wizards",
}

# Each team's home arena, roughly (lat, lon) -- only for the team page's "miles traveled", so a few
# blocks either way don't matter. Neutral-site games (Paris, Mexico City, ...) count no miles.
HOME_COORDS = {
    "ATL": (33.757, -84.396), "BOS": (42.366, -71.062), "BKN": (40.683, -73.976), "CHA": (35.225, -80.839),
    "CHI": (41.881, -87.674), "CLE": (41.496, -81.688), "DAL": (32.790, -96.810), "DEN": (39.749, -105.008),
    "DET": (42.341, -83.055), "GSW": (37.768, -122.388), "HOU": (29.751, -95.362), "IND": (39.764, -86.155),
    "LAC": (33.945, -118.341), "LAL": (34.043, -118.267), "MEM": (35.138, -90.051), "MIA": (25.781, -80.188),
    "MIL": (43.045, -87.917), "MIN": (44.979, -93.276), "NOP": (29.949, -90.082), "NYK": (40.751, -73.993),
    "OKC": (35.463, -97.515), "ORL": (28.539, -81.384), "PHI": (39.901, -75.172), "PHX": (33.446, -112.071),
    "POR": (45.532, -122.667), "SAC": (38.580, -121.500), "SAS": (29.427, -98.437), "TOR": (43.643, -79.379),
    "UTA": (40.768, -111.901), "WAS": (38.898, -77.021),
}


def full_name(code):
    """"BOS" -> "Boston Celtics" (the code itself for a team that isn't one of the 30)."""
    if code in NICKNAMES:
        loc = {"LAC": "LA", "LAL": "Los Angeles"}.get(code, LOCATION_NAMES[code])
        return f"{loc} {NICKNAMES[code]}"
    return code or "TBD"
