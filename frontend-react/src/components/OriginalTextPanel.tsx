import { ReactNode } from "react";
import type { RedactionEntity } from "../types";

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
          entityStyles[entity.entity_type] ?? "bg-slate-700/50 text-slate-400 ring-slate-700"
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
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow-lg shadow-black/20 h-full flex flex-col">
      <h2 className="text-sm font-semibold text-slate-200">Original Text</h2>
      <pre className="mt-3 flex-1 max-h-[35rem] overflow-auto whitespace-pre-wrap rounded-lg border border-slate-800 bg-slate-950 p-4 text-sm leading-6 text-slate-300">
        <>{parts}</>
      </pre>
    </div>
  );
}
