"""
Weather lookups via the National Weather Service API (api.weather.gov).
Free, official, no API key required. US stadiums only (NWS doesn't cover
outside the US -- fine for NFL, all stadiums are domestic).

Two-step flow required by NWS:
  1. GET /points/{lat},{lon}  -> gives you the specific forecast office/grid
     and a URL for the hourly forecast at that point.
  2. GET that hourly forecast URL -> list of hour-by-hour periods; we pick
     the one closest to kickoff time.

NWS only forecasts ~7 days out, so this only returns real data for games
in the near future -- for games further out, "not yet available" is the
correct/expected result, not a bug.
"""

from datetime import datetime, timezone
import requests

TIMEOUT = 15
HEADERS = {
    "User-Agent": "at-a-glance-app/0.1 (personal project, contact: n/a)",
    "Accept": "application/geo+json",
}


def get_kickoff_weather(lat, lon, kickoff_iso_utc):
    """
    Returns a dict with temperature/conditions for the closest forecasted
    hour to kickoff, or {"available": False, "reason": ...} if out of range
    or the lookup failed for any reason.
    """
    try:
        points_resp = requests.get(f"https://api.weather.gov/points/{lat},{lon}", headers=HEADERS, timeout=TIMEOUT)
        points_resp.raise_for_status()
        forecast_hourly_url = points_resp.json().get("properties", {}).get("forecastHourly")
        if not forecast_hourly_url:
            return {"available": False, "reason": "no forecastHourly url from NWS points lookup"}

        forecast_resp = requests.get(forecast_hourly_url, headers=HEADERS, timeout=TIMEOUT)
        forecast_resp.raise_for_status()
        periods = forecast_resp.json().get("properties", {}).get("periods", [])
        if not periods:
            return {"available": False, "reason": "no hourly periods returned"}

        kickoff_dt = datetime.fromisoformat(kickoff_iso_utc.replace("Z", "+00:00"))

        best = min(
            periods,
            key=lambda p: abs(datetime.fromisoformat(p["startTime"]) - kickoff_dt),
        )
        closest_gap_hours = abs(datetime.fromisoformat(best["startTime"]) - kickoff_dt).total_seconds() / 3600
        if closest_gap_hours > 6:
            # Kickoff is further out than NWS's hourly forecast window covers.
            return {"available": False, "reason": "kickoff is beyond the ~7-day NWS forecast window"}

        return {
            "available": True,
            "temperature_f": best.get("temperature"),
            "short_forecast": best.get("shortForecast"),
            "wind_speed": best.get("windSpeed"),
            "wind_direction": best.get("windDirection"),
            "precip_chance_pct": (best.get("probabilityOfPrecipitation") or {}).get("value"),
            "forecast_period_start": best.get("startTime"),
        }
    except Exception as e:
        return {"available": False, "reason": str(e)}


# ---------------------------------------------------------------- Page 1 (added 2026-09-16)
# Page 1's Game Info card shows the AVERAGE temperature over the game window
# (kickoff to +3 hours) and one icon for the most common condition in that window.

import re
from collections import Counter
from datetime import timedelta

_hourly_cache = {}  # (lat, lon) -> list of NWS hourly periods (one lookup per stadium per run)

WINDY_MPH = 18  # at or above this, wind becomes the "most prominent" condition on a clear/cloudy day


def condition_category(short_forecast):
    """NWS shortForecast text -> one of: storm, snow, rain, fog, wind, cloud, partly, sun (or None)."""
    t = (short_forecast or "").lower()
    if not t:
        return None
    if "thunder" in t:
        return "storm"
    if any(w in t for w in ("snow", "flurr", "sleet", "ice", "freezing")):
        return "snow"
    if any(w in t for w in ("rain", "shower", "drizzle")):
        return "rain"
    if any(w in t for w in ("fog", "haze", "smoke")):
        return "fog"
    if any(w in t for w in ("windy", "breezy", "blustery")):
        return "wind"
    if "partly" in t or "mostly sunny" in t or "mostly clear" in t:
        return "partly"
    if "cloud" in t or "overcast" in t:
        return "cloud"
    if "sunny" in t or "clear" in t:
        return "sun"
    return None


def _mph(wind_speed_text):
    nums = [int(n) for n in re.findall(r"\d+", str(wind_speed_text or ""))]
    return max(nums) if nums else None


def _hourly_periods(lat, lon):
    key = (round(lat, 4), round(lon, 4))
    if key not in _hourly_cache:
        points = requests.get(f"https://api.weather.gov/points/{lat},{lon}", headers=HEADERS, timeout=TIMEOUT)
        points.raise_for_status()
        url = points.json().get("properties", {}).get("forecastHourly")
        if not url:
            raise ValueError("no forecastHourly url from NWS points lookup")
        hourly = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        hourly.raise_for_status()
        _hourly_cache[key] = hourly.json().get("properties", {}).get("periods", [])
    return _hourly_cache[key]


def get_game_window_weather(lat, lon, kickoff_utc, hours=3):
    """
    kickoff_utc: timezone-aware datetime.
    Returns {"available": True, "temp_f", "condition", "wind_mph", "short_forecast"}
    or {"available": False, "reason": ...}. Never raises.
    """
    try:
        periods = _hourly_periods(lat, lon)
        start, end = kickoff_utc - timedelta(minutes=30), kickoff_utc + timedelta(hours=hours)
        window = [p for p in periods if start <= datetime.fromisoformat(p["startTime"]) < end]
        if not window:
            return {"available": False, "reason": "kickoff is outside the ~7-day NWS forecast window"}
        temps = [p.get("temperature") for p in window if isinstance(p.get("temperature"), (int, float))]
        winds = [w for w in (_mph(p.get("windSpeed")) for p in window) if w is not None]
        cats = [c for c in (condition_category(p.get("shortForecast")) for p in window) if c]
        condition = Counter(cats).most_common(1)[0][0] if cats else None
        wind = max(winds) if winds else None
        if wind is not None and wind >= WINDY_MPH and condition in (None, "sun", "partly", "cloud"):
            condition = "wind"
        return {
            "available": True,
            "temp_f": round(sum(temps) / len(temps)) if temps else None,
            "condition": condition,
            "wind_mph": wind,
            "short_forecast": window[0].get("shortForecast"),
        }
    except Exception as e:
        return {"available": False, "reason": str(e)}
