import { CheckSquare, Square } from "lucide-react";
import { useState } from "react";
import type { RedactionEntity } from "../types";
import { sortEntityTypes } from "../redactionUtils";

const entityStyles: Record<string, string> = {
  PERSON: "bg-sky-100 text-sky-800 border-sky-200",
  EMAIL: "bg-rose-100 text-rose-800 border-rose-200",
  PHONE: "bg-amber-100 text-amber-800 border-amber-200",
  ADDRESS: "bg-emerald-100 text-emerald-800 border-emerald-200",
  COMPANY: "bg-violet-100 text-violet-800 border-violet-200",
  LOCATION: "bg-teal-100 text-teal-800 border-teal-200",
  MONEY: "bg-lime-100 text-lime-800 border-lime-200",
  DATE: "bg-cyan-100 text-cyan-800 border-cyan-200",
  ID_NUMBER: "bg-fuchsia-100 text-fuchsia-800 border-fuchsia-200",
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
      <div className="flex h-full flex-col rounded-lg border border-slate-200 bg-white p-3 shadow-sm">
        <button
          onClick={() => setIsCollapsed(false)}
          className="rounded px-2 py-1 text-xs font-semibold text-slate-600 hover:bg-slate-100"
          title="Expand sidebar"
        >
          ◀ Entities
        </button>
      </div>
    );
  }

  return (
    <aside className="flex h-full flex-col rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between pb-4 border-b border-slate-200">
        <h3 className="text-sm font-semibold text-slate-900">Entities</h3>
        {collapsible && (
          <button
            onClick={() => setIsCollapsed(true)}
            className="rounded p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-700"
            title="Collapse sidebar"
          >
            ▶
          </button>
        )}
      </div>

      <div className="mt-3 flex flex-col gap-2 pb-4 border-b border-slate-200">
        <button
          onClick={onToggleAll}
          className="flex items-center gap-2 rounded px-2 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-100"
        >
          {allActive ? <CheckSquare className="h-4 w-4 text-emerald-600" /> : <Square className="h-4 w-4 text-slate-400" />}
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
          const style = entityStyles[type] ?? "bg-slate-100 text-slate-800 border-slate-200";

          return (
            <div key={type}>
              <button
                onClick={() => onToggleType(type)}
                className="w-full flex items-center gap-2 rounded px-2 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
              >
                {isAllActive ? (
                  <CheckSquare className="h-4 w-4 flex-shrink-0 text-emerald-600" />
                ) : isPartialActive ? (
                  <div className="h-4 w-4 flex-shrink-0 rounded border-2 border-amber-500 bg-amber-50" />
                ) : (
                  <Square className="h-4 w-4 flex-shrink-0 text-slate-300" />
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

      <div className="mt-4 border-t border-slate-200 pt-3">
        <div className="text-xs text-slate-600 space-y-1">
          <div>
            <span className="font-semibold">Active:</span> {totalActive} / {entities.length}
          </div>
          <div>
            <span className="font-semibold">Types:</span> {entityTypes.length}
          </div>
        </div>
      </div>
    </aside>
  );
}
