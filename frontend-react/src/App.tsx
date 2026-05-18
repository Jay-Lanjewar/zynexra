import { useState } from "react";
import { auditContractFile, type ApiError } from "./api";
import { AuditResultsPage } from "./pages/AuditResultsPage";
import { UploadContractPage } from "./pages/UploadContractPage";
import type { AuditResponse } from "./types";

export default function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [result, setResult] = useState<AuditResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<ApiError | null>(null);

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
      const auditResult = await auditContractFile(selectedFile, setUploadProgress);
      setResult(auditResult);
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
  }

  if (result || apiError) {
    return (
      <AuditResultsPage
        result={result}
        error={apiError}
        onReset={handleReset}
      />
    );
  }

  return (
    <UploadContractPage
      error={error}
      isLoading={isLoading}
      selectedFile={selectedFile}
      uploadProgress={uploadProgress}
      onFileChange={(file) => {
        setSelectedFile(file);
        setError(null);
        setApiError(null);
      }}
      onSubmit={handleSubmit}
    />
  );
}
