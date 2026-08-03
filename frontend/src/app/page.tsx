// frontend/src/app/page.tsx
"use client";

import { useState } from "react";
import { uiTranslations } from "../utils/translations";
import CheckInTab from "../components/CheckInTab";
import DashboardTab from "../components/DashboardTab";

export default function Home() {
  const [activeTab, setActiveTab] = useState("checkin");
  const [language, setLanguage] = useState("English");

  // Grab the current language translations for the header/tabs
  const t = uiTranslations[language] || uiTranslations["English"];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-8 font-sans">
      <div className="max-w-4xl mx-auto">
        
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-blue-400">CogniCare AI</h1>
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

        {/* Active Tab Routing */}
        {activeTab === "checkin" ? (
          <CheckInTab language={language} t={t} />
        ) : (
          <DashboardTab />
        )}

      </div>
    </div>
  );
}