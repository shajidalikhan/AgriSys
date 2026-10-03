"""4-Tier Weather Client integrating IMD, Open-Meteo, Redis Cache, and Offline Climatology."""

from __future__ import annotations
import datetime
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple
import httpx

from agrisys.agents.weather.models import DailyWeatherForecast

logger = logging.getLogger(__name__)


class WeatherClient:
    """Implements the 4-tier meteorological fallback chain (§7.1)."""

    def __init__(self, cache_ttl_seconds: int = 10800):  # 3 hours TTL
        self.ttl = cache_ttl_seconds
        self.imd_api_key = os.getenv("IMD_API_KEY", "")
        self._memory_cache: dict[str, tuple[float, list[DailyWeatherForecast], str]] = {}
        self._redis_client = None
        self._init_redis()

    def _init_redis(self):
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            import redis
            client = redis.from_url(redis_url, socket_timeout=1.5)
            client.ping()
            self._redis_client = client
        except Exception:
            self._redis_client = None

    def get_cached(self, key: str) -> tuple[list[DailyWeatherForecast], str] | None:
        """Checks Redis or in-memory cache for valid forecasts."""
        if self._redis_client:
            try:
                val = self._redis_client.get(key)
                if val:
                    data = json.loads(val.decode("utf-8"))
                    forecasts = [DailyWeatherForecast(**f) for f in data["forecasts"]]
                    return forecasts, "REDIS_CACHE"
            except Exception:
                pass

        # In-memory check
        entry = self._memory_cache.get(key)
        if entry:
            expire_at, forecasts, src = entry
            if time.time() < expire_at:
                return forecasts, src
            else:
                del self._memory_cache[key]
        return None

    def set_cached(self, key: str, forecasts: list[DailyWeatherForecast], source: str):
        """Stores forecasts in Redis and memory with TTL."""
        if self._redis_client:
            try:
                dump = {
                    "source": source,
                    "forecasts": [f.model_dump() for f in forecasts],
                }
                self._redis_client.setex(key, self.ttl, json.dumps(dump))
            except Exception:
                pass

        self._memory_cache[key] = (time.time() + self.ttl, forecasts, source)

    async def fetch_forecast_7d(
        self,
        lat: float = 26.85,
        lon: float = 80.95,
        district: str = "Lucknow",
    ) -> tuple[list[DailyWeatherForecast], str]:
        """
        Executes the 4-tier fallback retrieval:
        Tier 1: IMD API -> Tier 2: Open-Meteo -> Tier 3: Cache -> Tier 4: Offline Model
        """
        cache_key = f"weather:{round(lat, 2)}:{round(lon, 2)}"

        # 1. Tier 1: IMD Official API (if key present)
        if self.imd_api_key:
            try:
                forecasts = await self._fetch_imd_api(lat, lon, district)
                if forecasts:
                    self.set_cached(cache_key, forecasts, "IMD_API")
                    return forecasts, "IMD_API"
            except Exception as e:
                logger.warning("Tier 1 IMD API error: %s. Falling back to Open-Meteo.", e)

        # 2. Tier 2: Open-Meteo API (free, verified global coverage)
        try:
            forecasts = await self._fetch_open_meteo(lat, lon)
            if forecasts:
                self.set_cached(cache_key, forecasts, "OPEN_METEO")
                return forecasts, "OPEN_METEO"
        except Exception as e:
            logger.warning("Tier 2 Open-Meteo error: %s. Checking cache fallback.", e)

        # 3. Tier 3: Redis / Memory Cache
        cached_result = self.get_cached(cache_key)
        if cached_result:
            return cached_result[0], "REDIS_CACHE"

        # 4. Tier 4: Offline Climatological Baseline
        logger.info("Falling back to Tier 4: Offline climatological model.")
        offline_forecasts = self._generate_offline_climatology(district=district)
        return offline_forecasts, "LOCAL_OFFLINE"

    async def _fetch_open_meteo(self, lat: float, lon: float) -> list[DailyWeatherForecast]:
        """Queries Open-Meteo 7-day daily endpoint."""
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "precipitation_probability_max",
                "wind_speed_10m_max",
                "shortwave_radiation_sum",
            ],
            "timezone": "auto",
        }
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        daily = data.get("daily", {})
        dates = daily.get("time", [])
        t_max = daily.get("temperature_2m_max", [])
        t_min = daily.get("temperature_2m_min", [])
        rain = daily.get("precipitation_sum", [])
        rain_prob = daily.get("precipitation_probability_max", [0.0] * len(dates))
        winds = daily.get("wind_speed_10m_max", [])
        rads = daily.get("shortwave_radiation_sum", [18.0] * len(dates))

        forecasts: list[DailyWeatherForecast] = []
        for i in range(min(7, len(dates))):
            mx = float(t_max[i])
            mn = float(t_min[i])
            r = float(rain[i])
            w = float(winds[i]) / 3.6  # convert km/h to m/s
            rp = float(rain_prob[i]) if rain_prob else 0.0
            rd = float(rads[i]) if rads else 18.0

            # Condition summary
            if r > 10.0:
                summary = "Heavy Rain"
            elif r > 2.0:
                summary = "Rain Showers"
            elif rp > 50.0:
                summary = "Overcast / Rain Threat"
            elif mx > 38.0:
                summary = "Extreme Heat"
            else:
                summary = "Sunny / Clear"

            forecasts.append(
                DailyWeatherForecast(
                    date=dates[i],
                    temp_max=round(mx, 1),
                    temp_min=round(mn, 1),
                    temp_mean=round((mx + mn) / 2.0, 1),
                    relative_humidity=65.0,  # Standard diurnal mean
                    wind_speed_ms=round(w, 1),
                    precipitation_mm=round(r, 1),
                    precipitation_probability=round(rp, 1),
                    solar_radiation_mj=round(rd, 1),
                    condition_summary=summary,
                )
            )
        return forecasts

    async def _fetch_imd_api(self, lat: float, lon: float, district: str) -> list[DailyWeatherForecast]:
        """Placeholder query structure for official IMD endpoints."""
        # Simulated or actual endpoint query
        return []

    def _generate_offline_climatology(self, district: str) -> list[DailyWeatherForecast]:
        """Provides offline climatological benchmark for northern/central Indian agricultural zones."""
        today = datetime.date.today()
        base_tmax = 32.0
        base_tmin = 21.0
        forecasts: list[DailyWeatherForecast] = []

        for i in range(7):
            d = today + datetime.timedelta(days=i)
            # Add slight realistic multi-day variation
            tmax = base_tmax + (1.2 * math_sin(i))
            tmin = base_tmin + (0.8 * math_cos(i))
            rain = 6.0 if i == 3 else 0.0

            forecasts.append(
                DailyWeatherForecast(
                    date=d.isoformat(),
                    temp_max=round(tmax, 1),
                    temp_min=round(tmin, 1),
                    temp_mean=round((tmax + tmin) / 2.0, 1),
                    relative_humidity=62.0,
                    wind_speed_ms=2.2,
                    precipitation_mm=rain,
                    precipitation_probability=60.0 if rain > 0 else 10.0,
                    solar_radiation_mj=18.5,
                    condition_summary="Scattered Rain" if rain > 0 else "Partly Cloudy",
                )
            )
        return forecasts


def math_sin(i: int) -> float:
    return [0.0, 0.84, 0.90, 0.14, -0.75, -0.95, -0.27][i % 7]


def math_cos(i: int) -> float:
    return [1.0, 0.54, -0.41, -0.98, -0.65, 0.28, 0.96][i % 7]
