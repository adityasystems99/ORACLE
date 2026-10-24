import React, { useEffect, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ExternalLink,
  Info,
  Pause,
  Play,
  Plus,
  RefreshCw,
  Rss,
  ShieldAlert,
  ShieldCheck,
  Tag,
  X,
  Zap,
} from "lucide-react";
import { api } from "../api/client";
import { IngestionSource, SchedulerHealth } from "../types";

interface SourceManagerProps {
  sources: IngestionSource[];
  onTriggerSourceSync: (sourceId: string) => void;
  isSyncingId: string | null;
  onSourceAdded?: (source: IngestionSource) => void;
  onRefreshAllSources?: () => void;
}

export const SourceManager: React.FC<SourceManagerProps> = ({
  sources,
  onTriggerSourceSync,
  isSyncingId,
  onSourceAdded,
  onRefreshAllSources,
}) => {
  const [schedulerHealth, setSchedulerHealth] = useState<SchedulerHealth | null>(null);
  const [isRefreshingHealth, setIsRefreshingHealth] = useState(false);
  const [isTriggeringAll, setIsTriggeringAll] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Form State for Add Source
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [sourceType, setSourceType] = useState<
    "rss" | "github_releases" | "security_advisory" | "status_page" | "changelog" | "official_registry"
  >("rss");
  const [targetType, setTargetType] = useState<string>("technology");
  const [ecosystem, setEcosystem] = useState("python");
  const [intervalMinutes, setIntervalMinutes] = useState(15);
  const [topicsString, setTopicsString] = useState("web,api");

  const loadSchedulerHealth = async () => {
    setIsRefreshingHealth(true);
    try {
      const health = await api.getSchedulerHealth();
      if (health) {
        setSchedulerHealth(health);
      }
    } catch (e) {
      console.error("Failed to load scheduler health:", e);
    } finally {
      setIsRefreshingHealth(false);
    }
  };

  useEffect(() => {
    loadSchedulerHealth();
    const timer = setInterval(loadSchedulerHealth, 15000);
    return () => clearInterval(timer);
  }, []);

  const handleToggleScheduler = async () => {
    if (!schedulerHealth) return;
    try {
      if (schedulerHealth.is_paused) {
        await api.resumeScheduler();
      } else {
        await api.pauseScheduler();
      }
      await loadSchedulerHealth();
    } catch (e) {
      console.error("Failed to toggle scheduler:", e);
    }
  };

  const handleTriggerCycleNow = async () => {
    setIsTriggeringAll(true);
    try {
      await api.triggerSchedulerRunNow();
      await loadSchedulerHealth();
      if (onRefreshAllSources) onRefreshAllSources();
    } catch (e) {
      console.error("Failed to trigger cycle:", e);
    } finally {
      setIsTriggeringAll(false);
    }
  };

  const handleCreateSource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !url.trim()) return;

    const topics = topicsString
      .split(",")
      .map((t) => t.trim())
      .filter((t) => t.length > 0);

    const boundedInterval = Math.max(5, Math.min(1440, intervalMinutes));

    const newSource: IngestionSource = {
      id: `src-${name.toLowerCase().replace(/[^a-z0-9]/g, "-")}-${Date.now().toString(36)}`,
      name: name.trim(),
      url: url.trim(),
      source_type: sourceType,
      enabled: true,
      ecosystem,
      refresh_interval_minutes: boundedInterval,
      target_type: targetType,
      topics,
      consecutive_failures: 0,
      last_status: "idle",
    };

    try {
      const created = await api.addSource(newSource);
      if (onSourceAdded) onSourceAdded(created);
      setIsModalOpen(false);
      setName("");
      setUrl("");
      setTopicsString("");
      await loadSchedulerHealth();
    } catch (e) {
      console.error("Failed to add source:", e);
    }
  };

  const isPaused = schedulerHealth?.is_paused ?? false;

  return (
    <div className="space-y-6">
      {/* Top Banner & Observability Controls */}
      <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur-md flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
              <Rss className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold font-mono text-white flex items-center space-x-2">
                <span>Scheduled Ingestion & Source Observability</span>
                <span
                  className={`text-[10px] uppercase font-mono px-2 py-0.5 rounded-full border ${
                    isPaused
                      ? "bg-amber-950/80 text-amber-300 border-amber-800"
                      : "bg-emerald-950/80 text-emerald-300 border-emerald-800"
                  }`}
                >
                  {isPaused ? "Scheduler Paused" : "Scheduler Active"}
                </span>
              </h3>
              <p className="text-xs text-slate-400">
                Idempotent interval polling with HTTP 304 checkpoint caching and rate-limit backoff.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2 shrink-0">
          <button
            onClick={handleToggleScheduler}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border text-xs font-mono font-bold transition-all ${
              isPaused
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20"
                : "bg-amber-500/10 text-amber-400 border-amber-500/30 hover:bg-amber-500/20"
            }`}
            title={isPaused ? "Resume scheduled loop" : "Pause all background ingestion ticks"}
          >
            {isPaused ? <Play className="w-3.5 h-3.5" /> : <Pause className="w-3.5 h-3.5" />}
            <span>{isPaused ? "Resume Scheduler" : "Pause Scheduler"}</span>
          </button>

          <button
            onClick={handleTriggerCycleNow}
            disabled={isTriggeringAll}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-mono font-bold transition-all"
            title="Force immediate evaluation of all due sources"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isTriggeringAll ? "animate-spin text-cyan-400" : ""}`} />
            <span>Poll All Now</span>
          </button>

          <button
            onClick={() => setIsModalOpen(true)}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 text-xs font-bold font-mono transition-all shadow-glow"
          >
            <Plus className="w-4 h-4" />
            <span>Add Source</span>
          </button>
        </div>
      </div>

      {/* Honest Architecture & Push vs. Polling Disclaimer */}
      <div className="p-4 rounded-xl bg-slate-950/90 border border-slate-800/80 flex items-start space-x-3 text-xs font-mono text-slate-300">
        <Info className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <div className="font-bold text-white flex items-center space-x-2">
            <span>Architecture Notice: Scheduled Polling vs. Push Streams</span>
          </div>
          <p className="text-slate-400 leading-relaxed">
            ORACLE operates on bounded scheduled interval polling with HTTP conditional request checkpointing (ETag / If-Modified-Since, 304 Not Modified caching), not persistent webhooks or push streams. Monitoring jobs execute within the local modular monolith scheduler loop while the backend process is running. When the process is stopped, no background polling occurs.
          </p>
        </div>
      </div>

      {/* Scheduler Health Metrics Dashboard */}
      {schedulerHealth && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
          <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
            <span className="text-slate-500 text-[10px] uppercase font-bold">Monitored Feeds</span>
            <div className="text-lg font-bold text-white flex items-center space-x-1.5">
              <span>{schedulerHealth.active_sources_count}</span>
              <span className="text-[11px] text-slate-500 font-normal">active</span>
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
            <span className="text-slate-500 text-[10px] uppercase font-bold">Ingestion Runs</span>
            <div className="text-lg font-bold text-cyan-400 flex items-center space-x-1.5">
              <span>{schedulerHealth.total_runs_completed}</span>
              <span className="text-[11px] text-slate-500 font-normal">cycles</span>
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
            <span className="text-slate-500 text-[10px] uppercase font-bold">Events Detected</span>
            <div className="text-lg font-bold text-emerald-400 flex items-center space-x-1.5">
              <span>{schedulerHealth.total_events_detected}</span>
              <span className="text-[11px] text-slate-500 font-normal">classified</span>
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
            <span className="text-slate-500 text-[10px] uppercase font-bold">Failure Counter</span>
            <div className="text-lg font-bold text-rose-400 flex items-center space-x-1.5">
              <span>{schedulerHealth.total_errors}</span>
              <span className="text-[11px] text-slate-500 font-normal">errors</span>
            </div>
          </div>
        </div>
      )}

      {/* Sources Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sources.map((src) => {
          const isSyncing = isSyncingId === src.id;
          const isSuccess =
            src.last_status === "success" ||
            src.last_status === "initialized" ||
            src.last_status?.includes("304") ||
            src.last_status === "unchanged";
          const hasError = src.consecutive_failures && src.consecutive_failures > 0;

          return (
            <div
              key={src.id}
              className={`p-5 rounded-2xl border transition-all flex flex-col justify-between space-y-4 ${
                hasError
                  ? "bg-rose-950/10 border-rose-900/40 hover:border-rose-800/60"
                  : "bg-slate-900/60 border-slate-800 hover:border-slate-700 shadow-md"
              }`}
            >
              <div>
                {/* Header */}
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1.5">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded font-bold bg-slate-800 text-cyan-300 border border-slate-700">
                        {src.source_type}
                      </span>

                      {src.target_type && (
                        <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded font-bold bg-slate-950 text-slate-300 border border-slate-800 flex items-center space-x-1">
                          <Tag className="w-2.5 h-2.5 mr-0.5" />
                          <span>{src.target_type}</span>
                        </span>
                      )}

                      <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-950 text-slate-400 border border-slate-800">
                        {src.ecosystem}
                      </span>
                    </div>

                    <h4 className="text-sm font-bold text-white font-mono">{src.name}</h4>
                  </div>

                  <button
                    onClick={() => onTriggerSourceSync(src.id)}
                    disabled={isSyncing}
                    className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
                    title="Poll Source Now"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? "animate-spin text-cyan-400" : ""}`} />
                  </button>
                </div>

                {/* URL */}
                <div className="text-xs font-mono text-slate-400 break-all bg-slate-950/70 p-2 rounded-lg border border-slate-800 flex items-center justify-between mt-3">
                  <span className="truncate mr-2">{src.url}</span>
                  <a
                    href={src.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-cyan-400 hover:text-cyan-300 shrink-0"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                </div>

                {/* Topics / Tags */}
                {src.topics && src.topics.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2.5">
                    {src.topics.map((t) => (
                      <span
                        key={t}
                        className="text-[10px] px-2 py-0.5 rounded bg-slate-950 text-slate-400 border border-slate-800/80 font-mono"
                      >
                        #{t}
                      </span>
                    ))}
                  </div>
                )}

                {/* Checkpoint & Error Details */}
                <div className="mt-3 p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80 space-y-1.5 text-xs font-mono">
                  <div className="flex items-center justify-between text-slate-400">
                    <span className="text-slate-500">Polling Interval:</span>
                    <span className="text-slate-300 flex items-center space-x-1">
                      <Clock className="w-3 h-3 text-slate-500" />
                      <span>Every {src.refresh_interval_minutes}m (±5% jitter)</span>
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-slate-400">
                    <span className="text-slate-500">Last Synced:</span>
                    <span className="text-slate-300">
                      {src.last_synced_at
                        ? new Date(src.last_synced_at).toLocaleTimeString()
                        : "Pending First Run"}
                    </span>
                  </div>

                  {src.next_scheduled_run_at && (
                    <div className="flex items-center justify-between text-slate-400">
                      <span className="text-slate-500">Next Scheduled:</span>
                      <span className="text-cyan-400 font-semibold">
                        {new Date(src.next_scheduled_run_at).toLocaleTimeString()}
                      </span>
                    </div>
                  )}

                  {src.etag && (
                    <div className="flex items-center justify-between text-slate-400">
                      <span className="text-slate-500">HTTP ETag Checkpoint:</span>
                      <span className="text-slate-400 truncate max-w-[150px]" title={src.etag}>
                        {src.etag}
                      </span>
                    </div>
                  )}

                  {hasError && (
                    <div className="pt-1 border-t border-rose-900/40 text-rose-400 flex items-center space-x-1">
                      <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                      <span className="truncate">
                        {src.error_message || `${src.consecutive_failures} consecutive failures`}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Status Footer */}
              <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 pt-2.5 border-t border-slate-800/80">
                <div className="flex items-center space-x-1.5">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      hasError ? "bg-rose-400 animate-pulse" : isSuccess ? "bg-emerald-400" : "bg-cyan-400"
                    }`}
                  />
                  <span className="capitalize">{src.last_status || "idle"}</span>
                </div>

                <div className="text-slate-500 text-[10px]">
                  {src.consecutive_failures ? `${src.consecutive_failures} retry backoffs` : "0 failures"}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Add Monitored Source Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-lg rounded-2xl bg-slate-900 border border-slate-800 p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-base font-bold font-mono text-white flex items-center space-x-2">
                <Plus className="w-4 h-4 text-cyan-400" />
                <span>Configure Monitored Source</span>
              </h3>
              <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateSource} className="space-y-4 text-xs font-mono">
              <div className="space-y-1">
                <label className="text-slate-400">Feed / Repository / Advisory Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. FastAPI GitHub Releases"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-400">Feed URL / Endpoint</label>
                <input
                  type="url"
                  required
                  placeholder="https://github.com/tiangolo/fastapi/releases.atom"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-slate-400">Source Type</label>
                  <select
                    value={sourceType}
                    onChange={(e) => setSourceType(e.target.value as any)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="rss">RSS / Atom Feed</option>
                    <option value="github_releases">GitHub Releases Atom</option>
                    <option value="security_advisory">Security Advisory (CVE)</option>
                    <option value="status_page">Status Page / Outage Atom</option>
                    <option value="changelog">Changelog Feed</option>
                    <option value="official_registry">Official Registry</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-slate-400">Target Type</label>
                  <select
                    value={targetType}
                    onChange={(e) => setTargetType(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="technology">Technology / Framework</option>
                    <option value="api">API / Service</option>
                    <option value="product">Product</option>
                    <option value="repository">Repository</option>
                    <option value="security_advisory">Security Advisory</option>
                    <option value="topic">Topic / Domain</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-slate-400">Ecosystem</label>
                  <select
                    value={ecosystem}
                    onChange={(e) => setEcosystem(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="python">Python</option>
                    <option value="node">Node / TypeScript</option>
                    <option value="cloud">Cloud Infrastructure</option>
                    <option value="security">Security</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-slate-400">Polling Interval (Minutes)</label>
                  <input
                    type="number"
                    min={5}
                    max={1440}
                    value={intervalMinutes}
                    onChange={(e) => setIntervalMinutes(parseInt(e.target.value, 10) || 15)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                  />
                  <span className="text-[10px] text-slate-500 block">Bounded [5m, 1440m]</span>
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-slate-400">Topics / Tags (comma separated)</label>
                <input
                  type="text"
                  placeholder="e.g. web, api, framework, deprecation"
                  value={topicsString}
                  onChange={(e) => setTopicsString(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                />
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
                  Register Source
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
