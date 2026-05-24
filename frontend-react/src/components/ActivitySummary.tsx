import { FileSearch, Shield, MessageSquareText } from "lucide-react";
import type { HistorySummary } from "../api";

interface ActivitySummaryProps {
  summary?: HistorySummary;
  isLoading?: boolean;
  error?: string | null;
}

function StatCard({ icon: Icon, label, count }: { icon: React.ElementType; label: string; count: number }) {
  return (
    <div className="flex items-center gap-2 sm:gap-3 min-w-0">
      <div className="flex-shrink-0 w-8 h-8 sm:w-10 sm:h-10 bg-indigo-500/15 rounded-lg flex items-center justify-center text-indigo-400">
        <Icon className="w-5 h-5" />
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium text-slate-500 truncate">{label}</p>
        <p className="text-base sm:text-lg font-bold text-slate-100">{count}</p>
      </div>
    </div>
  );
}

export function ActivitySummary({ summary, isLoading = false, error = null }: ActivitySummaryProps) {
  if (error) {
    return (
      <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-6">
        <p className="text-sm text-amber-400">Unable to load activity summary</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 sm:p-6 animate-pulse overflow-hidden">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-12 bg-slate-700 rounded"></div>
          ))}
        </div>
      </div>
    );
  }

  const stats = summary?.stats || { audits: 0, redactions: 0, advisory: 0, total: 0 };

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 sm:p-6 overflow-hidden">
      <h3 className="text-sm font-semibold text-slate-200 mb-4">Activity Summary</h3>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-6">
        <StatCard icon={FileSearch} label="Audits" count={stats.audits} />
        <StatCard icon={Shield} label="Redactions" count={stats.redactions} />
        <StatCard icon={MessageSquareText} label="Advisory Chats" count={stats.advisory} />
      </div>
      <div className="mt-4 pt-4 border-t border-slate-800">
        <p className="text-xs text-slate-500">
          Total activities: <span className="font-semibold text-slate-200">{stats.total}</span>
        </p>
      </div>
    </div>
  );
}
