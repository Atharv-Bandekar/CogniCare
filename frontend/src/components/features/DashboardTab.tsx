// frontend/src/components/features/DashboardTab.tsx
import { useState, useEffect } from "react";
import { DashboardTabProps } from "../../types"; // Importing from central types!
import { Card } from "../ui/Card";               // Importing our clean UI component!

export default function DashboardTab({ session }: DashboardTabProps) {
  const [history, setHistory] = useState<any[]>([]);
  const [isFetchingHistory, setIsFetchingHistory] = useState(false);

  const loadHistory = async () => {
    setIsFetchingHistory(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/history`, {
        headers: { "Authorization": `Bearer ${session?.access_token}` }
      });
      const data = await res.json();
      setHistory(data.history || []);
    } catch (error) {
      console.error("Failed to load history", error);
    } finally {
      setIsFetchingHistory(false);
    }
  };

  useEffect(() => {
    if (session?.access_token) loadHistory();
  }, [session]);

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-blue-300 mb-4">Patient History & Trends</h2>
      
      {isFetchingHistory ? (
        <p className="text-slate-400">Loading history from database...</p>
      ) : history.length === 0 ? (
        <Card className="text-center p-8">
          <p className="text-slate-500">No interaction history found yet.</p>
        </Card>
      ) : (
        <div className="space-y-4">
          {history.map((entry, index) => (
            <Card key={index} className="hover:border-slate-700 transition-colors shadow-sm">
              
              {/* Date Header */}
              <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-4">
                <h3 className="text-sm font-semibold text-blue-400 uppercase tracking-wider">
                  {new Date(entry.timestamp || entry.created_at).toLocaleDateString(undefined, { 
                    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' 
                  })}
                </h3>
              </div>

              {/* Question & Answer */}
              <div className="space-y-3 mb-6">
                <div>
                  <strong className="text-blue-400 block text-sm mb-1 uppercase">AI Question:</strong>
                  <p className="text-slate-200 leading-relaxed">{entry.question}</p>
                </div>
                <div>
                  <strong className="text-green-400 block text-sm mb-1 uppercase">User Answer:</strong>
                  <p className="text-slate-300 italic leading-relaxed">"{entry.response}"</p>
                </div>
              </div>

              {/* RESTORED: AI Metrics Footer */}
              <div className="flex flex-wrap items-center gap-3 pt-4 border-t border-slate-800/50">
                
                {/* Mood Badge */}
                {entry.sentiment_label && (
                  <div className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded-full text-sm font-medium">
                    <span>🎭</span> 
                    <span>Mood: {entry.sentiment_label}</span>
                  </div>
                )}

                {/* Engagement Badge */}
                {entry.engagement_level && (
                  <div className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-full text-sm font-medium">
                    <span>⚡</span> 
                    <span>Engagement: {entry.engagement_level}</span>
                  </div>
                )}

                {/* Activity Insight Badge */}
                {entry.recommended_activity && (
                  <div className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-full text-sm font-medium">
                    <span>💡</span> 
                    {/* Truncated in case the AI generated a long activity string */}
                    <span className="truncate max-w-[200px] sm:max-w-md">
                      Activity: {entry.recommended_activity}
                    </span>
                  </div>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}