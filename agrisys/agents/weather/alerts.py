"""Agricultural Meteorological Hazard and Extreme Weather Alert Engine."""

from __future__ import annotations
from typing import List
from agrisys.agents.weather.models import DailyWeatherForecast, WeatherAlert


class WeatherAlertEngine:
    """Scans multi-day meteorological forecasts to raise actionable agricultural weather hazard alerts."""

    @staticmethod
    def detect_alerts(forecasts: list[DailyWeatherForecast]) -> list[WeatherAlert]:
        alerts: list[WeatherAlert] = []

        # Find extreme parameters across the forecast window
        min_temp = min((f.temp_min for f in forecasts), default=20.0)
        max_temp = max((f.temp_max for f in forecasts), default=30.0)
        max_rain = max((f.precipitation_mm for f in forecasts), default=0.0)
        max_wind = max((f.wind_speed_ms for f in forecasts), default=2.0)

        # 1. Ground Frost Alert
        if min_temp <= 4.0:
            severity = "WARNING" if min_temp <= 2.0 else "ADVISORY"
            alerts.append(
                WeatherAlert(
                    alert_type="FROST",
                    severity=severity,
                    headline=f"Frost Risk Warning: Night temperature dropping to {min_temp:.1f}°C",
                    description=f"Minimum temperatures are forecast to dip to {min_temp:.1f}°C, creating high probability of radiative ground frost on young foliage and blossoms.",
                    protective_action="Initiate light evening irrigation to maintain soil latent heat. Cover nurseries/vegetable beds with straw mulch or plastic sheets. Create controlled evening smoke screens at orchard borders.",
                )
            )

        # 2. Severe Heatwave Alert
        if max_temp >= 40.0:
            severity = "WARNING" if max_temp >= 43.0 else "ADVISORY"
            alerts.append(
                WeatherAlert(
                    alert_type="HEATWAVE",
                    severity=severity,
                    headline=f"Heatwave Alert: Maximum temperatures reaching {max_temp:.1f}°C",
                    description=f"Daytime heat indices exceed {max_temp:.1f}°C, inducing rapid stomatal closure, pollen sterility, and high evapotranspiration stress.",
                    protective_action="Schedule frequent light drip irrigation cycles during early dawn or late evening. Apply organic straw mulch to keep soil root zones cool. Postpone foliar chemical sprays to prevent leaf scorch.",
                )
            )

        # 3. Heavy Rainfall / Waterlogging Alert
        if max_rain >= 35.0:
            severity = "WARNING" if max_rain >= 65.0 else "ADVISORY"
            alerts.append(
                WeatherAlert(
                    alert_type="HEAVY_RAINFALL",
                    severity=severity,
                    headline=f"Heavy Downpour Alert: {max_rain:.1f} mm single-day rainfall anticipated",
                    description=f"Significant precipitation of {max_rain:.1f} mm is forecast, risking field waterlogging, nutrient leaching, and root asphyxiation.",
                    protective_action="Open field drainage furrows immediately to evacuate standing water. Suspend all nitrogen fertilizer top-dressing and pesticide spraying until weather clears.",
                )
            )

        # 4. High Wind / Crop Lodging Alert
        if max_wind >= 12.0:
            severity = "WARNING" if max_wind >= 16.0 else "WATCH"
            alerts.append(
                WeatherAlert(
                    alert_type="HIGH_WIND",
                    severity=severity,
                    headline=f"High Wind Advisory: Wind gusts up to {max_wind:.1f} m/s ({max_wind*3.6:.0f} km/h)",
                    description="Strong gusting winds pose significant risk of mechanical crop lodging in tall crops (maize, sugarcane, banana).",
                    protective_action="Provide bamboo propping or earthing up for banana and tall crops. Check and securely fasten polyhouse and shade-net ropes.",
                )
            )

        if not alerts:
            alerts.append(
                WeatherAlert(
                    alert_type="NONE",
                    severity="NORMAL",
                    headline="Favorable Weather Conditions",
                    description="No extreme meteorological hazards or abrupt temperature swings detected for the next 7 days.",
                    protective_action="Proceed with routine agronomic field operations, standard irrigation intervals, and scheduled intercultural practices.",
                )
            )

        return alerts
