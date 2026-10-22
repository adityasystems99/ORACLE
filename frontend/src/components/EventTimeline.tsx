import React, { useMemo, useState } from "react";
import {
  Calendar,
  CheckCircle,
  Clock,
  ExternalLink,
  Filter,
  History,
  Layers,
  Search,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { LifecycleStage, TimelineEvent } from "../types";

interface EventTimelineProps {
  events: TimelineEvent[];
  onSelectTechnology?: (tech: string) => void;
}

export const EventTimeline: React.FC<EventTimelineProps> = ({ events, onSelectTechnology }) => {
  const [selectedStage, setSelectedStage] = useState<string>("all");
  const [selectedTech, setSelectedTech] = useState<string>("all");
  const [search, setSearch] = useState("");

  const technologies = useMemo(() => {
    const set = new Set<string>();
    events.forEach((e) => set.add(e.primary_technology));
    return Array.from(set);
  }, [events]);

  const filteredEvents = useMemo(() => {
    return events.filter((e) => {
      const matchStage = selectedStage === "all" || e.stage === selectedStage;
      const matchTech = selectedTech === "all" || e.primary_technology === selectedTech;
      const matchSearch =
        e.title.toLowerCase().includes(search.toLowerCase()) ||
        e.summary.toLowerCase().includes(search.toLowerCase()) ||
        e.primary_technology.toLowerCase().includes(search.toLowerCase());
      return matchStage && matchTech && matchSearch;
    });
  }, [events, selectedStage, selectedTech, search]);

  const getStageBadge = (stage: LifecycleStage) => {
    switch (stage) {
      case "published":
        return {
          label: "1. Published Upstream",
          color: "bg-sky-950/80 text-sky-400 border-sky-800",
          dot: "bg-sky-400",
        };
      case "ingested":
        return {
          label: "2. Ingested & Hashed",
          color: "bg-emerald-950/80 text-emerald-400 border-emerald-800",
          dot: "bg-emerald-400",
        };
      case "updated":
        return {
          label: "3. Mitigation Linked",
          color: "bg-violet-950/80 text-violet-400 border-violet-800",
          dot: "bg-violet-400",
        };
      case "superseded":
        return {
          label: "4. Legacy Superseded",
          color: "bg-amber-950/80 text-amber-400 border-amber-800",
          dot: "bg-amber-400",
        };
    }
  };

  return (
    <div className="space-y-6">
      {/* Header and Filter Controls */}
      <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm space-y-4">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-bold font-mono text-white flex items-center space-x-2">
              <Clock className="w-5 h-5 text-cyan-400" />
              <span>Event Temporal Progression</span>
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Verifiable lifecycle timeline tracking information when published upstream, ingested by ORACLE, updated with mitigation, and superseded.
            </p>
          </div>

          <span className="px-2.5 py-1 rounded bg-slate-950 border border-slate-800 text-xs font-mono text-cyan-400 shrink-0">
            {filteredEvents.length} Recorded Milestones
          </span>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 pt-2 border-t border-slate-800/60">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Filter timeline by technology, release, or keyword..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div className="flex gap-2">
            <select
              value={selectedStage}
              onChange={(e) => setSelectedStage(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-cyan-500 font-mono"
            >
              <option value="all">All Lifecycle Stages</option>
              <option value="published">1. Published</option>
              <option value="ingested">2. Ingested</option>
              <option value="updated">3. Updated</option>
              <option value="superseded">4. Superseded</option>
            </select>

            <select
              value={selectedTech}
              onChange={(e) => setSelectedTech(e.target.value)}
              className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-cyan-500 font-mono"
            >
              <option value="all">All Technologies</option>
              {technologies.map((t) => (
                <option key={t} value={t}>
                  {t.toUpperCase()}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Chronological Timeline Stream */}
      <div className="relative pl-6 sm:pl-8 space-y-6 before:absolute before:left-3 before:top-2 before:bottom-2 before:w-[2px] before:bg-slate-800">
        {filteredEvents.length === 0 ? (
          <div className="p-8 text-center text-slate-500 rounded-xl bg-slate-900/40 border border-slate-800 text-xs">
            No events match your current filter parameters.
          </div>
        ) : (
          filteredEvents.map((item) => {
            const stageConfig = getStageBadge(item.stage);

            return (
              <div key={item.id} className="relative group">
                {/* Node Dot on timeline line */}
                <div
                  className={`absolute -left-[27px] sm:-left-[35px] top-1.5 w-3.5 h-3.5 rounded-full border-2 border-[#090d16] ${stageConfig.dot} shadow-glow`}
                />

                <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800/80 hover:border-slate-700 transition-all space-y-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center space-x-2">
                      <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded font-bold border ${stageConfig.color}`}>
                        {stageConfig.label}
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-cyan-400">
                        {item.primary_technology}
                      </span>
                      {item.version && (
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-950 text-slate-300 border border-slate-800">
                          v{item.version}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center space-x-2 text-xs font-mono text-slate-400">
                      {item.latency_from_publish && (
                        <span className="px-1.5 py-0.5 rounded bg-emerald-950/60 text-emerald-400 border border-emerald-800/50 text-[10px]">
                          Latency: {item.latency_from_publish}
                        </span>
                      )}
                      <span>{new Date(item.timestamp).toLocaleString()}</span>
                    </div>
                  </div>

                  <h4 className="text-sm font-semibold text-slate-100">{item.title}</h4>
                  <p className="text-xs text-slate-300 leading-relaxed font-sans">{item.summary}</p>

                  {item.superseded_by && (
                    <div className="text-[11px] font-mono text-amber-300/90 bg-amber-950/20 px-2.5 py-1.5 rounded border border-amber-800/40">
                      Superseded by: <span className="font-bold">{item.superseded_by}</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
