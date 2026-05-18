export type SeverityLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "UNRATED";

export type AuditIssue = {
  issue_title: string;
  severity: string;
  category: string;
  location: string;
  quoted_text: string;
  risk_explanation: string;
  suggested_improvement: string;
};

export type AuditResponse = {
  success: boolean;
  model: string;
  issue_count: number;
  issues: AuditIssue[];
  structured_parse_failed?: boolean;
  legacy_text?: string;
};

export type CategoryGroup = {
  category: string;
  issues: AuditIssue[];
  count: number;
};

export type ErrorState = {
  type: "NETWORK_ERROR" | "SERVER_ERROR" | "PARSE_ERROR" | "FILE_TOO_LARGE" | "INVALID_FILE_TYPE" | "UNKNOWN";
  message: string;
  recoverable: boolean;
};
