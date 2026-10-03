# AgriSys Technology Stack Inventory

This document tracks all primary technologies, libraries, minimum versions, roles, and rationale across all build stages.

---

## Stage 1: Foundation Layer

| Category | Component / Library | Version | Purpose & Rationale |
| :--- | :--- | :--- | :--- |
| **Language** | Python | `>=3.12.3` | Modern typing, native performance, memory-efficient asyncio. |
| **API Framework** | FastAPI | `>=0.115.0` | Async REST endpoints and native WebSocket `/ws/chat` protocol. |
| **ASGI Server** | Uvicorn | `>=0.30.0` | High-throughput asynchronous server. |
| **Data Validation** | Pydantic v2 | `>=2.10.0` | High-speed Rust-based schema validation and configuration management. |
| **Vector Store** | Qdrant Client | `>=1.19.0` | Dense cosine similarity vector search with rich payload metadata and in-memory test mode. |
| **Sparse Search** | Rank-BM25 | `>=0.2.2` | Fast BM25Okapi keyword retrieval for agricultural domain terms. |
| **HTTP Client** | HTTPX | `>=0.28.0` | Async HTTP client with native SSE (Server-Sent Events) streaming. |
| **LLM Provider** | OpenAI SDK | `>=1.50.0` | Official client for GPT-4o / GPT-5.5 completions and embeddings. |
| **Configuration** | PyYAML | `>=6.0.2` | Parsing `config/*.yaml` files with variable expansion. |
| **Testing** | Pytest + Pytest-Asyncio | `>=8.3.0` / `>=1.4.0` | Automated async test runner. |
| **Containers** | Docker Compose | `v3.8` | Qdrant, Redis, PostgreSQL, MinIO, Langfuse, API containerization. |

---

## Stage 2: Disease Diagnostic Agent

| Category | Component / Library | Version | Purpose & Rationale |
| :--- | :--- | :--- | :--- |
| **Computer Vision** | OpenCV (`opencv-python-headless`) | `>=5.0.0` | High-speed CLAHE contrast enhancement, Laplacian blur estimation, and HSV/LAB lesion color segmentation. |
| **Image Processing** | Pillow (PIL) | `>=10.3.0` | Format validation, EXIF orientation correction and privacy stripping. |
| **Tensors / XAI** | PyTorch (`torch`) | `>=2.12.0` | Normalized tensor creation `[1, 3, 224, 224]` and Grad-CAM gradient hooks for local model explainability. |
| **Endpoint Client** | HTTPX | `>=0.28.0` | Secure HTTPS communication to remote HuggingFace Inference APIs and local model endpoints with Bearer auth and circuit breaking. |

---

## Stage 3: Crop Recommendation Agent, 2D Visuals & LangGraph

| Category | Component / Library | Version | Purpose & Rationale |
| :--- | :--- | :--- | :--- |
| **Agent Orchestration** | LangGraph / LangChain-Core | `>=1.2.0` | StateGraph state machine, cyclic/acyclic graph routing, parallel agent dispatch, and reducer aggregation. |
| **Gradient Boosting** | XGBoost | `>=3.2.0` | High-performance multi-class tree boosting for crop prediction from soil & climate features. |
| **Ensemble Learning** | Scikit-Learn | `>=1.5.0` | Random Forest bagging classifier, label encoders, and stratified dataset preprocessing. |
| **Explainable AI (XAI)** | SHAP | `>=0.46.0` | TreeExplainer calculating exact feature attribution contributions with bilingual feature labels. |
| **2D Vector Graphics** | Native SVG XML Generator | Standard | Procedural 2D measured agronomic schematics (spacing grids, drip layouts, bed profiles) with zero client dependencies. |
| **Workflow Diagramming**| Mermaid.js syntax | Standard | Logical flowcharts, Gantt sowing calendars, timelines, and decision trees. |

---

## Planned Technologies for Stages 4–9

- **Stage 4 (Nutrition Agent)**: PyTorch (cross-modal fusion MLP + ResNet-50).
- **Stage 5 (Market Agent)**: Prophet, Pandas, Requests.
- **Stage 6 (Weather Agent)**: Open-Meteo, IMD API, Scipy (Penman-Monteith).
- **Stage 7 (Voice Pipeline)**: OpenAI Whisper, Bhashini API, SoundFile.
- **Stage 8 (XAI & Frontend)**: React 18, Vite, Tailwind CSS, Recharts, Mermaid.js.
- **Stage 9 (Evaluation)**: RAGAS, Langfuse, Prometheus client, Grafana.

