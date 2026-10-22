import React from "react";
import { Activity, Cpu, Database, RefreshCw, Rss, ShieldAlert, Sparkles } from "lucide-react";
import { SystemHealth } from "../types";

interface NavbarProps {
  activeTab: "feed" | "graph" | "reports" | "sources";
  setActiveTab: (tab: "feed" | "graph" | "reports" | "sources") => void;
  health: SystemHealth | null;
  onSync: () => void;
  isSyncing: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  health,
  onSync,
  isSyncing,
}) => {
  return (
    <header className="border-b border-slate-800 bg-[#090d16]/90 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand & Identity */}
          <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab("feed")}>
            <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 to-sky-400 p-0.5 shadow-glow">
              <div className="w-full h-full bg-[#090d16] rounded-[10px] flex items-center justify-center">
                <Activity className="w-5 h-5 text-cyan-400 animate-pulse" />
              </div>
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xl font-bold tracking-wider text-white font-mono">ORACLE</span>
                <span className="text-[10px] px-1.5 py-0.5 uppercase tracking-widest rounded bg-cyan-950/80 text-cyan-400 border border-cyan-800/60 font-mono">
                  Live Copilot
                </span>
              </div>
              <p className="text-xs text-slate-400 hidden sm:block">
                Autonomous Ecosystem Intelligence & Temporal Graph Reasoning
              </p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex space-x-1 sm:space-x-2">
            {[
              { id: "feed", label: "Intelligence Feed", icon: ShieldAlert },
              { id: "graph", label: "Knowledge Graph", icon: Cpu },
              { id: "reports", label: "Impact Dossiers", icon: Sparkles },
              { id: "sources", label: "Data Ingestion", icon: Rss },
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-lg text-xs sm:text-sm font-medium transition-all ${
                    isActive
                      ? "bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 shadow-glow"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? "text-cyan-400" : "text-slate-400"}`} />
                  <span className="hidden md:inline">{tab.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Telemetry & Trigger Sync */}
          <div className="flex items-center space-x-3">
            {health && (
              <div className="hidden lg:flex items-center space-x-2 text-xs font-mono">
                <div className="flex items-center space-x-1 px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
                  <Database className="w-3.5 h-3.5 text-cyan-400" />
                  <span>{health.graph.nodes} Nodes</span>
                </div>
                <div className="flex items-center space-x-1 px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-slate-300">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 radar-live"></span>
                  <span className="capitalize">{health.llm_provider}</span>
                </div>
              </div>
            )}

            <button
              onClick={onSync}
              disabled={isSyncing}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium font-mono transition-all ${
                isSyncing
                  ? "bg-slate-800 text-slate-400 cursor-not-allowed"
                  : "bg-cyan-500 text-slate-950 hover:bg-cyan-400 font-semibold shadow-glow"
              }`}
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? "animate-spin" : ""}`} />
              <span>{isSyncing ? "Syncing..." : "Sync Live"}</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};
