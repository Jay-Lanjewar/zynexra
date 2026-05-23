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
      return "bg-red-100 text-red-800 border-red-200";
    case "HIGH":
      return "bg-orange-100 text-orange-800 border-orange-200";
    case "MEDIUM":
      return "bg-yellow-100 text-yellow-800 border-yellow-200";
    case "LOW":
      return "bg-green-100 text-green-800 border-green-200";
    default:
      return "bg-slate-100 text-slate-800 border-slate-200";
  }
}

function getModeColor(mode?: string): string {
  switch (mode?.toUpperCase()) {
    case "AUDIT":
      return "bg-blue-100 text-blue-800 border-blue-200";
    case "REDACTION":
      return "bg-purple-100 text-purple-800 border-purple-200";
    case "ADVISORY":
      return "bg-indigo-100 text-indigo-800 border-indigo-200";
    default:
      return "bg-slate-100 text-slate-800 border-slate-200";
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
      className="bg-white rounded-lg border border-slate-200 p-4 hover:shadow-md transition-shadow cursor-pointer hover:border-slate-300"
    >
      <div className="space-y-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-sm text-slate-900 truncate">
              {record.filename || record.title || "Unnamed"}
            </h3>
            <p className="text-xs text-slate-500 mt-1">{formatDate(record.timestamp)}</p>
          </div>
          <button
            onClick={handleDelete}
            disabled={isDeleting}
            className="flex-shrink-0 p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
            title="Delete record"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
          </button>
        </div>

        <p className="text-sm text-slate-600 line-clamp-2">{getPreviewText(record)}</p>

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
            <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
              {record.issue_count} issue{record.issue_count !== 1 ? "s" : ""}
            </span>
          )}

          {record.redaction_count !== undefined && (
            <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
              {record.redaction_count} redaction{record.redaction_count !== 1 ? "s" : ""}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
