import React, { useState } from "react";
import { CheckCircle2, Clock, ExternalLink, Plus, RefreshCw, Rss, ShieldCheck } from "lucide-react";
import { IngestionSource } from "../types";

interface SourceManagerProps {
  sources: IngestionSource[];
  onTriggerSourceSync: (sourceId: string) => void;
  isSyncingId: string | null;
}

export const SourceManager: React.FC<SourceManagerProps> = ({
  sources,
  onTriggerSourceSync,
  isSyncingId,
}) => {
  return (
    <div className="space-y-6">
      {/* Title & Info */}
      <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-base font-bold text-white font-mono flex items-center space-x-2">
            <Rss className="w-5 h-5 text-cyan-400" />
            <span>Monitored Intelligence Feeds</span>
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Active connectors streaming official changelogs, GitHub release atoms, CVE advisories, and status pages.
          </p>
        </div>

        <div className="flex items-center space-x-2 text-xs font-mono text-slate-400">
          <span className="px-2.5 py-1 rounded bg-slate-950 border border-slate-800">
            {sources.length} Active Feeds
          </span>
        </div>
      </div>

      {/* Sources Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sources.map((src) => {
          const isSyncing = isSyncingId === src.id;
          const isSuccess = src.last_status === "success" || src.last_status === "initialized";

          return (
            <div
              key={src.id}
              className="p-5 rounded-xl bg-slate-900/50 border border-slate-800 hover:border-slate-700 transition-all space-y-3"
            >
              <div className="flex items-start justify-between">
                <div>
                  <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-800 text-cyan-400">
                    {src.source_type}
                  </span>
                  <h4 className="text-sm font-bold text-white mt-1.5 font-mono">{src.name}</h4>
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

              <div className="text-xs font-mono text-slate-400 break-all bg-slate-950/60 p-2 rounded border border-slate-800 flex items-center justify-between">
                <span className="truncate mr-2">{src.url}</span>
                <a href={src.url} target="_blank" rel="noreferrer" className="text-cyan-400 hover:text-cyan-300">
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>

              <div className="flex items-center justify-between text-[11px] font-mono text-slate-400 pt-2 border-t border-slate-800/60">
                <div className="flex items-center space-x-1.5">
                  <Clock className="w-3.5 h-3.5 text-slate-500" />
                  <span>Every {src.refresh_interval_minutes}m</span>
                </div>

                <div className="flex items-center space-x-1.5">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      isSuccess ? "bg-emerald-400" : "bg-rose-400"
                    }`}
                  ></span>
                  <span className="capitalize">{src.last_status || "idle"}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
