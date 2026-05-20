import type { HistorySummary } from "../api";

interface ActivitySummaryProps {
  summary?: HistorySummary;
  isLoading?: boolean;
  error?: string | null;
}

function StatCard({ icon: Icon, label, count }: { icon: React.ReactNode; label: string; count: number }) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex-shrink-0 w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center text-blue-600">
        {Icon}
      </div>
      <div>
        <p className="text-xs font-medium text-slate-600">{label}</p>
        <p className="text-lg font-bold text-slate-900">{count}</p>
      </div>
    </div>
  );
}

export function ActivitySummary({ summary, isLoading = false, error = null }: ActivitySummaryProps) {
  if (error) {
    return (
      <div className="bg-gradient-to-br from-amber-50 to-orange-50 rounded-lg border border-amber-200 p-6">
        <p className="text-sm text-amber-800">Unable to load activity summary</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg border border-blue-100 p-6 animate-pulse">
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-12 bg-slate-200 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  const stats = summary?.stats || { audits: 0, redactions: 0, advisory: 0, total: 0 };

  return (
    <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg border border-blue-100 p-6">
      <h3 className="text-sm font-semibold text-slate-900 mb-4">Activity Summary</h3>
      <div className="grid grid-cols-3 gap-6">
        <StatCard
          icon={
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          }
          label="Audits"
          count={stats.audits}
        />
        <StatCard
          icon={
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"
              />
            </svg>
          }
          label="Redactions"
          count={stats.redactions}
        />
        <StatCard
          icon={
            <svg
              className="w-5 h-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8 12h.01M12 12h.01M16 12h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          }
          label="Advisory Chats"
          count={stats.advisory}
        />
      </div>
      <div className="mt-4 pt-4 border-t border-blue-200">
        <p className="text-xs text-slate-600">
          Total activities: <span className="font-semibold text-slate-900">{stats.total}</span>
        </p>
      </div>
    </div>
  );
}
