// frontend/src/components/CheckInTab.tsx
import { useState, useRef } from "react";

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

/**
 * CheckInTab Component
 * * Manages the interactive daily assessment. Handles AI question generation,
 * microphone recording, audio transcription via Whisper, and displays the 
 * final personalized daily plan.
 */
export default function CheckInTab({ language, t, session }: CheckInTabProps) {
  // --- State Management ---
  const [question, setQuestion] = useState("");
  const [userResponse, setUserResponse] = useState("");
  const [status, setStatus] = useState("Click 'Get Question' to start.");
  const [isLoading, setIsLoading] = useState(false);
  const [activityPlan, setActivityPlan] = useState<any>(null);
  const [isRecording, setIsRecording] = useState(false);

  // --- Refs for Audio Recording ---
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<BlobPart[]>([]);

  /**
   * Helper: Parses the AI's JSON output for the activity plan into readable text.
   */
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

  /**
   * Helper: Triggers browser Text-to-Speech using the selected regional dialect.
   */
  const speakText = (text: string, lang: string) => {
    if (!("speechSynthesis" in window)) return;
    const locales: Record<string, string> = { English: "en-US", Hindi: "hi-IN", Marathi: "mr-IN", Tamil: "ta-IN" };
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = locales[lang] || "en-US";
    window.speechSynthesis.speak(utterance);
  };

  /**
   * API Call: Asks the backend to generate a culturally relevant question.
   */
  const fetchQuestion = async () => {
    setIsLoading(true);
    setStatus("Thinking of a question for you...");
    setActivityPlan(null);
    setUserResponse("");
    
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

  /**
   * Hardware: Requests microphone access and begins recording audio chunks.
   */
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

  /**
   * Hardware: Halts the recording stream, triggering the `onstop` event to upload.
   */
  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  /**
   * API Call: Sends the raw WebM blob to the backend for Groq Whisper transcription.
   */
  const uploadAudioForTranscription = async (blob: Blob) => {
    setIsLoading(true);
    setStatus("Transcribing audio via Groq Whisper...");
    const formData = new FormData();
    formData.append("audio", blob, "recording.webm");

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/transcribe`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${session?.access_token}`
        },
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
   * API Call: Submits the final text to the backend to generate the daily plan.
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
      setStatus(`Detected mood: ${data.evaluation.sentiment_label} | Engagement: ${data.evaluation.engagement_level}`);
      speakText("I have created a personalized activity plan for you. Check the screen for details.", language);
    } catch (error) {
      setStatus("Error analyzing response.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <p className="text-slate-400 italic">{status}</p>

      {/* Question Header */}
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

      {/* Input Section (Text or Voice) */}
      {question && !activityPlan && (
        <div className="space-y-4">
          <textarea 
            className="w-full bg-slate-900 border border-slate-700 rounded-xl p-4 text-white min-h-[120px] focus:ring-2 focus:ring-blue-500 outline-none"
            placeholder="Type your response here or use the microphone..."
            value={userResponse}
            onChange={(e) => setUserResponse(e.target.value)}
          />
          
          {/* Action Buttons with Tailwind Armor */}
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

      {/* Output Section (Activity Plan) */}
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
  );
}