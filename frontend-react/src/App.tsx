import { useState } from "react";
import { askAdvisoryQuestion, auditContractFile, type ApiError } from "./api";
import { AdvisoryChatPage } from "./pages/AdvisoryChatPage";
import { AuditResultsPage } from "./pages/AuditResultsPage";
import { RedactionResultsPage } from "./pages/RedactionResultsPage";
import { UploadContractPage } from "./pages/UploadContractPage";
import { WorkspacePage } from "./pages/WorkspacePage";
import { TopNavigation } from "./components/TopNavigation";
import type { AppMode, AuditResponse, ChatMessage, RedactionOptions, HistoryRecord } from "./types";

type AppState = AppMode | "WORKSPACE";

export default function App() {
  const [appState, setAppState] = useState<AppState>("AUDIT");
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
  const [advisorySessionId] = useState(() => crypto.randomUUID());
  const [advisoryInput, setAdvisoryInput] = useState("");
  const [advisoryMessages, setAdvisoryMessages] = useState<ChatMessage[]>([]);
  const [advisoryError, setAdvisoryError] = useState<ApiError | null>(null);
  const [isAdvisoryLoading, setIsAdvisoryLoading] = useState(false);

  async function handleSubmit() {
    if (!selectedFile) {
      setError("Select a contract file first.");
      return;
    }

    setIsLoading(true);
    setUploadProgress(0);
    setError(null);
    setApiError(null);

    try {
      const auditResult = await auditContractFile(
        selectedFile,
        selectedMode as Exclude<AppMode, "ADVISORY">,
        redactionOptions,
        setUploadProgress
      );
      setResult(auditResult);
      setAppState(selectedMode);
    } catch (caughtError) {
      const apiErr = caughtError as ApiError;
      setApiError(apiErr);
    } finally {
      setIsLoading(false);
    }
  }

  function handleReset() {
    setResult(null);
    setSelectedFile(null);
    setError(null);
    setApiError(null);
    setUploadProgress(0);
    setAppState("AUDIT");
  }

  async function handleAdvisorySend() {
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
      };
      setAdvisoryMessages((messages) => [...messages, assistantMessage]);
    } catch (caughtError) {
      setAdvisoryError(caughtError as ApiError);
    } finally {
      setIsAdvisoryLoading(false);
    }
  }

  function handleModeChange(mode: AppMode | "WORKSPACE") {
    if (mode !== "WORKSPACE") {
      setSelectedMode(mode as AppMode);
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
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
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
        />
      </div>
    );
  }

  // Redaction results view
  if (result?.mode === "REDACTION") {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
        <TopNavigation currentMode="REDACTION" onModeChange={handleModeChange} />
        <RedactionResultsPage
          result={result}
          onReset={handleReset}
        />
      </div>
    );
  }

  // Audit results view
  if (result || apiError) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
        <TopNavigation currentMode={result?.mode || "AUDIT"} onModeChange={handleModeChange} />
        <AuditResultsPage
          result={result}
          error={apiError}
          onReset={handleReset}
        />
      </div>
    );
  }

  // Upload/main view
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <TopNavigation currentMode="AUDIT" onModeChange={handleModeChange} />
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
  );
}
