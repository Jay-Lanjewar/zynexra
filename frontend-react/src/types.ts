export type SeverityLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "UNRATED";

export type AppMode = "AUDIT" | "REDACTION" | "ADVISORY";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  confidence_score?: number;
  confidence_label?: ConfidenceLabel;
};

export type HistoryRecord = {
  id: number;
  filename: string;
  timestamp: string;
  mode?: string;
  issue_count?: number;
  redaction_count?: number;
  title?: string;
  severity?: string;
  preview?: string;
  record_type?: "audit" | "redaction" | "advisory";
};

export type ConfidenceLabel = "HIGH" | "MEDIUM" | "LOW";

export type ConfidenceMetadata = {
  confidence_score: number;
  confidence_label: ConfidenceLabel;
  fallback_used?: boolean;
  model_name?: string;
  inference_duration_ms?: number;
  parser_used?: string;
  analysis_metadata?: AnalysisMetadata;
};

export type AnalysisMetadata = {
  was_truncated: boolean;
  kept_chars: number;
  dropped_chars: number;
  context_utilization_pct: number;
  pages_seen: number | null;
};

export type AuditIssue = {
  issue_title: string;
  severity: string;
  category: string;
  location: string;
  quoted_text: string;
  risk_explanation: string;
  suggested_improvement: string;
  contradiction_detected?: boolean;
};

export type RedactionEntityType =
  | "PERSON"
  | "EMAIL"
  | "PHONE"
  | "ADDRESS"
  | "COMPANY"
  | "LOCATION"
  | "MONEY"
  | "DATE"
  | "ID_NUMBER";

export type RedactionEntity = {
  entity_type: RedactionEntityType;
  original_text: string;
  replacement: string;
  confidence: number;
  start: number;
  end: number;
};

export type RedactionOptions = {
  emails: boolean;
  phones: boolean;
  names: boolean;
  addresses: boolean;
  companies: boolean;
};

export type PolicyNotice = {
  success: boolean;
  model: string;
  mode?: AppMode;
  response_type: "policy";
  issue_count: number;
  issues: AuditIssue[];
  structured_parse_failed?: boolean;
  legacy_text?: string;
  policy_type: string;
  policy_explanation: string;
  policy_confidence: number;
  metadata?: ConfidenceMetadata & {
    policy_keyword_score?: number;
    contractual_signal_score?: number;
    policy_keywords?: string[];
  };
};

export type NonLegalNotice = {
  success: boolean;
  model: string;
  mode?: AppMode;
  response_type: "non_legal";
  issue_count: number;
  issues: AuditIssue[];
  structured_parse_failed?: boolean;
  legacy_text?: string;
  content_type: string;
  content_explanation: string;
  domain_confidence: number;
  legal_keyword_ratio: number;
  structure_score: number;
  metadata?: ConfidenceMetadata & {
    domain?: string;
    legal_signal?: number;
    non_legal_penalty?: number;
  };
};

export type AuditResponse = {
  success: boolean;
  model: string;
  mode?: AppMode;
  response_type?: "audit" | "redaction" | "advisory" | "legacy" | "policy" | "non_legal";
  issue_count: number;
  issues: AuditIssue[];
  structured_parse_failed?: boolean;
  legacy_text?: string;
  redacted_text?: string;
  advisory_text?: string;
  original_text?: string;
  redaction_entities?: RedactionEntity[];
  redaction_count?: number;
  fallback_used?: boolean;
  confidence_score?: number;
  confidence_label?: ConfidenceLabel;
  metadata?: ConfidenceMetadata;
} & Partial<PolicyNotice> & Partial<NonLegalNotice>;

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
