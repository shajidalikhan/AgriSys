import React from 'react';
import {
  MessageSquareQuote,
  ScanEye,
  FlaskConical,
  TrendingUp,
  CloudSunRain,
  Mic,
} from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';

export default function Sidebar({ activeTab, setActiveTab }) {
  const { t } = useLanguage();

  const NAV_ITEMS = [
    { id: 'chat', label: t.nav.chat, icon: MessageSquareQuote },
    { id: 'disease', label: t.nav.disease, icon: ScanEye },
    { id: 'nutrition', label: t.nav.nutrition, icon: FlaskConical },
    { id: 'market', label: t.nav.market, icon: TrendingUp },
    { id: 'weather', label: t.nav.weather, icon: CloudSunRain },
    { id: 'voice', label: t.nav.voice, icon: Mic },
  ];

  return (
    <aside className="w-64 border-r border-slate-800 bg-slate-900/60 p-4 flex flex-col justify-between hidden md:flex">
      <nav className="space-y-1.5">
        <div className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Agent Workspace
        </div>
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl font-medium text-sm transition-all duration-150 ${
                isActive
                  ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Icon className={`w-5 h-5 ${isActive ? 'text-emerald-400' : 'text-slate-400'}`} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Footer System Info */}
      <div className="p-3 rounded-xl bg-slate-800/40 border border-slate-800 text-xs text-slate-400">
        <div className="font-semibold text-slate-300">AgriSys LangGraph</div>
        <div className="text-[11px] text-slate-400 mt-0.5">
          6 Autonomous Specialists with Hallucination Guard
        </div>
      </div>
    </aside>
  );
}
