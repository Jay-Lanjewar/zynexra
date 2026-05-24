import type { HistoryFilter } from "../api";

interface HistoryFilterProps {
  filter: HistoryFilter;
  onFilterChange: (filter: HistoryFilter) => void;
  onClear: () => void;
}

export function HistoryFilterUI({ filter, onFilterChange, onClear }: HistoryFilterProps) {
  const hasActiveFilters = Boolean(
    filter.filename || filter.mode || filter.severity || filter.startDate || filter.endDate
  );

  const inputClass = "w-full px-3 py-2 text-sm bg-slate-800/40 border border-slate-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 text-slate-200 placeholder-slate-500";

  return (
    <div className="bg-slate-900/60 rounded-xl border border-slate-800 p-4 space-y-4 backdrop-blur">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">Filter Results</h3>
        {hasActiveFilters && (
          <button
            onClick={onClear}
            className="text-xs font-medium text-indigo-400 hover:text-indigo-300 hover:bg-indigo-500/10 px-2 py-1 rounded transition-colors"
          >
            Clear Filters
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Mode</label>
          <select
            value={filter.mode || ""}
            onChange={(e) =>
              onFilterChange({ ...filter, mode: e.target.value || undefined, offset: 0 })
            }
            className={inputClass}
          >
            <option value="">All Modes</option>
            <option value="AUDIT">Audit</option>
            <option value="REDACTION">Redaction</option>
            <option value="ADVISORY">Advisory</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Severity</label>
          <select
            value={filter.severity || ""}
            onChange={(e) =>
              onFilterChange({ ...filter, severity: e.target.value || undefined, offset: 0 })
            }
            className={inputClass}
          >
            <option value="">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Filename</label>
          <input
            type="text"
            value={filter.filename || ""}
            onChange={(e) =>
              onFilterChange({ ...filter, filename: e.target.value || undefined, offset: 0 })
            }
            placeholder="Search filename..."
            className={inputClass}
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Record Type</label>
          <select
            value={filter.recordType || "all"}
            onChange={(e) =>
              onFilterChange({
                ...filter,
                recordType: (e.target.value as any) || "all",
                offset: 0,
              })
            }
            className={inputClass}
          >
            <option value="all">All Types</option>
            <option value="audit">Audits</option>
            <option value="redaction">Redactions</option>
            <option value="advisory">Advisory</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Start Date</label>
          <input
            type="date"
            value={filter.startDate || ""}
            onChange={(e) =>
              onFilterChange({ ...filter, startDate: e.target.value || undefined, offset: 0 })
            }
            className={inputClass}
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">End Date</label>
          <input
            type="date"
            value={filter.endDate || ""}
            onChange={(e) =>
              onFilterChange({ ...filter, endDate: e.target.value || undefined, offset: 0 })
            }
            className={inputClass}
          />
        </div>
      </div>
    </div>
  );
}
