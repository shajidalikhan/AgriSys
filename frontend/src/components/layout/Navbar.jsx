import React from 'react';
import { Sprout, Globe, Activity, ShieldCheck } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';

export default function Navbar({ backendOnline }) {
  const { language, setLanguage, languages, t } = useLanguage();

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-900/90 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-30">
      {/* Brand logo & title */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-green-400 flex items-center justify-center shadow-lg shadow-emerald-500/20">
          <Sprout className="w-6 h-6 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-emerald-400 to-green-200 bg-clip-text text-transparent font-heading">
              AgriSys
            </h1>
            <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              v1.0 • ICAR Grounded
            </span>
          </div>
          <p className="text-xs text-slate-400 hidden sm:block">
            {t.subtitle}
          </p>
        </div>
      </div>

      {/* Controls: Connection Status & Language Switcher */}
      <div className="flex items-center gap-4">
        {/* Backend Status Pill */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/80 border border-slate-700/60 text-xs">
          <span className="relative flex h-2 w-2">
            <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${backendOnline ? 'bg-emerald-400' : 'bg-amber-400'}`}></span>
            <span className={`relative inline-flex rounded-full h-2 w-2 ${backendOnline ? 'bg-emerald-500' : 'bg-amber-500'}`}></span>
          </span>
          <span className={backendOnline ? 'text-emerald-400 font-medium' : 'text-slate-400'}>
            {backendOnline ? t.status.connected : t.status.connecting}
          </span>
        </div>

        {/* Vernacular Language Selector */}
        <div className="flex items-center gap-2 bg-slate-800/80 border border-slate-700/60 rounded-lg px-2.5 py-1">
          <Globe className="w-4 h-4 text-emerald-400" />
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="bg-transparent text-sm font-medium text-slate-200 focus:outline-none cursor-pointer"
          >
            {languages.map((l) => (
              <option key={l.code} value={l.code} className="bg-slate-900 text-slate-200">
                {l.native} ({l.label})
              </option>
            ))}
          </select>
        </div>
      </div>
    </header>
  );
}
