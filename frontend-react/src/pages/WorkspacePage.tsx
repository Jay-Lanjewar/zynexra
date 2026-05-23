import { useState, useEffect, useRef } from "react";
import type { HistoryRecord, HistoryFilter, ApiError } from "../api";
import {
  getHistoryRecords,
  getRecordDetail,
  deleteRecord,
  getHistorySummary,
  type HistorySummary,
} from "../api";
import type { AppMode, AuditResponse } from "../types";
import { HistoryCard } from "../components/HistoryCard";
import { HistoryFilterUI } from "../components/HistoryFilter";
import { ActivitySummary } from "../components/ActivitySummary";
import { HistoryListSkeleton, SummarySkeleton } from "../components/LoadingSkeleton";
import { FolderOpen, FileSearch, Eraser, MessageSquareText, ArrowLeft } from "lucide-react";
import { persistence } from "../utils/persistence";

interface WorkspacePageProps {
  onModeChange: (mode: AppMode | "WORKSPACE") => void;
  onRecordOpen: (record: HistoryRecord, result: AuditResponse) => void;
}

const ITEMS_PER_PAGE = 10;

export function WorkspacePage({ onModeChange, onRecordOpen }: WorkspacePageProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<"all" | "audit" | "redaction" | "advisory">("all");
  const [records, setRecords] = useState<HistoryRecord[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [filter, setFilter] = useState<HistoryFilter>(() => {
    const saved = persistence.loadFilters();
    if (saved && saved.filter && saved.activeTab) {
      return { ...saved.filter, limit: ITEMS_PER_PAGE, offset: 0 };
    }
    return {
      recordType: "all",
      limit: ITEMS_PER_PAGE,
      offset: 0,
    };
  });
  const [summary, setSummary] = useState<HistorySummary | undefined>();
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [total, setTotal] = useState(0);
  const filterKey = JSON.stringify({ tab: activeTab, ...filter });
  const initialTabSet = useRef(false);

  useEffect(() => {
    const saved = persistence.loadFilters();
    if (saved && saved.activeTab) {
      setActiveTab(saved.activeTab as "all" | "audit" | "redaction" | "advisory");
    }
    fetchSummary();
    initialTabSet.current = true;
  }, []);

  useEffect(() => {
    if (initialTabSet.current) {
      fetchRecords();
      persistence.saveFilters({ filter, activeTab, timestamp: Date.now() });
    }
  }, [filterKey]);

  async function fetchRecords() {
    try {
      setIsLoading(true);
      setError(null);

      const effectiveFilter: HistoryFilter = {
        ...filter,
        recordType: (activeTab === "all" ? "all" : activeTab) as any,
      };

      const response = await getHistoryRecords(effectiveFilter);

      if (response.success) {
        setRecords(response.records);
        setTotal(response.total || 0);
      } else {
        setError({ code: "SERVER_ERROR", message: response.message || "Failed to load records" });
        setRecords([]);
      }
    } catch (err) {
      const apiErr = err as ApiError;
      setError(apiErr);
      setRecords([]);
    } finally {
      setIsLoading(false);
    }
  }

  async function fetchSummary() {
    try {
      setSummaryLoading(true);
      const summaryData = await getHistorySummary();
      setSummary(summaryData);
    } catch (err) {
      console.error("Failed to fetch summary:", err);
    } finally {
      setSummaryLoading(false);
    }
  }

  async function handleDelete(recordId: number) {
    if (!confirm("Are you sure you want to delete this record?")) return;

    try {
      setDeletingId(recordId);

      const recordType = records.find((r) => r.id === recordId)?.mode?.toLowerCase() as
        | "audit"
        | "redaction"
        | "advisory"
        | undefined;

      const response = await deleteRecord(recordId, recordType || "audit");

      if (response.success) {
        setRecords((prev) => prev.filter((r) => r.id !== recordId));
        setTotal((prev) => Math.max(0, prev - 1));
        fetchSummary();
      }
    } catch (err) {
      console.error("Failed to delete record:", err);
      setError(err as ApiError);
    } finally {
      setDeletingId(null);
    }
  }

  async function handleCardClick(record: HistoryRecord) {
    try {
      setIsLoading(true);

      const recordType = record.mode?.toLowerCase() as "audit" | "redaction" | "advisory" | undefined;
      const detail = await getRecordDetail(record.id, recordType || "audit");

      if (detail.success && detail.record) {
        const rawIssues = detail.record.issues || [];
        console.log("[Workspace] Reopened audit payload:", detail.record);
        console.log("[Workspace] Raw issues from API:", rawIssues);
        
        const issues = rawIssues.map((issue: Record<string, unknown>) => {
          const normalized = {
            issue_title: String(issue.issue_title || issue.title || ""),
            severity: String(issue.severity || "UNKNOWN"),
            category: String(issue.category || "General"),
            location: String(issue.location || "Unknown"),
            quoted_text: String(issue.quoted_text || issue.text || ""),
            risk_explanation: String(issue.risk_explanation || ""),
            suggested_improvement: String(issue.suggested_improvement || ""),
          };
          return normalized;
        });
        
        if (rawIssues.length === 0 && record.issue_count && record.issue_count > 0) {
          console.warn("[Workspace] Defensive fallback: issue_count > 0 but issues empty", {
            recordId: record.id,
            issueCount: record.issue_count,
            issuesFound: rawIssues.length
          });
        }
        
        console.log("[Workspace] Normalized issues count ->", issues.length);
        
        const auditResponse: AuditResponse = {
          success: true,
          model: "claude",
          mode: (record.mode?.toUpperCase() as AppMode) || "AUDIT",
          issue_count: issues.length || record.issue_count || 0,
          issues,
          redaction_count: record.redaction_count,
          redaction_entities: [],
          original_text: "",
          redacted_text: "",
          advisory_text: "",
          confidence_score: detail.record.confidence_score ?? detail.response?.confidence_score,
          confidence_label: detail.record.confidence_label ?? detail.response?.confidence_label,
          fallback_used: detail.record.fallback_used ?? detail.response?.fallback_used,
          metadata: detail.record.metadata ?? detail.response?.metadata,
        };

        onRecordOpen(record, auditResponse);
      }
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setIsLoading(false);
    }
  }

  function handleFilterChange(newFilter: HistoryFilter) {
    setFilter({ ...newFilter, offset: 0 });
  }

  function handleClearFilters() {
    setFilter({
      recordType: "all",
      limit: ITEMS_PER_PAGE,
      offset: 0,
    });
  }

  function handleTabChange(tab: typeof activeTab) {
    setActiveTab(tab);
    setFilter({ ...filter, offset: 0 });
  }

  const currentPage = Math.floor((filter.offset || 0) / ITEMS_PER_PAGE) + 1;
  const totalPages = Math.ceil(total / ITEMS_PER_PAGE);
  const hasActiveFilters = Boolean(
    filter.filename || filter.mode || filter.severity || filter.startDate || filter.endDate
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Mobile Menu Button */}
      <div className="lg:hidden fixed top-4 left-4 z-50">
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-2 bg-white rounded-lg border border-slate-200 shadow-sm hover:bg-slate-50"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 6h16M4 12h16M4 18h16"
            />
          </svg>
        </button>
      </div>

      <div className="flex h-screen">
        {/* Sidebar */}
        <div
          className={`${
            sidebarOpen ? "translate-x-0" : "-translate-x-full"
          } lg:translate-x-0 fixed lg:static w-64 h-full bg-white border-r border-slate-200 p-6 transition-transform duration-300 z-40 overflow-y-auto`}
        >
          <div className="space-y-6">
            <div className="flex items-center gap-2">
              <button
                onClick={() => onModeChange("AUDIT")}
                className="flex items-center gap-1.5 text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to Zynexra
              </button>
            </div>

            <div>
              <h1 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <FolderOpen className="h-5 w-5 text-blue-600" />
                Workspace
              </h1>
              <p className="text-sm text-slate-600 mt-1">Manage your audit history</p>
            </div>

            <div className="pt-4 border-t border-slate-200">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Navigate</p>
              <nav className="space-y-1">
                <button
                  onClick={() => onModeChange("AUDIT")}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-100 transition-colors"
                >
                  <FileSearch className="h-4 w-4 text-blue-500" />
                  New Audit
                </button>
                <button
                  onClick={() => onModeChange("REDACTION")}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-100 transition-colors"
                >
                  <Eraser className="h-4 w-4 text-amber-500" />
                  New Redaction
                </button>
                <button
                  onClick={() => onModeChange("ADVISORY")}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-100 transition-colors"
                >
                  <MessageSquareText className="h-4 w-4 text-emerald-500" />
                  Advisory Chat
                </button>
              </nav>
            </div>

            <div className="pt-4 border-t border-slate-200">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Filter by type</p>
            </div>

            <nav className="space-y-2">
              <button
                onClick={() => {
                  handleTabChange("all");
                  setSidebarOpen(false);
                }}
                className={`w-full text-left px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
                  activeTab === "all"
                    ? "bg-blue-100 text-blue-900"
                    : "text-slate-700 hover:bg-slate-100"
                }`}
              >
                📋 All Items
              </button>
              <button
                onClick={() => {
                  handleTabChange("audit");
                  setSidebarOpen(false);
                }}
                className={`w-full text-left px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
                  activeTab === "audit"
                    ? "bg-blue-100 text-blue-900"
                    : "text-slate-700 hover:bg-slate-100"
                }`}
              >
                ✓ Recent Audits
              </button>
              <button
                onClick={() => {
                  handleTabChange("redaction");
                  setSidebarOpen(false);
                }}
                className={`w-full text-left px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
                  activeTab === "redaction"
                    ? "bg-blue-100 text-blue-900"
                    : "text-slate-700 hover:bg-slate-100"
                }`}
              >
                🔒 Recent Redactions
              </button>
              <button
                onClick={() => {
                  handleTabChange("advisory");
                  setSidebarOpen(false);
                }}
                className={`w-full text-left px-4 py-2 rounded-lg font-medium text-sm transition-colors ${
                  activeTab === "advisory"
                    ? "bg-blue-100 text-blue-900"
                    : "text-slate-700 hover:bg-slate-100"
                }`}
              >
                💬 Advisory Chats
              </button>
            </nav>

            <div className="pt-6 border-t border-slate-200">
              <ActivitySummary summary={summary} isLoading={summaryLoading} />
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-6xl mx-auto p-4 lg:p-8">
            {/* Header */}
            <div className="mb-8">
              <h2 className="text-2xl lg:text-3xl font-bold text-slate-900">
                {activeTab === "all"
                  ? "All Items"
                  : activeTab === "audit"
                    ? "Recent Audits"
                    : activeTab === "redaction"
                      ? "Recent Redactions"
                      : "Advisory Chats"}
              </h2>
              <p className="text-slate-600 text-sm mt-1">
                {total === 0
                  ? "No items to display"
                  : `Showing ${Math.min((filter.offset || 0) + ITEMS_PER_PAGE, total)} of ${total}`}
              </p>
            </div>

            {/* Filters */}
            <div className="mb-6">
              <HistoryFilterUI
                filter={filter}
                onFilterChange={handleFilterChange}
                onClear={handleClearFilters}
              />
            </div>

            {/* Error State */}
            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-800">
                  <strong>Error:</strong> {error.message}
                </p>
              </div>
            )}

            {/* Loading State */}
            {isLoading && (
              <div>
                <HistoryListSkeleton />
              </div>
            )}

            {/* Empty State */}
            {!isLoading && records.length === 0 && (
              <div className="bg-white rounded-lg border border-slate-200 p-8 text-center">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded-lg bg-slate-100 mb-4">
                  <svg
                    className="w-6 h-6 text-slate-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                </div>
                <h3 className="font-semibold text-slate-900 mb-1">
                  {hasActiveFilters ? "No results found" : "No items yet"}
                </h3>
                <p className="text-sm text-slate-600 mb-4">
                  {hasActiveFilters
                    ? "Try adjusting your filters to find what you're looking for."
                    : `Start by creating a new ${activeTab === "advisory" ? "advisory chat" : activeTab} to see it here.`}
                </p>
                {hasActiveFilters && (
                  <button
                    onClick={handleClearFilters}
                    className="text-sm font-medium text-blue-600 hover:text-blue-700"
                  >
                    Clear Filters
                  </button>
                )}
              </div>
            )}

            {/* Results Grid */}
            {!isLoading && records.length > 0 && (
              <div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
                  {records.map((record) => (
                    <HistoryCard
                      key={record.id}
                      record={record}
                      onClick={() => handleCardClick(record)}
                      onDelete={() => handleDelete(record.id)}
                      isDeleting={deletingId === record.id}
                    />
                  ))}
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between">
                    <p className="text-sm text-slate-600">
                      Page {currentPage} of {totalPages}
                    </p>
                    <div className="flex gap-2">
                      <button
                        onClick={() =>
                          setFilter({
                            ...filter,
                            offset: Math.max(0, (filter.offset || 0) - ITEMS_PER_PAGE),
                          })
                        }
                        disabled={(filter.offset || 0) === 0}
                        className="px-3 py-2 text-sm font-medium bg-white border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        ← Previous
                      </button>
                      <button
                        onClick={() =>
                          setFilter({
                            ...filter,
                            offset: (filter.offset || 0) + ITEMS_PER_PAGE,
                          })
                        }
                        disabled={currentPage >= totalPages}
                        className="px-3 py-2 text-sm font-medium bg-white border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                      >
                        Next →
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Mobile Overlay */}
      {sidebarOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 z-30"
          onClick={() => setSidebarOpen(false)}
        />
      )}
    </div>
  );
}
