# Stage 6: Weather & Precision Irrigation Advisory Agent

## 1. Overview & Objectives
Stage 6 implements the **Weather and Irrigation Agent (§7)** in AgriSys. Meteorological factors directly dictate agricultural success: extreme frost, heatwaves, and unseasonal rainfall can destroy yields, while unscientific irrigation wastes groundwater and power.

### Key Objectives:
1. **4-Tier Meteorological Fallback Chain (§7.1)**:
   - **Tier 1 (Primary)**: India Meteorological Department (IMD) API (`api.imd.gov.in`).
   - **Tier 2 (Fallback 1)**: Open-Meteo Global Forecasting API (`api.open-meteo.com`) — free, real-time, no API key required.
   - **Tier 3 (Fallback 2)**: Redis / Memory Cache (TTL = 3 hours / 10,800 seconds).
   - **Tier 4 (Fallback 3)**: Offline Climatological Model for zero-connectivity situations.
2. **FAO-56 Penman-Monteith Evapotranspiration ($ET_0$)**:
   - Calculates daily reference crop water loss ($mm/\text{day}$) using standardized aerodynamic and radiation equations from temperature, humidity, solar radiation, and wind speed.
3. **Crop Evapotranspiration ($ET_c$) & Precision Irrigation Scheduling**:
   - Applies stage-specific crop coefficients ($K_c$) for 15+ major Indian crops to compute actual water demand ($ET_c = K_c \times ET_0$).
   - Calculates Net Irrigation Requirement ($NIR = \max(0, ET_c - P_{\text{eff}})$) and converts to run duration (hours of drip runtime at 4 mm/hr).
4. **Agricultural Extreme Weather Alerts**:
   - Automated detection of **Ground Frost** ($T_{\text{min}} < 4^\circ C$), **Severe Heatwave** ($T_{\text{max}} > 40^\circ C$), **Heavy Rainfall** ($> 35\text{ mm/day}$), and **High Wind / Lodging** ($> 12\text{ m/s}$).
5. **LangGraph StateGraph & API**:
   - Plugs `weather_agent_node` into `AgriSysState` and `create_agrisys_graph` for `"weather"` intent queries.
   - Exposes REST endpoint `/api/weather/forecast`.

---

## 2. SOLID Architecture Compliance

| Principle | Implementation in Stage 6 |
| :--- | :--- |
| **Single Responsibility (SRP)** | `WeatherClient` only fetches/caches meteorological data. `FAO56PenmanMonteithCalculator` only handles physical ETo math. `WeatherAlertEngine` only evaluates hazard thresholds. `WeatherAgent` synthesizes advisory recommendations. |
| **Open/Closed (OCP)** | New weather APIs or additional sensor endpoints can be added to `WeatherClient` without modifying the core agent coordination flow. |
| **Liskov Substitution (LSP)** | All fallback tiers return consistent `DailyWeatherForecast` schemas. |
| **Interface Segregation (ISP)** | Schemas isolate daily weather projections (`DailyWeatherForecast`), evapotranspiration analysis (`EToCalculationResult`), and hazards (`WeatherAlert`). |
| **Dependency Inversion (DIP)** | `WeatherAgent` coordinates through abstractions and delegates physical calculations to `FAO56PenmanMonteithCalculator`. |

---

## 3. Meteorological Fallback Chain & ETo Architecture

```
                     District / Coordinates Request
                                    │
                                    ▼
      ═════════════════════════════════════════════════════════
      4-Tier Meteorological Fallback Chain (§7.1)
      ═════════════════════════════════════════════════════════
      1. Primary: IMD Official API (api.imd.gov.in)
         │ (Timeout / Key pending)
         ▼
      2. Fallback 1: Open-Meteo Real-Time API (api.open-meteo.com)
         │ (Network failure)
         ▼
      3. Fallback 2: Cached Forecast (Redis TTL=3h / Memory)
         │ (Cache miss)
         ▼
      4. Fallback 3: Local Climatological Baseline
                                    │
                                    ▼
      ═════════════════════════════════════════════════════════
      FAO-56 Penman-Monteith Evapotranspiration Engine
      ═════════════════════════════════════════════════════════
      • Input: T_max, T_min, Humidity, Wind speed, Solar radiation
      • Formula:
          ET₀ = [0.408 Δ (R_n - G) + γ (900 / (T + 273)) u₂ (e_s - e_a)] /
                [Δ + γ (1 + 0.34 u₂)]
      • Crop Demand: ET_c = K_c × ET₀
      • Net Irrigation: NIR = max(0, ET_c - Effective_Rainfall)
                                    │
                 ┌──────────────────┴──────────────────┐
                 ▼                                     ▼
        Agri Weather Alerts               Precision Irrigation Plan
      • Frost Alert (T_min < 4°C)         • Immediate vs Delayed
      • Heatwave Alert (T_max > 40°C)     • Depth (mm) & Drip Hours
      • Heavy Rain (> 35 mm/day)          • Spraying Window Clearance
                 │                                     │
                 └──────────────────┬──────────────────┘
                                    ▼
                      Actionable Farmer Advisory
        "Lucknow: Light rain (14 mm) expected on Wednesday.
         Postpone Wheat irrigation for 48 hours. ETo is 3.8 mm/day."
```

---

## 4. Modules & Files Created

### 4.1 Data Models (`agrisys/agents/weather/models.py`)
- `DailyWeatherForecast`: Temperature (min, max, mean), humidity, wind speed, solar radiation, precipitation, and condition.
- `EToCalculationResult`: Reference $ET_0$, crop coefficient $K_c$, crop demand $ET_c$, effective rainfall, and net irrigation requirement.
- `WeatherAlert`: Hazard category (Frost, Heatwave, Heavy Rain, High Wind, Normal), severity, and immediate protective actions.
- `WeatherReport`: Full 7-day forecast, $ET_0$ analytics, active alerts, irrigation schedule, and advisory text.

### 4.2 FAO-56 Penman-Monteith Engine (`agrisys/agents/weather/eto_calculator.py`)
- Standard FAO-56 Penman-Monteith calculator.
- Crop coefficient ($K_c$) dictionary for 15+ major crops (Wheat, Rice, Tomato, Potato, Cotton, Sugarcane, Maize, Mustard, Banana, Pulses).
- Net irrigation requirement and drip run-time estimation.

### 4.3 4-Tier Fallback Client (`agrisys/agents/weather/client.py`)
- 4-tier fallback client (IMD $\to$ Open-Meteo $\to$ Redis Cache $\to$ Offline Baseline).

### 4.4 Hazard Alerting Engine (`agrisys/agents/weather/alerts.py`)
- Rule-based agricultural alert detector scanning 7-day forecasts for frost, heatwave, squalls, and heavy downpours.

### 4.5 Agent Coordinator & State Node (`agrisys/agents/weather/agent.py`, `node.py`)
- `WeatherAgent`: Master coordinator fetching weather, calculating $ET_0$, raising alerts, and generating bilingual (English + Hindi) advisories.
- `weather_agent_node`: LangGraph state node connected to `AgriSysState`.
