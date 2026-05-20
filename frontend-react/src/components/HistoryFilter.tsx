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

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-900">Filter Results</h3>
        {hasActiveFilters && (
          <button
            onClick={onClear}
            className="text-xs font-medium text-blue-600 hover:text-blue-700 hover:bg-blue-50 px-2 py-1 rounded transition-colors"
          >
            Clear Filters
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <div>
          <label className="block text-xs font-medium text-slate-700 mb-1">Mode</label>
          <select
            value={filter.mode || ""}
            onChange={(e) =>
              onFilterChange({ ...filter, mode: e.target.value || undefined, offset: 0 })
            }
            className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">All Modes</option>
            <option value="AUDIT">Audit</option>
            <option value="REDACTION">Redaction</option>
            <option value="ADVISORY">Advisory</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-700 mb-1">Severity</label>
          <select
            value={filter.severity || ""}
            onChange={(e) =>
              onFilterChange({ ...filter, severity: e.target.value || undefined, offset: 0 })
            }
            className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-700 mb-1">Filename</label>
          <input
            type="text"
            value={filter.filename || ""}
            onChange={(e) =>
              onFilterChange({ ...filter, filename: e.target.value || undefined, offset: 0 })
            }
            placeholder="Search filename..."
            className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-700 mb-1">Record Type</label>
          <select
            value={filter.recordType || "all"}
            onChange={(e) =>
              onFilterChange({
                ...filter,
                recordType: (e.target.value as any) || "all",
                offset: 0,
              })
            }
            className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
          <label className="block text-xs font-medium text-slate-700 mb-1">Start Date</label>
          <input
            type="date"
            value={filter.startDate || ""}
            onChange={(e) =>
              onFilterChange({ ...filter, startDate: e.target.value || undefined, offset: 0 })
            }
            className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-700 mb-1">End Date</label>
          <input
            type="date"
            value={filter.endDate || ""}
            onChange={(e) =>
              onFilterChange({ ...filter, endDate: e.target.value || undefined, offset: 0 })
            }
            className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>
    </div>
  );
}
