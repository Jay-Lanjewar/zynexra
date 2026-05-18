import { Loader2, ShieldCheck, Server } from "lucide-react";
import { FileUploader } from "../components/FileUploader";
import { ErrorState } from "../components/ErrorState";
import { getApiBaseUrl } from "../api";

type UploadContractPageProps = {
  error: string | null;
  isLoading: boolean;
  selectedFile: File | null;
  uploadProgress: number;
  onFileChange: (file: File | null) => void;
  onSubmit: () => void;
};

export function UploadContractPage({
  error,
  isLoading,
  selectedFile,
  uploadProgress,
  onFileChange,
  onSubmit,
}: UploadContractPageProps) {
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
          <h2 className="text-2xl font-semibold text-slate-950">Upload a contract for structured risk review</h2>
          <p className="mt-3 max-w-2xl text-base leading-7 text-slate-600">
            Submit a PDF or text contract and receive normalized audit issues from the FastAPI backend in JSON mode.
          </p>

          <div className="mt-8 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <FileUploader
              selectedFile={selectedFile}
              onFileChange={onFileChange}
              uploadProgress={uploadProgress}
              isUploading={isLoading}
              validationError={error}
            />

            <button
              type="button"
              onClick={onSubmit}
              disabled={!selectedFile || isLoading}
              className="mt-5 inline-flex h-11 w-full items-center justify-center gap-2 rounded-md bg-slate-950 px-4 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {isLoading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
              {isLoading ? "Auditing contract" : "Run audit"}
            </button>
          </div>
        </div>

        <aside className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-base font-semibold text-slate-950">Structured output fields</h2>
          <div className="mt-4 grid gap-2 text-sm text-slate-600">
            {["severity", "category", "location", "quoted_text", "risk_explanation", "suggested_improvement"].map(
              (field) => (
                <div key={field} className="rounded-md bg-slate-50 px-3 py-2 font-mono text-xs text-slate-700">
                  {field}
                </div>
              )
            )}
          </div>
          <div className="mt-6 flex items-center gap-2 rounded-md bg-slate-50 px-3 py-2 text-xs text-slate-500">
            <Server className="h-3.5 w-3.5" />
            <span>API: {getApiBaseUrl()}</span>
          </div>
        </aside>
      </section>
    </main>
  );
}
