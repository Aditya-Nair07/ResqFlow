"""Provider-neutral weather sensing with deterministic fixture fallback."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "data" / "chennai" / "weather_fixture.json"


def _fixture_weather(area: str = "Chennai") -> dict[str, Any]:
    if FIXTURE.exists():
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        data["fetchedAt"] = datetime.now(timezone.utc).isoformat()
        data["source"] = "PUBLIC_WEATHER_API"
        data["provider"] = "fixture"
        data["fresh"] = True
        data["area"] = area
        return data
    return {
        "area": area,
        "provider": "fixture",
        "source": "PUBLIC_WEATHER_API",
        "rainfallMmHour": 12.0,
        "forecastRainMmNext3h": 28.0,
        "fetchedAt": datetime.now(timezone.utc).isoformat(),
        "fresh": True,
        "note": "Deterministic offline rainfall fixture",
    }


def fetch_open_meteo(lat: float = 13.0827, lon: float = 80.2707, area: str = "Chennai") -> dict[str, Any]:
    """Fetch current precipitation. Falls back to fixture on any failure."""
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}&current=precipitation,rain"
        "&hourly=precipitation&forecast_days=1&timezone=Asia%2FKolkata"
    )
    try:
        with urlopen(url, timeout=4) as resp:  # noqa: S310 - public weather API
            payload = json.loads(resp.read().decode("utf-8"))
        current = payload.get("current", {})
        hourly = payload.get("hourly", {}).get("precipitation", [])[:3]
        rain = float(current.get("precipitation") or current.get("rain") or 0.0)
        forecast = float(sum(hourly)) if hourly else rain * 3
        return {
            "area": area,
            "provider": "open-meteo",
            "source": "PUBLIC_WEATHER_API",
            "lat": lat,
            "lon": lon,
            "rainfallMmHour": round(rain, 2),
            "forecastRainMmNext3h": round(forecast, 2),
            "fetchedAt": datetime.now(timezone.utc).isoformat(),
            "fresh": True,
            "rawCurrent": current,
        }
    except (URLError, TimeoutError, ValueError, KeyError, OSError) as exc:
        out = _fixture_weather(area)
        out["fallbackReason"] = str(exc)
        out["fresh"] = False
        return out


def weather_to_rainfall_nudge(weather: dict[str, Any]) -> float:
    """Map public rainfall context to a small deterministic simulator nudge."""
    mm = float(weather.get("rainfallMmHour") or 0.0)
    if mm >= 20:
        return 0.25
    if mm >= 10:
        return 0.12
    if mm >= 3:
        return 0.05
    return 0.0
