import React, { useMemo, useState } from "react";
import { Cpu, ExternalLink, Layers, Search, ZoomIn, ZoomOut } from "lucide-react";
import { GraphSnapshot, TemporalGraphNode } from "../types";

interface KnowledgeGraphViewProps {
  snapshot: GraphSnapshot | null;
  onSelectNode: (nodeId: string) => void;
}

export const KnowledgeGraphView: React.FC<KnowledgeGraphViewProps> = ({ snapshot, onSelectNode }) => {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [filterQuery, setFilterQuery] = useState("");
  const [selectedEcosystem, setSelectedEcosystem] = useState<string>("all");

  const nodes = snapshot?.nodes || [];
  const edges = snapshot?.edges || [];

  // Group nodes by ecosystem
  const ecosystems = useMemo(() => {
    const set = new Set<string>();
    nodes.forEach((n) => set.add(n.ecosystem));
    return Array.from(set);
  }, [nodes]);

  const filteredNodes = useMemo(() => {
    return nodes.filter((n) => {
      const matchQuery =
        n.name.toLowerCase().includes(filterQuery.toLowerCase()) ||
        n.id.toLowerCase().includes(filterQuery.toLowerCase());
      const matchEco = selectedEcosystem === "all" || n.ecosystem === selectedEcosystem;
      return matchQuery && matchEco;
    });
  }, [nodes, filterQuery, selectedEcosystem]);

  // Compute node layout positions deterministically
  const positionedNodes = useMemo(() => {
    const total = nodes.length;
    if (total === 0) return [];
    const width = 800;
    const height = 500;
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = 200;

    return nodes.map((node, i) => {
      const angle = (i / total) * 2 * Math.PI;
      // Add slight offset based on ecosystem
      const ecoOffset = node.ecosystem === "python" ? 0.8 : node.ecosystem === "node" ? 1.1 : 0.95;
      const x = centerX + Math.cos(angle) * (radius * ecoOffset);
      const y = centerY + Math.sin(angle) * (radius * ecoOffset);
      return {
        ...node,
        x,
        y,
      };
    });
  }, [nodes]);

  const nodePosMap = useMemo(() => {
    const map = new Map<string, { x: number; y: number }>();
    positionedNodes.forEach((n) => map.set(n.id, { x: n.x, y: n.y }));
    return map;
  }, [positionedNodes]);

  const selectedNode = useMemo(() => {
    return nodes.find((n) => n.id === selectedNodeId) || null;
  }, [nodes, selectedNodeId]);

  // Direct incoming (dependents) and outgoing (dependencies)
  const incomingEdges = useMemo(() => {
    if (!selectedNodeId) return [];
    return edges.filter((e) => e.target === selectedNodeId);
  }, [edges, selectedNodeId]);

  const outgoingEdges = useMemo(() => {
    if (!selectedNodeId) return [];
    return edges.filter((e) => e.source === selectedNodeId);
  }, [edges, selectedNodeId]);

  const getNodeColor = (eco: string) => {
    switch (eco) {
      case "python":
        return "#38bdf8"; // sky-400
      case "node":
        return "#34d399"; // emerald-400
      case "cloud":
        return "#a78bfa"; // violet-400
      case "database":
        return "#fbbf24"; // amber-400
      default:
        return "#94a3b8"; // slate-400
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Filter and Controls */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-4 bg-slate-900/60 border border-slate-800 rounded-xl backdrop-blur-sm">
        <div className="flex items-center space-x-2 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-64">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Find entity node..."
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <select
            value={selectedEcosystem}
            onChange={(e) => setSelectedEcosystem(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-cyan-500"
          >
            <option value="all">All Ecosystems</option>
            {ecosystems.map((eco) => (
              <option key={eco} value={eco}>
                {eco.toUpperCase()}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center space-x-3 text-xs font-mono text-slate-400">
          <span className="flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded-full bg-sky-400"></span>
            <span>Python</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
            <span>Node.js</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded-full bg-violet-400"></span>
            <span>Cloud</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
            <span>Database</span>
          </span>
        </div>
      </div>

      {/* Main Graph Canvas and Side Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Graph SVG Visualizer */}
        <div className="lg:col-span-2 relative bg-slate-950/80 border border-slate-800/80 rounded-xl overflow-hidden min-h-[500px] flex items-center justify-center cyber-grid">
          <svg className="w-full h-[520px]" viewBox="0 0 800 520">
            <defs>
              <marker
                id="arrowhead"
                markerWidth="8"
                markerHeight="6"
                refX="18"
                refY="3"
                orient="auto"
              >
                <polygon points="0 0, 8 3, 0 6" fill="#475569" />
              </marker>
              <marker
                id="arrowhead-highlight"
                markerWidth="8"
                markerHeight="6"
                refX="18"
                refY="3"
                orient="auto"
              >
                <polygon points="0 0, 8 3, 0 6" fill="#00f0ff" />
              </marker>
            </defs>

            {/* Render Edges */}
            {edges.map((edge, idx) => {
              const srcPos = nodePosMap.get(edge.source);
              const tgtPos = nodePosMap.get(edge.target);
              if (!srcPos || !tgtPos) return null;

              const isConnectedToSelected =
                selectedNodeId === edge.source || selectedNodeId === edge.target;

              return (
                <line
                  key={`${edge.source}-${edge.target}-${idx}`}
                  x1={srcPos.x}
                  y1={srcPos.y}
                  x2={tgtPos.x}
                  y2={tgtPos.y}
                  stroke={isConnectedToSelected ? "#00f0ff" : "#1e293b"}
                  strokeWidth={isConnectedToSelected ? 2 : 1}
                  strokeDasharray={edge.edge_type === "integrates_with" ? "4 4" : undefined}
                  markerEnd={isConnectedToSelected ? "url(#arrowhead-highlight)" : "url(#arrowhead)"}
                  className="transition-all duration-300"
                />
              );
            })}

            {/* Render Nodes */}
            {positionedNodes.map((node) => {
              const isSelected = selectedNodeId === node.id;
              const color = getNodeColor(node.ecosystem);

              return (
                <g
                  key={node.id}
                  transform={`translate(${node.x}, ${node.y})`}
                  onClick={() => {
                    setSelectedNodeId(node.id);
                    onSelectNode(node.id);
                  }}
                  className="cursor-pointer group"
                >
                  {/* Outer pulse if selected */}
                  {isSelected && (
                    <circle
                      r="22"
                      fill="none"
                      stroke="#00f0ff"
                      strokeWidth="2"
                      className="animate-ping opacity-50"
                    />
                  )}

                  {/* Node Circle */}
                  <circle
                    r={isSelected ? 16 : 12}
                    fill="#0f172a"
                    stroke={isSelected ? "#00f0ff" : color}
                    strokeWidth={isSelected ? 2.5 : 1.5}
                    className="transition-all duration-200 group-hover:scale-125"
                  />

                  {/* Inner glow dot */}
                  <circle r="4" fill={color} />

                  {/* Label */}
                  <text
                    y="24"
                    textAnchor="middle"
                    fill={isSelected ? "#00f0ff" : "#94a3b8"}
                    fontSize="11"
                    fontFamily="monospace"
                    className="select-none font-semibold transition-colors group-hover:fill-white"
                  >
                    {node.name}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* Selected Node Details & Blast Radius Actions */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-5">
          {selectedNode ? (
            <div className="space-y-4">
              <div>
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
                  {selectedNode.node_type}
                </span>
                <h3 className="text-xl font-bold text-white mt-2 font-mono">{selectedNode.name}</h3>
                <p className="text-xs text-slate-400 font-mono mt-0.5">Ecosystem: {selectedNode.ecosystem}</p>
                {selectedNode.latest_version && (
                  <p className="text-xs text-slate-400 font-mono">Latest Version: {selectedNode.latest_version}</p>
                )}
              </div>

              {/* Direct Dependents (Incoming) */}
              <div className="space-y-2">
                <span className="text-xs font-semibold uppercase text-slate-400 font-mono">
                  Direct Dependents ({incomingEdges.length})
                </span>
                <div className="space-y-1 max-h-32 overflow-y-auto">
                  {incomingEdges.length === 0 ? (
                    <p className="text-xs text-slate-500 italic">No incoming dependents in graph.</p>
                  ) : (
                    incomingEdges.map((e, i) => (
                      <div
                        key={i}
                        className="flex items-center justify-between text-xs font-mono p-1.5 rounded bg-slate-950 border border-slate-800 text-slate-300"
                      >
                        <span className="text-cyan-400">{e.source}</span>
                        <span className="text-[10px] text-slate-500">{e.edge_type}</span>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Dependencies (Outgoing) */}
              <div className="space-y-2">
                <span className="text-xs font-semibold uppercase text-slate-400 font-mono">
                  Depends On ({outgoingEdges.length})
                </span>
                <div className="space-y-1 max-h-32 overflow-y-auto">
                  {outgoingEdges.length === 0 ? (
                    <p className="text-xs text-slate-500 italic">No external dependencies.</p>
                  ) : (
                    outgoingEdges.map((e, i) => (
                      <div
                        key={i}
                        className="flex items-center justify-between text-xs font-mono p-1.5 rounded bg-slate-950 border border-slate-800 text-slate-300"
                      >
                        <span className="text-emerald-400">{e.target}</span>
                        <span className="text-[10px] text-slate-500">{e.version_constraint || e.edge_type}</span>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Blast Radius Action */}
              <button
                onClick={() => onSelectNode(selectedNode.id)}
                className="w-full flex items-center justify-center space-x-2 py-2 px-3 rounded-lg text-xs font-semibold bg-cyan-500 text-slate-950 hover:bg-cyan-400 shadow-glow transition-all"
              >
                <Layers className="w-4 h-4" />
                <span>Calculate Blast Radius</span>
              </button>
            </div>
          ) : (
            <div className="p-8 text-center text-slate-500 space-y-2">
              <Cpu className="w-8 h-8 mx-auto text-slate-600" />
              <p className="text-sm font-medium text-slate-300">Select an entity in the graph</p>
              <p className="text-xs">Click on any node to inspect directional dependencies and blast radius.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
