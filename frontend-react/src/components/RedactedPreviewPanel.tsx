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
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm h-full flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-sm font-semibold text-slate-900">Redacted Preview</h2>
        <span className="text-xs font-semibold text-slate-600 bg-slate-100 px-2 py-1 rounded">
          {redactionCount} / {totalRedacted} active
        </span>
      </div>
      <pre className="mt-3 flex-1 max-h-[35rem] overflow-auto whitespace-pre-wrap rounded-md border border-slate-200 bg-slate-950 p-4 text-sm leading-6 text-emerald-400 font-mono">
        {previewText || "No redactions applied."}
      </pre>
    </div>
  );
}
