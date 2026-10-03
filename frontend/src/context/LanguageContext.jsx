import React, { createContext, useContext, useState } from 'react';

export const LANGUAGES = [
  { code: 'en', label: 'English', native: 'English' },
  { code: 'hi', label: 'Hindi', native: 'हिन्दी' },
  { code: 'mr', label: 'Marathi', native: 'मराठी' },
  { code: 'te', label: 'Telugu', native: 'తెలుగు' },
  { code: 'ta', label: 'Tamil', native: 'தமிழ்' },
];

const TRANSLATIONS = {
  en: {
    title: "AgriSys",
    subtitle: "Multi-Agent Agricultural Intelligence",
    nav: {
      chat: "Advisory Chat",
      disease: "Disease Diagnosis",
      nutrition: "Soil & Nutrition",
      market: "Mandi Market",
      weather: "Weather & Irrigation",
      voice: "Voice Studio",
    },
    status: {
      connected: "Backend Connected",
      connecting: "Connecting...",
      offline: "Offline Mode",
    },
    chat: {
      placeholder: "Ask anything about crops, diseases, fertilizer dosing, or mandi prices...",
      send: "Send",
      speak: "Voice Query",
      retrieving: "Searching ICAR Knowledge Base...",
      generating: "Generating Agricultural Advisory...",
      evaluating: "Verifying Hallucination Guard...",
      groundedScore: "Grounding Score",
      sources: "Verified Sources",
      playAudio: "Listen to Advisory",
    },
    disease: {
      title: "Leaf Disease Scanner & Explainable AI",
      dragDrop: "Drag & drop leaf photo here, or click to browse",
      supported: "Supports JPG, PNG (Tomato, Potato, Corn, Wheat, Rice)",
      diagnosing: "Running ResNet-50 & Vision Transformer...",
      result: "Diagnosis Result",
      severity: "Severity Level",
      confidence: "Model Confidence",
      gradcam: "Grad-CAM Heatmap Attention",
      treatments: "Treatment Protocol",
      chemical: "Chemical Control",
      organic: "Bio-Control / Organic",
    },
    nutrition: {
      title: "Soil Health Card & Precision Fertilizer Dosing",
      subtitle: "ICAR 4R Nutrient Stewardship: Right Source, Right Rate, Right Time, Right Place",
      cropSelect: "Select Target Crop",
      calculate: "Compute Fertilizer Dosing",
      dosageTitle: "Commercial Fertilizer Requirements",
      urea: "Urea (46% N)",
      dap: "DAP (18% N, 46% P₂O₅)",
      mop: "MOP (60% K₂O)",
      perAcre: "per acre",
      perHa: "per hectare",
    },
    market: {
      title: "APMC Mandi Market Intelligence & Sell/Hold Advisory",
      commodity: "Select Commodity",
      distance: "Radius (km)",
      fetch: "Get Market Intelligence",
      ranking: "Net Profit Mandi Ranking",
      forecast: "7-Day Price Trajectory Forecast",
      sellHold: "Recommendation",
      modalPrice: "Modal Price",
      freight: "Freight Cost",
      netPrice: "Net Profit",
      mspFloor: "Govt MSP Floor",
    },
    weather: {
      title: "Weather Forecast & FAO-56 Precision Irrigation",
      subtitle: "Penman-Monteith Evapotranspiration and Extreme Agrometeorological Alerts",
      forecast7Day: "7-Day Weather Forecast",
      irrigationTitle: "Precision Irrigation Requirements",
      eto: "Reference Evapotranspiration (ET₀)",
      etc: "Crop Demand (ETc)",
      effRain: "Effective Rainfall (Peff)",
      nir: "Net Irrigation Req (NIR)",
      dripTime: "Recommended Drip Runtime",
      alerts: "Extreme Weather Hazard Alerts",
    },
  },
  hi: {
    title: "एग्रीसिस",
    subtitle: "कृषि बहु-एजेंट सलाहकार प्रणाली",
    nav: {
      chat: "सलाहकार चैट",
      disease: "रोग निदान",
      nutrition: "मृदा एवं उर्वरक",
      market: "मंडी भाव",
      weather: "मौसम व सिंचाई",
      voice: "ध्वनि स्टूडियो",
    },
    status: {
      connected: "सिस्टम कनेक्टेड",
      connecting: "कनेक्ट हो रहा है...",
      offline: "ऑफ़लाइन मोड",
    },
    chat: {
      placeholder: "फसल, कीट-रोग, खाद की मात्रा या मंडी भाव के बारे में पूछें...",
      send: "भेजें",
      speak: "बोलकर पूछें",
      retrieving: "ICAR ज्ञानकोश खोजा जा रहा है...",
      generating: "कृषि सलाह तैयार की जा रही है...",
      evaluating: "तथ्य सत्यापन जांच हो रही है...",
      groundedScore: "सत्यता स्कोर",
      sources: "प्रमाणित स्रोत",
      playAudio: "सलाह सुनें",
    },
    disease: {
      title: "पत्ती रोग पहचान एवं Grad-CAM विज़न",
      dragDrop: "पत्ती का फोटो यहाँ खींचें या अपलोड करने के लिए क्लिक करें",
      supported: "टमाटर, आलू, मक्का, गेहूँ, धान समर्थित",
      diagnosing: "एआई मॉडल पत्ती की जांच कर रहा है...",
      result: "निदान परिणाम",
      severity: "रोग गंभीरता",
      confidence: "सटीकता",
      gradcam: "Grad-CAM हीटमैप ध्यान क्षेत्र",
      treatments: "उपचार विधि",
      chemical: "रासायनिक नियंत्रण",
      organic: "जैविक उपचार",
    },
    nutrition: {
      title: "मृदा स्वास्थ्य कार्ड एवं सटीक उर्वरक खुराक",
      subtitle: "ICAR 4R पोषक तत्व प्रबंधन: सही स्रोत, सही मात्रा, सही समय, सही स्थान",
      cropSelect: "फसल चुनें",
      calculate: "उर्वरक मात्रा निकालें",
      dosageTitle: "अनुशंसित उर्वरक खुराक",
      urea: "यूरिया (46% N)",
      dap: "डीएपी (18% N, 46% P₂O₅)",
      mop: "एमओपी पोटाश (60% K₂O)",
      perAcre: "प्रति एकड़",
      perHa: "प्रति हेक्टेयर",
    },
    market: {
      title: "मंडी भाव विश्लेषण एवं बिक्री सलाह",
      commodity: "फसल चुनें",
      distance: "दूरी (किमी)",
      fetch: "मंडी भाव देखें",
      ranking: "शुद्ध मुनाफा मंडी रैंकिंग",
      forecast: "7 दिवसीय मूल्य पूर्वानुमान",
      sellHold: "सलाह",
      modalPrice: "मंडी भाव",
      freight: "परिवहन खर्च",
      netPrice: "शुद्ध भाव",
      mspFloor: "सरकारी एमएसपी (MSP)",
    },
    weather: {
      title: "मौसम पूर्वानुमान एवं FAO-56 सटीक सिंचाई",
      subtitle: "पेनमैन-मोंटेथ वाष्पीकरण और मौसम चेतावनी प्रणाली",
      forecast7Day: "7 दिवसीय मौसम पूर्वानुमान",
      irrigationTitle: "सिंचाई आवश्यकता",
      eto: "संदर्भ वाष्पोत्सर्जन (ET₀)",
      etc: "फसल जल आवश्यकता (ETc)",
      effRain: "प्रभावी वर्षा",
      nir: "शुद्ध सिंचाई जरूरत",
      dripTime: "ड्रिप चलाने का समय",
      alerts: "मौसम चेतावनी एवं खतरे",
    },
  },
};

const LanguageContext = createContext();

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState('en');

  const t = TRANSLATIONS[language] || TRANSLATIONS['en'];

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t, languages: LANGUAGES }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}
