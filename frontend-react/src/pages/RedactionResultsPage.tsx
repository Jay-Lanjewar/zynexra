import { ArrowLeft, Download, FileJson, FileText, ShieldCheck } from "lucide-react";
import { useState, useMemo } from "react";
import type { AuditResponse, RedactionEntity } from "../types";
import { useRedactionState } from "../redactionHooks";
import { computeEntityStats, sortEntityTypes } from "../redactionUtils";
import { ConfidenceBadge } from "../components/ConfidenceBadge";
import { EntitySidebar } from "../components/EntitySidebar";
import { OriginalTextPanel } from "../components/OriginalTextPanel";
import { RedactedPreviewPanel } from "../components/RedactedPreviewPanel";

type RedactionResultsPageProps = {
  result: AuditResponse;
  onReset: () => void;
};

const entityStyles: Record<string, string> = {
  PERSON: "bg-sky-500/10 text-sky-300 ring-sky-500/30",
  EMAIL: "bg-rose-500/10 text-rose-300 ring-rose-500/30",
  PHONE: "bg-amber-500/10 text-amber-300 ring-amber-500/30",
  ADDRESS: "bg-emerald-500/10 text-emerald-300 ring-emerald-500/30",
  COMPANY: "bg-violet-500/10 text-violet-300 ring-violet-500/30",
  LOCATION: "bg-teal-500/10 text-teal-300 ring-teal-500/30",
  MONEY: "bg-lime-500/10 text-lime-300 ring-lime-500/30",
  DATE: "bg-cyan-500/10 text-cyan-300 ring-cyan-500/30",
  ID_NUMBER: "bg-fuchsia-500/10 text-fuchsia-300 ring-fuchsia-500/30",
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

export function RedactionResultsPage({ result, onReset }: RedactionResultsPageProps) {
  const originalText = result.original_text || "";
  const redactedText = result.redacted_text || result.legacy_text || "";
  const entities = result.redaction_entities ?? [];

  const { activeRedactions, entityCounts, toggleEntity, toggleEntityType, toggleAllRedactions, isEntityActive, getActiveCount, getActiveCountByType } = useRedactionState(entities);

  const [hoveredEntityIndex, setHoveredEntityIndex] = useState<number | null>(null);

  const stats = useMemo(() => computeEntityStats(entities, activeRedactions), [entities, activeRedactions]);

  const entityTypes = useMemo(() => sortEntityTypes(Array.from(entityCounts.keys())), [entityCounts]);

  return (
    <main className="mx-auto min-h-screen w-full max-w-7xl px-5 py-8 sm:px-8">
      <header className="flex flex-col gap-4 border-b border-slate-800 pb-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">Redaction Results</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-100">
            {entities.length} sensitive entit{entities.length === 1 ? "y" : "ies"} detected
          </h1>
          <div className="mt-3 flex flex-wrap gap-2">
            {entityTypes.map((entityType) => {
              const count = entityCounts.get(entityType) ?? 0;
              return (
                <span
                  key={entityType}
                  className={`rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${entityStyles[entityType] ?? "bg-slate-700/50 text-slate-400 ring-slate-700"}`}
                >
                  {entityType}: {count}
                </span>
              );
            })}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => downloadBlob(redactedText, "redacted-text.txt", "text/plain")}
            className="inline-flex h-10 items-center gap-2 rounded-md border border-slate-700 bg-slate-800 px-3 text-sm font-semibold text-slate-300 hover:bg-slate-700"
          >
            <FileText className="h-4 w-4" />
            Text
          </button>
          <button
            type="button"
            onClick={() => downloadBlob(JSON.stringify(result, null, 2), "redaction-metadata.json", "application/json")}
            className="inline-flex h-10 items-center gap-2 rounded-md border border-slate-700 bg-slate-800 px-3 text-sm font-semibold text-slate-300 hover:bg-slate-700"
          >
            <FileJson className="h-4 w-4" />
            JSON
          </button>
          <button
            type="button"
            onClick={() => downloadBlob(redactedText, "redacted-output.txt", "text/plain")}
            className="inline-flex h-10 w-10 items-center justify-center rounded-md border border-slate-700 bg-slate-800 text-slate-300 hover:bg-slate-700"
            title="Download redacted text"
          >
            <Download className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={onReset}
            className="inline-flex h-10 items-center gap-2 rounded-md border border-slate-700 bg-slate-800 px-4 text-sm font-semibold text-slate-300 hover:bg-slate-700"
          >
            <ArrowLeft className="h-4 w-4" />
            New request
          </button>
        </div>
      </header>

      <section className="grid gap-5 py-6 grid-cols-1 lg:grid-cols-4">
        <div className="lg:col-span-1">
          <EntitySidebar
            entities={entities}
            entityCounts={entityCounts}
            activeCountByType={getActiveCountByType}
            onToggleType={toggleEntityType}
            onToggleAll={toggleAllRedactions}
            totalActive={getActiveCount()}
            collapsible={true}
          />
        </div>

        <div className="lg:col-span-3 grid gap-5 grid-cols-1 lg:grid-cols-2">
          <OriginalTextPanel
            text={originalText}
            entities={entities}
            activeIndices={activeRedactions}
            onHoverEntity={setHoveredEntityIndex}
            hoveredIndex={hoveredEntityIndex}
          />
          <RedactedPreviewPanel
            originalText={originalText}
            entities={entities}
            activeIndices={activeRedactions}
          />
        </div>
      </section>

      <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow-lg shadow-black/20">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-slate-200">Entity Metadata</h2>
          <div className="flex gap-3 text-xs font-semibold text-slate-500">
            <div className="bg-emerald-500/10 text-emerald-400 px-2 py-1 rounded">
              Active: {getActiveCount()}
            </div>
            <div className="bg-indigo-500/10 text-indigo-400 px-2 py-1 rounded">
              Total: {entities.length}
            </div>
          </div>
        </div>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[800px] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-xs uppercase tracking-wide text-slate-500">
                <th className="py-2 pr-3 w-8"></th>
                <th className="py-2 pr-3">Type</th>
                <th className="py-2 pr-3">Original</th>
                <th className="py-2 pr-3">Replacement</th>
                <th className="py-2 pr-3">Confidence</th>
                <th className="py-2 pr-3">Range</th>
              </tr>
            </thead>
            <tbody>
              {entities.map((entity, idx) => (
                <tr
                  key={`${entity.entity_type}-${entity.start}-${entity.end}-${idx}`}
                  className={`border-b border-slate-800 cursor-pointer transition-colors ${
                    isEntityActive(idx) ? "hover:bg-slate-800/40" : "opacity-50"
                  } ${hoveredEntityIndex === idx ? "bg-indigo-500/5" : ""}`}
                  onMouseEnter={() => setHoveredEntityIndex(idx)}
                  onMouseLeave={() => setHoveredEntityIndex(null)}
                  onClick={() => toggleEntity(idx)}
                >
                  <td className="py-2 pr-3">
                    <input
                      type="checkbox"
                      checked={isEntityActive(idx)}
                      onChange={() => toggleEntity(idx)}
                      className="rounded cursor-pointer accent-indigo-500"
                      aria-label={`Toggle ${entity.entity_type}`}
                    />
                  </td>
                  <td className="py-2 pr-3">
                    <span
                      className={`inline-block rounded px-2 py-0.5 text-xs font-semibold ${
                        entityStyles[entity.entity_type] ?? "bg-slate-700/50 text-slate-400"
                      }`}
                    >
                      {entity.entity_type}
                    </span>
                  </td>
                  <td className="max-w-xs py-2 pr-3 font-mono text-xs text-slate-300 truncate">
                    {entity.original_text}
                  </td>
                  <td className="py-2 pr-3 font-mono text-xs text-slate-400">{entity.replacement}</td>
                  <td className="py-2 pr-3">
                    <ConfidenceBadge confidence={entity.confidence} />
                  </td>
                  <td className="py-2 pr-3 text-slate-400">
                    {entity.start}-{entity.end}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <footer className="mt-8 border-t border-slate-800 py-4 text-center text-sm text-slate-500">
        <div className="flex items-center justify-center gap-2">
          <ShieldCheck className="h-4 w-4 text-emerald-500" />
          <span>Powered by {result.model}</span>
        </div>
      </footer>
    </main>
  );
}
