# Stage 9: Production Deployment, CI/CD & Monitoring Stack

## 1. Overview & Objectives
Stage 9 fulfills the productionization, monitoring, continuous integration, and containerized deployment requirements specified in **§18** of `AgriSys_Technical_Documentation.docx`.

### Key Objectives:
1. **Production Multi-Stage Docker Topology (§18.1)**:
   - `Dockerfile`: Multi-stage Python 3.12 backend container running Uvicorn on port `8000`.
   - `frontend/Dockerfile`: Multi-stage Node 22 $\to$ Nginx Alpine container serving built React 18 assets on port `80` (mapped to `5173`).
   - `frontend/nginx.conf`: Production reverse proxy handling SPA history routing, API reverse proxying (`/api/` $\to$ `http://api:8000/api/`), static audio assets, and WebSocket connection upgrades (`/ws/`).
2. **Docker Compose Orchestration Stack (§18.2)**:
   - Full 8-service enterprise topology in `docker-compose.yml`:
     - `agrisys-api`: FastAPI multi-agent backend (`:8000`).
     - `agrisys-frontend`: Nginx React PWA frontend (`:5173`).
     - `agrisys-qdrant`: Vector database (`:6333`, `:6334`).
     - `agrisys-redis`: Cache for Mandi & Weather APIs (`:6379`).
     - `agrisys-postgres`: PostgreSQL database for Langfuse and user session state (`:5432`).
     - `agrisys-minio`: S3-compatible visual/audio artifact storage (`:9000`, `:9001`).
     - `agrisys-langfuse`: Multi-agent tracing & LLM observability (`:3000`).
     - `agrisys-prometheus`: Prometheus metrics scraper (`:9090`).
     - `agrisys-grafana`: Grafana telemetry dashboards (`:3001`).
3. **Observability & Prometheus Metrics Exporter (§18.3)**:
   - Created `agrisys/api/metrics.py`: Custom zero-dependency in-memory Prometheus metrics collector and HTTP middleware.
   - Endpoint: `GET /metrics` exporting standard Prometheus exposition format:
     - `agrisys_requests_total{method, endpoint, status}`: Request count counter.
     - `agrisys_request_duration_seconds{method, endpoint}`: Average execution latency gauge.
     - `agrisys_agent_invocations_total{agent}`: Specialist agent execution counter (`disease`, `crop`, `nutrition`, `market`, `weather`, `diagram`, `rag`).
     - `agrisys_hallucination_guard_score`: Mean factual grounding confidence score from Stage 1 Guard.
   - `config/prometheus.yml`: Scraper configuration targeting `api:8000`.
4. **Continuous Integration (CI) Workflow (§18.4)**:
   - `.github/workflows/ci.yml`: Automated GitHub Actions pipeline executing on push/PR:
     - Python 3.12 dependency installation & unit tests (`pytest tests/ -v`).
     - Node.js 22 frontend build verification (`npm run build`).
     - Docker Compose syntax validation (`docker compose config`).

---

## 2. SOLID Architecture Compliance

| Principle | Implementation in Stage 9 |
| :--- | :--- |
| **Single Responsibility (SRP)** | `MetricsCollector` only collects and formats metrics. `PrometheusMiddleware` only intercepts HTTP timings. `nginx.conf` only handles routing and asset serving. |
| **Open/Closed (OCP)** | New custom metrics, agent tracking counters, or alert thresholds can be registered in `MetricsCollector` without modifying existing API routes. |
| **Liskov Substitution (LSP)** | Metrics endpoint returns standard Prometheus text exposition format compatible with any standard OpenMetrics/Prometheus scraper. |
| **Interface Segregation (ISP)** | Scrape configuration, Grafana dashboards, and CI actions are separated into clean, modular config files. |
| **Dependency Inversion (DIP)** | Middleware and metrics rely on abstract HTTP request interfaces rather than vendor-specific instrumentation clients. |

---

## 3. Production Deployment Topology

```
                                 Client Browser / Mobile PWA
                                              │
                                              ▼
                    ═════════════════════════════════════════════
                    Reverse Proxy & Static Web (Port 5173)
                    (Nginx 1.25 Alpine: React 18 + Vite PWA)
                    ═════════════════════════════════════════════
                                   │              │
                     REST & WS API │              │ Static Artifacts
                                   ▼              ▼
                    ═════════════════════════════════════════════
                    AgriSys Backend Service (Port 8000)
                    (FastAPI + LangGraph Orchestrator)
                    ═════════════════════════════════════════════
                       │              │              │
                       ▼              ▼              ▼
                 ┌───────────┐  ┌───────────┐  ┌───────────┐
                 │  Qdrant   │  │   Redis   │  │ PostgreSQL│
                 │ Vector DB │  │ API Cache │  │ Langfuse  │
                 │  (:6333)  │  │  (:6379)  │  │  (:5432)  │
                 └───────────┘  └───────────┘  └───────────┘
                       │
                       ▼ (Metrics Scrape :8000/metrics)
                 ┌───────────┐
                 │Prometheus │
                 │  (:9090)  │
                 └─────┬─────┘
                       │
                       ▼ (Telemetry Dashboards)
                 ┌───────────┐
                 │  Grafana  │
                 │  (:3001)  │
                 └───────────┘
```

---

## 4. Verification Results

1. **Automated Test Suite**:
   ```
   ========================= 113 passed in 59.57s =========================
   - tests/test_api.py (Includes test_prometheus_metrics_endpoint) ... 10/10 PASSED
   - tests/test_voice_pipeline.py .................................... 11/11 PASSED
   - tests/test_weather_agent.py ..................................... 12/12 PASSED
   - tests/test_market_agent.py ...................................... 14/14 PASSED
   - tests/test_nutrition_agent.py ................................... 12/12 PASSED
   - tests/test_crop_agent.py ......................................... 8/8  PASSED
   - tests/test_diagram_agent.py ...................................... 8/8  PASSED
   - tests/test_disease_agent.py ...................................... 6/6  PASSED
   - tests/test_model_registry.py ..................................... 4/4  PASSED
   - tests/test_orchestrator.py ....................................... 5/5  PASSED
   - tests/test_preprocessing.py ...................................... 5/5  PASSED
   - tests/test_providers.py .......................................... 7/7  PASSED
   - tests/test_rag_ingestion.py ...................................... 5/5  PASSED
   - tests/test_rag_retrieval.py ...................................... 6/6  PASSED
   ```

2. **Frontend Production Compilation**:
   ```bash
   npm run build
   ✓ 2401 modules transformed in 8.75s.
   dist/index.html (1.23 kB)
   dist/assets/index-CV0FarLI.css (24.84 kB)
   dist/assets/index-Bi45TNAN.js (600.13 kB)
   ```
