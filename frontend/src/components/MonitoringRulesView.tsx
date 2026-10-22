import React, { useState } from "react";
import {
  Bell,
  Check,
  CheckCircle2,
  Clock,
  Eye,
  Filter,
  Plus,
  Power,
  Radio,
  Send,
  Shield,
  ShieldAlert,
  Sparkles,
  ToggleLeft,
  ToggleRight,
  X,
} from "lucide-react";
import { ChangeCategory, MonitoringRule, SeverityLevel } from "../types";

interface MonitoringRulesViewProps {
  rules: MonitoringRule[];
  onToggleRule: (ruleId: string) => void;
  onCreateRule: (rule: Omit<MonitoringRule, "id" | "trigger_count" | "last_triggered_at">) => void;
}

export const MonitoringRulesView: React.FC<MonitoringRulesViewProps> = ({
  rules,
  onToggleRule,
  onCreateRule,
}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<ChangeCategory | "any">("any");
  const [minSeverity, setMinSeverity] = useState<SeverityLevel>("high");
  const [ecosystem, setEcosystem] = useState("all");
  const [techPattern, setTechPattern] = useState("");
  const [channels, setChannels] = useState<("webhook" | "slack" | "email" | "pagerduty")[]>([
    "slack",
    "webhook",
  ]);

  const handleToggleChannel = (chan: "webhook" | "slack" | "email" | "pagerduty") => {
    if (channels.includes(chan)) {
      setChannels(channels.filter((c) => c !== chan));
    } else {
      setChannels([...channels, chan]);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    onCreateRule({
      name: name.trim(),
      description: description.trim() || "Automated monitoring rule",
      category,
      min_severity: minSeverity,
      ecosystem,
      technology_pattern: techPattern.trim() || "*",
      enabled: true,
      alert_channels: channels,
    });

    setName("");
    setDescription("");
    setTechPattern("");
    setIsModalOpen(false);
  };

  return (
    <div className="space-y-6">
      {/* Title & Stats */}
      <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-bold font-mono text-white flex items-center space-x-2">
            <ShieldAlert className="w-5 h-5 text-cyan-400" />
            <span>Autonomous Monitoring & Watch Rules</span>
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Realtime event triggers, severity gates, and proactive dispatch to incident response webhooks.
          </p>
        </div>

        <button
          onClick={() => setIsModalOpen(true)}
          className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-cyan-500 text-slate-950 hover:bg-cyan-400 text-xs font-bold font-mono transition-all shadow-glow shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>New Monitoring Rule</span>
        </button>
      </div>

      {/* Rules Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {rules.map((rule) => {
          return (
            <div
              key={rule.id}
              className={`p-5 rounded-2xl border transition-all space-y-4 ${
                rule.enabled
                  ? "bg-slate-900/60 border-slate-800 hover:border-slate-700"
                  : "bg-slate-950/40 border-slate-800/40 opacity-60"
              }`}
            >
              {/* Header */}
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <span
                      className={`text-[10px] uppercase font-mono px-2 py-0.5 rounded font-bold border ${
                        rule.min_severity === "critical"
                          ? "bg-rose-950 text-rose-400 border-rose-800"
                          : rule.min_severity === "high"
                          ? "bg-amber-950 text-amber-400 border-amber-800"
                          : "bg-sky-950 text-sky-400 border-sky-800"
                      }`}
                    >
                      Min: {rule.min_severity}
                    </span>
                    <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                      Eco: {rule.ecosystem}
                    </span>
                  </div>
                  <h4 className="text-sm font-bold font-mono text-white mt-1">{rule.name}</h4>
                </div>

                <button
                  onClick={() => onToggleRule(rule.id)}
                  className={`p-1.5 rounded-lg transition-colors ${
                    rule.enabled
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/20"
                      : "bg-slate-800 text-slate-500 hover:text-slate-300"
                  }`}
                  title={rule.enabled ? "Rule is Active (click to pause)" : "Rule is Paused (click to activate)"}
                >
                  <Power className="w-4 h-4" />
                </button>
              </div>

              {/* Description */}
              <p className="text-xs text-slate-300 font-sans leading-relaxed">{rule.description}</p>

              {/* Filter Criteria */}
              <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800 space-y-1 text-xs font-mono">
                <div className="flex items-center justify-between text-slate-400">
                  <span className="text-slate-500">Tech Pattern:</span>
                  <span className="text-cyan-400 font-semibold">{rule.technology_pattern}</span>
                </div>
                <div className="flex items-center justify-between text-slate-400">
                  <span className="text-slate-500">Category Filter:</span>
                  <span className="text-slate-300 capitalize">{rule.category}</span>
                </div>
              </div>

              {/* Channels & Triggers Footer */}
              <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs font-mono">
                <div className="flex items-center space-x-1">
                  {rule.alert_channels.map((ch) => (
                    <span
                      key={ch}
                      className="text-[10px] uppercase px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700"
                    >
                      {ch}
                    </span>
                  ))}
                </div>

                <div className="text-slate-400 text-[11px]">
                  Fired <span className="text-cyan-400 font-bold">{rule.trigger_count}</span> times
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* New Rule Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-lg rounded-2xl bg-slate-900 border border-slate-800 p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-base font-bold font-mono text-white flex items-center space-x-2">
                <Shield className="w-4 h-4 text-cyan-400" />
                <span>Configure Monitoring Rule</span>
              </h3>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4 text-xs font-mono">
              <div className="space-y-1">
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

              <div className="space-y-1">
                <label className="text-slate-400">Description</label>
                <textarea
                  rows={2}
                  placeholder="Explain when this rule should trigger alerts..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-slate-400">Min Severity</label>
                  <select
                    value={minSeverity}
                    onChange={(e) => setMinSeverity(e.target.value as SeverityLevel)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="critical">Critical</option>
                    <option value="high">High</option>
                    <option value="medium">Medium</option>
                    <option value="low">Low</option>
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
                    <option value="node">Node.js</option>
                    <option value="cloud">Cloud</option>
                  </select>
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-slate-400">Technology Regex/Filter (optional)</label>
                <input
                  type="text"
                  placeholder="e.g. fastapi|pydantic|langchain (or * for all)"
                  value={techPattern}
                  onChange={(e) => setTechPattern(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              {/* Alert Destinations */}
              <div className="space-y-1.5">
                <label className="text-slate-400">Dispatch Channels</label>
                <div className="flex flex-wrap gap-2">
                  {(["slack", "webhook", "email", "pagerduty"] as const).map((chan) => (
                    <button
                      key={chan}
                      type="button"
                      onClick={() => handleToggleChannel(chan)}
                      className={`px-3 py-1.5 rounded-lg border uppercase text-[10px] font-mono transition-colors ${
                        channels.includes(chan)
                          ? "bg-cyan-500/20 text-cyan-300 border-cyan-500/40"
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
                  Save Monitoring Rule
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
