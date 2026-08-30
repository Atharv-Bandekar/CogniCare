// frontend/src/components/features/DashboardTab.tsx
"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { DashboardTabProps } from "../../types";
import { Card } from "../ui/Card";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Badge } from "../ui/Badge";
import { RecommendationCard } from "./RecommendationCard";
import { WeeklyReportView } from "./WeeklyReportView";
import DemoBanner from "./DemoBanner";
import DemoGuide from "./DemoGuide";

// Inline SVG icons to avoid external dependency
interface IconProps {
  className?: string;
  size?: number;
}

const iconClass = ({ className = "", size = 16 }: IconProps) =>
  `h-${size} w-${size} ${className}`;

const PlusCircle = ({ className, size }: IconProps) => (
  <svg className={iconClass({ className, size })} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
    <circle cx="12" cy="12" r="10" /><path d="M12 8v8M8 12h8" />
  </svg>
);
const CheckCircle2 = ({ className, size }: IconProps) => (
  <svg className={iconClass({ className, size })} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" />
  </svg>
);

const Trash2 = ({ className, size }: IconProps) => (
  <svg className={iconClass({ className, size })} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
    <polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
  </svg>
);
const XCircle = ({ className, size }: IconProps) => (
  <svg className={iconClass({ className, size })} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
    <circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" />
  </svg>
);

const MessageSquare = ({ className, size }: IconProps) => (
  <svg className={iconClass({ className, size })} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
  </svg>
);
const Copy = ({ className, size }: IconProps) => (
  <svg className={iconClass({ className, size })} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
  </svg>
);
const Check = ({ className, size }: IconProps) => (
  <svg className={iconClass({ className, size })} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
    <polyline points="20 6 9 17 4 12" />
  </svg>
);
const Loader2 = ({ className, size }: IconProps) => (
  <svg className={iconClass({ className, size })} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
    <path d="M21 12a9 9 0 1 1-6.219-8.56" />
  </svg>
);
const AlertCircle = ({ className, size }: IconProps) => (
  <svg className={iconClass({ className, size })} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
    <circle cx="12" cy="12" r="10" />
    <line x1="12" y1="8" x2="12" y2="12" />
    <line x1="12" y1="16" x2="12.01" y2="16" />
  </svg>
);
const X = ({ className, size }: IconProps) => (
  <svg className={iconClass({ className, size })} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
    <line x1="18" y1="6" x2="6" y2="18" />
    <line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);
const ExternalLink = ({ className, size }: IconProps) => (
  <svg className={iconClass({ className, size })} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
    <polyline points="15 3 21 3 21 9" />
    <line x1="10" y1="14" x2="21" y2="3" />
  </svg>
);
const FileText = ({ className, size }: IconProps) => (
  <svg className={iconClass({ className, size })} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
    <polyline points="10 9 9 9 8 9" />
  </svg>
);

interface Elder {
  id: string;
  name: string;
  preferred_language: string;
  preferred_interaction_time: string;
  timezone: string;
  proximity: string;
  mobility_constraints: string[];
  personal_context: Record<string, any>;
  whatsapp_number: string;
  telegram_chat_id: string | null;
  telegram_user_id: string | null;
  onboarding_method: 'demo' | 'production';
  cycle_day: number;
  deep_link?: string;
  created_at: string;
}

interface Recommendation {
  id: string;
  elder_id: string;
  interaction_id: string | null;
  recommendation_text: string;
  reason: string;
  status: "pending" | "done" | "dismissed" | "timed_out";
  created_at: string;
  resolved_at: string | null;
}

interface Interaction {
  id: string;
  elder_id: string;
  domain: string;
  question: string;
  raw_response: string | null;
  transcript_source: string;
  language: string;
  twilio_message_sid: string | null;
  created_at: string;
  insight: {
    sentiment_label: string;
    sentiment_score: number;
    engagement_level: string;
    engagement_score: number;
    response_depth: string;
    topics: string[];
    safety_flag: boolean;
  } | null;
}

export default function DashboardTab({ session }: DashboardTabProps) {
  const [elders, setElders] = useState<Elder[]>([]);
  const [selectedElder, setSelectedElder] = useState<Elder | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [history, setHistory] = useState<Interaction[]>([]);
  const [weeklyReports, setWeeklyReports] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isAddingElder, setIsAddingElder] = useState(false);
  const [newElderForm, setNewElderForm] = useState({
    name: "",
    preferred_language: "en",
    preferred_interaction_time: "09:00",
    timezone: "Asia/Kolkata",
    proximity: "remote",
  });
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [deepLink, setDeepLink] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [latestReport, setLatestReport] = useState<any>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<{ elderId: string; name: string } | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [showGuide, setShowGuide] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Detect demo account
  const isDemoAccount = session?.user?.email === "demo@cognicare.ai";

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const authHeader = useMemo(() => ({ "Authorization": `Bearer ${session?.access_token}` }), [session?.access_token]);

  const loadElders = useCallback(async () => {
    try {
      const res = await fetch(`${apiUrl}/api/elders/`, { headers: authHeader });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Unknown error" }));
        console.error("Failed to load elders:", err);
        setElders([]);
        return;
      }
      const data = await res.json();
      setElders(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Failed to load elders", error);
      setElders([]);
    }
  }, [apiUrl, authHeader]);

  const loadRecommendations = useCallback(async (elderId: string) => {
    try {
      const res = await fetch(`${apiUrl}/api/elders/${elderId}/recommendations`, { headers: authHeader });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Unknown error" }));
        console.error("Failed to load recommendations:", err);
        setRecommendations([]);
        return;
      }
      const data = await res.json();
      setRecommendations(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error("Failed to load recommendations", error);
      setRecommendations([]);
    }
  }, [apiUrl, authHeader]);

  const loadHistory = useCallback(async (elderId: string) => {
    try {
      const res = await fetch(`${apiUrl}/api/elders/${elderId}/interactions`, { headers: authHeader });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Unknown error" }));
        console.error("Failed to load history:", err);
        setHistory([]);
        return;
      }
      const data = await res.json();
      setHistory(data?.history || []);
    } catch (error) {
      console.error("Failed to load history", error);
      setHistory([]);
    }
  }, [apiUrl, authHeader]);

  const loadWeeklyReports = useCallback(async (elderId: string) => {
    try {
      const res = await fetch(`${apiUrl}/api/elders/${elderId}/weekly-reports?limit=10`, { headers: authHeader });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Unknown error" }));
        console.error("Failed to load weekly reports:", err);
        setWeeklyReports([]);
        setLatestReport(null);
        return;
      }
      const data = await res.json();
      setWeeklyReports(Array.isArray(data) ? data : []);
      if (data && data.length > 0) {
        setLatestReport(data[0]);
      } else {
        setLatestReport(null);
      }
    } catch (error) {
      console.error("Failed to load weekly reports", error);
      setWeeklyReports([]);
      setLatestReport(null);
    }
  }, [apiUrl, authHeader]);

  const handleElderSelect = useCallback(async (elder: Elder) => {
    setSelectedElder(elder);
    setIsLoading(true);
    await Promise.all([
      loadRecommendations(elder.id),
      loadHistory(elder.id),
      loadWeeklyReports(elder.id),
    ]);
    // Fetch deep-link for the elder
    fetch(`${apiUrl}/api/elders/${elder.id}/deep-link`, { headers: authHeader })
        .then(res => res.json())
        .then(data => {
          if (data.deep_link) {
            setSelectedElder(prev => prev ? { ...prev, deep_link: data.deep_link } : null);
          }
        })
        .catch(console.error);
    setIsLoading(false);
  }, [apiUrl, authHeader, loadRecommendations, loadHistory, loadWeeklyReports]);

  const handleDeleteElder = useCallback(async (elderId: string) => {
    const res = await fetch(`${apiUrl}/api/elders/${elderId}`, {
      method: "DELETE",
      headers: authHeader,
    });
    if (!res.ok) {
      let errMsg = "Failed to delete elder";
      try {
        const err = await res.json();
        if (err && typeof err === 'object' && Object.keys(err).length > 0) {
          errMsg = err.detail || err.message || JSON.stringify(err);
        } else {
          errMsg = `Server error: ${res.status} ${res.statusText}`;
        }
      } catch {
        errMsg = `Server error: ${res.status} ${res.statusText}`;
      }
      throw new Error(errMsg);
    }
    return res.json();
  }, [apiUrl, authHeader]);

  const handleConfirmDelete = useCallback(async () => {
    if (!deleteConfirm) return;
    setIsDeleting(true);
    try {
      await handleDeleteElder(deleteConfirm.elderId);
      setSelectedElder(null);
      loadElders();
    } catch (error) {
      const errMsg = error instanceof Error ? error.message : "Failed to delete elder";
      console.error("Delete error:", errMsg);
      alert(errMsg);
    } finally {
      setIsDeleting(false);
      setDeleteConfirm(null);
    }
  }, [deleteConfirm, handleDeleteElder, loadElders]);



  const createTelegramElder = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setCreateError(null);
    try {
      const res = await fetch(`${apiUrl}/api/elders/telegram`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader },
        body: JSON.stringify({
          caregiver_user_id: session?.user?.id,
          ...newElderForm,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        const errMsg = data?.detail || "Failed to create elder";
        // Friendly error for duplicate name (unique constraint on whatsapp_number)
        if (errMsg.includes("duplicate") || errMsg.includes("unique") || errMsg.includes("already exists")) {
          setCreateError(`An elder with the name "${newElderForm.name}" already exists on this account. Please use a different name.`);
        } else {
          setCreateError(errMsg);
        }
        setIsSubmitting(false);
        return;
      }
      // Fetch deep-link for the new elder
      if (data.id) {
        const linkRes = await fetch(`${apiUrl}/api/elders/${data.id}/deep-link`, { headers: authHeader });
        const linkData = await linkRes.json();
        if (linkData.deep_link) {
          setDeepLink(linkData.deep_link);
          setCopiedId(linkData.deep_link);
          setTimeout(() => setCopiedId(null), 3000);
        }
        // Update selected elder with deep_link
        if (selectedElder?.id === data.id) {
          setSelectedElder(prev => prev ? { ...prev, deep_link: linkData.deep_link } : null);
        }
      }
      setIsSubmitting(false);
      setIsAddingElder(false);
      setCreateError(null);
      setNewElderForm({ name: "", preferred_language: "en", preferred_interaction_time: "09:00", timezone: "Asia/Kolkata", proximity: "remote" });
      loadElders();
    } catch (error) {
      console.error("Failed to create elder", error);
      setCreateError("Network error — is the backend running?");
      setIsSubmitting(false);
    }
  };

  const handleRecommendationAction = useCallback(() => {
    if (selectedElder) {
      loadRecommendations(selectedElder.id);
    }
  }, [selectedElder, loadRecommendations]);

  const copyDeepLink = (link: string) => {
    navigator.clipboard.writeText(link)
      .then(() => {
        setCopiedId(link);
        setTimeout(() => setCopiedId(null), 3000);
      })
      .catch((err) => {
        // Fallback for when clipboard API is not available or document not focused
        console.warn("Clipboard copy failed:", err);
        // Try fallback using a temporary textarea
        try {
          const textarea = document.createElement('textarea');
          textarea.value = link;
          textarea.style.position = 'fixed';
          textarea.style.opacity = '0';
          document.body.appendChild(textarea);
          textarea.select();
          document.execCommand('copy');
          document.body.removeChild(textarea);
          setCopiedId(link);
          setTimeout(() => setCopiedId(null), 3000);
        } catch (fallbackErr) {
          console.error("Fallback copy also failed:", fallbackErr);
          alert("Could not copy to clipboard. Please copy manually.");
        }
      });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      case 'done': return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      case 'dismissed': return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
      case 'timed_out': return 'bg-rose-500/20 text-rose-400 border-rose-500/30';
      default: return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  const getEngagementColor = (level: string) => {
    switch (level?.toLowerCase()) {
      case 'high': return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      case 'medium': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30';
      case 'low': return 'bg-rose-500/20 text-rose-400 border-rose-500/30';
      default: return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  const getSentimentColor = (label: string) => {
    switch (label?.toLowerCase()) {
      case 'positive': return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      case 'neutral': return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'negative': return 'bg-rose-500/20 text-rose-400 border-rose-500/30';
      default: return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

  const formatTime = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleString(undefined, {
        weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  };



  // Auto-show guide on first demo visit
  useEffect(() => {
    if (isDemoAccount && !sessionStorage.getItem("demo-guide-seen")) {
      setShowGuide(true);
      sessionStorage.setItem("demo-guide-seen", "true");
    }
  }, [isDemoAccount]);

  useEffect(() => {
    if (session?.access_token) {
      loadElders();
    }
  }, [session, loadElders]);

  if (!session?.access_token) {
    return (
      <Card className="text-center p-12">
        <AlertCircle className="mx-auto text-slate-500 mb-4" size={48} />
        <h3 className="text-lg font-semibold text-slate-300 mb-2">Please sign in</h3>
        <p className="text-slate-500">Sign in to view your caregiver dashboard.</p>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Demo account banner */}
      {isDemoAccount && (
        <DemoBanner elderCount={elders.length} onOpenGuide={() => setShowGuide(true)} />
      )}

      {/* Quick Start Guide modal */}
      <DemoGuide isOpen={showGuide} onClose={() => setShowGuide(false)} />

      {/* Header with Add Elder */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <h2 className="text-2xl font-bold text-blue-300">Caregiver Dashboard</h2>
        <div className="flex items-center gap-2 w-full sm:w-auto">
          {isDemoAccount && (
            <Button
              variant="secondary"
              onClick={() => setShowGuide(true)}
              className="flex items-center gap-1.5"
              title="Quick Start Guide"
            >
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <circle cx="12" cy="12" r="10" />
                <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
              Guide
            </Button>
          )}
          <Button
            variant="primary"
            onClick={() => { setCreateError(null); setIsAddingElder(true); }}
            className="flex-1 sm:flex-none"
          >
            <PlusCircle className="mr-2 h-4 w-4" />
            Add Elder via Telegram
          </Button>
        </div>
      </div>

      {/* Elder List */}
      <Card className="p-4">
        <h3 className="font-semibold text-slate-200 mb-4">Your Elders</h3>
        {elders.length === 0 ? (
          <p className="text-slate-500 text-center py-8">No elders linked yet. Click "Add Elder via Telegram" to get started.</p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {elders.map((elder) => (
              <div
                key={elder.id}
                className={`p-4 rounded-lg border transition-all ${
                  selectedElder?.id === elder.id
                    ? "border-blue-500 bg-blue-500/10 shadow-lg shadow-blue-500/10"
                    : "border-slate-700 hover:border-slate-500 cursor-pointer"
                }`}
                onClick={(e) => {
                  // Don't select if clicking the delete button
                  if (!(e.target as HTMLElement).closest('button')) {
                    handleElderSelect(elder);
                  }
                }}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h4 className="font-semibold text-slate-100">{elder.name}</h4>
                    <p className="text-sm text-slate-400">
                      {elder.onboarding_method === 'demo' ? 'Demo (Chat ID)' : 'Production (User ID)'}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {selectedElder?.id === elder.id && (
                      <CheckCircle2 className="text-blue-500 h-5 w-5" />
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-slate-500 hover:text-red-400 hover:bg-red-500/10 p-1"
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteConfirm({ elderId: elder.id, name: elder.name });
                      }}
                      title="Delete elder"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                {elder.onboarding_method === 'demo' && elder.telegram_chat_id && (
                  <div className="mt-3 p-2 bg-slate-800/50 rounded text-xs">
                    <span className="text-slate-400">Telegram Chat ID: </span>
                    <span className="font-mono text-slate-200">{elder.telegram_chat_id}</span>
                  </div>
                )}
                {elder.onboarding_method === 'production' && elder.telegram_user_id && (
                  <div className="mt-3 p-2 bg-slate-800/50 rounded text-xs">
                    <span className="text-slate-400">Telegram User ID: </span>
                    <span className="font-mono text-slate-200">{elder.telegram_user_id}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Add Elder Modal */}
      {isAddingElder && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="w-full max-w-md p-6">
            <h3 className="text-xl font-bold text-slate-100 mb-4">Add Elder via Telegram</h3>
            <p className="text-slate-400 mb-6">
              Create a production elder profile. You'll get a deep-link to share with the elder.
              When they tap it, their Telegram account links automatically.
            </p>
            {createError && (
              <div className="mb-4 p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg text-sm text-rose-300">
                {createError}
              </div>
            )}
            <form onSubmit={createTelegramElder} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Name</label>
                <Input
                  value={newElderForm.name}
                  onChange={(e) => setNewElderForm({...newElderForm, name: e.target.value})}
                  placeholder="Elder's name"
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Language</label>
                  <select
                    value={newElderForm.preferred_language}
                    onChange={(e) => setNewElderForm({...newElderForm, preferred_language: e.target.value})}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-slate-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="en">English</option>
                    <option value="hi">Hindi</option>
                    <option value="mr">Marathi</option>
                    <option value="ta">Tamil</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Time</label>
                  <Input
                    type="time"
                    value={newElderForm.preferred_interaction_time}
                    onChange={(e) => setNewElderForm({...newElderForm, preferred_interaction_time: e.target.value})}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Timezone</label>
                  <Input
                    value={newElderForm.timezone}
                    onChange={(e) => setNewElderForm({...newElderForm, timezone: e.target.value})}
                    placeholder="Asia/Kolkata"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-300 mb-1">Proximity</label>
                  <select
                    value={newElderForm.proximity}
                    onChange={(e) => setNewElderForm({...newElderForm, proximity: e.target.value})}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-slate-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="remote">Remote</option>
                    <option value="nearby">Nearby</option>
                    <option value="live_in">Live-in</option>
                  </select>
                </div>
              </div>
              <div className="flex gap-3 pt-4">
                <Button type="button" variant="secondary" onClick={() => setIsAddingElder(false)} disabled={isSubmitting} className="flex-1">
                  Cancel
                </Button>
                <Button type="submit" variant="primary" disabled={isSubmitting} className="flex-1">
                  {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <>Create & Get Link</>}
                </Button>
              </div>
            </form>
          </Card>
        </div>
      )}

      {/* Selected Elder Detail */}
      {selectedElder && (
        <>
          {/* Deep Link for all elders — always show so caregiver can share it */}
          {selectedElder.id && (
            <Card className="p-4 bg-blue-500/10 border-blue-500/30">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div className="flex items-center gap-3">
                  <ExternalLink className="text-blue-400 h-5 w-5" />
                  <div>
                    <p className="text-sm font-medium text-blue-300">Telegram Deep Link</p>
                    <p className="text-xs text-slate-400">Share this with the elder to link their Telegram</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <code className="flex-1 text-xs bg-slate-800 px-2 py-1 rounded font-mono text-blue-200 truncate">
                    {selectedElder.deep_link || `https://t.me/${process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME || 'CogniCareDemoBot'}?start=elder_${selectedElder.id}`}
                  </code>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => copyDeepLink(selectedElder.deep_link || `https://t.me/${process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME || 'CogniCareDemoBot'}?start=elder_${selectedElder.id}`)}
                  >
                    {copiedId ? (
                      <>
                        <Check className="h-4 w-4" />
                        <span>Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="h-4 w-4" />
                        <span>Copy</span>
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </Card>
          )}

          {/* Weekly Report */}
          {latestReport && (
            <WeeklyReportView report={latestReport} />
          )}

          {/* Recommendations */}
          <Card className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-slate-200">Recommendations for {selectedElder.name}</h3>
              <Badge variant="outline" className={getStatusColor('pending')}>
                {recommendations.filter(r => r.status === 'pending').length} Pending
              </Badge>
            </div>

            {recommendations.length === 0 ? (
              <p className="text-slate-500 text-center py-8">No recommendations yet. They appear after the elder answers questions.</p>
            ) : (
              <div className="space-y-3">
                {recommendations.map((rec) => (
                  <RecommendationCard
                    key={rec.id}
                    recommendation={rec}
                    caregiverUserId={session?.user?.id || ""}
                    accessToken={session?.access_token || ""}
                    onAction={handleRecommendationAction}
                  />
                ))}
              </div>
            )}
          </Card>

          {/* Interaction History */}
          <Card className="p-4">
            <h3 className="font-semibold text-slate-200 mb-4">Interaction History</h3>
            {history.length === 0 ? (
              <p className="text-slate-500 text-center py-8">No interactions yet.</p>
            ) : (
              <div className="space-y-4">
                {history.map((entry) => (
                  <div key={entry.id} className="border border-slate-700 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm font-medium text-blue-400">
                        {entry.domain?.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                      </span>
                      <span className="text-xs text-slate-400">{formatTime(entry.created_at)}</span>
                    </div>

                    <div className="space-y-3 mb-4">
                      <div>
                        <strong className="text-blue-400 block text-sm mb-1">Question:</strong>
                        <p className="text-slate-200 leading-relaxed">{entry.question}</p>
                      </div>
                      {entry.raw_response && (
                        <div>
                          <strong className="text-green-400 block text-sm mb-1">Answer:</strong>
                          <p className="text-slate-300 italic leading-relaxed">"{entry.raw_response}"</p>
                        </div>
                      )}
                    </div>

                    {entry.insight && (
                      <div className="flex flex-wrap items-center gap-2 pt-3 border-t border-slate-700/50">
                        <Badge variant="outline" className={getSentimentColor(entry.insight.sentiment_label)}>
                          {entry.insight.sentiment_label}
                        </Badge>
                        <Badge variant="outline" className={getEngagementColor(entry.insight.engagement_level)}>
                          {entry.insight.engagement_level}
                        </Badge>
                        {entry.insight.safety_flag && (
                          <Badge variant="outline" className="bg-rose-500/20 text-rose-400 border-rose-500/30">
                            Safety Flag
                          </Badge>
                        )}
                        {entry.insight.topics && entry.insight.topics.length > 0 && (
                          <span className="text-xs text-slate-400">
                            Topics: {entry.insight.topics.join(", ")}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* All Weekly Reports */}
          {weeklyReports.length > 1 && (
            <Card className="p-4">
              <h3 className="font-semibold text-slate-200 mb-4">Previous Weekly Reports</h3>
              <div className="space-y-3">
                {weeklyReports.slice(1).map((report) => (
                  <WeeklyReportView key={report.id} report={report} />
                ))}
              </div>
            </Card>
          )}
        </>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirm && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4 animate-fade-in">
          <div className="w-full max-w-md bg-slate-800 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden animate-slide-up">
            <div className="p-6">
              <div className="flex items-start justify-between mb-4">
                <div className="w-12 h-12 rounded-full bg-rose-500/20 flex items-center justify-center mx-auto mb-4">
                  <AlertCircle className="text-rose-400 h-6 w-6" />
                </div>
              </div>
              <h3 className="text-xl font-bold text-slate-100 text-center mb-2">Delete Elder?</h3>
              <p className="text-slate-400 text-center mb-6">
                Are you sure you want to delete <strong className="text-slate-100">{deleteConfirm.name}</strong>?
                This will permanently remove all their data including interaction history,
                recommendations, and weekly reports. This action cannot be undone.
              </p>
              <div className="flex gap-3">
                <Button
                  variant="secondary"
                  onClick={() => setDeleteConfirm(null)}
                  disabled={isDeleting}
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button
                  variant="danger"
                  onClick={handleConfirmDelete}
                  disabled={isDeleting}
                  className="flex-1 bg-rose-600 hover:bg-rose-700 border-rose-600"
                >
                  {isDeleting ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Deleting...
                    </>
                  ) : (
                    <>
                      <Trash2 className="mr-2 h-4 w-4" />
                      Delete Permanently
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}