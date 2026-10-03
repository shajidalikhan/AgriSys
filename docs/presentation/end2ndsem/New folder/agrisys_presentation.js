const pptxgen = require("pptxgenjs");

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author = "AgriSys Thesis";
pres.title = "Towards a Next-Generation Agricultural Expert System";

// ── Color palette ──────────────────────────────────────────────────────────
const C = {
  darkBg:    "0F2027",   // deep dark teal-black (title/conclusion bg)
  midBg:     "1A3A4A",   // slightly lighter dark
  white:     "FFFFFF",
  offWhite:  "F4F6F8",
  purple:    "534AB7",
  purpleL:   "EEEDFE",
  teal:      "0F6E56",
  tealL:     "E1F5EE",
  coral:     "993C1D",
  coralL:    "FAECE7",
  amber:     "854F0B",
  amberL:    "FAEEDA",
  green:     "3B6D11",
  greenL:    "EAF3DE",
  blue:      "185FA5",
  blueL:     "E6F1FB",
  red:       "A32D2D",
  redL:      "FCEBEB",
  gray:      "5F5E5A",
  grayL:     "F1EFE8",
  muted:     "64748B",
  border:    "E2E8F0",
  accent:    "02C39A",   // mint accent
  accentD:   "0F6E56",
};

// ── Helpers ────────────────────────────────────────────────────────────────
const W = 10, H = 5.625;

function addTag(slide, text, color, x, y) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 1.5, h: 0.26, fill: { color }, line: { color, width: 0 }, rectRadius: 0.1 });
  slide.addText(text.toUpperCase(), { x, y, w: 1.5, h: 0.26, fontSize: 8, bold: true, color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
}

function slideNum(slide, n, total) {
  slide.addText(`${n} / ${total}`, { x: 9.2, y: 5.35, w: 0.7, h: 0.2, fontSize: 9, color: C.muted, align: "right" });
}

function sectionTitle(slide, title, sub) {
  slide.addText(title, { x: 0.5, y: 0.35, w: 9, h: 0.7, fontSize: 30, bold: true, color: C.darkBg, fontFace: "Calibri" });
  if (sub) slide.addText(sub, { x: 0.5, y: 1.05, w: 9, h: 0.28, fontSize: 13, color: C.muted, fontFace: "Calibri" });
}

function accentBar(slide) {
  slide.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 0.3, w: 0.06, h: 0.75, fill: { color: C.purple }, line: { color: C.purple } });
}

function card(slide, x, y, w, h, fillColor) {
  slide.addShape(pres.shapes.RECTANGLE, { x, y, w, h, fill: { color: fillColor || C.offWhite }, line: { color: C.border, width: 0.5 } });
}

const TOTAL = 10;

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 1 — TITLE
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.darkBg };

  // Left accent strip
  s.addShape(pres.shapes.RECTANGLE, { x: 0, y: 0, w: 0.12, h: H, fill: { color: C.accent }, line: { color: C.accent } });

  // Top label
  s.addText("THESIS PRESENTATION", { x: 0.4, y: 0.3, w: 6, h: 0.3, fontSize: 9, color: C.accent, bold: true, charSpacing: 4, fontFace: "Calibri" });

  // Main title
  s.addText("Towards a Next-Generation\nAgricultural Expert System", {
    x: 0.4, y: 0.7, w: 6.6, h: 1.8, fontSize: 34, bold: true, color: C.white, fontFace: "Calibri", lineSpacingMultiple: 1.15
  });

  // Sub
  s.addText("A Multimodal Conversational Approach", {
    x: 0.4, y: 2.5, w: 6.6, h: 0.4, fontSize: 17, color: C.accent, fontFace: "Calibri", italic: true
  });

  // Divider
  s.addShape(pres.shapes.LINE, { x: 0.4, y: 3.05, w: 6.3, h: 0, line: { color: "334455", width: 0.75 } });

  // Meta
  s.addText([
    { text: "Domain: ", options: { color: C.muted } },
    { text: "Artificial Intelligence · Precision Agriculture · NLP", options: { color: "AABBCC" } }
  ], { x: 0.4, y: 3.15, w: 6.6, h: 0.25, fontSize: 11, fontFace: "Calibri" });
  s.addText([
    { text: "Target: ", options: { color: C.muted } },
    { text: "Multi-crop India · Web platform deployment", options: { color: "AABBCC" } }
  ], { x: 0.4, y: 3.42, w: 6.6, h: 0.25, fontSize: 11, fontFace: "Calibri" });
  s.addText("Supervisor: [Name]   |   Department of Computer Science   |   [Institution]   |   2024–25", {
    x: 0.4, y: 3.75, w: 6.6, h: 0.22, fontSize: 10, color: C.muted, fontFace: "Calibri"
  });

  // Right stat cards
  const stats = [
    { num: "146M+", lbl: "Smallholder farm\nhouseholds in India" },
    { num: "₹1.5L cr", lbl: "Annual crop loss from\ndisease & poor advisory" },
    { num: "<30%", lbl: "Farmers with access\nto agronomist advice" },
  ];
  stats.forEach((st, i) => {
    const y = 0.5 + i * 1.65;
    s.addShape(pres.shapes.RECTANGLE, { x: 7.4, y, w: 2.2, h: 1.45, fill: { color: "132535" }, line: { color: "1E4060", width: 0.5 } });
    s.addText(st.num, { x: 7.4, y: y + 0.15, w: 2.2, h: 0.65, fontSize: 28, bold: true, color: C.accent, align: "center", fontFace: "Calibri" });
    s.addText(st.lbl, { x: 7.4, y: y + 0.78, w: 2.2, h: 0.55, fontSize: 10, color: "8AADCC", align: "center", fontFace: "Calibri" });
  });

  slideNum(s, 1, TOTAL);
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 2 — INTRODUCTION
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  accentBar(s);
  sectionTitle(s, "The agricultural advisory crisis in India", "Why existing systems fail the 146 million farmers who need them most");
  addTag(s, "Introduction", C.purple, 8.0, 0.38);

  // Left bullets
  const bullets = [
    "India has 1 agricultural extension worker per 1,000+ farmers — advice is inaccessible at scale  (ICAR, 2023)",
    "Crop disease is the leading cause of yield loss; most farmers diagnose by eye, often too late  (FAO, 2022)",
    "Soil nutrient deficiencies cost 20–30% of potential yield, yet soil testing adoption is <15%  (NABARD, 2023)",
    "Mandi price information asymmetry causes farmers to sell 30–40% below optimal price  (eNAM, 2023)",
    "Existing AI tools are English-only, text-only, or require stable internet — excluding most users",
  ];
  bullets.forEach((b, i) => {
    s.addText([
      { text: "  " + b, options: { color: "1E293B", fontSize: 11.5, fontFace: "Calibri" } }
    ], { x: 0.65, y: 1.4 + i * 0.46, w: 5.3, h: 0.42, bullet: false });
    s.addShape(pres.shapes.OVAL, { x: 0.65, y: 1.52 + i * 0.46, w: 0.1, h: 0.1, fill: { color: C.purple }, line: { color: C.purple } });
  });

  // Right cards
  // "What AI can offer"
  s.addShape(pres.shapes.RECTANGLE, { x: 6.15, y: 1.35, w: 3.6, h: 1.85, fill: { color: C.purpleL }, line: { color: C.purple, width: 0.5 } });
  s.addText("What AI can offer", { x: 6.25, y: 1.42, w: 3.4, h: 0.28, fontSize: 11, bold: true, color: C.purple, fontFace: "Calibri" });
  const aiOffers = ["24/7 voice advisory in Hindi & regional languages", "Instant leaf-image disease diagnosis + XAI", "Soil-sensor nutrition recommendations", "Live mandi price advisory with sell/hold guidance"];
  aiOffers.forEach((t, i) => {
    s.addText("→  " + t, { x: 6.25, y: 1.73 + i * 0.35, w: 3.4, h: 0.32, fontSize: 10, color: C.purple, fontFace: "Calibri" });
  });

  // "Why now?"
  s.addShape(pres.shapes.RECTANGLE, { x: 6.15, y: 3.3, w: 3.6, h: 1.8, fill: { color: C.tealL }, line: { color: C.teal, width: 0.5 } });
  s.addText("Why now?", { x: 6.25, y: 3.37, w: 3.4, h: 0.28, fontSize: 11, bold: true, color: C.teal, fontFace: "Calibri" });
  const why = ["LLMs (GPT-4o, Gemini 1.5) ready for domain advisory", "VLMs achieve >90% on PlantVillage disease datasets", "Bhashini API enables 10+ Indic language ASR/TTS", "RAG eliminates hallucination in knowledge-grounded advisory"];
  why.forEach((t, i) => {
    s.addText("→  " + t, { x: 6.25, y: 3.68 + i * 0.34, w: 3.4, h: 0.32, fontSize: 10, color: C.teal, fontFace: "Calibri" });
  });

  slideNum(s, 2, TOTAL);
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 3 — RELATED WORK
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  accentBar(s);
  sectionTitle(s, "Landscape of prior research", "Six research streams this thesis builds upon and extends");
  addTag(s, "Related Work", C.teal, 7.9, 0.38);

  const streams = [
    { n: "S1", title: "Multimodal conversational AI", body: "MIRAGE (2025) · AgMMU benchmark · Farmer.Chat (ACM 2024)\n→ Benchmarks & deployed systems; lack unified advisory in one session", c: C.purple, cl: C.purpleL },
    { n: "S2", title: "LLMs & RAG for farm advisory", body: "AgroLLM · AgriLLM · J. Agri. Engineering RAG (2026)\n→ Strong text-only RAG accuracy; no image or voice modality", c: C.teal, cl: C.tealL },
    { n: "S3", title: "VLMs for plant disease", body: "LLMI-CDP (Sci. Reports 2025) · AgriChain · Self-consistency VLMs\n→ 91–94% leaf accuracy; no farmer-facing conversational UI", c: C.coral, cl: C.coralL },
    { n: "S4", title: "Explainable AI in agriculture", body: "XAI-CROP (Springer NCA 2024) · Grad-CAM plant disease\n→ XAI per task in isolation; never surfaced to farmers conversationally", c: C.amber, cl: C.amberL },
    { n: "S5", title: "Speech & multilingual NLP", body: "Indic ASR benchmark (arXiv 2025) · IndicBERT · Bhashini\n→ Voice interfaces exist; not connected to agronomic advisory end-to-end", c: C.green, cl: C.greenL },
    { n: "S6", title: "Agentic & expert systems", body: "CropiBot (Sci. Reports 2026) · Transformer survey (EAAI 2024)\n→ Single-agent chatbots; lack specialist routing & cross-modal fusion", c: C.blue, cl: C.blueL },
  ];

  const cols = [0.5, 3.55, 6.6];
  const rows = [1.35, 3.0];
  streams.forEach((st, i) => {
    const x = cols[i % 3], y = rows[Math.floor(i / 3)];
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 2.9, h: 1.5, fill: { color: st.cl }, line: { color: st.c, width: 0.5 } });
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.5, h: 1.5, fill: { color: st.c }, line: { color: st.c } });
    s.addText(st.n, { x, y, w: 0.5, h: 1.5, fontSize: 13, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: "Calibri" });
    s.addText(st.title, { x: x + 0.58, y: y + 0.08, w: 2.25, h: 0.3, fontSize: 11, bold: true, color: st.c, fontFace: "Calibri" });
    s.addText(st.body, { x: x + 0.58, y: y + 0.38, w: 2.25, h: 1.05, fontSize: 9.5, color: "334455", fontFace: "Calibri", lineSpacingMultiple: 1.2 });
  });

  slideNum(s, 3, TOTAL);
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 4 — RESEARCH GAP
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  accentBar(s);
  sectionTitle(s, "What no existing system has built", "Five specific gaps identified across the literature survey");
  addTag(s, "Research Gap", C.coral, 7.9, 0.38);

  const gaps = [
    { n: "G1", t: "No unified multimodal advisory session", b: "No system combines disease diagnosis (image), nutrition advisory (sensor), crop recommendation, weather, and live market data in one conversational turn" },
    { n: "G2", t: "No cross-modal sensor–image nutrition fusion in a dialogue", b: "Sensor fusion papers work offline; no conversational interface wraps leaf image + soil NPK data for farmer-facing nutrition advice" },
    { n: "G3", t: "XAI not rendered to farmer in any system", b: "XAI-CROP and LLMI-CDP generate SHAP/Grad-CAM as research output — never surfaced as a visual explanation to the farmer in a web UI" },
    { n: "G4", t: "No end-to-end Indic voice-to-advisory pipeline", b: "Indic ASR benchmark achieves WER 16% for Hindi, but no system connects it to an agronomic RAG advisory backend with TTS response" },
    { n: "G5", t: "Live mandi price never co-delivered with agronomic advice", b: "Market agents and agronomic agents exist in silos across all surveyed literature — no system answers both in the same conversational response" },
  ];

  gaps.forEach((g, i) => {
    const y = 1.32 + i * 0.84;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y, w: 9.2, h: 0.78, fill: { color: i % 2 === 0 ? C.offWhite : "FBFAFF" }, line: { color: C.border, width: 0.5 } });
    s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y, w: 0.55, h: 0.78, fill: { color: C.coral }, line: { color: C.coral } });
    s.addText(g.n, { x: 0.5, y, w: 0.55, h: 0.78, fontSize: 12, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: "Calibri" });
    s.addText(g.t, { x: 1.12, y: y + 0.06, w: 8.4, h: 0.28, fontSize: 11.5, bold: true, color: "1E293B", fontFace: "Calibri" });
    s.addText(g.b, { x: 1.12, y: y + 0.36, w: 8.4, h: 0.38, fontSize: 10, color: C.muted, fontFace: "Calibri" });
  });

  slideNum(s, 4, TOTAL);
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 5 — PROBLEM STATEMENT
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  accentBar(s);
  sectionTitle(s, "Formal problem statement", "");
  addTag(s, "Problem Statement", C.red, 7.5, 0.38);

  // PS box
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.15, w: 9.2, h: 1.25, fill: { color: "F8F7FF" }, line: { color: C.purple, width: 1.5 } });
  s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y: 1.15, w: 0.08, h: 1.25, fill: { color: C.purple }, line: { color: C.purple } });
  s.addText(
    "Indian smallholder farmers face simultaneous, interdependent challenges — crop disease, nutrient deficiency, uncertain crop selection, irrigation, and price realisation — that no single AI model addresses. Existing expert systems are text-only, single-agent, single-language, and non-explainable. No current system accepts voice in Hindi, diagnoses disease from leaf images, integrates soil sensor data, and advises on live mandi prices within a single conversational turn — with explanations grounded in verified agronomic knowledge sources.",
    { x: 0.68, y: 1.2, w: 8.9, h: 1.15, fontSize: 11.5, color: "1E293B", fontFace: "Calibri", lineSpacingMultiple: 1.35 }
  );

  // Two column cards
  const challenges = ["Modality heterogeneity — voice, image, text, sensor, price are structurally different inputs", "Domain depth — agriculture needs expert-level, crop- and region-specific knowledge", "Hallucination risk — LLMs fabricate crop-care advice with dangerous confidence", "Language barrier — Indic ASR accuracy still sub-optimal for agricultural vocabulary", "Trust — farmers reject advice they cannot understand or verify"];
  const constraints = ["Must work on commodity Android device + 3G connection", "Response time < 4 seconds (cloud) · < 8 seconds (PWA offline cache)", "Knowledge grounded exclusively in ICAR, FAO, CGIAR verified sources", "Explainability must be farmer-readable — visual, not numerical", "Multi-crop: wheat, rice, maize, cotton, tomato, potato + more"];

  [
    { title: "Challenges to overcome", items: challenges, x: 0.5, c: C.coral, cl: C.coralL },
    { title: "Solution constraints", items: constraints, x: 5.1, c: C.green, cl: C.greenL },
  ].forEach(col => {
    s.addShape(pres.shapes.RECTANGLE, { x: col.x, y: 2.55, w: 4.45, h: 2.85, fill: { color: col.cl }, line: { color: col.c, width: 0.5 } });
    s.addText(col.title, { x: col.x + 0.15, y: 2.62, w: 4.1, h: 0.3, fontSize: 11, bold: true, color: col.c, fontFace: "Calibri" });
    col.items.forEach((item, i) => {
      s.addText("→  " + item, { x: col.x + 0.15, y: 2.96 + i * 0.46, w: 4.2, h: 0.42, fontSize: 10, color: "1E293B", fontFace: "Calibri" });
    });
  });

  slideNum(s, 5, TOTAL);
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 6 — OBJECTIVES
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  accentBar(s);
  sectionTitle(s, "Research objectives", "Eight measurable objectives mapping to identified research gaps");
  addTag(s, "Objectives", C.green, 8.2, 0.38);

  const objs = [
    { id: "O1", label: "Architecture", body: "Design LangGraph multi-agent orchestrator — intent classifier, parallel dispatch, Redis multi-turn memory", c: C.purple },
    { id: "O2", label: "Disease", body: "Fine-tune ViT-L/16 + LoRA on PlantVillage/PlantDoc/IP102 — >90% top-1 accuracy, 200+ diseases, 50+ crops", c: C.coral },
    { id: "O3", label: "Nutrition", body: "Cross-modal MLP fusing ResNet-50 leaf features with NPK/pH/EC sensor data — fertiliser dose recommendation", c: C.amber },
    { id: "O4", label: "RAG", body: "Hallucination-resistant RAG: 250k+ ICAR/FAO chunks in Qdrant, hybrid BM25+dense, LLM-as-judge confidence gating", c: C.teal },
    { id: "O5", label: "XAI", body: "Surface Grad-CAM heatmaps (disease) and SHAP bar charts (crop rec) in React PWA — farmer-facing, not research output", c: C.green },
    { id: "O6", label: "Voice", body: "Whisper large-v3 (Indic fine-tuned) ASR → Bhashini TTS — WER <20% Hindi, <30% regional, end-to-end <4s", c: C.blue },
    { id: "O7", label: "Market", body: "Agmarknet + eNAM live pull (15-min), Prophet 7-day forecast — sell/hold/transport advisory co-delivered with agronomy", c: C.gray },
    { id: "O8", label: "Evaluation", body: "Benchmark on MIRAGE, AgMMU; validate with 10 ICAR-certified agronomists on 200 real farmer queries (Likert ≥4.0/5.0)", c: C.purple },
  ];

  objs.forEach((o, i) => {
    const col = i % 2, row = Math.floor(i / 2);
    const x = col === 0 ? 0.5 : 5.2;
    const y = 1.35 + row * 1.05;
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 4.55, h: 0.92, fill: { color: C.offWhite }, line: { color: C.border, width: 0.5 } });
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 0.7, h: 0.92, fill: { color: o.c }, line: { color: o.c } });
    s.addText(o.id, { x, y, w: 0.7, h: 0.52, fontSize: 13, bold: true, color: "FFFFFF", align: "center", valign: "middle", fontFace: "Calibri" });
    s.addText(o.label.toUpperCase(), { x, y: y + 0.54, w: 0.7, h: 0.36, fontSize: 7, bold: true, color: "FFFFFF", align: "center", valign: "top", fontFace: "Calibri", charSpacing: 1 });
    s.addText(o.body, { x: x + 0.78, y: y + 0.06, w: 3.65, h: 0.8, fontSize: 10, color: "1E293B", fontFace: "Calibri", lineSpacingMultiple: 1.25 });
  });

  slideNum(s, 6, TOTAL);
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 7 — APPROACH (ARCHITECTURE)
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  accentBar(s);
  sectionTitle(s, "System approach — six-layer architecture", "Each layer addresses specific research objectives and gaps");
  addTag(s, "Approach", C.amber, 8.2, 0.38);

  const layers = [
    { label: "L1 · Input", detail: "Text · Voice (Whisper ASR) · Image (leaf/field) · Sensor (NPK/pH) · Live price (Agmarknet/eNAM)  ·  10 Indic languages via Bhashini", c: C.teal, cl: C.tealL },
    { label: "L2 · Preprocess", detail: "Parallel: ASR → Hindi norm · Image QA (BRISQUE) + 448×448 resize · Sensor calibration · Price anomaly filter", c: C.purple, cl: C.purpleL },
    { label: "L3 · Orchestrator", detail: "GPT-4o backbone + fine-tuned BERT intent classifier · LangGraph parallel dispatch · Redis session memory · confidence-gated response merge", c: C.purple, cl: "EEEDFE" },
    { label: "L4 · Agents ×5", detail: "[Disease: ViT-L LoRA + Grad-CAM]  [Nutrition: ResNet-50 + sensor MLP + SHAP]  [Crop: XGBoost + SHAP]  [Weather: LSTM + IMD]  [Market: Agmarknet + Prophet]", c: C.coral, cl: C.coralL },
    { label: "L5 · Knowledge", detail: "E5-large embeddings · Qdrant vector store · Hybrid BM25+dense · Cross-encoder rerank · HyDE query expand · Qwen3 LLM-as-judge · 250k+ ICAR/FAO/CGIAR chunks", c: C.green, cl: C.greenL },
    { label: "L6 · Output + XAI", detail: "React 18 PWA · Grad-CAM overlay on leaf image · SHAP charts · Bhashini TTS Hindi/regional · District map · Price trend chart · FastAPI WebSocket", c: C.blue, cl: C.blueL },
  ];

  layers.forEach((l, i) => {
    const y = 1.32 + i * 0.71;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y, w: 9.2, h: 0.63, fill: { color: l.cl }, line: { color: l.c, width: 0.5 } });
    s.addText(l.label, { x: 0.65, y, w: 1.45, h: 0.63, fontSize: 10.5, bold: true, color: l.c, valign: "middle", fontFace: "Calibri" });
    s.addShape(pres.shapes.LINE, { x: 2.1, y: y + 0.08, w: 0, h: 0.47, line: { color: l.c, width: 0.5 } });
    s.addText(l.detail, { x: 2.2, y, w: 7.3, h: 0.63, fontSize: 10, color: "1E293B", valign: "middle", fontFace: "Calibri" });
  });

  slideNum(s, 7, TOTAL);
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 8 — EVALUATION FRAMEWORK
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  accentBar(s);
  sectionTitle(s, "Evaluation framework", "Quantitative metrics per component before claiming contribution");
  addTag(s, "Evaluation", C.gray, 8.2, 0.38);

  const evals = [
    { title: "Disease diagnostic (O2)", lines: ["Dataset: PlantVillage test + PlantDoc", "Metrics: Top-1 Acc · F1 macro · AUC-ROC", "Target: >90% top-1 · 200+ diseases", "XAI: Grad-CAM IoU vs. expert annotation"], c: C.coral, cl: C.coralL },
    { title: "Nutrition agent (O3)", lines: ["Dataset: ICAR soil health card DB + synthetic sensor", "Metrics: RMSE on fertiliser dose · F1 deficiency class", "Target: RMSE <5 kg/ha · F1 >0.85", "XAI: SHAP stability score across runs"], c: C.amber, cl: C.amberL },
    { title: "Crop recommendation (O4)", lines: ["Dataset: ICRISAT district yield + IMD climate", "Metrics: Top-3 Acc · agronomist agreement %", "Target: Top-3 acc >85% · agreement >80%", "XAI: SHAP feature rank correlation"], c: C.green, cl: C.greenL },
    { title: "RAG quality (O4)", lines: ["Framework: RAGAS evaluation suite", "Metrics: Faithfulness · context relevance · answer rel.", "Target: Faithfulness >0.88 · hallucination <5%", "Benchmark: MIRAGE · AgMMU eval sets"], c: C.purple, cl: C.purpleL },
    { title: "ASR / voice pipeline (O6)", lines: ["Dataset: Indic ASR benchmark (10,934 recordings)", "Metric: WER per language", "Target: WER <20% Hindi · <30% Indic regional", "End-to-end: voice → response latency <4 s"], c: C.blue, cl: C.blueL },
    { title: "Expert agronomist panel (O8)", lines: ["Panel: 10 ICAR-certified agronomists", "Metric: 5-point Likert correctness + clarity", "Target: Mean correctness >4.0 / 5.0", "Blind eval: 200 real farmer queries"], c: C.gray, cl: C.grayL },
  ];

  evals.forEach((e, i) => {
    const col = i % 3, row = Math.floor(i / 3);
    const x = 0.5 + col * 3.12, y = 1.3 + row * 2.1;
    s.addShape(pres.shapes.RECTANGLE, { x, y, w: 3.0, h: 1.95, fill: { color: e.cl }, line: { color: e.c, width: 0.5 } });
    s.addText(e.title, { x: x + 0.12, y: y + 0.1, w: 2.78, h: 0.3, fontSize: 11, bold: true, color: e.c, fontFace: "Calibri" });
    e.lines.forEach((l, li) => {
      s.addText(l, { x: x + 0.12, y: y + 0.42 + li * 0.36, w: 2.78, h: 0.33, fontSize: 9.5, color: "1E293B", fontFace: "Calibri" });
    });
  });

  s.addText("Ablation: 5-agent vs. single-agent baseline · RAG vs. no-RAG · XAI rendered vs. not · voice vs. text-only", {
    x: 0.5, y: 5.3, w: 9.2, h: 0.22, fontSize: 9.5, color: C.muted, italic: true, fontFace: "Calibri"
  });

  slideNum(s, 8, TOTAL);
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 9 — CONTRIBUTIONS + ROADMAP
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.darkBg };

  s.addText("Research contributions & timeline", { x: 0.5, y: 0.28, w: 9, h: 0.55, fontSize: 26, bold: true, color: C.white, fontFace: "Calibri" });
  s.addText("Five novel contributions over prior art — and the 12-month delivery plan", { x: 0.5, y: 0.85, w: 9, h: 0.28, fontSize: 12, color: "8AADCC", fontFace: "Calibri" });
  addTag(s, "Contributions", C.accent, 7.7, 0.3);

  const contribs = [
    { n: "C1", t: "First multi-agent system routing to five specialist domain models", s: "Closes G1 · novel over: Farmer.Chat, AgroLLM, CropiBot (all single-model)" },
    { n: "C2", t: "Cross-modal leaf image + soil sensor fusion for nutrition in a dialogue", s: "Closes G2 · novel over: all surveyed nutrition papers (offline inference only)" },
    { n: "C3", t: "Farmer-facing Grad-CAM heatmaps and SHAP charts rendered in web UI", s: "Closes G3 · novel over: XAI-CROP (Springer), LLMI-CDP — both log XAI internally" },
    { n: "C4", t: "End-to-end Indic voice pipeline: Whisper ASR → Hindi RAG → Bhashini TTS", s: "Closes G4 · novel over: Indic ASR benchmark paper (no advisory backend)" },
    { n: "C5", t: "Live mandi price co-delivered with agronomic advice in one conversational turn", s: "Closes G5 · novel over: all surveyed papers — no prior system attempts this" },
  ];

  contribs.forEach((c, i) => {
    const y = 1.2 + i * 0.77;
    s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y, w: 6.8, h: 0.68, fill: { color: "132535" }, line: { color: "1E4060", width: 0.5 } });
    s.addShape(pres.shapes.RECTANGLE, { x: 0.5, y, w: 0.55, h: 0.68, fill: { color: C.accent }, line: { color: C.accent } });
    s.addText(c.n, { x: 0.5, y, w: 0.55, h: 0.68, fontSize: 12, bold: true, color: C.darkBg, align: "center", valign: "middle", fontFace: "Calibri" });
    s.addText(c.t, { x: 1.13, y: y + 0.05, w: 6.1, h: 0.3, fontSize: 11.5, bold: true, color: C.white, fontFace: "Calibri" });
    s.addText(c.s, { x: 1.13, y: y + 0.36, w: 6.1, h: 0.28, fontSize: 9.5, color: "8AADCC", fontFace: "Calibri" });
  });

  // Timeline
  const phases = [
    { phase: "M1–3", detail: "Data collection\nKnowledge base\nRAG pipeline" },
    { phase: "M4–6", detail: "Agent model\ntraining · Fusion\nmodule · ASR" },
    { phase: "M7–9", detail: "Orchestrator\nWeb PWA\nIntegration test" },
    { phase: "M10–12", detail: "Evaluation\nExpert panel\nThesis writing" },
  ];

  phases.forEach((p, i) => {
    const x = 7.55 + 0.0;
    const y = 1.2 + i * 0.77;
    s.addShape(pres.shapes.RECTANGLE, { x: 7.55, y, w: 2.1, h: 0.68, fill: { color: "132535" }, line: { color: "1E4060", width: 0.5 } });
    s.addText(p.phase, { x: 7.57, y: y + 0.04, w: 2.06, h: 0.28, fontSize: 12, bold: true, color: C.accent, align: "center", fontFace: "Calibri" });
    s.addText(p.detail, { x: 7.57, y: y + 0.3, w: 2.06, h: 0.36, fontSize: 9, color: "8AADCC", align: "center", fontFace: "Calibri" });
  });

  slideNum(s, 9, TOTAL);
}

// ══════════════════════════════════════════════════════════════════════════
// SLIDE 10 — REFERENCES
// ══════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  accentBar(s);
  sectionTitle(s, "References", "Key papers cited in this research");
  addTag(s, "References", C.purple, 8.2, 0.38);

  const refs = [
    "[1] MIRAGE: A Benchmark for Multimodal Information-Seeking and Reasoning in Agricultural Expert-Guided Conversations. arXiv, 2025.",
    "[2] A Multimodal Conversational Assistant for Agricultural Plots from Geospatial Open Data. arXiv, 2025.",
    "[3] AgMMU: Agricultural Multimodal Understanding and Reasoning Benchmark. arXiv, April 2025.",
    "[4] Farmer.Chat: Scaling AI-Powered Agricultural Services for Smallholder Farmers. ACM, 2024. arXiv:2409.08916.",
    "[5] LLMI-CDP: A Large Language Model for Multimodal Identification of Crop Diseases and Pests. Scientific Reports (Nature), 2025.",
    "[6] AgriChain: Visually-Grounded Expert-Verified Reasoning for Agricultural VLMs. arXiv, 2025.",
    "[7] Enhancing Crop Recommendation with XAI (XAI-CROP). Neural Computing and Applications, Springer, 2024.",
    "[8] RAG-Based LLM Advisory Framework for Farmers. Journal of Agricultural Engineering, 2026.",
    "[9] Agentic AI-Driven Autonomous Decision Support System for Smart Agriculture (CropiBot). Scientific Reports, 2026.",
    "[10] Benchmarking ASR for Indian Languages in Agricultural Contexts. arXiv, 2025.",
    "[11] Harnessing Large Vision and Language Models in Agriculture: A Review. Frontiers in Plant Science, 2025.",
    "[12] Recent Advances in Transformer Technology for Agriculture: A Survey. Engineering Applications of AI, Elsevier, 2024.",
    "[13] Self-Consistency in VLMs for Precision Agriculture. arXiv, 2025.",
    "[14] Overcoming LLM Challenges using RAG-Driven Precision in Coffee Leaf Disease Remediation. IEEE Conference, 2024.",
    "[15] Deep Learning and Computer Vision in Plant Disease Detection. Artificial Intelligence Review, Springer, 2025.",
  ];

  // Two columns
  const half = Math.ceil(refs.length / 2);
  const col1 = refs.slice(0, half);
  const col2 = refs.slice(half);

  [[col1, 0.5], [col2, 5.1]].forEach(([col, x]) => {
    col.forEach((r, i) => {
      s.addText(r, {
        x, y: 1.32 + i * 0.53, w: 4.45, h: 0.5,
        fontSize: 9, color: "1E293B", fontFace: "Calibri", lineSpacingMultiple: 1.2
      });
      s.addShape(pres.shapes.LINE, { x, y: 1.85 + i * 0.53, w: 4.45, h: 0, line: { color: C.border, width: 0.3 } });
    });
  });

  slideNum(s, 10, TOTAL);
}

// Write file
pres.writeFile({ fileName: "AgriSys_Thesis_Presentation.pptx" })
  .then(() => console.log("DONE"))
  .catch(e => { console.error(e); process.exit(1); });
