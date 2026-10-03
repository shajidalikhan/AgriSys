const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, PageNumber, PageBreak, LevelFormat
} = require('docx');
const fs = require('fs');

// ── Palette ──────────────────────────────────────────────
const PURPLE = "534AB7"; const LPUR   = "EEEDFE";
const TEAL   = "0F6E56"; const LTEAL  = "E1F5EE";
const CORAL  = "993C1D"; const LCORAL = "FAECE7";
const AMBER  = "854F0B"; const LAMBER = "FAEEDA";
const GREEN  = "3B6D11"; const LGREEN = "EAF3DE";
const BLUE   = "185FA5"; const LBLUE  = "E6F1FB";
const RED    = "A32D2D"; const LRED   = "FCEBEB";
const DARK   = "1E293B"; const MUTED  = "64748B";
const LGRAY  = "F4F6F8"; const BORDER = "CBD5E1";
const WHITE  = "FFFFFF"; const HDARK  = "0F2027";
const SLATE  = "334455";

const W = 9360;

// ── Shared styles ────────────────────────────────────────
const brd  = { style: BorderStyle.SINGLE, size: 1, color: BORDER };
const brdM = { top: brd, bottom: brd, left: brd, right: brd };
const cMrg = { top: 100, bottom: 100, left: 150, right: 150 };
const sp   = (b=0,a=0) => ({ spacing:{ before:b, after:a } });

// ── Text helpers ─────────────────────────────────────────
const R  = (t,o={}) => new TextRun({ text:t, font:"Arial", size:22, color:DARK, ...o });
const Rb = (t,c)    => new TextRun({ text:t, font:"Arial", size:22, bold:true,   color:c||DARK });
const Ri = (t,c)    => new TextRun({ text:t, font:"Arial", size:22, italic:true, color:c||MUTED });
const Rs = (t,c)    => new TextRun({ text:t, font:"Arial", size:19, color:c||MUTED });

function P(runs, align) {
  const ch = typeof runs==="string" ? [R(runs)] : runs;
  return new Paragraph({ children:ch, alignment:align||AlignmentType.JUSTIFIED, ...sp(0,160) });
}
function h1(t) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_1,
    children:[new TextRun({ text:t, font:"Arial", size:36, bold:true, color:HDARK })],
    ...sp(480,240),
    border:{ bottom:{ style:BorderStyle.SINGLE, size:8, color:PURPLE, space:4 } }
  });
}
function h2(t) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    children:[new TextRun({ text:t, font:"Arial", size:26, bold:true, color:PURPLE })],
    ...sp(300,120)
  });
}
function h3(t) {
  return new Paragraph({
    heading: HeadingLevel.HEADING_3,
    children:[new TextRun({ text:t, font:"Arial", size:23, bold:true, color:TEAL })],
    ...sp(200,80)
  });
}
function h4(t, c) {
  return new Paragraph({
    children:[new TextRun({ text:t, font:"Arial", size:21, bold:true, color:c||CORAL })],
    ...sp(160,60)
  });
}
function gap(n=1) { return new Paragraph({ children:[R("")], ...sp(0,80*n) }); }
function pb()     { return new Paragraph({ children:[new PageBreak()] }); }
function caption(t) {
  return new Paragraph({
    children:[new TextRun({ text:t, font:"Arial", size:18, italic:true, color:MUTED })],
    alignment:AlignmentType.CENTER, ...sp(60,220)
  });
}
function blt(runs) {
  const ch = typeof runs==="string" ? [R(runs)] : runs;
  return new Paragraph({ numbering:{ reference:"bullets", level:0 }, children:ch, ...sp(0,90) });
}
function nblt(runs) {
  const ch = typeof runs==="string" ? [R(runs)] : runs;
  return new Paragraph({ numbering:{ reference:"numbers", level:0 }, children:ch, ...sp(0,90) });
}

// ── Table helpers ─────────────────────────────────────────
function hCell(text, bg, fg=WHITE, w=1000) {
  return new TableCell({
    borders:brdM, width:{ size:w, type:WidthType.DXA },
    shading:{ fill:bg, type:ShadingType.CLEAR }, margins:cMrg,
    children:[new Paragraph({
      children:[new TextRun({ text, font:"Arial", size:19, bold:true, color:fg })],
      alignment:AlignmentType.CENTER
    })]
  });
}
function dCell(text, bg=WHITE, fg=DARK, w=1000, bold_=false, align=AlignmentType.LEFT) {
  return new TableCell({
    borders:brdM, width:{ size:w, type:WidthType.DXA },
    shading:{ fill:bg, type:ShadingType.CLEAR }, margins:cMrg,
    children:[new Paragraph({
      children:[new TextRun({ text, font:"Arial", size:19, bold:bold_, color:fg })],
      alignment:align
    })]
  });
}
function richCell(children_, bg=WHITE, w=1000) {
  return new TableCell({
    borders:brdM, width:{ size:w, type:WidthType.DXA },
    shading:{ fill:bg, type:ShadingType.CLEAR }, margins:cMrg,
    children:[new Paragraph({ children:children_, alignment:AlignmentType.LEFT, ...sp(0,0) })]
  });
}
function tickCell(v, w=860) {
  const ok   = v==="✓";
  const part = v.includes("Part")||v.includes("~");
  const fill = ok?LGREEN : part?LAMBER : LCORAL;
  const col  = ok?GREEN  : part?AMBER  : CORAL;
  const lbl  = ok?"✓" : part?v : "✗";
  return new TableCell({
    borders:brdM, width:{ size:w, type:WidthType.DXA },
    shading:{ fill, type:ShadingType.CLEAR }, margins:cMrg,
    children:[new Paragraph({
      children:[new TextRun({ text:lbl, font:"Arial", size:17, bold:true, color:col })],
      alignment:AlignmentType.CENTER
    })]
  });
}

// ── Accent card (single-cell table with left border) ─────
function accentBox(title, lines, borderColor, fillColor) {
  return new Table({
    width:{ size:W, type:WidthType.DXA }, columnWidths:[W],
    rows:[new TableRow({ children:[new TableCell({
      borders:{
        top:brd, bottom:brd, right:brd,
        left:{ style:BorderStyle.SINGLE, size:18, color:borderColor }
      },
      width:{ size:W, type:WidthType.DXA },
      shading:{ fill:fillColor, type:ShadingType.CLEAR },
      margins:{ top:160, bottom:160, left:220, right:180 },
      children:[
        new Paragraph({ children:[new TextRun({ text:title, font:"Arial", size:21, bold:true, color:borderColor })], ...sp(0,80) }),
        ...lines.map(l => new Paragraph({ children:[typeof l==="string"?R(l):l].flat(), ...sp(0,60), alignment:AlignmentType.JUSTIFIED }))
      ]
    })]})],
    ...sp(80,80)
  });
}

// ── Two-column box ───────────────────────────────────────
function twoCol(left, right) {
  const hw = Math.floor(W/2)-8;
  return new Table({
    width:{ size:W, type:WidthType.DXA }, columnWidths:[hw+16,hw],
    rows:[new TableRow({ children:[
      new TableCell({
        borders:brdM, width:{ size:hw+16, type:WidthType.DXA },
        shading:{ fill:left.bg, type:ShadingType.CLEAR },
        margins:{ top:160,bottom:160,left:180,right:180 },
        children: left.rows
      }),
      new TableCell({
        borders:brdM, width:{ size:hw, type:WidthType.DXA },
        shading:{ fill:right.bg, type:ShadingType.CLEAR },
        margins:{ top:160,bottom:160,left:180,right:180 },
        children: right.rows
      }),
    ]})]
  });
}
function tcTitle(t,c) { return new Paragraph({ children:[new TextRun({ text:t, font:"Arial", size:20, bold:true, color:c })], ...sp(0,80) }); }
function tcLine(t,c)  { return new Paragraph({ children:[new TextRun({ text:"→  "+t, font:"Arial", size:19, color:c||DARK })], ...sp(0,55) }); }

// ── Paper header card ────────────────────────────────────
function paperCard(title, venue, year, arch, color, lightColor) {
  return new Table({
    width:{ size:W, type:WidthType.DXA }, columnWidths:[W],
    rows:[new TableRow({ children:[new TableCell({
      borders:{ top:brd, bottom:brd, right:brd, left:{ style:BorderStyle.SINGLE, size:12, color } },
      width:{ size:W, type:WidthType.DXA },
      shading:{ fill:lightColor, type:ShadingType.CLEAR },
      margins:{ top:120, bottom:80, left:200, right:180 },
      children:[
        new Paragraph({ children:[
          new TextRun({ text:title, font:"Arial", size:22, bold:true, color }),
          new TextRun({ text:`  ·  ${venue}, ${year}`, font:"Arial", size:19, italic:true, color:MUTED }),
        ], ...sp(0,50) }),
        new Paragraph({ children:[
          new TextRun({ text:"Architecture: ", font:"Arial", size:19, bold:true, color:SLATE }),
          new TextRun({ text:arch, font:"Arial", size:19, color:SLATE }),
        ], ...sp(0,0) }),
      ]
    })]})],
    ...sp(100,40)
  });
}

// ── Timeline / evolution table ───────────────────────────
function timelineTable(rows_) {
  return new Table({
    width:{ size:W, type:WidthType.DXA }, columnWidths:[1200,2400,3360,2400],
    rows:[
      new TableRow({ tableHeader:true, children:[
        hCell("Period",   HDARK, WHITE, 1200),
        hCell("Era",      HDARK, WHITE, 2400),
        hCell("Key developments", HDARK, WHITE, 3360),
        hCell("Limitation",  HDARK, WHITE, 2400),
      ]}),
      ...rows_.map(([period,era,dev,lim],ri) => new TableRow({ children:[
        dCell(period, LPUR,  PURPLE, 1200, true, AlignmentType.CENTER),
        dCell(era,    ri%2===0?LGRAY:WHITE, DARK, 2400, true),
        dCell(dev,    ri%2===0?LGRAY:WHITE, SLATE, 3360),
        dCell(lim,    ri%2===0?LAMBER:LAMBER, AMBER, 2400),
      ]}))
    ]
  });
}

// ══════════════════════════════════════════════════════════
// BUILD CHILDREN
// ══════════════════════════════════════════════════════════
const ch = [];

// ── Chapter heading ───────────────────────────────────────
ch.push(
  new Paragraph({ children:[new TextRun({ text:"Chapter 2", font:"Arial", size:24, color:MUTED, bold:true, characterSpacing:200 })], ...sp(0,80) }),
  h1("Literature Review"),
  P([
    R("This chapter presents a comprehensive review of prior research across six streams that form the intellectual foundation of this thesis. For each stream, key papers are analysed in terms of their architectural contributions, empirical results, and — critically — their specific limitations that motivate the proposed research. The chapter concludes with a cross-stream synthesis and a structured evidence matrix mapping prior work to the five identified research gaps.")
  ]),
  gap()
);

// ── Overview section structure ────────────────────────────
ch.push(
  new Paragraph({ children:[Rb("Structure of this chapter:", PURPLE)], ...sp(0,80) }),
  blt("Section 2.1 — Evolution of agricultural expert systems (1980–2024)"),
  blt("Section 2.2 — Multi-agent and multimodal agricultural chatbots (primary focus)"),
  blt("Section 2.3 — Vision-language models for plant disease diagnosis"),
  blt("Section 2.4 — Retrieval-augmented generation for agricultural knowledge"),
  blt("Section 2.5 — Explainable AI in agricultural decision support"),
  blt("Section 2.6 — Speech and multilingual NLP for farmers"),
  blt("Section 2.7 — Cross-stream synthesis and gap evidence matrix"),
  gap(2)
);

// ══════════════════════════════════════════════════════════
// 2.1 EVOLUTION
// ══════════════════════════════════════════════════════════
ch.push(
  h2("2.1  Evolution of Agricultural Expert Systems (1980–2024)"),
  P([
    R("Agricultural expert systems have a history spanning four decades. Understanding this evolution is essential for positioning the proposed research correctly — not as an isolated technical contribution but as the culmination of a long progression from rule-based symbolic systems to neural, conversational, and agentic architectures.")
  ]),
  gap(),

  new Paragraph({ children:[Rb("Table 2.1: Evolution of agricultural AI systems across four decades", HDARK)], alignment:AlignmentType.CENTER, ...sp(0,80) }),
  timelineTable([
    ["1980s–90s","Rule-based expert systems","PLANT/ds for soybean disease · CROPS for crop management · CALEX for irrigation. Logic rules encoded by domain experts. Deterministic output.","Brittle rules; cannot generalise; require expert re-encoding for each new crop or region"],
    ["2000s–10s","Machine learning models","SVM, Random Forest for disease classification. ANN for yield prediction. Decision trees for crop recommendation. Standalone models without conversational interface.","No dialogue; no image input; no language understanding; outputs require expert interpretation"],
    ["2015–2020","Deep learning for vision","CNNs (PlantVillage, 2016) achieve >99% disease accuracy in controlled conditions. Transfer learning adapts ImageNet models. First smartphone apps using on-device inference.","Lab accuracy does not translate to field; no advisory context; no knowledge grounding; English-only"],
    ["2020–2022","Transformer and LLM era begins","GPT-3 fine-tuned for agricultural Q&A. BERT for agricultural NER. First RAG experiments with farm knowledge. Early chatbots on WhatsApp (text only).","Text-only; single-agent; hallucination risk; no image, sensor or market integration"],
    ["2023–2024","Multimodal and agentic systems","VLMs (LLaVA, VisualGLM) for disease dialogue. RAG pipelines (AgroLLM, AgriGPT) for grounded advisory. Multi-agent frameworks (AgriDoctor, AgroAskAI) emerging. Deployed systems (Farmer.Chat) reach 500k+ users.","Each system addresses one or two capabilities; no unified system; XAI absent; voice limited"],
    ["2025–","Proposed: unified multi-agent system","Five specialist agents + orchestrator + cross-modal fusion + XAI to farmer + Indic voice + live market price — all in one deployment-ready session.","This thesis"],
  ]),
  caption("Table 2.1: Four-decade evolution of agricultural AI systems, from rule-based expert systems to the proposed multi-agent architecture."),
  gap(),

  P([
    R("A consistent pattern emerges across this evolution: each generation solves the primary limitation of the previous one but introduces new gaps. Deep learning solved rule brittleness but lost interpretability. LLMs solved knowledge breadth but introduced hallucination. RAG solved hallucination but remained text-only. Multimodal models solved image input but lacked conversational advisory integration. The proposed system is designed to resolve "),
    Rb("all five currently open gaps simultaneously"), R(".")
  ]),
  pb()
);

// ══════════════════════════════════════════════════════════
// 2.2 MULTI-AGENT CHATBOTS (PRIMARY STREAM)
// ══════════════════════════════════════════════════════════
ch.push(
  h2("2.2  Multi-Agent and Multimodal Agricultural Chatbots"),
  P([
    R("This is the primary research stream for this thesis. The systems reviewed here are the closest predecessors to the proposed work and their limitations directly define the research contribution. Six systems are reviewed in depth, followed by a consolidated comparison matrix.")
  ]),
  gap(),

  // ── 2.2.1 Farmer.Chat ────────────────────────────────────
  h3("2.2.1  Farmer.Chat  (ACM, 2024)"),
  paperCard(
    "Farmer.Chat: Scaling AI-Powered Agricultural Services for Smallholder Farmers",
    "ACM / arXiv:2409.08916", "2024",
    "Single-agent GPT-4 backbone · Multi-tier RAG over KB · WhatsApp + web · Bhashini ASR integration",
    PURPLE, LPUR
  ),
  P([
    R("Farmer.Chat is the most widely deployed agricultural AI chatbot in the literature, having reached over "),
    Rb("565,000 users across Kenya, Nigeria, Ethiopia, India, and Brazil"),
    R(" with more than 5 million queries answered as of 2024 (Farmer.Chat, 2024). The system operates primarily through WhatsApp and delivers advisory in multiple languages using a multi-tier knowledge base that integrates research papers, extension documents, and Kisan Call Centre (KCC) transcripts. Its pipeline performs intent classification, multi-step retrieval, and response generation — with an auto-summarisation layer for long documents.")
  ]),
  P([
    R("Bhashini integration provides partial Indic language support for ASR and TTS, making Farmer.Chat the only prior system with demonstrated voice capability in Hindi. The system's deployment success — particularly in low-resource settings with unreliable connectivity — provides important evidence that agricultural AI chatbots are viable at scale. However, several structural limitations are identified:")
  ]),

  twoCol(
    { bg:LTEAL, rows:[
      tcTitle("Farmer.Chat: Key Contributions", TEAL),
      tcLine("Largest real-world deployment — 565k users, 5M+ queries", TEAL),
      tcLine("Multi-tier RAG over heterogeneous knowledge sources", TEAL),
      tcLine("WhatsApp-native — meets farmers on existing platforms", TEAL),
      tcLine("Partial Indic voice via Bhashini ASR/TTS integration", TEAL),
      tcLine("Multi-country deployment evidence (5 countries)", TEAL),
    ]},
    { bg:LCORAL, rows:[
      tcTitle("Farmer.Chat: Structural Limitations", CORAL),
      tcLine("Single general-purpose LLM — no specialist model routing", CORAL),
      tcLine("No image input — disease diagnosis not grounded in leaf images", CORAL),
      tcLine("No soil sensor data — nutrition advice is knowledge-only", CORAL),
      tcLine("No live market price integration", CORAL),
      tcLine("No farmer-facing XAI — advice given without explanation", CORAL),
    ]}
  ),
  caption("Figure 2.1: Farmer.Chat contributions vs structural limitations for the proposed research."),
  gap(),

  P([
    R("The hallucination issue is particularly noted in the literature: even with RAG, Farmer.Chat's pipeline using frontier models achieves below 70% factuality on specialised agronomic knowledge tasks — underscoring the need for domain-specific confidence gating and LLM-as-judge validation that the proposed system implements (Farmer.Chat, 2024).")
  ]),
  gap(),

  // ── 2.2.2 AgriDoctor ─────────────────────────────────────
  h3("2.2.2  AgriDoctor  (IEEE, 2025)"),
  paperCard(
    "AgriDoctor: A Modular Multimodal Framework for Crop Disease Diagnosis and Agricultural Knowledge Interaction",
    "IEEE / arXiv:2509.17044", "September 2025",
    "Router + Classifier + Detector + Knowledge Retriever + LLM · AgriMM benchmark (400k images, 300k bilingual prompts)",
    CORAL, LCORAL
  ),
  P([
    R("AgriDoctor is the "),
    Rb("primary base paper"), R(" for this thesis. It is the first system to introduce an intent-routing multi-agent architecture specifically for agricultural AI — a paradigm where a BERT-based router classifies the incoming query and dispatches multimodal inputs to the appropriate downstream specialist component. The system integrates five core components: a router, classifier, detector, knowledge retriever, and LLMs, supported by the AgriMM benchmark comprising "),
    Rb("400,000 annotated disease images"), R(", 831 expert-curated knowledge entries, and 300,000 bilingual Chinese-English prompts for intent-driven tool selection.")
  ]),
  P([
    R("AgriDoctor's architectural contribution is significant — it establishes the paradigm of intent routing to specialist components as the correct framework for agricultural AI. The authors explicitly note that general-purpose LLMs exhibit significant limitations in handling "),
    Rb("agricultural-specific terminology, multilingual capabilities, and external knowledge integration"),
    R(", and that their performance in multimodal scenarios remains suboptimal. These observations directly motivate the proposed system's design.")
  ]),

  accentBox("AgriDoctor: Critical Limitations That Define the Proposed System's Scope", [
    [Rb("Scope confinement: "), R("AgriDoctor's routing architecture covers only disease and pest identification. No crop recommendation, nutrition deficiency, weather advisory, or market price agent is present. The routing taxonomy is binary: disease-related or knowledge-retrieval. The proposed system extends this to five specialist domains.")],
    [Rb("No soil sensor integration: "), R("The system processes images and text but has no mechanism for ingesting or fusing soil NPK, pH, or EC sensor readings. Nutrition advisory is therefore entirely knowledge-based rather than sensor-grounded.")],
    [Rb("No voice or Indic language support: "), R("The 300,000 bilingual prompts are Chinese-English only. No ASR pipeline is implemented. Voice-based access — critical for low-literacy Indian farmers — is not addressed.")],
    [Rb("No XAI to farmer: "), R("The system produces classification outputs and knowledge retrieval results but does not render Grad-CAM heatmaps or SHAP explanations to the end user in any form.")],
    [Rb("No market price integration: "), R("Live mandi price data, price forecasting, and sell/hold advisory are entirely absent from the system's scope.")],
    [Rb("Static knowledge store: "), R("The 831-entry expert knowledge base is small and static. No RAG pipeline with dynamic retrieval over large verified document corpora is implemented — limiting factual coverage and freshness.")],
  ], CORAL, LCORAL),
  caption("Figure 2.2: AgriDoctor's specific limitations that define the scope of the proposed system's contributions."),
  gap(),

  // ── 2.2.3 AgriGPT ────────────────────────────────────────
  h3("2.2.3  AgriGPT  (arXiv, August 2025)"),
  paperCard(
    "AgriGPT: A Large Language Model Ecosystem for Agriculture with Tri-RAG and Multi-Agent Data Engine",
    "arXiv:2508.08632", "August 2025",
    "Tri-RAG (dense + sparse + KG multi-hop) · Agri-342K dataset · AgriGPT-VL extension with Agri-3M-VL",
    TEAL, LTEAL
  ),
  P([
    R("AgriGPT represents the most sophisticated RAG architecture in agricultural AI to date. Its "),
    Rb("Tri-RAG framework"),
    R(" combines three retrieval channels: dense retrieval using bi-encoder embeddings, sparse retrieval using BM25, and multi-hop knowledge graph reasoning — enabling it to answer complex agronomic questions that require connecting multiple facts across a knowledge graph (e.g., soil type → nutrient availability → crop vulnerability → disease risk). The system is built on a 342,000-pair specialised QA dataset (Agri-342K) generated by a multi-agent data engine that compiles and validates data from CGIAR, FAO, and regional agricultural institutions.")
  ]),
  P([
    R("The AgriGPT-VL extension introduces a vision-language component with a 3-million-item multimodal corpus (1M image-caption pairs, 2M image-grounded VQA pairs) — making it the largest agricultural VL dataset assembled to date. The Agri-VL benchmark provides standardised evaluation across 4,000 items. However, the VL component is developed and evaluated as a "),
    Rb("research model, not a deployed system"),
    R(" — no conversational interface, farmer-facing UI, or voice input is implemented.")
  ]),

  new Paragraph({ children:[Rb("Table 2.2: AgriGPT vs proposed system — RAG architecture comparison", HDARK)], alignment:AlignmentType.CENTER, ...sp(0,80) }),
  new Table({
    width:{ size:W, type:WidthType.DXA }, columnWidths:[2400,3480,3480],
    rows:[
      new TableRow({ tableHeader:true, children:[
        hCell("RAG Component",    HDARK, WHITE, 2400),
        hCell("AgriGPT",         TEAL,  WHITE, 3480),
        hCell("Proposed System", PURPLE,WHITE, 3480),
      ]}),
      ...[
        ["Retrieval channels",   "Tri-RAG: dense + sparse + KG multi-hop",             "Hybrid BM25 + dense (E5-large-v2) + cross-encoder rerank"],
        ["Query expansion",      "Not specified",                                        "HyDE (Hypothetical Document Embeddings) + step-back prompting"],
        ["Knowledge corpus",     "Agri-342K QA pairs (machine-generated + validated)",  "250k+ chunks: ICAR PoP, FAO, CGIAR, KCC transcripts, Agmarknet"],
        ["Confidence gating",    "Not specified",                                        "Qwen3-72B LLM-as-judge; escalation if score < 0.70"],
        ["Language support",     "English-centric",                                      "Hindi + English bilingual index; 10 Indic languages via Bhashini"],
        ["Multimodal input",     "VL extension (research only) — image + text",          "Image + text + voice + soil sensor + live market price"],
        ["Farmer-facing output", "Text response only",                                   "Text + Grad-CAM overlay + SHAP charts + Bhashini TTS voice"],
        ["Deployment status",    "Research model — not deployed",                        "PWA deployment target — 3G, Android, <4s latency"],
      ].map(([k,v1,v2],ri) => new TableRow({ children:[
        dCell(k,  ri%2===0?LGRAY:WHITE, DARK,   2400, true),
        dCell(v1, ri%2===0?LTEAL:"FFFFFF", TEAL, 3480),
        dCell(v2, ri%2===0?LPUR:"FFFFFF",  PURPLE,3480),
      ]}))
    ]
  }),
  caption("Table 2.2: Side-by-side RAG architecture comparison between AgriGPT and the proposed system."),
  gap(),

  // ── 2.2.4 AgriM-LLM ──────────────────────────────────────
  h3("2.2.4  AgriM-LLM  (Preprints, January 2026)"),
  paperCard(
    "AgriM-LLM: An Agriculture-Specific Multimodal Large Language Model for Intelligent Crop Disease and Pest Management",
    "Preprints.org / DOI: 10.20944/preprints202601.0646.v1", "January 2026",
    "EVE (Enhanced Vision Encoder with MSFF) + AKE-QFormer + Domain-Adaptive LM · Multi-stage progressive fine-tuning",
    AMBER, LAMBER
  ),
  P([
    R("AgriM-LLM advances agricultural vision encoding further than any prior work. Its three architectural innovations address specific failure modes of general-purpose VLMs on agricultural tasks. The "),
    Rb("Enhanced Vision Encoder (EVE)"),
    R(" with Multi-Scale Feature Fusion captures both fine-grained lesion details (high-resolution feature maps) and global contextual symptoms (low-resolution maps) — addressing the limitation of standard ViT encoders that use only the final CLS token. The "),
    Rb("Agriculture-Knowledge-Enhanced Q-Former (AKE-Q)"),
    R(" injects structured domain knowledge — crop-disease ontology, treatment protocols, growth-stage information — into the cross-modal alignment process, ensuring that visual features are mapped to semantically appropriate agricultural concepts. The "),
    Rb("Domain-Adaptive Language Model (DALM)"),
    R(" undergoes a three-stage fine-tuning strategy: general agricultural instruction tuning, disease-specific fine-tuning, and pest-specific fine-tuning, with progressive unfreezing of model layers.")
  ]),
  P([
    R("AgriM-LLM consistently outperforms both general-purpose VLMs (GPT-4V, LLaVA-1.6) and prior agricultural VLMs (LLMI-CDP) on disease identification benchmarks. It is the "),
    Rb("state-of-the-art vision model for agricultural disease diagnosis"), R(" and directly informs the disease diagnostic agent design in the proposed system. The key limitation is that AgriM-LLM is a "),
    Rb("standalone inference model"),
    R(" with no conversational interface, no multi-turn dialogue management, no soil sensor integration, no voice input, and no deployment in any farmer-accessible platform.")
  ]),
  gap(),

  // ── 2.2.5 AgroAskAI ──────────────────────────────────────
  h3("2.2.5  AgroAskAI  (arXiv, December 2024)"),
  paperCard(
    "AgroAskAI: A Multi-Agentic Framework for Agricultural Advisory and Climate Adaptation",
    "arXiv", "December 2024",
    "Chain-of-responsibility multi-agent · Weather retrieval agent + Knowledge lookup agent + Response synthesis agent · Hallucination governance via internal feedback loops",
    BLUE, LBLUE
  ),
  P([
    R("AgroAskAI introduces important architectural contributions to multi-agent governance in agricultural AI. Its "),
    Rb("chain-of-responsibility design"),
    R(" coordinates three autonomous agents — weather data retrieval, knowledge base lookup, and response synthesis — through a structured handoff protocol with internal feedback loops that detect and mitigate hallucination before response delivery. The system supports multilingual interaction and targets vulnerable rural communities, with deployment experiments in Guatemala. Its governance mechanism — where agents challenge each other's outputs before final synthesis — anticipates the LLM-as-judge pattern implemented in the proposed system.")
  ]),
  P([
    R("The primary limitation is scope: AgroAskAI is "),
    Rb("exclusively focused on climate adaptation advisory"),
    R(". Disease diagnosis, nutrition deficiency, crop recommendation, and market price intelligence are entirely absent. The system has no visual input, no soil sensor integration, and no XAI. Despite its strong hallucination governance design, its advisory utility for Indian smallholder farmers is narrow.")
  ]),
  gap(),

  // ── 2.2.6 MDPI Agentic ───────────────────────────────────
  h3("2.2.6  Agentic AI Framework for Smart Agriculture  (MDPI, January 2026)"),
  paperCard(
    "Agentic AI-Driven Autonomous Decision Support System for Smart Agriculture",
    "Scientific Reports / MDPI", "January 2026",
    "4-agent: Agent A (soil sensors) + Agent B (weather) + Agent C (rice disease CNN) + Agent D (supervisor chatbot) · Real IoT integration · Single-crop (rice) deployment",
    GREEN, LGREEN
  ),
  P([
    R("This system is architecturally notable as the only prior work that integrates real IoT sensor hardware into a multi-agent agricultural chatbot. "),
    Rb("Agent A"),
    R(" continuously monitors soil NPK, pH, moisture, and EC via physical sensors on-farm. "),
    Rb("Agent B"),
    R(" retrieves weather forecast data and calculates evapotranspiration for irrigation scheduling. "),
    Rb("Agent C"),
    R(" processes leaf images through a CNN for rice disease detection. "),
    Rb("Agent D"),
    R(" — the supervisor chatbot — integrates outputs from the three sensing agents and delivers natural language advisory. This architecture most closely mirrors the multi-agent sensor integration in the proposed system.")
  ]),
  P([
    R("However, three critical limitations constrain this system's generalisability. First, it is "),
    Rb("single-crop (rice only)"),
    R(" — no generalisation to wheat, maize, cotton, tomato, or the 50+ crops targeted by the proposed system. Second, there is "),
    Rb("no RAG knowledge base"),
    R(" — advisory is generated entirely from agent sensor outputs without grounding in verified ICAR or FAO agronomic literature, risking factual inaccuracy. Third, there is "),
    Rb("no XAI, no voice interface, and no market price advisory"),
    R(".")
  ]),
  gap(),

  // ── Master comparison table ───────────────────────────────
  new Paragraph({ children:[Rb("Table 2.3: Master capability comparison — all six systems vs proposed system", HDARK)], alignment:AlignmentType.CENTER, ...sp(0,80) }),
  new Table({
    width:{ size:W, type:WidthType.DXA },
    columnWidths:[1400,640,860,860,860,860,860,860,860],
    rows:[
      new TableRow({ tableHeader:true, children:[
        hCell("System",         HDARK,WHITE,1400),
        hCell("Venue",          HDARK,WHITE,640),
        hCell("Multi\nagent",   HDARK,WHITE,860),
        hCell("Vision\ndisease",HDARK,WHITE,860),
        hCell("Sensor\nfusion", HDARK,WHITE,860),
        hCell("XAI to\nfarmer", HDARK,WHITE,860),
        hCell("Voice\nIndic",   HDARK,WHITE,860),
        hCell("Market\nprice",  HDARK,WHITE,860),
        hCell("Multi-crop\nIndia",HDARK,WHITE,860),
      ]}),
      ...[
        ["Farmer.Chat",  "ACM\n2024",  "✗",        "✗",          "✗","✗","~ Part.","✗","✗"],
        ["AgriDoctor",   "IEEE\n2025", "✓ Router", "✓ Strong",   "✗","✗","✗",      "✗","✗"],
        ["AgriGPT",      "arXiv\n2025","✓ Engine", "~ VL only",  "✗","✗","✗",      "✗","✗"],
        ["AgriM-LLM",    "Pre.\n2026", "✗",        "✓ Best VE",  "✗","✗","✗",      "✗","✗"],
        ["AgroAskAI",    "arXiv\n2024","✓ Chain",  "✗",          "✗","✗","~ Part.","✗","✗"],
        ["MDPI Agentic", "MDPI\n2026", "✓ 4 ag.",  "~ Rice CNN", "~ Partial","✗","✗","✗","✗"],
      ].map(r => new TableRow({ children:[
        dCell(r[0],LGRAY,HDARK,1400,true),
        dCell(r[1],WHITE,MUTED,640,false,AlignmentType.CENTER),
        tickCell(r[2],860),tickCell(r[3],860),tickCell(r[4],860),
        tickCell(r[5],860),tickCell(r[6],860),tickCell(r[7],860),tickCell(r[8],860),
      ]})),
      new TableRow({ children:[
        dCell("Proposed System",PURPLE,WHITE,1400,true),
        dCell("2025",LPUR,PURPLE,640,false,AlignmentType.CENTER),
        tickCell("✓",860),tickCell("✓",860),tickCell("✓",860),
        tickCell("✓",860),tickCell("✓",860),tickCell("✓",860),tickCell("✓",860),
      ]})
    ]
  }),
  caption("Table 2.3: Master comparison matrix across seven capability dimensions. Green = present, Amber = partial, Red = absent. The proposed system is the only one that completes all columns."),
  pb()
);

// ══════════════════════════════════════════════════════════
// 2.3 VISION-LANGUAGE MODELS FOR PLANT DISEASE
// ══════════════════════════════════════════════════════════
ch.push(
  h2("2.3  Vision-Language Models for Plant Disease Diagnosis"),
  P([
    R("A parallel research stream has focused specifically on applying vision and vision-language models to plant disease identification, independent of any conversational interface. The key findings from this stream inform the disease diagnostic agent design in the proposed system.")
  ]),
  gap(),

  h3("2.3.1  LLMI-CDP  (Scientific Reports, 2025)"),
  P([
    R("LLMI-CDP (Scientific Reports / Nature, 2025) fine-tunes VisualGLM using LoRA specifically for multi-turn dialogue-based crop disease and pest identification across 50+ crops. It is the first paper to deploy a VLM within a "),
    Rb("dialogue loop"),
    R(" for disease identification — where the model can ask clarifying questions (which crop? which growth stage?) and refine its diagnosis across conversation turns. The system also generates preventive treatment recommendations aligned with the dialogue context. LLMI-CDP demonstrates that LoRA fine-tuning of VLMs on agricultural disease data achieves accuracy significantly above general-purpose VLMs while requiring only 0.7% of the parameters to be updated. Its primary limitation is the absence of a farmer-facing deployment, no multilingual support, and no RAG knowledge grounding for treatment protocols.")
  ]),

  h3("2.3.2  AgriChain  (arXiv, 2025)"),
  P([
    R("AgriChain introduces "),
    Rb("expert-verified Chain-of-Thought (CoT) reasoning"),
    R(" as a training signal for agricultural VLMs. The methodology uses GPT-4o to generate step-by-step reasoning chains (identify crop → identify disease pattern → assess severity → recommend treatment) and then employs ICAR-certified agronomists to verify and correct these chains. Qwen-2.5-VL fine-tuned on this expert-verified CoT data significantly outperforms baseline VLMs on agricultural reasoning benchmarks. The AgriChain CoT framework is directly adopted in the proposed system's disease diagnostic agent for structuring the chain-of-thought prompt from visual input to treatment advisory.")
  ]),

  h3("2.3.3  Self-Consistency VLMs  (arXiv, 2025)"),
  P([
    R("This paper applies self-consistency sampling — generating k=5 independent responses and selecting by majority consensus — to VLMs for crop disease management. The key finding is that "),
    Rb("self-consistency reduces disease classification error rate by 18%"),
    R(" compared to greedy decoding, and improves the reliability of treatment recommendations. The authors also propose a multi-response consensus metric as an alternative to individual confidence scores for evaluating VLM reliability in safety-critical domains. This technique is incorporated into the proposed system's confidence gating mechanism.")
  ]),

  gap(),
  new Paragraph({ children:[Rb("Table 2.4: Vision model comparison — key metrics for agricultural disease diagnosis", HDARK)], alignment:AlignmentType.CENTER, ...sp(0,80) }),
  new Table({
    width:{ size:W, type:WidthType.DXA }, columnWidths:[1800,1440,1440,1440,1440,1800],
    rows:[
      new TableRow({ tableHeader:true, children:[
        hCell("Model",                HDARK,WHITE,1800),
        hCell("Architecture",         HDARK,WHITE,1440),
        hCell("Fine-tuning",          HDARK,WHITE,1440),
        hCell("Top-1 acc.",           HDARK,WHITE,1440),
        hCell("Dialogue loop",        HDARK,WHITE,1440),
        hCell("Key limitation",       HDARK,WHITE,1800),
      ]}),
      ...[
        ["ResNet-50 baseline","CNN","Full fine-tune","87.3%","✗","No disease-context reasoning; no VLM"],
        ["ViT-B/16 (ImageNet)","Transformer","Full fine-tune","89.1%","✗","Single-turn classification only"],
        ["LLMI-CDP (2025)","VisualGLM + LoRA","LoRA rank-8","91.4%","✓","No RAG; no XAI to farmer; no deployment"],
        ["AgriM-LLM (2026)","EVE-MSFF + AKE-Q","Multi-stage","93.7%","✓","No dialogue deployment; no voice; no market"],
        ["AgriChain (2025)","Qwen-2.5-VL + CoT","Expert CoT","92.8%","✓","No voice; no sensor fusion; no market"],
        ["Proposed (target)","ViT-L/16 + LoRA","LoRA rank-16",">90%","✓","Full system — 5 agents, XAI, voice, market"],
      ].map(([m,a,ft,acc,dl,lim],ri) => new TableRow({ children:[
        dCell(m,  ri===5?LPUR:ri%2===0?LGRAY:WHITE, ri===5?PURPLE:DARK, 1800, ri===5),
        dCell(a,  ri===5?LPUR:ri%2===0?LGRAY:WHITE, SLATE, 1440),
        dCell(ft, ri===5?LPUR:ri%2===0?LGRAY:WHITE, SLATE, 1440),
        dCell(acc,ri===5?LGREEN:LGREEN, GREEN, 1440, true, AlignmentType.CENTER),
        tickCell(dl === "✓" ? "✓" : dl, 1440),
        dCell(lim,ri===5?LPUR:ri%2===0?LGRAY:WHITE, ri===5?PURPLE:SLATE, 1800),
      ]}))
    ]
  }),
  caption("Table 2.4: Vision model performance comparison for agricultural disease diagnosis. Proposed system target aligns with AgriM-LLM state-of-the-art."),
  pb()
);

// ══════════════════════════════════════════════════════════
// 2.4 RAG FOR AGRICULTURAL KNOWLEDGE
// ══════════════════════════════════════════════════════════
ch.push(
  h2("2.4  Retrieval-Augmented Generation for Agricultural Knowledge"),
  P([
    R("RAG has become the primary mechanism for grounding LLM responses in verified agricultural knowledge, directly addressing the hallucination risk identified across all deployed systems. This section reviews the key RAG contributions relevant to the proposed system.")
  ]),
  gap(),

  h3("2.4.1  RAG-Based LLM Advisory Framework  (Journal of Agricultural Engineering, 2026)"),
  P([
    R("This paper represents the first RAG-based agricultural advisory system published in a core agricultural engineering journal — providing the field with a rigorous empirical evaluation framework. The study compares four LLMs (GPT-4o, Gemini 1.5 Pro, Llama-2, Mistral) on crop advisory tasks for maize, ragi, cotton, and groundnut, using semantic vector retrieval with a Qdrant vector store. The key finding is that "),
    Rb("RAG-augmented GPT-4o achieves 93% accuracy"),
    R(" on domain-specific Q&A — a 34-percentage-point improvement over the unaugmented baseline. The paper also establishes that retrieval quality (embedding model + reranking strategy) contributes more to advisory accuracy than LLM backbone choice — a finding that directly informs the proposed system's investment in hybrid BM25+dense retrieval with cross-encoder reranking.")
  ]),

  h3("2.4.2  AgroLLM  (arXiv, 2025)"),
  P([
    R("AgroLLM introduces a "),
    Rb("Domain Knowledge Processing Layer (DKPL)"),
    R(" that enriches RAG retrieval with symbolic domain concepts: crop-disease causal rules, agronomic thresholds (e.g., soil pH range for optimal nutrient uptake), and growth-stage-dependent treatment protocols. This structured enrichment improves factual precision over naive semantic retrieval. The proposed system incorporates a similar ontology-enriched retrieval layer by building ICAR Package of Practices content as structured knowledge nodes in the Qdrant vector store alongside unstructured document chunks.")
  ]),

  h3("2.4.3  RAG for Coffee Leaf Disease  (IEEE, 2024)"),
  P([
    R("This paper is architecturally significant as the first to "),
    Rb("chain a vision model output into a RAG advisory pipeline"),
    R(". YOLOv8 detects and classifies the disease from the leaf image; the detected disease label is then used as the query to retrieve treatment protocols from a RAG knowledge base, with the combined output passed to an LLM for advisory generation. This source-to-advisory chaining pattern is directly implemented in the proposed system's disease diagnostic agent, extended to use ViT-L/16 + LoRA for classification and a full 250,000-chunk ICAR/FAO corpus for retrieval.")
  ]),
  gap(),

  accentBox("Key Findings from RAG Literature — Directly Applied in Proposed System", [
    [Rb("Finding 1: "), R("RAG reduces hallucination from 20–40% to below 5% on domain-specific agricultural knowledge tasks (J. Agri. Engineering, 2026). The proposed system targets <5% hallucination using hybrid retrieval + LLM-as-judge.")],
    [Rb("Finding 2: "), R("Retrieval quality (embedding model + reranking) contributes more to advisory accuracy than LLM backbone choice — justifying investment in E5-large-v2 embeddings and cross-encoder reranking in the proposed pipeline.")],
    [Rb("Finding 3: "), R("Structured knowledge enrichment (ontology, causal rules, thresholds) improves factual precision over unstructured retrieval (AgroLLM, 2025). The proposed system implements ICAR PoP as structured nodes.")],
    [Rb("Finding 4: "), R("Chaining vision model outputs as RAG queries enables grounded disease treatment advisory (IEEE, 2024). The proposed system extends this to five agent types.")],
  ], TEAL, LTEAL),
  caption("Figure 2.3: Key empirical findings from the RAG literature directly applied in the proposed system design."),
  pb()
);

// ══════════════════════════════════════════════════════════
// 2.5 XAI IN AGRICULTURE
// ══════════════════════════════════════════════════════════
ch.push(
  h2("2.5  Explainable AI in Agricultural Decision Support"),
  P([
    R("Despite the strong capabilities of modern agricultural AI, trust and adoption by farmers remain a persistent barrier. XAI research in agriculture has produced mature techniques but has failed to bridge the gap between explanation as research output and explanation as farmer-facing advisory interface.")
  ]),
  gap(),

  h3("2.5.1  XAI-CROP  (Springer NCA, 2024)"),
  P([
    R("XAI-CROP applies SHAP (SHapley Additive exPlanations) TreeExplainer to XGBoost and Random Forest crop recommendation models trained on soil composition, climate, and historical yield data across 22 Indian states. The paper makes two important empirical contributions: (1) SHAP feature importance correctly identifies soil pH, rainfall, and temperature as the primary determinants for most crop recommendations — matching domain expert expectations; and (2) "),
    Rb("farmers shown SHAP feature bars alongside recommendations adopted the AI advice 31% more frequently"),
    R(" than those shown recommendations without explanation — providing the strongest evidence in the literature that XAI improves adoption in agricultural contexts. Despite this, XAI-CROP's SHAP values are generated as research output in a Jupyter notebook — never rendered in a farmer-accessible interface. The proposed system is the first to close this gap.")
  ]),

  h3("2.5.2  Grad-CAM for Plant Disease Classification"),
  P([
    R("Multiple papers have applied Gradient-weighted Class Activation Mapping (Grad-CAM) to CNN and ViT models for plant disease classification, generating saliency maps that highlight the image regions most influential in the classification decision. The primary contribution is to "),
    Rb("enable expert validation"),
    R(": agronomists can verify whether the model attended to the correct lesion region rather than background artefacts. Studies show that models attending to leaves rather than pots or backgrounds achieve significantly higher field accuracy — Grad-CAM enables this quality check. In the proposed system, Grad-CAM overlays are rendered to the farmer in the PWA interface as colour heatmaps over the uploaded leaf image — transforming a research quality-control tool into a farmer-facing trust mechanism.")
  ]),

  h3("2.5.3  Agentic XAI for Agricultural Recommendation  (arXiv, 2025)"),
  P([
    R("This paper proposes an agentic XAI framework combining SHAP with LLM-driven iterative explanation refinement, evaluated by human experts across seven quality metrics including specificity, clarity, practicality, and crop science credibility. SHAP explanations generated iteratively over 11 rounds converge on explanations rated significantly higher by agronomists than single-round SHAP output. However, the system generates explanations "),
    Rb("for crop scientists, not farmers"),
    R(" — the language, numerical detail, and assumed background knowledge are inappropriate for low-literacy farm audiences. The proposed system adapts this iterative explanation refinement concept but constrains output to farmer-readable visualisations — colour heatmaps and bar charts — rather than text-heavy technical reports.")
  ]),
  gap()
);

// ══════════════════════════════════════════════════════════
// 2.6 SPEECH AND MULTILINGUAL NLP
// ══════════════════════════════════════════════════════════
ch.push(
  h2("2.6  Speech Processing and Multilingual NLP for Farmers"),
  P([
    R("Voice accessibility is one of the most critical and underserved dimensions of agricultural AI for India. This section reviews ASR, multilingual NLP, and speech synthesis research directly relevant to the proposed system's voice pipeline.")
  ]),
  gap(),

  h3("2.6.1  Indic ASR Benchmark for Agriculture  (arXiv, 2025)"),
  P([
    R("This paper provides the first agricultural-domain ASR benchmark for Indian languages, evaluating Whisper (multiple sizes), IndicWav2Vec, and commercial ASR services on "),
    Rb("10,934 real farm voice recordings"),
    R(" collected from the Farmer.Chat platform in Hindi and Odia. Key results: Whisper large-v3 achieves "),
    Rb("WER 16.2% for Hindi"),
    R(" and 35.1% for Odia on agricultural speech. Agricultural vocabulary — crop names, pesticide names, disease names — is identified as the primary source of ASR errors, motivating domain-specific fine-tuning. The paper also identifies that "),
    Rb("background noise from farm environments"),
    R(" (wind, machinery, animals) increases WER by 8–12 percentage points over studio conditions, requiring noise-robust model selection. This benchmark directly defines the WER targets for the proposed system (< 20% Hindi, < 30% regional) and identifies fine-tuning on agricultural vocabulary as essential.")
  ]),

  h3("2.6.2  Bhashini and IndicBERT"),
  P([
    R("Bhashini (MeitY, 2024) is the Government of India's national digital language inclusion platform, providing production-quality ASR and TTS for 10+ Indic languages including Hindi, Tamil, Telugu, Marathi, Kannada, Bengali, Gujarati, Punjabi, Odia, and Assamese. Unlike commercial ASR providers, Bhashini is purpose-built for Indian languages, trained on Indian-accent speech data, and freely available via API. IndicBERT provides a pre-trained transformer language model covering 12 Indic languages and is used for downstream NLP tasks including intent classification and agricultural named entity recognition in the proposed system.")
  ]),

  h3("2.6.3  Multilingual LLMs for Agricultural QA  (arXiv, 2025)"),
  P([
    R("This paper evaluates multilingual LLMs on low-resource language agricultural Q&A, using synthetic data augmentation (machine translation of English agricultural QA pairs) to overcome the scarcity of annotated Indic agricultural text. The key finding is that synthetic data achieves 78% of the performance of human-annotated data for Hindi agricultural QA — validating the use of machine-translated ICAR content for building the proposed system's Hindi RAG index. The paper also identifies that "),
    Rb("code-switching between Hindi and English is extremely common"),
    R(" in Indian farmer queries — motivating the hybrid Hindi+English bilingual knowledge index implemented in the proposed system.")
  ]),
  gap()
);

// ══════════════════════════════════════════════════════════
// 2.7 CROSS-STREAM SYNTHESIS
// ══════════════════════════════════════════════════════════
ch.push(
  h2("2.7  Cross-Stream Synthesis and Gap Evidence Matrix"),
  P([
    R("The six research streams reviewed in this chapter collectively establish the technological feasibility of each component of the proposed system. Table 2.5 provides the cross-stream gap evidence matrix — mapping each of the five research gaps to the specific prior work that establishes the gap exists, the paper that comes closest to addressing it, and the remaining contribution of the proposed system.")
  ]),
  gap(),

  new Paragraph({ children:[Rb("Table 2.5: Cross-stream gap evidence matrix", HDARK)], alignment:AlignmentType.CENTER, ...sp(0,80) }),
  new Table({
    width:{ size:W, type:WidthType.DXA }, columnWidths:[540,2040,2340,2340,2100],
    rows:[
      new TableRow({ tableHeader:true, children:[
        hCell("Gap", PURPLE,WHITE,540),
        hCell("Research stream",   PURPLE,WHITE,2040),
        hCell("Evidence for gap (paper + specific finding)", PURPLE,WHITE,2340),
        hCell("Closest prior attempt",    PURPLE,WHITE,2340),
        hCell("Proposed contribution",    PURPLE,WHITE,2100),
      ]}),
      ...[
        ["G1","Multi-agent chatbots (§2.2)","No system reviewed in §2.2 combines all five domains — Farmer.Chat (text+KB only), AgriDoctor (disease only), AgroAskAI (climate only), MDPI Agentic (rice disease+sensor only)","MDPI Agentic (4 agents, rice, no RAG)","5-agent orchestrator (disease, nutrition, crop, weather, market) with LangGraph routing"],
        ["G2","VLMs for disease (§2.3) + RAG (§2.4)","AgriM-LLM (2026) — best vision model, but no sensor fusion. Cross-modal fusion papers (PMC, 2025) — offline only, no conversational interface","MDPI Agentic (sensor + CNN, rice only, no dialogue)","ResNet-50 + sensor MLP cross-modal fusion inside conversation loop, 50+ crops"],
        ["G3","XAI in agriculture (§2.5)","XAI-CROP (2024): SHAP increases adoption by 31% but generated as research output — never in farmer UI. Grad-CAM papers: quality-control tool for researchers only","Agentic XAI (2025): iterative SHAP for scientists","Grad-CAM overlay + SHAP bars rendered in React PWA as part of advisory response"],
        ["G4","Speech & NLP (§2.6)","Indic ASR benchmark (2025): WER 16.2% Hindi is achievable — but no system connects ASR to advisory backend. Bhashini exists — but not connected to RAG pipeline","Farmer.Chat: Bhashini ASR input only (text output)","Whisper ASR → Hindi/regional RAG → Bhashini TTS — end-to-end voice advisory pipeline"],
        ["G5","Multi-agent chatbots (§2.2)","All 6 systems in §2.2 reviewed — none has market price agent. AgroLLM, AgriGPT — text-only advisory, no Agmarknet/eNAM integration","None — no prior system attempts this","Agmarknet+eNAM live feed + Prophet 7-day forecast co-delivered with agronomic advice"],
      ].map(([g,stream,evidence,closest,contrib],ri) => new TableRow({ children:[
        dCell(g,      LPUR, PURPLE, 540, true, AlignmentType.CENTER),
        dCell(stream, ri%2===0?LGRAY:WHITE, TEAL, 2040, true),
        dCell(evidence, ri%2===0?LGRAY:WHITE, SLATE, 2340),
        dCell(closest,  ri%2===0?LAMBER:LAMBER, AMBER, 2340),
        dCell(contrib,  ri%2===0?LGREEN:LGREEN, GREEN, 2100),
      ]}))
    ]
  }),
  caption("Table 2.5: Cross-stream gap evidence matrix — maps each gap to its research stream, specific evidentiary papers, closest prior attempt, and the proposed contribution."),
  gap(),

  // Summary paragraph
  accentBox("Chapter Summary: What the Literature Establishes", [
    [Rb("Component feasibility: "), R("Every individual component of the proposed system (ViT-L/16 disease diagnosis, RAG advisory, Whisper ASR, Bhashini TTS, XGBoost crop rec, SHAP/Grad-CAM XAI) has been individually demonstrated at state-of-the-art performance levels in the reviewed literature.")],
    [Rb("Integration gap: "), R("No reviewed system combines more than two of the five required capability dimensions simultaneously. The integration of all five in a deployment-ready system is the novel contribution of this research.")],
    [Rb("Base paper: "), R("AgriDoctor (IEEE, 2025) is identified as the primary base paper — it establishes the intent-routing multi-agent paradigm that the proposed system extends across five domains with sensor fusion, RAG, XAI, voice, and market integration.")],
    [Rb("Technology readiness: "), R("The convergence of ViT LoRA fine-tuning, Whisper large-v3, Bhashini API, hybrid RAG, and LangGraph in 2023-2025 makes the proposed system both necessary and technically feasible at this time.")],
  ], PURPLE, LPUR),
  caption("Figure 2.4: Chapter 2 summary — what the literature establishes and the specific integration gap addressed by this research."),
  pb()
);

// ══════════════════════════════════════════════════════════
// REFERENCES
// ══════════════════════════════════════════════════════════
ch.push(
  h1("References"),
  P([Ri("The following references are cited in Chapter 2. Complete bibliographic details are consolidated in the thesis reference list.")]),
  gap()
);

const refs = [
  { tag:"[1]",  cite:"Farmer.Chat: Scaling AI-Powered Agricultural Services for Smallholder Farmers. ACM, 2024. arXiv:2409.08916." },
  { tag:"[2]",  cite:"AgriDoctor: A Modular Multimodal Framework for Crop Disease Diagnosis and Agricultural Knowledge Interaction. IEEE / arXiv:2509.17044, September 2025." },
  { tag:"[3]",  cite:"AgriGPT: A Large Language Model Ecosystem for Agriculture with Tri-RAG and Multi-Agent Data Engine. arXiv:2508.08632, August 2025." },
  { tag:"[4]",  cite:"AgriGPT-VL: Agricultural Vision-Language Understanding Suite with the Agri-3M-VL Dataset. arXiv:2510.04002, October 2025." },
  { tag:"[5]",  cite:"AgriM-LLM: An Agriculture-Specific Multimodal Large Language Model for Intelligent Crop Disease and Pest Management. Preprints.org, January 2026. DOI: 10.20944/preprints202601.0646.v1." },
  { tag:"[6]",  cite:"AgroAskAI: A Multi-Agentic Framework for Agricultural Advisory and Climate Adaptation. arXiv, December 2024." },
  { tag:"[7]",  cite:"Agentic AI-Driven Autonomous Decision Support System for Smart Agriculture (CropiBot). Scientific Reports, January 2026." },
  { tag:"[8]",  cite:"MIRAGE: A Benchmark for Multimodal Information-Seeking and Reasoning in Agricultural Expert-Guided Conversations. arXiv, 2025." },
  { tag:"[9]",  cite:"AgMMU: Agricultural Multimodal Understanding and Reasoning Benchmark. arXiv, April 2025." },
  { tag:"[10]", cite:"LLMI-CDP: A Large Language Model for Multimodal Identification of Crop Diseases and Pests. Scientific Reports (Nature), 2025. DOI: 10.1038/s41598-025-01908-0." },
  { tag:"[11]", cite:"AgriChain: Visually-Grounded Expert-Verified Reasoning for Agricultural Vision-Language Models. arXiv, 2025." },
  { tag:"[12]", cite:"Self-Consistency in Vision-Language Models for Precision Agriculture: Multi-Response Consensus for Crop Disease Management. arXiv, 2025." },
  { tag:"[13]", cite:"Cross-Modal Data Fusion via Vision-Language Model for Crop Disease Recognition under Complex Field Conditions. PMC / MDPI, 2025." },
  { tag:"[14]", cite:"RAG-Based Large Language Model Advisory Framework for Farmers. Journal of Agricultural Engineering, 2026." },
  { tag:"[15]", cite:"AgroLLM: Connecting Farmers and Agricultural Practices through Large Language Models with Domain Knowledge Processing. arXiv:2503.04788, 2025." },
  { tag:"[16]", cite:"Overcoming LLM Challenges using RAG-Driven Precision in Coffee Leaf Disease Remediation. IEEE Conference, 2024." },
  { tag:"[17]", cite:"Enhancing Crop Recommendation with Explainable Artificial Intelligence (XAI-CROP). Neural Computing and Applications, Springer, 2024. DOI: 10.1007/s00521-024-xxxxx." },
  { tag:"[18]", cite:"Agentic XAI Framework for Agricultural Recommendation Using SHAP-Based LLM Iterative Refinement. arXiv, 2025." },
  { tag:"[19]", cite:"Selvaraju, R.R. et al. Grad-CAM: Visual Explanations from Deep Networks via Gradient-Based Localization. ICCV, 2017. DOI: 10.1109/ICCV.2017.74." },
  { tag:"[20]", cite:"Lundberg, S.M. and Lee, S.I. A Unified Approach to Interpreting Model Predictions (SHAP). NeurIPS, 2017. arXiv:1705.07874." },
  { tag:"[21]", cite:"Benchmarking Automatic Speech Recognition for Indian Languages in Agricultural Contexts. arXiv, 2025." },
  { tag:"[22]", cite:"MeitY / Bhashini. Digital Language Inclusion Platform for India. Ministry of Electronics and Information Technology, Government of India, 2024. Available at: bhashini.gov.in." },
  { tag:"[23]", cite:"Leveraging Synthetic Data for Agricultural QA with Multilingual LLMs. arXiv, 2025." },
  { tag:"[24]", cite:"Kakwani, D. et al. IndicNLPSuite: Monolingual Corpora, Evaluation Benchmarks and Pre-trained Multilingual Language Models for Indian Languages. EMNLP Findings, 2020." },
  { tag:"[25]", cite:"Radford, A. et al. Robust Speech Recognition via Large-Scale Weak Supervision (Whisper). ICML, 2023. arXiv:2212.04356." },
  { tag:"[26]", cite:"Recent Advances in Transformer Technology for Agriculture: A Survey. Engineering Applications of AI, Elsevier, 2024." },
  { tag:"[27]", cite:"Harnessing Large Vision and Language Models in Agriculture: A Review. Frontiers in Plant Science, 2025." },
  { tag:"[28]", cite:"Deep Learning and Computer Vision Approaches in Plant Disease Detection: A Comprehensive Review. Artificial Intelligence Review, Springer, 2025." },
  { tag:"[29]", cite:"Hughes, D. and Salathé, M. An Open Access Repository of Images on Plant Health to Enable the Development of Mobile Disease Diagnostics (PlantVillage). arXiv:1511.08060, 2015." },
  { tag:"[30]", cite:"Singh, D. et al. PlantDoc: A Dataset for Visual Plant Disease Detection. CoDS-COMAD, 2020. DOI: 10.1145/3371158.3371196." },
  { tag:"[31]", cite:"Wu, X. et al. IP102: A Large-Scale Benchmark Dataset for Insect Pest Recognition. CVPR, 2019." },
  { tag:"[32]", cite:"PhenoAssistant: AI-Driven Plant Phenotyping via Natural Language Interaction. Nature Communications, 2026." },
  { tag:"[33]", cite:"AgriBuddy: An Agentic Chatbot for Bangladeshi Smallholder Farmers with CNN Disease Detection. BRAC University, 2025." },
  { tag:"[34]", cite:"IPM-AgriGPT: A Large Language Model for Pest and Disease Management Based on Integrated Pest Management. Mathematics (MDPI), 2025. DOI: 10.3390/math13040566." },
  { tag:"[35]", cite:"Lewis, P. et al. Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. NeurIPS, 2020. arXiv:2005.11401." },
  { tag:"[36]", cite:"Hu, E. et al. LoRA: Low-Rank Adaptation of Large Language Models. ICLR, 2022. arXiv:2106.09685." },
  { tag:"[37]", cite:"Dosovitskiy, A. et al. An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale. ICLR, 2021. arXiv:2010.11929." },
  { tag:"[38]", cite:"PLANT/ds Rule-Based Disease Expert System for Soybean. Purdue University Agricultural Experiment Station, 1983." },
  { tag:"[39]", cite:"RAGAS: Automated Evaluation of Retrieval-Augmented Generation. arXiv:2309.15217, 2023." },
];

refs.forEach(r => {
  ch.push(new Paragraph({
    children:[
      new TextRun({ text:r.tag+"  ", font:"Arial", size:19, bold:true, color:PURPLE }),
      new TextRun({ text:r.cite, font:"Arial", size:19, color:SLATE }),
    ],
    indent:{ left:540, hanging:540 },
    ...sp(0,100)
  }));
});

// ══════════════════════════════════════════════════════════
// ASSEMBLE
// ══════════════════════════════════════════════════════════
const doc = new Document({
  numbering:{
    config:[
      { reference:"bullets",
        levels:[{ level:0, format:LevelFormat.BULLET, text:"\u2022", alignment:AlignmentType.LEFT,
          style:{ paragraph:{ indent:{ left:720, hanging:360 } } } }]
      },
      { reference:"numbers",
        levels:[{ level:0, format:LevelFormat.DECIMAL, text:"%1.", alignment:AlignmentType.LEFT,
          style:{ paragraph:{ indent:{ left:720, hanging:360 } } } }]
      },
    ]
  },
  styles:{
    default:{ document:{ run:{ font:"Arial", size:22 } } },
    paragraphStyles:[
      { id:"Heading1", name:"Heading 1", basedOn:"Normal", next:"Normal", quickFormat:true,
        run:{ size:36, bold:true, font:"Arial", color:HDARK },
        paragraph:{ spacing:{ before:480, after:240 }, outlineLevel:0 } },
      { id:"Heading2", name:"Heading 2", basedOn:"Normal", next:"Normal", quickFormat:true,
        run:{ size:26, bold:true, font:"Arial", color:PURPLE },
        paragraph:{ spacing:{ before:300, after:120 }, outlineLevel:1 } },
      { id:"Heading3", name:"Heading 3", basedOn:"Normal", next:"Normal", quickFormat:true,
        run:{ size:23, bold:true, font:"Arial", color:TEAL },
        paragraph:{ spacing:{ before:200, after:80 }, outlineLevel:2 } },
    ]
  },
  sections:[{
    properties:{
      page:{
        size:{ width:12240, height:15840 },
        margin:{ top:1440, right:1440, bottom:1440, left:1440 }
      }
    },
    headers:{
      default: new Header({ children:[
        new Paragraph({
          children:[
            new TextRun({ text:"Chapter 2: Literature Review", font:"Arial", size:18, color:MUTED }),
            new TextRun({ text:"  |  Towards a Next-Generation Agricultural Expert System", font:"Arial", size:18, color:PURPLE }),
          ],
          border:{ bottom:{ style:BorderStyle.SINGLE, size:4, color:PURPLE, space:4 } },
          ...sp(0,80)
        })
      ]})
    },
    footers:{
      default: new Footer({ children:[
        new Paragraph({
          children:[
            new TextRun({ text:"[Student Name]  |  [Department]  |  [Institution]  |  2024–25", font:"Arial", size:18, color:MUTED }),
            new TextRun({ text:"     Page ", font:"Arial", size:18, color:MUTED }),
            new TextRun({ children:[PageNumber.CURRENT], font:"Arial", size:18, color:PURPLE }),
          ],
          border:{ top:{ style:BorderStyle.SINGLE, size:4, color:PURPLE, space:4 } },
          ...sp(80,0)
        })
      ]})
    },
    children: ch
  }]
});

Packer.toBuffer(doc)
  .then(buf => {
    fs.writeFileSync("AgriSys_Chapter2_LiteratureReview.docx", buf);
    console.log("DONE");
  })
  .catch(e => { console.error(e); process.exit(1); });
