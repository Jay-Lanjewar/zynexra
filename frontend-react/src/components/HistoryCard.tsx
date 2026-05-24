import { Trash2 } from "lucide-react";
import type { HistoryRecord } from "../api";

interface HistoryCardProps {
  record: HistoryRecord;
  onDelete?: (recordId: number) => void;
  onClick?: (record: HistoryRecord) => void;
  isDeleting?: boolean;
}

function getSeverityColor(severity?: string): string {
  switch (severity?.toUpperCase()) {
    case "CRITICAL":
      return "bg-red-500/10 text-red-400 border-red-500/20";
    case "HIGH":
      return "bg-orange-500/10 text-orange-400 border-orange-500/20";
    case "MEDIUM":
      return "bg-amber-500/10 text-amber-400 border-amber-500/20";
    case "LOW":
      return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
    default:
      return "bg-slate-700/50 text-slate-400 border-slate-700";
  }
}

function getModeColor(mode?: string): string {
  switch (mode?.toUpperCase()) {
    case "AUDIT":
      return "bg-indigo-500/10 text-indigo-400 border-indigo-500/20";
    case "REDACTION":
      return "bg-amber-500/10 text-amber-400 border-amber-500/20";
    case "ADVISORY":
      return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
    default:
      return "bg-slate-700/50 text-slate-400 border-slate-700";
  }
}

function formatDate(timestamp?: string): string {
  if (!timestamp) return "Unknown";
  try {
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) return "Invalid date";
    return date.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      timeZoneName: "short",
    });
  } catch {
    return timestamp || "Unknown";
  }
}

function getPreviewText(record: HistoryRecord): string {
  if (record.preview) return record.preview;
  if (record.mode?.toUpperCase() === "ADVISORY") return "Advisory chat session";
  if (record.issue_count !== undefined)
    return `Found ${record.issue_count} issue${record.issue_count !== 1 ? "s" : ""}`;
  if (record.redaction_count !== undefined)
    return `Redacted ${record.redaction_count} entit${record.redaction_count !== 1 ? "ies" : "y"}`;
  return "No preview available";
}

export function HistoryCard({
  record,
  onDelete,
  onClick,
  isDeleting = false,
}: HistoryCardProps) {
  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onDelete) {
      onDelete(record.id);
    }
  };

  return (
    <div
      onClick={() => onClick?.(record)}
      className="group bg-slate-900/60 rounded-xl border border-slate-800 p-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-slate-700 hover:shadow-lg hover:shadow-black/20 cursor-pointer"
    >
      <div className="space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-sm text-slate-200 truncate">
              {record.filename || record.title || "Unnamed"}
            </h3>
            <p className="text-xs text-slate-500 mt-1">{formatDate(record.timestamp)}</p>
          </div>
          <button
            onClick={handleDelete}
            disabled={isDeleting}
            className="flex-shrink-0 p-1.5 text-slate-600 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors disabled:opacity-50"
            title="Delete record"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>

        <p className="text-sm text-slate-400 line-clamp-2">{getPreviewText(record)}</p>

        <div className="flex flex-wrap gap-2">
          <span
            className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium border ${getModeColor(record.mode)}`}
          >
            {record.mode?.toUpperCase() || "UNKNOWN"}
          </span>

          {record.severity && (
            <span
              className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium border ${getSeverityColor(record.severity)}`}
            >
              {record.severity.toUpperCase()}
            </span>
          )}

          {record.issue_count !== undefined && (
            <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-slate-800 text-slate-400 border border-slate-700">
              {record.issue_count} issue{record.issue_count !== 1 ? "s" : ""}
            </span>
          )}

          {record.redaction_count !== undefined && (
            <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-slate-800 text-slate-400 border border-slate-700">
              {record.redaction_count} redaction{record.redaction_count !== 1 ? "s" : ""}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
