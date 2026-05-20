import { ReactNode } from "react";
import type { RedactionEntity } from "../types";

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

interface OriginalTextPanelProps {
  text: string;
  entities: RedactionEntity[];
  activeIndices: Set<number>;
  onHoverEntity?: (index: number | null) => void;
  hoveredIndex?: number | null;
}

export function OriginalTextPanel({
  text,
  entities,
  activeIndices,
  onHoverEntity,
  hoveredIndex,
}: OriginalTextPanelProps) {
  const ordered = [...entities]
    .map((e, idx) => ({ ...e, idx }))
    .filter((item) => activeIndices.has(item.idx))
    .sort((a, b) => a.start - b.start);

  const parts: ReactNode[] = [];
  let cursor = 0;

  ordered.forEach((item, partIndex) => {
    const entity = item;
    const idx = item.idx;

    if (entity.start > cursor) {
      parts.push(<span key={`text-${partIndex}`}>{text.slice(cursor, entity.start)}</span>);
    }

    parts.push(
      <mark
        key={`${entity.entity_type}-${entity.start}-${entity.end}-${idx}`}
        className={`rounded px-1 py-0.5 ring-1 cursor-pointer transition-all ${
          entityStyles[entity.entity_type] ?? "bg-slate-100 text-slate-800 ring-slate-200"
        } ${hoveredIndex === idx ? "ring-2 shadow-md" : ""}`}
        title={`${entity.entity_type} - ${(entity.confidence * 100).toFixed(0)}%`}
        onMouseEnter={() => onHoverEntity?.(idx)}
        onMouseLeave={() => onHoverEntity?.(null)}
      >
        {text.slice(entity.start, entity.end)}
      </mark>
    );
    cursor = entity.end;
  });

  if (cursor < text.length) {
    parts.push(<span key="text-tail">{text.slice(cursor)}</span>);
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm h-full flex flex-col">
      <h2 className="text-sm font-semibold text-slate-900">Original Text</h2>
      <pre className="mt-3 flex-1 max-h-[35rem] overflow-auto whitespace-pre-wrap rounded-md border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-800">
        <>{parts}</>
      </pre>
    </div>
  );
}
