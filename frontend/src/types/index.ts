export type ChangeCategory =
  | "breaking_change"
  | "deprecation"
  | "security_vulnerability"
  | "outage"
  | "performance_regression"
  | "major_release"
  | "patch"
  | "general_update";

export type SeverityLevel = "critical" | "high" | "medium" | "low" | "info";

export interface EvidenceRef {
  source_url: string;
  source_type: string;
  title: string;
  snippet: string;
  published_at?: string;
  content_hash: string;
}

export interface IntelligenceEvent {
  id: string;
  raw_signal_id: string;
  category: ChangeCategory;
  severity: SeverityLevel;
  title: string;
  summary: string;
  primary_technology: string;
  affected_entities: string[];
  version_affected?: string;
  version_fixed?: string;
  cve_id?: string;
  confidence: number;
  detection_rationale: string;
  evidence: EvidenceRef[];
  timestamp: string;
  is_live_data: boolean;
  metadata: Record<string, any>;
}

export interface TemporalGraphNode {
  id: string;
  name: string;
  node_type: "technology" | "package" | "service" | "organization" | "specification" | "database";
  ecosystem: string;
  latest_version?: string;
  first_seen?: string;
  last_updated?: string;
  description?: string;
  properties?: Record<string, any>;
}

export interface TemporalGraphEdge {
  source: string;
  target: string;
  edge_type: "depends_on" | "integrates_with" | "deprecated_by" | "affected_by" | "maintained_by";
  valid_from: string;
  valid_to?: string;
  version_constraint?: string;
  confidence?: number;
  properties?: Record<string, any>;
}

export interface GraphSnapshot {
  nodes: TemporalGraphNode[];
  edges: TemporalGraphEdge[];
  node_count: number;
  edge_count: number;
  generated_at: string;
}

export interface BlastRadiusNode {
  node_id: string;
  name: string;
  node_type: "technology" | "package" | "service" | "organization" | "specification" | "database";
  ecosystem: string;
  depth: number;
  relationship_path: string[];
  impact_likelihood: number;
  vulnerability_reasons: string[];
}

export interface BlastRadiusReport {
  root_entity: string;
  event_id?: string;
  max_traversal_depth: number;
  total_nodes_scanned: number;
  direct_dependents_count: number;
  transitive_dependents_count: number;
  affected_nodes: BlastRadiusNode[];
  analysis_timestamp: string;
}

export interface MitigationAction {
  step_number: number;
  title: string;
  description: string;
  priority: SeverityLevel;
  action_type: string;
  code_or_command?: string;
  verification_check?: string;
  estimated_effort: string;
}

export interface ImpactReport {
  id: string;
  event_id: string;
  event_title: string;
  severity: SeverityLevel;
  primary_technology: string;
  ecosystem: string;
  executive_summary: string;
  technical_root_cause: string;
  breaking_changes: string[];
  impacted_components: BlastRadiusNode[];
  evidence_trail: EvidenceRef[];
  mitigation_playbook: MitigationAction[];
  confidence_score: number;
  llm_provenance: Record<string, any>;
  generated_at: string;
  is_live_data: boolean;
}

export interface IngestionSource {
  id: string;
  name: string;
  url: string;
  source_type: "rss" | "github_releases" | "security_advisory" | "status_page" | "changelog";
  enabled: boolean;
  ecosystem: string;
  refresh_interval_minutes: number;
  last_synced_at?: string;
  last_status?: string;
}

export interface SystemHealth {
  status: string;
  app_name: string;
  environment: string;
  llm_provider: string;
  llm_model: string;
  sources_count: number;
  signals_count: number;
  events_count: number;
  reports_count: number;
  graph: {
    nodes: number;
    edges: number;
  };
}

export type NavigationTab =
  | "overview"
  | "signals"
  | "investigations"
  | "graph"
  | "reports"
  | "timeline"
  | "rules"
  | "sources"
  | "settings";

export type ConnectionMode = "connected" | "demo_fixtures" | "connecting" | "error";

export interface InvestigationMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  citations?: EvidenceRef[];
  suggestedFollowUps?: string[];
  codeSnippets?: Array<{ language: string; code: string; filename?: string }>;
}

export interface InvestigationSession {
  id: string;
  title: string;
  primary_technology: string;
  severity: SeverityLevel;
  created_at: string;
  updated_at: string;
  messages: InvestigationMessage[];
  status: "active" | "resolved" | "archived";
}

export type LifecycleStage = "published" | "ingested" | "updated" | "superseded";

export interface TimelineEvent {
  id: string;
  eventId: string;
  stage: LifecycleStage;
  title: string;
  primary_technology: string;
  timestamp: string;
  summary: string;
  latency_from_publish?: string;
  superseded_by?: string;
  version?: string;
}

export interface MonitoringRule {
  id: string;
  name: string;
  description: string;
  category: ChangeCategory | "any";
  min_severity: SeverityLevel;
  ecosystem: string;
  technology_pattern: string;
  enabled: boolean;
  trigger_count: number;
  last_triggered_at?: string;
  alert_channels: ("webhook" | "slack" | "email" | "pagerduty")[];
}

export interface NotificationItem {
  id: string;
  title: string;
  description: string;
  severity: SeverityLevel;
  timestamp: string;
  read: boolean;
  category: ChangeCategory;
  targetTab?: NavigationTab;
  targetId?: string;
}

