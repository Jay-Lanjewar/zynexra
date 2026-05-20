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
  PERSON: "bg-sky-100 text-sky-800 ring-sky-200",
  EMAIL: "bg-rose-100 text-rose-800 ring-rose-200",
  PHONE: "bg-amber-100 text-amber-800 ring-amber-200",
  ADDRESS: "bg-emerald-100 text-emerald-800 ring-emerald-200",
  COMPANY: "bg-violet-100 text-violet-800 ring-violet-200",
  LOCATION: "bg-teal-100 text-teal-800 ring-teal-200",
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
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">Redaction Results</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-950">
            {entities.length} sensitive entit{entities.length === 1 ? "y" : "ies"} detected
          </h1>
          <div className="mt-3 flex flex-wrap gap-2">
            {entityTypes.map((entityType) => {
              const count = entityCounts.get(entityType) ?? 0;
              return (
                <span
                  key={entityType}
                  className={`rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${entityStyles[entityType] ?? "bg-slate-100 text-slate-700 ring-slate-200"}`}
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

      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold text-slate-900">Entity Metadata</h2>
          <div className="flex gap-3 text-xs font-semibold text-slate-600">
            <div className="bg-emerald-50 text-emerald-700 px-2 py-1 rounded">
              Active: {getActiveCount()}
            </div>
            <div className="bg-blue-50 text-blue-700 px-2 py-1 rounded">
              Total: {entities.length}
            </div>
          </div>
        </div>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[800px] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
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
                  className={`border-b border-slate-100 cursor-pointer transition-colors ${
                    isEntityActive(idx) ? "hover:bg-slate-50" : "opacity-50"
                  } ${hoveredEntityIndex === idx ? "bg-blue-50" : ""}`}
                  onMouseEnter={() => setHoveredEntityIndex(idx)}
                  onMouseLeave={() => setHoveredEntityIndex(null)}
                  onClick={() => toggleEntity(idx)}
                >
                  <td className="py-2 pr-3">
                    <input
                      type="checkbox"
                      checked={isEntityActive(idx)}
                      onChange={() => toggleEntity(idx)}
                      className="rounded cursor-pointer"
                      aria-label={`Toggle ${entity.entity_type}`}
                    />
                  </td>
                  <td className="py-2 pr-3">
                    <span
                      className={`inline-block rounded px-2 py-0.5 text-xs font-semibold ${
                        entityStyles[entity.entity_type] ?? "bg-slate-100 text-slate-700"
                      }`}
                    >
                      {entity.entity_type}
                    </span>
                  </td>
                  <td className="max-w-xs py-2 pr-3 font-mono text-xs text-slate-700 truncate">
                    {entity.original_text}
                  </td>
                  <td className="py-2 pr-3 font-mono text-xs text-slate-700">{entity.replacement}</td>
                  <td className="py-2 pr-3">
                    <ConfidenceBadge confidence={entity.confidence} />
                  </td>
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
