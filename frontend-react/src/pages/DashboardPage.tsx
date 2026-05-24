import { useState, useEffect, useMemo } from "react";
import {
  FileSearch, Eraser, MessageSquareText,
  BarChart3, Clock, Lightbulb, ArrowRight,
  TrendingUp, Shield, FileText,
} from "lucide-react";
import {
  getHistorySummary, getHistoryRecords,
  type HistorySummary, type HistoryRecord,
} from "../api";

type NavMode = "AUDIT" | "REDACTION" | "ADVISORY" | "WORKSPACE" | "DASHBOARD";

type DashboardPageProps = {
  onModeChange: (mode: NavMode) => void;
};

const modeCards = [
  {
    value: "AUDIT" as const,
    title: "Audit",
    description: "Scan contracts for legal risks, obligations, and problematic clauses with structured analysis.",
    input: "PDF, TXT, or DOC files — NDA, SaaS, employment, or any legal agreement",
    useCases: ["NDA review", "SaaS agreement", "Employment contract", "Vendor agreement"],
    color: "blue",
    icon: FileSearch,
  },
  {
    value: "REDACTION" as const,
    title: "Redaction",
    description: "Detect and redact personally identifiable information before sharing documents externally.",
    input: "PDF, TXT, or DOC files containing names, emails, phones, addresses, or company data",
    useCases: ["Share discovery docs", "Remove employee PII", "Sanitize contracts", "Compliance export"],
    color: "amber",
    icon: Shield,
  },
  {
    value: "ADVISORY" as const,
    title: "Advisory",
    description: "Ask legal-practice questions and get AI-powered guidance without uploading a document.",
    input: "Free-form text questions about contract law, liability, compliance, or legal strategy",
    useCases: ["Liability questions", "Compliance checks", "Jurisdiction advice", "Risk assessment"],
    color: "emerald",
    icon: MessageSquareText,
  },
];

function formatRelativeTime(timestamp: string): string {
  const diff = Date.now() - new Date(timestamp).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(timestamp).toLocaleDateString();
}

function getModeIcon(mode?: string) {
  switch (mode?.toUpperCase()) {
    case "AUDIT": return FileSearch;
    case "REDACTION": return Shield;
    case "ADVISORY": return MessageSquareText;
    default: return FileText;
  }
}

const colorConfig: Record<string, { border: string; iconBg: string; iconText: string; tagBg: string; tagText: string; tagBorder: string; button: string }> = {
  blue: {
    border: "border-indigo-500/30",
    iconBg: "bg-indigo-500/15",
    iconText: "text-indigo-400",
    tagBg: "bg-indigo-500/10",
    tagText: "text-indigo-300",
    tagBorder: "border-indigo-500/20",
    button: "bg-indigo-500 hover:bg-indigo-400 text-white",
  },
  amber: {
    border: "border-amber-500/30",
    iconBg: "bg-amber-500/15",
    iconText: "text-amber-400",
    tagBg: "bg-amber-500/10",
    tagText: "text-amber-300",
    tagBorder: "border-amber-500/20",
    button: "bg-amber-500 hover:bg-amber-400 text-white",
  },
  emerald: {
    border: "border-emerald-500/30",
    iconBg: "bg-emerald-500/15",
    iconText: "text-emerald-400",
    tagBg: "bg-emerald-500/10",
    tagText: "text-emerald-300",
    tagBorder: "border-emerald-500/20",
    button: "bg-emerald-500 hover:bg-emerald-400 text-white",
  },
};

function ModeCardSkeleton() {
  return (
    <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-6 animate-pulse">
      <div className="flex items-center gap-3 mb-4">
        <div className="h-10 w-10 rounded-lg bg-slate-700" />
        <div className="h-5 bg-slate-700 rounded w-24" />
      </div>
      <div className="space-y-2">
        <div className="h-3 bg-slate-700 rounded w-full" />
        <div className="h-3 bg-slate-700 rounded w-5/6" />
        <div className="h-3 bg-slate-700 rounded w-4/6" />
      </div>
    </div>
  );
}

export function DashboardPage({ onModeChange }: DashboardPageProps) {
  const [summary, setSummary] = useState<HistorySummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [summaryError, setSummaryError] = useState(false);
  const [recentRecords, setRecentRecords] = useState<HistoryRecord[]>([]);
  const [recordsLoading, setRecordsLoading] = useState(true);
  const [recordsError, setRecordsError] = useState(false);
  const [avgConfidence, setAvgConfidence] = useState<number | null>(null);

  useEffect(() => {
    fetchSummary();
    fetchRecentRecords();
  }, []);

  async function fetchSummary() {
    try {
      setSummaryLoading(true);
      setSummaryError(false);
      const data = await getHistorySummary();
      setSummary(data);
    } catch {
      setSummaryError(true);
    } finally {
      setSummaryLoading(false);
    }
  }

  async function fetchRecentRecords() {
    try {
      setRecordsLoading(true);
      setRecordsError(false);
      const response = await getHistoryRecords({ limit: 20 });
      if (response.success) {
        setRecentRecords(response.records);
        const withConfidence = response.records.filter(
          (r): r is HistoryRecord & { confidence_score: number } =>
            r.confidence_score != null
        );
        if (withConfidence.length > 0) {
          const avg = withConfidence.reduce((sum, r) => sum + r.confidence_score, 0) / withConfidence.length;
          setAvgConfidence(Math.round(avg * 100));
        }
      }
    } catch {
      setRecordsError(true);
    } finally {
      setRecordsLoading(false);
    }
  }

  const stats = summary?.stats || { audits: 0, redactions: 0, advisory: 0, total: 0 };

  const latestPerType = useMemo(() => {
    const audit = recentRecords.find((r) => r.mode?.toUpperCase() === "AUDIT");
    const redaction = recentRecords.find((r) => r.mode?.toUpperCase() === "REDACTION");
    const advisory = recentRecords.find((r) => r.mode?.toUpperCase() === "ADVISORY");
    return { audit, redaction, advisory };
  }, [recentRecords]);

  const tips = [
    {
      icon: FileSearch,
      title: "Audit a contract",
      description: "Upload an NDA, SaaS agreement, or employment contract for risk analysis.",
      action: () => onModeChange("AUDIT"),
      label: "Start Audit",
      color: "blue",
    },
    {
      icon: Shield,
      title: "Redact sensitive data",
      description: "Remove PII from documents before sharing with third parties.",
      action: () => onModeChange("REDACTION"),
      label: "Start Redaction",
      color: "amber",
    },
    {
      icon: MessageSquareText,
      title: "Ask legal questions",
      description: "Get AI-powered guidance on liability, compliance, and legal strategy.",
      action: () => onModeChange("ADVISORY"),
      label: "Ask Advisory",
      color: "emerald",
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-950 to-black">
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(59,130,246,0.15),transparent_50%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom_left,rgba(16,185,129,0.1),transparent_50%)]" />
        <div className="relative mx-auto max-w-7xl px-5 py-16 sm:px-8 sm:py-20 lg:py-28">
          <div className="animate-fade-up max-w-2xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-medium text-white/60 mb-6">
              <TrendingUp className="h-3.5 w-3.5" />
              Intelligent Document Analysis
            </div>
            <h1 className="text-4xl font-bold tracking-tight text-white sm:text-5xl lg:text-6xl">
              Zynexra
            </h1>
            <p className="mt-4 text-lg leading-relaxed text-slate-300 sm:text-xl sm:leading-8">
              Analyze contracts, redact sensitive data, and get legal guidance — all powered by local LLMs.
              Your documents never leave your machine.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              {tips.map((tip) => (
                <button
                  key={tip.label}
                  onClick={tip.action}
                  className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-3.5 py-1.5 text-sm font-medium text-slate-300 transition hover:bg-white/10 hover:text-white"
                >
                  <tip.icon className="h-3.5 w-3.5" />
                  {tip.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Mode Cards Section */}
      <section className="relative -mt-10 mx-auto max-w-7xl px-5 sm:px-8">
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {modeCards.map((card, index) => {
            const Icon = card.icon;
            const colors = colorConfig[card.color];

            return (
              <div
                key={card.value}
                className="animate-fade-up group relative flex flex-col rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur shadow-lg shadow-black/20 transition-all duration-200 hover:-translate-y-0.5 hover:border-slate-700"
                style={{ animationDelay: `${index * 100}ms` }}
              >
                <div className="p-6 flex-1">
                  <div className="flex items-center gap-3 mb-4">
                    <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${colors.iconBg}`}>
                      <Icon className={`h-5 w-5 ${colors.iconText}`} aria-hidden="true" />
                    </div>
                    <h2 className="text-lg font-semibold text-slate-100">{card.title}</h2>
                  </div>
                  <p className="text-sm leading-6 text-slate-400 mb-4">{card.description}</p>
                  <div className="mb-4">
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
                      Expected input
                    </p>
                    <p className="text-sm text-slate-400">{card.input}</p>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
                      Use cases
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {card.useCases.map((useCase) => (
                        <span
                          key={useCase}
                          className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${colors.tagBg} ${colors.tagText} ${colors.tagBorder}`}
                        >
                          {useCase}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
                <div className="px-6 pb-6">
                  <button
                    onClick={() => onModeChange(card.value)}
                    className={`inline-flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-semibold text-white transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 ${colors.button}`}
                  >
                    Get Started
                    <ArrowRight className="h-4 w-4" aria-hidden="true" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Quick Stats Section */}
      <section className="mx-auto max-w-7xl px-5 sm:px-8 mt-12">
        <div className="flex items-center gap-2 mb-6">
          <BarChart3 className="h-5 w-5 text-slate-500" aria-hidden="true" />
          <h2 className="text-lg font-semibold text-slate-200">Activity Overview</h2>
        </div>
        {summaryLoading ? (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="bg-slate-900/60 rounded-xl border border-slate-800 p-5 animate-pulse">
                <div className="h-4 w-16 bg-slate-700 rounded mb-3" />
                <div className="h-8 w-12 bg-slate-700 rounded" />
              </div>
            ))}
          </div>
        ) : summaryError ? (
          <div className="bg-slate-900/60 rounded-xl border border-slate-800 p-6 text-center">
            <p className="text-sm text-slate-500">Unable to load statistics</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="animate-fade-up bg-slate-900/60 rounded-xl border border-slate-800 p-5 transition-all duration-200 hover:-translate-y-0.5 hover:border-slate-700 hover:shadow-md hover:shadow-black/20">
              <div className="flex items-center gap-2 text-sm font-medium text-indigo-400 mb-2">
                <FileSearch className="h-4 w-4" />
                Audits
              </div>
              <p className="text-3xl font-bold text-slate-100">{stats.audits}</p>
            </div>
            <div className="animate-fade-up-delay-1 bg-slate-900/60 rounded-xl border border-slate-800 p-5 transition-all duration-200 hover:-translate-y-0.5 hover:border-slate-700 hover:shadow-md hover:shadow-black/20">
              <div className="flex items-center gap-2 text-sm font-medium text-amber-400 mb-2">
                <Shield className="h-4 w-4" />
                Redactions
              </div>
              <p className="text-3xl font-bold text-slate-100">{stats.redactions}</p>
            </div>
            <div className="animate-fade-up-delay-2 bg-slate-900/60 rounded-xl border border-slate-800 p-5 transition-all duration-200 hover:-translate-y-0.5 hover:border-slate-700 hover:shadow-md hover:shadow-black/20">
              <div className="flex items-center gap-2 text-sm font-medium text-emerald-400 mb-2">
                <MessageSquareText className="h-4 w-4" />
                Advisory
              </div>
              <p className="text-3xl font-bold text-slate-100">{stats.advisory}</p>
            </div>
            <div className="animate-fade-up-delay-3 bg-slate-900/60 rounded-xl border border-slate-800 p-5 transition-all duration-200 hover:-translate-y-0.5 hover:border-slate-700 hover:shadow-md hover:shadow-black/20">
              <div className="flex items-center gap-2 text-sm font-medium text-slate-400 mb-2">
                <TrendingUp className="h-4 w-4" />
                Avg Confidence
              </div>
              <p className="text-3xl font-bold text-slate-100">
                {avgConfidence !== null ? `${avgConfidence}%` : "--"}
              </p>
            </div>
          </div>
        )}
      </section>

      {/* Recent Activity Section */}
      <section className="mx-auto max-w-7xl px-5 sm:px-8 mt-12">
        <div className="flex items-center gap-2 mb-6">
          <Clock className="h-5 w-5 text-slate-500" aria-hidden="true" />
          <h2 className="text-lg font-semibold text-slate-200">Recent Activity</h2>
        </div>
        {recordsLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="bg-slate-900/60 rounded-xl border border-slate-800 p-5 animate-pulse">
                <div className="flex items-center gap-3">
                  <div className="h-8 w-8 rounded-lg bg-slate-700" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-slate-700 rounded w-1/3" />
                    <div className="h-3 bg-slate-700 rounded w-1/4" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : recordsError ? (
          <div className="bg-slate-900/60 rounded-xl border border-slate-800 p-6 text-center">
            <p className="text-sm text-slate-500">Unable to load recent activity</p>
            <button
              onClick={fetchRecentRecords}
              className="mt-3 text-sm font-medium text-indigo-400 hover:text-indigo-300"
            >
              Try again
            </button>
          </div>
        ) : recentRecords.length === 0 ? (
          <div className="bg-slate-900/60 rounded-2xl border border-slate-800 p-8 text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-lg bg-slate-800 mb-4">
              <Clock className="h-6 w-6 text-slate-400" />
            </div>
            <h3 className="font-semibold text-slate-200 mb-1">No activity yet</h3>
            <p className="text-sm text-slate-400 mb-4">
              Start by running an audit, redaction, or asking a legal question.
            </p>
            <button
              onClick={() => onModeChange("AUDIT")}
              className="inline-flex items-center gap-2 rounded-lg bg-indigo-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-400"
            >
              Get Started
              <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {(["audit", "redaction", "advisory"] as const).map((type) => {
              const record = latestPerType[type];
              if (!record) return null;

              const RecordIcon = getModeIcon(record.mode);
              const borderColor = {
                blue: "border-l-indigo-500",
                amber: "border-l-amber-500",
                emerald: "border-l-emerald-500",
                slate: "border-l-slate-600",
              }[type === "audit" ? "blue" : type === "redaction" ? "amber" : "emerald"];

              return (
                <button
                  key={record.id}
                  onClick={() => onModeChange(record.mode?.toUpperCase() === "ADVISORY" ? "ADVISORY" : record.mode?.toUpperCase() === "REDACTION" ? "REDACTION" : "AUDIT")}
                  className={`w-full text-left bg-slate-900/60 rounded-xl border border-slate-800 border-l-4 ${borderColor} p-4 transition-all duration-200 hover:-translate-y-0.5 hover:bg-slate-800/40 hover:border-slate-700 hover:shadow-md hover:shadow-black/20`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${
                      type === "audit" ? "bg-indigo-500/15 text-indigo-400" :
                      type === "redaction" ? "bg-amber-500/15 text-amber-400" :
                      "bg-emerald-500/15 text-emerald-400"
                    }`}>
                      <RecordIcon className="h-4 w-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-200 truncate">
                        {record.filename || record.title || `${record.mode || "Record"} #${record.id}`}
                      </p>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {record.mode && `${record.mode} \u00B7 `}
                        {formatRelativeTime(record.timestamp)}
                        {record.confidence_score != null && ` \u00B7 ${Math.round(record.confidence_score * 100)}% confidence`}
                      </p>
                    </div>
                    <ArrowRight className="h-4 w-4 text-slate-600 flex-shrink-0" />
                  </div>
                </button>
              );
            })}
            {recentRecords.length > 0 && (
              <div className="text-center pt-2">
                <button
                  onClick={() => onModeChange("WORKSPACE")}
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-indigo-400 hover:text-indigo-300 transition"
                >
                  View all activity
                  <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </div>
            )}
          </div>
        )}
      </section>

      {/* Onboarding Tips Section */}
      <section className="mx-auto max-w-7xl px-5 sm:px-8 mt-12 pb-16">
        <div className="flex items-center gap-2 mb-6">
          <Lightbulb className="h-5 w-5 text-slate-500" aria-hidden="true" />
          <h2 className="text-lg font-semibold text-slate-200">Quick Start</h2>
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          {tips.map((tip, index) => {
            const TipIcon = tip.icon;
            const colors = colorConfig[tip.color];

            return (
              <button
                key={tip.title}
                onClick={tip.action}
                className="group text-left bg-slate-900/60 backdrop-blur rounded-xl border border-slate-800 p-5 transition-all duration-200 hover:-translate-y-0.5 hover:border-slate-700"
              >
                <div className={`inline-flex h-10 w-10 items-center justify-center rounded-lg ${colors.iconBg} mb-3`}>
                  <TipIcon className={`h-5 w-5 ${colors.iconText}`} />
                </div>
                <h3 className="text-sm font-semibold text-slate-200 mb-1">{tip.title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed mb-3">{tip.description}</p>
                <span className={`inline-flex items-center gap-1 text-sm font-medium ${colors.iconText} transition`}>
                  {tip.label}
                  <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
                </span>
              </button>
            );
          })}
        </div>
      </section>
    </div>
  );
}
