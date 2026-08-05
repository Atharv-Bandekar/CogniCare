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
            /* Look how clean this is now using <Card>! */
            <Card key={index}>
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 mb-4 border-b border-slate-800 pb-4">
                <span className="text-slate-400 text-sm font-medium">
                  {new Date(entry.timestamp).toLocaleString()}
                </span>
                <div className="flex flex-wrap gap-2">
                  <span className="bg-slate-800 text-slate-300 px-3 py-1 rounded-full text-sm border border-slate-700 font-semibold">
                    Mood: {entry.sentiment_label || "Unknown"}
                  </span>
                </div>
              </div>

              <div className="space-y-3 mb-4">
                <div>
                  <strong className="text-blue-400 block text-sm mb-1 uppercase">AI Question:</strong>
                  <p className="text-slate-200 leading-relaxed">{entry.question}</p>
                </div>
                <div>
                  <strong className="text-green-400 block text-sm mb-1 uppercase">User Answer:</strong>
                  <p className="text-slate-300 italic leading-relaxed">"{entry.response}"</p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}