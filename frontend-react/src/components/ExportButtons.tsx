import { Download, FileJson, FileText } from "lucide-react";
import type { AuditResponse } from "../types";

type ExportButtonsProps = {
  result: AuditResponse;
  fileName?: string;
};

export function ExportButtons({ result, fileName = "audit-report" }: ExportButtonsProps) {
  const handleExportJson = () => {
    const jsonStr = JSON.stringify(result, null, 2);
    const blob = new Blob([jsonStr], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${fileName}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleExportText = () => {
    const lines: string[] = [];
    lines.push(`Zynexra Contract Audit Report`);
    lines.push(`Generated: ${new Date().toISOString()}`);
    lines.push(`Model: ${result.model}`);
    lines.push(`Issues Found: ${result.issue_count}`);
    lines.push("");
    lines.push("=".repeat(50));

    if (result.structured_parse_failed) {
      lines.push("");
      lines.push("PARSE WARNING: Structured parsing failed.");
      if (result.legacy_text) {
        lines.push("");
        lines.push("Legacy Output:");
        lines.push(result.legacy_text);
      }
    } else {
      result.issues.forEach((issue, idx) => {
        lines.push("");
        lines.push(`--- Issue ${idx + 1} ---`);
        lines.push(`Title: ${issue.issue_title || `Issue ${idx + 1}`}`);
        lines.push(`Severity: ${issue.severity || "UNRATED"}`);
        lines.push(`Category: ${issue.category || "Uncategorized"}`);
        lines.push(`Location: ${issue.location || "Unspecified"}`);
        lines.push("");
        lines.push(`Quoted Text:`);
        lines.push(issue.quoted_text || "N/A");
        lines.push("");
        lines.push(`Risk Explanation:`);
        lines.push(issue.risk_explanation || "N/A");
        lines.push("");
        lines.push(`Suggested Improvement:`);
        lines.push(issue.suggested_improvement || "N/A");
      });
    }

    const blob = new Blob([lines.join("\n")], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${fileName}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-slate-500">Export:</span>
      <button
        type="button"
        onClick={handleExportJson}
        className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50 transition-colors"
      >
        <FileJson className="h-4 w-4" />
        JSON
      </button>
      <button
        type="button"
        onClick={handleExportText}
        className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50 transition-colors"
      >
        <FileText className="h-4 w-4" />
        Text
      </button>
      <button
        type="button"
        onClick={handleExportJson}
        className="inline-flex items-center gap-2 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50 transition-colors"
      >
        <Download className="h-4 w-4" />
      </button>
    </div>
  );
}