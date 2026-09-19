"""
Static reference table of NFL stadiums: lat/long (for weather lookups) and
whether the stadium is a dome/indoor (in which case weather is not applicable).

Keyed by ESPN team abbreviation (matches the "abbreviation" field on team
objects returned by ESPN's scoreboard/team endpoints).

NOTE: A few teams share a stadium (e.g. NYG/NYJ at MetLife, LAR/LAC at SoFi).
Indoor/outdoor and lat/long are also available directly on ESPN's venue
object per-game (venue.indoor boolean, venue.address), so this table is a
fallback/cross-check more than the sole source of truth -- prefer the
live venue data from the scoreboard response when present, and fall back
to this table if a field is missing.

Coordinates are the stadium's approximate lat/long, sufficient for a
weather API lookup (not survey-grade precision).

"roof" (added 2026-09-19 for Page 2): "outdoor" | "dome" (fixed roof, always
indoors) | "retractable" (open or closed game by game). This table is the
source of truth for the roof TYPE -- nflverse's per-game roof column is only
used for a retractable roof's open/closed status, because it is wrong for some
venues (e.g. the MCG listed as a dome) and blank for upcoming retractable games.
"indoor" is kept for older callers: True for domes and retractables.
"""

STADIUMS = {
    "ARI": {"name": "State Farm Stadium", "city": "Glendale", "state": "AZ", "lat": 33.5276, "lon": -112.2626, "roof": "retractable", "indoor": True},
    "ATL": {"name": "Mercedes-Benz Stadium", "city": "Atlanta", "state": "GA", "lat": 33.7554, "lon": -84.4008, "roof": "retractable", "indoor": True},
    "BAL": {"name": "M&T Bank Stadium", "city": "Baltimore", "state": "MD", "lat": 39.2780, "lon": -76.6227, "roof": "outdoor", "indoor": False},
    "BUF": {"name": "Highmark Stadium", "city": "Orchard Park", "state": "NY", "lat": 42.7738, "lon": -78.7870, "roof": "outdoor", "indoor": False},
    "CAR": {"name": "Bank of America Stadium", "city": "Charlotte", "state": "NC", "lat": 35.2258, "lon": -80.8528, "roof": "outdoor", "indoor": False},
    "CHI": {"name": "Soldier Field", "city": "Chicago", "state": "IL", "lat": 41.8623, "lon": -87.6167, "roof": "outdoor", "indoor": False},
    "CIN": {"name": "Paycor Stadium", "city": "Cincinnati", "state": "OH", "lat": 39.0955, "lon": -84.5161, "roof": "outdoor", "indoor": False},
    "CLE": {"name": "Huntington Bank Field", "city": "Cleveland", "state": "OH", "lat": 41.5061, "lon": -81.6995, "roof": "outdoor", "indoor": False},
    "DAL": {"name": "AT&T Stadium", "city": "Arlington", "state": "TX", "lat": 32.7473, "lon": -97.0945, "roof": "retractable", "indoor": True},
    "DEN": {"name": "Empower Field at Mile High", "city": "Denver", "state": "CO", "lat": 39.7439, "lon": -105.0201, "roof": "outdoor", "indoor": False},
    "DET": {"name": "Ford Field", "city": "Detroit", "state": "MI", "lat": 42.3400, "lon": -83.0456, "roof": "dome", "indoor": True},
    "GB":  {"name": "Lambeau Field", "city": "Green Bay", "state": "WI", "lat": 44.5013, "lon": -88.0622, "roof": "outdoor", "indoor": False},
    "HOU": {"name": "NRG Stadium", "city": "Houston", "state": "TX", "lat": 29.6847, "lon": -95.4107, "roof": "retractable", "indoor": True},
    "IND": {"name": "Lucas Oil Stadium", "city": "Indianapolis", "state": "IN", "lat": 39.7601, "lon": -86.1639, "roof": "retractable", "indoor": True},
    "JAX": {"name": "EverBank Stadium", "city": "Jacksonville", "state": "FL", "lat": 30.3239, "lon": -81.6373, "roof": "outdoor", "indoor": False},
    "KC":  {"name": "GEHA Field at Arrowhead Stadium", "city": "Kansas City", "state": "MO", "lat": 39.0489, "lon": -94.4839, "roof": "outdoor", "indoor": False},
    "LV":  {"name": "Allegiant Stadium", "city": "Las Vegas", "state": "NV", "lat": 36.0909, "lon": -115.1833, "roof": "dome", "indoor": True},
    "LAC": {"name": "SoFi Stadium", "city": "Inglewood", "state": "CA", "lat": 33.9535, "lon": -118.3392, "roof": "dome", "indoor": True},
    "LAR": {"name": "SoFi Stadium", "city": "Inglewood", "state": "CA", "lat": 33.9535, "lon": -118.3392, "roof": "dome", "indoor": True},
    "MIA": {"name": "Hard Rock Stadium", "city": "Miami Gardens", "state": "FL", "lat": 25.9580, "lon": -80.2389, "roof": "outdoor", "indoor": False},
    "MIN": {"name": "U.S. Bank Stadium", "city": "Minneapolis", "state": "MN", "lat": 44.9736, "lon": -93.2575, "roof": "dome", "indoor": True},
    "NE":  {"name": "Gillette Stadium", "city": "Foxborough", "state": "MA", "lat": 42.0909, "lon": -71.2643, "roof": "outdoor", "indoor": False},
    "NO":  {"name": "Caesars Superdome", "city": "New Orleans", "state": "LA", "lat": 29.9511, "lon": -90.0812, "roof": "dome", "indoor": True},
    "NYG": {"name": "MetLife Stadium", "city": "East Rutherford", "state": "NJ", "lat": 40.8135, "lon": -74.0745, "roof": "outdoor", "indoor": False},
    "NYJ": {"name": "MetLife Stadium", "city": "East Rutherford", "state": "NJ", "lat": 40.8135, "lon": -74.0745, "roof": "outdoor", "indoor": False},
    "PHI": {"name": "Lincoln Financial Field", "city": "Philadelphia", "state": "PA", "lat": 39.9008, "lon": -75.1675, "roof": "outdoor", "indoor": False},
    "PIT": {"name": "Acrisure Stadium", "city": "Pittsburgh", "state": "PA", "lat": 40.4468, "lon": -80.0158, "roof": "outdoor", "indoor": False},
    "SF":  {"name": "Levi's Stadium", "city": "Santa Clara", "state": "CA", "lat": 37.4032, "lon": -121.9698, "roof": "outdoor", "indoor": False},
    "SEA": {"name": "Lumen Field", "city": "Seattle", "state": "WA", "lat": 47.5952, "lon": -122.3316, "roof": "outdoor", "indoor": False},
    "TB":  {"name": "Raymond James Stadium", "city": "Tampa", "state": "FL", "lat": 27.9759, "lon": -82.5033, "roof": "outdoor", "indoor": False},
    "TEN": {"name": "Nissan Stadium", "city": "Nashville", "state": "TN", "lat": 36.1665, "lon": -86.7713, "roof": "outdoor", "indoor": False},
    "WSH": {"name": "Northwest Stadium", "city": "Landover", "state": "MD", "lat": 38.9076, "lon": -76.8645, "roof": "outdoor", "indoor": False},
}


# ---------------------------------------------------------------- Page 2 (added 2026-09-19)

STATE_NAMES = {
    "AZ": "Arizona", "CA": "California", "CO": "Colorado", "FL": "Florida", "GA": "Georgia", "IL": "Illinois",
    "IN": "Indiana", "LA": "Louisiana", "MA": "Massachusetts", "MD": "Maryland", "MI": "Michigan", "MN": "Minnesota",
    "MO": "Missouri", "NC": "North Carolina", "NJ": "New Jersey", "NV": "Nevada", "NY": "New York", "OH": "Ohio",
    "PA": "Pennsylvania", "TN": "Tennessee", "TX": "Texas", "WA": "Washington", "WI": "Wisconsin",
}

# Neutral-site venues (international series, etc.), keyed by nflverse's stadium_id.
# "region" is what Page 2 prints after the city. Roof types checked against each venue,
# NOT copied from nflverse (which lists the MCG, Stade de France and Allianz Arena as domes).
NEUTRAL_VENUES = {
    "LON00": {"name": "Wembley Stadium", "city": "London", "region": "England", "lat": 51.5560, "lon": -0.2796, "roof": "outdoor"},
    "LON02": {"name": "Tottenham Hotspur Stadium", "city": "London", "region": "England", "lat": 51.6043, "lon": -0.0664, "roof": "outdoor"},
    "MUN01": {"name": "Allianz Arena", "city": "Munich", "region": "Germany", "lat": 48.2188, "lon": 11.6247, "roof": "outdoor"},
    "FRA00": {"name": "Deutsche Bank Park", "city": "Frankfurt", "region": "Germany", "lat": 50.0686, "lon": 8.6455, "roof": "retractable"},
    "BER00": {"name": "Olympiastadion", "city": "Berlin", "region": "Germany", "lat": 52.5147, "lon": 13.2395, "roof": "outdoor"},
    "MAD01": {"name": "Santiago Bernabéu", "city": "Madrid", "region": "Spain", "lat": 40.4531, "lon": -3.6883, "roof": "retractable"},
    "PAR00": {"name": "Stade de France", "city": "Saint-Denis", "region": "France", "lat": 48.9245, "lon": 2.3602, "roof": "outdoor"},
    "DUB00": {"name": "Croke Park", "city": "Dublin", "region": "Ireland", "lat": 53.3607, "lon": -6.2512, "roof": "outdoor"},
    "MEX00": {"name": "Estadio Banorte", "city": "Mexico City", "region": "Mexico", "lat": 19.3029, "lon": -99.1505, "roof": "outdoor"},
    "SAO00": {"name": "Neo Química Arena", "city": "São Paulo", "region": "Brazil", "lat": -23.5453, "lon": -46.4742, "roof": "outdoor"},
    "RIO00": {"name": "Maracanã", "city": "Rio de Janeiro", "region": "Brazil", "lat": -22.9122, "lon": -43.2302, "roof": "outdoor"},
    "MEL00": {"name": "Melbourne Cricket Ground", "city": "Melbourne", "region": "Australia", "lat": -37.8200, "lon": 144.9834, "roof": "outdoor"},
}
