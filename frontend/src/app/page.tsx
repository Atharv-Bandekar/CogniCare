// frontend/src/app/page.tsx
"use client";

import { useState, useEffect } from "react";
import { supabase } from "../utils/supabaseClient";
import { uiTranslations } from "../utils/translations";
import { useSettings } from "../hooks/useSettings";

// Clean architectural imports
import AuthScreen from "../components/auth/AuthScreen";
import CheckInTab from "../components/features/CheckInTab";
import DashboardTab from "../components/features/DashboardTab";
import SettingsSidebar from "../components/layout/SettingsSidebar";

const fontClasses: Record<string, string> = {
  normal: "text-base",
  large: "text-lg",
  xl: "text-xl leading-relaxed"
};

export default function Home() {
  const [session, setSession] = useState<any>(null);
  const [loadingSession, setLoadingSession] = useState(true);
  const [activeTab, setActiveTab] = useState("checkin");
  
  // Bring in the persistent settings hook
  const { settings, updateSetting, isLoaded } = useSettings();
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setLoadingSession(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setLoadingSession(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  if (loadingSession || !isLoaded) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400">
        Loading session...
      </div>
    );
  }

  if (!session) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 p-8 font-sans">
        <AuthScreen />
      </div>
    );
  }

  const currentLang = settings.language || "English";
  const t = uiTranslations[currentLang] || uiTranslations["English"];

  return (
    <div className={`min-h-screen bg-slate-950 text-slate-100 p-8 font-sans ${fontClasses[settings.fontSize]}`}>
      <div className="max-w-4xl mx-auto relative">

        {/* Header with App Title and Settings Button */}
        <div className="flex justify-between items-center mb-10 mt-4">
          <h1 className="text-3xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-400 tracking-tight">
            CogniCare AI
          </h1>
          
          <button 
            onClick={() => setIsSettingsOpen(true)}
            className="group flex items-center gap-2 bg-slate-900/50 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 text-slate-300 px-5 py-2.5 rounded-full text-sm font-medium transition-all shadow-sm"
          >
            <svg 
              className="w-4 h-4 text-slate-400 group-hover:text-blue-400 group-hover:rotate-45 transition-all duration-300 ease-in-out" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24" 
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            {t.settingsBtn} {/* <--- Update this! */}
          </button>
          
        </div>

        {/* Navigation Tabs */}
        <div className="flex space-x-4 border-b border-slate-800 mb-8">
          <button 
            className={`pb-2 px-4 whitespace-nowrap transition-colors ${activeTab === "checkin" ? "border-b-2 border-blue-500 text-blue-400 font-semibold" : "text-slate-400"}`}
            onClick={() => setActiveTab("checkin")}
          >
            {t.checkInTab}
          </button>
          <button 
            className={`pb-2 px-4 whitespace-nowrap transition-colors ${activeTab === "dashboard" ? "border-b-2 border-blue-500 text-blue-400 font-semibold" : "text-slate-400"}`}
            onClick={() => setActiveTab("dashboard")}
          >
            {t.dashboardTab}
          </button>
        </div>

        {/* Active Tab Routing */}
        {activeTab === "checkin" ? (
          <CheckInTab language={currentLang} t={t} session={session} />
        ) : (
          <DashboardTab session={session} />
        )}

      </div>

      {/* Global Accessibility Sidebar */}
      <SettingsSidebar 
        isOpen={isSettingsOpen} 
        onClose={() => setIsSettingsOpen(false)}
        settings={settings}
        updateSetting={updateSetting}
        language={currentLang}
        session={session}
      />
    </div>
  );
}