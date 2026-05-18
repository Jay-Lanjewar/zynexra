import { ArrowLeft, AlertCircle, CheckCircle2, Eraser, FileSearch, MessageSquareText, ShieldCheck } from "lucide-react";
import { CollapsibleIssueCard } from "../components/CollapsibleIssueCard";
import { ExportButtons } from "../components/ExportButtons";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import type { AuditResponse } from "../types";
import type { ApiError } from "../api";
import { groupIssuesByCategory, getSeverityCounts } from "../utils";

type AuditResultsPageProps = {
  result: AuditResponse | null;
  error: ApiError | null;
  onReset: () => void;
};

const severityConfig: Record<string, { label: string; bg: string; text: string; icon: React.ElementType }> = {
  CRITICAL: { label: "Critical", bg: "bg-red-100 text-red-700", text: "text-red-600", icon: AlertCircle },
  HIGH: { label: "High", bg: "bg-orange-100 text-orange-700", text: "text-orange-600", icon: AlertCircle },
  MEDIUM: { label: "Medium", bg: "bg-amber-100 text-amber-700", text: "text-amber-600", icon: AlertCircle },
  LOW: { label: "Low", bg: "bg-emerald-100 text-emerald-700", text: "text-emerald-600", icon: CheckCircle2 },
  UNRATED: { label: "Unrated", bg: "bg-slate-100 text-slate-700", text: "text-slate-600", icon: AlertCircle },
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
          className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600"
        >
          {group.category}: {group.count}
        </span>
      ))}
    </div>
  );
}

export function AuditResultsPage({ result, error, onReset }: AuditResultsPageProps) {
  if (error) {
    return (
      <main className="mx-auto min-h-screen w-full max-w-3xl px-5 py-8 sm:px-8">
        <ErrorState error={error} onReset={onReset} />
      </main>
    );
  }

  if (!result) {
    return (
      <main className="mx-auto min-h-screen w-full max-w-3xl px-5 py-8 sm:px-8">
        <EmptyState type="NO_FILE" onReset={onReset} />
      </main>
    );
  }

  const mode = result.mode ?? "AUDIT";
  const isAuditMode = mode === "AUDIT";
  const displayText = result.redacted_text || result.advisory_text || result.legacy_text || "";

  if (isAuditMode && result.issue_count === 0 && !result.structured_parse_failed) {
    return (
      <main className="mx-auto min-h-screen w-full max-w-3xl px-5 py-8 sm:px-8">
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

  return (
    <main className="mx-auto min-h-screen w-full max-w-6xl px-5 py-8 sm:px-8">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
            <ModeIcon className="h-4 w-4" aria-hidden="true" />
            {modeLabel}
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-950">{heading}</h1>
          {isAuditMode ? (
            <>
              <SeveritySummary issues={result.issues} />
              <CategorySummary issues={result.issues} />
            </>
          ) : null}
        </div>
        <div className="flex flex-col items-end gap-3 sm:flex-row">
          <ExportButtons result={result} />
          <button
            type="button"
            onClick={onReset}
            className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            New request
          </button>
        </div>
      </header>

      {!isAuditMode ? (
        <section className="mt-6 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
            <ModeIcon className="h-4 w-4" aria-hidden="true" />
            {mode === "REDACTION" ? "Redacted Text" : "Advisory Text"}
          </div>
          <pre className="mt-4 max-h-[34rem] overflow-auto whitespace-pre-wrap rounded-md border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-800">
            {displayText || "The backend returned an empty response."}
          </pre>
        </section>
      ) : result.structured_parse_failed ? (
        <section className="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-5">
          <div className="flex items-center gap-2 text-sm font-semibold text-amber-800">
            <AlertCircle className="h-4 w-4" aria-hidden="true" />
            Parsing Warning
          </div>
          <p className="mt-2 text-sm text-amber-700">
            The contract was processed but structured analysis failed. Displaying raw output below.
          </p>
          <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap rounded-md border border-amber-200 bg-white p-4 text-sm leading-6 text-amber-900">
            {result.legacy_text || "The backend returned text but no structured issues."}
          </pre>
        </section>
      ) : (
        <div className="mt-6 space-y-6">
          {groups.length > 1 ? (
            groups.map((group) => (
              <section key={group.category}>
                <div className="mb-3 flex items-center gap-2">
                  <h2 className="text-lg font-semibold text-slate-900">{group.category}</h2>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
                    {group.count}
                  </span>
                </div>
                <div className="grid gap-4">
                  {group.issues.map((issue, idx) => (
                    <CollapsibleIssueCard
                      key={`${issue.location}-${issue.category}-${idx}`}
                      issue={issue}
                      index={idx}
                    />
                  ))}
                </div>
              </section>
            ))
          ) : (
            <section className="grid gap-4">
              {result.issues.map((issue, index) => (
                <CollapsibleIssueCard
                  key={`${issue.location}-${issue.category}-${index}`}
                  issue={issue}
                  index={index}
                />
              ))}
            </section>
          )}
        </div>
      )}

      <footer className="mt-8 border-t border-slate-200 py-4 text-center text-sm text-slate-500">
        <div className="flex items-center justify-center gap-2">
          <ShieldCheck className="h-4 w-4 text-emerald-600" />
          <span>Powered by {result.model}</span>
        </div>
      </footer>
    </main>
  );
}
