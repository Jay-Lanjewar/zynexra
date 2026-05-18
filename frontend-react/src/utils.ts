import type { AuditIssue, CategoryGroup } from "./types";

export function groupIssuesByCategory(issues: AuditIssue[]): CategoryGroup[] {
  const groups: Record<string, AuditIssue[]> = {};

  for (const issue of issues) {
    const category = issue.category || "Uncategorized";
    if (!groups[category]) {
      groups[category] = [];
    }
    groups[category].push(issue);
  }

  return Object.entries(groups).map(([category, categoryIssues]) => ({
    category,
    issues: categoryIssues,
    count: categoryIssues.length,
  }));
}

export function getSeverityCounts(issues: AuditIssue[]): Record<string, number> {
  const counts: Record<string, number> = {
    CRITICAL: 0,
    HIGH: 0,
    MEDIUM: 0,
    LOW: 0,
    UNRATED: 0,
  };

  for (const issue of issues) {
    const severity = (issue.severity?.toUpperCase() as keyof typeof counts) || "UNRATED";
    if (severity in counts) {
      counts[severity]++;
    } else {
      counts.UNRATED++;
    }
  }

  return counts;
}

export function formatDate(date: Date): string {
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}