// frontend/src/components/features/CheckInTab.tsx
import { useState, useEffect } from "react";
import { CheckInTabProps } from "../../types";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";
import { useSpeech } from "../../hooks/useSpeech";
import { useAudioRecorder } from "../../hooks/useAudioRecorder";

export default function CheckInTab({ language, t, session }: CheckInTabProps) {
  // --- UI & Assessment State ---
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [status, setStatus] = useState<string>("Click 'Generate' to start.");
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
    setStatus("Thinking of a question for you...");
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/question`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Authorization": `Bearer ${session?.access_token}` },
        body: JSON.stringify({ language }),
      });
      const data = await res.json();
      setQuestion(data.question);
      setStatus("Please answer below:");
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
    setStatus("Analyzing your response...");
    
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

  // ==========================================
  // UI RENDERING
  // ==========================================

  if (isCheckingStatus) {
    return <div className="p-6 text-center text-slate-400">Loading your daily dashboard...</div>;
  }

  // View 1: Daily Itinerary
  if (hasCheckedInToday && activityPlan) {
    let parsedPlan = typeof activityPlan === 'string' ? JSON.parse(activityPlan || "{}") : activityPlan;
    const textToRead = `Here is your plan. Morning: ${parsedPlan.morning_activity || 'Rest.'} Afternoon: ${parsedPlan.afternoon_activity || 'Rest.'} Evening: ${parsedPlan.evening_activity || 'Rest.'}`;

    return (
      <div className="p-6 max-w-2xl mx-auto space-y-6 animate-fade-in">
        <div className="text-center space-y-2 mb-8">
          <h2 className="text-4xl font-extrabold text-green-500">Great job today! 🎉</h2>
          <p className="text-slate-400 text-xl">Here is your personalized plan.</p>
        </div>

        <div className="shadow-lg rounded-2xl p-6 border border-slate-700/50 bg-slate-800/20 backdrop-blur-sm space-y-6 text-left">
          {parsedPlan.morning_activity && (
            <div className="bg-orange-500/10 border-l-4 border-orange-500 p-5 rounded-r-xl">
              <h4 className="font-bold text-orange-500 flex items-center gap-3 text-2xl mb-2">🌅 Morning</h4>
              <p className="text-slate-200 text-xl leading-relaxed">{parsedPlan.morning_activity}</p>
            </div>
          )}
          {parsedPlan.afternoon_activity && (
            <div className="bg-blue-500/10 border-l-4 border-blue-500 p-5 rounded-r-xl">
              <h4 className="font-bold text-blue-500 flex items-center gap-3 text-2xl mb-2">☀️ Afternoon</h4>
              <p className="text-slate-200 text-xl leading-relaxed">{parsedPlan.afternoon_activity}</p>
            </div>
          )}
          {parsedPlan.evening_activity && (
            <div className="bg-indigo-500/10 border-l-4 border-indigo-500 p-5 rounded-r-xl">
              <h4 className="font-bold text-indigo-500 flex items-center gap-3 text-2xl mb-2">🌙 Evening</h4>
              <p className="text-slate-200 text-xl leading-relaxed">{parsedPlan.evening_activity}</p>
            </div>
          )}
        </div>

        <Button variant="primary" className="w-full mt-6 py-5 text-2xl" onClick={() => speakText(textToRead)}>
          🔊 Read My Plan Out Loud
        </Button>
      </div>
    );
  }

  // View 2: Default Question View
  return (
    <div className="space-y-6 max-w-2xl mx-auto p-4 animate-fade-in">
      <p className="text-slate-400 italic text-center">{status}</p>

      <Card className="text-center p-8">
        {question ? (
          <h2 className="text-2xl font-semibold leading-relaxed text-white">{question}</h2>
        ) : (
          <Button variant="primary" onClick={fetchQuestion} disabled={isLoading} className="w-auto mx-auto min-h-[64px]">
            {t?.generateBtn || "Generate Today's Question"}
          </Button>
        )}
      </Card>

      {question && (
        <div className="space-y-4">
          <textarea 
            className="w-full bg-slate-900 border border-slate-700 rounded-xl p-4 text-white min-h-[120px] focus:ring-2 focus:ring-blue-500 outline-none"
            placeholder="Type your response here or use the microphone..."
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