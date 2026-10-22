import React, { useState } from "react";
import {
  AlertTriangle,
  ArrowUpRight,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Flame,
  Info,
  Layers,
  Search,
  Shield,
  Sparkles,
} from "lucide-react";
import { ChangeCategory, IntelligenceEvent, SeverityLevel } from "../types";

interface LiveFeedProps {
  events: IntelligenceEvent[];
  onExploreBlastRadius: (tech: string, eventId: string) => void;
  onGenerateReport: (eventId: string) => void;
  isGeneratingReport: string | null;
}

export const LiveFeed: React.FC<LiveFeedProps> = ({
  events,
  onExploreBlastRadius,
  onGenerateReport,
  isGeneratingReport,
}) => {
  const [search, setSearch] = useState("");
  const [selectedSeverity, setSelectedSeverity] = useState<string>("all");
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [expandedEvidence, setExpandedEvidence] = useState<Record<string, boolean>>({});

  const toggleEvidence = (id: string) => {
    setExpandedEvidence((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const getSeverityStyle = (severity: SeverityLevel) => {
    switch (severity) {
      case "critical":
        return "bg-rose-950/80 text-rose-400 border-rose-800 shadow-glow-rose";
      case "high":
        return "bg-amber-950/80 text-amber-400 border-amber-800";
      case "medium":
        return "bg-sky-950/80 text-sky-400 border-sky-800";
      default:
        return "bg-slate-900 text-slate-400 border-slate-800";
    }
  };

  const getCategoryBadge = (category: ChangeCategory) => {
    switch (category) {
      case "breaking_change":
        return { label: "Breaking Change", color: "text-amber-300 bg-amber-500/10 border-amber-500/30" };
      case "security_vulnerability":
        return { label: "Security CVE", color: "text-rose-300 bg-rose-500/10 border-rose-500/30" };
      case "outage":
        return { label: "Service Outage", color: "text-red-400 bg-red-500/10 border-red-500/30" };
      case "deprecation":
        return { label: "Deprecation", color: "text-yellow-300 bg-yellow-500/10 border-yellow-500/30" };
      case "major_release":
        return { label: "Major Release", color: "text-cyan-300 bg-cyan-500/10 border-cyan-500/30" };
      default:
        return { label: "Update", color: "text-slate-300 bg-slate-800 border-slate-700" };
    }
  };

  const filteredEvents = events.filter((ev) => {
    const matchesSearch =
      ev.title.toLowerCase().includes(search.toLowerCase()) ||
      ev.primary_technology.toLowerCase().includes(search.toLowerCase()) ||
      ev.summary.toLowerCase().includes(search.toLowerCase()) ||
      (ev.cve_id && ev.cve_id.toLowerCase().includes(search.toLowerCase()));

    const matchesSeverity = selectedSeverity === "all" || ev.severity === selectedSeverity;
    const matchesCategory = selectedCategory === "all" || ev.category === selectedCategory;

    return matchesSearch && matchesSeverity && matchesCategory;
  });

  return (
    <div className="space-y-6">
      {/* Search & Filter Bar */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm space-y-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
            <input
              type="text"
              placeholder="Search intelligence by technology, CVE, or keyword..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
            />
          </div>

          <div className="flex gap-2">
            <select
              value={selectedSeverity}
              onChange={(e) => setSelectedSeverity(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-cyan-500"
            >
              <option value="all">All Severities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>

            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-300 focus:outline-none focus:border-cyan-500"
            >
              <option value="all">All Categories</option>
              <option value="breaking_change">Breaking Changes</option>
              <option value="security_vulnerability">Security Vulnerabilities</option>
              <option value="outage">Outages</option>
              <option value="deprecation">Deprecations</option>
              <option value="major_release">Major Releases</option>
            </select>
          </div>
        </div>
      </div>

      {/* Events Stream */}
      <div className="space-y-4">
        {filteredEvents.length === 0 ? (
          <div className="p-12 text-center rounded-xl bg-slate-900/30 border border-slate-800 text-slate-400">
            <Info className="w-8 h-8 mx-auto mb-2 text-slate-500" />
            <p className="text-base font-medium text-slate-300">No matching intelligence events found.</p>
            <p className="text-xs text-slate-500 mt-1">
              Click "Sync Live" in the top bar to ingest fresh feeds or adjust your search filters.
            </p>
          </div>
        ) : (
          filteredEvents.map((event) => {
            const catBadge = getCategoryBadge(event.category);
            const isEvidenceOpen = expandedEvidence[event.id];
            const isAnalyzing = isGeneratingReport === event.id;

            return (
              <div
                key={event.id}
                className="p-5 rounded-xl bg-slate-900/50 border border-slate-800/80 hover:border-slate-700 transition-all space-y-4 hover:shadow-lg"
              >
                {/* Header Row */}
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center space-x-2">
                    <span
                      className={`px-2 py-0.5 rounded text-xs uppercase font-mono font-bold border ${getSeverityStyle(
                        event.severity
                      )}`}
                    >
                      {event.severity}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-xs font-mono border ${catBadge.color}`}>
                      {catBadge.label}
                    </span>
                    {event.cve_id && (
                      <span className="px-2 py-0.5 rounded text-xs font-mono bg-rose-950/60 text-rose-300 border border-rose-800">
                        {event.cve_id}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center space-x-2 text-xs font-mono text-slate-400">
                    <span className="px-2 py-0.5 rounded bg-slate-800/80 text-cyan-400">
                      {event.primary_technology}
                    </span>
                    <span>•</span>
                    <span>{new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                </div>

                {/* Event Title & Summary */}
                <div>
                  <h3 className="text-base font-semibold text-slate-100">{event.title}</h3>
                  <p className="text-sm text-slate-300 mt-1.5 leading-relaxed">{event.summary}</p>
                </div>

                {/* Detection Rationale */}
                <div className="text-xs font-mono text-slate-400 bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/60">
                  <span className="text-slate-500">Detection Rationale: </span>
                  <span className="text-slate-300">{event.detection_rationale}</span>
                  <span className="ml-2 text-cyan-400 font-semibold">({intConfidence(event.confidence)}% Confidence)</span>
                </div>

                {/* Ground Truth Evidence Drawer */}
                {event.evidence && event.evidence.length > 0 && (
                  <div className="border border-slate-800/80 rounded-lg overflow-hidden bg-slate-950/40">
                    <button
                      onClick={() => toggleEvidence(event.id)}
                      className="w-full flex items-center justify-between px-3 py-2 text-xs font-mono text-slate-400 hover:text-slate-200 transition-colors"
                    >
                      <span className="flex items-center space-x-1.5">
                        <Shield className="w-3.5 h-3.5 text-cyan-400" />
                        <span>Ground-Truth Evidence ({event.evidence.length} citation)</span>
                      </span>
                      {isEvidenceOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                    </button>

                    {isEvidenceOpen && (
                      <div className="p-3 border-t border-slate-800 space-y-2 text-xs">
                        {event.evidence.map((ev, idx) => (
                          <div key={idx} className="space-y-1">
                            <div className="flex items-center justify-between">
                              <span className="font-semibold text-slate-300">{ev.title}</span>
                              <a
                                href={ev.source_url}
                                target="_blank"
                                rel="noreferrer"
                                className="flex items-center space-x-1 text-cyan-400 hover:text-cyan-300"
                              >
                                <span>Source</span>
                                <ExternalLink className="w-3 h-3" />
                              </a>
                            </div>
                            <p className="font-mono text-slate-400 italic bg-slate-900/80 p-2 rounded border border-slate-800">
                              "{ev.snippet}"
                            </p>
                            <span className="text-[10px] font-mono text-slate-500">Hash: {ev.content_hash.slice(0, 16)}...</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Actions Row */}
                <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-800/60">
                  <div className="flex items-center space-x-2 text-xs text-slate-400">
                    {event.affected_entities && event.affected_entities.length > 0 && (
                      <span className="font-mono text-xs text-slate-500">
                        Ecosystem link: {event.affected_entities.slice(0, 3).join(", ")}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => onExploreBlastRadius(event.primary_technology, event.id)}
                      className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 text-slate-200 hover:bg-slate-700 transition-colors"
                    >
                      <Layers className="w-3.5 h-3.5 text-cyan-400" />
                      <span>Explore Blast Radius</span>
                    </button>

                    <button
                      onClick={() => onGenerateReport(event.id)}
                      disabled={isAnalyzing}
                      className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                        isAnalyzing
                          ? "bg-slate-800 text-slate-400 cursor-wait"
                          : "bg-cyan-500 text-slate-950 hover:bg-cyan-400 shadow-glow"
                      }`}
                    >
                      <Sparkles className={`w-3.5 h-3.5 ${isAnalyzing ? "animate-spin" : ""}`} />
                      <span>{isAnalyzing ? "Synthesizing Dossier..." : "Generate Impact Dossier"}</span>
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

function intConfidence(c: number): number {
  return Math.round(c * 100);
}
