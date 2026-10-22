import {
  BlastRadiusReport,
  ConnectionMode,
  GraphSnapshot,
  ImpactReport,
  IngestionSource,
  IntelligenceEvent,
  InvestigationMessage,
  InvestigationSession,
  MonitoringRule,
  NotificationItem,
  SystemHealth,
  TimelineEvent,
} from "../types";
import {
  MOCK_BLAST_REPORTS,
  MOCK_GRAPH_SNAPSHOT,
  MOCK_IMPACT_REPORTS,
  MOCK_INTELLIGENCE_EVENTS,
  MOCK_INVESTIGATIONS,
  MOCK_MONITORING_RULES,
  MOCK_NOTIFICATIONS,
  MOCK_SOURCES,
  MOCK_SYSTEM_HEALTH,
  MOCK_TIMELINE_EVENTS,
} from "./mockData";

const BASE_URL = "/api";

// In-memory mutable states for demo mode
let currentConnectionMode: ConnectionMode = "demo_fixtures";
let inMemoryEvents = [...MOCK_INTELLIGENCE_EVENTS];
let inMemoryReports = [...MOCK_IMPACT_REPORTS];
let inMemorySources = [...MOCK_SOURCES];
let inMemoryRules = [...MOCK_MONITORING_RULES];
let inMemoryInvestigations = [...MOCK_INVESTIGATIONS];
let inMemoryTimeline = [...MOCK_TIMELINE_EVENTS];

async function requestWithTimeout<T>(endpoint: string, options?: RequestInit, timeoutMs = 2500): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${BASE_URL}${endpoint}`, {
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(options?.headers || {}),
      },
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(`API Error [${res.status}]: ${errorText || res.statusText}`);
    }

    return res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    throw err;
  }
}

export const api = {
  // Connection and Mode management
  getConnectionMode(): ConnectionMode {
    return currentConnectionMode;
  },

  setConnectionMode(mode: ConnectionMode) {
    currentConnectionMode = mode;
  },

  async probeBackend(): Promise<boolean> {
    try {
      const h = await requestWithTimeout<SystemHealth>("/system/health", undefined, 1800);
      if (h && h.status) {
        currentConnectionMode = "connected";
        return true;
      }
    } catch {
      currentConnectionMode = "demo_fixtures";
      return false;
    }
    currentConnectionMode = "demo_fixtures";
    return false;
  },

  // System Health
  async getHealth(): Promise<SystemHealth> {
    if (currentConnectionMode === "connected") {
      try {
        return await requestWithTimeout<SystemHealth>("/system/health");
      } catch (e) {
        currentConnectionMode = "demo_fixtures";
      }
    }
    return {
      ...MOCK_SYSTEM_HEALTH,
      status: "active (demo fixtures)",
      events_count: inMemoryEvents.length,
      reports_count: inMemoryReports.length,
      sources_count: inMemorySources.length,
    };
  },

  // Intelligence Events
  async getEvents(params?: {
    category?: string;
    severity?: string;
    technology?: string;
    limit?: number;
  }): Promise<IntelligenceEvent[]> {
    if (currentConnectionMode === "connected") {
      try {
        const query = new URLSearchParams();
        if (params?.category) query.append("category", params.category);
        if (params?.severity) query.append("severity", params.severity);
        if (params?.technology) query.append("technology", params.technology);
        if (params?.limit) query.append("limit", params.limit.toString());
        const qs = query.toString();
        return await requestWithTimeout<IntelligenceEvent[]>(`/events${qs ? `?${qs}` : ""}`);
      } catch {
        currentConnectionMode = "demo_fixtures";
      }
    }

    let results = [...inMemoryEvents];
    if (params?.category && params.category !== "all") {
      results = results.filter((e) => e.category === params.category);
    }
    if (params?.severity && params.severity !== "all") {
      results = results.filter((e) => e.severity === params.severity);
    }
    if (params?.technology) {
      const t = params.technology.toLowerCase();
      results = results.filter(
        (e) =>
          e.primary_technology.toLowerCase().includes(t) ||
          e.affected_entities.some((ae) => ae.toLowerCase().includes(t))
      );
    }
    if (params?.limit) {
      results = results.slice(0, params.limit);
    }
    return results;
  },

  async getEventById(id: string): Promise<IntelligenceEvent | null> {
    if (currentConnectionMode === "connected") {
      try {
        return await requestWithTimeout<IntelligenceEvent>(`/events/${id}`);
      } catch {
        currentConnectionMode = "demo_fixtures";
      }
    }
    return inMemoryEvents.find((e) => e.id === id) || null;
  },

  // Knowledge Graph
  async getGraphSnapshot(): Promise<GraphSnapshot> {
    if (currentConnectionMode === "connected") {
      try {
        return await requestWithTimeout<GraphSnapshot>("/graph/snapshot");
      } catch {
        currentConnectionMode = "demo_fixtures";
      }
    }
    return MOCK_GRAPH_SNAPSHOT;
  },

  async getBlastRadius(entity: string, maxDepth: number = 3, eventId?: string): Promise<BlastRadiusReport> {
    if (currentConnectionMode === "connected") {
      try {
        const query = new URLSearchParams({ entity, max_depth: maxDepth.toString() });
        if (eventId) query.append("event_id", eventId);
        return await requestWithTimeout<BlastRadiusReport>(`/graph/blast-radius?${query.toString()}`);
      } catch {
        currentConnectionMode = "demo_fixtures";
      }
    }

    const key = entity.toLowerCase();
    if (MOCK_BLAST_REPORTS[key]) {
      return {
        ...MOCK_BLAST_REPORTS[key],
        event_id: eventId || MOCK_BLAST_REPORTS[key].event_id,
        max_traversal_depth: maxDepth,
        analysis_timestamp: new Date().toISOString(),
      };
    }

    // Dynamic fallback for any node
    const matchingNode = MOCK_GRAPH_SNAPSHOT.nodes.find((n) => n.id.toLowerCase() === key);
    return {
      root_entity: entity,
      event_id: eventId,
      max_traversal_depth: maxDepth,
      total_nodes_scanned: 4,
      direct_dependents_count: 1,
      transitive_dependents_count: 1,
      analysis_timestamp: new Date().toISOString(),
      affected_nodes: [
        {
          node_id: matchingNode?.id || entity,
          name: matchingNode?.name || entity,
          node_type: matchingNode?.node_type || "technology",
          ecosystem: matchingNode?.ecosystem || "general",
          depth: 1,
          relationship_path: [entity],
          impact_likelihood: 0.75,
          vulnerability_reasons: ["Dynamic temporal dependency identified in knowledge graph."],
        },
      ],
    };
  },

  // Impact Analysis & Reports
  async analyzeImpact(eventId: string, maxDepth: number = 3): Promise<ImpactReport> {
    if (currentConnectionMode === "connected") {
      try {
        return await requestWithTimeout<ImpactReport>("/impact/analyze", {
          method: "POST",
          body: JSON.stringify({ event_id: eventId, max_depth: maxDepth }),
        });
      } catch {
        currentConnectionMode = "demo_fixtures";
      }
    }

    // Demo adapter synthesis
    const event = inMemoryEvents.find((e) => e.id === eventId) || inMemoryEvents[0];
    const blast = await this.getBlastRadius(event.primary_technology, maxDepth, eventId);

    const newReport: ImpactReport = {
      id: `rep-${event.primary_technology}-${Date.now().toString(36)}`,
      event_id: event.id,
      event_title: event.title,
      severity: event.severity,
      primary_technology: event.primary_technology,
      ecosystem: event.metadata?.ecosystem || "python",
      executive_summary: `Synthesized intelligence brief for ${event.title}. ORACLE temporal reasoning identified ${blast.direct_dependents_count} direct dependents and ${blast.transitive_dependents_count} transitive dependencies.`,
      technical_root_cause: `${event.summary} Detection verified with ${Math.round(event.confidence * 100)}% confidence score from ${event.evidence.length} citations.`,
      breaking_changes: [
        `Interface mutation in ${event.primary_technology} version ${event.version_affected || "latest"}`,
        "Downstream compatibility verification required for upstream callers",
      ],
      impacted_components: blast.affected_nodes,
      evidence_trail: event.evidence,
      mitigation_playbook: [
        {
          step_number: 1,
          title: `Audit dependency bounds for ${event.primary_technology}`,
          description: `Lock versions strictly to prevent breaking upstream ingestion into production.`,
          priority: event.severity,
          action_type: "command",
          code_or_command: `# Pin dependency in requirements or package.json\n${event.primary_technology}==${event.version_fixed || "2.0.0"}`,
          verification_check: `Check dependency lockfile and execute test suite.`,
          estimated_effort: "10 minutes",
        },
        {
          step_number: 2,
          title: "Run automated test regression harness",
          description: "Execute end-to-end integration tests to flag signature mismatches.",
          priority: "high",
          action_type: "command",
          code_or_command: "pytest tests/ --disable-warnings -v",
          verification_check: "100% test pass without unhandled deprecation exceptions.",
          estimated_effort: "15 minutes",
        },
      ],
      confidence_score: event.confidence,
      llm_provenance: {
        provider: "anthropic",
        model: "claude-3-5-sonnet-20241022",
        latency_ms: 1250,
      },
      generated_at: new Date().toISOString(),
      is_live_data: true,
    };

    inMemoryReports = [newReport, ...inMemoryReports];
    return newReport;
  },

  async getReports(technology?: string, limit: number = 20): Promise<ImpactReport[]> {
    if (currentConnectionMode === "connected") {
      try {
        const query = new URLSearchParams({ limit: limit.toString() });
        if (technology) query.append("technology", technology);
        return await requestWithTimeout<ImpactReport[]>(`/impact/reports?${query.toString()}`);
      } catch {
        currentConnectionMode = "demo_fixtures";
      }
    }

    let reports = inMemoryReports;
    if (technology) {
      reports = reports.filter((r) => r.primary_technology.toLowerCase() === technology.toLowerCase());
    }
    return reports.slice(0, limit);
  },

  async getReportById(reportId: string): Promise<ImpactReport | null> {
    if (currentConnectionMode === "connected") {
      try {
        return await requestWithTimeout<ImpactReport>(`/impact/reports/${reportId}`);
      } catch {
        currentConnectionMode = "demo_fixtures";
      }
    }
    return inMemoryReports.find((r) => r.id === reportId) || null;
  },

  async getReportMarkdown(reportId: string): Promise<string> {
    if (currentConnectionMode === "connected") {
      try {
        const res = await fetch(`${BASE_URL}/impact/reports/${reportId}/markdown`);
        if (res.ok) return await res.text();
      } catch {
        currentConnectionMode = "demo_fixtures";
      }
    }

    const r = inMemoryReports.find((item) => item.id === reportId) || inMemoryReports[0];
    return `# ORACLE Intelligence Dossier: ${r.event_title}\n\n**Severity**: ${r.severity.toUpperCase()}\n**Technology**: ${r.primary_technology} (${r.ecosystem})\n**Generated**: ${r.generated_at}\n\n## Executive Summary\n${r.executive_summary}\n\n## Root Cause Analysis\n${r.technical_root_cause}\n\n## Breaking Changes\n${r.breaking_changes.map((bc) => `- ${bc}`).join("\n")}\n\n## Mitigation Playbook\n${r.mitigation_playbook.map((s) => `### Step ${s.step_number}: ${s.title}\n${s.description}\n\n\`\`\`\n${s.code_or_command || ""}\n\`\`\`\n`).join("\n")}\n`;
  },

  // Ingestion Sources
  async getSources(): Promise<IngestionSource[]> {
    if (currentConnectionMode === "connected") {
      try {
        return await requestWithTimeout<IngestionSource[]>("/ingest/sources");
      } catch {
        currentConnectionMode = "demo_fixtures";
      }
    }
    return inMemorySources;
  },

  async triggerSync(sourceId?: string): Promise<{
    status: string;
    signals_ingested: number;
    events_detected: number;
    event_ids: string[];
  }> {
    if (currentConnectionMode === "connected") {
      try {
        const query = sourceId ? `?source_id=${sourceId}` : "";
        return await requestWithTimeout(`/ingest/sync${query}`, { method: "POST" });
      } catch {
        currentConnectionMode = "demo_fixtures";
      }
    }

    // Demo simulation
    await new Promise((resolve) => setTimeout(resolve, 800));
    if (sourceId) {
      inMemorySources = inMemorySources.map((s) =>
        s.id === sourceId ? { ...s, last_synced_at: new Date().toISOString(), last_status: "success" } : s
      );
    } else {
      inMemorySources = inMemorySources.map((s) => ({
        ...s,
        last_synced_at: new Date().toISOString(),
        last_status: "success",
      }));
    }

    return {
      status: "success",
      signals_ingested: 8,
      events_detected: 2,
      event_ids: ["evt-pydantic-v2", "evt-fastapi-lifespan"],
    };
  },

  // Timeline Events
  async getTimelineEvents(): Promise<TimelineEvent[]> {
    return inMemoryTimeline;
  },

  // Monitoring Rules
  async getMonitoringRules(): Promise<MonitoringRule[]> {
    return inMemoryRules;
  },

  async toggleMonitoringRule(ruleId: string): Promise<MonitoringRule> {
    inMemoryRules = inMemoryRules.map((r) => (r.id === ruleId ? { ...r, enabled: !r.enabled } : r));
    const updated = inMemoryRules.find((r) => r.id === ruleId)!;
    return updated;
  },

  async createMonitoringRule(rule: Omit<MonitoringRule, "id" | "trigger_count" | "last_triggered_at">): Promise<MonitoringRule> {
    const newRule: MonitoringRule = {
      ...rule,
      id: `rule-${Date.now().toString(36)}`,
      trigger_count: 0,
    };
    inMemoryRules = [newRule, ...inMemoryRules];
    return newRule;
  },

  // Investigations Copilot
  async getInvestigationSessions(): Promise<InvestigationSession[]> {
    return inMemoryInvestigations;
  },

  async getInvestigationById(id: string): Promise<InvestigationSession | null> {
    return inMemoryInvestigations.find((s) => s.id === id) || null;
  },

  async createInvestigationSession(title: string, technology: string): Promise<InvestigationSession> {
    const newSession: InvestigationSession = {
      id: `inv-${Date.now().toString(36)}`,
      title,
      primary_technology: technology,
      severity: "high",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      status: "active",
      messages: [
        {
          id: `msg-${Date.now().toString(36)}`,
          role: "assistant",
          content: `Initialized investigation session for **${technology}**. Ask any technical questions about upcoming breaking changes, deprecation timelines, security CVEs, or blast radius impacts.`,
          timestamp: new Date().toISOString(),
          suggestedFollowUps: [
            `What breaking changes are planned for ${technology}?`,
            `Show dependencies that import ${technology}`,
            `Generate migration script`,
          ],
        },
      ],
    };
    inMemoryInvestigations = [newSession, ...inMemoryInvestigations];
    return newSession;
  },

  async sendInvestigationMessage(
    sessionId: string,
    userQuery: string,
    onChunk?: (token: string) => void
  ): Promise<InvestigationMessage> {
    const session = inMemoryInvestigations.find((s) => s.id === sessionId);
    const userMsg: InvestigationMessage = {
      id: `msg-u-${Date.now().toString(36)}`,
      role: "user",
      content: userQuery,
      timestamp: new Date().toISOString(),
    };

    if (session) {
      session.messages.push(userMsg);
      session.updated_at = new Date().toISOString();
    }

    // Dynamic intelligent response generation based on prompt
    const tech = session?.primary_technology || "the target technology";
    const qLower = userQuery.toLowerCase();

    let fullAnswer = "";
    let citations = MOCK_INTELLIGENCE_EVENTS[0].evidence;
    let codeSnippets: InvestigationMessage["codeSnippets"] = undefined;
    let suggestedFollowUps: string[] = [];

    if (qLower.includes("cve") || qLower.includes("security") || qLower.includes("vulnerab")) {
      fullAnswer = `### Security Analysis: ${tech}\n\nORACLE vulnerability scanners cross-referenced **NVD CVE advisories** and upstream security patches:\n\n- **Impact Rating**: Critical (CVSS 9.8)\n- **Affected Versions**: Unpatched minor releases before the latest security milestone.\n- **Attack Vector**: Direct remote execution through unvalidated parser hooks.\n\nRecommended immediate action: Upgrade dependencies and enforce strict input validation schemas.`;
      citations = [MOCK_INTELLIGENCE_EVENTS[2].evidence[0]];
      suggestedFollowUps = [
        "Generate automated remediation script",
        "Which downstream packages inherit this vulnerability?",
      ];
    } else if (qLower.includes("blast") || qLower.includes("depend")) {
      fullAnswer = `### Temporal Graph Blast Radius: ${tech}\n\nTraversing the **ORACLE Temporal Dependency Graph** reveals:\n\n- **Direct Dependents**: 3 packages in your current stack rely directly on ${tech}.\n- **Transitive Impact**: 5 upstream services inherit breaking changes through transitive bindings.\n- **Criticality**: High risk of regression if interfaces change without automated migration.`;
      suggestedFollowUps = [
        "Open Knowledge Graph view for this entity",
        "Generate full Impact Dossier",
      ];
    } else if (qLower.includes("migrat") || qLower.includes("upgrade") || qLower.includes("code")) {
      fullAnswer = `### Migration & Compatibility Playbook: ${tech}\n\nTo safely upgrade without breaking production endpoints:\n\n1. Update dependency constraints in your lockfile.\n2. Apply AST code rewrites to replace legacy calls.\n3. Run the validation test harness.`;
      codeSnippets = [
        {
          language: "python",
          filename: "migration_example.py",
          code: `# Safe modernization snippet\nfrom pydantic import BaseModel, ConfigDict\n\nclass ModernSchema(BaseModel):\n    model_config = ConfigDict(populate_by_name=True)\n    name: str\n    version: str`,
        },
      ];
      suggestedFollowUps = [
        "What are the breaking changes in the latest release?",
        "How do I verify backwards compatibility?",
      ];
    } else {
      fullAnswer = `Based on live intelligence gathered across changelogs, commits, and issue trackers for **${tech}**:\n\nThe ecosystem is moving toward strict type enforcement and compilation-assisted performance. Ensure your application verifies interface signatures before deploying to production.`;
      suggestedFollowUps = [
        `What breaking changes are in ${tech}?`,
        `Show blast radius for ${tech}`,
        `Audit security CVEs for ${tech}`,
      ];
    }

    // If caller provided onChunk, stream out the response token by token
    if (onChunk) {
      const words = fullAnswer.split(" ");
      for (const word of words) {
        onChunk(word + " ");
        await new Promise((r) => setTimeout(r, 18));
      }
    }

    const assistantMsg: InvestigationMessage = {
      id: `msg-a-${Date.now().toString(36)}`,
      role: "assistant",
      content: fullAnswer,
      timestamp: new Date().toISOString(),
      citations,
      codeSnippets,
      suggestedFollowUps,
    };

    if (session) {
      session.messages.push(assistantMsg);
      session.updated_at = new Date().toISOString();
    }

    return assistantMsg;
  },

  // Notifications
  async getNotifications(): Promise<NotificationItem[]> {
    return MOCK_NOTIFICATIONS;
  },
};
