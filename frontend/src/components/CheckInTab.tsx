import { useState, useEffect, useRef } from "react";

/**
 * Interface defining the properties passed to the CheckInTab component.
 * @property {string} language - The user's currently selected UI language.
 * @property {Record<string, string>} t - Dictionary containing localized text strings.
 * @property {any} session - The active Supabase authentication session object containing the JWT.
 */
interface CheckInTabProps {
  language: string;
  t: Record<string, string>;
  session: any;
}

/**
 * CheckInTab Component
 * * Handles the daily cognitive assessment workflow for the user.
 * Includes logic to ensure the user is only asked one question per day,
 * transitioning to a persistent daily itinerary view upon completion.
 */
export default function CheckInTab({ language, t, session }: CheckInTabProps) {
  // --- UI State Management ---
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [status, setStatus] = useState<string>("");
  
  // --- Assessment State ---
  const [question, setQuestion] = useState<string>("");
  const [userResponse, setUserResponse] = useState<string>("");
  const [activityPlan, setActivityPlan] = useState<any>(null);
  
  // --- Workflow Control State ---
  // Determines if the user has already completed their assessment for the current calendar day
  const [hasCheckedInToday, setHasCheckedInToday] = useState<boolean>(false);
  // Prevents UI flashing by showing a loading state while querying the database on mount
  const [isCheckingStatus, setIsCheckingStatus] = useState<boolean>(true);

  /**
   * Synthesizes and plays text-to-speech audio for the provided string.
   * Includes voice matching for regional languages with a safe fallback.
   * @param {string} text - The content to be read aloud.
   * @param {string} lang - The selected language (English, Hindi, Marathi, Tamil).
   */
  const speakText = (text: string, lang: string) => {
    if (!window.speechSynthesis) {
      console.warn("Speech synthesis not supported in this browser.");
      return;
    }

    // Cancel any ongoing speech utterances
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    
    // Map application languages to BCP 47 tags
    const langMap: Record<string, string> = {
      "Hindi": "hi-IN",
      "Marathi": "mr-IN",
      "Tamil": "ta-IN",
      "English": "en-US"
    };
    
    const targetLangCode = langMap[lang] || "en-US";
    utterance.lang = targetLangCode;

    // Attempt to find a matching voice installed on the user's system
    const voices = window.speechSynthesis.getVoices();
    const matchingVoice = voices.find(voice => voice.lang === targetLangCode || voice.lang.startsWith(targetLangCode.split('-')[0]));
    
    if (matchingVoice) {
      utterance.voice = matchingVoice;
    } else {
      console.warn(`No native voice found for ${targetLangCode}. Using default system voice.`);
    }

    window.speechSynthesis.speak(utterance);
  };

  /**
   * Initialization Hook: Validates the user's daily check-in status.
   * Queries the backend for the most recent conversation history. 
   * If the latest entry matches today's date, it bypasses the question flow
   * and directly renders the user's activity plan.
   */
  useEffect(() => {
    const checkTodayStatus = async () => {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/history`, {
          headers: {
            "Authorization": `Bearer ${session?.access_token}`
          }
        });
        const data = await res.json();
        
        if (data.history && data.history.length > 0) {
          const latestEntry = data.history[0];
          
          // Normalize dates to localized strings for accurate daily comparison
          const latestDate = new Date(latestEntry.timestamp).toDateString();
          const todayDate = new Date().toDateString();

          if (latestDate === todayDate && latestEntry.activity_plan) {
            setHasCheckedInToday(true);
            setActivityPlan(latestEntry.activity_plan);
          }
        }
      } catch (error) {
        console.error("Failed to verify today's check-in status:", error);
      } finally {
        setIsCheckingStatus(false);
      }
    };

    // Only attempt to fetch history if a valid auth token is present
    if (session?.access_token) {
      checkTodayStatus();
    }
  }, [session]);


  /**
   * Triggers the backend AI Interviewer Agent to generate a localized question.
   * Updates UI state and initiates TTS playback upon success.
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
      console.error("Question Generation Error:", error);
      setStatus("Error connecting to backend.");
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Submits the user's response to the backend Evaluator and Coordinator agents.
   * Upon successful evaluation, locks the UI into the Persistent Itinerary view.
   */
  const submitAnswer = async () => {
    if (!userResponse) {
      return alert("Please provide an answer first.");
    }

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
      
      // Update state to lock the daily workflow and display the plan
      setActivityPlan(data.activity_plan);
      setHasCheckedInToday(true); 
      setStatus("Done for today!");
      
      speakText("I have created a personalized activity plan for you. Check the screen for details.", language);
    } catch (error) {
      console.error("Response Analysis Error:", error);
      setStatus("Error analyzing response.");
    } finally {
      setIsLoading(false);
    }
  };


  // ==========================================
  // UI RENDERING LOGIC
  // ==========================================

  // 1. Loading State while querying Supabase for today's status
  if (isCheckingStatus) {
    return <div className="p-6 text-center text-gray-500">Loading your daily dashboard...</div>;
  }

  // 2. Persistent Daily Itinerary View (Triggered if already checked in today)
  if (hasCheckedInToday && activityPlan) {
    let parsedPlan = activityPlan;
    if (typeof activityPlan === 'string') {
      try { parsedPlan = JSON.parse(activityPlan); } 
      catch (e) { /* Fallback */ }
    }

    const isObject = typeof parsedPlan === 'object' && parsedPlan !== null;

    const textToRead = isObject 
      ? `Here is your plan for today. 
         Morning: ${parsedPlan.morning_activity || 'Rest and relax.'} 
         Afternoon: ${parsedPlan.afternoon_activity || 'Rest and relax.'} 
         Evening: ${parsedPlan.evening_activity || 'Rest and relax.'}`
      : String(parsedPlan);

    return (
      <div className="p-6 max-w-2xl mx-auto space-y-6 animate-fade-in">
        <div className="text-center space-y-2 mb-8">
          <h2 className="text-4xl font-extrabold text-green-500">Great job today! 🎉</h2>
          <p className="text-gray-500 text-xl">Here is your personalized plan.</p>
        </div>

        {/* Outer Wrapper: Removed bg-white! Added a subtle glass/transparent effect so your app's background shows through */}
        <div className="shadow-lg rounded-2xl p-6 border border-gray-200/50 dark:border-gray-700/50 bg-gray-50/10 dark:bg-gray-800/20 backdrop-blur-sm space-y-6 text-left">
          
          {isObject ? (
            <>
              {/* Morning: Colorful border with a 10% transparent tint instead of solid white */}
              {parsedPlan.morning_activity && (
                <div className="bg-orange-500/10 border-l-4 border-orange-500 p-5 rounded-r-xl">
                  <h4 className="font-bold text-orange-500 flex items-center gap-3 text-2xl mb-2">
                    <span className="text-3xl">🌅</span> Morning
                  </h4>
                  {/* Added dark:text-gray-300 so it looks great if your app is in dark mode */}
                  <p className="text-gray-800 dark:text-gray-200 text-xl leading-relaxed">{parsedPlan.morning_activity}</p>
                </div>
              )}
              
              {/* Afternoon: Blue border with 10% transparent blue tint */}
              {parsedPlan.afternoon_activity && (
                <div className="bg-blue-500/10 border-l-4 border-blue-500 p-5 rounded-r-xl">
                  <h4 className="font-bold text-blue-500 flex items-center gap-3 text-2xl mb-2">
                    <span className="text-3xl">☀️</span> Afternoon
                  </h4>
                  <p className="text-gray-800 dark:text-gray-200 text-xl leading-relaxed">{parsedPlan.afternoon_activity}</p>
                </div>
              )}

              {/* Evening: Indigo border with 10% transparent indigo tint */}
              {parsedPlan.evening_activity && (
                <div className="bg-indigo-500/10 border-l-4 border-indigo-500 p-5 rounded-r-xl">
                  <h4 className="font-bold text-indigo-500 flex items-center gap-3 text-2xl mb-2">
                    <span className="text-3xl">🌙</span> Evening
                  </h4>
                  <p className="text-gray-800 dark:text-gray-200 text-xl leading-relaxed">{parsedPlan.evening_activity}</p>
                </div>
              )}

              {/* Caregiver Note */}
              {parsedPlan.caregiver_rationale && (
                <div className="mt-8 pt-6 border-t border-gray-200/50 dark:border-gray-700/50">
                  <h4 className="font-semibold text-gray-500 dark:text-gray-400 flex items-center gap-2 text-lg mb-2">
                    💡 Note for Family/Caregiver
                  </h4>
                  <p className="text-gray-500 dark:text-gray-400 italic text-base">{parsedPlan.caregiver_rationale}</p>
                </div>
              )}
            </>
          ) : (
            <p className="text-gray-800 dark:text-gray-200 text-xl leading-relaxed whitespace-pre-wrap bg-gray-500/10 p-5 rounded-xl border-l-4 border-gray-500">
              {String(parsedPlan)}
            </p>
          )}
        </div>

        <button 
          onClick={() => speakText(textToRead, language)}
          className="w-full mt-6 py-5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl font-bold text-2xl shadow-sm transition-all flex items-center justify-center gap-3"
        >
          🔊 Read My Plan Out Loud
        </button>
      </div>
    );
  }

  // 3. Default Question View (Triggered if no check-in exists for today)
  return (
    <div className="p-4 space-y-6 max-w-2xl mx-auto">
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-2">Daily Check-In</h2>
        <button 
          onClick={fetchQuestion} 
          disabled={isLoading}
          className="bg-indigo-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-indigo-700 disabled:opacity-50 w-full md:w-auto transition-all"
        >
          Generate Today's Question
        </button>
      </div>

      {question && (
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 space-y-4">
          <h3 className="text-xl font-medium text-gray-800">{question}</h3>
          
          {/* TODO: Integrate Groq Whisper Audio Upload Component Here */}
              
          <textarea
            className="w-full p-4 border rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 min-h-[120px]"
            placeholder="Type your answer here, or use the microphone..."
            value={userResponse}
            onChange={(e) => setUserResponse(e.target.value)}
          />

          <button 
            onClick={submitAnswer} 
            disabled={isLoading}
            className="w-full bg-green-600 text-white py-4 rounded-lg font-bold text-lg hover:bg-green-700 disabled:opacity-50 transition-all"
          >
            {isLoading ? "Processing..." : "Submit Answer"}
          </button>
          
          {status && <p className="text-sm text-center text-gray-500 mt-2">{status}</p>}
        </div>
      )}
    </div>
  );
}