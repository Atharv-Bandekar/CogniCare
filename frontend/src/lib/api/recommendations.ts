// frontend/src/lib/api/recommendations.ts
// Typed client functions for recommendation endpoints

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function authHeader(token: string) {
  return { Authorization: `Bearer ${token}` };
}

export interface Recommendation {
  id: string;
  elder_id: string;
  interaction_id: string | null;
  recommendation_text: string;
  reason: string;
  status: "pending" | "done" | "dismissed" | "timed_out";
  created_at: string;
  resolved_at: string | null;
}

export interface SuggestionPayload {
  suggestion_text: string;
  caregiver_user_id: string;
}

export async function getRecommendations(
  elderId: string,
  token: string,
  status?: string
): Promise<Recommendation[]> {
  const params = new URLSearchParams();
  if (status) params.append("status", status);
  const res = await fetch(`${API_URL}/api/${elderId}/recommendations?${params}`, {
    headers: authHeader(token),
  });
  if (!res.ok) throw new Error("Failed to fetch recommendations");
  return res.json();
}

export async function markDone(
  recommendationId: string,
  caregiverUserId: string,
  token: string
): Promise<{ status: string }> {
  const res = await fetch(`${API_URL}/api/recommendations/${recommendationId}/done`, {
    method: "POST",
    headers: { ...authHeader(token), "Content-Type": "application/json" },
    body: JSON.stringify({ caregiver_user_id: caregiverUserId }),
  });
  if (!res.ok) throw new Error("Failed to mark done");
  return res.json();
}

export async function markDismissed(
  recommendationId: string,
  caregiverUserId: string,
  token: string
): Promise<{ status: string }> {
  const res = await fetch(`${API_URL}/api/recommendations/${recommendationId}/dismiss`, {
    method: "POST",
    headers: { ...authHeader(token), "Content-Type": "application/json" },
    body: JSON.stringify({ caregiver_user_id: caregiverUserId }),
  });
  if (!res.ok) throw new Error("Failed to dismiss");
  return res.json();
}

export async function submitSuggestion(
  recommendationId: string,
  suggestionText: string,
  caregiverUserId: string,
  token: string
): Promise<{ status: string }> {
  const res = await fetch(`${API_URL}/api/recommendations/${recommendationId}/suggest`, {
    method: "POST",
    headers: { ...authHeader(token), "Content-Type": "application/json" },
    body: JSON.stringify({ suggestion_text: suggestionText, caregiver_user_id: caregiverUserId }),
  });
  if (!res.ok) throw new Error("Failed to submit suggestion");
  return res.json();
}