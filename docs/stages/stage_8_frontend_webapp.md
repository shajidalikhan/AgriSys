# Stage 8: Interactive Frontend Web Application & PWA

## 1. Overview & Objectives
Stage 8 implements the interactive farmer-facing user interface and Progressive Web App (PWA) specified in **§1.4, §17.1, §17.2, §17.3, and §17.4** of `AgriSys_Technical_Documentation.docx`.

### Key Objectives:
1. **Modern Agricultural Design System**:
   - Built with **React 18 + Vite + Tailwind CSS**.
   - Curated agricultural color palette featuring emerald green (`#10b981`), deep forest green (`#064e3b`), amber alert accents (`#f59e0b`), dark mode glassmorphism panels, and Google Fonts typography (Inter & Outfit).
2. **WebSocket Streaming Advisory Chat (§1.4)**:
   - Connects to `ws://localhost:8000/ws/chat`.
   - Real-time token streaming with stage indicators (`retrieving_knowledge`, `generating_advisory`, `guard_eval`).
   - Verified citation cards linking to grounded ICAR documents.
   - Hallucination Guard score badge (Grounding Confidence $\ge 70\%$).
   - Built-in spoken voice audio playback.
3. **Computer Vision Disease Diagnosis Panel (§4, §5)**:
   - Drag-and-drop leaf photograph uploader with preview.
   - Grad-CAM heatmap overlay toggle highlighting infected leaf attention regions.
   - Disease classification report, severity rating, and integrated IPM chemical + organic bio-control treatment tables.
4. **Soil Health Card & Fertilizer Dosing Panel (§6, §10)**:
   - Interactive sliders for Nitrogen, Phosphorus, Potassium, Soil pH, Electrical Conductivity, and Moisture.
   - Real-time ICAR Soil Health Card status rating badges (Low, Medium, High).
   - Commercial fertilizer dosing calculator (exact kg/ha and kg/acre of Urea 46% N, DAP, and MOP).
   - Split application schedule (Basal dose at planting, 1st and 2nd top dressing).
5. **APMC Mandi Market Intelligence Panel (§9)**:
   - Commodity search across 9+ Indian crops and distance radius slider ($0 - 150\text{ km}$).
   - Mandi cards ranked by **Net Realized Profit** after freight transportation deductions ($₹4/\text{km}/\text{tonne}$).
   - Recharts 7-day price trajectory line chart with CACP Minimum Support Price (MSP) benchmark line.
   - Actionable **Sell Now** vs **Hold** recommendation banner.
6. **Weather Forecast & FAO-56 Precision Irrigation Panel (§7)**:
   - 7-day meteorological forecast cards (min/max temp, rain probability %, wind speed).
   - Extreme agricultural weather hazard alert banners (Ground frost, heatwave, heavy downpour).
   - FAO-56 Penman-Monteith Evapotranspiration calculation widget: Reference $ET_0$, crop coefficient $K_c$, crop demand $ET_c$, effective rainfall $P_{\text{eff}}$, net irrigation requirement $NIR$, and drip run hours at $4\text{ mm/hr}$.
7. **Multilingual Vernacular Voice Studio (§11)**:
   - Vernacular language switcher: English, Hindi (हिन्दी), Marathi (मराठी), Telugu (తెలుగు), and Tamil (தமிழ்).
   - Live microphone recording button with animated audio waveforms.
   - Speech-to-Text (ASR) transcription with Indic text normalization.
   - Indic Text-to-Speech (TTS) synthesizer with audio playback.
8. **Progressive Web App (PWA) Offline Capabilities (§17.4)**:
   - `manifest.json` for standalone home screen installation.
   - Service worker `sw.js` for caching static assets and enabling offline advisory access.

---

## 2. Directory Structure

```
frontend/
├── index.html                    # SEO & Google Fonts (Inter, Outfit)
├── vite.config.js                # Vite dev server & reverse proxy
├── tailwind.config.js            # Custom agricultural palette & tokens
├── postcss.config.js             # PostCSS Tailwind plugins
├── package.json                  # Dependencies: React 18, Recharts, Lucide
├── public/
│   ├── manifest.json             # PWA Web App Manifest
│   └── sw.js                     # Service Worker for offline caching
└── src/
    ├── main.jsx                  # React DOM & Service Worker registration
    ├── App.jsx                   # Layout, Navbar, Sidebar & Tab Routing
    ├── index.css                 # Tailwind directives, glassmorphism, animations
    ├── context/
    │   └── LanguageContext.jsx   # Vernacular translations & state
    ├── api/
    │   ├── client.js             # REST API client for FastAPI endpoints
    │   └── websocket.js          # Streaming WebSocket client
    └── components/
        ├── layout/
        │   ├── Navbar.jsx        # Branding, connection pill, language selector
        │   └── Sidebar.jsx       # Tab navigation across all agents
        ├── chat/
        │   └── StreamingChat.jsx # WebSocket token streaming with citations
        ├── disease/
        │   └── DiseasePanel.jsx  # Leaf uploader & Grad-CAM viewer
        ├── nutrition/
        │   └── NutritionPanel.jsx# SHC sliders & fertilizer dosing
        ├── market/
        │   └── MarketPanel.jsx   # Mandi ranking & Recharts price trajectory
        ├── weather/
        │   └── WeatherPanel.jsx  # 7-day forecast & FAO-56 irrigation
        └── voice/
            └── VoiceStudio.jsx   # Vernacular ASR recording & TTS playback
```

---

## 3. Build & Compilation Verification

The production bundle was compiled using Vite:

```bash
cd frontend
npm run build
```

**Result**:
- `dist/index.html` (1.23 kB)
- `dist/assets/index-CV0FarLI.css` (24.84 kB)
- `dist/assets/index-Bi45TNAN.js` (600.13 kB)
- **Status**: 0 build errors, 2401 modules transformed in 8.75s.
