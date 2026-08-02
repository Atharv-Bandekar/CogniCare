"use client";

import { useState, useRef } from "react";

export default function Home() {
  const [activeTab, setActiveTab] = useState("checkin");
  const [language, setLanguage] = useState("English");
  const [question, setQuestion] = useState("");
  const [userResponse, setUserResponse] = useState("");
  const [status, setStatus] = useState("Click 'Get Question' to start.");
  const [isLoading, setIsLoading] = useState(false);
  const [activityPlan, setActivityPlan] = useState<any>(null);
  const [isRecording, setIsRecording] = useState(false);

  // Refs for Audio Recording
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<BlobPart[]>([]);

  // --- Helper to safely render LLM output ---
  const renderActivity = (activity: any) => {
    if (!activity) return "No activity suggested.";
    if (typeof activity === "string") return activity;
    
    // If the LLM returns a nested object (like {title, description, duration})
    if (typeof activity === "object") {
      const title = activity.title ? `**${activity.title}**: ` : "";
      const desc = activity.description || "";
      const dur = activity.duration ? ` (${activity.duration})` : "";
      return `${title}${desc}${dur}`;
    }
    
    return JSON.stringify(activity); // Ultimate fallback
  };

  // --- Text-to-Speech (Browser Native) ---
  const speakText = (text: string, lang: string) => {
    if (!("speechSynthesis" in window)) return;
    
    // Map dropdown languages to browser locales
    const locales: Record<string, string> = {
      English: "en-US",
      Hindi: "hi-IN",
      Marathi: "mr-IN",
      Tamil: "ta-IN"
    };

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = locales[lang] || "en-US";
    window.speechSynthesis.speak(utterance);
  };

  // --- Agent 1: Fetch Question ---
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
      
      // Read the question out loud!
      speakText(data.question, language);
    } catch (error) {
      setStatus("Error connecting to backend.");
    }
    setIsLoading(false);
  };

  // --- Microphone Recording Logic ---
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        await uploadAudioForTranscription(audioBlob);
        // Stop the microphone tracks to turn off the red recording dot in the browser tab
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      setStatus("Recording... Click stop when finished.");
    } catch (error) {
      console.error("Error accessing mic:", error);
      alert("Microphone access denied. Please allow mic permissions in your browser.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const uploadAudioForTranscription = async (blob: Blob) => {
    setIsLoading(true);
    setStatus("Transcribing audio via Groq Whisper...");
    const formData = new FormData();
    formData.append("audio", blob, "recording.webm");

    try {
      const res = await fetch("http://localhost:8000/api/transcribe", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (data.text) {
        setUserResponse(data.text);
        setStatus("Audio transcribed! You can edit the text or submit it.");
      }
    } catch (error) {
      setStatus("Error transcribing audio.");
    }
    setIsLoading(false);
  };

  // --- Agents 2 & 3: Submit Answer ---
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
      
      // Read a quick summary out loud
      speakText("I have created a personalized activity plan for you. Check the screen for details.", language);
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
                <h2 className="text-2xl font-semibold leading-relaxed">{question}</h2>
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
                  placeholder="Type your response here or use the microphone..."
                  value={userResponse}
                  onChange={(e) => setUserResponse(e.target.value)}
                />
                
                <div className="flex space-x-4">
                  {/* Microphone Button */}
                  <button 
                    onClick={isRecording ? stopRecording : startRecording}
                    className={`flex-1 ${isRecording ? 'bg-red-600 hover:bg-red-700' : 'bg-slate-800 hover:bg-slate-700 border border-slate-600'} text-white px-6 py-4 rounded-xl font-bold text-lg transition-colors flex items-center justify-center`}
                  >
                    {isRecording ? "⏹ Stop Recording" : "🎤 Speak Answer"}
                  </button>

                  {/* Submit Button */}
                  <button 
                    onClick={submitAnswer}
                    disabled={isLoading || isRecording}
                    className="flex-1 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white px-6 py-4 rounded-xl font-bold text-lg transition-colors"
                  >
                    {isLoading && !isRecording ? "Processing..." : "Submit Answer"}
                  </button>
                </div>
              </div>
            )}

            {/* Results / Activity Plan */}
            {activityPlan && (
              <div className="bg-slate-800 border border-blue-500/30 rounded-xl p-6 mt-6 shadow-xl">
                <h3 className="text-xl font-bold mb-4 text-blue-300">Recommended Activities for Today:</h3>
                <div className="space-y-4 text-slate-200">
                  <p><span className="text-xl mr-2">🌅</span> <strong>Morning:</strong> {renderActivity(activityPlan.morning_activity)}</p>
                  <p><span className="text-xl mr-2">☀️</span> <strong>Afternoon:</strong> {renderActivity(activityPlan.afternoon_activity)}</p>
                  <p><span className="text-xl mr-2">🌙</span> <strong>Evening:</strong> {renderActivity(activityPlan.evening_activity)}</p>
                  <div className="mt-6 p-4 bg-slate-900/50 border border-slate-700 rounded-lg text-sm text-slate-400">
                    <strong>💡 Caregiver Note:</strong> {
                      typeof activityPlan.caregiver_rationale === "string" 
                        ? activityPlan.caregiver_rationale 
                        : JSON.stringify(activityPlan.caregiver_rationale)
                    }
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Dashboard Tab */}
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