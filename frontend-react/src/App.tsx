import { useState, useEffect, useCallback } from "react";
import { askAdvisoryQuestion, auditContractFile, type ApiError, getHistoryRecords } from "./api";
import { AdvisoryChatPage } from "./pages/AdvisoryChatPage";
import { AuditResultsPage } from "./pages/AuditResultsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { RedactionResultsPage } from "./pages/RedactionResultsPage";
import { UploadContractPage } from "./pages/UploadContractPage";
import { WorkspacePage } from "./pages/WorkspacePage";
import { TopNavigation } from "./components/TopNavigation";
import { ToastProvider, useToast } from "./contexts/ToastContext";
import { AuditLoadingWorkflow } from "./components/AuditLoadingWorkflow";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { OfflineIndicator } from "./components/OfflineIndicator";
import { RetryButton } from "./components/RetryButton";
import { useConnection } from "./hooks/useConnection";
import { persistence, type PersistedAppState, type PersistedAdvisory } from "./utils/persistence";
import { logger, logApiError } from "./utils/logger";
import type { AppMode, AuditResponse, ChatMessage, RedactionOptions, HistoryRecord } from "./types";

type AppState = AppMode | "WORKSPACE" | "DASHBOARD";

function AppContent() {
  const [appState, setAppState] = useState<AppState>("DASHBOARD");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [result, setResult] = useState<AuditResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<ApiError | null>(null);
  const [selectedMode, setSelectedMode] = useState<AppMode>("AUDIT");
  const [redactionOptions, setRedactionOptions] = useState<RedactionOptions>({
    emails: true,
    phones: true,
    names: true,
    addresses: true,
    companies: true,
  });
  const [advisorySessionId, setAdvisorySessionId] = useState(() => crypto.randomUUID());
  const [advisoryInput, setAdvisoryInput] = useState("");
  const [advisoryMessages, setAdvisoryMessages] = useState<ChatMessage[]>([]);
  const [advisoryError, setAdvisoryError] = useState<ApiError | null>(null);
  const [isAdvisoryLoading, setIsAdvisoryLoading] = useState(false);
  const [retryAttempt, setRetryAttempt] = useState(0);
  const [historyRetryAttempt, setHistoryRetryAttempt] = useState(0);
  const [isTakingLong, setIsTakingLong] = useState(false);
  const { addToast } = useToast();
  const connectionState = useConnection();

  useEffect(() => {
    const savedState = persistence.loadAppState();
    if (savedState) {
      setAppState(savedState.mode);
      setSelectedMode(savedState.selectedMode);
      setRedactionOptions(savedState.redactionOptions);
    }
  }, []);

  useEffect(() => {
    persistence.saveAppState({
      mode: appState,
      selectedMode,
      redactionOptions,
    });
  }, [appState, selectedMode, redactionOptions]);

  useEffect(() => {
    if (appState === "ADVISORY") {
      const savedAdvisory = persistence.loadAdvisoryState();
      if (savedAdvisory) {
        setAdvisorySessionId(savedAdvisory.sessionId);
        setAdvisoryMessages(savedAdvisory.messages);
      }
    }
  }, [appState]);

  useEffect(() => {
    if (appState === "ADVISORY" && advisoryMessages.length > 0) {
      persistence.saveAdvisoryState({
        sessionId: advisorySessionId,
        messages: advisoryMessages,
      });
    }
  }, [advisorySessionId, advisoryMessages, appState]);

  async function handleSubmit() {
    if (!selectedFile) {
      setError("Select a contract file first.");
      return;
    }

    setIsLoading(true);
    setUploadProgress(0);
    setError(null);
    setApiError(null);
    setRetryAttempt(0);
    setIsTakingLong(false);

    const longTimer = setTimeout(() => {
      setIsTakingLong(true);
      addToast("warning", "Still analyzing your document. Complex files may take longer — your data remains private.");
    }, 15000);

    try {
      addToast("loading", `Processing ${selectedFile.name}...`);
      const auditResult = await auditContractFile(
        selectedFile,
        selectedMode as Exclude<AppMode, "ADVISORY">,
        redactionOptions,
        setUploadProgress
      );
      setResult(auditResult);
      window.scrollTo({ top: 0, behavior: "instant" });
      setAppState(selectedMode);
      addToast("success", `${selectedMode} completed successfully`);
      logger.info("File processed successfully", { mode: selectedMode, filename: selectedFile.name });
      await new Promise((r) => setTimeout(r, 280));
    } catch (caughtError) {
      const apiErr = caughtError as ApiError;
      setApiError(apiErr);
      setRetryAttempt(1);
      addToast("error", apiErr.message);
      logApiError("/ask_file", apiErr, { mode: selectedMode, filename: selectedFile?.name });
      await new Promise((r) => setTimeout(r, 280));
    } finally {
      clearTimeout(longTimer);
      setIsLoading(false);
    }
  }

  const handleRetry = useCallback(async () => {
    if (!selectedFile || connectionState === "offline") return;
    setRetryAttempt((prev) => prev + 1);
    setIsLoading(true);
    setUploadProgress(0);
    setApiError(null);

    try {
      addToast("loading", `Retrying (attempt ${retryAttempt + 1})...`);
      const auditResult = await auditContractFile(
        selectedFile,
        selectedMode as Exclude<AppMode, "ADVISORY">,
        redactionOptions,
        setUploadProgress
      );
      setResult(auditResult);
      setAppState(selectedMode);
      addToast("success", "Retry successful!");
    } catch (caughtError) {
      const apiErr = caughtError as ApiError;
      setApiError(apiErr);
      addToast("error", apiErr.message);
      logApiError("/ask_file (retry)", apiErr, { attempt: retryAttempt + 1 });
    } finally {
      setIsLoading(false);
    }
  }, [selectedFile, selectedMode, redactionOptions, connectionState, retryAttempt, addToast]);

  function handleReset() {
    setResult(null);
    setSelectedFile(null);
    setError(null);
    setApiError(null);
    setUploadProgress(0);
    setAppState("AUDIT");
    setRetryAttempt(0);
    persistence.clearAppState();
  }

  async function handleAdvisorySend(retried = false) {
    const question = advisoryInput.trim();
    if (!question || isAdvisoryLoading) return;

    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: question,
      createdAt: new Date().toISOString(),
    };
    const historyBeforeSend = advisoryMessages;

    setAdvisoryMessages((messages) => [...messages, userMessage]);
    setAdvisoryInput("");
    setAdvisoryError(null);
    setIsAdvisoryLoading(true);

    try {
      addToast("loading", "Getting response...");
      const response = await askAdvisoryQuestion(question, advisorySessionId, historyBeforeSend);
      const assistantText = response.advisory_text || response.legacy_text || "";
      const genericGreeting = /^(hello|hi|welcome|how can i help|how may i assist)[\s!.?,]*$/i.test(assistantText.trim());

      const assistantMessage: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: genericGreeting
          ? "The backend returned a generic greeting instead of answering the supplied advisory question."
          : assistantText || "The backend returned an empty advisory response.",
        createdAt: new Date().toISOString(),
        confidence_score: response.confidence_score,
        confidence_label: response.confidence_label,
      };
      setAdvisoryMessages((messages) => [...messages, assistantMessage]);
      addToast("success", "Response received");
    } catch (caughtError) {
      const apiErr = caughtError as ApiError;
      setAdvisoryError(apiErr);
      addToast("error", apiErr.message);
      logApiError("/ask (advisory)", apiErr, { retried });
    } finally {
      setIsAdvisoryLoading(false);
    }
  }

  const handleAdvisoryRetry = useCallback(() => {
    handleAdvisorySend(true);
  }, []);

  function handleModeChange(mode: AppMode | "WORKSPACE" | "DASHBOARD") {
    if (mode === "AUDIT" || mode === "REDACTION" || mode === "ADVISORY") {
      setSelectedMode(mode);
    }
    setResult(null);
    setError(null);
    setApiError(null);
    setAdvisoryError(null);
    setAppState(mode);
  }

  function handleRecordOpen(record: HistoryRecord, result: AuditResponse) {
    setResult(result);
    setAppState(result.mode || "AUDIT");
  }

  // Dashboard view (new landing)
  if (appState === "DASHBOARD") {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-950 to-black">
        <TopNavigation currentMode="DASHBOARD" onModeChange={handleModeChange} />
        <DashboardPage onModeChange={handleModeChange} />
      </div>
    );
  }

  // Workspace view
  if (appState === "WORKSPACE") {
    return (
      <WorkspacePage
        onModeChange={handleModeChange}
        onRecordOpen={handleRecordOpen}
      />
    );
  }

  // Advisory view
  if (appState === "ADVISORY") {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-950 to-black">
        <TopNavigation currentMode="ADVISORY" onModeChange={handleModeChange} />
        <AdvisoryChatPage
          messages={advisoryMessages}
          inputValue={advisoryInput}
          isLoading={isAdvisoryLoading}
          error={advisoryError}
          sessionId={advisorySessionId}
          onInputChange={setAdvisoryInput}
          onSend={handleAdvisorySend}
          onModeChange={handleModeChange}
          onRetry={advisoryError ? handleAdvisoryRetry : undefined}
          isRetrying={isAdvisoryLoading}
        />
      </div>
    );
  }

  // Redaction results view
  if (result?.mode === "REDACTION") {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-950 to-black">
        <TopNavigation currentMode="REDACTION" onModeChange={handleModeChange} />
        <RedactionResultsPage
          result={result}
          onReset={handleReset}
        />
      </div>
    );
  }

  // Shared wrapper for upload, loading, and results
  const showUpload = !result && !apiError && !isLoading;
  const showResults = !!(result || apiError);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-950 to-black relative">
      {/* Upload content (wrapper stays in DOM during loading for fade-out) */}
      {!result && !apiError && (
        <div
          className={`transition-all duration-200 ease-out ${
            isLoading
              ? 'opacity-0 scale-[0.97] pointer-events-none'
              : 'animate-fade-up-long'
          }`}
        >
          <TopNavigation currentMode={appState as AppMode} onModeChange={handleModeChange} />
          <UploadContractPage
            error={error}
            isLoading={isLoading}
            selectedFile={selectedFile}
            uploadProgress={uploadProgress}
            selectedMode={selectedMode}
            redactionOptions={redactionOptions}
            onFileChange={(file) => {
              setSelectedFile(file);
              setError(null);
              setApiError(null);
            }}
            onModeChange={handleModeChange}
            onRedactionOptionsChange={setRedactionOptions}
            onSubmit={handleSubmit}
          />
        </div>
      )}

      {/* Results content (renders behind loading overlay during transition) */}
      {showResults && (
        <div>
          <TopNavigation currentMode={result?.mode || (apiError ? "AUDIT" : "AUDIT")} onModeChange={handleModeChange} />
          <AuditResultsPage
            result={result}
            error={apiError}
            onReset={handleReset}
          />
          {apiError && (
            <div className="fixed bottom-4 left-4 z-40">
              <RetryButton
                onRetry={handleRetry}
                isRetrying={isLoading}
                attempt={retryAttempt}
                maxAttempts={3}
                label="Retry Upload"
              />
            </div>
          )}
        </div>
      )}

      {/* Loading overlay (on top of results during transition, fades out) */}
      {isLoading && (
        <div
          className={`fixed inset-0 z-30 transition-opacity duration-300 ease-out ${
            result || apiError ? 'opacity-0 pointer-events-none' : 'animate-fade-up-long'
          }`}
        >
          <AuditLoadingWorkflow
            filename={selectedFile?.name ?? ""}
            mode={appState as AppMode}
          />
        </div>
      )}
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <ToastProvider>
        <OfflineIndicator />
        <AppContent />
      </ToastProvider>
    </ErrorBoundary>
  );
}
