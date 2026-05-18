import { CheckCircle2, ShieldCheck } from "lucide-react";

type EmptyStateProps = {
  type: "NO_ISSUES" | "NO_FILE";
  onReset?: () => void;
};

export function EmptyState({ type, onReset }: EmptyStateProps) {
  if (type === "NO_ISSUES") {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-emerald-200 bg-emerald-50 p-8 text-center">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100">
          <CheckCircle2 className="h-8 w-8 text-emerald-600" />
        </div>
        <h3 className="mt-4 text-lg font-semibold text-emerald-900">No Issues Found</h3>
        <p className="mt-2 max-w-md text-sm text-emerald-700">
          The contract analysis completed successfully with no significant issues detected. This doesn't guarantee the contract is risk-free, but no obvious concerns were identified.
        </p>
        {onReset && (
          <button
            type="button"
            onClick={onReset}
            className="mt-6 rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 transition-colors"
          >
            Audit Another Contract
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-slate-200 bg-slate-50 p-8 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-slate-100">
        <ShieldCheck className="h-8 w-8 text-slate-400" />
      </div>
      <h3 className="mt-4 text-lg font-semibold text-slate-700">No File Selected</h3>
      <p className="mt-2 max-w-md text-sm text-slate-500">
        Upload a contract file to begin the audit process. Supported formats: PDF, TXT, DOC.
      </p>
    </div>
  );
}