import React, { useState } from "react";
import {
  AlertCircle,
  Check,
  CheckCircle2,
  Copy,
  Download,
  ExternalLink,
  FileText,
  Layers,
  ShieldAlert,
  Sparkles,
  Terminal,
} from "lucide-react";
import { ImpactReport } from "../types";

interface ImpactDossierProps {
  reports: ImpactReport[];
  selectedReportId: string | null;
  onSelectReport: (id: string) => void;
  onExportMarkdown: (id: string) => void;
}

export const ImpactDossier: React.FC<ImpactDossierProps> = ({
  reports,
  selectedReportId,
  onSelectReport,
  onExportMarkdown,
}) => {
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  const activeReport = reports.find((r) => r.id === selectedReportId) || reports[0] || null;

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedCode(id);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  if (reports.length === 0) {
    return (
      <div className="p-12 text-center rounded-xl bg-slate-900/40 border border-slate-800 text-slate-400">
        <Sparkles className="w-8 h-8 mx-auto text-cyan-400 mb-2" />
        <h3 className="text-base font-semibold text-white">No Impact Dossiers Generated Yet</h3>
        <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
          Navigate to the "Intelligence Feed" and click "Generate Impact Dossier" on any detected event to synthesize an
          evidence-backed analysis.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Reports Directory (Left column) */}
      <div className="space-y-3">
        <h3 className="text-xs uppercase font-mono tracking-wider font-semibold text-slate-400">
          Generated Dossiers ({reports.length})
        </h3>

        <div className="space-y-2 max-h-[700px] overflow-y-auto">
          {reports.map((r) => {
            const isSelected = activeReport?.id === r.id;
            return (
              <div
                key={r.id}
                onClick={() => onSelectReport(r.id)}
                className={`p-3.5 rounded-xl border cursor-pointer transition-all space-y-1.5 ${
                  isSelected
                    ? "bg-cyan-500/10 border-cyan-500/40 shadow-glow"
                    : "bg-slate-900/50 border-slate-800 hover:border-slate-700"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-slate-800 text-cyan-400">
                    {r.primary_technology}
                  </span>
                  <span className="text-[10px] font-mono text-slate-500">
                    {new Date(r.generated_at).toLocaleDateString()}
                  </span>
                </div>
                <h4 className="text-xs font-semibold text-slate-200 line-clamp-1">{r.event_title}</h4>
                <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                  <span className="uppercase text-amber-400 font-semibold">{r.severity}</span>
                  <span>{r.impacted_components.length} affected deps</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Active Dossier View (Right 2 columns) */}
      {activeReport && (
        <div className="lg:col-span-2 bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-6 backdrop-blur-sm">
          {/* Header */}
          <div className="flex flex-wrap items-center justify-between gap-3 pb-5 border-b border-slate-800">
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xs uppercase font-mono px-2 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-800 font-bold">
                  {activeReport.severity}
                </span>
                <span className="text-xs font-mono text-slate-400">ID: `{activeReport.id}`</span>
              </div>
              <h2 className="text-xl font-bold text-white mt-1.5">{activeReport.event_title}</h2>
              <p className="text-xs text-slate-400 font-mono mt-1">
                Primary Technology: <span className="text-cyan-400 capitalize">{activeReport.primary_technology}</span> |{" "}
                Ecosystem: <span className="text-slate-300">{activeReport.ecosystem}</span>
              </p>
            </div>

            <button
              onClick={() => onExportMarkdown(activeReport.id)}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-mono font-medium bg-slate-800 text-slate-200 hover:bg-slate-700 transition-colors border border-slate-700"
            >
              <Download className="w-3.5 h-3.5 text-cyan-400" />
              <span>Export Markdown</span>
            </button>
          </div>

          {/* Executive Summary */}
          <div className="p-4 rounded-xl bg-cyan-950/20 border border-cyan-800/40 space-y-2">
            <h4 className="text-xs uppercase font-mono font-bold text-cyan-400 tracking-wider flex items-center space-x-1.5">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Executive Briefing</span>
            </h4>
            <p className="text-sm text-slate-200 leading-relaxed">{activeReport.executive_summary}</p>
          </div>

          {/* Technical Root Cause */}
          <div className="space-y-2">
            <h4 className="text-xs uppercase font-mono font-semibold text-slate-400 tracking-wider">
              Technical Root Cause & Ecosystem Impact
            </h4>
            <p className="text-sm text-slate-300 leading-relaxed bg-slate-950/60 p-4 rounded-xl border border-slate-800">
              {activeReport.technical_root_cause}
            </p>
          </div>

          {/* Breaking Changes */}
          {activeReport.breaking_changes && activeReport.breaking_changes.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs uppercase font-mono font-semibold text-amber-400 tracking-wider">
                Concrete Breaking Interface Changes
              </h4>
              <ul className="space-y-1.5 text-xs text-slate-300 bg-slate-950/60 p-4 rounded-xl border border-slate-800">
                {activeReport.breaking_changes.map((bc, idx) => (
                  <li key={idx} className="flex items-start space-x-2">
                    <span className="text-amber-400 font-bold">•</span>
                    <span>{bc}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Knowledge Graph Blast Radius */}
          {activeReport.impacted_components && activeReport.impacted_components.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs uppercase font-mono font-semibold text-slate-400 tracking-wider">
                Knowledge Graph Blast Radius ({activeReport.impacted_components.length} components)
              </h4>
              <div className="overflow-x-auto border border-slate-800 rounded-xl">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-slate-950 border-b border-slate-800 text-slate-400 uppercase text-[10px]">
                    <tr>
                      <th className="p-2.5">Component</th>
                      <th className="p-2.5">Type</th>
                      <th className="p-2.5">Depth</th>
                      <th className="p-2.5">Likelihood</th>
                      <th className="p-2.5">Path</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300 bg-slate-950/30">
                    {activeReport.impacted_components.map((comp, idx) => (
                      <tr key={idx} className="hover:bg-slate-900/60">
                        <td className="p-2.5 font-bold text-white">{comp.name}</td>
                        <td className="p-2.5 text-slate-400">{comp.node_type}</td>
                        <td className="p-2.5 text-cyan-400">Hop {comp.depth}</td>
                        <td className="p-2.5">{Math.round(comp.impact_likelihood * 100)}%</td>
                        <td className="p-2.5 text-[11px] text-slate-400">
                          {comp.relationship_path?.join(" -> ") || "Direct"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Evidence Trail */}
          {activeReport.evidence_trail && activeReport.evidence_trail.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs uppercase font-mono font-semibold text-slate-400 tracking-wider">
                Evidence Provenance & Citations
              </h4>
              <div className="space-y-2">
                {activeReport.evidence_trail.map((ev, idx) => (
                  <div key={idx} className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-200">{ev.title}</span>
                      <a
                        href={ev.source_url}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center space-x-1 text-cyan-400 hover:text-cyan-300"
                      >
                        <span>View Source</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                    <p className="font-mono text-slate-400 italic bg-slate-900 p-2 rounded">
                      "{ev.snippet}"
                    </p>
                    <span className="text-[10px] font-mono text-slate-500">Hash: {ev.content_hash}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Actionable Mitigation Playbook */}
          {activeReport.mitigation_playbook && activeReport.mitigation_playbook.length > 0 && (
            <div className="space-y-3 pt-2 border-t border-slate-800">
              <h4 className="text-xs uppercase font-mono font-bold text-emerald-400 tracking-wider flex items-center space-x-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>Actionable Mitigation Playbook</span>
              </h4>

              <div className="space-y-3">
                {activeReport.mitigation_playbook.map((step) => (
                  <div
                    key={step.step_number}
                    className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-white font-mono flex items-center space-x-2">
                        <span className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-[11px]">
                          {step.step_number}
                        </span>
                        <span>{step.title}</span>
                      </span>
                      <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400">
                        Effort: {step.estimated_effort}
                      </span>
                    </div>

                    <p className="text-xs text-slate-300">{step.description}</p>

                    {step.code_or_command && (
                      <div className="relative group">
                        <pre className="p-3 rounded-lg bg-slate-900 border border-slate-800 font-mono text-xs text-cyan-300 overflow-x-auto">
                          {step.code_or_command}
                        </pre>
                        <button
                          onClick={() => copyToClipboard(step.code_or_command!, `cmd-${step.step_number}`)}
                          className="absolute right-2 top-2 p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                        >
                          {copiedCode === `cmd-${step.step_number}` ? (
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                    )}

                    {step.verification_check && (
                      <div className="text-[11px] font-mono text-slate-400 bg-slate-900/40 p-2 rounded border border-slate-800">
                        <span className="text-slate-500">Verification: </span>
                        <span className="text-slate-300">{step.verification_check}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Provenance Footer */}
          {activeReport.llm_provenance && (
            <div className="pt-4 border-t border-slate-800/60 text-[11px] font-mono text-slate-500 flex flex-wrap items-center justify-between gap-2">
              <span>
                Provider: <span className="text-slate-400">{activeReport.llm_provenance.provider}</span> (
                {activeReport.llm_provenance.model})
              </span>
              <span>Latency: {activeReport.llm_provenance.latency_ms}ms</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
