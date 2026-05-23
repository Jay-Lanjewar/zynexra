import { useEffect, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Circle,
  FileOutput,
  FileText,
  GitBranch,
  LineChart,
  Loader2,
  Search,
  ShieldCheck,
} from "lucide-react";
import type { AppMode } from "../types";

type Stage = {
  id: string;
  label: string;
};

const auditStages: Stage[] = [
  { id: "extracting", label: "Extracting document text" },
  { id: "detecting", label: "Detecting legal structure" },
  { id: "analyzing", label: "Analyzing risk clauses" },
  { id: "checking", label: "Checking contradictions" },
  { id: "evaluating", label: "Evaluating confidence" },
  { id: "generating", label: "Generating final report" },
];

const redactionStages: Stage[] = [
  { id: "extracting", label: "Extracting document text" },
  { id: "scanning", label: "Scanning for personal data" },
  { id: "detecting", label: "Detecting entity types" },
  { id: "validating", label: "Validating redactions" },
  { id: "evaluating", label: "Evaluating confidence" },
  { id: "generating", label: "Generating redacted output" },
];

const statusMessages = [
  "Reviewing indemnification language...",
  "Checking confidentiality obligations...",
  "Detecting structural inconsistencies...",
  "Validating document quality...",
  "Cross-referencing jurisdiction clauses...",
  "Analyzing liability limitations...",
  "Verifying compliance requirements...",
  "Scanning for ambiguous language...",
  "Evaluating risk exposure across sections...",
  "Reviewing termination conditions...",
  "Checking warranty disclaimers...",
  "Analyzing dispute resolution clauses...",
];

const stageIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  extracting: FileText,
  detecting: Search,
  analyzing: AlertTriangle,
  scanning: Search,
  checking: GitBranch,
  validating: ShieldCheck,
  evaluating: LineChart,
  generating: FileOutput,
};

type AuditLoadingWorkflowProps = {
  filename: string;
  mode: AppMode;
};

export function AuditLoadingWorkflow({ filename, mode }: AuditLoadingWorkflowProps) {
  const [activeStageIndex, setActiveStageIndex] = useState(0);
  const [statusIndex, setStatusIndex] = useState(0);

  const stages = mode === "AUDIT" ? auditStages : redactionStages;

  useEffect(() => {
    const durations = [1800, 2200, 2500, 2500, 2000];
    const jitter = () => Math.random() * 300 - 150;

    let cumulativeDelay = durations[0] + jitter();
    const timeouts: ReturnType<typeof setTimeout>[] = [];

    for (let i = 1; i < durations.length; i++) {
      const stageIndex = i;
      timeouts.push(setTimeout(() => {
        setActiveStageIndex(stageIndex);
      }, cumulativeDelay));
      cumulativeDelay += durations[i] + jitter();
    }

    timeouts.push(setTimeout(() => {
      setActiveStageIndex(durations.length);
    }, cumulativeDelay));

    return () => {
      timeouts.forEach(clearTimeout);
    };
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setStatusIndex((prev) => (prev + 1) % statusMessages.length);
    }, 2800);
    return () => clearInterval(interval);
  }, []);

  const progressPercent = (activeStageIndex / (stages.length - 1)) * 100;

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-b from-slate-900 via-slate-950 to-black">
      {/* Animated progress bar */}
      <div className="h-[3px] w-full bg-slate-800">
        <div
          className="h-full transition-all duration-700 ease-out"
          style={{
            width: `${Math.min(progressPercent, 100)}%`,
            background: "linear-gradient(90deg, #6366f1, #10b981)",
          }}
        />
      </div>

      {/* Header */}
      <header className="border-b border-slate-800/50 px-6 py-4">
        <div className="mx-auto flex max-w-lg items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-500/10">
            <ShieldCheck className="h-5 w-5 text-indigo-400" />
          </div>
          <div className="min-w-0 flex-1">
            <h1 className="text-sm font-semibold text-slate-100">
              {mode === "AUDIT" ? "Contract Audit" : "Document Redaction"}
            </h1>
            <p className="truncate text-xs text-slate-500">{filename}</p>
          </div>
          <span className="shrink-0 rounded-full bg-indigo-500/10 px-3 py-1 text-[11px] font-medium text-indigo-400">
            Processing
          </span>
        </div>
      </header>

      {/* Main stages */}
      <main className="flex flex-1 items-center justify-center px-6 py-12">
        <div className="w-full max-w-md" role="list" aria-label="Processing stages">
          {stages.map((stage, index) => {
            const isActive = index === activeStageIndex;
            const isCompleted = index < activeStageIndex;
            const StageIcon = stageIcons[stage.id] || FileText;
            const isLast = index === stages.length - 1;

            return (
              <div key={stage.id} role="listitem">
                <div className="flex items-start gap-4 py-2">
                  {/* Stage indicator */}
                  <div className="relative flex h-8 w-8 shrink-0 items-center justify-center">
                    {isCompleted ? (
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-500/10">
                        <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                      </div>
                    ) : isActive ? (
                      <div className="pulse-glow flex h-8 w-8 items-center justify-center rounded-full bg-indigo-500/15">
                        <Loader2 className="h-5 w-5 animate-spin text-indigo-400" />
                      </div>
                    ) : (
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-800/50">
                        <Circle className="h-4 w-4 text-slate-600" />
                      </div>
                    )}
                  </div>

                  {/* Stage content */}
                  <div className="min-w-0 flex-1 pt-1.5">
                    <p
                      className={`text-sm font-medium transition-all duration-300 ${
                        isActive
                          ? "text-slate-100"
                          : isCompleted
                            ? "text-slate-400"
                            : "text-slate-600"
                      }`}
                    >
                      {stage.label}
                    </p>
                    {isActive && (
                      <p
                        key={statusIndex}
                        className="mt-1 animate-fade-in text-xs text-slate-500"
                        aria-live="polite"
                      >
                        {statusMessages[statusIndex]}
                      </p>
                    )}
                  </div>
                </div>

                {/* Connector line between stages */}
                {!isLast && (
                  <div className="ml-4 h-7 w-[2px] bg-slate-800">
                    <div
                      className={`w-full transition-all duration-700 ease-out ${
                        activeStageIndex > index
                          ? "h-full bg-emerald-500/40"
                          : activeStageIndex === index
                            ? "h-1/2 bg-indigo-500/40"
                            : "h-0"
                      }`}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/50 px-6 py-4">
        <div className="mx-auto flex max-w-lg items-center justify-between">
          <div className="flex items-center gap-2 text-xs text-slate-600">
            <div className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-emerald-500/70" />
            Local inference
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-600">
            <ShieldCheck className="h-3.5 w-3.5" />
            Secure processing
          </div>
        </div>
      </footer>
    </div>
  );
}
