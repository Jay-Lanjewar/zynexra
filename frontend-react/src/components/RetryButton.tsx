import { RefreshCw, AlertCircle } from "lucide-react";

type RetryButtonProps = {
  onRetry: () => void;
  isRetrying?: boolean;
  attempt?: number;
  maxAttempts?: number;
  label?: string;
  className?: string;
};

export function RetryButton({
  onRetry,
  isRetrying = false,
  attempt = 0,
  maxAttempts = 3,
  label = "Try Again",
  className = "",
}: RetryButtonProps) {
  const canRetry = attempt < maxAttempts;

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <button
        type="button"
        onClick={onRetry}
        disabled={isRetrying || !canRetry}
        className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-500 text-white rounded-lg font-medium text-sm hover:bg-indigo-400 disabled:bg-slate-700 disabled:text-slate-500 disabled:cursor-not-allowed transition-colors"
        aria-label={canRetry ? `${label} (attempt ${attempt + 1} of ${maxAttempts})` : "Max attempts reached"}
      >
        <RefreshCw className={`h-4 w-4 ${isRetrying ? "animate-spin" : ""}`} />
        {isRetrying ? "Retrying..." : label}
      </button>
      {attempt > 0 && (
        <span className="text-sm text-slate-500">
          Attempt {attempt} of {maxAttempts}
        </span>
      )}
    </div>
  );
}

export function ErrorWithRetry({
  message,
  onRetry,
  isRetrying,
  attempt,
  maxAttempts = 3,
}: {
  message: string;
  onRetry: () => void;
  isRetrying?: boolean;
  attempt?: number;
  maxAttempts?: number;
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-red-500/20 bg-red-500/5 p-6 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-500/10 mb-4">
        <AlertCircle className="h-6 w-6 text-red-400" />
      </div>
      <p className="text-sm text-red-300 mb-4 max-w-sm">{message}</p>
      <RetryButton
        onRetry={onRetry}
        isRetrying={isRetrying}
        attempt={attempt}
        maxAttempts={maxAttempts}
      />
    </div>
  );
}
