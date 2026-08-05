// frontend/src/components/layout/SettingsSidebar.tsx
import { SettingsSidebarProps } from "../../types";
import { supabase } from "../../utils/supabaseClient";

export default function SettingsSidebar({ 
  isOpen, 
  onClose, 
  settings, 
  updateSetting 
}: SettingsSidebarProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm transition-opacity animate-fade-in">
      <div className="w-full max-w-md bg-slate-900 h-full border-l border-slate-800 shadow-2xl p-6 flex flex-col overflow-y-auto">
        
        {/* Header - Upgraded with an SVG Gear */}
        <div className="flex justify-between items-center mb-8 pb-4 border-b border-slate-800">
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            <svg className="w-6 h-6 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            Settings & Controls
          </h2>
          <button onClick={onClose} className="text-slate-500 hover:text-white text-3xl font-light p-2 transition-colors">
            &times;
          </button>
        </div>

        <div className="space-y-8 flex-1">
          {/* 1. Language Selection */}
          <div className="space-y-3">
            <label className="text-slate-300 font-semibold text-lg block">App Language</label>
            <div className="grid grid-cols-2 gap-3">
              {["English", "Hindi", "Marathi", "Tamil"].map((lang) => (
                <button
                  key={lang}
                  onClick={() => updateSetting("language", lang)}
                  className={`py-3 rounded-xl font-bold transition-all text-sm ${
                    settings.language === lang 
                    ? "bg-blue-600 text-white shadow-md border-2 border-blue-400" 
                    : "bg-slate-800 text-slate-300 border border-slate-700 hover:bg-slate-700"
                  }`}
                >
                  {lang}
                </button>
              ))}
            </div>
          </div>

          {/* 2. Text Size */}
          <div className="space-y-3">
            <label className="text-slate-300 font-semibold text-lg block">Text Size</label>
            <div className="flex bg-slate-800 rounded-xl p-1 border border-slate-700">
              {[
                { id: "normal", label: "Standard", size: "text-sm" },
                { id: "large", label: "Large", size: "text-base" },
                { id: "xl", label: "X-Large", size: "text-lg" }
              ].map((opt) => (
                <button
                  key={opt.id}
                  onClick={() => updateSetting("fontSize", opt.id as "normal"|"large"|"xl")}
                  className={`flex-1 py-3 rounded-lg font-medium transition-all ${opt.size} ${
                    settings.fontSize === opt.id ? "bg-slate-700 text-white shadow" : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* 3. Voice Speed */}
          <div className="space-y-3">
            <label className="text-slate-300 font-semibold text-lg block">AI Voice Speed</label>
            <div className="space-y-2">
              {[
                { speed: 1.0, label: "Normal Pace (1.0x)" },
                { speed: 0.8, label: "Slow & Clear (0.8x)" },
                { speed: 0.6, label: "Very Slow (0.6x)" }
              ].map((opt) => (
                <label key={opt.speed} className="flex items-center space-x-3 bg-slate-800 p-4 rounded-xl border border-slate-700 cursor-pointer hover:bg-slate-700 transition-colors">
                  <input 
                    type="radio" 
                    name="voiceSpeed" 
                    checked={settings.voiceSpeed === opt.speed}
                    onChange={() => updateSetting("voiceSpeed", opt.speed)}
                    className="w-5 h-5 text-blue-600 focus:ring-blue-500 bg-slate-900 border-slate-600"
                  />
                  <span className="text-white font-medium">{opt.label}</span>
                </label>
              ))}
            </div>
          </div>
        </div>

        {/* Footer: Sign Out Button - Upgraded with an SVG Log Out Icon */}
        <div className="mt-8 pt-6 border-t border-slate-800 space-y-4">
          <button 
            onClick={() => supabase.auth.signOut()}
            className="w-full bg-slate-800/50 hover:bg-red-500/10 border border-slate-700/50 hover:border-red-500/30 text-slate-400 hover:text-red-400 py-4 rounded-xl font-semibold text-base transition-all flex items-center justify-center gap-3"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            Sign Out
          </button>
        </div>

      </div>
    </div>
  );
}