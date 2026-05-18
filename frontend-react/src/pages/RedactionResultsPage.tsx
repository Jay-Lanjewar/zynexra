import { ArrowLeft, Download, FileJson, FileText, ShieldCheck } from "lucide-react";
import type { ReactNode } from "react";
import type { AuditResponse, RedactionEntity } from "../types";

type RedactionResultsPageProps = {
  result: AuditResponse;
  onReset: () => void;
};

const entityStyles: Record<string, string> = {
  PERSON: "bg-sky-100 text-sky-800 ring-sky-200",
  EMAIL: "bg-rose-100 text-rose-800 ring-rose-200",
  PHONE: "bg-amber-100 text-amber-800 ring-amber-200",
  ADDRESS: "bg-emerald-100 text-emerald-800 ring-emerald-200",
  COMPANY: "bg-violet-100 text-violet-800 ring-violet-200",
  MONEY: "bg-lime-100 text-lime-800 ring-lime-200",
  DATE: "bg-cyan-100 text-cyan-800 ring-cyan-200",
  ID_NUMBER: "bg-fuchsia-100 text-fuchsia-800 ring-fuchsia-200",
};

function downloadBlob(content: string, fileName: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function HighlightedText({ text, entities }: { text: string; entities: RedactionEntity[] }) {
  const ordered = [...entities].sort((a, b) => a.start - b.start);
  const parts: ReactNode[] = [];
  let cursor = 0;

  ordered.forEach((entity, index) => {
    if (entity.start > cursor) {
      parts.push(<span key={`text-${index}`}>{text.slice(cursor, entity.start)}</span>);
    }

    parts.push(
      <mark
        key={`${entity.entity_type}-${entity.start}-${entity.end}`}
        className={`rounded px-1 py-0.5 ring-1 ${entityStyles[entity.entity_type] ?? "bg-slate-100 text-slate-800 ring-slate-200"}`}
        title={`${entity.entity_type} - ${(entity.confidence * 100).toFixed(0)}%`}
      >
        {text.slice(entity.start, entity.end)}
      </mark>
    );
    cursor = entity.end;
  });

  if (cursor < text.length) {
    parts.push(<span key="text-tail">{text.slice(cursor)}</span>);
  }

  return <>{parts}</>;
}

export function RedactionResultsPage({ result, onReset }: RedactionResultsPageProps) {
  const originalText = result.original_text || "";
  const redactedText = result.redacted_text || result.legacy_text || "";
  const entities = result.redaction_entities ?? [];

  return (
    <main className="mx-auto min-h-screen w-full max-w-6xl px-5 py-8 sm:px-8">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">Redaction Results</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-950">
            {entities.length} sensitive entit{entities.length === 1 ? "y" : "ies"} detected
          </h1>
          <div className="mt-3 flex flex-wrap gap-2">
            {Object.entries(
              entities.reduce<Record<string, number>>((counts, entity) => {
                counts[entity.entity_type] = (counts[entity.entity_type] ?? 0) + 1;
                return counts;
              }, {})
            ).map(([entityType, count]) => (
              <span
                key={entityType}
                className={`rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${entityStyles[entityType] ?? "bg-slate-100 text-slate-700 ring-slate-200"}`}
              >
                {entityType}: {count}
              </span>
            ))}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => downloadBlob(redactedText, "redacted-text.txt", "text/plain")}
            className="inline-flex h-10 items-center gap-2 rounded-md border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            <FileText className="h-4 w-4" />
            Text
          </button>
          <button
            type="button"
            onClick={() => downloadBlob(JSON.stringify(result, null, 2), "redaction-metadata.json", "application/json")}
            className="inline-flex h-10 items-center gap-2 rounded-md border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            <FileJson className="h-4 w-4" />
            JSON
          </button>
          <button
            type="button"
            onClick={() => downloadBlob(redactedText, "redacted-output.txt", "text/plain")}
            className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-slate-300 bg-white text-slate-700 hover:bg-slate-50"
            title="Download redacted text"
          >
            <Download className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={onReset}
            className="inline-flex h-10 items-center gap-2 rounded-md border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50"
          >
            <ArrowLeft className="h-4 w-4" />
            New request
          </button>
        </div>
      </header>

      <section className="grid gap-5 py-6 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900">Original Text</h2>
          <pre className="mt-3 max-h-[28rem] overflow-auto whitespace-pre-wrap rounded-md border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-800">
            {originalText || "No original text returned."}
          </pre>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-900">Highlighted Sensitive Entities</h2>
          <div className="mt-3 max-h-[28rem] overflow-auto whitespace-pre-wrap rounded-md border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-800">
            <HighlightedText text={originalText} entities={entities} />
          </div>
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm lg:col-span-2">
          <h2 className="text-sm font-semibold text-slate-900">Redacted Preview</h2>
          <pre className="mt-3 max-h-[24rem] overflow-auto whitespace-pre-wrap rounded-md border border-slate-200 bg-slate-950 p-4 text-sm leading-6 text-white">
            {redactedText || "No redacted text returned."}
          </pre>
        </div>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-sm font-semibold text-slate-900">Entity Metadata</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[720px] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                <th className="py-2 pr-3">Type</th>
                <th className="py-2 pr-3">Original</th>
                <th className="py-2 pr-3">Replacement</th>
                <th className="py-2 pr-3">Confidence</th>
                <th className="py-2 pr-3">Range</th>
              </tr>
            </thead>
            <tbody>
              {entities.map((entity) => (
                <tr key={`${entity.entity_type}-${entity.start}-${entity.end}`} className="border-b border-slate-100">
                  <td className="py-2 pr-3 font-semibold text-slate-800">{entity.entity_type}</td>
                  <td className="max-w-xs py-2 pr-3 font-mono text-xs text-slate-700">{entity.original_text}</td>
                  <td className="py-2 pr-3 font-mono text-xs text-slate-700">{entity.replacement}</td>
                  <td className="py-2 pr-3 text-slate-700">{(entity.confidence * 100).toFixed(0)}%</td>
                  <td className="py-2 pr-3 text-slate-700">
                    {entity.start}-{entity.end}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <footer className="mt-8 border-t border-slate-200 py-4 text-center text-sm text-slate-500">
        <div className="flex items-center justify-center gap-2">
          <ShieldCheck className="h-4 w-4 text-emerald-600" />
          <span>Powered by {result.model}</span>
        </div>
      </footer>
    </main>
  );
}
