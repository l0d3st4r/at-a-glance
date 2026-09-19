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


# ---------------------------------------------------------------- Page 2 (added 2026-09-19)
# The Game Info deep dive shows the full picture over the game window (kickoff - 30 min
# to kickoff + 3 h): actual temp, feels-like, wind range + direction, chance and amount of
# precipitation, and humidity.
#
#   upcoming US games inside NWS's ~7-day window -> NWS hourly forecast + gridpoint data
#                                                   (apparentTemperature, quantitativePrecipitation)
#   finished games, and games outside the US     -> Open-Meteo (free, no key): the historical
#                                                   archive for games more than ~5 days old,
#                                                   the forecast endpoint (with past days) otherwise
#
# Every function returns {"available": False, "reason": ...} instead of raising.

import math

COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
OM_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
OM_FORECAST = "https://api.open-meteo.com/v1/forecast"
OM_FIELDS = "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m,weather_code"
OM_ARCHIVE_LAG_DAYS = 5   # the archive trails real time by a few days; newer games use the forecast endpoint

_grid_cache = {}   # (lat, lon) -> NWS gridpoint "properties"
_om_cache = {}     # (lat, lon, kind) -> {"YYYY-MM-DDTHH:00": row}


def _window(kickoff_utc, hours=3):
    return kickoff_utc - timedelta(minutes=30), kickoff_utc + timedelta(hours=hours)


def compass(degrees):
    if degrees is None:
        return None
    return COMPASS[int((float(degrees) % 360) / 22.5 + 0.5) % 16]


def _mean_direction(degrees):
    """Circular mean, so 350° and 10° average to N rather than S."""
    ds = [d for d in degrees if d is not None]
    if not ds:
        return None
    x = sum(math.cos(math.radians(d)) for d in ds)
    y = sum(math.sin(math.radians(d)) for d in ds)
    return math.degrees(math.atan2(y, x)) % 360


def _wmo_category(code):
    """Open-Meteo WMO weather code -> the same categories condition_category() returns."""
    try:
        c = int(code)
    except (TypeError, ValueError):
        return None
    if c == 0:
        return "sun"
    if c in (1, 2):
        return "partly"
    if c == 3:
        return "cloud"
    if c in (45, 48):
        return "fog"
    if c in (71, 73, 75, 77, 85, 86):
        return "snow"
    if c >= 95:
        return "storm"
    if 51 <= c <= 67 or 80 <= c <= 82:
        return "rain"
    return None


def _condition(cats, wind_max):
    cats = [c for c in cats if c]
    condition = Counter(cats).most_common(1)[0][0] if cats else None
    if wind_max is not None and wind_max >= WINDY_MPH and condition in (None, "sun", "partly", "cloud"):
        condition = "wind"
    return condition


def _avg(vals):
    vals = [v for v in vals if isinstance(v, (int, float))]
    return sum(vals) / len(vals) if vals else None


def _round(v):
    return None if v is None else int(round(v))


def _iso_duration_hours(text):
    """'PT1H' / 'PT6H' / 'P1D' / 'P1DT6H' -> hours."""
    m = re.match(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?)?$", text or "")
    if not m:
        return 1.0
    d, h, mi = (int(x) if x else 0 for x in m.groups())
    return d * 24 + h + mi / 60 or 1.0


def _grid_series(prop, start, end):
    """NWS gridpoint series -> [(value, fraction of that interval inside start..end)]."""
    out = []
    for v in (prop or {}).get("values", []):
        try:
            t0_text, dur = v["validTime"].split("/")
            t0 = datetime.fromisoformat(t0_text)
            t1 = t0 + timedelta(hours=_iso_duration_hours(dur))
        except (KeyError, ValueError):
            continue
        overlap = (min(t1, end) - max(t0, start)).total_seconds()
        if overlap > 0 and v.get("value") is not None:
            out.append((v["value"], overlap / (t1 - t0).total_seconds()))
    return out


def _grid(lat, lon):
    key = (round(lat, 4), round(lon, 4))
    if key not in _grid_cache:
        points = requests.get(f"https://api.weather.gov/points/{lat},{lon}", headers=HEADERS, timeout=TIMEOUT)
        points.raise_for_status()
        url = points.json().get("properties", {}).get("forecastGridData")
        if not url:
            raise ValueError("no forecastGridData url from NWS points lookup")
        grid = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        grid.raise_for_status()
        _grid_cache[key] = grid.json().get("properties", {})
    return _grid_cache[key]


def feels_like_f(temp_f, rh, wind_mph):
    """NWS apparent temperature: wind chill at or below 50°F with wind over 3 mph, heat index at 80°F and up."""
    if temp_f is None:
        return None
    if temp_f <= 50 and wind_mph and wind_mph > 3:
        v = wind_mph ** 0.16
        return 35.74 + 0.6215 * temp_f - 35.75 * v + 0.4275 * temp_f * v
    if temp_f >= 80 and rh is not None:
        t, r = temp_f, rh
        return (-42.379 + 2.04901523 * t + 10.14333127 * r - 0.22475541 * t * r - 0.00683783 * t * t
                - 0.05481717 * r * r + 0.00122874 * t * t * r + 0.00085282 * t * r * r - 0.00000199 * t * t * r * r)
    return temp_f


def get_game_window_detail_nws(lat, lon, kickoff_utc, hours=3):
    """Upcoming US game inside the NWS forecast window -> full Page 2 weather dict."""
    try:
        start, end = _window(kickoff_utc, hours)
        window = [p for p in _hourly_periods(lat, lon) if start <= datetime.fromisoformat(p["startTime"]) < end]
        if not window:
            return {"available": False, "reason": "kickoff is outside the ~7-day NWS forecast window"}
        temps = [p.get("temperature") for p in window]
        rhs = [(p.get("relativeHumidity") or {}).get("value") for p in window]
        pops = [(p.get("probabilityOfPrecipitation") or {}).get("value") for p in window]
        winds = [[int(n) for n in re.findall(r"\d+", str(p.get("windSpeed") or ""))] for p in window]
        lows = [min(w) for w in winds if w]
        highs = [max(w) for w in winds if w]
        dirs = [p.get("windDirection") for p in window if p.get("windDirection")]
        out = {
            "available": True, "source": "nws",
            "temp_f": _round(_avg(temps)),
            "humidity_pct": _round(_avg(rhs)),
            "precip_pct": _round(max([p for p in pops if p is not None], default=None) if any(p is not None for p in pops) else None),
            "wind_min_mph": min(lows) if lows else None,
            "wind_max_mph": max(highs) if highs else None,
            "wind_dir": Counter(dirs).most_common(1)[0][0] if dirs else None,
            "condition": _condition([condition_category(p.get("shortForecast")) for p in window], max(highs) if highs else None),
            "feels_f": None, "precip_in": None,
        }
        try:  # the gridpoint data adds apparent temperature and precipitation amounts
            g = _grid(lat, lon)
            app = _grid_series(g.get("apparentTemperature"), start, end)
            if app:
                c = sum(v * f for v, f in app) / sum(f for _v, f in app)
                out["feels_f"] = _round(c * 9 / 5 + 32)
            qpf = _grid_series(g.get("quantitativePrecipitation"), start, end)
            if qpf:
                out["precip_in"] = round(sum(v * f for v, f in qpf) / 25.4, 2)
        except Exception as e:
            out["grid_error"] = str(e)
        if out["feels_f"] is None:
            out["feels_f"] = _round(feels_like_f(out["temp_f"], out["humidity_pct"], _avg(highs)))
        return out
    except Exception as e:
        return {"available": False, "reason": str(e)}


def _om_fetch(lat, lon, kind, start_date=None, end_date=None):
    """One Open-Meteo request for a location -> {hour: row}; merged into the cache."""
    params = {"latitude": lat, "longitude": lon, "hourly": OM_FIELDS, "timezone": "GMT",
              "temperature_unit": "fahrenheit", "wind_speed_unit": "mph", "precipitation_unit": "inch"}
    if kind == "archive":
        url = OM_ARCHIVE
        params.update(start_date=start_date, end_date=end_date)
    else:
        url = OM_FORECAST
        params.update(past_days=10, forecast_days=16)
        params["hourly"] += ",precipitation_probability"
    r = requests.get(url, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    h = r.json().get("hourly") or {}
    times = h.get("time") or []
    rows = {}
    for i, t in enumerate(times):
        rows[t[:13]] = {k: (h.get(k) or [None] * len(times))[i] for k in h if k != "time"}
    key = (round(lat, 4), round(lon, 4), kind)
    _om_cache.setdefault(key, {}).update(rows)
    return rows


def prefetch_open_meteo(lat, lon, kickoffs, now_utc):
    """
    Load every hour Page 2 will need at one location in at most two requests (instead of one
    per game): the archive for games older than the archive lag, the forecast endpoint (which
    also covers the last 10 days) for the rest. Returns a list of error strings.
    """
    errors = []
    old = [k for k in kickoffs if k < now_utc - timedelta(days=OM_ARCHIVE_LAG_DAYS)]
    new = [k for k in kickoffs if k not in old]
    if old:
        try:
            _om_fetch(lat, lon, "archive", min(old).strftime("%Y-%m-%d"), (max(old) + timedelta(days=1)).strftime("%Y-%m-%d"))
        except Exception as e:
            errors.append(f"open-meteo archive {lat},{lon}: {e}")
    if new:
        try:
            _om_fetch(lat, lon, "forecast")
        except Exception as e:
            errors.append(f"open-meteo forecast {lat},{lon}: {e}")
    return errors


def get_game_window_detail_om(lat, lon, kickoff_utc, hours=3):
    """Finished game or non-US venue -> full Page 2 weather dict from Open-Meteo (cached by prefetch)."""
    try:
        start, end = _window(kickoff_utc, hours)
        base = (round(lat, 4), round(lon, 4))
        rows = []
        t = start.replace(minute=0, second=0, microsecond=0)
        while t < end:
            k = t.strftime("%Y-%m-%dT%H")
            row = _om_cache.get(base + ("archive",), {}).get(k) or _om_cache.get(base + ("forecast",), {}).get(k)
            if row and row.get("temperature_2m") is not None:
                rows.append(row)
            t += timedelta(hours=1)
        if not rows:
            return {"available": False, "reason": "no Open-Meteo data for the game window"}
        winds = [r.get("wind_speed_10m") for r in rows if r.get("wind_speed_10m") is not None]
        pops = [r.get("precipitation_probability") for r in rows if r.get("precipitation_probability") is not None]
        precip = [r.get("precipitation") for r in rows if r.get("precipitation") is not None]
        return {
            "available": True, "source": "open-meteo",
            "temp_f": _round(_avg([r.get("temperature_2m") for r in rows])),
            "feels_f": _round(_avg([r.get("apparent_temperature") for r in rows])),
            "humidity_pct": _round(_avg([r.get("relative_humidity_2m") for r in rows])),
            "precip_pct": _round(max(pops)) if pops else None,
            "precip_in": round(sum(precip), 2) if precip else None,
            "wind_min_mph": _round(min(winds)) if winds else None,
            "wind_max_mph": _round(max(winds)) if winds else None,
            "wind_dir": compass(_mean_direction([r.get("wind_direction_10m") for r in rows])),
            "condition": _condition([_wmo_category(r.get("weather_code")) for r in rows], max(winds) if winds else None),
        }
    except Exception as e:
        return {"available": False, "reason": str(e)}
