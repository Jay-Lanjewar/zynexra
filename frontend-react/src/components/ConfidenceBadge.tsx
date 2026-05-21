import type { ConfidenceLabel } from "../types";

type ConfidenceBadgeProps = {
  confidence?: number;
  label?: ConfidenceLabel;
  showPercentage?: boolean;
  size?: "sm" | "md";
};

const labelConfig: Record<ConfidenceLabel, { bg: string; text: string; dot: string; tooltip: string }> = {
  HIGH: {
    bg: "bg-emerald-100",
    text: "text-emerald-700",
    dot: "bg-emerald-500",
    tooltip: "High confidence: Strong structured output with complete analysis",
  },
  MEDIUM: {
    bg: "bg-amber-100",
    text: "text-amber-700",
    dot: "bg-amber-500",
    tooltip: "Medium confidence: Partial analysis or fallback parsing used",
  },
  LOW: {
    bg: "bg-red-100",
    text: "text-red-700",
    dot: "bg-red-500",
    tooltip: "Low confidence: Weak response quality, review results carefully",
  },
};

export function ConfidenceBadge({ confidence, label, showPercentage = true, size = "sm" }: ConfidenceBadgeProps) {
  const resolvedLabel = label ?? (confidence !== undefined ? deriveLabel(confidence) : undefined);
  if (!resolvedLabel) return null;

  const config = labelConfig[resolvedLabel];
  const percentage = confidence !== undefined ? Math.round(confidence * 100) : null;
  const sizeClasses = size === "md" ? "px-2.5 py-1 text-xs" : "px-2 py-0.5 text-[11px]";

  return (
    <span
      className={`group relative inline-flex items-center gap-1.5 rounded font-semibold ${config.bg} ${config.text} ${sizeClasses}`}
      title={config.tooltip}
    >
      <span className={`h-2 w-2 rounded-full ${config.dot} opacity-70`}></span>
      {showPercentage && percentage !== null ? `${percentage}%` : resolvedLabel}
      <span className="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden whitespace-nowrap rounded bg-slate-900 px-2 py-1 text-xs font-normal text-white opacity-0 transition-opacity group-hover:block group-hover:opacity-100">
        {config.tooltip}
      </span>
    </span>
  );
}

function deriveLabel(score: number): ConfidenceLabel {
  if (score >= 0.75) return "HIGH";
  if (score >= 0.45) return "MEDIUM";
  return "LOW";
}
