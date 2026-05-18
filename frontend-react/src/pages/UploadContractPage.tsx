import { Eraser, FileSearch, Info, Loader2, MessageSquareText, ShieldCheck, Server } from "lucide-react";
import type { ElementType } from "react";
import { FileUploader } from "../components/FileUploader";
import { getApiBaseUrl } from "../api";
import type { AppMode, RedactionOptions } from "../types";

type UploadContractPageProps = {
  error: string | null;
  isLoading: boolean;
  selectedFile: File | null;
  uploadProgress: number;
  selectedMode: AppMode;
  redactionOptions: RedactionOptions;
  onFileChange: (file: File | null) => void;
  onModeChange: (mode: AppMode) => void;
  onRedactionOptionsChange: (options: RedactionOptions) => void;
  onSubmit: () => void;
};

const modes: Array<{
  value: AppMode;
  label: string;
  description: string;
  tooltip: string;
  icon: ElementType;
}> = [
  {
    value: "AUDIT",
    label: "Audit",
    description: "Find contract risks and return structured issue cards.",
    tooltip: "Uses /ask_file with JSON output and preserves the structured audit issue schema.",
    icon: FileSearch,
  },
  {
    value: "REDACTION",
    label: "Redaction",
    description: "Redact obvious personal data from uploaded text or PDF content.",
    tooltip: "Uses /ask_file with REDACTION mode and renders the redacted text output.",
    icon: Eraser,
  },
  {
    value: "ADVISORY",
    label: "Advisory",
    description: "Ask a legal-practice question without uploading a document.",
    tooltip: "Uses /ask because the backend does not support document analysis in ADVISORY mode.",
    icon: MessageSquareText,
  },
];

export function UploadContractPage({
  error,
  isLoading,
  selectedFile,
  uploadProgress,
  selectedMode,
  redactionOptions,
  onFileChange,
  onModeChange,
  onRedactionOptionsChange,
  onSubmit,
}: UploadContractPageProps) {
  const selectedModeConfig = modes.find((mode) => mode.value === selectedMode) ?? modes[0];
  const submitDisabled = isLoading || !selectedFile;
  const toggleOptions: Array<{ key: keyof RedactionOptions; label: string }> = [
    { key: "emails", label: "Emails" },
    { key: "phones", label: "Phones" },
    { key: "names", label: "Names" },
    { key: "addresses", label: "Addresses" },
    { key: "companies", label: "Companies" },
  ];

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col px-5 py-8 sm:px-8">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">Zynexra</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-950">Contract Audit</h1>
        </div>
        <div className="flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600">
          <ShieldCheck className="h-4 w-4 text-emerald-600" aria-hidden="true" />
          <span className="hidden sm:inline">Offline legal analysis</span>
        </div>
      </header>

      <section className="grid flex-1 gap-8 py-8 lg:grid-cols-[1fr_0.8fr] lg:items-center">
        <div>
          <h2 className="text-2xl font-semibold text-slate-950">
            Upload a contract for local processing
          </h2>
          <p className="mt-3 max-w-2xl text-base leading-7 text-slate-600">
            {selectedModeConfig.description}
          </p>

          <div className="mt-8 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <div className="mb-5">
              <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-slate-800">
                Mode
                <Info className="h-4 w-4 text-slate-400" aria-hidden="true" />
              </div>
              <div className="grid gap-2 rounded-md bg-slate-100 p-1 sm:grid-cols-3" role="tablist" aria-label="Processing mode">
                {modes.map((mode) => {
                  const Icon = mode.icon;
                  const isSelected = selectedMode === mode.value;
                  return (
                    <button
                      key={mode.value}
                      type="button"
                      role="tab"
                      aria-selected={isSelected}
                      title={mode.tooltip}
                      onClick={() => onModeChange(mode.value)}
                      className={`flex min-h-20 flex-col items-start justify-center gap-2 rounded-md px-3 py-2 text-left transition ${
                        isSelected
                          ? "bg-white text-slate-950 shadow-sm ring-1 ring-slate-200"
                          : "text-slate-600 hover:bg-white/70 hover:text-slate-900"
                      }`}
                    >
                      <span className="flex items-center gap-2 text-sm font-semibold">
                        <Icon className="h-4 w-4" aria-hidden="true" />
                        {mode.label}
                      </span>
                      <span className="text-xs leading-5 text-slate-500">{mode.description}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <FileUploader
              selectedFile={selectedFile}
              onFileChange={onFileChange}
              uploadProgress={uploadProgress}
              isUploading={isLoading}
              validationError={error}
            />

            {selectedMode === "REDACTION" ? (
              <div className="mt-5 border-t border-slate-200 pt-5">
                <div className="text-sm font-semibold text-slate-800">Redaction toggles</div>
                <div className="mt-3 grid gap-2 sm:grid-cols-2">
                  {toggleOptions.map((option) => (
                    <label
                      key={option.key}
                      className="flex items-center justify-between gap-3 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700"
                    >
                      <span>{option.label}</span>
                      <input
                        type="checkbox"
                        checked={redactionOptions[option.key]}
                        onChange={(event) => {
                          onRedactionOptionsChange({
                            ...redactionOptions,
                            [option.key]: event.target.checked,
                          });
                        }}
                        className="h-4 w-4 accent-slate-950"
                      />
                    </label>
                  ))}
                </div>
              </div>
            ) : null}

            <button
              type="button"
              onClick={onSubmit}
              disabled={submitDisabled}
              className="mt-5 inline-flex h-11 w-full items-center justify-center gap-2 rounded-md bg-slate-950 px-4 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {isLoading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
              {isLoading ? "Processing request" : `Run ${selectedModeConfig.label.toLowerCase()}`}
            </button>
          </div>
        </div>

        <aside className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-base font-semibold text-slate-950">{selectedModeConfig.label} output</h2>
          {selectedMode === "AUDIT" ? (
            <div className="mt-4 grid gap-2 text-sm text-slate-600">
              {["severity", "category", "location", "quoted_text", "risk_explanation", "suggested_improvement"].map(
                (field) => (
                  <div key={field} className="rounded-md bg-slate-50 px-3 py-2 font-mono text-xs text-slate-700">
                    {field}
                  </div>
                )
              )}
            </div>
          ) : (
            <p className="mt-4 rounded-md bg-slate-50 px-3 py-3 text-sm leading-6 text-slate-600">
              {selectedMode === "REDACTION"
                ? "The backend returns original text, entity metadata, confidence scores, and redacted text."
                : "Advisory uses the existing question endpoint and returns advisory_text plus legacy_text."}
            </p>
          )}
          <div className="mt-6 flex items-center gap-2 rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-500">
            <Server className="h-3.5 w-3.5" />
            <span>API: {getApiBaseUrl()}</span>
          </div>
        </aside>
      </section>
    </main>
  );
}
