import { WifiOff, RefreshCw } from "lucide-react";
import { useConnection } from "../hooks/useConnection";

type OfflineIndicatorProps = {
  onRetry?: () => void;
  isRetrying?: boolean;
};

export function OfflineIndicator({ onRetry, isRetrying }: OfflineIndicatorProps) {
  const connectionState = useConnection();

  if (connectionState === "online") return null;

  const isOffline = connectionState === "offline";
  const isReconnecting = connectionState === "reconnecting";

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium bg-amber-500 text-white"
    >
      <WifiOff className="h-4 w-4" />
      {isOffline && (
        <>
          <span>No internet connection</span>
          <button
            type="button"
            onClick={onRetry}
            disabled={isRetrying}
            className="ml-2 inline-flex items-center gap-1 rounded bg-white/20 px-2 py-1 text-xs font-semibold hover:bg-white/30 disabled:opacity-50 transition-colors"
          >
            <RefreshCw className={`h-3 w-3 ${isRetrying ? "animate-spin" : ""}`} />
            Retry
          </button>
        </>
      )}
      {isReconnecting && <span>Reconnecting...</span>}
    </div>
  );
}