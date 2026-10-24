import React, { useEffect, useState } from "react";
import {
  AlertTriangle,
  Bell,
  CheckCircle2,
  Clock,
  Edit3,
  ExternalLink,
  Filter,
  History,
  Layers,
  ListFilter,
  Plus,
  Power,
  RefreshCw,
  Search,
  Send,
  Shield,
  ShieldAlert,
  Sparkles,
  Tag,
  Trash2,
  X,
  Zap,
} from "lucide-react";
import { api } from "../api/client";
import {
  AlertRecord,
  ChangeCategory,
  MonitoringRule,
  SeverityLevel,
} from "../types";

interface MonitoringRulesViewProps {
  rules: MonitoringRule[];
  onToggleRule: (ruleId: string) => void;
  onCreateRule: (rule: Omit<MonitoringRule, "id" | "trigger_count" | "last_triggered_at">) => void;
  onUpdateRule?: (ruleId: string, rule: Partial<MonitoringRule>) => void;
  onDeleteRule?: (ruleId: string) => void;
  onNavigateToInvestigation?: (investigationId: string) => void;
}

export const MonitoringRulesView: React.FC<MonitoringRulesViewProps> = ({
  rules,
  onToggleRule,
  onCreateRule,
  onUpdateRule,
  onDeleteRule,
  onNavigateToInvestigation,
}) => {
  const [activeTab, setActiveTab] = useState<"rules" | "alerts">("rules");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRuleId, setEditingRuleId] = useState<string | null>(null);

  // Form State
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [targetType, setTargetType] = useState<
    "technology" | "api" | "product" | "repository" | "security_advisory" | "topic"
  >("technology");
  const [category, setCategory] = useState<ChangeCategory | "any">("any");
  const [minSeverity, setMinSeverity] = useState<SeverityLevel>("high");
  const [ecosystem, setEcosystem] = useState("all");
  const [techPattern, setTechPattern] = useState("");
  const [channels, setChannels] = useState<("webhook" | "slack" | "email" | "pagerduty" | "in_app")[]>([
    "in_app",
    "slack",
    "webhook",
  ]);
  const [autoTriggerInvestigation, setAutoTriggerInvestigation] = useState(true);
  const [includeDossier, setIncludeDossier] = useState(true);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [slackChannel, setSlackChannel] = useState("#oracle-alerts");

  // Alert Audit State
  const [alertRecords, setAlertRecords] = useState<AlertRecord[]>([]);
  const [isLoadingAlerts, setIsLoadingAlerts] = useState(false);

  // Filter & Search
  const [searchQuery, setSearchQuery] = useState("");
  const [targetFilter, setTargetFilter] = useState<string>("all");

  const loadAlerts = async () => {
    setIsLoadingAlerts(true);
    try {
      const records = await api.getAlertRecords();
      setAlertRecords(records);
    } catch (e) {
      console.error("Failed to load alerts", e);
    } finally {
      setIsLoadingAlerts(false);
    }
  };

  useEffect(() => {
    if (activeTab === "alerts") {
      loadAlerts();
    }
  }, [activeTab]);

  const handleToggleChannel = (chan: "webhook" | "slack" | "email" | "pagerduty" | "in_app") => {
    if (channels.includes(chan)) {
      setChannels(channels.filter((c) => c !== chan));
    } else {
      setChannels([...channels, chan]);
    }
  };

  const handleOpenCreate = () => {
    setEditingRuleId(null);
    setName("");
    setDescription("");
    setTargetType("technology");
    setCategory("any");
    setMinSeverity("high");
    setEcosystem("all");
    setTechPattern("*");
    setChannels(["in_app", "slack", "webhook"]);
    setAutoTriggerInvestigation(true);
    setIncludeDossier(true);
    setWebhookUrl("");
    setSlackChannel("#oracle-alerts");
    setIsModalOpen(true);
  };

  const handleOpenEdit = (rule: MonitoringRule) => {
    setEditingRuleId(rule.id);
    setName(rule.name);
    setDescription(rule.description || "");
    setTargetType(rule.target_type || "technology");
    setCategory(rule.category);
    setMinSeverity(rule.min_severity);
    setEcosystem(rule.ecosystem || "all");
    setTechPattern(rule.technology_pattern || "*");
    setChannels(rule.alert_channels || ["in_app"]);
    setAutoTriggerInvestigation(rule.notification_preferences?.auto_trigger_investigation ?? true);
    setIncludeDossier(rule.notification_preferences?.include_dossier ?? true);
    setWebhookUrl(rule.notification_preferences?.webhook_url || "");
    setSlackChannel(rule.notification_preferences?.slack_channel || "");
    setIsModalOpen(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    const payload = {
      name: name.trim(),
      description: description.trim() || "Automated monitoring rule",
      target_type: targetType,
      category,
      min_severity: minSeverity,
      ecosystem,
      technology_pattern: techPattern.trim() || "*",
      enabled: true,
      alert_channels: channels,
      notification_preferences: {
        auto_trigger_investigation: autoTriggerInvestigation,
        include_dossier: includeDossier,
        webhook_url: webhookUrl.trim() || undefined,
        slack_channel: slackChannel.trim() || undefined,
      },
    };

    if (editingRuleId && onUpdateRule) {
      onUpdateRule(editingRuleId, payload);
    } else {
      onCreateRule(payload);
    }

    setIsModalOpen(false);
  };

  const filteredRules = rules.filter((rule) => {
    const matchesSearch =
      rule.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      rule.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      rule.technology_pattern.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesTarget =
      targetFilter === "all" || (rule.target_type || "technology") === targetFilter;
    return matchesSearch && matchesTarget;
  });

  const activeCount = rules.filter((r) => r.enabled).length;
  const pausedCount = rules.length - activeCount;

  return (
    <div className="space-y-6">
      {/* Top Banner & Control Deck */}
      <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur-md flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold font-mono text-white flex items-center space-x-2">
                <span>Autonomous Monitoring & Watch Rules</span>
                <span className="text-[11px] px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-normal">
                  Idempotent & Bounded
                </span>
              </h3>
              <p className="text-xs text-slate-400">
                Continuous technology, API, repository, CVE, and topic watchers with automated impact triage.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2 shrink-0">
          {/* Tab selector */}
          <div className="flex rounded-lg bg-slate-950 p-1 border border-slate-800 text-xs font-mono">
            <button
              onClick={() => setActiveTab("rules")}
              className={`px-3 py-1.5 rounded-md transition-colors flex items-center space-x-1.5 ${
                activeTab === "rules"
                  ? "bg-slate-800 text-cyan-300 font-bold shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Shield className="w-3.5 h-3.5" />
              <span>Rules ({rules.length})</span>
            </button>
            <button
              onClick={() => setActiveTab("alerts")}
              className={`px-3 py-1.5 rounded-md transition-colors flex items-center space-x-1.5 ${
                activeTab === "alerts"
                  ? "bg-slate-800 text-cyan-300 font-bold shadow"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <History className="w-3.5 h-3.5" />
              <span>Audit Log & Alerts</span>
            </button>
          </div>

          <button
            onClick={handleOpenCreate}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-bold font-mono transition-all shadow-glow"
          >
            <Plus className="w-4 h-4" />
            <span>New Rule</span>
          </button>
        </div>
      </div>

      {activeTab === "rules" ? (
        <>
          {/* Quick Stats & Filters */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 text-xs font-mono">
            {/* Filter pills */}
            <div className="flex items-center space-x-1.5 overflow-x-auto pb-1 sm:pb-0">
              <span className="text-slate-500 flex items-center space-x-1 px-1">
                <Filter className="w-3.5 h-3.5" />
              </span>
              {[
                { id: "all", label: "All Targets" },
                { id: "technology", label: "Tech" },
                { id: "api", label: "APIs" },
                { id: "product", label: "Products" },
                { id: "repository", label: "Repos" },
                { id: "security_advisory", label: "Advisories" },
                { id: "topic", label: "Topics" },
              ].map((tf) => (
                <button
                  key={tf.id}
                  onClick={() => setTargetFilter(tf.id)}
                  className={`px-2.5 py-1 rounded-lg border uppercase text-[10px] transition-colors whitespace-nowrap ${
                    targetFilter === tf.id
                      ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/40 font-bold"
                      : "bg-slate-900/60 text-slate-400 border-slate-800 hover:border-slate-700"
                  }`}
                >
                  {tf.label}
                </button>
              ))}
            </div>

            {/* Search */}
            <div className="relative min-w-[220px]">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search rules..."
                className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-300 placeholder-slate-600 focus:outline-none focus:border-cyan-500 text-xs"
              />
            </div>
          </div>

          {/* Rules Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredRules.map((rule) => {
              const pref = rule.notification_preferences;
              return (
                <div
                  key={rule.id}
                  className={`p-5 rounded-2xl border transition-all flex flex-col justify-between space-y-4 ${
                    rule.enabled
                      ? "bg-slate-900/60 border-slate-800 hover:border-slate-700 shadow-md"
                      : "bg-slate-950/40 border-slate-800/40 opacity-60"
                  }`}
                >
                  <div>
                    {/* Header */}
                    <div className="flex items-start justify-between gap-3">
                      <div className="space-y-1.5">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded font-bold bg-slate-800 text-cyan-300 border border-slate-700 flex items-center space-x-1">
                            <Tag className="w-2.5 h-2.5 mr-0.5" />
                            <span>{rule.target_type || "technology"}</span>
                          </span>

                          <span
                            className={`text-[10px] uppercase font-mono px-2 py-0.5 rounded font-bold border ${
                              rule.min_severity === "critical"
                                ? "bg-rose-950/80 text-rose-300 border-rose-800"
                                : rule.min_severity === "high"
                                ? "bg-amber-950/80 text-amber-300 border-amber-800"
                                : "bg-sky-950/80 text-sky-300 border-sky-800"
                            }`}
                          >
                            Min: {rule.min_severity}
                          </span>

                          <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-950 text-slate-400 border border-slate-800">
                            {rule.ecosystem}
                          </span>

                          {pref?.auto_trigger_investigation && (
                            <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-indigo-950/60 text-indigo-300 border border-indigo-800/60 flex items-center space-x-1">
                              <Sparkles className="w-2.5 h-2.5 text-indigo-400" />
                              <span>Auto-Investigate</span>
                            </span>
                          )}
                        </div>

                        <h4 className="text-sm font-bold font-mono text-white mt-1">
                          {rule.name}
                        </h4>
                      </div>

                      {/* Rule Action Controls */}
                      <div className="flex items-center space-x-1">
                        <button
                          onClick={() => handleOpenEdit(rule)}
                          className="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white transition-colors"
                          title="Edit Rule Configuration"
                        >
                          <Edit3 className="w-3.5 h-3.5" />
                        </button>

                        {onDeleteRule && (
                          <button
                            onClick={() => {
                              if (confirm(`Delete monitoring rule "${rule.name}"?`)) {
                                onDeleteRule(rule.id);
                              }
                            }}
                            className="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-rose-400 transition-colors"
                            title="Delete Rule"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}

                        <button
                          onClick={() => onToggleRule(rule.id)}
                          className={`p-1.5 rounded-lg transition-colors ${
                            rule.enabled
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/20"
                              : "bg-slate-800 text-slate-500 hover:text-slate-300"
                          }`}
                          title={
                            rule.enabled
                              ? "Rule is Active (click to pause)"
                              : "Rule is Paused (click to activate)"
                          }
                        >
                          <Power className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    {/* Description */}
                    <p className="text-xs text-slate-300 font-sans leading-relaxed mt-2.5">
                      {rule.description}
                    </p>

                    {/* Filter Criteria */}
                    <div className="mt-3 p-2.5 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1.5 text-xs font-mono">
                      <div className="flex items-center justify-between text-slate-400">
                        <span className="text-slate-500">Pattern Filter:</span>
                        <span className="text-cyan-400 font-semibold truncate max-w-[200px]">
                          {rule.technology_pattern}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-slate-400">
                        <span className="text-slate-500">Category Filter:</span>
                        <span className="text-slate-300 capitalize">{rule.category}</span>
                      </div>
                      {pref?.slack_channel && (
                        <div className="flex items-center justify-between text-slate-400">
                          <span className="text-slate-500">Slack Dispatch:</span>
                          <span className="text-slate-300">{pref.slack_channel}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Channels & Triggers Footer */}
                  <div className="pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-xs font-mono">
                    <div className="flex items-center space-x-1">
                      {rule.alert_channels.map((ch) => (
                        <span
                          key={ch}
                          className="text-[9px] uppercase px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700"
                        >
                          {ch}
                        </span>
                      ))}
                    </div>

                    <div className="text-slate-400 text-[11px] flex items-center space-x-2">
                      {rule.last_triggered_at && (
                        <span className="text-slate-500 text-[10px]">
                          Last: {new Date(rule.last_triggered_at).toLocaleTimeString()}
                        </span>
                      )}
                      <span>
                        Fired <span className="text-cyan-400 font-bold">{rule.trigger_count}</span>x
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {filteredRules.length === 0 && (
            <div className="p-8 rounded-2xl bg-slate-900/30 border border-slate-800 text-center text-slate-500 font-mono text-xs">
              No monitoring rules matching the selected filter.
            </div>
          )}
        </>
      ) : (
        /* Alert History & Audit Log Section */
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs font-mono">
            <div className="text-slate-400 flex items-center space-x-2">
              <History className="w-4 h-4 text-cyan-400" />
              <span>Deduplicated Alert Audit Trail</span>
              <span className="text-[10px] text-slate-500">
                (Strictly key-deduplicated per Rule + Event + Version)
              </span>
            </div>

            <button
              onClick={loadAlerts}
              disabled={isLoadingAlerts}
              className="flex items-center space-x-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono"
            >
              <RefreshCw className={`w-3 h-3 ${isLoadingAlerts ? "animate-spin text-cyan-400" : ""}`} />
              <span>Refresh Log</span>
            </button>
          </div>

          {isLoadingAlerts ? (
            <div className="p-8 text-center text-xs font-mono text-slate-400 animate-pulse">
              Querying historical alert records...
            </div>
          ) : alertRecords.length === 0 ? (
            <div className="p-8 rounded-2xl bg-slate-900/40 border border-slate-800 text-center text-slate-500 font-mono text-xs">
              No alert dispatches recorded yet. Alerts will appear here when scheduled ingestion runs detect events matching active rules.
            </div>
          ) : (
            <div className="space-y-2.5">
              {alertRecords.map((alert) => (
                <div
                  key={alert.id}
                  className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs font-mono hover:border-slate-700 transition-all"
                >
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span
                        className={`text-[9px] uppercase px-1.5 py-0.5 rounded font-bold border ${
                          alert.severity === "critical"
                            ? "bg-rose-950 text-rose-300 border-rose-800"
                            : alert.severity === "high"
                            ? "bg-amber-950 text-amber-300 border-amber-800"
                            : "bg-sky-950 text-sky-300 border-sky-800"
                        }`}
                      >
                        {alert.severity}
                      </span>
                      <span className="text-white font-bold">{alert.event_title}</span>
                      <span className="text-cyan-400 text-[11px]">v{alert.event_version}</span>
                    </div>

                    <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-400">
                      <span>Triggered by: <span className="text-slate-200">{alert.rule_name}</span></span>
                      <span>•</span>
                      <span>Dispatched: {new Date(alert.dispatched_at).toLocaleString()}</span>
                      <span>•</span>
                      <span className="text-[10px] text-slate-500 font-mono truncate max-w-[220px]" title={alert.dedup_key}>
                        Key: {alert.dedup_key}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2 shrink-0">
                    <div className="flex space-x-1">
                      {alert.channels.map((c) => (
                        <span key={c} className="text-[9px] uppercase px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                          {c}
                        </span>
                      ))}
                    </div>

                    {alert.investigation_id && onNavigateToInvestigation && (
                      <button
                        onClick={() => onNavigateToInvestigation(alert.investigation_id!)}
                        className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 hover:bg-indigo-500/20 text-[10px] font-bold"
                      >
                        <Sparkles className="w-3 h-3 text-indigo-400" />
                        <span>Investigation</span>
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Create / Edit Rule Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-xl max-h-[90vh] overflow-y-auto rounded-2xl bg-slate-900 border border-slate-800 p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-base font-bold font-mono text-white flex items-center space-x-2">
                <Shield className="w-4 h-4 text-cyan-400" />
                <span>{editingRuleId ? "Edit Monitoring Rule" : "Configure New Monitoring Rule"}</span>
              </h3>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4 text-xs font-mono">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1 sm:col-span-2">
                  <label className="text-slate-400">Rule Name</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. FastAPI Core Lifespan Watch"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div className="space-y-1 sm:col-span-2">
                  <label className="text-slate-400">Description</label>
                  <textarea
                    rows={2}
                    placeholder="Explain when this rule should trigger alerts and auto-investigations..."
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-slate-400">Target Type</label>
                  <select
                    value={targetType}
                    onChange={(e) => setTargetType(e.target.value as any)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="technology">Technology / Framework</option>
                    <option value="api">API / Endpoint</option>
                    <option value="product">Product</option>
                    <option value="repository">GitHub Repository</option>
                    <option value="security_advisory">Security Advisory (CVE)</option>
                    <option value="topic">Topic / Domain</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-slate-400">Minimum Severity Gate</label>
                  <select
                    value={minSeverity}
                    onChange={(e) => setMinSeverity(e.target.value as SeverityLevel)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="critical">Critical (Highest Urgency)</option>
                    <option value="high">High (Breaking & Security)</option>
                    <option value="medium">Medium (Deprecations & Shifts)</option>
                    <option value="low">Low (All Minor Events)</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-slate-400">Change Category Gate</label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value as any)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="any">Any Category</option>
                    <option value="breaking_change">Breaking Changes Only</option>
                    <option value="security_vulnerability">Security Vulnerabilities</option>
                    <option value="deprecation">Deprecations</option>
                    <option value="outage">Infrastructure Outages</option>
                    <option value="api_change">API Schema Changes</option>
                    <option value="architecture_shift">Architecture Shifts</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-slate-400">Ecosystem</label>
                  <select
                    value={ecosystem}
                    onChange={(e) => setEcosystem(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="all">All Ecosystems</option>
                    <option value="python">Python</option>
                    <option value="node">Node / TypeScript</option>
                    <option value="cloud">Cloud / Distributed</option>
                    <option value="security">Security / NIST</option>
                  </select>
                </div>

                <div className="space-y-1 sm:col-span-2">
                  <label className="text-slate-400">Technology / Keyword Pattern (Regex or * for all)</label>
                  <input
                    type="text"
                    placeholder="e.g. fastapi|pydantic|langchain (or * for wildcard)"
                    value={techPattern}
                    onChange={(e) => setTechPattern(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                </div>
              </div>

              {/* Notification Preferences */}
              <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 space-y-3">
                <span className="text-[11px] font-bold text-slate-300 uppercase tracking-wider block">
                  Automated Actions & Preferences
                </span>

                <div className="space-y-2">
                  <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={autoTriggerInvestigation}
                      onChange={(e) => setAutoTriggerInvestigation(e.target.checked)}
                      className="rounded bg-slate-900 border-slate-700 text-cyan-500 focus:ring-0"
                    />
                    <span className="text-slate-300">
                      Auto-trigger Temporal Graph Investigation & Impact Dossier on match
                    </span>
                  </label>

                  <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={includeDossier}
                      onChange={(e) => setIncludeDossier(e.target.checked)}
                      className="rounded bg-slate-900 border-slate-700 text-cyan-500 focus:ring-0"
                    />
                    <span className="text-slate-300">
                      Include blast-radius evidence citations in alert payload
                    </span>
                  </label>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                  <div className="space-y-1">
                    <label className="text-slate-500">Slack Channel (optional)</label>
                    <input
                      type="text"
                      placeholder="#oracle-critical"
                      value={slackChannel}
                      onChange={(e) => setSlackChannel(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-slate-500">Webhook URL (optional)</label>
                    <input
                      type="text"
                      placeholder="https://hooks.slack.com/services/..."
                      value={webhookUrl}
                      onChange={(e) => setWebhookUrl(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                </div>
              </div>

              {/* Alert Destinations */}
              <div className="space-y-1.5">
                <label className="text-slate-400">Dispatch Channels</label>
                <div className="flex flex-wrap gap-2">
                  {(["in_app", "slack", "webhook", "email", "pagerduty"] as const).map((chan) => (
                    <button
                      key={chan}
                      type="button"
                      onClick={() => handleToggleChannel(chan)}
                      className={`px-3 py-1.5 rounded-lg border uppercase text-[10px] font-mono transition-colors ${
                        channels.includes(chan)
                          ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/40 font-bold"
                          : "bg-slate-950 text-slate-500 border-slate-800"
                      }`}
                    >
                      {channels.includes(chan) ? `✓ ${chan}` : `+ ${chan}`}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-end space-x-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-lg text-slate-400 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-cyan-500 text-slate-950 hover:bg-cyan-400 font-bold shadow-glow"
                >
                  {editingRuleId ? "Update Monitoring Rule" : "Save Monitoring Rule"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
