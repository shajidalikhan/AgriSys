# Stage 2: Disease Diagnostic Agent — Comprehensive Implementation & Pipeline Guide

This document provides the complete, authoritative technical documentation for **AgriSys Stage 2: Disease Diagnostic Agent** (§4 and §12.1). It details the architectural design, the 7-step sequential pipeline, the 5 approved architectural enhancements, endpoint security mechanisms, candidate HuggingFace model tools, data schemas, and developer extension procedures.

---

## 1. Architectural Overview & Design Rationale

The Disease Diagnostic Agent is responsible for analyzing leaf photographs uploaded by farmers (via text, voice, or file upload), validating their clarity and botanical content, identifying the crop, diagnosing disease conditions, estimating infection severity, providing visual explainability overlays, and generating actionable treatment advisories grounded in official ICAR/FAO protocols.

### Core Architectural Decisions:
1. **Endpoint-Only Model Security Architecture**:
   - In adherence to strict security and sandboxing principles, the core AgriSys process **never loads untrusted neural network weights directly into memory**.
   - All AI models (whether hosted remotely on the HuggingFace Hub or running locally inside dedicated microservice containers) are accessed exclusively through secure HTTP/REST endpoints with Bearer token authorization and strict timeout policies.
2. **Sequential Crop-First Pipeline**:
   - Rather than executing all disease models in parallel on every image, the system executes a dedicated **Crop Detector** first. Once the crop is established, it dispatches to a specialist model trained specifically for that crop family, maximizing diagnostic accuracy and minimizing compute waste.
3. **Pluggable Model Tool Pattern (Open/Closed Principle - OCP)**:
   - All disease models are registered as modular tools implementing `BaseDiseaseModelTool`.
   - New models can be added by adding an entry to `MODEL_REGISTRY` in `config/` or `registry.py` without modifying any existing agent code.

---

## 2. The 7-Step Sequential Diagnostic Pipeline

```
                     Farmer Uploads Leaf Photo (+ Optional Text Query)
                                             │
                                             ▼
     ═════════════════════════════════════════════════════════════════════════
     STEP 1: Image Preprocessing & Plant Leaf Gatekeeper
     ═════════════════════════════════════════════════════════════════════════
     • Input: Raw image bytes (JPEG, PNG, WEBP, HEIC)
     • Validation: Format verification via PIL, minimum resolution check (224×224 px)
     • Sharpness Check: Laplacian variance estimation (Var(∇²I) ≥ 35.0 required)
     • Foliage Gatekeeper (Improvement 1): HSV thresholding for vegetative pixels
       ──► If foliage ratio < 12%: REJECT with helpful prompt
     • Normalization: EXIF privacy strip, auto-orientation transpose
     • Enhancement: CLAHE (clipLimit=2.0, tileGrid=(8,8)) in LAB color space
     • Dual Output: Clean RGB JPEG bytes (for HTTP endpoints) +
                    Normalized PyTorch tensor [1, 3, 224, 224] (for local Grad-CAM)
                                             │
                                             ▼
     ═════════════════════════════════════════════════════════════════════════
     STEP 2: Dedicated Crop Identification & Discrepancy Resolution
     ═════════════════════════════════════════════════════════════════════════
     • Input: Enhanced image bytes + optional farmer text query
     • Crop Detector Tool: Dedicated endpoint (MobileNetV2 crop classifier)
     • Discrepancy Resolver (Improvement 2):
       - Extracts crop hints from text (e.g. "My tomato crop has yellow spots")
       - If vision agrees with text: "consensus" (+5% confidence bonus)
       - If vision conflicts with text: prioritizes vision if confidence ≥ 80%,
         transparently logging a discrepancy note in the final advisory
     • Output: CropDetectionResult(crop, confidence, source, discrepancy_note)
                                             │
                                             ▼
     ═════════════════════════════════════════════════════════════════════════
     STEP 3: Targeted Crop Specialist vs. General Disease Routing
     ═════════════════════════════════════════════════════════════════════════
     • Crop Model Router: Queries MODEL_REGISTRY for candidate tools matching crop:
       - Tomato / Solanaceae ──► Tomato Specialist Endpoint (MobileNetV2)
       - Wheat / Rice / Corn ──► Cereal Grain Specialist Endpoint (ViT-Base)
       - Unlisted Crop or Busy Endpoint ──► General Disease Detector (PlantVillage ViT)
     • Circuit Breaker (Improvement 4):
       - 4.0s timeout per HTTP endpoint call
       - Automatic fallback to backup universal model on 503/429/timeout
                                             │
                                             ▼
     ═════════════════════════════════════════════════════════════════════════
     STEP 4: Weighted Ensemble Voting & Quantitative Severity Indexing
     ═════════════════════════════════════════════════════════════════════════
     • Weighted Voter: Combines multiple specialist outputs:
       $$\text{Vote Share}(d) = \sum_{m} \frac{w_m}{\sum w} \cdot \mathbf{1}_{m}(d)$$
       $$\text{Confidence}(d) = \frac{\sum_{m \in \text{voters}(d)} w_m \cdot C_m}{\sum_{m \in \text{voters}(d)} w_m}$$
     • Severity Index (Improvement 3): Clinical 0 to 5 scale:
       Grade 0: Healthy | Grade 1: Trace (<5%) | Grade 2: Mild (5-15%) |
       Grade 3: Moderate (15-30%) | Grade 4: Severe (30-50%) | Grade 5: Critical (>50%)
     • Output: DiseasePrediction(crop, disease, confidence, severity, severity_label)
                                             │
                                             ▼
     ═════════════════════════════════════════════════════════════════════════
     STEP 5: Visual Explainability (Grad-CAM & Adaptive Lesion Heatmap)
     ═════════════════════════════════════════════════════════════════════════
     • Dual Explainability Architecture (Improvement 5):
       - Local Models: Tensor Grad-CAM on layer4 convolutional feature maps
       - Remote API Endpoints: Adaptive Color-Space Lesion Segmentation:
         - Isolates chlorotic yellow halos (HSV: [10,40,40]-[25,255,255]) and
           necrotic brown spots (LAB luminance thresholding)
         - Gaussian diffusion filter (kernel=31×31) creating smooth activation map
         - Overlays colored JET colormap (35% alpha blend)
         - Draws bounding boxes around primary lesion clusters (>0.5% leaf area)
     • Saves artifact: data/artifacts/lesion_heatmap_{hash}.jpg
                                             │
                                             ▼
     ═════════════════════════════════════════════════════════════════════════
     STEP 6: AgriChain CoT Reasoning & Stage 1 RAG Retrieval
     ═════════════════════════════════════════════════════════════════════════
     • Queries Stage 1 Qdrant vector database:
       query = "treatment dosage fungicide management for {disease} in {crop}"
       filters = {crop, domain: "disease", language}
     • Pulls official ICAR/FAO package of practices (active ingredients, dosages)
     • Formulates severity-specific action guidelines:
       - Grade 1: Preventive bio-fungicides (Trichoderma) or contact sprays
       - Grade 3: Curative systemic sprays (e.g. Ridomil MZ at 2.5g/l)
       - Grade 5: Rogueing and disposal of affected crop to stop epidemic
                                             │
                                             ▼
     ═════════════════════════════════════════════════════════════════════════
     STEP 7: LangGraph State Node Integration
     ═════════════════════════════════════════════════════════════════════════
     • disease_agent_node(state) -> state
     • Updates state: disease_result, active_agent="disease", final_advisory
```

---

## 3. Detailed Breakdown of the 5 Approved Improvements

### Improvement 1: Plant Leaf Gatekeeper (Non-Plant Filter)
- **Problem Solved**: Prevents the vision models from hallucinating crop diseases when farmers upload non-plant photos (e.g., machinery, soil, animals, household items).
- **Algorithm**:
  1. Image is converted to HSV (Hue, Saturation, Value) color space.
  2. Green plant foliage mask is computed: $\text{Hue} \in [25, 90], \text{Sat} \in [30, 255], \text{Val} \in [30, 255]$.
  3. Chlorotic / diseased leaf mask is computed: $\text{Hue} \in [10, 25], \text{Sat} \in [40, 255], \text{Val} \in [40, 255]$.
  4. Total vegetative pixel count is divided by total image pixels: $\text{Ratio} = \frac{N_{\text{foliage}}}{W \times H}$.
  5. If $\text{Ratio} < 0.12$, the image is rejected early with status `"rejected"` and message:  
     *"The image does not appear to show plant foliage or a crop leaf. Please upload a clear photo of the crop leaf."*
- **Blur Filter**: Uses discrete 2D Laplacian operator convolution $\nabla^2 I$. If $\text{Var}(\nabla^2 I) < 35.0$, image is flagged as blurry and rejected.

### Improvement 2: Multi-Modal Crop Agreement & Discrepancy Resolver
- **Problem Solved**: Prevents confusion between visually similar crops (e.g., tomato vs. potato, which are both Solanaceae and have similar leaf geometry).
- **Algorithm**:
  1. Extracts crop keywords from farmer query (supporting English names and Hindi aliases like `"टमाटर"`, `"धान"`, `"गेहूं"`).
  2. If the user text specifies a crop:
     - **Agreement**: If $\text{Crop}_{\text{text}} == \text{Crop}_{\text{vision}}$, source is tagged as `"consensus"` with a $+5\%$ confidence boost.
     - **Conflict**: If $\text{Crop}_{\text{text}} \neq \text{Crop}_{\text{vision}}$:
       - If vision confidence $\ge 80\%$, vision prediction is accepted and a transparent advisory note is added:  
         *`"User mentioned 'wheat', but image vision analysis detected 'tomato' (94% confidence)."`*
       - If vision confidence $< 80\%$, user text hint is trusted.

### Improvement 3: Quantitative Severity Index (Scale 0 to 5)
- **Problem Solved**: Farmers need urgency and stage-appropriate dosages, not just an abstract disease label.
- **Scale Definition**:
  - **Grade 0 (Healthy)**: No visible disease symptoms. Normal photosynthetic tissue.
  - **Grade 1 (Trace, <5% area)**: Faint initial spots. Recommendation: bio-fungicides or protective contact sprays (Mancozeb 2.0g/l).
  - **Grade 2 (Mild, 5–15% area)**: Discrete scattered lesions. Recommendation: early curative spray.
  - **Grade 3 (Moderate, 15–30% area)**: Coalescing lesions with chlorotic halos. Recommendation: systemic curative spray (Ridomil MZ 2.5g/l).
  - **Grade 4 (Severe, 30–50% area)**: Significant leaf curl and tissue necrosis.
  - **Grade 5 (Critical, >50% area)**: Extensive leaf collapse. Recommendation: immediate rogueing to protect adjacent healthy plants.

### Improvement 4: Circuit Breaker & Automatic Endpoint Fallback
- **Problem Solved**: Protects against remote API downtime (HuggingFace 503 loading states or 429 rate limits) and network latency spikes.
- **Mechanism**:
  - All endpoint calls are wrapped in `SecureModelEndpointClient` with a strict $4.0\text{s}$ timeout.
  - Fallback Hierarchy:
    $$\text{Crop Specialist Endpoint} \xrightarrow{\text{timeout / error}} \text{Universal Disease Endpoint} \xrightarrow{\text{error}} \text{Local Deterministic Fallback}$$
  - Guarantees that the farmer's chat session never crashes or hangs indefinitely.

### Improvement 5: Dual Visual Explainability (Grad-CAM & Adaptive Lesion Heatmap)
- **Problem Solved**: Remote API endpoints return class predictions but do not expose internal network gradients required for standard Grad-CAM.
- **Dual Engine in `DiseaseGradCAM`**:
  - **Local Model Mode**: Registers forward and backward PyTorch hooks on `layer4` convolutional feature maps, computing gradient-weighted class activation maps.
  - **Remote API Mode (Color-Space Lesion Segmentation)**:
    1. Computes necrotic mask using LAB luminance inverted threshold ($L < 75$) combined with HSV brown lesion spectrum ($H \in [5, 25]$).
    2. Applies large-radius Gaussian smoothing ($31 \times 31$ kernel) to produce a smooth, continuous activation intensity map.
    3. Colors activation map using OpenCV `cv2.COLORMAP_JET`.
    4. Alpha blends over original image ($35\%$ heatmap, $65\%$ leaf).
    5. Detects contours of lesion clusters with area $>0.5\%$ of leaf and draws red bounding boxes around primary infection sites.
    6. Saves visualization image to `data/artifacts/lesion_heatmap_{hash}.jpg`.

---

## 4. Candidate HuggingFace Models Catalog

| Model Handle | Architecture | Role in AgriSys | Classes Covered | Recommended Setting |
| :--- | :--- | :--- | :--- | :--- |
| `linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification` | MobileNetV2 | Primary Crop Detector & Vegetable Specialist | 38 classes (Tomato, Potato, Corn, Apple, Grape, Peach, etc.) | Default enabled for `crop_detector` and `tomato_specialist`. Ultra-fast (<50ms). |
| `wambugu71/crop_leaf_diseases_vit` | ViT-Base | Cereal & Grain Specialist | 14 classes (Wheat, Rice, Corn, Potato) | Default enabled for `cereal_grain_specialist`. Strong attention on grain leaf rusts and leaf blasts. |
| `ozair23/plant-disease-detection` | ViT / ResNet | Universal Disease Fallback | 39 classes (Universal PlantVillage) | Default enabled for `general_disease_detector`. Catches unlisted crops and circuit-breaker fallbacks. |
| `custom_user_model` | Any HF Hub Model | User Extension | Custom | User uploads fine-tuned weights to Hugging Face and registers handle in `MODEL_REGISTRY`. |

---

## 5. Modules, Classes, and Methods Reference

### 5.1 `agrisys.agents.disease.models`
- `GatekeeperResult`: Pydantic model (`is_plant`, `foliage_ratio`, `blur_score`, `is_blurred`, `message`).
- `CropDetectionResult`: Pydantic model (`crop`, `confidence`, `source`, `top_candidates`, `discrepancy_note`).
- `DiseasePrediction`: Pydantic model (`crop`, `disease`, `confidence`, `severity`, `severity_label`, `top_k`, `model_name`, `execution_mode`).
- `DiseaseDiagnosticReport`: Complete diagnostic report schema (`crop`, `disease`, `confidence`, `severity_score`, `severity_label`, `advisory`, `treatment_protocol`, `verified_sources`, `heatmap_artifact_path`, `gatekeeper`, `crop_detection`).

### 5.2 `agrisys.agents.disease.preprocessor` (`ImagePreprocessor`)
- `validate_and_gatekeep(image_bytes: bytes) -> Tuple[GatekeeperResult, Optional[Image.Image]]`: Validates format, resolution, blur, and foliage ratio.
- `enhance(pil_image: Image.Image) -> Tuple[bytes, torch.Tensor, np.ndarray]`: Applies CLAHE contrast enhancement in LAB color space, resizes to target dimension ($224 \times 224$), and produces dual outputs: clean JPEG bytes + normalized tensor.

### 5.3 `agrisys.agents.disease.client` (`SecureModelEndpointClient`)
- `predict_image(endpoint_url: str, image_bytes: bytes, headers_override: Optional[Dict]) -> List[Dict]`: Sends image bytes to remote API or local container with Bearer auth, timeout (4.0s), retries, and circuit breaker.
- `parse_plantvillage_label(raw_label: str) -> Tuple[str, str]`: Converts labels like `"Tomato___Early_blight"` to `("tomato", "early_blight")`.

### 5.4 `agrisys.agents.disease.registry`
- `BaseDiseaseModelTool`: Abstract base class for model tools (`name`, `crops_supported`, `role`, `weight`, `predict()`).
- `EndpointDiseaseModelTool`: Concrete implementation delegating inference to an HTTP/REST endpoint.
- `MODEL_REGISTRY`: Central dictionary catalog of all registered model tools.
- `get_disease_tool(tool_name: str) -> BaseDiseaseModelTool`: Registry factory method.
- `register_disease_tool(tool_name: str, tool: BaseDiseaseModelTool) -> None`: Dynamic tool registration (OCP).

### 5.5 `agrisys.agents.disease.crop_detector` (`CropDetector`)
- `detect_crop(image_bytes: bytes, user_query: Optional[str] = None) -> CropDetectionResult`: Identifies crop using vision endpoint and executes multi-modal text hint consensus resolution.
- `extract_crop_hint(text: Optional[str]) -> Optional[str]`: Regex extractor for crop names and aliases across English and Hindi.

### 5.6 `agrisys.agents.disease.ensemble` (`WeightedEnsembleVoter`)
- `vote(predictions: List[DiseasePrediction], weights: List[float], threshold: float = 0.70) -> DiseasePrediction`: Consolidates multi-model predictions via weighted voting and computes average confidence.
- `SEVERITY_LEVELS`: Mapping of severity index (0–5) to clinical stages and descriptions.

### 5.7 `agrisys.agents.disease.model_router` (`CropModelRouter`)
- `get_candidate_tools(crop: str) -> List[BaseDiseaseModelTool]`: Discovers specialist tools supporting the crop, with fallback to general tools.
- `route_and_predict(crop: str, image_bytes: bytes) -> DiseasePrediction`: Concurrently queries candidate tools via `asyncio.gather` and executes ensemble voting.

### 5.8 `agrisys.xai.gradcam` (`DiseaseGradCAM`)
- `generate_heatmap_overlay(rgb_image_np: np.ndarray, model_tensor: Optional[torch.Tensor] = None, pytorch_model: Optional[Any] = None) -> Tuple[np.ndarray, str]`: Generates visual explainability overlay (tensor Grad-CAM for local models; adaptive lesion contrast segmentation for remote APIs) and saves artifact to `data/artifacts/`.

### 5.9 `agrisys.agents.disease.chain` (`AgriChainDiagnosticEngine`)
- `generate_diagnostic_report(...) -> DiseaseDiagnosticReport`: Synthesizes full diagnostic advisory by bridging diagnosed crop and disease with Stage 1's `RetrievalPipeline` to inject verified ICAR/FAO fungicides, dosages, and severity-specific action guidelines.

### 5.10 `agrisys.agents.disease.node` (`DiseaseAgent` & `disease_agent_node`)
- `diagnose(image_bytes: bytes, user_query: Optional[str] = None, language: str = "en") -> Dict[str, Any]`: Master diagnostic workflow.
- `disease_agent_node(state: Dict[str, Any]) -> Dict[str, Any]`: LangGraph node function reading state inputs, diagnosing leaf, and writing results back to state.

---

## 6. How to Add a New Model Tool to AgriSys

To register a new model (e.g. your custom fine-tuned model uploaded to Hugging Face or hosted in a local container):

### Step 1: Add Entry to `MODEL_REGISTRY`
Open [agrisys/agents/disease/registry.py](file:///d:/Study%20Material/Computer%20Science%20and%20Application/Projects/AgriSys/agrisys/agents/disease/registry.py) and add:

```python
MODEL_REGISTRY["my_custom_model"] = {
    "endpoint_url": "https://api-inference.huggingface.co/models/your-username/your-model-name",
    "crops": ["cotton", "mustard"],      # Crops supported by this model
    "role": "crop_specific_disease",     # or 'general_disease' or 'crop_detection'
    "weight": 0.50,                      # Accuracy weight in ensemble voting
    "enabled": True,
}
```

### Step 2: (Optional) Set Environment Key
If your model requires authentication, ensure `HF_TOKEN` is set in your `.env` file:
```env
HF_TOKEN=hf_your_token_here
```

No code modifications to the agent, preprocessor, router, or LangGraph state machine are needed.

---

## 7. Automated Test Verification Results

All 15 Stage 2 tests executed and passed:
```powershell
pytest tests/test_preprocessing.py tests/test_model_registry.py tests/test_disease_agent.py -v
```

```
tests/test_preprocessing.py::test_valid_leaf_image_accepted PASSED       [  6%]
tests/test_preprocessing.py::test_non_plant_image_rejected_by_gatekeeper PASSED [ 13%]
tests/test_preprocessing.py::test_low_resolution_image_rejected PASSED   [ 20%]
tests/test_preprocessing.py::test_blurry_image_rejected PASSED           [ 26%]
tests/test_preprocessing.py::test_invalid_bytes_handled PASSED           [ 33%]
tests/test_model_registry.py::test_plantvillage_label_parsing PASSED     [ 40%]
tests/test_model_registry.py::test_model_registry_entries PASSED         [ 46%]
tests/test_model_registry.py::test_endpoint_tool_prediction PASSED       [ 53%]
tests/test_model_registry.py::test_open_closed_principle_extension PASSED [ 60%]
tests/test_disease_agent.py::test_crop_detector_consensus PASSED         [ 66%]
tests/test_disease_agent.py::test_crop_model_router PASSED               [ 73%]
tests/test_disease_agent.py::test_weighted_ensemble_voter PASSED         [ 80%]
tests/test_disease_agent.py::test_disease_gradcam_overlay PASSED         [ 86%]
tests/test_disease_agent.py::test_disease_agent_end_to_end_diagnosis PASSED [ 93%]
tests/test_disease_agent.py::test_langgraph_disease_agent_node PASSED    [100%]

============================= 15 passed in 4.56s ==============================
```

**Total Project Test Suite: 38 out of 38 tests passing across Stage 1 and Stage 2.**
