import { useState, useMemo } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  FileText,
  ChevronDown,
  ChevronRight,
  Copy,
  Check,
  Lightbulb,
  GitCompareArrows,
} from "lucide-react";
import type { AuditIssue, SeverityLevel } from "../types";

type CollapsibleIssueCardProps = {
  issue: AuditIssue;
  index: number;
};

const severityConfig: Record<string, { bg: string; text: string; ring: string; border: string; strip: string; label: string }> = {
  CRITICAL: { bg: "bg-red-500/10", text: "text-red-400", ring: "ring-red-500/30", border: "border-red-500/20", strip: "border-l-red-500/60", label: "CRITICAL" },
  HIGH: { bg: "bg-orange-500/10", text: "text-orange-400", ring: "ring-orange-500/30", border: "border-orange-500/20", strip: "border-l-orange-500/60", label: "HIGH" },
  MEDIUM: { bg: "bg-amber-500/10", text: "text-amber-400", ring: "ring-amber-500/30", border: "border-amber-500/20", strip: "border-l-amber-500/60", label: "MEDIUM" },
  LOW: { bg: "bg-emerald-500/10", text: "text-emerald-400", ring: "ring-emerald-500/30", border: "border-emerald-500/20", strip: "border-l-emerald-500/60", label: "LOW" },
  UNRATED: { bg: "bg-slate-500/10", text: "text-slate-400", ring: "ring-slate-500/30", border: "border-slate-500/20", strip: "border-l-slate-500/60", label: "UNRATED" },
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

const semanticTerms = [
  { pattern: /\bindemnif(y|ies|ication)\b/gi, className: "text-amber-300 font-bold underline decoration-amber-500/30 decoration-dotted underline-offset-2" },
  { pattern: /\bperpetual\b/gi, className: "text-amber-300 font-bold underline decoration-amber-500/30 decoration-dotted underline-offset-2" },
  { pattern: /\bunlimited liability\b/gi, className: "text-red-300 font-bold underline decoration-red-500/30 decoration-wavy underline-offset-2" },
  { pattern: /\btermination\b/gi, className: "text-indigo-300 font-medium underline decoration-indigo-500/30 decoration-dotted underline-offset-2" },
  { pattern: /\bexclusive jurisdiction\b/gi, className: "text-cyan-300 font-medium underline decoration-cyan-500/30 decoration-dotted underline-offset-2" },
  { pattern: /\bconfidentiality survives\b/gi, className: "text-violet-300 font-medium underline decoration-violet-500/30 decoration-dotted underline-offset-2" },
  { pattern: /\bforce majeure\b/gi, className: "text-orange-300 font-medium underline decoration-orange-500/30 decoration-dotted underline-offset-2" },
  { pattern: /\blimitation of liability\b/gi, className: "text-red-300 font-medium underline decoration-red-500/30 decoration-dotted underline-offset-2" },
  { pattern: /\bgoverning law\b/gi, className: "text-teal-300 font-medium underline decoration-teal-500/30 decoration-dotted underline-offset-2" },
  { pattern: /\barbitration\b/gi, className: "text-amber-300 font-medium underline decoration-amber-500/30 decoration-dotted underline-offset-2" },
];

function SemanticText({ text }: { text: string }) {
  const parts = useMemo(() => {
    if (!text) return [text];
    const matches: { start: number; end: number; className: string }[] = [];
    for (const { pattern, className } of semanticTerms) {
      let m;
      while ((m = pattern.exec(text)) !== null) {
        matches.push({ start: m.index, end: m.index + m[0].length, className });
      }
    }
    matches.sort((a, b) => a.start - b.start);
    if (matches.length === 0) return [text];
    const result: { text: string; highlight?: string }[] = [];
    let cursor = 0;
    for (const match of matches) {
      if (match.start > cursor) {
        result.push({ text: text.slice(cursor, match.start) });
      }
      result.push({ text: text.slice(match.start, match.end), highlight: match.className });
      cursor = match.end;
    }
    if (cursor < text.length) {
      result.push({ text: text.slice(cursor) });
    }
    return result;
  }, [text]);

  if (parts.length === 1) {
    return <>{text}</>;
  }

  return (
    <>
      {parts.map((part, i) =>
        part.highlight ? (
          <span key={i} className={part.highlight}>{part.text}</span>
        ) : (
          <span key={i}>{part.text}</span>
        )
      )}
    </>
  );
}

export function CollapsibleIssueCard({ issue, index }: CollapsibleIssueCardProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const severity = getSeverityConfig(issue.severity);
  const title = issue.issue_title || `Issue ${index + 1}`;
  const hasContradiction = issue.contradiction_detected;

  return (
    <article
      className={`overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60 shadow-sm transition-all duration-200 hover:border-slate-700 hover:shadow-md hover:shadow-black/20 ${severity.strip} border-l-4`}
    >
      {hasContradiction && (
        <div className="flex items-start gap-2 border-b border-amber-500/20 bg-amber-500/5 px-4 py-2.5 text-xs text-amber-400">
          <GitCompareArrows className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          <span className="font-medium">Conflicting contractual obligations detected.</span>
        </div>
      )}
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex w-full items-center justify-between p-4 text-left transition-colors hover:bg-slate-800/30"
      >
        <div className="flex items-center gap-3">
          <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${severity.bg}`}>
            <span className={`text-sm font-bold ${severity.text}`}>{index + 1}</span>
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
              className={`rounded-full px-2.5 py-0.5 text-xs font-bold tracking-wide ring-1 ${severity.bg} ${severity.text} ${severity.ring}`}
            >
              {severity.label}
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
              className={`rounded-full px-2.5 py-0.5 text-xs font-bold tracking-wide ring-1 ${severity.bg} ${severity.text} ${severity.ring}`}
            >
              {severity.label}
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
              <blockquote className="rounded-lg border-l-4 border-slate-700 bg-slate-950/70 px-4 py-3 font-mono text-sm leading-6 text-slate-400">
                <SemanticText text={issue.quoted_text || "No quoted text returned."} />
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

              <section className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4">
                <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-emerald-300">
                  <Lightbulb className="h-4 w-4 text-emerald-400" />
                  Suggested Improvement
                </div>
                <p className="text-sm leading-6 text-emerald-400/90">
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
