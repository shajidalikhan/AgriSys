# Stage 5: Market Price Intelligence Agent & Mandi Analytics

## 1. Overview & Objectives
Stage 5 implements the **Market Price Intelligence Agent (§8)** in AgriSys. The agent helps farmers avoid distress selling, capture geographic price arbitrage across regional APMC mandis, and anticipate weekly price swings.

### Key Objectives:
1. **Mandi Data Pipeline (§8.1)**: Dual-stream ingestion for Agmarknet and eNAM data with a 10-minute caching layer (Redis cache with in-memory TTL fallback).
2. **Statistical Anomaly Filter**: Interquartile Range (IQR) outlier removal ($Q1 - 1.5 \times IQR$ to $Q3 + 1.5 \times IQR$) protecting downstream models against fat-finger reporting errors.
3. **7-Day Price Forecaster**: Computes 7-day projected price points, trend velocity (RISING, FALLING, STABLE), and percentage change with Prophet and statistical regression fallback.
4. **CACP MSP Comparator**: Benchmark evaluation against official Commission for Agricultural Costs and Prices procurement floors.
5. **Haversine Mandi Ranker**: Evaluates Great-Circle distances from farmer coordinates to APMC mandis and ranks candidates by **net realization price** after freight logistics.
6. **Sell / Hold / Transport Advisory**: Actionable farmer recommendations synthesized in English and Hindi.
7. **LangGraph StateGraph & API**: Plugs `market_agent_node` into the orchestrator and exposes `/api/market/advisory`.

---

## 2. SOLID Architecture Compliance

| Principle | Implementation in Stage 5 |
| :--- | :--- |
| **Single Responsibility (SRP)** | `MandiDataClient` handles data fetching/caching. `IQRAnomalyFilter` only performs outlier removal. `HaversineMandiRanker` calculates distances and net profits. `StatisticalPriceForecaster` only computes time-series projections. `compare_msp` validates MSP. `MarketAgent` coordinates the advisory. |
| **Open/Closed (OCP)** | `BasePriceForecaster` allows plugging alternative forecasting algorithms (e.g. ARIMA, NeuralProphet, LightGBM) without modifying the agent coordinator. |
| **Liskov Substitution (LSP)** | `ProphetPriceForecaster` and `StatisticalPriceForecaster` both implement `BasePriceForecaster` and can be substituted transparently. |
| **Interface Segregation (ISP)** | Schemas isolate mandi records (`MandiRecord`), forecast intervals (`PriceForecastPoint`), and MSP comparisons (`MSPComparison`). |
| **Dependency Inversion (DIP)** | High-level `MarketAgent` depends on `BasePriceForecaster` and `BaseLLMProvider` abstractions rather than hardcoded concrete engines. |

---

## 3. Market Data Pipeline Architecture

```
   Agmarknet API (15-min)                  eNAM Live Feed / Seed Data
             │                                        │
             └───────────────────┬────────────────────┘
                                 ▼
                     Redis Cache (TTL = 10 min)
                  (with In-Memory Fallback Store)
                                 │
                                 ▼
                         IQR Anomaly Filter
                [Q1 - 1.5*IQR  ≤  P  ≤  Q3 + 1.5*IQR]
                                 │
                                 ▼
                    7-Day Price Forecaster
              (Prophet / Statistical Trend-Seasonality)
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
       CACP MSP Comparison            Haversine Mandi Ranker
       (Procurement Floor)         d = 2R * arcsin(√hav(θ))
                 │                   Net Price = Mandi - Transport
                 └───────────────┬───────────────┘
                                 ▼
                    Sell / Hold / Transport Advisory
          "Tomato ₹18/kg at Lucknow (12km). Trending ↑ 8%.
           Recommendation: HOLD 5 days if storage available."
```

---

## 4. Modules & Files Created

### 4.1 Data Models (`agrisys/agents/market/models.py`)
- `MandiRecord`: Specific mandi arrival, min/max/modal prices, coordinates, distance, transport cost, and net realization price.
- `PriceForecastPoint`: Day offset (1 to 7), projected price, and 80% confidence interval.
- `MSPComparison`: Difference relative to official CACP floor and strategic procurement advice.
- `MarketAdvisoryReport`: Master advisory payload with top 5 mandis, 7-day forecast, and Sell/Hold action.

### 4.2 CACP Database & Evaluation (`agrisys/agents/market/msp_database.py`)
- Curated MSP database for major Indian crops (Paddy, Wheat, Maize, Cotton, Soyabean, Mustard, Gram, Tur, Moong, Urad, Groundnut, Sugarcane).
- `compare_msp`: Computes percentage deviations and procurement advisories.

### 4.3 Data Ingestion & Caching (`agrisys/agents/market/data_client.py`)
- `MandiDataClient`: Ingests mandi feeds with 10-minute Redis caching and in-memory TTL fallback.

### 4.4 Anomaly Removal (`agrisys/agents/market/anomaly_filter.py`)
- `IQRAnomalyFilter`: Rejects transaction price outliers.

### 4.5 Distance Calculation & Logistics (`agrisys/agents/market/haversine_ranker.py`)
- `haversine_distance`: Great-circle distance in kilometers.
- `HaversineMandiRanker`: Ranks regional mandis by net profit after deducting transit freight costs.

### 4.6 7-Day Forecaster (`agrisys/agents/market/forecaster.py`)
- `StatisticalPriceForecaster`: Robust polynomial regression with weekly arrival seasonality.
- `ProphetPriceForecaster`: Prophet wrapper with automatic statistical fallback.

### 4.7 Agent Coordinator & State Node (`agrisys/agents/market/agent.py`, `node.py`)
- `MarketAgent`: Coordinates the end-to-end intelligence pipeline.
- `market_agent_node`: LangGraph state node connected to `AgriSysState`.
