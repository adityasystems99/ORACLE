import {
  BlastRadiusReport,
  GraphSnapshot,
  ImpactReport,
  IngestionSource,
  IntelligenceEvent,
  SystemHealth,
} from "../types";

const BASE_URL = "/api";

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`API Error [${res.status}]: ${errorText || res.statusText}`);
  }

  return res.json();
}

export const api = {
  // System Health
  getHealth: () => request<SystemHealth>("/system/health"),

  // Events
  getEvents: (params?: { category?: string; severity?: string; technology?: string; limit?: number }) => {
    const query = new URLSearchParams();
    if (params?.category) query.append("category", params.category);
    if (params?.severity) query.append("severity", params.severity);
    if (params?.technology) query.append("technology", params.technology);
    if (params?.limit) query.append("limit", params.limit.toString());
    const qs = query.toString();
    return request<IntelligenceEvent[]>(`/events${qs ? `?${qs}` : ""}`);
  },

  getEventById: (id: string) => request<IntelligenceEvent>(`/events/${id}`),

  // Graph
  getGraphSnapshot: () => request<GraphSnapshot>("/graph/snapshot"),

  getBlastRadius: (entity: string, maxDepth: number = 3, eventId?: string) => {
    const query = new URLSearchParams({ entity, max_depth: maxDepth.toString() });
    if (eventId) query.append("event_id", eventId);
    return request<BlastRadiusReport>(`/graph/blast-radius?${query.toString()}`);
  },

  // Impact Analysis
  analyzeImpact: (eventId: string, maxDepth: number = 3) =>
    request<ImpactReport>("/impact/analyze", {
      method: "POST",
      body: JSON.stringify({ event_id: eventId, max_depth: maxDepth }),
    }),

  getReports: (technology?: string, limit: number = 20) => {
    const query = new URLSearchParams({ limit: limit.toString() });
    if (technology) query.append("technology", technology);
    return request<ImpactReport[]>(`/impact/reports?${query.toString()}`);
  },

  getReportById: (reportId: string) => request<ImpactReport>(`/impact/reports/${reportId}`),

  getReportMarkdown: async (reportId: string): Promise<string> => {
    const res = await fetch(`${BASE_URL}/impact/reports/${reportId}/markdown`);
    return res.text();
  },

  // Ingestion
  getSources: () => request<IngestionSource[]>("/ingest/sources"),

  triggerSync: (sourceId?: string) => {
    const query = sourceId ? `?source_id=${sourceId}` : "";
    return request<{ status: string; signals_ingested: number; events_detected: number; event_ids: string[] }>(
      `/ingest/sync${query}`,
      { method: "POST" }
    );
  },
};
