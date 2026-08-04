// frontend/src/app/page.tsx
"use client";

import { useState, useEffect } from "react";
import { supabase } from "../utils/supabaseClient";
import { uiTranslations } from "../utils/translations";
import CheckInTab from "../components/CheckInTab";
import DashboardTab from "../components/DashboardTab";
import AuthScreen from "../components/AuthScreen";

export default function Home() {
  const [session, setSession] = useState<any>(null);
  const [loadingSession, setLoadingSession] = useState(true);
  const [activeTab, setActiveTab] = useState("checkin");
  const [language, setLanguage] = useState("English");

  useEffect(() => {
    // 1. Check current session on mount
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setLoadingSession(false);
    });

    // 2. Listen for login/logout changes dynamically
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setLoadingSession(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  if (loadingSession) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400">
        Loading session...
      </div>
    );
  }

  // If user is not authenticated, render the secure login/signup screen
  if (!session) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 p-8 font-sans">
        <AuthScreen />
      </div>
    );
  }

  const t = uiTranslations[language] || uiTranslations["English"];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-8 font-sans">
      <div className="max-w-4xl mx-auto">
        
        {/* Header with Logout Button */}
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-blue-400">CogniCare AI</h1>
          
          <div className="flex items-center space-x-4">
            <select 
              className="bg-slate-800 border border-slate-700 text-white rounded px-4 py-2 outline-none"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
            >
              <option>English</option>
              <option>Hindi</option>
              <option>Marathi</option>
              <option>Tamil</option>
            </select>

            <button 
              onClick={() => supabase.auth.signOut()}
              className="bg-slate-800 hover:bg-red-900/40 border border-slate-700 text-slate-300 hover:text-red-300 px-4 py-2 rounded-lg text-sm transition-colors"
            >
              Sign Out
            </button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex space-x-4 border-b border-slate-800 mb-8">
          <button 
            className={`pb-2 px-4 whitespace-nowrap transition-colors ${activeTab === "checkin" ? "border-b-2 border-blue-500 text-blue-400" : "text-slate-400"}`}
            onClick={() => setActiveTab("checkin")}
          >
            {t.checkInTab}
          </button>
          <button 
            className={`pb-2 px-4 whitespace-nowrap transition-colors ${activeTab === "dashboard" ? "border-b-2 border-blue-500 text-blue-400" : "text-slate-400"}`}
            onClick={() => setActiveTab("dashboard")}
          >
            {t.dashboardTab}
          </button>
        </div>

        {/* Active Tab Routing (Passing session token for secure API requests) */}
        {activeTab === "checkin" ? (
          <CheckInTab language={language} t={t} session={session} />
        ) : (
          <DashboardTab session={session} />
        )}

      </div>
    </div>
  );
}