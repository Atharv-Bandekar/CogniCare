"""
Weather integration using the free Open-Meteo API.
Includes a simple in-memory cache to prevent redundant external API calls.
"""
import requests
import time
import logging

logger = logging.getLogger(__name__)

# Simple in-memory cache: {(lat, lon): {"summary": str, "expires_at": float}}
_weather_cache = {}
CACHE_TTL_SECONDS = 3600  # 1 hour

def get_weather_summary(lat: float, lon: float) -> str:
    """
    Fetches weather data for a given location and classifies it into a safe category
    for the AI Coordinator to understand.
    Returns: "clear" | "heavy_rain" | "extreme_heat" | "normal"
    """
    cache_key = (lat, lon)
    current_time = time.time()

    # 1. Check cache
    if cache_key in _weather_cache:
        cached_data = _weather_cache[cache_key]
        if current_time < cached_data["expires_at"]:
            return cached_data["summary"]

    # 2. Fetch from API
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        current_weather = data.get("current_weather", {})
        temp = current_weather.get("temperature", 20)
        code = current_weather.get("weathercode", 0)

        # 3. Classify weather based on WMO Weather interpretation codes
        summary = "normal"
        if temp >= 35:
            summary = "extreme_heat"
        elif code in [63, 65, 66, 67, 81, 82, 95, 96, 99]:  # Heavy rain/thunderstorm codes
            summary = "heavy_rain"
        elif code in [0, 1]:  # Clear skies
            summary = "clear"

        # 4. Save to cache
        _weather_cache[cache_key] = {
            "summary": summary,
            "expires_at": current_time + CACHE_TTL_SECONDS
        }
        
        return summary

    except Exception as e:
        logger.error(f"Weather API failed: {e}")
        return "normal"  # Safe default fallback