import { ArrowLeft, AlertCircle, AlertTriangle, CheckCircle2, Eraser, FileSearch, MessageSquareText, ShieldCheck, ListChecks, ShieldAlert, FileWarning } from "lucide-react";
import { CollapsibleIssueCard } from "../components/CollapsibleIssueCard";
import { ExportButtons } from "../components/ExportButtons";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { ConfidenceBadge } from "../components/ConfidenceBadge";
import type { AnalysisMetadata, AuditResponse } from "../types";
import type { ApiError } from "../api";
import { groupIssuesByCategory, getSeverityCounts } from "../utils";

type AuditResultsPageProps = {
  result: AuditResponse | null;
  error: ApiError | null;
  onReset: () => void;
};

type RiskLevel = "SAFE" | "LOW_RISK" | "MODERATE_RISK" | "HIGH_RISK";

const riskLevelConfig: Record<RiskLevel, { label: string; bg: string; text: string; border: string; icon: React.ElementType }> = {
  SAFE: { label: "SAFE", bg: "bg-emerald-500/15", text: "text-emerald-400", border: "border-emerald-500/30", icon: ShieldCheck },
  LOW_RISK: { label: "LOW RISK", bg: "bg-emerald-500/15", text: "text-emerald-400", border: "border-emerald-500/30", icon: CheckCircle2 },
  MODERATE_RISK: { label: "MODERATE RISK", bg: "bg-amber-500/15", text: "text-amber-400", border: "border-amber-500/30", icon: AlertCircle },
  HIGH_RISK: { label: "HIGH RISK", bg: "bg-red-500/15", text: "text-red-400", border: "border-red-500/30", icon: ShieldAlert },
};

const severityConfig: Record<string, { label: string; bg: string; text: string; icon: React.ElementType }> = {
  CRITICAL: { label: "Critical", bg: "bg-red-500/10 text-red-400", text: "text-red-400", icon: AlertCircle },
  HIGH: { label: "High", bg: "bg-orange-500/10 text-orange-400", text: "text-orange-400", icon: AlertCircle },
  MEDIUM: { label: "Medium", bg: "bg-amber-500/10 text-amber-400", text: "text-amber-400", icon: AlertCircle },
  LOW: { label: "Low", bg: "bg-emerald-500/10 text-emerald-400", text: "text-emerald-400", icon: CheckCircle2 },
  UNRATED: { label: "Unrated", bg: "bg-slate-500/10 text-slate-400", text: "text-slate-400", icon: AlertCircle },
};

function classifyRiskLevel(issues: AuditResponse["issues"], confidenceScore?: number): RiskLevel {
  const counts = getSeverityCounts(issues);
  const hasContradictions = issues.some((i) => i.contradiction_detected);
  const confidence = confidenceScore ?? 0;

  if (counts.CRITICAL > 0 || counts.HIGH > 0) {
    if (hasContradictions) return "HIGH_RISK";
    if (confidence < 0.45) return "MODERATE_RISK";
    return "HIGH_RISK";
  }

  if (counts.MEDIUM > 0) {
    if (hasContradictions) return "HIGH_RISK";
    return "MODERATE_RISK";
  }

  if (counts.LOW > 0) {
    if (hasContradictions) return "MODERATE_RISK";
    return "LOW_RISK";
  }

  return "SAFE";
}

function generateOneLineSummary(issues: AuditResponse["issues"], riskLevel: RiskLevel): string {
  if (issues.length === 0) return "No compliance issues detected in this document.";

  const criticalHigh = issues.filter((i) => i.severity === "CRITICAL" || i.severity === "HIGH");
  const categories = [...new Set(issues.map((i) => i.category))];

  if (riskLevel === "HIGH_RISK" && criticalHigh.length > 0) {
    const topCat = criticalHigh[0].category;
    return `High-risk ${topCat.toLowerCase()} and other critical concerns detected.`;
  }

  if (riskLevel === "MODERATE_RISK") {
    const catStr = categories.slice(0, 2).join(" and ");
    return `${catStr} concerns found. Review recommended before signing.`;
  }

  if (riskLevel === "LOW_RISK") {
    return "Minor compliance observations. Document is generally sound.";
  }

  return "Document appears compliant. No significant issues found.";
}

function generateKeyFindings(issues: AuditResponse["issues"]): string[] {
  const findings: string[] = [];
  const usedTitles = new Set<string>();

  const contradictions = issues.filter((i) => i.contradiction_detected);
  for (const c of contradictions) {
    const finding = `Contradictory ${c.category.toLowerCase()} clauses found`;
    if (!usedTitles.has(finding)) {
      findings.push(finding);
      usedTitles.add(finding);
    }
  }

  const severe = issues.filter((i) => i.severity === "CRITICAL" || i.severity === "HIGH");
  for (const s of severe) {
    let finding = s.issue_title;
    if (finding && !finding.endsWith("detected") && !finding.endsWith("found")) {
      finding = `${finding} detected`;
    }
    if (finding && !usedTitles.has(finding)) {
      findings.push(finding);
      usedTitles.add(finding);
    }
  }

  const categories = [...new Set(issues.map((i) => i.category))];
  for (const cat of categories) {
    const exists = findings.some((f) => f.toLowerCase().includes(cat.toLowerCase()));
    if (!exists) {
      const catIssues = issues.filter((i) => i.category === cat);
      if (catIssues.length > 1) {
        findings.push(`Multiple ${cat.toLowerCase()} issues found`);
      } else {
        findings.push(`${cat} concern identified`);
      }
    }
  }

  return findings.slice(0, 5);
}

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

function SeveritySummaryBar({ issues }: { issues: AuditResponse["issues"] }) {
  const counts = getSeverityCounts(issues);
  const hasIssues = Object.values(counts).some((v) => v > 0);
  if (!hasIssues || issues.length === 0) return null;

  const items: { key: string; count: number; color: string }[] = [];
  if (counts.CRITICAL > 0) items.push({ key: "Critical", count: counts.CRITICAL, color: "bg-red-500" });
  if (counts.HIGH > 0) items.push({ key: "High", count: counts.HIGH, color: "bg-orange-500" });
  if (counts.MEDIUM > 0) items.push({ key: "Medium", count: counts.MEDIUM, color: "bg-amber-500" });
  if (counts.LOW > 0) items.push({ key: "Low", count: counts.LOW, color: "bg-emerald-500" });

  if (items.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-800 bg-slate-900/40 px-4 py-2.5 text-xs">
      <span className="font-semibold text-slate-500">Issues:</span>
      {items.map((item) => (
        <span key={item.key} className="flex items-center gap-1.5 font-medium text-slate-300">
          <span className={`h-2 w-2 rounded-full ${item.color}`} />
          {item.count} {item.key}
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
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-500">Confidence Score</span>
        <ConfidenceBadge confidence={score} label={label as "HIGH" | "MEDIUM" | "LOW"} showPercentage={false} size="sm" />
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
        <div
          className={`h-full rounded-full transition-all duration-1000 ease-out ${labelColor}`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <div className="flex items-center justify-between text-xs">
        <span className="text-slate-500">{percentage}%</span>
        <span className="text-slate-600">{label}</span>
      </div>
    </div>
  );
}

function RiskLevelBadge({ level }: { level: RiskLevel }) {
  const config = riskLevelConfig[level];
  const Icon = config.icon;

  return (
    <div className={`inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 ${config.border} ${config.bg}`}>
      <Icon className={`h-5 w-5 ${config.text}`} aria-hidden="true" />
      <span className={`text-sm font-bold tracking-wide ${config.text}`}>{config.label}</span>
    </div>
  );
}

function AuditSummary({ issues, riskLevel, confidenceLabel, confidenceScore, inferenceDurationMs, analysis }: {
  issues: AuditResponse["issues"];
  riskLevel: RiskLevel;
  confidenceLabel?: string;
  confidenceScore?: number;
  inferenceDurationMs?: number;
  analysis?: AnalysisMetadata;
}) {
  const oneLiner = generateOneLineSummary(issues, riskLevel);
  const duration = inferenceDurationMs ? (inferenceDurationMs / 1000).toFixed(1) : null;

  const totalInput = analysis ? analysis.kept_chars + analysis.dropped_chars : 0;
  const analyzedPct =
    analysis && totalInput > 0
      ? Math.max(0, Math.min(100, Math.round((analysis.kept_chars / totalInput) * 100)))
      : null;

  return (
    <section
      className="rounded-xl border border-slate-800 bg-gradient-to-br from-slate-900/90 to-slate-900/40 p-6 shadow-lg shadow-black/20"
      aria-label="Audit summary at a glance"
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-center gap-4">
          <RiskLevelBadge level={riskLevel} />
          <div>
            <span className="text-2xl font-bold text-slate-100">{issues.length}</span>
            <span className="ml-1.5 text-slate-400">issue{issues.length !== 1 ? "s" : ""} found</span>
          </div>
        </div>
      </div>

      <div className="mt-4">
        <SeveritySummary issues={issues} />
      </div>

      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        {confidenceLabel && confidenceScore !== undefined && (
          <div className="rounded-lg border border-slate-800 bg-slate-900/60 px-4 py-3">
            <ConfidenceSection label={confidenceLabel} score={confidenceScore} />
          </div>
        )}

        <div className="rounded-lg border border-slate-800 bg-slate-900/60 px-4 py-3">
          <div className="flex flex-col gap-2">
            <span className="text-xs text-slate-500">Processing</span>
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <ShieldCheck className="h-4 w-4 text-emerald-500" aria-hidden="true" />
              <span>Processed locally</span>
            </div>
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-500">
              <span>No cloud upload used</span>
              {duration && (
                <>
                  <span className="text-slate-600">·</span>
                  <span className="font-medium text-slate-400">Analyzed in {duration}s</span>
                </>
              )}
              {analyzedPct !== null && (
                <>
                  <span className="text-slate-600">·</span>
                  <span className={`font-medium ${analysis?.was_truncated ? "text-amber-400" : "text-slate-400"}`}>
                    {analyzedPct}% of document analysed
                  </span>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="mt-4 border-t border-slate-800 pt-4">
        <p className="text-sm leading-relaxed text-slate-300">
          <span className="font-semibold text-slate-200">Summary: </span>
          {oneLiner}
        </p>
      </div>
    </section>
  );
}

function formatNumber(n: number): string {
  return n.toLocaleString("en-US");
}

function TruncationBanner({ analysis }: { analysis: AnalysisMetadata | undefined }) {
  if (!analysis) return null;

  const totalInput = analysis.kept_chars + analysis.dropped_chars;
  const analyzedPct =
    totalInput > 0
      ? Math.max(0, Math.min(100, Math.round((analysis.kept_chars / totalInput) * 100)))
      : 100;

  if (analysis.was_truncated) {
    return (
      <section
        role="alert"
        aria-label="Document was truncated before analysis"
        className="mt-4 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4"
      >
        <div className="flex items-start gap-3">
          <FileWarning className="mt-0.5 h-5 w-5 shrink-0 text-amber-400" aria-hidden="true" />
          <div className="min-w-0 flex-1">
            <h3 className="text-sm font-semibold text-amber-300">
              Only part of this document was analysed
            </h3>
            <p className="mt-1 text-sm leading-6 text-amber-400/90">
              The document exceeded the model&apos;s context window. The audit ran on{" "}
              <span className="font-semibold text-amber-300">{analyzedPct}%</span> of the
              source ({formatNumber(analysis.kept_chars)} of{" "}
              {formatNumber(totalInput)} characters kept;{" "}
              {formatNumber(analysis.dropped_chars)} characters omitted).
              {analysis.pages_seen !== null && analysis.pages_seen !== undefined && (
                <>
                  {" "}Pages seen: <span className="font-semibold text-amber-300">{analysis.pages_seen}</span>.
                </>
              )}
            </p>
            <p className="mt-1 text-xs text-amber-400/70">
              Findings may not reflect clauses in the omitted portion. Consider re-uploading a
              shorter excerpt or splitting the document.
            </p>
          </div>
        </div>
      </section>
    );
  }

  if (totalInput > 0 && analysis.context_utilization_pct >= 85) {
    return (
      <section
        role="status"
        aria-label="Document nearly filled the model context"
        className="mt-4 rounded-xl border border-slate-700 bg-slate-900/60 p-4"
      >
        <div className="flex items-start gap-3">
          <FileWarning className="mt-0.5 h-5 w-5 shrink-0 text-slate-400" aria-hidden="true" />
          <div className="min-w-0 flex-1 text-sm text-slate-300">
            <span className="font-semibold">Document used {analysis.context_utilization_pct.toFixed(1)}%</span> of the model
            context window. No content was dropped on this run, but smaller documents are
            analysed with more headroom.
            {analysis.pages_seen !== null && analysis.pages_seen !== undefined && (
              <> Pages seen: <span className="font-semibold text-slate-200">{analysis.pages_seen}</span>.</>
            )}
          </div>
        </div>
      </section>
    );
  }

  return null;
}

function KeyFindingsPanel({ issues }: { issues: AuditResponse["issues"] }) {
  const findings = generateKeyFindings(issues);

  if (findings.length === 0) return null;

  return (
    <section
      className="animate-fade-up rounded-xl border border-slate-800 bg-slate-900/40 px-5 py-4"
      style={{ animationDelay: "300ms" }}
      aria-label="Key findings"
    >
      <div className="flex items-center gap-2 text-sm font-semibold text-slate-300">
        <ListChecks className="h-4 w-4 text-indigo-400" aria-hidden="true" />
        Key Findings
      </div>
      <ul className="mt-3 space-y-1.5">
        {findings.map((finding, idx) => (
          <li key={idx} className="flex items-start gap-2 text-sm text-slate-400">
            <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-500/60" aria-hidden="true" />
            <span>{finding}</span>
          </li>
        ))}
      </ul>
    </section>
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
  const riskLevel = isAuditMode ? classifyRiskLevel(result.issues, confidenceScore) : null;

  return (
    <main className="mx-auto min-h-screen w-full max-w-6xl animate-fade-up-long bg-gradient-to-b from-slate-900 via-slate-950 to-black px-5 py-8 sm:px-8">
      <header className="flex flex-col gap-4 border-b border-slate-800 pb-6 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
            <ModeIcon className="h-4 w-4" aria-hidden="true" />
            {modeLabel}
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-100">{heading}</h1>
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

      {isAuditMode && !result.structured_parse_failed && (
        <div className="mt-6 space-y-4">
          <TruncationBanner analysis={result.metadata?.analysis_metadata} />
          <AuditSummary
            issues={result.issues}
            riskLevel={riskLevel ?? "SAFE"}
            confidenceLabel={confidenceLabel}
            confidenceScore={confidenceScore}
            inferenceDurationMs={result.metadata?.inference_duration_ms}
            analysis={result.metadata?.analysis_metadata}
          />
          <KeyFindingsPanel issues={result.issues} />
        </div>
      )}

      {!isAuditMode && confidenceLabel && confidenceScore !== undefined && (
        <div className="mt-6">
          <div className="flex items-center gap-4 rounded-xl border border-slate-800 bg-slate-900/60 px-5 py-4">
            <div className="flex flex-col">
              <span className="text-xs text-slate-500">Confidence</span>
              <span className="text-2xl font-bold text-slate-100">{Math.round(confidenceScore * 100)}%</span>
            </div>
            <div className="flex flex-1 flex-col gap-1.5">
              <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
                <div
                  className={`h-full rounded-full transition-all duration-1000 ease-out ${
                    confidenceLabel === "HIGH" ? "bg-emerald-500" : confidenceLabel === "MEDIUM" ? "bg-amber-500" : "bg-red-500"
                  }`}
                  style={{ width: `${Math.round(confidenceScore * 100)}%` }}
                />
              </div>
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-500">Score</span>
                <ConfidenceBadge confidence={confidenceScore} label={confidenceLabel as "HIGH" | "MEDIUM" | "LOW"} showPercentage={false} size="md" />
              </div>
            </div>
          </div>
        </div>
      )}

      {isLowConfidence && (
        <section className="mt-4 rounded-xl border border-red-500/20 bg-red-500/5 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-red-400" />
            <div>
              <h3 className="text-sm font-semibold text-red-300">Low Confidence Response</h3>
              <p className="mt-1 text-sm text-red-400/80">
                Some sections may require manual legal review due to limited structural clarity. Consider re-running the analysis.
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
                Some clauses may need further review. The analysis is partially structured — cross-check important sections.
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
        <div className="mt-6">
          <SeveritySummaryBar issues={result.issues} />
          <div className="mt-4 space-y-6">
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
                      style={{ animationDelay: `${600 + idx * 80}ms` }}
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
                  style={{ animationDelay: `${600 + index * 80}ms` }}
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
