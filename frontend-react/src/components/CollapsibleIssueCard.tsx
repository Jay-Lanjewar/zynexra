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
  CRITICAL: { bg: "bg-red-50", text: "text-red-700", ring: "ring-red-200", border: "border-red-200" },
  HIGH: { bg: "bg-orange-50", text: "text-orange-700", ring: "ring-orange-200", border: "border-orange-200" },
  MEDIUM: { bg: "bg-amber-50", text: "text-amber-700", ring: "ring-amber-200", border: "border-amber-200" },
  LOW: { bg: "bg-emerald-50", text: "text-emerald-700", ring: "ring-emerald-200", border: "border-emerald-200" },
  UNRATED: { bg: "bg-slate-100", text: "text-slate-700", ring: "ring-slate-200", border: "border-slate-200" },
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
      className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium text-slate-500 hover:bg-slate-100 hover:text-slate-700 transition-colors"
      title="Copy to clipboard"
    >
      {copied ? (
        <>
          <Check className="h-3.5 w-3.5 text-emerald-600" />
          <span className="text-emerald-600">Copied</span>
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
    <article className={`overflow-hidden rounded-lg border ${severity.border} bg-white shadow-sm`}>
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex w-full items-center justify-between p-4 text-left hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className={`flex h-8 w-8 items-center justify-center rounded-md ${severity.bg}`}>
            <span className={`text-sm font-bold ${severity.text}`}>{index + 1}</span>
          </div>
          <div>
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <FileText className="h-3.5 w-3.5" />
              <span>{issue.location || "Unspecified location"}</span>
            </div>
            <h3 className="mt-1 font-semibold text-slate-900">{title}</h3>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden flex-wrap gap-2 sm:flex">
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ${severity.bg} ${severity.text} ${severity.ring}`}
            >
              {issue.severity || "UNRATED"}
            </span>
            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-700 ring-1 ring-slate-200">
              {issue.category || "Uncategorized"}
            </span>
          </div>
          {isExpanded ? (
            <ChevronDown className="h-5 w-5 text-slate-400" />
          ) : (
            <ChevronRight className="h-5 w-5 text-slate-400" />
          )}
        </div>
      </button>

      {isExpanded && (
        <div className="border-t border-slate-100 p-4">
          <div className="flex gap-2 sm:hidden mb-4">
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ${severity.bg} ${severity.text} ${severity.ring}`}
            >
              {issue.severity || "UNRATED"}
            </span>
            <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-semibold text-slate-700 ring-1 ring-slate-200">
              {issue.category || "Uncategorized"}
            </span>
          </div>

          <div className="space-y-4">
            <section>
              <div className="mb-2 flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                  <AlertTriangle className="h-4 w-4 text-amber-600" />
                  Quoted Text
                </div>
                <CopyButton text={issue.quoted_text || ""} />
              </div>
              <blockquote className="rounded-md border-l-3 border-slate-300 bg-slate-50 px-4 py-3 text-sm leading-6 text-slate-700 font-mono">
                {issue.quoted_text || "No quoted text returned."}
              </blockquote>
            </section>

            <div className="grid gap-4 md:grid-cols-2">
              <section className="rounded-lg bg-slate-50 p-4">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-700 mb-2">
                  <AlertTriangle className="h-4 w-4 text-orange-600" />
                  Risk Explanation
                </div>
                <p className="text-sm leading-6 text-slate-600">
                  {issue.risk_explanation || "No risk explanation returned."}
                </p>
              </section>

              <section className="rounded-lg bg-emerald-50 p-4">
                <div className="flex items-center gap-2 text-sm font-semibold text-emerald-800 mb-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  Suggested Improvement
                </div>
                <p className="text-sm leading-6 text-emerald-700">
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