import { useState, useEffect, useCallback } from "react";

export type ConnectionState = "online" | "offline" | "reconnecting";

export function useConnection() {
  const [connectionState, setConnectionState] = useState<ConnectionState>(() => {
    if (typeof window === "undefined") return "online";
    return navigator.onLine ? "online" : "offline";
  });

  useEffect(() => {
    const handleOnline = () => {
      setConnectionState("reconnecting");
      setTimeout(() => setConnectionState("online"), 1000);
    };

    const handleOffline = () => {
      setConnectionState("offline");
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  return connectionState;
}

export function useRetry<T>(
  fetchFn: () => Promise<T>,
  options: {
    onSuccess?: (data: T) => void;
    onError?: (error: Error) => void;
    maxRetries?: number;
    retryDelay?: number;
  } = {}
) {
  const [isRetrying, setIsRetrying] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const { onSuccess, onError, maxRetries = 3, retryDelay = 1000 } = options;

  const retry = useCallback(async () => {
    setIsRetrying(true);
    setAttempt((prev) => prev + 1);

    let lastError: Error | null = null;

    for (let i = 0; i < maxRetries; i++) {
      try {
        const data = await fetchFn();
        onSuccess?.(data);
        setIsRetrying(false);
        return data;
      } catch (error) {
        lastError = error as Error;
        if (i < maxRetries - 1) {
          await new Promise((resolve) => setTimeout(resolve, retryDelay * (i + 1)));
        }
      }
    }

    if (lastError) {
      onError?.(lastError);
    }

    setIsRetrying(false);
    throw lastError;
  }, [fetchFn, maxRetries, retryDelay, onSuccess, onError]);

  return { retry, isRetrying, attempt, reset: () => setAttempt(0) };
}