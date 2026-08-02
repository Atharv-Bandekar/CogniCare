"use client";

import { useState, useEffect } from "react";

export default function Home() {
  const [activeTab, setActiveTab] = useState("checkin");
  const [language, setLanguage] = useState("English");
  const [question, setQuestion] = useState("");
  const [userResponse, setUserResponse] = useState("");
  const [status, setStatus] = useState("Click 'Get Question' to start.");
  const [isLoading, setIsLoading] = useState(false);
  const [activityPlan, setActivityPlan] = useState<any>(null);

  // Function to fetch a question from FastAPI
  const fetchQuestion = async () => {
    setIsLoading(true);
    setStatus("Thinking of a question for you...");
    setActivityPlan(null);
    setUserResponse("");
    
    try {
      const res = await fetch("http://localhost:8000/api/question", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language }),
      });
      const data = await res.json();
      setQuestion(data.question);
      setStatus("Please answer below:");
    } catch (error) {
      setStatus("Error connecting to backend.");
    }
    setIsLoading(false);
  };

  // Function to submit the answer to FastAPI
  const submitAnswer = async () => {
    if (!userResponse) return alert("Please provide an answer first.");
    
    setIsLoading(true);
    setStatus("Analyzing your response...");
    
    try {
      const res = await fetch("http://localhost:8000/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language, question, user_response: userResponse }),
      });
      const data = await res.json();
      setActivityPlan(data.activity_plan);
      setStatus(`Detected mood: ${data.evaluation.sentiment_label} | Engagement: ${data.evaluation.engagement_level}`);
    } catch (error) {
      setStatus("Error analyzing response.");
    }
    setIsLoading(false);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-8 font-sans">
      <div className="max-w-4xl mx-auto">
        
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-blue-400">CogniCare AI</h1>
          <select 
            className="bg-slate-800 border border-slate-700 text-white rounded px-4 py-2"
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
            className={`pb-2 px-4 ${activeTab === "checkin" ? "border-b-2 border-blue-500 text-blue-400" : "text-slate-400"}`}
            onClick={() => setActiveTab("checkin")}
          >
            Daily Check-In
          </button>
          <button 
            className={`pb-2 px-4 ${activeTab === "dashboard" ? "border-b-2 border-blue-500 text-blue-400" : "text-slate-400"}`}
            onClick={() => setActiveTab("dashboard")}
          >
            Caregiver Dashboard
          </button>
        </div>

        {/* Main Content Area */}
        {activeTab === "checkin" && (
          <div className="space-y-6">
            <p className="text-slate-400 italic">{status}</p>

            {/* Question Card */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center shadow-lg">
              {question ? (
                <h2 className="text-2xl font-semibold">{question}</h2>
              ) : (
                <button 
                  onClick={fetchQuestion}
                  disabled={isLoading}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium transition-colors"
                >
                  Generate Today's Question
                </button>
              )}
            </div>

            {/* Input Area */}
            {question && !activityPlan && (
              <div className="space-y-4">
                <textarea 
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl p-4 text-white min-h-[120px] focus:ring-2 focus:ring-blue-500 outline-none"
                  placeholder="Type your response here..."
                  value={userResponse}
                  onChange={(e) => setUserResponse(e.target.value)}
                />
                <button 
                  onClick={submitAnswer}
                  disabled={isLoading}
                  className="w-full bg-green-600 hover:bg-green-700 text-white px-6 py-4 rounded-xl font-bold text-lg transition-colors"
                >
                  {isLoading ? "Processing..." : "Submit Answer"}
                </button>
              </div>
            )}

            {/* Results / Activity Plan */}
            {activityPlan && (
              <div className="bg-slate-800 border border-blue-500/30 rounded-xl p-6 mt-6">
                <h3 className="text-xl font-bold mb-4 text-blue-300">Recommended Activities for Today:</h3>
                <div className="space-y-4">
                  <p><strong>🌅 Morning:</strong> {activityPlan.morning_activity}</p>
                  <p><strong>☀️ Afternoon:</strong> {activityPlan.afternoon_activity}</p>
                  <p><strong>🌙 Evening:</strong> {activityPlan.evening_activity}</p>
                  <div className="mt-4 p-4 bg-slate-900/50 rounded-lg text-sm text-slate-300">
                    <strong>💡 Caregiver Note:</strong> {activityPlan.caregiver_rationale}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Placeholder for Dashboard Tab */}
        {activeTab === "dashboard" && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center">
            <h2 className="text-xl text-slate-300 mb-2">Caregiver Dashboard</h2>
            <p className="text-slate-500">History will populate here from Supabase.</p>
          </div>
        )}

      </div>
    </div>
  );
}