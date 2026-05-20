import { AlertTriangle, WifiOff, Server, FileWarning, HelpCircle, ArrowLeft, RefreshCw } from "lucide-react";
import type { ApiError } from "../api";

type ErrorStateProps = {
  error: ApiError | string;
  onReset?: () => void;
  onRetry?: () => void;
  isRetrying?: boolean;
  retryAttempt?: number;
};

export function ErrorState({ error, onReset }: ErrorStateProps) {
  const getErrorInfo = (err: ApiError | string) => {
    if (typeof err === "string") {
      return {
        icon: HelpCircle,
        title: "Unknown Error",
        message: err,
        variant: "default" as const,
      };
    }

    switch (err.code) {
      case "NETWORK_ERROR":
        return {
          icon: WifiOff,
          title: "Backend Unavailable",
          message: "Unable to connect to the server. Please verify the backend is running and try again.",
          variant: "warning" as const,
        };
      case "SERVER_ERROR":
        return {
          icon: Server,
          title: "Server Error",
          message: err.message || "The server encountered an error processing your request.",
          variant: "error" as const,
        };
      case "VALIDATION_ERROR":
        return {
          icon: FileWarning,
          title: "Validation Error",
          message: err.message || "The request could not be processed due to invalid input.",
          variant: "warning" as const,
        };
      case "REQUEST_ERROR":
        return {
          icon: FileWarning,
          title: "Request Error",
          message: err.message || "The request could not be processed.",
          variant: "warning" as const,
        };
      case "TIMEOUT_ERROR":
        return {
          icon: Server,
          title: "Request Timeout",
          message: err.message || "The request timed out. Please try again.",
          variant: "warning" as const,
        };
      case "ENCRYPTED_PDF":
        return {
          icon: FileWarning,
          title: "Unsupported PDF",
          message: "This PDF appears to be encrypted, password protected, or unsupported.",
          variant: "warning" as const,
        };
      case "PARSE_ERROR":
        return {
          icon: FileWarning,
          title: "Parsing Failed",
          message: "The contract could not be parsed. Please ensure the file is a valid PDF, TXT, or DOC.",
          variant: "warning" as const,
        };
      case "FILE_TOO_LARGE":
        return {
          icon: FileWarning,
          title: "File Too Large",
          message: err.message || "The file exceeds the maximum allowed size.",
          variant: "warning" as const,
        };
      case "INVALID_FILE_TYPE":
        return {
          icon: FileWarning,
          title: "Invalid File Type",
          message: err.message || "Only PDF, TXT, and DOC files are supported.",
          variant: "warning" as const,
        };
      default:
        return {
          icon: AlertTriangle,
          title: "Error",
          message: err.message || "An unexpected error occurred.",
          variant: "default" as const,
        };
    }
  };

  const { icon: Icon, title, message, variant } = getErrorInfo(error);

  const bgColors = {
    default: "bg-slate-50 border-slate-200",
    warning: "bg-amber-50 border-amber-200",
    error: "bg-red-50 border-red-200",
  };

  const iconColors = {
    default: "bg-slate-100 text-slate-600",
    warning: "bg-amber-100 text-amber-600",
    error: "bg-red-100 text-red-600",
  };

  const titleColors = {
    default: "text-slate-900",
    warning: "text-amber-900",
    error: "text-red-900",
  };

  const messageColors = {
    default: "text-slate-600",
    warning: "text-amber-700",
    error: "text-red-700",
  };

  return (
    <div className={`flex flex-col items-center rounded-lg border p-8 text-center ${bgColors[variant]}`}>
      <div className={`flex h-16 w-16 items-center justify-center rounded-full ${iconColors[variant]}`}>
        <Icon className="h-8 w-8" />
      </div>
      <h3 className={`mt-4 text-lg font-semibold ${titleColors[variant]}`}>{title}</h3>
      <p className={`mt-2 max-w-md text-sm ${messageColors[variant]}`}>{message}</p>

      {(onReset || onRetry) && (
        <div className="mt-6 flex gap-3 flex-wrap justify-center">
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              disabled={isRetrying}
              className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:bg-slate-400 transition-colors"
            >
              <RefreshCw className={`h-4 w-4 ${isRetrying ? "animate-spin" : ""}`} />
              {isRetrying ? "Retrying..." : "Retry"}
            </button>
          )}
          {onReset && (
            <button
              type="button"
              onClick={onReset}
              className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
            >
              <ArrowLeft className="h-4 w-4" />
              Start Over
            </button>
          )}
        </div>
      )}
    </div>
  );
}