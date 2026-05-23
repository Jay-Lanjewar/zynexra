import type { AppMode } from "../types";
import type { HistoryFilter } from "../api";

const STORAGE_KEYS = {
  APP_STATE: "zynexra_app_state",
  MODE: "zynexra_mode",
  FILTERS: "zynexra_filters",
  ADVISORY_SESSION: "zynexra_advisory_session",
  ADVISORY_MESSAGES: "zynexra_advisory_messages",
  SIDEBAR: "zynexra_sidebar",
} as const;

export type PersistedAppState = {
  mode: AppMode | "WORKSPACE" | "DASHBOARD";
  selectedMode: AppMode;
  redactionOptions: {
    emails: boolean;
    phones: boolean;
    names: boolean;
    addresses: boolean;
    companies: boolean;
  };
  timestamp: number;
};

export type PersistedFilters = {
  filter: HistoryFilter;
  activeTab: "all" | "audit" | "redaction" | "advisory";
  timestamp: number;
};

export type PersistedAdvisory = {
  sessionId: string;
  messages: Array<{
    id: string;
    role: "user" | "assistant";
    content: string;
    createdAt: string;
  }>;
  timestamp: number;
};

export const persistence = {
  saveAppState(state: PersistedAppState) {
    try {
      const data = { ...state, timestamp: Date.now() };
      sessionStorage.setItem(STORAGE_KEYS.APP_STATE, JSON.stringify(data));
    } catch (e) {
      console.warn("Failed to persist app state:", e);
    }
  },

  loadAppState(): PersistedAppState | null {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEYS.APP_STATE);
      if (!raw) return null;
      const data = JSON.parse(raw) as PersistedAppState;
      const age = Date.now() - data.timestamp;
      if (age > 30 * 60 * 1000) {
        sessionStorage.removeItem(STORAGE_KEYS.APP_STATE);
        return null;
      }
      return data;
    } catch {
      return null;
    }
  },

  clearAppState() {
    sessionStorage.removeItem(STORAGE_KEYS.APP_STATE);
  },

  saveFilters(filters: PersistedFilters) {
    try {
      sessionStorage.setItem(STORAGE_KEYS.FILTERS, JSON.stringify({ ...filters, timestamp: Date.now() }));
    } catch (e) {
      console.warn("Failed to persist filters:", e);
    }
  },

  loadFilters(): PersistedFilters | null {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEYS.FILTERS);
      if (!raw) return null;
      const data = JSON.parse(raw) as PersistedFilters;
      const age = Date.now() - data.timestamp;
      if (age > 24 * 60 * 60 * 1000) {
        sessionStorage.removeItem(STORAGE_KEYS.FILTERS);
        return null;
      }
      return data;
    } catch {
      return null;
    }
  },

  saveAdvisoryState(state: PersistedAdvisory) {
    try {
      sessionStorage.setItem(STORAGE_KEYS.ADVISORY_SESSION, JSON.stringify(state.sessionId));
      sessionStorage.setItem(STORAGE_KEYS.ADVISORY_MESSAGES, JSON.stringify({ ...state, timestamp: Date.now() }));
    } catch (e) {
      console.warn("Failed to persist advisory state:", e);
    }
  },

  loadAdvisoryState(): { sessionId: string; messages: PersistedAdvisory["messages"] } | null {
    try {
      const sessionId = sessionStorage.getItem(STORAGE_KEYS.ADVISORY_SESSION);
      const raw = sessionStorage.getItem(STORAGE_KEYS.ADVISORY_MESSAGES);
      if (!sessionId || !raw) return null;
      const data = JSON.parse(raw) as PersistedAdvisory;
      const age = Date.now() - data.timestamp;
      if (age > 60 * 60 * 1000) {
        sessionStorage.removeItem(STORAGE_KEYS.ADVISORY_SESSION);
        sessionStorage.removeItem(STORAGE_KEYS.ADVISORY_MESSAGES);
        return null;
      }
      return { sessionId, messages: data.messages };
    } catch {
      return null;
    }
  },

  saveSidebarOpen(open: boolean) {
    try {
      sessionStorage.setItem(STORAGE_KEYS.SIDEBAR, JSON.stringify({ open, timestamp: Date.now() }));
    } catch (e) {
      console.warn("Failed to persist sidebar state:", e);
    }
  },

  loadSidebarOpen(): boolean | null {
    try {
      const raw = sessionStorage.getItem(STORAGE_KEYS.SIDEBAR);
      if (!raw) return null;
      const data = JSON.parse(raw);
      return data.open;
    } catch {
      return null;
    }
  },

  clearAll() {
    Object.values(STORAGE_KEYS).forEach((key) => {
      sessionStorage.removeItem(key);
    });
  },
};