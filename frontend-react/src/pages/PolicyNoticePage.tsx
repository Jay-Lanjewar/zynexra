import { ArrowLeft, FileText, ShieldOff, Info, Scale, FileSearch } from "lucide-react";
import type { AuditResponse } from "../types";
import type { ApiError } from "../api";

type PolicyNoticePageProps = {
  result: AuditResponse | null;
  error: ApiError | null;
  onReset: () => void;
};

const policyTypeIcons: Record<string, React.ElementType> = {
  "Administrative Rules": FileText,
  "Procedures": FileText,
  "Eligibility Criteria": Scale,
  "Guidelines": FileText,
  "Rebate Policy": Scale,
  "Hostel Regulations": FileText,
  "Academic Policies": Scale,
  "Institutional Notice": FileText,
};

export function PolicyNoticePage({ result, error, onReset }: PolicyNoticePageProps) {
  if (error) {
    return (
      <main className="mx-auto min-h-screen w-full max-w-3xl animate-fade-up-long bg-gradient-to-b from-slate-900 via-slate-950 to-black px-5 py-8 sm:px-8">
        <div className="flex flex-col items-center justify-center rounded-xl border border-red-500/20 bg-red-500/5 p-8 text-center shadow-lg shadow-black/10">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-red-500/10 text-red-400">
            <ShieldOff className="h-8 w-8" />
          </div>
          <h3 className="mt-4 text-lg font-semibold text-red-300">Error Processing Document</h3>
          <p className="mt-2 max-w-md text-sm leading-relaxed text-red-400/70">{error.message}</p>
          <button
            type="button"
            onClick={onReset}
            className="mt-6 rounded-lg bg-indigo-500 px-5 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-400"
          >
            Try Again
          </button>
        </div>
      </main>
    );
  }

  if (!result || result.response_type !== "policy") {
    return (
      <main className="mx-auto min-h-screen w-full max-w-3xl animate-fade-up-long bg-gradient-to-b from-slate-900 via-slate-950 to-black px-5 py-8 sm:px-8">
        <div className="flex flex-col items-center justify-center rounded-xl border border-slate-700/50 bg-slate-900/50 p-8 text-center shadow-lg shadow-black/10">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-slate-800 text-slate-400">
            <FileSearch className="h-8 w-8" />
          </div>
          <h3 className="mt-4 text-lg font-semibold text-slate-300">No Policy Information</h3>
          <p className="mt-2 max-w-md text-sm leading-relaxed text-slate-500">No policy detection result is available.</p>
          <button
            type="button"
            onClick={onReset}
            className="mt-6 rounded-lg bg-indigo-500 px-5 py-2 text-sm font-semibold text-white transition-colors hover:bg-indigo-400"
          >
            Back to Upload
          </button>
        </div>
      </main>
    );
  }

  const policyType = result.policy_type || "Document";
  const Icon = policyTypeIcons[policyType] || FileText;

  return (
    <main className="mx-auto min-h-screen w-full max-w-4xl animate-fade-up-long bg-gradient-to-b from-slate-900 via-slate-950 to-black px-5 py-8 sm:px-8">
      <header className="flex flex-col gap-4 border-b border-slate-800 pb-6 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-amber-400">
            <ShieldOff className="h-4 w-4" />
            Policy Document Detected
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-100">Not a Contractual Agreement</h1>
        </div>
        <button
          type="button"
          onClick={onReset}
          className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-slate-700 bg-slate-800 px-4 text-sm font-semibold text-slate-300 transition-colors hover:bg-slate-700"
        >
          <ArrowLeft className="h-4 w-4" />
          New request
        </button>
      </header>

      <div className="mt-8 space-y-6">
        <section className="rounded-xl border border-amber-500/20 bg-gradient-to-br from-amber-500/5 to-amber-500/10 p-6 shadow-lg shadow-black/20">
          <div className="flex items-start gap-4">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-amber-500/10">
              <Icon className="h-7 w-7 text-amber-400" />
            </div>
            <div className="min-w-0">
              <h2 className="text-xl font-semibold text-amber-300">{policyType}</h2>
              <p className="mt-2 text-sm leading-relaxed text-amber-200/80">
                {result.policy_explanation || "This document contains policy or procedural rules rather than a contractual agreement."}
              </p>
            </div>
          </div>
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-6 shadow-lg shadow-black/10">
          <div className="flex items-start gap-3">
            <Info className="mt-0.5 h-5 w-5 shrink-0 text-indigo-400" />
            <div>
              <h3 className="text-sm font-semibold text-slate-200">What this means</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">
                The legal-risk audit pipeline is designed for contractual agreements that establish
                binding rights and obligations between parties. Policy and procedure documents —
                while important — serve a different purpose: they provide rules, guidelines,
                eligibility criteria, or administrative information rather than mutual promises
                that create enforceable legal duties.
              </p>
            </div>
          </div>
        </section>

        {result.metadata?.policy_keywords && result.metadata.policy_keywords.length > 0 && (
          <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
            <h3 className="text-sm font-semibold text-slate-300">Detected policy keywords</h3>
            <div className="mt-3 flex flex-wrap gap-2">
              {result.metadata.policy_keywords.map((keyword) => (
                <span
                  key={keyword}
                  className="rounded-md bg-amber-500/10 px-2.5 py-1 text-xs font-medium text-amber-400"
                >
                  {keyword}
                </span>
              ))}
            </div>
          </section>
        )}

        {result.policy_confidence !== undefined && (
          <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
            <h3 className="text-sm font-semibold text-slate-300">Detection Confidence</h3>
            <div className="mt-3 flex items-center gap-3">
              <div className="flex-1">
                <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
                  <div
                    className="h-full rounded-full bg-amber-500 transition-all duration-1000 ease-out"
                    style={{ width: `${Math.min(result.policy_confidence * 100, 100)}%` }}
                  />
                </div>
              </div>
              <span className="text-sm font-medium text-slate-400">
                {Math.round(result.policy_confidence * 100)}%
              </span>
            </div>
          </section>
        )}

        <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-6 text-center shadow-lg shadow-black/10">
          <div className="flex items-center justify-center gap-2 text-sm text-slate-500">
            <Scale className="h-4 w-4" />
            <span>This classification is based on document content analysis and is provided for informational purposes.</span>
          </div>
        </section>
      </div>

      <footer className="mt-8 border-t border-slate-800 py-4 text-center text-sm text-slate-500">
        <div className="flex items-center justify-center gap-2">
          <ShieldOff className="h-4 w-4 text-amber-500" />
          <span>Policy document — not processed through legal-risk audit pipeline</span>
        </div>
      </footer>
    </main>
  );
}
