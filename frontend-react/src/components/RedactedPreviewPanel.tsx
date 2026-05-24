import { useMemo } from "react";
import type { RedactionEntity } from "../types";
import { computeLivePreview } from "../redactionUtils";

interface RedactedPreviewPanelProps {
  originalText: string;
  entities: RedactionEntity[];
  activeIndices: Set<number>;
}

export function RedactedPreviewPanel({
  originalText,
  entities,
  activeIndices,
}: RedactedPreviewPanelProps) {
  const previewText = useMemo(
    () => computeLivePreview(originalText, entities, activeIndices),
    [originalText, entities, activeIndices]
  );

  const redactionCount = activeIndices.size;
  const totalRedacted = entities.length;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow-lg shadow-black/20 h-full flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-sm font-semibold text-slate-200">Redacted Preview</h2>
        <span className="text-xs font-semibold text-slate-500 bg-slate-800 px-2 py-1 rounded">
          {redactionCount} / {totalRedacted} active
        </span>
      </div>
      <pre className="mt-3 flex-1 max-h-[35rem] overflow-auto whitespace-pre-wrap rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm leading-6 text-emerald-400 font-mono">
        {previewText || "No redactions applied."}
      </pre>
    </div>
  );
}
