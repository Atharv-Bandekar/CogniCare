// frontend/src/components/features/WeeklyReportView.tsx
"use client";

import { WeeklyReport } from "@/lib/api/reports";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

interface WeeklyReportViewProps {
  report: WeeklyReport;
}

const DOMAIN_LABELS: Record<string, string> = {
  memory: "Memory",
  orientation: "Orientation",
  language: "Language",
  reasoning: "Reasoning",
  social: "Social",
  physical: "Physical",
};

function formatDomainCounts(counts: Record<string, number> | null | undefined): string {
  if (!counts || Object.keys(counts).length === 0) return "None";
  return Object.entries(counts)
    .map(([domain, count]) => `${DOMAIN_LABELS[domain] || domain}: ${count}`)
    .join(", ");
}

function formatTopics(topics: string[] | null | undefined): string {
  if (!topics || topics.length === 0) return "None";
  return topics.join(", ");
}

function formatFamilyEngagement(engagement: any): string {
  if (!engagement) return "No data";
  const parts = [];
  if (engagement.total_sent) parts.push(`Sent: ${engagement.total_sent}`);
  if (engagement.acted_on) parts.push(`Acted on: ${engagement.acted_on}`);
  if (engagement.pending) parts.push(`Pending: ${engagement.pending}`);
  if (engagement.timed_out) parts.push(`Timed out: ${engagement.timed_out}`);
  return parts.join(" | ") || "No data";
}

function getTrendColor(trend: string): string {
  switch (trend) {
    case "improving":
      return "bg-emerald-100 text-emerald-800";
    case "stable":
      return "bg-blue-100 text-blue-800";
    case "declining":
      return "bg-rose-100 text-rose-800";
    default:
      return "bg-slate-100 text-slate-800";
  }
}

export function WeeklyReportView({ report }: WeeklyReportViewProps) {
  const cycleStart = new Date(report.cycle_start).toLocaleDateString();
  const cycleEnd = new Date(report.cycle_end).toLocaleDateString();

  return (
    <Card className="p-6 mb-6 border-blue-200 bg-blue-50">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Weekly Cognitive Report</h3>
          <p className="text-sm text-slate-600">
            Cycle: {cycleStart} – {cycleEnd}
          </p>
        </div>
        <span className="text-xs text-slate-400">
          Generated: {new Date(report.created_at).toLocaleDateString()}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Engagement Trend */}
        <div>
          <h4 className="text-sm font-medium text-slate-700 mb-2">Engagement Trend</h4>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className={getTrendColor(report.engagement_trend?.trend || "unknown")}>
              {report.engagement_trend?.trend || "Unknown"}
            </Badge>
            <span className="text-sm text-slate-600">
              {report.engagement_trend?.summary || "No summary available"}
            </span>
          </div>
        </div>

        {/* Emotional Trend */}
        <div>
          <h4 className="text-sm font-medium text-slate-700 mb-2">Emotional Trend</h4>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className={getTrendColor(report.emotional_trend?.trend || "unknown")}>
              {report.emotional_trend?.trend || "Unknown"}
            </Badge>
            <span className="text-sm text-slate-600">
              {report.emotional_trend?.summary || "No summary available"}
            </span>
          </div>
        </div>

        {/* Domains Completed */}
        <div>
          <h4 className="text-sm font-medium text-slate-700 mb-2">Domains Completed</h4>
          <p className="text-sm text-slate-600">
            {formatDomainCounts(report.domains_completed)}
          </p>
        </div>

        {/* Recurring Topics */}
        <div>
          <h4 className="text-sm font-medium text-slate-700 mb-2">Recurring Topics</h4>
          <p className="text-sm text-slate-600">
            {formatTopics(report.recurring_topics)}
          </p>
        </div>

        {/* Family Engagement */}
        <div className="md:col-span-2">
          <h4 className="text-sm font-medium text-slate-700 mb-2">Family Engagement</h4>
          <p className="text-sm text-slate-600">
            {formatFamilyEngagement(report.family_engagement)}
          </p>
        </div>
      </div>
    </Card>
  );
}