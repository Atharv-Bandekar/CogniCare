// frontend/src/components/DashboardTab.tsx
import { useState, useEffect } from "react";

/**
 * DashboardTab Component
 * * Serves as the primary view for caregivers. It automatically fetches
 * the historical interaction data from the backend/Supabase database 
 * and renders it as a chronological feed of insights.
 */

interface DashboardTabProps {
  session: any;
}


export default function DashboardTab({ session }: DashboardTabProps) {
  const [history, setHistory] = useState<any[]>([]);
  const [isFetchingHistory, setIsFetchingHistory] = useState(false);
  /**
   * Fetches the user's historical check-in data from the FastAPI backend.
   * Runs automatically when the component mounts.
   */
  const loadHistory = async () => {
    setIsFetchingHistory(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/history`, {
        // Attach the user's secure token to the request
        headers: {
          "Authorization": `Bearer ${session?.access_token}`
        }
      });
      const data = await res.json();
      setHistory(data.history || []);
    } catch (error) {
      console.error("Failed to load history", error);
    } finally {
      setIsFetchingHistory(false);
    }
  };
  

  // Lifecycle Hook: Load history immediately when this tab is opened
  useEffect(() => {
    loadHistory();
  }, []);

  return (
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
              
              {/* Header: Timestamp & Badges */}
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

              {/* Body: Q & A Transcripts */}
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
  );
}