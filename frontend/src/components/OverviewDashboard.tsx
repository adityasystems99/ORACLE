import React from "react";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  ArrowUpRight,
  CheckCircle2,
  Clock,
  Cpu,
  Database,
  ExternalLink,
  Flame,
  Layers,
  MessageSquare,
  Radio,
  Rss,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import {
  GraphSnapshot,
  ImpactReport,
  IngestionSource,
  IntelligenceEvent,
  InvestigationSession,
  NavigationTab,
  SystemHealth,
} from "../types";

interface OverviewDashboardProps {
  health: SystemHealth | null;
  events: IntelligenceEvent[];
  reports: ImpactReport[];
  sources: IngestionSource[];
  snapshot: GraphSnapshot | null;
  investigations: InvestigationSession[];
  onNavigateTab: (tab: NavigationTab, targetId?: string) => void;
  onExploreBlastRadius: (tech: string, eventId?: string) => void;
  onGenerateReport: (eventId: string) => void;
  isGeneratingReport: string | null;
}

export const OverviewDashboard: React.FC<OverviewDashboardProps> = ({
  health,
  events,
  reports,
  sources,
  snapshot,
  investigations,
  onNavigateTab,
  onExploreBlastRadius,
  onGenerateReport,
  isGeneratingReport,
}) => {
  const criticalEvents = events.filter((e) => e.severity === "critical");
  const breakingEvents = events.filter((e) => e.category === "breaking_change" || e.category === "deprecation");
  const healthySources = sources.filter((s) => s.last_status === "success" || s.last_status === "initialized");

  return (
    <div className="space-y-6">
      {/* Top Telemetry Metrics Ribbon */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
            <span>Raw Signals</span>
            <Radio className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white">
            {health?.signals_count || 142}
          </div>
          <div className="flex items-center space-x-1.5 text-[10px] font-mono text-emerald-400">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 radar-live" />
            <span>Streaming Realtime</span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
            <span>Active Events</span>
            <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-amber-300">
            {events.length}
          </div>
          <div className="text-[10px] font-mono text-rose-400">
            {criticalEvents.length} Critical Severity
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
            <span>Breaking Changes</span>
            <Flame className="w-3.5 h-3.5 text-rose-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-rose-400">
            {breakingEvents.length}
          </div>
          <div className="text-[10px] font-mono text-slate-400">
            Requires Migration
          </div>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
            <span>Graph Scale</span>
            <Cpu className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-cyan-300">
            {snapshot?.node_count || 16}
          </div>
          <div className="text-[10px] font-mono text-slate-400">
            {snapshot?.edge_count || 26} Directional Edges
          </div>
        </div>

        <div className="col-span-2 md:col-span-4 lg:col-span-1 p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-xs font-mono">
            <span>Feeds Health</span>
            <Rss className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-300">
            {healthySources.length}/{sources.length}
          </div>
          <div className="text-[10px] font-mono text-emerald-400">
            100% Operational
          </div>
        </div>
      </div>

      {/* Main Grid: Left Stream (2 cols) & Right Intelligence Panels (1 col) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 spans): Live Technology Signals & Breaking Changes */}
        <div className="lg:col-span-2 space-y-6">
          {/* Live Technology Signals Panel */}
          <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4 backdrop-blur-sm">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-2.5">
                <div className="p-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
                  <Radio className="w-4 h-4 animate-pulse" />
                </div>
                <div>
                  <h3 className="text-sm font-bold font-mono text-white">Live Technology Signals</h3>
                  <p className="text-[11px] font-mono text-slate-400">
                    Continuous stream of ecosystem events and changelog mutations
                  </p>
                </div>
              </div>

              <button
                onClick={() => onNavigateTab("signals")}
                className="flex items-center space-x-1 text-xs font-mono text-cyan-400 hover:text-cyan-300 transition-colors"
              >
                <span>View All ({events.length})</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Event list snippet */}
            <div className="space-y-3">
              {events.slice(0, 4).map((ev) => (
                <div
                  key={ev.id}
                  className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition-all space-y-2 group"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center space-x-2">
                      <span
                        className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded font-bold border ${
                          ev.severity === "critical"
                            ? "bg-rose-950 text-rose-400 border-rose-800"
                            : ev.severity === "high"
                            ? "bg-amber-950 text-amber-400 border-amber-800"
                            : "bg-sky-950 text-sky-400 border-sky-800"
                        }`}
                      >
                        {ev.severity}
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-cyan-300 border border-slate-700">
                        {ev.primary_technology}
                      </span>
                      {ev.cve_id && (
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800">
                          {ev.cve_id}
                        </span>
                      )}
                    </div>

                    <span className="text-[11px] font-mono text-slate-500">
                      {new Date(ev.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </div>

                  <h4 className="text-xs font-semibold text-slate-100 group-hover:text-cyan-300 transition-colors">
                    {ev.title}
                  </h4>
                  <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                    {ev.summary}
                  </p>

                  <div className="flex items-center justify-between pt-2 border-t border-slate-800/60 text-xs">
                    <span className="text-[11px] font-mono text-slate-500">
                      Confidence: {Math.round(ev.confidence * 100)}% ({ev.evidence.length} citation)
                    </span>

                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => onExploreBlastRadius(ev.primary_technology, ev.id)}
                        className="px-2.5 py-1 rounded bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 transition-colors text-xs font-medium font-mono"
                      >
                        Blast Radius
                      </button>

                      <button
                        onClick={() => onGenerateReport(ev.id)}
                        disabled={isGeneratingReport === ev.id}
                        className="px-2.5 py-1 rounded bg-cyan-500 text-slate-950 hover:bg-cyan-400 transition-colors text-xs font-semibold font-mono"
                      >
                        {isGeneratingReport === ev.id ? "Analyzing..." : "Synthesize Dossier"}
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Breaking Changes Spotlight */}
          <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4 backdrop-blur-sm">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-2.5">
                <div className="p-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400">
                  <Flame className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold font-mono text-white">Recent Breaking Changes & Deprecations</h3>
                  <p className="text-[11px] font-mono text-slate-400">
                    High-impact architectural shifts requiring immediate engineering review
                  </p>
                </div>
              </div>

              <span className="text-xs font-mono text-amber-400">
                {breakingEvents.length} Pending Actions
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {breakingEvents.slice(0, 2).map((bc) => (
                <div
                  key={bc.id}
                  className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 space-y-2.5 flex flex-col justify-between"
                >
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800 font-bold">
                        {bc.primary_technology}
                      </span>
                      <span className="text-[10px] font-mono text-slate-500">
                        {bc.version_affected || "Major Release"}
                      </span>
                    </div>

                    <h5 className="text-xs font-bold text-slate-200 line-clamp-1">{bc.title}</h5>
                    <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed">
                      {bc.summary}
                    </p>
                  </div>

                  <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs">
                    <span className="text-[10px] font-mono text-slate-500">
                      Downstream: {bc.affected_entities.slice(0, 2).join(", ")}
                    </span>
                    <button
                      onClick={() => onExploreBlastRadius(bc.primary_technology, bc.id)}
                      className="text-cyan-400 hover:text-cyan-300 font-mono text-xs flex items-center space-x-1"
                    >
                      <span>Impact Path</span>
                      <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column (1 span): Investigations, Impact Reports, Sources Health */}
        <div className="space-y-6">
          {/* High Priority Investigations Copilot Card */}
          <div className="p-5 rounded-2xl bg-gradient-to-b from-cyan-950/30 to-slate-900/60 border border-cyan-800/40 space-y-4 backdrop-blur-sm">
            <div className="flex items-center justify-between pb-3 border-b border-cyan-800/30">
              <div className="flex items-center space-x-2">
                <Sparkles className="w-4 h-4 text-cyan-400" />
                <h3 className="text-sm font-bold font-mono text-white">Investigation Threads</h3>
              </div>
              <button
                onClick={() => onNavigateTab("investigations")}
                className="text-[11px] font-mono text-cyan-400 hover:text-cyan-300"
              >
                Launch Copilot →
              </button>
            </div>

            <div className="space-y-2.5">
              {investigations.map((inv) => (
                <div
                  key={inv.id}
                  onClick={() => onNavigateTab("investigations", inv.id)}
                  className="p-3 rounded-xl bg-slate-950/80 border border-slate-800/80 hover:border-cyan-500/40 cursor-pointer transition-all space-y-1.5"
                >
                  <div className="flex items-center justify-between text-[10px] font-mono">
                    <span className="text-cyan-400 uppercase font-bold">{inv.primary_technology}</span>
                    <span className="text-slate-500">
                      {new Date(inv.updated_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </span>
                  </div>
                  <h5 className="text-xs font-semibold text-slate-200 line-clamp-1">{inv.title}</h5>
                  <p className="text-[11px] text-slate-400 line-clamp-1">
                    {inv.messages[inv.messages.length - 1]?.content.slice(0, 70)}...
                  </p>
                </div>
              ))}
            </div>

            <button
              onClick={() => onNavigateTab("investigations")}
              className="w-full flex items-center justify-center space-x-2 py-2 px-3 rounded-lg text-xs font-semibold font-mono bg-cyan-500 text-slate-950 hover:bg-cyan-400 shadow-glow transition-all"
            >
              <MessageSquare className="w-3.5 h-3.5" />
              <span>New Intelligence Investigation</span>
            </button>
          </div>

          {/* Recent Impact Dossiers */}
          <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4 backdrop-blur-sm">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <Layers className="w-4 h-4 text-amber-400" />
                <h3 className="text-sm font-bold font-mono text-white">Recent Impact Dossiers</h3>
              </div>
              <button
                onClick={() => onNavigateTab("reports")}
                className="text-[11px] font-mono text-cyan-400 hover:text-cyan-300"
              >
                All Dossiers ({reports.length}) →
              </button>
            </div>

            <div className="space-y-2.5">
              {reports.slice(0, 3).map((rep) => (
                <div
                  key={rep.id}
                  onClick={() => onNavigateTab("reports", rep.id)}
                  className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 cursor-pointer transition-all space-y-1"
                >
                  <div className="flex items-center justify-between text-[10px] font-mono">
                    <span className="text-amber-400 font-bold uppercase">{rep.severity}</span>
                    <span className="text-slate-500">{rep.impacted_components.length} hops affected</span>
                  </div>
                  <h5 className="text-xs font-semibold text-slate-200 line-clamp-1">{rep.event_title}</h5>
                  <p className="text-[10px] font-mono text-slate-400">
                    Playbook: {rep.mitigation_playbook.length} actionable mitigation steps
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Monitored Feeds & Ingestion Health */}
          <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4 backdrop-blur-sm">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <Rss className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-bold font-mono text-white">Ingestion Health</h3>
              </div>
              <button
                onClick={() => onNavigateTab("sources")}
                className="text-[11px] font-mono text-cyan-400 hover:text-cyan-300"
              >
                Configure Feeds →
              </button>
            </div>

            <div className="space-y-2">
              {sources.slice(0, 4).map((src) => (
                <div
                  key={src.id}
                  className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80 text-xs font-mono"
                >
                  <div className="flex items-center space-x-2 truncate">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 shrink-0" />
                    <span className="text-slate-300 truncate">{src.name}</span>
                  </div>
                  <span className="text-[10px] text-slate-500 uppercase">{src.source_type}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
