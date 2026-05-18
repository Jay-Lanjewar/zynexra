import type { AuditResponse } from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type ApiError = {
  code: "NETWORK_ERROR" | "SERVER_ERROR" | "PARSE_ERROR" | "FILE_TOO_LARGE" | "INVALID_FILE_TYPE" | "VALIDATION_ERROR" | "REQUEST_ERROR" | "TIMEOUT_ERROR" | "ENCRYPTED_PDF";
  message: string;
};

export function getApiBaseUrl(): string {
  return API_BASE_URL;
}

export async function auditContractFile(
  file: File,
  onProgress?: (progress: number) => void
): Promise<AuditResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("session_id", crypto.randomUUID());
  formData.append("mode", "AUDIT");
  formData.append("response_format", "json");

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
      const backendMessage = payload.detail || payload.legacy_text || payload.message || `Audit request failed with status ${response.status}`;
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
