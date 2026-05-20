type LogLevel = "debug" | "info" | "warn" | "error";

interface LogEntry {
  level: LogLevel;
  message: string;
  timestamp: string;
  data?: Record<string, unknown>;
}

const MAX_LOGS = 100;
const logs: LogEntry[] = [];

const formatTimestamp = () => new Date().toISOString();

const shouldLog = (level: LogLevel): boolean => {
  if (import.meta.env.DEV) return true;
  return level === "error" || level === "warn";
};

export const logger = {
  debug(message: string, data?: Record<string, unknown>) {
    if (!shouldLog("debug")) return;
    const entry: LogEntry = { level: "debug", message, timestamp: formatTimestamp(), data };
    logs.push(entry);
    if (logs.length > MAX_LOGS) logs.shift();
    console.debug(`[DEBUG] ${message}`, data ?? "");
  },

  info(message: string, data?: Record<string, unknown>) {
    if (!shouldLog("info")) return;
    const entry: LogEntry = { level: "info", message, timestamp: formatTimestamp(), data };
    logs.push(entry);
    if (logs.length > MAX_LOGS) logs.shift();
    console.info(`[INFO] ${message}`, data ?? "");
  },

  warn(message: string, data?: Record<string, unknown>) {
    if (!shouldLog("warn")) return;
    const entry: LogEntry = { level: "warn", message, timestamp: formatTimestamp(), data };
    logs.push(entry);
    if (logs.length > MAX_LOGS) logs.shift();
    console.warn(`[WARN] ${message}`, data ?? "");
  },

  error(message: string, data?: Record<string, unknown>) {
    const entry: LogEntry = { level: "error", message, timestamp: formatTimestamp(), data };
    logs.push(entry);
    if (logs.length > MAX_LOGS) logs.shift();
    console.error(`[ERROR] ${message}`, data ?? "");
  },

  getLogs(): LogEntry[] {
    return [...logs];
  },

  clearLogs() {
    logs.length = 0;
  },
};

export const logApiError = (endpoint: string, error: unknown, context?: Record<string, unknown>) => {
  const errorObj = error as Error;
  logger.error(`API Error: ${endpoint}`, {
    message: errorObj.message,
    name: errorObj.name,
    ...context,
  });
};

export const logRenderError = (componentName: string, error: Error) => {
  logger.error(`Render error in ${componentName}`, {
    message: error.message,
    stack: error.stack,
  });
};

export const logInvalidPayload = (operation: string, payload: unknown, reason: string) => {
  logger.warn(`Invalid payload for ${operation}`, { payload, reason });
};