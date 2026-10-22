import React from "react";
import { AlertTriangle, ArrowRight, CheckCircle, Layers, Sparkles, X } from "lucide-react";
import { BlastRadiusReport } from "../types";

interface BlastRadiusModalProps {
  report: BlastRadiusReport | null;
  isOpen: boolean;
  onClose: () => void;
  onSynthesizeReport?: (entity: string) => void;
}

export const BlastRadiusModal: React.FC<BlastRadiusModalProps> = ({
  report,
  isOpen,
  onClose,
  onSynthesizeReport,
}) => {
  if (!isOpen || !report) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-800 bg-slate-950/60">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              <Layers className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white font-mono">
                Blast Radius: <span className="text-cyan-400 capitalize">{report.root_entity}</span>
              </h2>
              <p className="text-xs text-slate-400 font-mono">
                Temporal graph dependency explosion ({report.max_traversal_depth} hops max depth)
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Overview Stats */}
        <div className="grid grid-cols-3 gap-3 p-5 bg-slate-950/40 border-b border-slate-800 text-center font-mono">
          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
            <div className="text-2xl font-bold text-white">{report.direct_dependents_count}</div>
            <div className="text-[11px] text-slate-400 uppercase tracking-wider mt-0.5">Direct Dependents</div>
          </div>
          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
            <div className="text-2xl font-bold text-cyan-400">{report.transitive_dependents_count}</div>
            <div className="text-[11px] text-slate-400 uppercase tracking-wider mt-0.5">Transitive Impact</div>
          </div>
          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
            <div className="text-2xl font-bold text-emerald-400">{report.total_nodes_scanned}</div>
            <div className="text-[11px] text-slate-400 uppercase tracking-wider mt-0.5">Total Graph Hops</div>
          </div>
        </div>

        {/* Affected Entities List */}
        <div className="p-5 flex-1 overflow-y-auto space-y-3">
          <h4 className="text-xs uppercase font-mono tracking-wider font-semibold text-slate-400">
            Impacted Components ({report.affected_nodes.length})
          </h4>

          {report.affected_nodes.length === 0 ? (
            <div className="p-8 text-center text-slate-500 rounded-xl bg-slate-950/60 border border-slate-800">
              <CheckCircle className="w-8 h-8 mx-auto text-emerald-500 mb-2" />
              <p className="text-sm font-medium text-slate-300">Isolated Blast Radius</p>
              <p className="text-xs text-slate-500 mt-1">
                No active upstream projects in the knowledge graph depend directly on this component.
              </p>
            </div>
          ) : (
            report.affected_nodes.map((node, i) => (
              <div
                key={i}
                className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-slate-700 transition-all space-y-2"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="font-mono font-bold text-white text-sm">{node.name}</span>
                    <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                      {node.ecosystem}
                    </span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
                      Hop {node.depth}
                    </span>
                  </div>

                  <div className="flex items-center space-x-1.5 text-xs font-mono">
                    <span className="text-slate-400">Likelihood:</span>
                    <span className="text-cyan-400 font-bold">{Math.round(node.impact_likelihood * 100)}%</span>
                  </div>
                </div>

                {/* Path representation */}
                {node.relationship_path && node.relationship_path.length > 0 && (
                  <div className="text-[11px] font-mono text-slate-400 bg-slate-900/80 px-2 py-1 rounded border border-slate-800 flex items-center space-x-1">
                    <span className="text-slate-500">Path:</span>
                    <span>{node.relationship_path.join(" -> ")}</span>
                  </div>
                )}

                {/* Reasons */}
                {node.vulnerability_reasons && (
                  <div className="text-xs text-slate-400">
                    {node.vulnerability_reasons.map((r, idx) => (
                      <p key={idx} className="flex items-center space-x-1">
                        <span className="text-amber-400">•</span>
                        <span>{r}</span>
                      </p>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/80 flex items-center justify-between">
          <span className="text-xs text-slate-500 font-mono">
            Analyzed {new Date(report.analysis_timestamp).toLocaleTimeString()}
          </span>

          <div className="flex items-center space-x-2">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-xs font-medium text-slate-300 hover:bg-slate-800 transition-colors"
            >
              Close
            </button>
            {onSynthesizeReport && (
              <button
                onClick={() => {
                  onClose();
                  onSynthesizeReport(report.root_entity);
                }}
                className="flex items-center space-x-1.5 px-4 py-2 rounded-lg text-xs font-semibold bg-cyan-500 text-slate-950 hover:bg-cyan-400 shadow-glow transition-all"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Synthesize Full Report</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
