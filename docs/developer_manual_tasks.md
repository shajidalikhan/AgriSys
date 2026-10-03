# AgriSys Developer Manual Action & Prerequisites Guide

This document is the authoritative reference for all **human actions, external API registrations, dataset downloads, manual GPU training runs, and expert validation tasks** required to build, operate, and validate AgriSys across all 9 build stages.

---

## Quick Reference: Action Checklist by Stage

| Stage / Module | Category | Task | External Portal / Dependency | Priority |
| :--- | :--- | :--- | :--- | :--- |
| **Global / Setup** | Environment | Fill secrets in `.env` | Local `.env` from `.env.example` | **CRITICAL** |
| **Global / Infra** | Containers | Launch Docker infrastructure | `docker compose up -d` | **HIGH** |
| **Stage 1: Foundation** | API Keys | OpenAI / Groq / OpenRouter API keys | Provider dashboards | **HIGH** |
| **Stage 1: RAG Corpus** | Data | Download ICAR Package of Practices PDFs | [krishi.icar.gov.in](https://krishi.icar.gov.in) | **MEDIUM** |
| **Stage 1: RAG Corpus** | Data | Clean Kisan Call Centre (KCC) CSVs | [data.gov.in](https://data.gov.in) | **MEDIUM** |
| **Stage 2: Disease** | Model Endpoints | Verify HuggingFace endpoint keys & labels | HuggingFace Inference API | **MEDIUM** |
| **Stage 2: Disease** | Compute (Opt.) | Fine-tune ViT-L/16 + LoRA checkpoint | A10G / A100 GPU (Colab/Cloud) | **LOW** |
| **Stage 3: Crop Rec** | Data & Models | Train XGBoost & Random Forest models | `scripts/training/train_crop_models.py` | **DONE (Built-in)** |
| **Stage 4: Nutrition** | Data | Synthesize ICAR SHC sensor pairs | `scripts/data/generate_sensor_pairs.py` | **DONE (Built-in)** |
| **Stage 4: Nutrition** | Data (Opt.) | Download Mendeley banana/coffee deficiency sets | [data.mendeley.com](https://data.mendeley.com) | **LOW** |
| **Stage 5: Market** | API Registration | Agmarknet / OGD API Key | [data.gov.in/apis](https://data.gov.in/apis) | **HIGH** |
| **Stage 5: Market** | API Registration | eNAM live feed access (Optional/Institutional) | [enam.gov.in](https://enam.gov.in) | **LOW** |
| **Stage 5: Market** | Data Update | Annual CACP MSP table update | [cacp.dacnet.nic.in](https://cacp.dacnet.nic.in) | **LOW (Annual)** |
| **Stage 6: Weather** | API Registration | IMD Weather API (Institutional) | [api.imd.gov.in](https://api.imd.gov.in) | **MEDIUM** (3-5 days) |
| **Stage 7: Voice** | API Registration | Bhashini ULCA API (Indian ASR/TTS) | [ulca.bhashini.gov.in](https://ulca.bhashini.gov.in) | **HIGH** (2-3 days) |
| **Stage 7: Voice** | Compute (Opt.) | Fine-tune Whisper on Indic languages | A10G GPU / Google Colab | **LOW** |
| **Stage 8: Frontend** | Build | Install Node packages & Vite PWA build | Node.js `>=18.x`, `npm install` | **MEDIUM** |
| **Stage 9: Evaluation** | Observability | Configure Langfuse tracing & Grafana | Langfuse Cloud / Docker | **MEDIUM** |
| **Stage 9: Validation** | Human Evaluation | ICAR Agronomist panel review & Hindi audit | 10 certified agronomists | **FINAL STEP** |

---

## 1. External API Registrations & Credentials

These accounts must be created manually because government portals and AI vendors require human identity verification, institutional emails, or payment billing profiles.

### 1.1 IMD Weather API (India Meteorological Department)
- **Portal**: [https://api.imd.gov.in/public/index.php](https://api.imd.gov.in/public/index.php)
- **Purpose**: Official district-level 7-day weather forecasts and rainfall alerts (Stage 6).
- **Step-by-Step Instructions**:
  1. Visit the portal and click **New User Registration**.
  2. Register using an **institutional or academic email address** (IMD frequently rejects generic `@gmail.com` accounts).
  3. Under *Intended Use*, select **Academic / Research / Agricultural Non-Commercial**.
  4. Wait **3 to 5 business days** for administrative approval and API key issuance.
  5. Copy your API Key into `.env`:
     ```env
     IMD_API_KEY="your_imd_api_key_here"
     ```
  > [!TIP]
  > **Development Fallback**: During local development while waiting for IMD key approval, AgriSys automatically falls back to **Open-Meteo** (no API key required).

### 1.2 Agmarknet / Open Government Data (OGD) API
- **Portal**: [https://data.gov.in/apis](https://data.gov.in/apis)
- **Purpose**: Daily APMC mandi price and commodity arrival feeds across Indian states (Stage 5).
- **Step-by-Step Instructions**:
  1. Create an account on [data.gov.in](https://data.gov.in).
  2. Verify your mobile number and email via OTP.
  3. Navigate to **APIs** $\to$ Search for **Current Daily Price of Various Commodities (Agmarknet)**.
  4. Click **Request API Key / Subscribe**. Approval is usually instantaneous.
  5. Add to `.env`:
     ```env
     AGMARKNET_API_KEY="your_data_gov_in_api_key"
     ```

### 1.3 Bhashini ULCA API (Ministry of Electronics & IT)
- **Portal**: [https://ulca.bhashini.gov.in/](https://ulca.bhashini.gov.in/)
- **Purpose**: Indian language Automated Speech Recognition (ASR) and Text-to-Speech (TTS) in Hindi, Punjabi, Marathi, Telugu, Tamil, etc. (Stage 7).
- **Step-by-Step Instructions**:
  1. Register an account on the ULCA Bhashini portal.
  2. Submit an API access request specifying your research/developer application.
  3. Retrieve your `UserID`, `APIKey`, and `PipelineID`.
  4. Add to `.env`:
     ```env
     BHASHINI_USER_ID="your_user_id"
     BHASHINI_API_KEY="your_bhashini_key"
     BHASHINI_PIPELINE_ID="your_pipeline_id"
     ```

### 1.4 LLM & Vision Provider Accounts
- **OpenAI**: [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys) (For GPT-4o / embeddings).
- **Groq Cloud**: [https://console.groq.com/keys](https://console.groq.com/keys) (Ultra-fast Llama 3.3 streaming inference).
- **OpenRouter**: [https://openrouter.ai/keys](https://openrouter.ai/keys) (Multi-model gateway fallback).
- **HuggingFace**: [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) (Bearer token for disease vision endpoints).

---

## 2. Infrastructure Setup (Docker Services)

AgriSys uses containerized microservices for storage, vector indexing, caching, and observability.

### Step-by-Step Instructions:
1. Ensure Docker Desktop is installed and running on your machine.
2. From the project root (`AgriSys/`), start all supporting background services:
   ```bash
   docker compose up -d qdrant redis postgres minio
   ```
3. Verify running containers:
   ```bash
   docker ps
   ```
   - **Qdrant Vector DB**: `http://localhost:6333/dashboard`
   - **Redis Cache**: `localhost:6379`
   - **MinIO S3 Storage**: `http://localhost:9001` (Default User: `minioadmin`, Pass: `minioadmin`)
   - **PostgreSQL**: `localhost:5432`

---

## 3. Data Collection & Preprocessing Tasks

Government agronomic manuals and raw transcripts must be curated and preprocessed.

### 3.1 ICAR Package of Practices (PoP) Ingestion
- **Source**: [https://krishi.icar.gov.in](https://krishi.icar.gov.in)
- **Instructions**:
  1. Download official Package of Practices PDFs for key regional crops (Wheat, Rice, Tomato, Potato, Cotton, Sugarcane, Maize, Pulses).
  2. Save the downloaded PDFs into `data/raw/icar_pop/`.
  3. Ingest documents into the Qdrant vector database using the Stage 1 ingestion pipeline:
     ```bash
     python -m agrisys.rag.ingestion.pipeline --source data/raw/icar_pop/ --collection agrisys_knowledge
     ```

### 3.2 Kisan Call Centre (KCC) Transcript Cleaning
- **Source**: [data.gov.in/resource/kisan-call-centre](https://data.gov.in)
- **Instructions**:
  1. Download historical KCC farmer query-response CSV datasets.
  2. Run the cleaning script to strip Personal Identifiable Information (PII), standardize Hindi Devnagari character encoding, and extract Q&A pairs:
     ```bash
     python scripts/data/clean_kcc.py --input data/raw/kcc_raw.csv --output data/processed/kcc_cleaned.csv
     ```

### 3.3 Annual CACP Minimum Support Price (MSP) Update
- **Source**: [https://cacp.dacnet.nic.in](https://cacp.dacnet.nic.in)
- **Instructions**:
  - The Commission for Agricultural Costs and Prices releases official MSP rates before the Kharif and Rabi sowing seasons.
  - Review [agrisys/agents/market/msp_database.py](file:///d:/Study%20Material/Computer%20Science%20and%20Application/Projects/AgriSys/agrisys/agents/market/msp_database.py) once per year to update the base rates (₹/quintal) for new fiscal cycles.

---

## 4. Optional GPU Model Fine-Tuning Tasks

While AgriSys includes production-grade ML models (XGBoost, Random Forest, ResNet-50 fusion, and remote HF endpoints), fine-tuning custom local weights provides higher domain specialization:

### 4.1 Fine-Tuning Whisper for Regional Indian Agricultural Accents
- **Hardware**: NVIDIA A10G (24GB VRAM) or Google Colab A100.
- **Dataset**: AI4Bharat IndicSUPERB + Bhashini ULCA speech subsets.
- **Command**:
  ```bash
  python scripts/training/finetune_whisper.py --language hi --epochs 5 --batch-size 16
  ```
- **Output Checkpoint**: `models/voice/whisper_indic_agri/`

### 4.2 Fine-Tuning ViT-L/16 + LoRA for Crop Leaf Pathology
- **Hardware**: NVIDIA A10G / A100 (~8 hours compute).
- **Dataset**: Combined PlantVillage (87k) + PlantDoc (2.5k field photos) + IP102 pest dataset.
- **Command**:
  ```bash
  python scripts/training/finetune_vit_lora.py --base google/vit-large-patch16-224 --lora-r 16
  ```
- **Output Checkpoint**: `models/disease/vit_lora/`

---

## 5. Human-in-the-Loop Expert Validation (§16.4)

Before final field deployment to farming communities, rigorous human expert validation is mandatory:

### 5.1 Plant Pathologist / ICAR Model Verification
1. Sample 100 high-resolution field leaf images from actual local farm visits.
2. Provide images to a certified plant pathologist or ICAR Krishi Vigyan Kendra (KVK) scientist.
3. Record their ground truth diagnoses in `evaluation/disease_expert_eval.xlsx`.
4. Run the model inference comparison script and verify accuracy $\ge 85\%$:
   ```bash
   python evaluation/verify_disease_expert.py
   ```

### 5.2 Agronomist Advisory Quality Panel
1. Recruit 5–10 ICAR-certified agronomy extension officers.
2. Present 100 randomly sampled generated treatment advisories (combining chemical dosage, organic alternatives, and split schedules).
3. Officers score each advisory on a 1-5 Likert scale for:
   - **Safety & Toxicity** (correct pesticide withholding periods)
   - **Cost Effectiveness**
   - **Practical Feasibility**
4. Any advisory flagged for chemical overdosing or phytotoxicity must be logged and used to update guardrail rules.

### 5.3 Native Hindi & Regional Language Review
1. Have a native speaker from a rural agricultural background review 50 synthesized Hindi responses.
2. Confirm that terminology uses standard local terms (e.g. *दीमक*, *उकठा रोग*, *पत्ती धब्बा*, *यूरिया छिड़काव*) rather than awkward machine translations.
3. Verify that voice TTS outputs pronounce numbers, units (*क्विंटल*, *एकड़*), and chemical names accurately.

---

## 6. Production Deployment & Telemetry Verification (§18)

### 6.1 Launching the Full Stack
Run the production multi-container stack via Docker Compose:
```bash
docker compose up -d --build
```
Verify all 9 containers are healthy:
```bash
docker compose ps
```

### 6.2 Monitoring & Telemetry Dashboards
1. **Prometheus Metrics**:
   - Access Prometheus UI at `http://localhost:9090`.
   - Query metrics: `agrisys_requests_total`, `agrisys_request_duration_seconds`, `agrisys_agent_invocations_total`, `agrisys_hallucination_guard_score`.
2. **Grafana Dashboards**:
   - Access Grafana at `http://localhost:3001` (Default credentials: `admin` / `agrisys_grafana_admin`).
   - Add Prometheus as a Data Source (`http://prometheus:9090`).
   - Import the AgriSys System Dashboard to monitor P99 query latency, LLM token consumption, Hallucination Guard score trends, and active mobile users.
3. **Langfuse LLM Tracing**:
   - Access Langfuse at `http://localhost:3000`.
   - Track live agent execution traces, prompt versions, and token costs per turn.
