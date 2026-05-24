import { CheckSquare, Square } from "lucide-react";
import { useState } from "react";
import type { RedactionEntity } from "../types";
import { sortEntityTypes } from "../redactionUtils";

const entityStyles: Record<string, string> = {
  PERSON: "bg-sky-500/10 text-sky-300 border-sky-500/20",
  EMAIL: "bg-rose-500/10 text-rose-300 border-rose-500/20",
  PHONE: "bg-amber-500/10 text-amber-300 border-amber-500/20",
  ADDRESS: "bg-emerald-500/10 text-emerald-300 border-emerald-500/20",
  COMPANY: "bg-violet-500/10 text-violet-300 border-violet-500/20",
  LOCATION: "bg-teal-500/10 text-teal-300 border-teal-500/20",
  MONEY: "bg-lime-500/10 text-lime-300 border-lime-500/20",
  DATE: "bg-cyan-500/10 text-cyan-300 border-cyan-500/20",
  ID_NUMBER: "bg-fuchsia-500/10 text-fuchsia-300 border-fuchsia-500/20",
};

interface EntitySidebarProps {
  entities: RedactionEntity[];
  entityCounts: Map<string, number>;
  activeCountByType: (type: string) => number;
  onToggleType: (type: string) => void;
  onToggleAll: () => void;
  totalActive: number;
  collapsible?: boolean;
}

export function EntitySidebar({
  entities,
  entityCounts,
  activeCountByType,
  onToggleType,
  onToggleAll,
  totalActive,
  collapsible = true,
}: EntitySidebarProps) {
  const [expandedTypes, setExpandedTypes] = useState<Set<string>>(() => new Set(entityCounts.keys()));
  const [isCollapsed, setIsCollapsed] = useState(false);

  const toggleExpand = (type: string) => {
    setExpandedTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  };

  const entityTypes = sortEntityTypes(Array.from(entityCounts.keys()));
  const allActive = totalActive === entities.length;

  if (isCollapsed && collapsible) {
    return (
      <div className="flex h-full flex-col rounded-xl border border-slate-800 bg-slate-900/60 p-3 shadow-lg shadow-black/20">
        <button
          onClick={() => setIsCollapsed(false)}
          className="rounded px-2 py-1 text-xs font-semibold text-slate-400 hover:bg-slate-800/40"
          title="Expand sidebar"
        >
          ◀ Entities
        </button>
      </div>
    );
  }

  return (
    <aside className="flex h-full flex-col rounded-xl border border-slate-800 bg-slate-900/60 p-4 shadow-lg shadow-black/20">
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <h3 className="text-sm font-semibold text-slate-200">Entities</h3>
        {collapsible && (
          <button
            onClick={() => setIsCollapsed(true)}
            className="rounded p-1 text-slate-500 hover:bg-slate-800/40 hover:text-slate-300"
            title="Collapse sidebar"
          >
            ▶
          </button>
        )}
      </div>

      <div className="mt-3 flex flex-col gap-2 pb-4 border-b border-slate-800">
        <button
          onClick={onToggleAll}
          className="flex items-center gap-2 rounded px-2 py-1.5 text-sm font-medium text-slate-300 hover:bg-slate-800/40"
        >
          {allActive ? <CheckSquare className="h-4 w-4 text-emerald-400" /> : <Square className="h-4 w-4 text-slate-500" />}
          <span>{allActive ? "Deselect All" : "Select All"}</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2">
        {entityTypes.map((type) => {
          const count = entityCounts.get(type) ?? 0;
          const activeCount = activeCountByType(type);
          const isExpanded = expandedTypes.has(type);
          const isPartialActive = activeCount > 0 && activeCount < count;
          const isAllActive = activeCount === count;
          const style = entityStyles[type] ?? "bg-slate-700/50 text-slate-400 border-slate-700";

          return (
            <div key={type}>
              <button
                onClick={() => onToggleType(type)}
                className="w-full flex items-center gap-2 rounded px-2 py-1.5 text-sm font-medium text-slate-300 hover:bg-slate-800/40 transition-colors"
              >
                {isAllActive ? (
                  <CheckSquare className="h-4 w-4 flex-shrink-0 text-emerald-400" />
                ) : isPartialActive ? (
                  <div className="h-4 w-4 flex-shrink-0 rounded border-2 border-amber-500 bg-amber-500/20" />
                ) : (
                  <Square className="h-4 w-4 flex-shrink-0 text-slate-600" />
                )}
                <span className="flex-1 text-left">{type}</span>
                <span className="text-xs text-slate-500">
                  {activeCount}/{count}
                </span>
              </button>

              {isExpanded && (
                <div className={`mt-1 rounded border ${style} px-2 py-2`}>
                  <p className="text-xs font-semibold text-current opacity-75 mb-2">{count} entities</p>
                  <div className="space-y-1">
                    {entities
                      .map((e, idx) => ({ entity: e, idx }))
                      .filter((item) => item.entity.entity_type === type)
                      .slice(0, 3)
                      .map((item) => (
                        <div key={item.idx} className="text-xs text-current opacity-80 truncate">
                          "{item.entity.original_text.slice(0, 20)}{item.entity.original_text.length > 20 ? "…" : ""}"
                        </div>
                      ))}
                    {count > 3 && (
                      <div className="text-xs text-current opacity-60 italic">
                        +{count - 3} more
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="mt-4 border-t border-slate-800 pt-3">
        <div className="text-xs text-slate-500 space-y-1">
          <div>
            <span className="font-semibold text-slate-300">Active:</span> {totalActive} / {entities.length}
          </div>
          <div>
            <span className="font-semibold text-slate-300">Types:</span> {entityTypes.length}
          </div>
        </div>
      </div>
    </aside>
  );
}
