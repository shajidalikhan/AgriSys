import React, { useState, useEffect } from 'react';
import Navbar from './components/layout/Navbar';
import Sidebar from './components/layout/Sidebar';
import StreamingChat from './components/chat/StreamingChat';
import DiseasePanel from './components/disease/DiseasePanel';
import NutritionPanel from './components/nutrition/NutritionPanel';
import MarketPanel from './components/market/MarketPanel';
import WeatherPanel from './components/weather/WeatherPanel';
import VoiceStudio from './components/voice/VoiceStudio';
import { checkHealth } from './api/client';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [backendOnline, setBackendOnline] = useState(false);

  useEffect(() => {
    const pingBackend = async () => {
      const res = await checkHealth();
      setBackendOnline(!!res);
    };
    pingBackend();
    const interval = setInterval(pingBackend, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleSendToChat = (queryText) => {
    setActiveTab('chat');
  };

  return (
    <div className="h-full flex flex-col bg-slate-950 text-slate-100 overflow-hidden font-sans">
      <Navbar backendOnline={backendOnline} />

      <div className="flex-1 flex overflow-hidden">
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} />

        <main className="flex-1 flex flex-col h-full overflow-hidden bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
          {activeTab === 'chat' && <StreamingChat />}
          {activeTab === 'disease' && <DiseasePanel />}
          {activeTab === 'nutrition' && <NutritionPanel />}
          {activeTab === 'market' && <MarketPanel />}
          {activeTab === 'weather' && <WeatherPanel />}
          {activeTab === 'voice' && <VoiceStudio onSendToChat={handleSendToChat} />}
        </main>
      </div>

      {/* Mobile Tab Bar */}
      <div className="md:hidden border-t border-slate-800 bg-slate-900/90 backdrop-blur-md p-2 flex justify-around text-xs">
        <button
          onClick={() => setActiveTab('chat')}
          className={`px-3 py-1.5 rounded-lg ${activeTab === 'chat' ? 'text-emerald-400 font-bold bg-slate-800' : 'text-slate-400'}`}
        >
          Chat
        </button>
        <button
          onClick={() => setActiveTab('disease')}
          className={`px-3 py-1.5 rounded-lg ${activeTab === 'disease' ? 'text-emerald-400 font-bold bg-slate-800' : 'text-slate-400'}`}
        >
          Disease
        </button>
        <button
          onClick={() => setActiveTab('nutrition')}
          className={`px-3 py-1.5 rounded-lg ${activeTab === 'nutrition' ? 'text-emerald-400 font-bold bg-slate-800' : 'text-slate-400'}`}
        >
          Nutrition
        </button>
        <button
          onClick={() => setActiveTab('market')}
          className={`px-3 py-1.5 rounded-lg ${activeTab === 'market' ? 'text-emerald-400 font-bold bg-slate-800' : 'text-slate-400'}`}
        >
          Market
        </button>
        <button
          onClick={() => setActiveTab('weather')}
          className={`px-3 py-1.5 rounded-lg ${activeTab === 'weather' ? 'text-emerald-400 font-bold bg-slate-800' : 'text-slate-400'}`}
        >
          Weather
        </button>
        <button
          onClick={() => setActiveTab('voice')}
          className={`px-3 py-1.5 rounded-lg ${activeTab === 'voice' ? 'text-emerald-400 font-bold bg-slate-800' : 'text-slate-400'}`}
        >
          Voice
        </button>
      </div>
    </div>
  );
}
