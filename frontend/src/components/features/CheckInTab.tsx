// frontend/src/components/features/CheckInTab.tsx
import { useState, useEffect } from "react";
import { CheckInTabProps } from "../../types";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";
import { useSpeech } from "../../hooks/useSpeech";
import { useAudioRecorder } from "../../hooks/useAudioRecorder";

export default function CheckInTab({ language, t, session }: CheckInTabProps) {
  // --- UI & Assessment State ---
  // --- UI & Assessment State ---
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [status, setStatus] = useState<string>(""); // Keep this blank initially
  const [question, setQuestion] = useState<string>("");
  const [userResponse, setUserResponse] = useState<string>("");
  const [activityPlan, setActivityPlan] = useState<any>(null);
  const [hasCheckedInToday, setHasCheckedInToday] = useState<boolean>(false);
  const [isCheckingStatus, setIsCheckingStatus] = useState<boolean>(true);

  // --- Hardware Hooks ---
  const { speakText } = useSpeech(language);
  const { isRecording, startRecording, stopRecording } = useAudioRecorder(async (audioBlob) => {
    await uploadAudioForTranscription(audioBlob);
  });

  // --- Core Functions ---
  useEffect(() => {
    const checkTodayStatus = async () => {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/history`, {
          headers: { "Authorization": `Bearer ${session?.access_token}` }
        });
        const data = await res.json();
        
        if (data.history && data.history.length > 0) {
          // Temporarily disabled date lock for testing
          if(false){
            setHasCheckedInToday(true);
            setActivityPlan(data.history[0].activity_plan);
          }
        }
      } catch (error) {
        console.error("Failed to verify status:", error);
      } finally {
        setIsCheckingStatus(false);
      }
    };
    if (session?.access_token) checkTodayStatus();
  }, [session]);

  const fetchQuestion = async () => {
    setIsLoading(true);
    setStatus(t?.statusThinking);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/question`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${session?.access_token}` },
        body: JSON.stringify({ language }),
      });
      const data = await res.json();
      setQuestion(data.question);
      setStatus(t?.statusAnswer);
      speakText(data.question);
    } catch (error) {
      setStatus("Error connecting to backend.");
    } finally {
      setIsLoading(false);
    }
  };

  const uploadAudioForTranscription = async (blob: Blob) => {
    setIsLoading(true);
    setStatus("Transcribing audio...");
    const formData = new FormData();
    formData.append("audio", blob, "recording.webm");
    formData.append("language", language);

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

  const submitAnswer = async () => {
    if (!userResponse) return alert("Please provide an answer first.");
    setIsLoading(true);
    setStatus(t?.loading);
    
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${session?.access_token}` },
        body: JSON.stringify({ language, question, user_response: userResponse }),
      });
      const data = await res.json();
      
      setActivityPlan(data.activity_plan);
      setHasCheckedInToday(true);
      setStatus("Done for today!");
      speakText("I have created a personalized activity plan for you. Check the screen for details.");
    } catch (error) {
      setStatus("Error analyzing response.");
    } finally {
      setIsLoading(false);
    }
  };



  const refreshQuestion = async () => {
    setIsLoading(true);
    setStatus(t?.statusRefresh);
    
    // We don't clear setUserResponse("") yet, just in case the request fails
    
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/refresh-question`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${session?.access_token}` 
        },
        // 🚨 SEND THE CURRENT QUESTION TO BE BLACKLISTED
        body: JSON.stringify({ language, current_question: question }), 
      });
      
      const data = await res.json();
      setQuestion(data.question);
      setUserResponse(""); // Clear the text input only after we successfully get a new question
      setStatus(t?.statusAnswer);
      speakText(data.question);
    } catch (error) {
      setStatus("Error connecting to backend.");
    } finally {
      setIsLoading(false);
    }
  };

  // ==========================================
  // UI RENDERING
  // ==========================================

  if (isCheckingStatus) {
    return <div className="p-6 text-center text-slate-400">Loading your daily dashboard...</div>;
  }

  // View 1: Daily Itinerary
  if (hasCheckedInToday && activityPlan) {
    
    // --- BULLETPROOF PARSING LOGIC (WITH TYPESCRIPT FIX) ---
    // Added Record<string, any> so TypeScript knows this object is safe to read
    let parsedPlan: Record<string, any> = {};
    
    if (typeof activityPlan === 'object' && activityPlan !== null) {
      parsedPlan = activityPlan;
    } else if (typeof activityPlan === 'string') {
      try {
        const jsonMatch = activityPlan.match(/\{[\s\S]*\}/);
        parsedPlan = jsonMatch ? JSON.parse(jsonMatch[0]) : JSON.parse(activityPlan);
      } catch (e) {
        console.warn("AI returned plain text instead of JSON. Falling back gracefully.");
        parsedPlan = { morning_activity: activityPlan };
      }
    }

    // Safety fallback
    if (!parsedPlan.morning_activity && !parsedPlan.afternoon_activity && !parsedPlan.evening_activity) {
        const fallbackText = parsedPlan.recommended_activity || parsedPlan.activity || parsedPlan.plan || parsedPlan.activity_plan;
        if (fallbackText && typeof fallbackText === 'string') {
            parsedPlan.morning_activity = fallbackText;
        } else if (Object.keys(parsedPlan).length > 0) {
            parsedPlan.morning_activity = "Activity generated: Please check your dashboard history for details.";
        }
    }

    const textToRead = `Here is your plan. Morning: ${parsedPlan?.morning_activity || 'Rest.'} Afternoon: ${parsedPlan?.afternoon_activity || 'Rest.'} Evening: ${parsedPlan?.evening_activity || 'Rest.'}`;

    return (
      <div className="p-6 max-w-2xl mx-auto space-y-6 animate-fade-in">
        <div className="text-center space-y-2 mb-8">
          <h2 className="text-4xl font-extrabold text-green-500">{t?.greatJob}</h2>
          <p className="text-slate-400 text-xl">{t?.planSubtitle}</p>
        </div>

        <div className="shadow-lg rounded-2xl p-6 bg-slate-900/40 border border-slate-800/80 space-y-6 text-left relative overflow-hidden">
          {/* Notice the added '?.' which makes TypeScript happy! */}
          {parsedPlan?.morning_activity && (
            <div className="bg-orange-500/10 border-l-4 border-orange-500 p-5 rounded-r-xl">
              <h4 className="font-bold text-orange-500 flex items-center gap-3 text-2xl mb-2">🌅 {t?.morning}</h4>
              <p className="text-slate-200 text-xl leading-relaxed">{parsedPlan.morning_activity}</p>
            </div>
          )}
          {parsedPlan?.afternoon_activity && (
            <div className="bg-blue-500/10 border-l-4 border-blue-500 p-5 rounded-r-xl">
              <h4 className="font-bold text-blue-500 flex items-center gap-3 text-2xl mb-2">☀️ {t?.afternoon}</h4>
              <p className="text-slate-200 text-xl leading-relaxed">{parsedPlan.afternoon_activity}</p>
            </div>
          )}
          {parsedPlan?.evening_activity && (
            <div className="bg-indigo-500/10 border-l-4 border-indigo-500 p-5 rounded-r-xl">
              <h4 className="font-bold text-indigo-500 flex items-center gap-3 text-2xl mb-2">🌙 {t?.evening}</h4>
              <p className="text-slate-200 text-xl leading-relaxed">{parsedPlan.evening_activity}</p>
            </div>
          )}
        </div>

        <Button variant="primary" className="w-full mt-6 py-5 text-2xl" onClick={() => speakText(textToRead)}>
          {t?.readPlanBtn}
        </Button>
      </div>
    );
  }

  // View 2: Default Question View
  return (
    <div className="space-y-6 max-w-2xl mx-auto p-4 animate-fade-in">
      <p className="text-slate-400 italic text-center">{status || t?.statusStart}</p>

      {/* Clean card container without a heavy border or background distractions */}
      <Card className="text-center p-8 space-y-4 relative bg-slate-900/40 border-slate-800/80">
        {/* Minimalist Borderless Refresh Button */}
        {question && (
          <button 
            onClick={refreshQuestion}
            disabled={isLoading || isRecording}
            title="Get a different question"
            className="absolute top-4 right-4 group p-2 text-slate-400 hover:text-blue-400 transition-colors disabled:opacity-50"
          >
            <svg 
              className="w-5 h-5 group-hover:-rotate-180 transition-transform duration-500 ease-in-out" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24" 
              xmlns="http://www.w3.org/2000/svg"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        )}

        {question ? (
          <div className="flex flex-col items-center gap-5 my-2">
            <h2 className="text-2xl font-semibold leading-relaxed text-white text-left sm:text-center">
              {question}
            </h2>
            
            {/* Replay Audio Button */}
            <button
              onClick={() => speakText(question)}
              title="Hear Question Again"
              className="flex items-center gap-2 bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/30 hover:border-blue-500/60 px-5 py-2.5 rounded-full transition-all duration-300 font-medium shadow-sm"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path d="M13.5 4.06c0-1.336-1.616-2.005-2.56-1.06l-4.5 4.5H4.508c-1.141 0-2.318.664-2.66 1.905A9.76 9.76 0 001.5 12c0 .898.121 1.768.35 2.595.341 1.24 1.518 1.905 2.659 1.905h1.93l4.5 4.5c.945.945 2.56.276 2.56-1.06V4.06zM18.584 5.106a.75.75 0 011.06 0c3.808 3.807 3.808 9.98 0 13.788a.75.75 0 11-1.06-1.06 8.25 8.25 0 000-11.668.75.75 0 010-1.06z" />
                <path d="M15.932 7.757a.75.75 0 011.061 0 6 6 0 010 8.486.75.75 0 01-1.06-1.061 4.5 4.5 0 000-6.364.75.75 0 010-1.06z" />
              </svg>
              {t?.replayAudioBtn || "Hear Question Again"}
            </button>
          </div>
        ) : (
          <Button variant="primary" onClick={fetchQuestion} disabled={isLoading} className="w-auto mx-auto min-h-[64px]">
            {t?.generateBtn || "Generate Today's Question"}
          </Button>
        )}
      </Card>

      {question && (
        <div className="space-y-4">
          <textarea 
            className="w-full bg-slate-900 border border-slate-700 rounded-xl p-4 text-white min-h-[120px] focus:ring-2 focus:ring-blue-500 focus:bg-slate-900 outline-none transition-all"
            placeholder={t?.placeholderTxt}
            value={userResponse}
            onChange={(e) => setUserResponse(e.target.value)}
          />
          
          <div className="flex flex-col sm:flex-row space-y-4 sm:space-y-0 sm:space-x-4">
            <Button variant={isRecording ? "danger" : "secondary"} onClick={isRecording ? stopRecording : startRecording} className="flex-1 min-h-[64px] text-lg">
              {isRecording ? (t?.stopBtn || "Stop Recording") : (t?.speakBtn || "Use Microphone")}
            </Button>

            <Button variant="success" onClick={submitAnswer} disabled={isLoading || isRecording} className="flex-1 min-h-[64px] text-lg">
              {isLoading && !isRecording ? (t?.loading || "Processing...") : (t?.submitBtn || "Submit Answer")}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}