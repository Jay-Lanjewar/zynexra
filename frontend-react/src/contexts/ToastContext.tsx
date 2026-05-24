import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import { X, CheckCircle, AlertTriangle, AlertCircle, Loader2 } from "lucide-react";

export type ToastType = "success" | "error" | "warning" | "loading";

export type Toast = {
  id: string;
  type: ToastType;
  message: string;
  duration?: number;
};

type ToastContextType = {
  toasts: Toast[];
  addToast: (type: ToastType, message: string, duration?: number) => string;
  removeToast: (id: string) => void;
  clearToasts: () => void;
};

const ToastContext = createContext<ToastContextType | null>(null);

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((type: ToastType, message: string, duration = 5000) => {
    const id = crypto.randomUUID();
    setToasts((prev) => [...prev, { id, type, message, duration }]);
    
    if (type !== "loading" && duration > 0) {
      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, duration);
    }
    
    return id;
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const clearToasts = useCallback(() => {
    setToasts([]);
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast, clearToasts }}>
      {children}
    </ToastContext.Provider>
  );
}

const toastIcons = {
  success: CheckCircle,
  error: AlertCircle,
  warning: AlertTriangle,
  loading: Loader2,
};

const toastStyles = {
  success: "bg-slate-800 border-emerald-500/30 text-emerald-300 shadow-lg shadow-black/30",
  error: "bg-slate-800 border-red-500/30 text-red-300 shadow-lg shadow-black/30",
  warning: "bg-slate-800 border-amber-500/30 text-amber-300 shadow-lg shadow-black/30",
  loading: "bg-slate-800 border-indigo-500/30 text-indigo-300 shadow-lg shadow-black/30",
};

const iconStyles = {
  success: "text-emerald-400",
  error: "text-red-400",
  warning: "text-amber-400",
  loading: "text-indigo-400",
};

export function ToastContainer() {
  const { toasts, removeToast } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm"
      role="region"
      aria-label="Notifications"
    >
      {toasts.map((toast) => {
        const Icon = toastIcons[toast.type];
        return (
          <div
            key={toast.id}
            role="alert"
            aria-live={toast.type === "error" ? "assertive" : "polite"}
            className={`flex items-start gap-3 rounded-lg border px-4 py-3 shadow-lg animate-slide-in backdrop-blur ${toastStyles[toast.type]}`}
          >
            <Icon className={`h-5 w-5 shrink-0 mt-0.5 ${iconStyles[toast.type]} ${toast.type === "loading" ? "animate-spin" : ""}`} />
            <p className="flex-1 text-sm font-medium">{toast.message}</p>
            <button
              type="button"
              onClick={() => removeToast(toast.id)}
              className="shrink-0 p-1 rounded hover:bg-white/5 transition-colors"
              aria-label="Dismiss notification"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
