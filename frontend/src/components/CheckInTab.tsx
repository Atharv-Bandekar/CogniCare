import { useState, useEffect, useRef } from "react";

/**
 * CheckInTab Component Props
 * @property {string} language - The currently selected language (e.g., "English", "Tamil")
 * @property {Record<string, string>} t - The active translation dictionary for UI elements
 * @property {any} session - The active Supabase user session token
 */
interface CheckInTabProps {
  language: string;
  t: Record<string, string>;
  session: any;
}

export default function CheckInTab({ language, t, session }: CheckInTabProps) {
  // --- UI & Assessment State ---
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [status, setStatus] = useState<string>("Click 'Generate' to start.");
  const [question, setQuestion] = useState<string>("");
  const [userResponse, setUserResponse] = useState<string>("");
  const [activityPlan, setActivityPlan] = useState<any>(null);
  
  // --- Workflow Control State ---
  const [hasCheckedInToday, setHasCheckedInToday] = useState<boolean>(false);
  const [isCheckingStatus, setIsCheckingStatus] = useState<boolean>(true);

  // --- Audio Recording State & Refs ---
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<BlobPart[]>([]);

  /**
   * Fetches high-quality Cloud TTS audio from our FastAPI backend
   */
  const speakText = (text: string, lang: string) => {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    
    const utterance = new SpeechSynthesisUtterance(text);
    
    const langMap: Record<string, string> = {
      "Hindi": "hi-IN",
      "Marathi": "mr-IN",
      "Tamil": "ta-IN",
      "English": "en-US"
    };
    
    const targetLangCode = langMap[lang] || "en-US";
    utterance.lang = targetLangCode;
    utterance.rate = 0.9; // Slightly slower for better comprehension

    const voices = window.speechSynthesis.getVoices();
    const matchingVoice = 
      voices.find(v => v.lang === targetLangCode) || 
      voices.find(v => v.lang.startsWith(targetLangCode.split('-')[0])) ||
      voices.find(v => v.name.toLowerCase().includes(lang.toLowerCase()));
    
    if (matchingVoice) {
      utterance.voice = matchingVoice;
    }

    window.speechSynthesis.speak(utterance);
  };

  /**
   * Browser Hack: Force the speech engine to load voices into memory immediately
   * when the component mounts, rather than waiting for the first click.
   */
  useEffect(() => {
    if (typeof window !== "undefined" && window.speechSynthesis) {
      window.speechSynthesis.getVoices();
      window.speechSynthesis.onvoiceschanged = () => {
        window.speechSynthesis.getVoices();
      };
    }
  }, []);

  /**
   * Initialization Hook: Checks if the user already completed today's assessment.
   */
  useEffect(() => {
    const checkTodayStatus = async () => {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/history`, {
          headers: { "Authorization": `Bearer ${session?.access_token}` }
        });
        const data = await res.json();
        
        if (data.history && data.history.length > 0) {
          const latestEntry = data.history[0];
          const latestDate = new Date(latestEntry.timestamp).toDateString();
          const todayDate = new Date().toDateString();

          // if (latestDate === todayDate && latestEntry.activity_plan) {
          if(false){
            setHasCheckedInToday(true);
            setActivityPlan(latestEntry.activity_plan);
          }
        }
      } catch (error) {
        console.error("Failed to verify today's status:", error);
      } finally {
        setIsCheckingStatus(false);
      }
    };

    if (session?.access_token) checkTodayStatus();
  }, [session]);

  /**
   * Fetches the daily question from the AI.
   */
  const fetchQuestion = async () => {
    setIsLoading(true);
    setStatus("Thinking of a question for you...");
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/question`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${session?.access_token}` 
        },
        body: JSON.stringify({ language }),
      });
      const data = await res.json();
      setQuestion(data.question);
      setStatus("Please answer below:");
      speakText(data.question, language);
    } catch (error) {
      setStatus("Error connecting to backend.");
    } finally {
      setIsLoading(false);
    }
  };

  // --- Restored Audio Functions ---
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
        headers: { "Authorization": `Bearer ${session?.access_token}` },
        body: formData,
      });
      const data = await res.json();
      if (data.text) {
        setUserResponse(data.text);
        setStatus("Audio transcribed! You can edit the text or submit it.");
      }
    } catch (error) {
      setStatus("Error transcribing audio.");
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Submits the text response to generate the activity plan.
   */
  const submitAnswer = async () => {
    if (!userResponse) return alert("Please provide an answer first.");
    setIsLoading(true);
    setStatus("Analyzing your response...");
    
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/analyze`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${session?.access_token}`
        },
        body: JSON.stringify({ language, question, user_response: userResponse }),
      });
      const data = await res.json();
      
      setActivityPlan(data.activity_plan);
      setHasCheckedInToday(true);
      setStatus("Done for today!");
      
      speakText("I have created a personalized activity plan for you. Check the screen for details.", language);
    } catch (error) {
      setStatus("Error analyzing response.");
    } finally {
      setIsLoading(false);
    }
  };

  // ==========================================
  // UI RENDERING LOGIC
  // ==========================================

  if (isCheckingStatus) {
    return <div className="p-6 text-center text-slate-400">Loading your daily dashboard...</div>;
  }

  // 1. Persistent Daily Itinerary View (Using the transparent colorful UI you liked)
  if (hasCheckedInToday && activityPlan) {
    let parsedPlan = activityPlan;
    if (typeof activityPlan === 'string') {
      try { parsedPlan = JSON.parse(activityPlan); } catch (e) { }
    }

    const isObject = typeof parsedPlan === 'object' && parsedPlan !== null;
    const textToRead = isObject 
      ? `Here is your plan for today. Morning: ${parsedPlan.morning_activity || 'Rest.'} Afternoon: ${parsedPlan.afternoon_activity || 'Rest.'} Evening: ${parsedPlan.evening_activity || 'Rest.'}`
      : String(parsedPlan);

    return (
      <div className="p-6 max-w-2xl mx-auto space-y-6 animate-fade-in">
        <div className="text-center space-y-2 mb-8">
          <h2 className="text-4xl font-extrabold text-green-500">Great job today! 🎉</h2>
          <p className="text-slate-400 text-xl">Here is your personalized plan.</p>
        </div>

        <div className="shadow-lg rounded-2xl p-6 border border-slate-700/50 bg-slate-800/20 backdrop-blur-sm space-y-6 text-left">
          {isObject ? (
            <>
              {parsedPlan.morning_activity && (
                <div className="bg-orange-500/10 border-l-4 border-orange-500 p-5 rounded-r-xl">
                  <h4 className="font-bold text-orange-500 flex items-center gap-3 text-2xl mb-2"><span className="text-3xl">🌅</span> Morning</h4>
                  <p className="text-slate-200 text-xl leading-relaxed">{parsedPlan.morning_activity}</p>
                </div>
              )}
              {parsedPlan.afternoon_activity && (
                <div className="bg-blue-500/10 border-l-4 border-blue-500 p-5 rounded-r-xl">
                  <h4 className="font-bold text-blue-500 flex items-center gap-3 text-2xl mb-2"><span className="text-3xl">☀️</span> Afternoon</h4>
                  <p className="text-slate-200 text-xl leading-relaxed">{parsedPlan.afternoon_activity}</p>
                </div>
              )}
              {parsedPlan.evening_activity && (
                <div className="bg-indigo-500/10 border-l-4 border-indigo-500 p-5 rounded-r-xl">
                  <h4 className="font-bold text-indigo-500 flex items-center gap-3 text-2xl mb-2"><span className="text-3xl">🌙</span> Evening</h4>
                  <p className="text-slate-200 text-xl leading-relaxed">{parsedPlan.evening_activity}</p>
                </div>
              )}
              {parsedPlan.caregiver_rationale && (
                <div className="mt-8 pt-6 border-t border-slate-700/50">
                  <h4 className="font-semibold text-slate-400 flex items-center gap-2 text-lg mb-2">💡 Note for Family/Caregiver</h4>
                  <p className="text-slate-400 italic text-base">{parsedPlan.caregiver_rationale}</p>
                </div>
              )}
            </>
          ) : (
            <p className="text-slate-200 text-xl leading-relaxed whitespace-pre-wrap bg-slate-500/10 p-5 rounded-xl border-l-4 border-slate-500">
              {String(parsedPlan)}
            </p>
          )}
        </div>

        <button 
          onClick={() => speakText(textToRead, language)}
          className="w-full mt-6 py-5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold text-2xl shadow-sm transition-all flex items-center justify-center gap-3"
        >
          🔊 Read My Plan Out Loud
        </button>
      </div>
    );
  }

  // 2. Default Question View (Restored exactly to your original Slate design)
  return (
    <div className="space-y-6 max-w-2xl mx-auto p-4 animate-fade-in">
      <p className="text-slate-400 italic text-center">{status}</p>

      {/* Question Header (Button or Text) */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 text-center shadow-lg">
        {question ? (
          <h2 className="text-2xl font-semibold leading-relaxed text-white">{question}</h2>
        ) : (
          <button 
            onClick={fetchQuestion}
            disabled={isLoading}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-4 rounded-lg font-medium transition-colors break-words min-h-[64px]"
          >
            {t?.generateBtn || "Generate Today's Question"}
          </button>
        )}
      </div>

      {/* Input Section (Textarea -> Flex Buttons) */}
      {question && (
        <div className="space-y-4">
          <textarea 
            className="w-full bg-slate-900 border border-slate-700 rounded-xl p-4 text-white min-h-[120px] focus:ring-2 focus:ring-blue-500 outline-none placeholder-slate-500"
            placeholder="Type your response here or use the microphone..."
            value={userResponse}
            onChange={(e) => setUserResponse(e.target.value)}
          />
          
          <div className="flex flex-col sm:flex-row space-y-4 sm:space-y-0 sm:space-x-4">
            <button 
              onClick={isRecording ? stopRecording : startRecording}
              className={`flex-1 ${isRecording ? 'bg-red-600 hover:bg-red-700' : 'bg-slate-800 hover:bg-slate-700 border border-slate-600'} text-white px-6 py-4 rounded-xl font-bold text-lg transition-colors flex items-center justify-center break-words min-h-[64px] leading-tight`}
            >
              {isRecording ? (t?.stopBtn || "Stop Recording") : (t?.speakBtn || "Use Microphone")}
            </button>

            <button 
              onClick={submitAnswer}
              disabled={isLoading || isRecording}
              className="flex-1 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white px-6 py-4 rounded-xl font-bold text-lg transition-colors break-words min-h-[64px] leading-tight flex items-center justify-center"
            >
              {isLoading && !isRecording ? (t?.loading || "Processing...") : (t?.submitBtn || "Submit Answer")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}