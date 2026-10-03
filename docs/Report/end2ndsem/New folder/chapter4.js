const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, PageNumber, PageBreak, LevelFormat
} = require('docx');
const fs = require('fs');

const PURPLE = "534AB7"; const LPUR   = "EEEDFE";
const TEAL   = "0F6E56"; const LTEAL  = "E1F5EE";
const CORAL  = "993C1D"; const LCORAL = "FAECE7";
const AMBER  = "854F0B"; const LAMBER = "FAEEDA";
const GREEN  = "3B6D11"; const LGREEN = "EAF3DE";
const BLUE   = "185FA5"; const LBLUE  = "E6F1FB";
const DARK   = "1E293B"; const MUTED  = "64748B";
const LGRAY  = "F4F6F8"; const BORDER = "CBD5E1";
const WHITE  = "FFFFFF"; const HDARK  = "0F2027";
const SLATE  = "334455";

const W = 9360;
const brd  = { style: BorderStyle.SINGLE, size: 1, color: BORDER };
const brdM = { top: brd, bottom: brd, left: brd, right: brd };
const cMrg = { top: 100, bottom: 100, left: 150, right: 150 };
const sp   = (b=0,a=0) => ({ spacing:{ before:b, after:a } });

const R  = (t,o={}) => new TextRun({ text:t, font:"Arial", size:22, color:DARK, ...o });
const Rb = (t,c)    => new TextRun({ text:t, font:"Arial", size:22, bold:true, color:c||DARK });
const Ri = (t,c)    => new TextRun({ text:t, font:"Arial", size:22, italic:true, color:c||MUTED });

function P(runs, align) {
  const ch = typeof runs==="string"?[R(runs)]:runs;
  return new Paragraph({ children:ch, alignment:align||AlignmentType.JUSTIFIED, ...sp(0,160) });
}
function h1(t) {
  return new Paragraph({
    heading:HeadingLevel.HEADING_1,
    children:[new TextRun({ text:t, font:"Arial", size:36, bold:true, color:HDARK })],
    ...sp(480,240),
    border:{ bottom:{ style:BorderStyle.SINGLE, size:8, color:PURPLE, space:4 } }
  });
}
function h2(t) {
  return new Paragraph({
    heading:HeadingLevel.HEADING_2,
    children:[new TextRun({ text:t, font:"Arial", size:26, bold:true, color:PURPLE })],
    ...sp(280,120)
  });
}
function gap(n=1) { return new Paragraph({ children:[R("")], ...sp(0,80*n) }); }
function pb()     { return new Paragraph({ children:[new PageBreak()] }); }
function caption(t) {
  return new Paragraph({
    children:[new TextRun({ text:t, font:"Arial", size:18, italic:true, color:MUTED })],
    alignment:AlignmentType.CENTER, ...sp(60,200)
  });
}
function blt(runs) {
  const ch = typeof runs==="string"?[R(runs)]:runs;
  return new Paragraph({ numbering:{ reference:"bullets", level:0 }, children:ch, ...sp(0,80) });
}

function hCell(text,bg,fg=WHITE,w=1000) {
  return new TableCell({
    borders:brdM, width:{ size:w, type:WidthType.DXA },
    shading:{ fill:bg, type:ShadingType.CLEAR }, margins:cMrg,
    children:[new Paragraph({
      children:[new TextRun({ text, font:"Arial", size:19, bold:true, color:fg })],
      alignment:AlignmentType.CENTER
    })]
  });
}
function dCell(text,bg=WHITE,fg=DARK,w=1000,bold_=false,align=AlignmentType.LEFT) {
  return new TableCell({
    borders:brdM, width:{ size:w, type:WidthType.DXA },
    shading:{ fill:bg, type:ShadingType.CLEAR }, margins:cMrg,
    children:[new Paragraph({
      children:[new TextRun({ text, font:"Arial", size:19, bold:bold_, color:fg })],
      alignment:align
    })]
  });
}

// Objective card — left accent border
function objCard(id, title, color, lightColor, rows) {
  const cardRows = [];
  // header
  cardRows.push(new TableRow({ children:[new TableCell({
    borders:{ top:brd, bottom:brd, right:brd, left:{ style:BorderStyle.SINGLE, size:18, color } },
    width:{ size:W, type:WidthType.DXA },
    shading:{ fill:lightColor, type:ShadingType.CLEAR },
    margins:{ top:140, bottom:60, left:200, right:180 },
    children:[new Paragraph({ children:[
      new TextRun({ text:id+"  ", font:"Arial", size:22, bold:true, color }),
      new TextRun({ text:title, font:"Arial", size:22, bold:true, color:HDARK }),
    ], ...sp(0,0) })]
  })]}));
  // content rows
  rows.forEach(({ label, content }) => {
    cardRows.push(new TableRow({ children:[new TableCell({
      borders:{ top:{ style:BorderStyle.NONE }, bottom:brd, right:brd, left:{ style:BorderStyle.SINGLE, size:18, color } },
      width:{ size:W, type:WidthType.DXA },
      shading:{ fill:lightColor, type:ShadingType.CLEAR },
      margins:{ top:60, bottom:60, left:200, right:180 },
      children:[
        new Paragraph({ children:[new TextRun({ text:label, font:"Arial", size:19, bold:true, color })], ...sp(0,30) }),
        new Paragraph({ children: typeof content==="string"?[R(content)]:content, alignment:AlignmentType.JUSTIFIED, ...sp(0,0) })
      ]
    })]}));
  });
  return new Table({ width:{ size:W, type:WidthType.DXA }, columnWidths:[W], rows:cardRows, ...sp(80,100) });
}

// ════════════════════════════════════════════════════
const ch = [];

// Chapter heading
ch.push(
  new Paragraph({ children:[new TextRun({ text:"Chapter 4", font:"Arial", size:24, color:MUTED, bold:true, characterSpacing:200 })], ...sp(0,80) }),
  h1("Research Objectives"),
  P([
    R("This chapter defines the eight specific, measurable research objectives of the proposed system. Each objective is derived directly from a research gap identified in Chapter 3 and a research question from Chapter 1. The objectives are designed to be independently testable — each has a named target metric — yet collectively form an integrated system. Section 4.1 states the primary objective. Sections 4.2 through 4.9 detail each specific objective. Section 4.10 provides the complete gap-to-objective traceability matrix.")
  ]),
  gap()
);

// ── 4.1 PRIMARY OBJECTIVE ────────────────────────────────
ch.push(
  h2("4.1  Primary Objective"),
  new Table({
    width:{ size:W, type:WidthType.DXA }, columnWidths:[W],
    rows:[new TableRow({ children:[new TableCell({
      borders:{ top:brd, bottom:brd, right:brd, left:{ style:BorderStyle.SINGLE, size:20, color:PURPLE } },
      width:{ size:W, type:WidthType.DXA },
      shading:{ fill:LPUR, type:ShadingType.CLEAR },
      margins:{ top:180, bottom:180, left:240, right:220 },
      children:[
        new Paragraph({ children:[new TextRun({ text:"Primary Objective", font:"Arial", size:20, bold:true, color:PURPLE })], ...sp(0,80) }),
        new Paragraph({
          children:[
            R("To design, develop, and evaluate a "),
            Rb("deployment-ready multi-agent, multi-model agricultural expert system"), R(" for Indian smallholder farmers that integrates five specialist AI agents — disease diagnosis, nutrition deficiency, crop recommendation, weather and irrigation, and live market price advisory — orchestrated by an intent-routing backbone, grounded in a verified RAG knowledge base, augmented with farmer-facing explainability, and accessible via a multilingual Indic voice interface on a Progressive Web Application.")
          ],
          alignment:AlignmentType.JUSTIFIED
        })
      ]
    })]})],
    ...sp(0,120)
  }),
  gap()
);

// ── 4.2 SPECIFIC OBJECTIVES ──────────────────────────────
ch.push(h2("4.2  Specific Objectives"));

// O1
ch.push(
  objCard("O1", "Multi-Agent Orchestration Architecture", PURPLE, LPUR, [
    { label:"Description", content:[
      R("Design and implement a "), Rb("LangGraph-based orchestrator"), R(" that classifies incoming farmer queries into one of eight intent categories and dispatches inputs in parallel to the appropriate specialist agent(s). The orchestrator maintains multi-turn conversational state via Redis session memory and merges multi-agent responses into a single coherent advisory reply.")
    ]},
    { label:"Gaps closed", content:"G1 — No unified multimodal advisory session" },
    { label:"Key technologies", content:"LangGraph v1.1 · GPT-5.5 backbone · fine-tuned BERT-multilingual intent classifier · Redis session store · asyncio parallel dispatch" },
    { label:"Target metrics", content:"Intent classification accuracy > 95% · End-to-end response latency < 4 s (cloud) and < 8 s (PWA offline cache)" },
  ]),
  gap()
);

// O2
ch.push(
  objCard("O2", "Disease Diagnostic Agent", CORAL, LCORAL, [
    { label:"Description", content:[
      R("Fine-tune "), Rb("ViT-L/16"), R(" with LoRA adaptation (rank-16, alpha-32) on a composite dataset of 164,500 leaf and pest images across PlantVillage, PlantDoc, and IP102. Integrate AgriChain Chain-of-Thought prompting for structured reasoning from visual input to treatment protocol. Generate Grad-CAM saliency maps for every diagnosis.")
    ]},
    { label:"Gaps closed", content:"G1 (image input modality) · G3 (Grad-CAM generated for rendering)" },
    { label:"Key technologies", content:"ViT-L/16 (ImageNet-21k) · LoRA rank-16 · LLMI-CDP dialogue style · AgriChain CoT · PlantVillage (87k) + PlantDoc (2.5k) + IP102 (75k)" },
    { label:"Target metrics", content:"Top-1 accuracy > 90% · F1 macro > 0.87 · Grad-CAM IoU vs. expert annotation > 0.75 · Covers 200+ diseases across 50+ crops" },
  ]),
  gap()
);

// O3
ch.push(
  objCard("O3", "Nutrition Deficiency Agent with Cross-Modal Fusion", AMBER, LAMBER, [
    { label:"Description", content:[
      R("Develop a "), Rb("cross-modal fusion network"), R(" that concatenates ResNet-50 leaf image feature vectors (2048-dim) with normalised real-time soil sensor readings (NPK, pH, EC, moisture — 6-dim) into a joint 2054-dimensional representation. Three fully-connected layers produce: (1) deficiency class label (N/P/K/Fe/Zn/B deficiency or healthy), and (2) fertiliser dose recommendation in kg/ha aligned with ICAR Soil Health Card norms.")
    ]},
    { label:"Gaps closed", content:"G2 — No cross-modal sensor + image nutrition fusion in a conversational loop" },
    { label:"Key technologies", content:"ResNet-50 encoder · 6-dim sensor vector (MQTT/REST) · Cross-modal MLP · ICAR Soil Health Card DB · SHAP feature importance" },
    { label:"Target metrics", content:"Deficiency class F1 > 0.85 · Fertiliser dose RMSE < 5 kg/ha · SHAP stability score > 0.80 across repeated runs" },
  ]),
  gap()
);

// O4
ch.push(
  objCard("O4", "Hallucination-Resistant RAG Knowledge Layer", TEAL, LTEAL, [
    { label:"Description", content:[
      R("Build a "), Rb("250,000+ document chunk RAG pipeline"), R(" over verified ICAR Package of Practices (all major Indian crops), KCC call transcripts, CGIAR, FAO, Agmarknet historical data, and Soil Health Card norms. Implement hybrid BM25 + dense retrieval with E5-large-v2 embeddings, cross-encoder reranking, HyDE query expansion, and Qwen3-72B LLM-as-judge confidence gating. Escalate to KCC expert webhook if confidence score < 0.70.")
    ]},
    { label:"Gaps closed", content:"G1 (knowledge grounding across all five domains)" },
    { label:"Key technologies", content:"Qdrant vector store · E5-large-v2 embeddings · ms-marco cross-encoder · HyDE + MMR · Qwen3-72B judge · Bilingual Hindi+English index" },
    { label:"Target metrics", content:"RAGAS faithfulness > 0.88 · Context relevance > 0.85 · Hallucination rate < 5% · Expert escalation trigger accuracy > 90%" },
  ]),
  gap()
);

// O5
ch.push(
  objCard("O5", "Farmer-Facing Explainable AI (XAI)", GREEN, LGREEN, [
    { label:"Description", content:[
      R("Render "), Rb("Grad-CAM saliency heatmaps"), R(" as colour overlays on the farmer's uploaded leaf image and "), Rb("SHAP feature importance bar charts"), R(" for crop recommendations — directly within the React PWA advisory response as farmer-accessible UI components, with Hindi-labelled axes and simplified visual legends. This closes the gap between XAI as a research output and XAI as a farmer-facing trust mechanism.")
    ]},
    { label:"Gaps closed", content:"G3 — XAI never rendered to the farmer in any deployed system" },
    { label:"Key technologies", content:"Grad-CAM (layer4) · EigenCAM (validation) · SHAP TreeExplainer · Recharts (PWA bar charts) · Hindi axis labels via i18next" },
    { label:"Target metrics", content:"Grad-CAM IoU > 0.75 vs. ICAR agronomist annotation · SHAP stability > 0.80 · Farmer comprehension score > 3.5/5.0 (Likert, n=30 pilot)" },
  ]),
  gap()
);

// O6
ch.push(
  objCard("O6", "End-to-End Indic Voice Advisory Pipeline", BLUE, LBLUE, [
    { label:"Description", content:[
      R("Implement a complete voice advisory pipeline: "), Rb("Whisper large-v3"), R(" (fine-tuned on Indic agricultural speech from the 10,934-recording benchmark corpus) for ASR → multilingual RAG retrieval over Hindi+English bilingual knowledge index → "), Rb("Bhashini TTS"), R(" for spoken response delivery in 10 Indic languages. The pipeline must operate within a 4-second end-to-end latency budget on 3G connectivity.")
    ]},
    { label:"Gaps closed", content:"G4 — No end-to-end Indic voice-to-advisory pipeline exists in any agricultural system" },
    { label:"Key technologies", content:"Whisper large-v3 (Indic fine-tuned) · Bhashini ASR + TTS API · IndicBERT NER · MediaRecorder (PWA browser) · 16 kHz mono WAV preprocessing" },
    { label:"Target metrics", content:"WER < 20% for Hindi agricultural speech · WER < 30% for five regional languages (Tamil, Telugu, Marathi, Kannada, Odia) · End-to-end latency < 4 s" },
  ]),
  gap()
);

// O7
ch.push(
  objCard("O7", "Live Market Price Advisory Agent", PURPLE, LPUR, [
    { label:"Description", content:[
      R("Integrate "), Rb("Agmarknet and eNAM live mandi price feeds"), R(" (15-minute refresh, Redis cache) with a Prophet-based 7-day price forecast model. Rank nearby mandis by Haversine distance and price differential. Co-deliver sell, hold, or transport-to-mandi advisory within the same conversational session as agronomic advice — enabling compound queries such as 'my crop has blight; should I treat or sell now?'")
    ]},
    { label:"Gaps closed", content:"G5 — Live market price never co-delivered with agronomic advice in any prior system" },
    { label:"Key technologies", content:"Agmarknet API · eNAM data feed · Prophet time-series forecast · CACP MSP dataset 2024–25 · Haversine mandi ranking · Redis 15-min TTL cache" },
    { label:"Target metrics", content:"7-day price forecast MAPE < 8% · Mandi ranking accuracy > 85% vs. actual best-price mandi · Sell/hold advisory agronomist agreement > 75%" },
  ]),
  gap()
);

// O8
ch.push(
  objCard("O8", "System Evaluation and Expert Validation", TEAL, LTEAL, [
    { label:"Description", content:[
      R("Benchmark the complete integrated system on "), Rb("MIRAGE"), R(" (multi-turn agricultural dialogue benchmark) and "), Rb("AgMMU"), R(" (agricultural multimodal understanding benchmark). Validate advisory quality via a blind evaluation panel of ten ICAR-certified agronomists rating 200 real farmer queries across five crop categories on a 5-point Likert scale for correctness, clarity, safety, and actionability.")
    ]},
    { label:"Gaps closed", content:"Validates that all five gaps are closed — quantitative evidence for each claim" },
    { label:"Key technologies", content:"MIRAGE benchmark · AgMMU benchmark · RAGAS eval suite · ICAR agronomist panel (n=10) · Langfuse tracing · Ablation study framework" },
    { label:"Target metrics", content:"Agronomist correctness Likert > 4.0/5.0 · Agronomist agreement > 80% · MIRAGE score > baseline by 15% · Ablation: 5-agent vs. single-agent · RAG vs. no-RAG" },
  ]),
  gap(2)
);

// ── 4.3 OBJECTIVES SUMMARY TABLE ─────────────────────────
ch.push(
  h2("4.3  Objectives Summary and Traceability Matrix"),
  P([
    R("Table 4.1 provides the complete traceability matrix mapping each research objective to its parent research question (Chapter 1), the research gap it closes (Chapter 3), the primary technologies required, and the quantitative target metric for evaluation.")
  ]),
  gap(),

  new Paragraph({ children:[Rb("Table 4.1: Research objectives — full traceability matrix", HDARK)], alignment:AlignmentType.CENTER, ...sp(0,80) }),
  new Table({
    width:{ size:W, type:WidthType.DXA },
    columnWidths:[540, 720, 720, 2700, 2340, 2340],
    rows:[
      new TableRow({ tableHeader:true, children:[
        hCell("Obj.",      HDARK, WHITE, 540),
        hCell("RQ",        HDARK, WHITE, 720),
        hCell("Gap",       HDARK, WHITE, 720),
        hCell("Description", HDARK, WHITE, 2700),
        hCell("Technology", HDARK, WHITE, 2340),
        hCell("Target metric", HDARK, WHITE, 2340),
      ]}),
      ...([
        ["O1","RQ1","G1","Multi-agent orchestrator — intent routing to 5 specialist agents with Redis memory","LangGraph v1.1 · BERT intent classifier · GPT-5.5","Intent accuracy > 95% · Latency < 4 s"],
        ["O2","RQ1","G1","Disease agent — ViT-L/16 + LoRA on 164k images with CoT reasoning and Grad-CAM","ViT-L/16 · LoRA rank-16 · AgriChain CoT · PlantVillage+PlantDoc+IP102","Top-1 acc > 90% · F1 > 0.87 · Grad-CAM IoU > 0.75"],
        ["O3","RQ2","G2","Nutrition agent — cross-modal fusion of ResNet-50 leaf features + soil NPK/pH/EC","ResNet-50 + 6-dim sensor MLP · ICAR SHC norms · SHAP","Deficiency F1 > 0.85 · Dose RMSE < 5 kg/ha"],
        ["O4","RQ1","G1","RAG pipeline — 250k+ ICAR/FAO chunks, hybrid retrieval, LLM-as-judge gating","Qdrant · E5-large-v2 · Cross-encoder · HyDE · Qwen3","Faithfulness > 0.88 · Hallucination < 5%"],
        ["O5","RQ3","G3","Farmer XAI — Grad-CAM overlay + SHAP charts rendered in React PWA advisory UI","Grad-CAM · SHAP TreeExplainer · Recharts · i18next Hindi","IoU > 0.75 · Farmer comprehension > 3.5/5.0"],
        ["O6","RQ4","G4","Indic voice pipeline — Whisper ASR + bilingual RAG + Bhashini TTS end-to-end","Whisper large-v3 Indic · Bhashini API · IndicBERT","WER < 20% Hindi · < 30% regional · < 4 s E2E"],
        ["O7","RQ5","G5","Market agent — Agmarknet/eNAM live feed + Prophet forecast co-delivered with agronomy","Agmarknet + eNAM API · Prophet · MSP DB · Redis TTL","Price MAPE < 8% · Agronomist agreement > 75%"],
        ["O8","All","All","System evaluation — MIRAGE, AgMMU, ICAR agronomist panel (n=10, 200 queries)","RAGAS · MIRAGE · AgMMU · Langfuse · Ablation","Likert > 4.0/5.0 · Agronomist agreement > 80%"],
      ]).map(([obj,rq,gap_,desc,tech,metric],ri) => new TableRow({ children:[
        dCell(obj,    LPUR,  PURPLE,540,true,AlignmentType.CENTER),
        dCell(rq,     ri%2===0?LGRAY:WHITE,MUTED,720,false,AlignmentType.CENTER),
        dCell(gap_,   ri%2===0?LAMBER:LAMBER,AMBER,720,true,AlignmentType.CENTER),
        dCell(desc,   ri%2===0?LGRAY:WHITE,DARK,2700),
        dCell(tech,   ri%2===0?LGRAY:WHITE,SLATE,2340),
        dCell(metric, ri%2===0?LGREEN:LGREEN,GREEN,2340),
      ]}))
    ]
  }),
  caption("Table 4.1: Full traceability matrix — each objective traced to research question, gap closed, technology stack, and quantitative evaluation target."),
  gap(2)
);

// ── 4.4 RELATIONSHIP DIAGRAM (as table) ──────────────────
ch.push(
  h2("4.4  Objective–Gap–Contribution Relationship"),
  P("Table 4.2 summarises the direct relationship between each gap identified in Chapter 3, the objective that closes it, and the novel contribution it produces — confirming that every gap has exactly one closing objective and every objective produces a clearly stated novel contribution."),
  gap(),

  new Paragraph({ children:[Rb("Table 4.2: Gap-to-objective-to-contribution mapping", HDARK)], alignment:AlignmentType.CENTER, ...sp(0,80) }),
  new Table({
    width:{ size:W, type:WidthType.DXA },
    columnWidths:[540, 2520, 540, 5760],
    rows:[
      new TableRow({ tableHeader:true, children:[
        hCell("Gap",          PURPLE, WHITE, 540),
        hCell("Gap statement (brief)", PURPLE, WHITE, 2520),
        hCell("Obj.",         PURPLE, WHITE, 540),
        hCell("Novel contribution produced", PURPLE, WHITE, 5760),
      ]}),
      ...([
        ["G1","No unified multimodal advisory session across all five domains","O1","First deployment-ready multi-agent system routing to five specialist models in one session — novel over Farmer.Chat, AgriDoctor, AgroAskAI (all single-model or single-domain)"],
        ["G2","No cross-modal sensor+image nutrition fusion in a dialogue","O3","First cross-modal fusion network combining leaf image features + soil sensor data for nutrition deficiency advisory inside a conversational loop — novel over all surveyed nutrition and VLM papers"],
        ["G3","XAI never rendered to farmer in any deployed system","O5","First system rendering Grad-CAM heatmaps and SHAP charts to farmers as a UI component of the advisory response — novel over XAI-CROP (Springer), LLMI-CDP, Agentic XAI (all researcher-facing only)"],
        ["G4","No end-to-end Indic voice-to-advisory pipeline","O6","First end-to-end pipeline: Whisper ASR → multilingual RAG → Bhashini TTS for agricultural advisory — novel over Farmer.Chat (partial ASR only) and all other systems (no voice)"],
        ["G5","Market price never co-delivered with agronomic advice","O7","First system delivering live mandi price forecast and sell/hold advisory within the same session as disease and nutrition advice — novel over all 25+ surveyed papers (none attempt this)"],
      ]).map(([g,gs,o,c],ri) => new TableRow({ children:[
        dCell(g,  LCORAL, CORAL, 540, true, AlignmentType.CENTER),
        dCell(gs, ri%2===0?LGRAY:WHITE, DARK, 2520),
        dCell(o,  LPUR,   PURPLE,540, true, AlignmentType.CENTER),
        dCell(c,  ri%2===0?LGREEN:LGREEN, GREEN, 5760),
      ]}))
    ]
  }),
  caption("Table 4.2: Direct gap-to-objective-to-contribution traceability. Every identified gap is closed by exactly one objective; every objective produces a clearly novel contribution over the surveyed literature."),
  pb()
);

// ── REFERENCES ────────────────────────────────────────────
ch.push(
  h1("References"),
  P([Ri("References cited in Chapter 4. Full details in consolidated thesis reference list.")]),
  gap()
);

[
  ["[1]",  "AgriDoctor: A Modular Multimodal Framework for Crop Disease Diagnosis. IEEE / arXiv:2509.17044, 2025."],
  ["[2]",  "AgriGPT: A Large Language Model Ecosystem for Agriculture with Tri-RAG. arXiv:2508.08632, 2025."],
  ["[3]",  "AgriM-LLM: An Agriculture-Specific Multimodal LLM for Crop Disease and Pest Management. Preprints.org, 2026."],
  ["[4]",  "Farmer.Chat: Scaling AI-Powered Agricultural Services for Smallholder Farmers. ACM, 2024. arXiv:2409.08916."],
  ["[5]",  "AgriChain: Visually-Grounded Expert-Verified Reasoning for Agricultural VLMs. arXiv, 2025."],
  ["[6]",  "LLMI-CDP: A Large Language Model for Multimodal Identification of Crop Diseases and Pests. Scientific Reports, 2025."],
  ["[7]",  "Enhancing Crop Recommendation with Explainable AI (XAI-CROP). Neural Computing and Applications, Springer, 2024."],
  ["[8]",  "Benchmarking ASR for Indian Languages in Agricultural Contexts. arXiv, 2025."],
  ["[9]",  "MeitY / Bhashini. Digital Language Inclusion Platform. Government of India, 2024."],
  ["[10]", "RAG-Based LLM Advisory Framework for Farmers. Journal of Agricultural Engineering, 2026."],
  ["[11]", "MIRAGE: Benchmark for Multimodal Information-Seeking in Agricultural Expert-Guided Conversations. arXiv, 2025."],
  ["[12]", "AgMMU: Agricultural Multimodal Understanding and Reasoning Benchmark. arXiv, April 2025."],
  ["[13]", "RAGAS: Automated Evaluation of Retrieval-Augmented Generation. arXiv:2309.15217, 2023."],
  ["[14]", "Hu, E. et al. LoRA: Low-Rank Adaptation of Large Language Models. ICLR, 2022. arXiv:2106.09685."],
  ["[15]", "Dosovitskiy, A. et al. An Image is Worth 16×16 Words: Transformers for Image Recognition at Scale. ICLR, 2021."],
  ["[16]", "Selvaraju, R.R. et al. Grad-CAM: Visual Explanations from Deep Networks. ICCV, 2017."],
  ["[17]", "Lundberg, S.M. and Lee, S.I. A Unified Approach to Interpreting Model Predictions (SHAP). NeurIPS, 2017."],
  ["[18]", "Radford, A. et al. Robust Speech Recognition via Large-Scale Weak Supervision (Whisper). ICML, 2023."],
  ["[19]", "LangChain. State of AI Agents Report 2025. LangChain Inc., 2025."],
  ["[20]", "eNAM Annual Report 2022–23. National Agriculture Market, Ministry of Agriculture, Government of India, 2023."],
  ["[21]", "ICAR Package of Practices for Major Indian Crops. Indian Council of Agricultural Research, 2023."],
].forEach(([tag, cite]) => {
  ch.push(new Paragraph({
    children:[
      new TextRun({ text:tag+"  ", font:"Arial", size:19, bold:true, color:PURPLE }),
      new TextRun({ text:cite, font:"Arial", size:19, color:SLATE }),
    ],
    indent:{ left:540, hanging:540 }, ...sp(0,100)
  }));
});

// ── ASSEMBLE ──────────────────────────────────────────────
const doc = new Document({
  numbering:{
    config:[
      { reference:"bullets", levels:[{ level:0, format:LevelFormat.BULLET, text:"\u2022", alignment:AlignmentType.LEFT, style:{ paragraph:{ indent:{ left:720, hanging:360 } } } }] },
      { reference:"numbers", levels:[{ level:0, format:LevelFormat.DECIMAL, text:"%1.", alignment:AlignmentType.LEFT, style:{ paragraph:{ indent:{ left:720, hanging:360 } } } }] },
    ]
  },
  styles:{
    default:{ document:{ run:{ font:"Arial", size:22 } } },
    paragraphStyles:[
      { id:"Heading1", name:"Heading 1", basedOn:"Normal", next:"Normal", quickFormat:true, run:{ size:36, bold:true, font:"Arial", color:HDARK }, paragraph:{ spacing:{ before:480, after:240 }, outlineLevel:0 } },
      { id:"Heading2", name:"Heading 2", basedOn:"Normal", next:"Normal", quickFormat:true, run:{ size:26, bold:true, font:"Arial", color:PURPLE }, paragraph:{ spacing:{ before:280, after:120 }, outlineLevel:1 } },
    ]
  },
  sections:[{
    properties:{ page:{ size:{ width:12240, height:15840 }, margin:{ top:1440, right:1440, bottom:1440, left:1440 } } },
    headers:{ default: new Header({ children:[new Paragraph({
      children:[
        new TextRun({ text:"Chapter 4: Research Objectives", font:"Arial", size:18, color:MUTED }),
        new TextRun({ text:"  |  Towards a Next-Generation Agricultural Expert System", font:"Arial", size:18, color:PURPLE }),
      ],
      border:{ bottom:{ style:BorderStyle.SINGLE, size:4, color:PURPLE, space:4 } }, ...sp(0,80)
    })]})},
    footers:{ default: new Footer({ children:[new Paragraph({
      children:[
        new TextRun({ text:"[Student Name]  |  [Department]  |  [Institution]  |  2024–25", font:"Arial", size:18, color:MUTED }),
        new TextRun({ text:"     Page ", font:"Arial", size:18, color:MUTED }),
        new TextRun({ children:[PageNumber.CURRENT], font:"Arial", size:18, color:PURPLE }),
      ],
      border:{ top:{ style:BorderStyle.SINGLE, size:4, color:PURPLE, space:4 } }, ...sp(80,0)
    })]})},
    children: ch
  }]
});

Packer.toBuffer(doc)
  .then(buf => { fs.writeFileSync("AgriSys_Chapter4_Objectives.docx", buf); console.log("DONE"); })
  .catch(e => { console.error(e); process.exit(1); });
