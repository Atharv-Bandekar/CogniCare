"use client";

import { useState, useEffect, useRef } from "react";

// Translation Dictionary
const uiTranslations: Record<string, any> = {
  English: {
    checkInTab: "Daily Check-In",
    dashboardTab: "Caregiver Dashboard",
    generateBtn: "Generate Today's Question",
    speakBtn: "🎤 Speak Answer",
    stopBtn: "⏹ Stop Recording",
    submitBtn: "Submit Answer",
    loading: "Processing...",
  },
  Hindi: {
    checkInTab: "दैनिक चेक-इन",
    dashboardTab: "देखभालकर्ता डैशबोर्ड",
    generateBtn: "आज का प्रश्न प्राप्त करें",
    speakBtn: "🎤 उत्तर बोलें",
    stopBtn: "⏹ रिकॉर्डिंग रोकें",
    submitBtn: "उत्तर सबमिट करें",
    loading: "प्रोसेस हो रहा है...",
  },
  Marathi: {
    checkInTab: "दैनंदिन चेक-इन",
    dashboardTab: "केअरगिव्हर डॅशबोर्ड",
    generateBtn: "आजचा प्रश्न मिळवा",
    speakBtn: "🎤 उत्तर बोला",
    stopBtn: "⏹ रेकॉर्डिंग थांबवा",
    submitBtn: "उत्तर पाठवा",
    loading: "प्रक्रिया सुरू आहे...",
  },
  Tamil: {
    checkInTab: "தினசரி சரிபார்ப்பு",
    dashboardTab: "பராமரிப்பாளர் டாஷ்போர்டு",
    generateBtn: "இன்றைய கேள்வியை உருவாக்கு",
    speakBtn: "🎤 பதிலை பேசு",
    stopBtn: "⏹ பதிவை நிறுத்து",
    submitBtn: "பதிலைச் சமர்ப்பி",
    loading: "செயலாக்கப்படுகிறது...",
  }
};

export default function Home() {
  const [activeTab, setActiveTab] = useState("checkin");
  const [language, setLanguage] = useState("English");
  const [question, setQuestion] = useState("");
  const [userResponse, setUserResponse] = useState("");
  const [status, setStatus] = useState("Click 'Get Question' to start.");
  const [isLoading, setIsLoading] = useState(false);
  const [activityPlan, setActivityPlan] = useState<any>(null);
  const [isRecording, setIsRecording] = useState(false);
  
  // New state for the dashboard history
  const [history, setHistory] = useState<any[]>([]);
  const [isFetchingHistory, setIsFetchingHistory] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<BlobPart[]>([]);

  // --- Helper to safely render LLM output ---
  const renderActivity = (activity: any) => {
    if (!activity) return "No activity suggested.";
    if (typeof activity === "string") return activity;
    if (typeof activity === "object") {
      const title = activity.title ? `**${activity.title}**: ` : "";
      const desc = activity.description || "";
      const dur = activity.duration ? ` (${activity.duration})` : "";
      return `${title}${desc}${dur}`;
    }
    return JSON.stringify(activity);
  };

  const speakText = (text: string, lang: string) => {
    if (!("speechSynthesis" in window)) return;
    const locales: Record<string, string> = { English: "en-US", Hindi: "hi-IN", Marathi: "mr-IN", Tamil: "ta-IN" };
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = locales[lang] || "en-US";
    window.speechSynthesis.speak(utterance);
  };

  const fetchQuestion = async () => {
    setIsLoading(true);
    setStatus("Thinking of a question for you...");
    setActivityPlan(null);
    setUserResponse("");
    
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/question`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language }),
      });
      const data = await res.json();
      setQuestion(data.question);
      setStatus("Please answer below:");
      speakText(data.question, language);
    } catch (error) {
      setStatus("Error connecting to backend.");
    }
    setIsLoading(false);
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        await uploadAudioForTranscription(audioBlob);
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
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/transcribe`, {
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

  const submitAnswer = async () => {
    if (!userResponse) return alert("Please provide an answer first.");
    setIsLoading(true);
    setStatus("Analyzing your response...");
    
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ language, question, user_response: userResponse }),
      });
      const data = await res.json();
      setActivityPlan(data.activity_plan);
      setStatus(`Detected mood: ${data.evaluation.sentiment_label} | Engagement: ${data.evaluation.engagement_level}`);
      speakText("I have created a personalized activity plan for you. Check the screen for details.", language);
    } catch (error) {
      setStatus("Error analyzing response.");
    }
    setIsLoading(false);
  };

  // --- Fetch History Logic ---
  const loadHistory = async () => {
    setIsFetchingHistory(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/history`);
      const data = await res.json();
      setHistory(data.history || []);
    } catch (error) {
      console.error("Failed to load history", error);
    }
    setIsFetchingHistory(false);
  };

  // Automatically fetch history when the Dashboard tab is clicked
  useEffect(() => {
    if (activeTab === "dashboard") {
      loadHistory();
    }
  }, [activeTab]);

  // Grab the current language translations for easy usage
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

        {/* Check-in Tab */}
        {activeTab === "checkin" && (
          <div className="space-y-6">
            <p className="text-slate-400 italic">{status}</p>

            <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center shadow-lg">
              {question ? (
                <h2 className="text-2xl font-semibold leading-relaxed">{question}</h2>
              ) : (
                <button 
                  onClick={fetchQuestion}
                  disabled={isLoading}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-4 rounded-lg font-medium transition-colors break-words min-h-[64px]"
                >
                  {t.generateBtn}
                </button>
              )}
            </div>

            {question && !activityPlan && (
              <div className="space-y-4">
                <textarea 
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl p-4 text-white min-h-[120px] focus:ring-2 focus:ring-blue-500 outline-none"
                  placeholder="Type your response here or use the microphone..."
                  value={userResponse}
                  onChange={(e) => setUserResponse(e.target.value)}
                />
                
                {/* Armored Button Container */}
                <div className="flex flex-col sm:flex-row space-y-4 sm:space-y-0 sm:space-x-4">
                  <button 
                    onClick={isRecording ? stopRecording : startRecording}
                    className={`flex-1 ${isRecording ? 'bg-red-600 hover:bg-red-700' : 'bg-slate-800 hover:bg-slate-700 border border-slate-600'} text-white px-6 py-4 rounded-xl font-bold text-lg transition-colors flex items-center justify-center break-words min-h-[64px] leading-tight`}
                  >
                    {isRecording ? t.stopBtn : t.speakBtn}
                  </button>

                  <button 
                    onClick={submitAnswer}
                    disabled={isLoading || isRecording}
                    className="flex-1 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white px-6 py-4 rounded-xl font-bold text-lg transition-colors break-words min-h-[64px] leading-tight flex items-center justify-center"
                  >
                    {isLoading && !isRecording ? t.loading : t.submitBtn}
                  </button>
                </div>
              </div>
            )}

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
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-blue-300 mb-4">Patient History & Trends</h2>
            
            {isFetchingHistory ? (
              <p className="text-slate-400">Loading history from database...</p>
            ) : history.length === 0 ? (
              <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center">
                <p className="text-slate-500">No interaction history found yet.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {history.map((entry, index) => (
                  <div key={index} className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-lg">
                    
                    {/* Timestamp & Mood Badge */}
                    <div className="flex justify-between items-start mb-4 border-b border-slate-800 pb-4">
                      <span className="text-slate-400 text-sm">
                        {new Date(entry.timestamp).toLocaleString()}
                      </span>
                      <div className="flex space-x-2">
                        <span className="bg-slate-800 text-slate-300 px-3 py-1 rounded-full text-sm border border-slate-700">
                          Mood: {entry.sentiment_label || "Unknown"}
                        </span>
                        <span className="bg-slate-800 text-slate-300 px-3 py-1 rounded-full text-sm border border-slate-700">
                          Engagement: {entry.engagement_level || "Unknown"}
                        </span>
                      </div>
                    </div>

                    {/* Q & A */}
                    <div className="space-y-3 mb-4">
                      <div>
                        <strong className="text-blue-400 block text-sm mb-1">AI Question:</strong>
                        <p className="text-slate-200">{entry.question}</p>
                      </div>
                      <div>
                        <strong className="text-green-400 block text-sm mb-1">User Answer:</strong>
                        <p className="text-slate-300 italic">"{entry.response}"</p>
                      </div>
                    </div>

                  </div>
                ))}
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}