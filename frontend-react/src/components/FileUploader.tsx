import { useState, useRef, useCallback } from "react";
import { FileUp, FileCheck, X, UploadCloud, AlertCircle } from "lucide-react";
import { validateFile, type ApiError } from "../api";

type FileUploaderProps = {
  selectedFile: File | null;
  onFileChange: (file: File | null) => void;
  uploadProgress: number;
  isUploading: boolean;
  validationError: string | null;
};

export function FileUploader({
  selectedFile,
  onFileChange,
  uploadProgress,
  isUploading,
  validationError,
}: FileUploaderProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    (file: File | null) => {
      setLocalError(null);
      if (!file) return;

      const validationResult = validateFile(file);
      if (validationResult) {
        setLocalError(validationResult.message);
        onFileChange(null);
        return;
      }

      onFileChange(file);
    },
    [onFileChange]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);

      if (isUploading) return;

      const files = e.dataTransfer.files;
      if (files.length > 0) {
        handleFile(files[0]);
      }
    },
    [handleFile, isUploading]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleClear = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onFileChange(null);
      setLocalError(null);
      if (inputRef.current) {
        inputRef.current.value = "";
      }
    },
    [onFileChange]
  );

  const displayError = localError || validationError;

  return (
    <div className="space-y-4">
      <div
        onClick={() => !isUploading && inputRef.current?.click()}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onKeyDown={(e) => {
          if ((e.key === "Enter" || e.key === " ") && !isUploading) {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        role="button"
        tabIndex={isUploading ? -1 : 0}
        aria-label={selectedFile ? `File selected: ${selectedFile.name}. Press to change.` : "Upload file. Click or drag and drop."}
        aria-describedby={displayError ? "file-error" : undefined}
        className={`
          relative cursor-pointer rounded-lg border-2 border-dashed bg-slate-900/60 p-8 text-center transition-all
          ${isDragOver
            ? "border-indigo-500/50 bg-indigo-500/10 ring-2 ring-indigo-500/20"
            : "border-slate-700 hover:border-indigo-500/50 hover:bg-slate-800/30"
          }
          ${isUploading ? "cursor-wait opacity-60" : ""}
          focus-visible:focus-ring
        `}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt,.doc,.docx,application/pdf,text/plain,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          className="sr-only"
          onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
          disabled={isUploading}
          aria-label="Select file to upload"
        />

        {selectedFile ? (
          <div className="flex flex-col items-center gap-3">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-emerald-500/10">
              <FileCheck className="h-7 w-7 text-emerald-400" />
            </div>
            <div className="flex items-center gap-2">
              <span className="font-medium text-slate-200">{selectedFile.name}</span>
              <button
                type="button"
                onClick={handleClear}
                disabled={isUploading}
                className="rounded-full p-1 text-slate-500 hover:bg-slate-800 hover:text-slate-300 disabled:cursor-not-allowed"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <span className="text-sm text-slate-400">
              {(selectedFile.size / 1024).toFixed(1)} KB
            </span>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className={`flex h-14 w-14 items-center justify-center rounded-full ${isDragOver ? "bg-indigo-500/10" : "bg-slate-800/50"}`}>
              {isDragOver ? (
                <UploadCloud className="h-7 w-7 text-indigo-400" />
              ) : (
                <FileUp className="h-7 w-7 text-slate-400" />
              )}
            </div>
            <div className="space-y-1">
              <p className="font-medium text-slate-200">
                {isDragOver ? "Drop file here" : "Drag and drop your contract"}
              </p>
              <p className="text-sm text-slate-400">
                or click to browse · PDF up to 25MB, DOC/DOCX up to 15MB, TXT up to 2MB
              </p>
            </div>
          </div>
        )}
      </div>

      {isUploading && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-400">Uploading and analyzing...</span>
            <span className="font-medium text-slate-200">{uploadProgress}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-700">
            <div
              className="h-full bg-indigo-500 transition-all duration-300 ease-out"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
        </div>
      )}

      {displayError && (
        <div id="file-error" role="alert" className="flex items-center gap-2 rounded-md border border-red-500/20 bg-red-500/5 px-4 py-3 text-sm text-red-400">
          <AlertCircle className="h-4 w-4 flex-shrink-0" aria-hidden="true" />
          {displayError}
        </div>
      )}
    </div>
  );
}
