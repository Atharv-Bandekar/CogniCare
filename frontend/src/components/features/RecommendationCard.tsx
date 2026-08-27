// frontend/src/components/features/RecommendationCard.tsx
"use client";

import { useState, FormEvent, ChangeEvent } from "react";
import { Recommendation } from "@/lib/api/recommendations";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Textarea } from "@/components/ui/Textarea";

interface RecommendationCardProps {
  recommendation: Recommendation;
  caregiverUserId: string;
  accessToken: string;
  onAction: () => void;
}

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-amber-100 text-amber-800",
  done: "bg-emerald-100 text-emerald-800",
  dismissed: "bg-slate-100 text-slate-800",
  timed_out: "bg-rose-100 text-rose-800",
};

export function RecommendationCard({
  recommendation,
  caregiverUserId,
  accessToken,
  onAction,
}: RecommendationCardProps) {
  const [isSubmitting, setIsSubmitting] = useState<string | null>(null);
  const [showSuggest, setShowSuggest] = useState(false);
  const [suggestionText, setSuggestionText] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleDone = async () => {
    setIsSubmitting("done");
    setError(null);
    try {
      const { markDone } = await import("@/lib/api/recommendations");
      await markDone(recommendation.id, caregiverUserId, accessToken);
      onAction();
    } catch (err) {
      setError("Failed to mark as done");
    } finally {
      setIsSubmitting(null);
    }
  };

  const handleDismiss = async () => {
    setIsSubmitting("dismiss");
    setError(null);
    try {
      const { markDismissed } = await import("@/lib/api/recommendations");
      await markDismissed(recommendation.id, caregiverUserId, accessToken);
      onAction();
    } catch (err) {
      setError("Failed to dismiss");
    } finally {
      setIsSubmitting(null);
    }
  };

  const handleSuggest = async (e: FormEvent) => {
    e.preventDefault();
    if (!suggestionText.trim()) return;
    setIsSubmitting("suggest");
    setError(null);
    try {
      const { submitSuggestion } = await import("@/lib/api/recommendations");
      await submitSuggestion(recommendation.id, suggestionText, caregiverUserId, accessToken);
      onAction();
    } catch (err) {
      setError("Failed to submit suggestion");
    } finally {
      setIsSubmitting(null);
      setShowSuggest(false);
      setSuggestionText("");
    }
  };

  const statusColor = STATUS_COLORS[recommendation.status] || "bg-slate-100 text-slate-800";
  const isResolved = recommendation.status !== "pending";

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex-1">
          <p className="text-slate-700 mb-2">{recommendation.recommendation_text}</p>
          <p className="text-sm text-slate-500">{recommendation.reason}</p>
        </div>
        <Badge variant="outline" className={statusColor}>
          {recommendation.status.replace("_", " ")}
        </Badge>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-400">
          {new Date(recommendation.created_at).toLocaleDateString()}
        </span>

        {recommendation.status === "pending" && (
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={handleDone}
              disabled={isSubmitting !== null}
              className="h-8 px-3"
            >
              {isSubmitting === "done" ? (
                <span className="flex items-center gap-1">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                </span>
              ) : (
                "Done"
              )}
            </Button>

            <Button
              variant="secondary"
              size="sm"
              onClick={handleDismiss}
              disabled={isSubmitting !== null}
              className="h-8 px-3"
            >
              {isSubmitting === "dismiss" ? (
                <span className="flex items-center gap-1">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                </span>
              ) : (
                "Dismiss"
              )}
            </Button>

            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowSuggest(true)}
              disabled={isSubmitting !== null}
              className="h-8 px-3"
            >
              Suggest
            </Button>
          </div>
        )}

        {recommendation.status === "done" && (
          <span className="text-xs text-emerald-600">Completed</span>
        )}

        {recommendation.status === "dismissed" && (
          <span className="text-xs text-slate-500">Dismissed</span>
        )}

        {recommendation.status === "timed_out" && (
          <span className="text-xs text-rose-500">Timed out</span>
        )}
      </div>

      {showSuggest && (
        <form onSubmit={handleSuggest} className="mt-3 space-y-2">
          <Textarea
            value={suggestionText}
            onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setSuggestionText(e.target.value)}
            placeholder="Enter your custom suggestion for the elder..."
            rows={3}
            className="w-full"
            disabled={isSubmitting !== null}
          />
          <div className="flex justify-end gap-2">
            <Button type="button" variant="ghost" size="sm" onClick={() => setShowSuggest(false)} disabled={isSubmitting !== null}>
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={isSubmitting !== null || !suggestionText.trim()}>
              {isSubmitting === "suggest" ? "Sending..." : "Submit"}
            </Button>
          </div>
          {error && <p className="text-sm text-rose-500">{error}</p>}
        </form>
      )}
    </Card>
  );
}