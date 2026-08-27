// frontend/src/lib/api/reports.ts
// Typed client functions for weekly report endpoints

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function authHeader(token: string) {
  return { Authorization: `Bearer ${token}` };
}

export interface WeeklyReport {
  id: string;
  elder_id: string;
  cycle_start: string;
  cycle_end: string;
  engagement_trend: any;
  domains_completed: any;
  recurring_topics: any;
  emotional_trend: any;
  family_engagement: any;
  created_at: string;
}

export async function getWeeklyReports(
  elderId: string,
  token: string,
  limit: number = 10
): Promise<WeeklyReport[]> {
  const params = new URLSearchParams();
  params.append("limit", String(limit));
  const res = await fetch(`${API_URL}/api/elders/${elderId}/weekly-reports?${params}`, {
    headers: authHeader(token),
  });
  if (!res.ok) throw new Error("Failed to fetch weekly reports");
  return res.json();
}

export async function getLatestWeeklyReport(
  elderId: string,
  token: string
): Promise<WeeklyReport> {
  const res = await fetch(`${API_URL}/api/elders/${elderId}/weekly-reports/latest`, {
    headers: authHeader(token),
  });
  if (!res.ok) {
    if (res.status === 404) return null as any;
    throw new Error("Failed to fetch latest weekly report");
  }
  return res.json();
}