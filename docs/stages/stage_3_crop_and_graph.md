# Stage 3: Crop Recommendation Agent, 2D Visual Diagram Agent & LangGraph Orchestrator

## 1. Overview & Objectives
Stage 3 operationalizes the core reasoning and agronomic planning engines of AgriSys. It integrates:
1. **Crop Recommendation Agent (§6)**: Multi-model ensemble (XGBoost + Random Forest + Remote API) predicting optimal crops from 10 soil and climate features, enriched by Stage 1 RAG ICAR Package of Practices.
2. **Agronomic Feasibility & Seasonality Guardrail**: Post-model validation against season (Kharif, Rabi, Zaid), water source availability (irrigated vs rainfed), and soil pH limits.
3. **What-If Sensitivity Simulator**: Proactive tool allowing farmers and extension officers to simulate perturbations in nutrients or rainfall and observe real-time probability and SHAP shifts.
4. **SHAP TreeExplainer (§12.2)**: Multilingual (English + Hindi) feature attribution explaining *why* crops were recommended and what factors limited yields.
5. **Dual-Engine Visual Diagramming Agent (§9)**:
   - **Engine A (Mermaid.js)**: Logical workflows, IPM decision trees, sowing calendars (`gantt`), and timelines.
   - **Engine B (Parametric 2D SVG Schematics)**: High-resolution, measured vector schematics tailored for physical agricultural instructions (planting spacing grids, drip irrigation layouts, raised bed & mulch cross-sections, canopy pruning guides, and trap grids).
   - **Self-Healing Syntax Linter & Auto-Repair**: Ensures error-free client rendering.
   - **Bilingual Label Injector**: Injects Hindi and English annotations.
6. **LangGraph StateGraph Orchestrator (§3)**: State machine integrating Disease, Crop, Diagram, and RAG agents with multi-intent routing, response synthesis, and session memory.

---

## 2. SOLID Architecture Compliance

| Principle | Implementation in Stage 3 |
| :--- | :--- |
| **Single Responsibility (SRP)** | `LocalXGBoostCropModelTool` only computes XGBoost inferences. `CropSHAPExplainer` only calculates SHAP values. `SvgSchematicEngine` only builds 2D vector schematics. `MermaidEngine` only generates Mermaid code. `CropFeasibilityGuard` only validates agronomic constraints. `ResponseMerger` only synthesizes multi-agent responses. |
| **Open/Closed (OCP)** | `CROP_MODEL_REGISTRY` allows registering new crop models (e.g. CatBoost, LightGBM, remote endpoints) without touching agent code. `BaseVisualEngine` allows adding new rendering engines (e.g. Canvas, Three.js) without modifying the Diagram Agent. |
| **Liskov Substitution (LSP)** | All crop models implement `BaseCropModelTool` and can substitute one another. All visual engines implement `BaseVisualEngine`. |
| **Interface Segregation (ISP)** | Clean, minimal interfaces: `BaseCropModelTool` requires only `predict()`; `BaseVisualEngine` requires only `generate()`. |
| **Dependency Inversion (DIP)** | High-level `CropRecommendationAgent` depends on `BaseCropModelTool` and `BaseLLMProvider`, not concrete classes. LangGraph nodes communicate exclusively via `AgriSysState`. |

---

## 3. Crop Recommendation Pipeline Architecture

```
                                Soil & Climate Features
                        (N, P, K, pH, EC, Temp, Humidity, Rain)
                                          │
                                          ▼
                                ┌───────────────────┐
                                │ Feature Validator │
                                └─────────┬─────────┘
                                          │
                     ┌────────────────────┴────────────────────┐
                     ▼                                         ▼
        ┌─────────────────────────┐               ┌─────────────────────────┐
        │  XGBoost Classifier     │               │  Random Forest          │
        │  (Gradient-Boosted)     │               │  (Bagging Trees)        │
        └────────────┬────────────┘               └────────────┬────────────┘
                     │ (weight = 0.60)                         │ (weight = 0.40)
                     └────────────────────┬────────────────────┘
                                          ▼
                             ┌─────────────────────────┐
                             │  Weighted Ensemble Vote │
                             └────────────┬────────────┘
                                          ▼
                             ┌─────────────────────────┐
                             │  Agronomic Feasibility  │
                             │  & Seasonality Guard    │
                             │  (Kharif/Rabi/Zaid/pH)  │
                             └────────────┬────────────┘
                                          ▼
                             ┌─────────────────────────┐
                             │  SHAP TreeExplainer     │
                             │  (Hindi/English Labels) │
                             └────────────┬────────────┘
                                          ▼
                             ┌─────────────────────────┐
                             │  Stage 1 RAG Retrieval  │
                             │  (ICAR PoP Enrichment)  │
                             └─────────────────────────┘
```

### 3.1 Feature Vector Specification
The 10 feature inputs validated through Pydantic v2:
1. `N` (Nitrogen): $0 - 200\text{ kg/ha}$
2. `P` (Phosphorus): $0 - 200\text{ kg/ha}$
3. `K` (Potassium): $0 - 250\text{ kg/ha}$
4. `pH` (Soil reaction): $3.5 - 9.5$
5. `EC` (Electrical Conductivity): $0.0 - 5.0\text{ dS/m}$
6. `temperature`: $5.0 - 50.0\text{ }^\circ\text{C}$
7. `humidity`: $10.0 - 100.0\%$
8. `rainfall`: $100 - 3500\text{ mm}$
9. `season`: `kharif`, `rabi`, `zaid`, or `annual`
10. `water_availability`: `canal_irrigated`, `borewell_drip`, or `rainfed`

### 3.2 Supported Crops (22 Classes)
`rice`, `maize`, `chickpea`, `kidneybeans`, `pigeonpeas`, `mothbeans`, `mungbean`, `blackgram`, `lentil`, `pomegranate`, `banana`, `mango`, `grapes`, `watermelon`, `muskmelon`, `apple`, `orange`, `papaya`, `coconut`, `cotton`, `jute`, `coffee`.

---

## 4. Dual-Engine Visual Diagramming Architecture

### 4.1 Engine Comparison

| Engine | Primary Output | Best For | Typical Use Cases |
| :--- | :--- | :--- | :--- |
| **Engine A: Mermaid.js** | Logical graph string | Process flows & calendars | Sowing calendars (`gantt`), growth stages (`timeline`), IPM spray decision trees (`flowchart`), fertilizer NPK breakdown (`pie`). |
| **Engine B: Parametric 2D SVG** | Measured vector SVG XML | Physical 2D field schematics | Planting spacing grids ($60\text{ cm} \times 45\text{ cm}$), drip irrigation layouts (filters, mains, laterals), raised bed cross-sections, canopy pruning cuts, pheromone trap distributions. |

### 4.2 2D SVG Schematic Capabilities
1. **Measured Planting Grids**: Displays plant icons with exact row-to-row and plant-to-plant dimension lines, plant population per acre, and tractor passage tracks.
2. **Drip Irrigation Layout**: Top-down technical layout showing pump, disc filter, venturi fertilizer injector, main pipe ($50\text{ mm}$), sub-main ($32\text{ mm}$), drip laterals ($16\text{ mm}$), flush valves, and inline dripper spacing ($30\text{ cm}$).
3. **Raised Bed & Mulch Cross-Section**: Side-view profile displaying top width ($90\text{ cm}$), bottom width ($120\text{ cm}$), furrow depth ($15\text{ cm}$), silver-black plastic mulch layer, lateral drip line depth, and seed pocket placement.
4. **Tree Pruning & Canopy Architecture**: Tree structural silhouette distinguishing main stem, primary scaffold branches, secondary fruiting wood, and water sprouts marked with 45° angle cut callouts.
5. **Acre-Grid Trap Distribution**: Field perimeter with 6–8 trap icons, installation height ($30\text{ cm}$ above canopy), wind direction arrow, and lure replacement interval.

### 4.3 Self-Healing Syntax Linter
The linter checks:
- Mermaid syntax integrity (balanced brackets, escaped quotes, valid direction tokens).
- SVG XML well-formedness (closing tags, valid viewBox, namespace attributes).
- Injects bilingual Indic labels (Hindi + English) for all measurements and technical terms.
- Performs automatic deterministic repair or single-shot LLM self-correction if syntax errors are detected.

---

## 5. LangGraph StateGraph Architecture

### 5.1 Graph Topology
```
                      START / User Query
                              │
                              ▼
                     [ intent_router ]
                              │
         ┌────────────────────┼────────────────────┐
         ▼ (if disease)       ▼ (if crop_rec)      ▼ (if diagram)
   [ disease_agent ]    [ crop_agent ]       [ diagram_agent ]
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
                              ▼
                     [ rag_retriever ]
                              │
                              ▼
                    [ response_merger ]
                              │
                              ▼
                   [ hallucination_guard ]
                              │
                 ┌────────────┴────────────┐
                 ▼ (score >= 0.70)         ▼ (score < 0.70)
             [  END  ]             [ Escalate KCC ]
```

### 5.2 AgriSysState Schema
```python
class AgriSysState(TypedDict):
    query: str
    image_bytes: bytes | None
    image_path: str | None
    sensor_data: dict | None
    voice_audio_path: str | None
    language: str
    location: dict | None
    session_id: str
    turn_number: int
    history: list[dict]
    intents: list[str]
    active_agents: list[str]
    agent_results: Annotated[list[dict], operator.add]
    rag_chunks: Annotated[list[dict], operator.add]
    citations: list[str]
    grad_cam_path: str | None
    shap_values: dict | None
    diagram_code: str | None
    diagram_type: str | None
    svg_schematic: str | None
    merged_response: str
    confidence_score: float
    escalate: bool
    tts_audio_path: str | None
```

---

## 6. Verification & Test Strategy
- `tests/test_crop_agent.py`: 8 tests covering XGBoost, Random Forest, ensemble voting, feasibility filter, What-If simulator, and SHAP.
- `tests/test_diagram_agent.py`: 7 tests covering Mermaid workflows, 2D SVG schematics, self-healing syntax linter, and bilingual translator.
- `tests/test_orchestrator.py`: 8 tests covering intent routing, multi-intent dispatch, state reducer aggregation, response merger, and full StateGraph workflow.
- All 38 existing tests must continue to pass (Total $\ge 61$ passing tests).
