"""
Static reference: team abbreviation -> conference/division.
This almost never changes (last realignment was 2002), so hardcoding it
is safer than depending on a library function that may or may not exist
under the name we guess.

Keyed using nflverse's standard team abbreviations. A couple of
abbreviations differ between data sources (e.g. Washington is WAS here,
some sources use WSH; the Rams/Chargers are LA-prefixed everywhere in
nflverse). ABBR_ALIASES below maps common variants we might see elsewhere
(like from stadiums.py, which was originally built against ESPN's
abbreviations) onto the keys used here.
"""

DIVISIONS = {
    "BUF": "AFC East", "MIA": "AFC East", "NE": "AFC East", "NYJ": "AFC East",
    "BAL": "AFC North", "CIN": "AFC North", "CLE": "AFC North", "PIT": "AFC North",
    "HOU": "AFC South", "IND": "AFC South", "JAX": "AFC South", "TEN": "AFC South",
    "DEN": "AFC West", "KC": "AFC West", "LV": "AFC West", "LAC": "AFC West",
    "DAL": "NFC East", "NYG": "NFC East", "PHI": "NFC East", "WAS": "NFC East",
    "CHI": "NFC North", "DET": "NFC North", "GB": "NFC North", "MIN": "NFC North",
    "ATL": "NFC South", "CAR": "NFC South", "NO": "NFC South", "TB": "NFC South",
    "ARI": "NFC West", "LAR": "NFC West", "SF": "NFC West", "SEA": "NFC West",
}

# Normalize a possibly-different abbreviation spelling to the keys used above.
ABBR_ALIASES = {
    "WSH": "WAS",
    "LA": "LAR",
    "OAK": "LV",   # historical
    "SD": "LAC",   # historical
    "STL": "LAR",  # historical
}


def normalize_abbr(abbr):
    return ABBR_ALIASES.get(abbr, abbr)


def get_division(abbr):
    return DIVISIONS.get(normalize_abbr(abbr))
