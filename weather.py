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
