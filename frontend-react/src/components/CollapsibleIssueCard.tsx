import { useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  FileText,
  ChevronDown,
  ChevronRight,
  Copy,
  Check,
} from "lucide-react";
import type { AuditIssue, SeverityLevel } from "../types";

type CollapsibleIssueCardProps = {
  issue: AuditIssue;
  index: number;
};

const severityConfig: Record<string, { bg: string; text: string; ring: string; border: string }> = {
  CRITICAL: { bg: "bg-red-500/10", text: "text-red-400", ring: "ring-red-500/30", border: "border-red-500/20" },
  HIGH: { bg: "bg-orange-500/10", text: "text-orange-400", ring: "ring-orange-500/30", border: "border-orange-500/20" },
  MEDIUM: { bg: "bg-amber-500/10", text: "text-amber-400", ring: "ring-amber-500/30", border: "border-amber-500/20" },
  LOW: { bg: "bg-emerald-500/10", text: "text-emerald-400", ring: "ring-emerald-500/30", border: "border-emerald-500/20" },
  UNRATED: { bg: "bg-slate-500/10", text: "text-slate-400", ring: "ring-slate-500/30", border: "border-slate-500/20" },
};

function getSeverityConfig(severity: string) {
  const key = (severity.toUpperCase() as SeverityLevel) || "UNRATED";
  return severityConfig[key] || severityConfig.UNRATED;
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-slate-500 transition-colors hover:bg-slate-800 hover:text-slate-300"
      title="Copy to clipboard"
    >
      {copied ? (
        <>
          <Check className="h-3.5 w-3.5 text-emerald-400" />
          <span className="text-emerald-400">Copied</span>
        </>
      ) : (
        <>
          <Copy className="h-3.5 w-3.5" />
          <span>Copy</span>
        </>
      )}
    </button>
  );
}

export function CollapsibleIssueCard({ issue, index }: CollapsibleIssueCardProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const severity = getSeverityConfig(issue.severity);
  const title = issue.issue_title || `Issue ${index + 1}`;

  return (
    <article className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60 shadow-sm transition-all duration-200 hover:border-slate-700">
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex w-full items-center justify-between p-4 text-left transition-colors hover:bg-slate-800/30"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500/10">
            <span className="text-sm font-bold text-indigo-400">{index + 1}</span>
          </div>
          <div>
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <FileText className="h-3.5 w-3.5" />
              <span>{issue.location || "Unspecified location"}</span>
            </div>
            <h3 className="mt-1 font-semibold text-slate-100">{title}</h3>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden flex-wrap gap-2 sm:flex">
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ${severity.bg} ${severity.text} ${severity.ring}`}
            >
              {issue.severity || "UNRATED"}
            </span>
            <span className="rounded-full bg-slate-800 px-2.5 py-0.5 text-xs font-semibold text-slate-400 ring-1 ring-slate-700/50">
              {issue.category || "Uncategorized"}
            </span>
          </div>
          {isExpanded ? (
            <ChevronDown className="h-5 w-5 text-slate-500" />
          ) : (
            <ChevronRight className="h-5 w-5 text-slate-500" />
          )}
        </div>
      </button>

      {isExpanded && (
        <div className="border-t border-slate-800 p-4">
          <div className="mb-4 flex gap-2 sm:hidden">
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ${severity.bg} ${severity.text} ${severity.ring}`}
            >
              {issue.severity || "UNRATED"}
            </span>
            <span className="rounded-full bg-slate-800 px-2.5 py-0.5 text-xs font-semibold text-slate-400 ring-1 ring-slate-700/50">
              {issue.category || "Uncategorized"}
            </span>
          </div>

          <div className="space-y-4">
            <section>
              <div className="mb-2 flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-300">
                  <AlertTriangle className="h-4 w-4 text-amber-400" />
                  Quoted Text
                </div>
                <CopyButton text={issue.quoted_text || ""} />
              </div>
              <blockquote className="rounded-lg border-l-2 border-slate-700 bg-slate-950/50 px-4 py-3 font-mono text-sm leading-6 text-slate-400">
                {issue.quoted_text || "No quoted text returned."}
              </blockquote>
            </section>

            <div className="grid gap-4 md:grid-cols-2">
              <section className="rounded-lg border-l-2 border-orange-500/30 bg-slate-800/30 p-4">
                <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-300">
                  <AlertTriangle className="h-4 w-4 text-orange-400" />
                  Risk Explanation
                </div>
                <p className="text-sm leading-6 text-slate-400">
                  {issue.risk_explanation || "No risk explanation returned."}
                </p>
              </section>

              <section className="rounded-lg border-l-2 border-emerald-500/30 bg-slate-800/30 p-4">
                <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-300">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  Suggested Improvement
                </div>
                <p className="text-sm leading-6 text-slate-400">
                  {issue.suggested_improvement || "No suggested improvement returned."}
                </p>
              </section>
            </div>
          </div>
        </div>
      )}
    </article>
  );
}
