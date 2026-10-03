# Stage 4: Nutrition Deficiency Agent & Cross-Modal Fusion Architecture

## 1. Overview & Objectives
Stage 4 implements the **Nutrition Deficiency Agent (§5)** in AgriSys. Crop nutrient deficiencies often cause confusing foliar visual patterns that closely resemble disease lesions or environmental stresses. By integrating foliar computer vision with direct soil chemical sensor metrics, the Nutrition Agent achieves high diagnostic precision and generates tailored commercial fertilizer recommendations (Urea, DAP, MOP) compliant with official **ICAR Soil Health Card (SHC)** benchmarks.

### Key Objectives:
1. **Cross-Modal Fusion Architecture (§5.1)**: Fuses 448×448 RGB leaf imagery (ResNet-50 2048-dim feature representation) with 6-channel normalized soil sensors ($N, P, K, pH, EC, \text{moisture}$) into a 2054-dim joint vector.
2. **Dual Multi-Task Prediction Heads**:
   - **Head A**: 12 agronomic deficiency classes (Nitrogen, Phosphorus, Potassium, Calcium, Magnesium, Sulfur, Iron, Zinc, Manganese, Boron, Copper, Healthy).
   - **Head B**: Continuous elemental $[N_{\text{dose}}, P_{\text{dose}}, K_{\text{dose}}]$ (kg/ha) regression.
3. **ICAR Soil Health Card Rules & Fertilizer Converter**: Translates elemental targets into commercial farmer quantities (Urea, DAP, MOP in kg/ha and kg/acre) with split application timing.
4. **Multimodal Fallbacks**: Operates seamlessly across multimodal, sensor-only, and vision-only modes.
5. **LangGraph Orchestrator Integration**: Plugs `nutrition_agent_node` into `AgriSysState` and `create_agrisys_graph`.

---

## 2. SOLID Architecture Compliance

| Principle | Implementation in Stage 4 |
| :--- | :--- |
| **Single Responsibility (SRP)** | `ResNet50FeatureExtractor` only extracts image embeddings. `SensorNormalizer` only handles sensor scale projection. `SoilHealthCardEvaluator` only applies ICAR rules and fertilizer math. `CrossModalNutritionFusionNet` computes neural inferences. `NutritionAgent` coordinates end-to-end diagnosis. |
| **Open/Closed (OCP)** | New nutrient deficiency classes or additional sensor parameters can be extended without altering the core agent coordination flow. |
| **Liskov Substitution (LSP)** | Multimodal fallbacks maintain consistent output contracts (`DeficiencyPrediction`, `FertilizerDoseRecommendation`) regardless of execution modality. |
| **Interface Segregation (ISP)** | Pydantic models isolate sensor schemas (`SoilSensorReading`), predictions (`DeficiencyPrediction`), and commercial dosing (`FertilizerDoseRecommendation`). |
| **Dependency Inversion (DIP)** | `NutritionAgent` depends on abstractions and delegates model logic to `CrossModalNutritionFusionNet` and rule evaluation to `SoilHealthCardEvaluator`. |

---

## 3. Cross-Modal Fusion Pipeline Architecture

```
  Leaf Image (448×448 RGB)                  Soil Sensor Readings
             │                           {N, P, K, pH, EC, Moisture}
             ▼                                        │
  ResNet-50 Feature Backbone                   Feature Normalizer
  (Bottleneck blocks 3-4-6-3)                      (Range [0, 1])
             │ (2048-dim)                             │ (6-dim)
             └───────────────────┬────────────────────┘
                                 ▼
                   Concatenate → 2054-dim Joint Vector
                                 │
                                 ▼
                         Cross-Modal MLP
                   FC(2054 → 512) + ReLU + Dropout(0.3)
                   FC(512 → 128)  + ReLU + Dropout(0.2)
                   FC(128 → 64)   + ReLU
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
       Deficiency Head (Head A)          Dose Head (Head B)
             FC(64 → 12)                     FC(64 → 3)
                 │                               │
                 ▼                               ▼
          Softmax Probs                   Continuous NPK
     12 Deficiency Classes                Doses (kg/ha)
                                                 │
                                                 ▼
                                     Clamped to ICAR SHC Norms
                                                 │
                                                 ▼
                                    Commercial Fertilizer Units
                                      (Urea, DAP, MOP per acre)
```

---

## 4. Modules & Files Created

### 4.1 Data Models (`agrisys/agents/nutrition/models.py`)
- `SoilSensorReading`: Pydantic schema with strict range and pH viability checks.
- `DeficiencyPrediction`: Predicted nutrient deficiency class, confidence, severity, and foliar symptoms.
- `FertilizerDoseRecommendation`: Elemental and commercial quantities (Urea, DAP, MOP) in kg/ha and kg/acre, with split-application stages.
- `NutritionReport`: Master structured advisory containing evaluations, citations, and treatment schedules.

### 4.2 Agronomic Rules & Commercial Formulations (`agrisys/agents/nutrition/shc_rules.py`)
- `SoilHealthCardEvaluator`: Categorizes N, P, K, pH, EC, and moisture into ICAR benchmark tiers (Low, Medium, High).
- Converts elemental deficits into commercial fertilizers using standard compound equations:
  $$\text{DAP (kg/ha)} = \frac{P_{\text{target}}}{0.46}$$
  $$\text{Urea (kg/ha)} = \frac{\max(0, N_{\text{target}} - (\text{DAP} \times 0.18))}{0.46}$$
  $$\text{MOP (kg/ha)} = \frac{K_{\text{target}}}{0.60}$$

### 4.3 PyTorch Cross-Modal Network (`agrisys/agents/nutrition/fusion_model.py`)
- `ResNet50FeatureExtractor`: Native PyTorch ResNet-50 backbone producing 2048-dimensional visual vectors.
- `SensorNormalizer`: Scales raw sensor inputs to $[0, 1]$ bounds.
- `CrossModalNutritionFusionNet`: Concatenation layer, 3-layer shared MLP with dropout, 12-class deficiency head, and 3-output regression head. Supports zero-imputation fallbacks for single-modality queries.

### 4.4 Agent Coordinator & State Node (`agrisys/agents/nutrition/agent.py`, `node.py`)
- `NutritionAgent`: Master coordinator executing multimodal diagnosis with Hindi/English bilingual advisories.
- `nutrition_agent_node`: LangGraph StateNode consuming `sensor_data` and/or `image_bytes`, populating `nutrition_data` and `agent_results`.

### 4.5 Synthetic Data Generator (`scripts/data/generate_sensor_pairs.py`)
- Generates paired synthetic sensor readings and ground truth deficiency labels derived from ICAR SHC statistical distributions.

### 4.6 Orchestrator & API Endpoints
- `agrisys/orchestrator/state.py`: Adds `nutrition_data` to `AgriSysState`.
- `agrisys/orchestrator/graph.py`: Adds conditional routing and node registration for `nutrition_agent`.
- `agrisys/api/main.py`: Exposes `/api/nutrition/diagnose` for direct REST querying.
