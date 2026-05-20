interface ConfidenceBadgeProps {
  confidence: number;
  showPercentage?: boolean;
}

export function ConfidenceBadge({ confidence, showPercentage = true }: ConfidenceBadgeProps) {
  const percentage = Math.round(confidence * 100);
  
  let colorClass = "bg-red-100 text-red-700";
  if (percentage >= 85) {
    colorClass = "bg-emerald-100 text-emerald-700";
  } else if (percentage >= 75) {
    colorClass = "bg-amber-100 text-amber-700";
  } else if (percentage >= 65) {
    colorClass = "bg-orange-100 text-orange-700";
  }

  return (
    <span className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-xs font-semibold ${colorClass}`}>
      <span className="h-2 w-2 rounded-full bg-current opacity-60"></span>
      {showPercentage ? `${percentage}%` : `${confidence.toFixed(2)}`}
    </span>
  );
}
