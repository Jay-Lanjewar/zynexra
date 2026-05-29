import { ArrowLeft, FileSearch, ShieldOff, Info, BookOpen, HelpCircle, FileText, MessageSquare } from "lucide-react";
import type { AuditResponse } from "../types";
import type { ApiError } from "../api";

type NonLegalDocumentPageProps = {
  result: AuditResponse | null;
  error: ApiError | null;
  onReset: () => void;
};

const contentTypeIcons: Record<string, React.ElementType> = {
  "Educational Material": BookOpen,
  "Questions or Assignments": HelpCircle,
  "General Text or Notes": FileText,
  "Non-Contract Communication": MessageSquare,
};

export function NonLegalDocumentPage({ result, error, onReset }: NonLegalDocumentPageProps) {
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

  if (!result || result.response_type !== "non_legal") {
    return (
      <main className="mx-auto min-h-screen w-full max-w-3xl animate-fade-up-long bg-gradient-to-b from-slate-900 via-slate-950 to-black px-5 py-8 sm:px-8">
        <div className="flex flex-col items-center justify-center rounded-xl border border-slate-700/50 bg-slate-900/50 p-8 text-center shadow-lg shadow-black/10">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-slate-800 text-slate-400">
            <FileSearch className="h-8 w-8" />
          </div>
          <h3 className="mt-4 text-lg font-semibold text-slate-300">No Document Information</h3>
          <p className="mt-2 max-w-md text-sm leading-relaxed text-slate-500">No document classification result is available.</p>
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

  const contentType = result.content_type || "Uncategorized Non-Legal";
  const Icon = contentTypeIcons[contentType] || FileText;

  return (
    <main className="mx-auto min-h-screen w-full max-w-4xl animate-fade-up-long bg-gradient-to-b from-slate-900 via-slate-950 to-black px-5 py-8 sm:px-8">
      <header className="flex flex-col gap-4 border-b border-slate-800 pb-6 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-500">
            <ShieldOff className="h-4 w-4" />
            Non-Contract Document
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
        <section className="rounded-xl border border-slate-700/50 bg-gradient-to-br from-slate-800/30 to-slate-800/10 p-6 shadow-lg shadow-black/20">
          <div className="flex items-start gap-4">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-xl bg-slate-700/30">
              <Icon className="h-7 w-7 text-slate-300" />
            </div>
            <div className="min-w-0">
              <h2 className="text-xl font-semibold text-slate-200">{contentType}</h2>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">
                {result.content_explanation || "This document does not appear to be a legal contract, agreement, or policy document."}
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
                The legal-risk audit pipeline is designed to analyze contractual agreements that establish
                binding rights and obligations between parties. The uploaded document lacks the structural
                and linguistic characteristics of a contract — such as parties, consideration, terms,
                signatures, or binding legal language.
              </p>
              <p className="mt-3 text-sm leading-relaxed text-slate-500">
                Supported document types include contracts, agreements, non-disclosure agreements,
                service agreements, licensing terms, and similar legally-binding instruments.
              </p>
            </div>
          </div>
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
          <h3 className="text-sm font-semibold text-slate-300">Domain Analysis</h3>
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            <div className="rounded-lg border border-slate-800 bg-slate-900/60 px-4 py-3">
              <span className="text-xs text-slate-500">Domain Confidence</span>
              <p className="mt-1 text-lg font-semibold text-slate-200">{Math.round((result.domain_confidence ?? 0) * 100)}%</p>
              <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
                <div
                  className="h-full rounded-full bg-slate-600"
                  style={{ width: `${Math.min((result.domain_confidence ?? 0) * 100, 100)}%` }}
                />
              </div>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-900/60 px-4 py-3">
              <span className="text-xs text-slate-500">Legal Keyword Ratio</span>
              <p className="mt-1 text-lg font-semibold text-slate-200">
                {((result.legal_keyword_ratio ?? 0) * 100).toFixed(1)}%
              </p>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-900/60 px-4 py-3">
              <span className="text-xs text-slate-500">Structure Score</span>
              <p className="mt-1 text-lg font-semibold text-slate-200">
                {((result.structure_score ?? 0) * 100).toFixed(1)}%
              </p>
            </div>
          </div>
        </section>

        <section className="rounded-xl border border-slate-800 bg-slate-900/40 p-6 text-center shadow-lg shadow-black/10">
          <div className="flex items-center justify-center gap-2 text-sm text-slate-500">
            <FileSearch className="h-4 w-4" />
            <span>This classification is based on document content analysis and is provided for informational purposes.</span>
          </div>
        </section>
      </div>

      <footer className="mt-8 border-t border-slate-800 py-4 text-center text-sm text-slate-500">
        <div className="flex items-center justify-center gap-2">
          <ShieldOff className="h-4 w-4 text-slate-500" />
          <span>Non-contract document — not processed through legal-risk audit pipeline</span>
        </div>
      </footer>
    </main>
  );
}
