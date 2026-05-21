import type { AppMode, AuditResponse, ChatMessage, RedactionOptions, ConfidenceLabel, ConfidenceMetadata } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type ApiError = {
  code: "NETWORK_ERROR" | "SERVER_ERROR" | "PARSE_ERROR" | "FILE_TOO_LARGE" | "INVALID_FILE_TYPE" | "VALIDATION_ERROR" | "REQUEST_ERROR" | "TIMEOUT_ERROR" | "ENCRYPTED_PDF";
  message: string;
};

export type HistoryRecord = {
  id: number;
  filename: string;
  timestamp: string;
  mode?: string;
  issue_count?: number;
  redaction_count?: number;
  title?: string;
  severity?: string;
  preview?: string;
  record_type?: "audit" | "redaction" | "advisory";
  issues?: Record<string, unknown>[];
  confidence_score?: number;
  confidence_label?: ConfidenceLabel;
  fallback_used?: boolean;
  metadata?: ConfidenceMetadata;
};

export type HistoryResponse = {
  success: boolean;
  records: HistoryRecord[];
  total: number;
  limit?: number;
  offset?: number;
  message?: string;
};

export type HistoryFilter = {
  recordType?: "all" | "audit" | "redaction" | "advisory";
  filename?: string;
  mode?: string;
  severity?: string;
  startDate?: string;
  endDate?: string;
  limit?: number;
  offset?: number;
};

export type HistorySummary = {
  success: boolean;
  stats: {
    audits: number;
    redactions: number;
    advisory: number;
    total: number;
  };
  message?: string;
};

export function getApiBaseUrl(): string {
  return API_BASE_URL;
}

export async function auditContractFile(
  file: File,
  mode: Exclude<AppMode, "ADVISORY"> = "AUDIT",
  redactionOptions?: RedactionOptions,
  onProgress?: (progress: number) => void
): Promise<AuditResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("session_id", crypto.randomUUID());
  formData.append("mode", mode);
  formData.append("response_format", "json");
  if (mode === "REDACTION" && redactionOptions) {
    formData.append("redact_emails", String(redactionOptions.emails));
    formData.append("redact_phones", String(redactionOptions.phones));
    formData.append("redact_names", String(redactionOptions.names));
    formData.append("redact_addresses", String(redactionOptions.addresses));
    formData.append("redact_companies", String(redactionOptions.companies));
  }

  try {
    if (onProgress) onProgress(10);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000);

    const response = await fetch(`${API_BASE_URL}/ask_file`, {
      method: "POST",
      body: formData,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (onProgress) onProgress(80);

    console.log("[API] HTTP Status:", response.status);
    console.log("[API] Response headers:", response.headers.get("content-type"));

    const contentType = response.headers.get("content-type") ?? "";
    const payload = contentType.includes("application/json")
      ? await response.json()
      : { success: false, legacy_text: await response.text() };

    console.log("[API] Parsed response:", payload);

    if (!response.ok || payload.success === false) {
      const backendMessage = payload.detail || payload.legacy_text || payload.message || `Request failed with status ${response.status}`;
      console.log("[API] Backend error message:", backendMessage);

      if (response.status === 413) {
        throw { code: "FILE_TOO_LARGE", message: "File exceeds maximum size limit." } as ApiError;
      }

      if (response.status === 400) {
        const lowerMessage = backendMessage.toLowerCase();
        if (lowerMessage.includes("encrypt") || lowerMessage.includes("password") || lowerMessage.includes("protected") || lowerMessage.includes("decrypt")) {
          throw { code: "ENCRYPTED_PDF", message: "This PDF appears to be encrypted, password protected, or unsupported." } as ApiError;
        }
        throw { code: "VALIDATION_ERROR", message: backendMessage } as ApiError;
      }

      if (response.status === 422) {
        throw { code: "REQUEST_ERROR", message: backendMessage } as ApiError;
      }

      if (response.status >= 500) {
        throw { code: "SERVER_ERROR", message: backendMessage } as ApiError;
      }

      throw { code: "SERVER_ERROR", message: backendMessage } as ApiError;
    }

    if (onProgress) onProgress(100);

    return payload as AuditResponse;
  } catch (error) {
    console.log("[API] Fetch/Network exception:", error);

    if ((error as ApiError).code) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes("fetch")) {
      throw { code: "NETWORK_ERROR", message: "Unable to connect to the backend. Please verify the server is running." } as ApiError;
    }

    if (error instanceof Error) {
      if (error.name === "AbortError") {
        throw { code: "TIMEOUT_ERROR", message: "The request timed out. The backend may be taking too long to process the file." } as ApiError;
      }
      if (error.message.includes("network") || error.message.includes("connection")) {
        throw { code: "NETWORK_ERROR", message: "Unable to connect to the backend. Please verify the server is running." } as ApiError;
      }
      throw { code: "SERVER_ERROR", message: error.message } as ApiError;
    }

    throw { code: "SERVER_ERROR", message: "An unexpected error occurred." } as ApiError;
  }
}

export async function askAdvisoryQuestion(
  question: string,
  sessionId: string,
  history: ChatMessage[] = [],
  onProgress?: (progress: number) => void
): Promise<AuditResponse> {
  try {
    if (onProgress) onProgress(20);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 120000);

    const contextMessages = history.slice(-8);
    const taskAnchor = contextMessages.length > 0
      ? [
          "FRONTEND CONVERSATION CONTEXT:",
          "Use this only to preserve continuity if server-side session history is unavailable.",
          ...contextMessages.map((message) => `${message.role.toUpperCase()}: ${message.content}`),
        ].join("\n")
      : undefined;

    const response = await fetch(`${API_BASE_URL}/ask?response_format=json`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question,
        session_id: sessionId,
        mode: "ADVISORY",
        response_format: "json",
        task_anchor: taskAnchor,
      }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (onProgress) onProgress(80);

    const contentType = response.headers.get("content-type") ?? "";
    const payload = contentType.includes("application/json")
      ? await response.json()
      : { success: false, legacy_text: await response.text() };

    if (!response.ok || payload.success === false) {
      const backendMessage = payload.detail || payload.legacy_text || payload.message || `Request failed with status ${response.status}`;

      if (response.status === 400) {
        throw { code: "VALIDATION_ERROR", message: backendMessage } as ApiError;
      }

      if (response.status === 422) {
        throw { code: "REQUEST_ERROR", message: backendMessage } as ApiError;
      }

      if (response.status >= 500) {
        throw { code: "SERVER_ERROR", message: backendMessage } as ApiError;
      }

      throw { code: "SERVER_ERROR", message: backendMessage } as ApiError;
    }

    if (onProgress) onProgress(100);

    return payload as AuditResponse;
  } catch (error) {
    console.log("[API] Advisory exception:", error);

    if ((error as ApiError).code) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes("fetch")) {
      throw { code: "NETWORK_ERROR", message: "Unable to connect to the backend. Please verify the server is running." } as ApiError;
    }

    if (error instanceof Error) {
      if (error.name === "AbortError") {
        throw { code: "TIMEOUT_ERROR", message: "The request timed out. The backend may be taking too long to respond." } as ApiError;
      }
      throw { code: "SERVER_ERROR", message: error.message } as ApiError;
    }

    throw { code: "SERVER_ERROR", message: "An unexpected error occurred." } as ApiError;
  }
}

export function validateFile(file: File): ApiError | null {
  const MAX_SIZE_MB = 10;
  const allowedTypes = ["application/pdf", "text/plain", "application/msword"];
  const allowedExtensions = [".pdf", ".txt", ".doc"];

  if (file.size > MAX_SIZE_MB * 1024 * 1024) {
    return { code: "FILE_TOO_LARGE", message: `File exceeds maximum size of ${MAX_SIZE_MB}MB.` };
  }

  const hasAllowedType = allowedTypes.includes(file.type);
  const hasAllowedExtension = allowedExtensions.some(ext => file.name.toLowerCase().endsWith(ext));

  if (!hasAllowedType && !hasAllowedExtension) {
    return { code: "INVALID_FILE_TYPE", message: "Only PDF, TXT, and DOC files are supported." };
  }

  return null;
}

export async function getHistoryRecords(filter: HistoryFilter = {}): Promise<HistoryResponse> {
  try {
    const params = new URLSearchParams();
    
    if (filter.recordType) params.append("record_type", filter.recordType);
    if (filter.limit) params.append("limit", String(filter.limit));
    if (filter.offset) params.append("offset", String(filter.offset));
    if (filter.filename) params.append("filename", filter.filename);
    if (filter.mode) params.append("mode", filter.mode);
    if (filter.severity) params.append("severity", filter.severity);
    if (filter.startDate) params.append("start_date", filter.startDate);
    if (filter.endDate) params.append("end_date", filter.endDate);

    const response = await fetch(`${API_BASE_URL}/history?${params.toString()}`);
    
    if (!response.ok) {
      throw { code: "SERVER_ERROR", message: `Failed to fetch history: ${response.status}` } as ApiError;
    }

    const data = await response.json() as HistoryResponse;
    return data;
  } catch (error) {
    console.error("[API] History fetch error:", error);
    
    if ((error as ApiError).code) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes("fetch")) {
      throw { code: "NETWORK_ERROR", message: "Unable to connect to the backend. Please verify the server is running." } as ApiError;
    }

    throw { code: "SERVER_ERROR", message: "Failed to fetch history records." } as ApiError;
  }
}

export async function getRecordDetail(
  recordId: number,
  recordType: "audit" | "redaction" | "advisory" = "audit"
): Promise<{ success: boolean; record: HistoryRecord; response?: AuditResponse }> {
  try {
    const response = await fetch(`${API_BASE_URL}/history/${recordId}?record_type=${recordType}`);
    
    if (!response.ok) {
      if (response.status === 404) {
        throw { code: "SERVER_ERROR", message: "Record not found." } as ApiError;
      }
      throw { code: "SERVER_ERROR", message: `Failed to fetch record: ${response.status}` } as ApiError;
    }

    const data = await response.json() as { success: boolean; record: HistoryRecord; response?: AuditResponse };
    return data;
  } catch (error) {
    console.error("[API] Record detail fetch error:", error);
    
    if ((error as ApiError).code) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes("fetch")) {
      throw { code: "NETWORK_ERROR", message: "Unable to connect to the backend." } as ApiError;
    }

    throw { code: "SERVER_ERROR", message: "Failed to fetch record details." } as ApiError;
  }
}

export async function deleteRecord(
  recordId: number,
  recordType: "audit" | "redaction" | "advisory" = "audit"
): Promise<{ success: boolean; message: string }> {
  try {
    const response = await fetch(`${API_BASE_URL}/history/${recordId}?record_type=${recordType}`, {
      method: "DELETE",
    });
    
    if (!response.ok) {
      if (response.status === 404) {
        throw { code: "SERVER_ERROR", message: "Record not found." } as ApiError;
      }
      throw { code: "SERVER_ERROR", message: `Failed to delete record: ${response.status}` } as ApiError;
    }

    const data = await response.json() as { success: boolean; message: string };
    return data;
  } catch (error) {
    console.error("[API] Record delete error:", error);
    
    if ((error as ApiError).code) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes("fetch")) {
      throw { code: "NETWORK_ERROR", message: "Unable to connect to the backend." } as ApiError;
    }

    throw { code: "SERVER_ERROR", message: "Failed to delete record." } as ApiError;
  }
}

export async function getHistorySummary(): Promise<HistorySummary> {
  try {
    const response = await fetch(`${API_BASE_URL}/history/stats/summary`);
    
    if (!response.ok) {
      throw { code: "SERVER_ERROR", message: `Failed to fetch summary: ${response.status}` } as ApiError;
    }

    const data = await response.json() as HistorySummary;
    return data;
  } catch (error) {
    console.error("[API] Summary fetch error:", error);
    
    if ((error as ApiError).code) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes("fetch")) {
      throw { code: "NETWORK_ERROR", message: "Unable to connect to the backend." } as ApiError;
    }

    throw { code: "SERVER_ERROR", message: "Failed to fetch summary." } as ApiError;
  }
}
