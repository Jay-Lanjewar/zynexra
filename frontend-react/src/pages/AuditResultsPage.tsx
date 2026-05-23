import { ArrowLeft, AlertCircle, AlertTriangle, CheckCircle2, Eraser, FileSearch, MessageSquareText, ShieldCheck } from "lucide-react";
import { CollapsibleIssueCard } from "../components/CollapsibleIssueCard";
import { ExportButtons } from "../components/ExportButtons";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { ConfidenceBadge } from "../components/ConfidenceBadge";
import type { AuditResponse } from "../types";
import type { ApiError } from "../api";
import { groupIssuesByCategory, getSeverityCounts } from "../utils";

type AuditResultsPageProps = {
  result: AuditResponse | null;
  error: ApiError | null;
  onReset: () => void;
};

const severityConfig: Record<string, { label: string; bg: string; text: string; icon: React.ElementType }> = {
  CRITICAL: { label: "Critical", bg: "bg-red-500/10 text-red-400", text: "text-red-400", icon: AlertCircle },
  HIGH: { label: "High", bg: "bg-orange-500/10 text-orange-400", text: "text-orange-400", icon: AlertCircle },
  MEDIUM: { label: "Medium", bg: "bg-amber-500/10 text-amber-400", text: "text-amber-400", icon: AlertCircle },
  LOW: { label: "Low", bg: "bg-emerald-500/10 text-emerald-400", text: "text-emerald-400", icon: CheckCircle2 },
  UNRATED: { label: "Unrated", bg: "bg-slate-500/10 text-slate-400", text: "text-slate-400", icon: AlertCircle },
};

function SeveritySummary({ issues }: { issues: AuditResponse["issues"] }) {
  const counts = getSeverityCounts(issues);
  const hasIssues = Object.values(counts).some((v) => v > 0);

  if (!hasIssues) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {Object.entries(counts).map(([severity, count]) => {
        if (count === 0) return null;
        const config = severityConfig[severity];
        const Icon = config.icon;
        return (
          <div
            key={severity}
            className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium ${config.bg}`}
          >
            <Icon className="h-4 w-4" />
            <span>
              {count} {config.label}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function CategorySummary({ issues }: { issues: AuditResponse["issues"] }) {
  const groups = groupIssuesByCategory(issues);

  if (groups.length <= 1) return null;

  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {groups.map((group) => (
        <span
          key={group.category}
          className="rounded-full bg-slate-800 px-2.5 py-1 text-xs font-medium text-slate-400"
        >
          {group.category}: {group.count}
        </span>
      ))}
    </div>
  );
}

function ConfidenceSection({ label, score }: { label: string; score: number }) {
  const percentage = Math.round(score * 100);
  const labelColor =
    label === "HIGH" ? "bg-emerald-500" : label === "MEDIUM" ? "bg-amber-500" : "bg-red-500";

  return (
    <div className="mt-4 flex items-center gap-4 rounded-xl border border-slate-800 bg-slate-900/60 px-5 py-4">
      <div className="flex flex-col">
        <span className="text-xs text-slate-500">Confidence</span>
        <span className="text-2xl font-bold text-slate-100">{percentage}%</span>
      </div>
      <div className="flex flex-1 flex-col gap-1.5">
        <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
          <div
            className={`h-full rounded-full transition-all duration-1000 ease-out ${labelColor}`}
            style={{ width: `${percentage}%` }}
          />
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-500">Score</span>
          <ConfidenceBadge confidence={score} label={label as "HIGH" | "MEDIUM" | "LOW"} showPercentage={false} size="md" />
        </div>
      </div>
    </div>
  );
}

export function AuditResultsPage({ result, error, onReset }: AuditResultsPageProps) {
  if (error) {
    return (
      <main className="mx-auto min-h-screen w-full max-w-3xl animate-fade-up-long px-5 py-8 sm:px-8">
        <ErrorState error={error} onReset={onReset} />
      </main>
    );
  }

  if (!result) {
    return (
      <main className="mx-auto min-h-screen w-full max-w-3xl animate-fade-up-long px-5 py-8 sm:px-8">
        <EmptyState type="NO_FILE" onReset={onReset} />
      </main>
    );
  }

  const mode = result.mode ?? "AUDIT";
  const isAuditMode = mode === "AUDIT";
  const displayText = result.redacted_text || result.advisory_text || result.legacy_text || "";

  if (isAuditMode && result.issue_count === 0 && !result.structured_parse_failed) {
    return (
      <main className="mx-auto min-h-screen w-full max-w-3xl animate-fade-up-long px-5 py-8 sm:px-8">
        <EmptyState type="NO_ISSUES" onReset={onReset} />
      </main>
    );
  }

  const groups = groupIssuesByCategory(result.issues);
  const ModeIcon = mode === "REDACTION" ? Eraser : mode === "ADVISORY" ? MessageSquareText : FileSearch;
  const modeLabel = mode === "REDACTION" ? "Redaction Results" : mode === "ADVISORY" ? "Advisory Response" : "Audit Results";
  const heading = mode === "AUDIT"
    ? `${result.issue_count} issue${result.issue_count !== 1 ? "s" : ""} found`
    : mode === "REDACTION"
      ? "Redacted output"
      : "Advisory guidance";

  const confidenceLabel = result.confidence_label;
  const confidenceScore = result.confidence_score;
  const isLowConfidence = confidenceLabel === "LOW";
  const isMediumConfidence = confidenceLabel === "MEDIUM";

  return (
    <main className="mx-auto min-h-screen w-full max-w-6xl animate-fade-up-long bg-gradient-to-b from-slate-900 via-slate-950 to-black px-5 py-8 sm:px-8">
      <header className="flex flex-col gap-4 border-b border-slate-800 pb-6 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
            <ModeIcon className="h-4 w-4" aria-hidden="true" />
            {modeLabel}
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-100">{heading}</h1>
          {isAuditMode ? (
            <>
              <SeveritySummary issues={result.issues} />
              <CategorySummary issues={result.issues} />
            </>
          ) : null}
          {confidenceLabel && confidenceScore !== undefined && (
            <ConfidenceSection label={confidenceLabel} score={confidenceScore} />
          )}
        </div>
        <div className="flex shrink-0 flex-col items-end gap-3 sm:flex-row">
          <ExportButtons result={result} />
          <button
            type="button"
            onClick={onReset}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-slate-700 bg-slate-800 px-4 text-sm font-semibold text-slate-300 transition-colors hover:bg-slate-700"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            New request
          </button>
        </div>
      </header>

      {isLowConfidence && (
        <section className="mt-4 rounded-xl border border-red-500/20 bg-red-500/5 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-red-400" />
            <div>
              <h3 className="text-sm font-semibold text-red-300">Low Confidence Response</h3>
              <p className="mt-1 text-sm text-red-400/80">
                This response may be incomplete or unreliable. Review the results carefully and consider re-running the analysis.
              </p>
            </div>
          </div>
        </section>
      )}

      {isMediumConfidence && !isLowConfidence && (
        <section className="mt-4 rounded-xl border border-amber-500/20 bg-amber-500/5 p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-amber-400" />
            <div>
              <h3 className="text-sm font-semibold text-amber-300">Medium Confidence</h3>
              <p className="mt-1 text-sm text-amber-400/80">
                Some aspects of this response may be incomplete. Review results for accuracy.
              </p>
            </div>
          </div>
        </section>
      )}

      {!isAuditMode ? (
        <section className="mt-6 rounded-xl border border-slate-800 bg-slate-900/60 p-5">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-300">
            <ModeIcon className="h-4 w-4" aria-hidden="true" />
            {mode === "REDACTION" ? "Redacted Text" : "Advisory Text"}
          </div>
          <pre className="mt-4 max-h-[34rem] overflow-auto whitespace-pre-wrap rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm leading-6 text-slate-300">
            {displayText || "The backend returned an empty response."}
          </pre>
        </section>
      ) : result.structured_parse_failed ? (
        <section className="mt-6 rounded-xl border border-amber-500/20 bg-amber-500/5 p-5">
          <div className="flex items-center gap-2 text-sm font-semibold text-amber-400">
            <AlertCircle className="h-4 w-4" aria-hidden="true" />
            Parsing Warning
          </div>
          <p className="mt-2 text-sm text-amber-400/80">
            The contract was processed but structured analysis failed. Displaying raw output below.
          </p>
          <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap rounded-lg border border-amber-500/20 bg-slate-950 p-4 text-sm leading-6 text-amber-300">
            {result.legacy_text || "The backend returned text but no structured issues."}
          </pre>
        </section>
      ) : (
        <div className="mt-6 space-y-6">
          {groups.length > 1 ? (
            groups.map((group) => (
              <section key={group.category}>
                <div className="mb-3 flex items-center gap-2">
                  <h2 className="text-lg font-semibold text-slate-200">{group.category}</h2>
                  <span className="rounded-full bg-slate-800 px-2 py-0.5 text-xs font-medium text-slate-400">
                    {group.count}
                  </span>
                </div>
                <div className="grid gap-3">
                  {group.issues.map((issue, idx) => (
                    <div
                      key={`${issue.location}-${issue.category}-${idx}`}
                      className="animate-fade-up"
                      style={{ animationDelay: `${idx * 80}ms` }}
                    >
                      <CollapsibleIssueCard
                        issue={issue}
                        index={idx}
                      />
                    </div>
                  ))}
                </div>
              </section>
            ))
          ) : (
            <section className="grid gap-3">
              {result.issues.map((issue, index) => (
                <div
                  key={`${issue.location}-${issue.category}-${index}`}
                  className="animate-fade-up"
                  style={{ animationDelay: `${index * 80}ms` }}
                >
                  <CollapsibleIssueCard
                    issue={issue}
                    index={index}
                  />
                </div>
              ))}
            </section>
          )}
        </div>
      )}

      <footer className="mt-8 border-t border-slate-800 py-4 text-center text-sm text-slate-500">
        <div className="flex items-center justify-center gap-2">
          <ShieldCheck className="h-4 w-4 text-emerald-500" />
          <span>Powered by {result.model}</span>
          {result.metadata?.inference_duration_ms && (
            <span className="text-slate-600">· {(result.metadata.inference_duration_ms / 1000).toFixed(1)}s</span>
          )}
        </div>
      </footer>
    </main>
  );
}
