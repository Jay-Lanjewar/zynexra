import { CheckCircle2, ShieldCheck, FileUp, Search, MessageSquare, Eraser, FolderOpen } from "lucide-react";
import type { AppMode } from "../types";

type EmptyStateProps = {
  type: "NO_ISSUES" | "NO_FILE" | "NO_RECORDS" | "NO_SEARCH_RESULTS" | "NO_CHATS";
  onReset?: () => void;
  mode?: AppMode;
  onAction?: () => void;
  actionLabel?: string;
};

const emptyStateIcons = {
  NO_ISSUES: CheckCircle2,
  NO_FILE: FileUp,
  NO_RECORDS: FolderOpen,
  NO_SEARCH_RESULTS: Search,
  NO_CHATS: MessageSquare,
};

const emptyStateStyles = {
  NO_ISSUES: {
    icon: "bg-emerald-100 text-emerald-600",
    title: "text-emerald-900",
    desc: "text-emerald-700",
    bg: "border-emerald-200 bg-emerald-50",
    button: "bg-emerald-600 hover:bg-emerald-700",
  },
  NO_FILE: {
    icon: "bg-slate-100 text-slate-400",
    title: "text-slate-700",
    desc: "text-slate-500",
    bg: "border-slate-200 bg-slate-50",
    button: "bg-slate-900 hover:bg-slate-800",
  },
  NO_RECORDS: {
    icon: "bg-blue-100 text-blue-500",
    title: "text-slate-900",
    desc: "text-slate-600",
    bg: "border-slate-200 bg-white",
    button: "bg-slate-900 hover:bg-slate-800",
  },
  NO_SEARCH_RESULTS: {
    icon: "bg-amber-100 text-amber-500",
    title: "text-slate-900",
    desc: "text-slate-600",
    bg: "border-slate-200 bg-white",
    button: "bg-slate-900 hover:bg-slate-800",
  },
  NO_CHATS: {
    icon: "bg-emerald-100 text-emerald-500",
    title: "text-slate-900",
    desc: "text-slate-600",
    bg: "border-slate-200 bg-white",
    button: "bg-slate-900 hover:bg-slate-800",
  },
};

const emptyStateContent = {
  NO_ISSUES: {
    title: "No Issues Found",
    description: "The contract analysis completed successfully with no significant issues detected. This doesn't guarantee the contract is risk-free, but no obvious concerns were identified.",
    actionLabel: "Audit Another Contract",
  },
  NO_FILE: {
    title: "No File Selected",
    description: "Upload a contract file to begin the audit process. Supported formats: PDF, TXT, DOC.",
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
};

export function EmptyState({ type, onReset, onAction, actionLabel }: EmptyStateProps) {
  const Icon = emptyStateIcons[type];
  const styles = emptyStateStyles[type];
  const content = emptyStateContent[type];
  const defaultAction = type === "NO_ISSUES" ? onReset : type === "NO_SEARCH_RESULTS" ? onReset : undefined;
  const label = actionLabel ?? content.actionLabel;

  return (
    <div
      role="status"
      aria-live="polite"
      className={`flex flex-col items-center justify-center rounded-lg border p-8 text-center ${styles.bg}`}
    >
      <div className={`flex h-16 w-16 items-center justify-center rounded-full ${styles.icon}`}>
        <Icon className="h-8 w-8" aria-hidden="true" />
      </div>
      <h3 className={`mt-4 text-lg font-semibold ${styles.title}`}>{content.title}</h3>
      <p className={`mt-2 max-w-md text-sm ${styles.desc}`}>{content.description}</p>
      {(label && (onAction || defaultAction)) && (
        <button
          type="button"
          onClick={onAction || defaultAction}
          className={`mt-6 rounded-md px-4 py-2 text-sm font-semibold text-white transition-colors ${styles.button}`}
        >
          {label}
        </button>
      )}
    </div>
  );
}