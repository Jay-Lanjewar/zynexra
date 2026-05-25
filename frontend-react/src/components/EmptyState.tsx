import { CheckCircle2, ShieldCheck, FileUp, Search, MessageSquare, Eraser, FolderOpen, AlertTriangle } from "lucide-react";
import type { AppMode } from "../types";

type EmptyStateProps = {
  type: "NO_ISSUES" | "NO_FILE" | "NO_RECORDS" | "NO_SEARCH_RESULTS" | "NO_CHATS" | "LOW_CONFIDENCE";
  onReset?: () => void;
  mode?: AppMode;
  onAction?: () => void;
  actionLabel?: string;
  onRetry?: () => void;
};

const emptyStateIcons = {
  NO_ISSUES: CheckCircle2,
  NO_FILE: FileUp,
  NO_RECORDS: FolderOpen,
  NO_SEARCH_RESULTS: Search,
  NO_CHATS: MessageSquare,
  LOW_CONFIDENCE: AlertTriangle,
};

const emptyStateStyles = {
  NO_ISSUES: {
    icon: "bg-emerald-500/10 text-emerald-400",
    title: "text-emerald-300",
    desc: "text-emerald-400/70",
    bg: "border-emerald-500/20 bg-emerald-500/5",
    button: "bg-emerald-500 hover:bg-emerald-400 text-slate-950",
  },
  NO_FILE: {
    icon: "bg-slate-800 text-slate-400",
    title: "text-slate-300",
    desc: "text-slate-500",
    bg: "border-slate-700/50 bg-slate-900/50",
    button: "bg-indigo-500 hover:bg-indigo-400 text-white",
  },
  NO_RECORDS: {
    icon: "bg-indigo-500/10 text-indigo-400",
    title: "text-slate-200",
    desc: "text-slate-400",
    bg: "border-slate-700/50 bg-slate-900/50",
    button: "bg-indigo-500 hover:bg-indigo-400 text-white",
  },
  NO_SEARCH_RESULTS: {
    icon: "bg-amber-500/10 text-amber-400",
    title: "text-slate-200",
    desc: "text-slate-400",
    bg: "border-slate-700/50 bg-slate-900/50",
    button: "bg-indigo-500 hover:bg-indigo-400 text-white",
  },
  NO_CHATS: {
    icon: "bg-emerald-500/10 text-emerald-400",
    title: "text-slate-200",
    desc: "text-slate-400",
    bg: "border-slate-700/50 bg-slate-900/50",
    button: "bg-indigo-500 hover:bg-indigo-400 text-white",
  },
  LOW_CONFIDENCE: {
    icon: "bg-red-500/10 text-red-400",
    title: "text-red-300",
    desc: "text-red-400/80",
    bg: "border-red-500/20 bg-red-500/5",
    button: "bg-indigo-500 hover:bg-indigo-400 text-white",
  },
};

const emptyStateContent = {
  NO_ISSUES: {
    title: "No Issues Found",
    description: "Analysis complete. No major contractual risks were identified in the reviewed clauses. Always consult legal counsel for final approval.",
    actionLabel: "Audit Another Contract",
  },
  NO_FILE: {
    title: "No File Selected",
    description: "Upload a contract file to begin the audit process. Supported formats: PDF, TXT, DOC, DOCX.",
    actionLabel: undefined,
  },
  NO_RECORDS: {
    title: "No records yet",
    description: "Start by creating a new audit, redaction, or advisory chat to see it here.",
    actionLabel: "Start New",
  },
  NO_SEARCH_RESULTS: {
    title: "No results found",
    description: "Try adjusting your filters or search terms to find what you're looking for.",
    actionLabel: "Clear Filters",
  },
  NO_CHATS: {
    title: "No chats yet",
    description: "Start a new advisory chat to ask legal-practice questions.",
    actionLabel: "Start Chat",
  },
  LOW_CONFIDENCE: {
    title: "Low Confidence Response",
    description: "Some sections may require manual legal review due to limited structural clarity. Consider re-running the analysis or consulting legal counsel.",
    actionLabel: "Try Again",
  },
};

export function EmptyState({ type, onReset, onAction, actionLabel, onRetry }: EmptyStateProps) {
  const Icon = emptyStateIcons[type];
  const styles = emptyStateStyles[type];
  const content = emptyStateContent[type];
  const defaultAction = type === "NO_ISSUES" ? onReset : type === "NO_SEARCH_RESULTS" ? onReset : type === "LOW_CONFIDENCE" ? onRetry || onReset : undefined;
  const label = actionLabel ?? content.actionLabel;

  return (
    <div
      role="status"
      aria-live="polite"
      className={`flex flex-col items-center justify-center rounded-xl border p-8 text-center shadow-lg shadow-black/10 ${styles.bg}`}
    >
      <div className={`flex h-16 w-16 items-center justify-center rounded-full ${styles.icon}`}>
        <Icon className="h-8 w-8" aria-hidden="true" />
      </div>
      <h3 className={`mt-4 text-lg font-semibold ${styles.title}`}>{content.title}</h3>
      <p className={`mt-2 max-w-md text-sm leading-relaxed ${styles.desc}`}>{content.description}</p>
      {(label && (onAction || defaultAction)) && (
        <button
          type="button"
          onClick={onAction || defaultAction}
          className={`mt-6 rounded-lg px-5 py-2 text-sm font-semibold text-white transition-colors ${styles.button}`}
        >
          {label}
        </button>
      )}
    </div>
  );
}
