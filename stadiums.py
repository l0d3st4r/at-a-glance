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
"""

STADIUMS = {
    "ARI": {"name": "State Farm Stadium", "city": "Glendale", "state": "AZ", "lat": 33.5276, "lon": -112.2626, "indoor": True},
    "ATL": {"name": "Mercedes-Benz Stadium", "city": "Atlanta", "state": "GA", "lat": 33.7554, "lon": -84.4008, "indoor": True},
    "BAL": {"name": "M&T Bank Stadium", "city": "Baltimore", "state": "MD", "lat": 39.2780, "lon": -76.6227, "indoor": False},
    "BUF": {"name": "Highmark Stadium", "city": "Orchard Park", "state": "NY", "lat": 42.7738, "lon": -78.7870, "indoor": False},
    "CAR": {"name": "Bank of America Stadium", "city": "Charlotte", "state": "NC", "lat": 35.2258, "lon": -80.8528, "indoor": False},
    "CHI": {"name": "Soldier Field", "city": "Chicago", "state": "IL", "lat": 41.8623, "lon": -87.6167, "indoor": False},
    "CIN": {"name": "Paycor Stadium", "city": "Cincinnati", "state": "OH", "lat": 39.0955, "lon": -84.5161, "indoor": False},
    "CLE": {"name": "Huntington Bank Field", "city": "Cleveland", "state": "OH", "lat": 41.5061, "lon": -81.6995, "indoor": False},
    "DAL": {"name": "AT&T Stadium", "city": "Arlington", "state": "TX", "lat": 32.7473, "lon": -97.0945, "indoor": True},
    "DEN": {"name": "Empower Field at Mile High", "city": "Denver", "state": "CO", "lat": 39.7439, "lon": -105.0201, "indoor": False},
    "DET": {"name": "Ford Field", "city": "Detroit", "state": "MI", "lat": 42.3400, "lon": -83.0456, "indoor": True},
    "GB":  {"name": "Lambeau Field", "city": "Green Bay", "state": "WI", "lat": 44.5013, "lon": -88.0622, "indoor": False},
    "HOU": {"name": "NRG Stadium", "city": "Houston", "state": "TX", "lat": 29.6847, "lon": -95.4107, "indoor": True},
    "IND": {"name": "Lucas Oil Stadium", "city": "Indianapolis", "state": "IN", "lat": 39.7601, "lon": -86.1639, "indoor": True},
    "JAX": {"name": "EverBank Stadium", "city": "Jacksonville", "state": "FL", "lat": 30.3239, "lon": -81.6373, "indoor": False},
    "KC":  {"name": "GEHA Field at Arrowhead Stadium", "city": "Kansas City", "state": "MO", "lat": 39.0489, "lon": -94.4839, "indoor": False},
    "LV":  {"name": "Allegiant Stadium", "city": "Las Vegas", "state": "NV", "lat": 36.0909, "lon": -115.1833, "indoor": True},
    "LAC": {"name": "SoFi Stadium", "city": "Inglewood", "state": "CA", "lat": 33.9535, "lon": -118.3392, "indoor": True},
    "LAR": {"name": "SoFi Stadium", "city": "Inglewood", "state": "CA", "lat": 33.9535, "lon": -118.3392, "indoor": True},
    "MIA": {"name": "Hard Rock Stadium", "city": "Miami Gardens", "state": "FL", "lat": 25.9580, "lon": -80.2389, "indoor": False},
    "MIN": {"name": "U.S. Bank Stadium", "city": "Minneapolis", "state": "MN", "lat": 44.9736, "lon": -93.2575, "indoor": True},
    "NE":  {"name": "Gillette Stadium", "city": "Foxborough", "state": "MA", "lat": 42.0909, "lon": -71.2643, "indoor": False},
    "NO":  {"name": "Caesars Superdome", "city": "New Orleans", "state": "LA", "lat": 29.9511, "lon": -90.0812, "indoor": True},
    "NYG": {"name": "MetLife Stadium", "city": "East Rutherford", "state": "NJ", "lat": 40.8135, "lon": -74.0745, "indoor": False},
    "NYJ": {"name": "MetLife Stadium", "city": "East Rutherford", "state": "NJ", "lat": 40.8135, "lon": -74.0745, "indoor": False},
    "PHI": {"name": "Lincoln Financial Field", "city": "Philadelphia", "state": "PA", "lat": 39.9008, "lon": -75.1675, "indoor": False},
    "PIT": {"name": "Acrisure Stadium", "city": "Pittsburgh", "state": "PA", "lat": 40.4468, "lon": -80.0158, "indoor": False},
    "SF":  {"name": "Levi's Stadium", "city": "Santa Clara", "state": "CA", "lat": 37.4032, "lon": -121.9698, "indoor": False},
    "SEA": {"name": "Lumen Field", "city": "Seattle", "state": "WA", "lat": 47.5952, "lon": -122.3316, "indoor": False},
    "TB":  {"name": "Raymond James Stadium", "city": "Tampa", "state": "FL", "lat": 27.9759, "lon": -82.5033, "indoor": False},
    "TEN": {"name": "Nissan Stadium", "city": "Nashville", "state": "TN", "lat": 36.1665, "lon": -86.7713, "indoor": False},
    "WSH": {"name": "Northwest Stadium", "city": "Landover", "state": "MD", "lat": 38.9076, "lon": -76.8645, "indoor": False},
}
