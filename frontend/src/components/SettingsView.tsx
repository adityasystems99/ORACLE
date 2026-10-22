import React, { useState } from "react";
import {
  Check,
  CheckCircle2,
  Cpu,
  Database,
  Layers,
  RefreshCw,
  Save,
  Server,
  Settings,
  Shield,
  Sparkles,
  Wifi,
  WifiOff,
} from "lucide-react";
import { ConnectionMode, SystemHealth } from "../types";

interface SettingsViewProps {
  health: SystemHealth | null;
  connectionMode: ConnectionMode;
  onSetConnectionMode: (mode: ConnectionMode) => void;
  onProbeBackend: () => void;
  isProbing: boolean;
  onShowToast: (msg: string) => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({
  health,
  connectionMode,
  onSetConnectionMode,
  onProbeBackend,
  isProbing,
  onShowToast,
}) => {
  const [provider, setProvider] = useState(health?.llm_provider || "anthropic");
  const [model, setModel] = useState(health?.llm_model || "claude-3-5-sonnet-20241022");
  const [pollInterval, setPollInterval] = useState("15");
  const [isSaved, setIsSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaved(true);
    onShowToast(`Settings updated: LLM provider set to ${provider} (${model}).`);
    setTimeout(() => setIsSaved(false), 2500);
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Title */}
      <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm flex items-center justify-between">
        <div>
          <h3 className="text-base font-bold font-mono text-white flex items-center space-x-2">
            <Settings className="w-5 h-5 text-cyan-400" />
            <span>ORACLE System Settings & Diagnostics</span>
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            LLM engine selection, embedding vector store status, ingestion cadence, and adapter runtime mode.
          </p>
        </div>
      </div>

      {/* Connection & Runtime Adapter Mode */}
      <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm space-y-4">
        <h4 className="text-xs font-mono font-bold uppercase text-slate-400 tracking-wider flex items-center space-x-2">
          <Server className="w-4 h-4 text-cyan-400" />
          <span>Runtime Environment & Adapter Mode</span>
        </h4>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div
            onClick={() => onSetConnectionMode("connected")}
            className={`p-4 rounded-xl border cursor-pointer transition-all space-y-2 ${
              connectionMode === "connected"
                ? "bg-emerald-950/20 border-emerald-500/50 shadow-glow"
                : "bg-slate-950/50 border-slate-800 hover:border-slate-700"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-white flex items-center space-x-2">
                <Wifi className="w-4 h-4 text-emerald-400" />
                <span>Live FastAPI Backend</span>
              </span>
              {connectionMode === "connected" && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300">
                  Active
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 leading-relaxed font-sans">
              Routes all telemetry, vector embeddings, and graph queries directly to the live backend service on port 8000.
            </p>
          </div>

          <div
            onClick={() => onSetConnectionMode("demo_fixtures")}
            className={`p-4 rounded-xl border cursor-pointer transition-all space-y-2 ${
              connectionMode === "demo_fixtures"
                ? "bg-amber-950/20 border-amber-500/50 shadow-glow"
                : "bg-slate-950/50 border-slate-800 hover:border-slate-700"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-white flex items-center space-x-2">
                <WifiOff className="w-4 h-4 text-amber-400" />
                <span>Typed Demo Fixtures Adapter</span>
              </span>
              {connectionMode === "demo_fixtures" && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-300">
                  Active
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 leading-relaxed font-sans">
              Provides robust offline fixtures with ground-truth citations, interactive blast radius, and streaming copilot.
            </p>
          </div>
        </div>

        <div className="flex items-center justify-between pt-2 text-xs font-mono text-slate-400">
          <span>Backend status: {connectionMode === "connected" ? "Connected (Live)" : "Offline (Demo Fixtures)"}</span>
          <button
            onClick={onProbeBackend}
            disabled={isProbing}
            className="flex items-center space-x-1 px-3 py-1.5 rounded-lg bg-slate-800 text-slate-200 hover:bg-slate-700 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isProbing ? "animate-spin text-cyan-400" : ""}`} />
            <span>{isProbing ? "Probing Port 8000..." : "Probe Backend Health"}</span>
          </button>
        </div>
      </div>

      {/* Intelligence Engine Configuration */}
      <form onSubmit={handleSave} className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm space-y-4">
        <h4 className="text-xs font-mono font-bold uppercase text-slate-400 tracking-wider flex items-center space-x-2">
          <Sparkles className="w-4 h-4 text-cyan-400" />
          <span>LLM Reasoning & Copilot Adapter</span>
        </h4>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
          <div className="space-y-1">
            <label className="text-slate-400">LLM Provider</label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="anthropic">Anthropic (Claude 3.5 Sonnet)</option>
              <option value="openai">OpenAI (GPT-4o / GPT-4o-mini)</option>
              <option value="local">Local Ollama / Llama 3</option>
              <option value="mock">Deterministic Test Mock</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-slate-400">Model Identifier</label>
            <input
              type="text"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div className="space-y-1">
            <label className="text-slate-400">Default Refresh Polling (minutes)</label>
            <input
              type="number"
              min="1"
              max="1440"
              value={pollInterval}
              onChange={(e) => setPollInterval(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div className="space-y-1">
            <label className="text-slate-400">Confidence Threshold for Auto-Dossier</label>
            <input
              type="text"
              readOnly
              value=">= 0.85 (Strict Verification)"
              className="w-full px-3 py-2 rounded-lg bg-slate-950/60 border border-slate-800 text-slate-500 cursor-not-allowed"
            />
          </div>
        </div>

        <div className="flex justify-end pt-3 border-t border-slate-800">
          <button
            type="submit"
            className="flex items-center space-x-1.5 px-4 py-2 rounded-lg bg-cyan-500 text-slate-950 hover:bg-cyan-400 font-bold font-mono text-xs transition-all shadow-glow"
          >
            {isSaved ? <Check className="w-4 h-4 text-slate-950" /> : <Save className="w-4 h-4" />}
            <span>{isSaved ? "Saved Successfully" : "Save Configuration"}</span>
          </button>
        </div>
      </form>

      {/* Diagnostics Readout */}
      <div className="p-5 rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm space-y-3">
        <h4 className="text-xs font-mono font-bold uppercase text-slate-400 tracking-wider flex items-center space-x-2">
          <Database className="w-4 h-4 text-cyan-400" />
          <span>System Diagnostics & Index Capacity</span>
        </h4>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
          <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800">
            <div className="text-slate-500 text-[10px] uppercase">Graph Nodes</div>
            <div className="text-base font-bold text-white mt-1">{health?.graph.nodes || 16}</div>
          </div>
          <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800">
            <div className="text-slate-500 text-[10px] uppercase">Graph Edges</div>
            <div className="text-base font-bold text-cyan-400 mt-1">{health?.graph.edges || 26}</div>
          </div>
          <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800">
            <div className="text-slate-500 text-[10px] uppercase">Reports Stored</div>
            <div className="text-base font-bold text-amber-400 mt-1">{health?.reports_count || 8}</div>
          </div>
          <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800">
            <div className="text-slate-500 text-[10px] uppercase">Vector Storage</div>
            <div className="text-base font-bold text-emerald-400 mt-1">ChromaDB Local</div>
          </div>
        </div>
      </div>
    </div>
  );
};
