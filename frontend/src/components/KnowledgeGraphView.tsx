import React, { useMemo, useRef, useState } from "react";
import {
  ArrowRight,
  Cpu,
  ExternalLink,
  Layers,
  Move,
  RotateCcw,
  Search,
  Sparkles,
  X,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { GraphSnapshot, TemporalGraphNode } from "../types";

interface KnowledgeGraphViewProps {
  snapshot: GraphSnapshot | null;
  onSelectNode: (nodeId: string) => void;
  onSynthesizeReport?: (nodeId: string) => void;
}

export const KnowledgeGraphView: React.FC<KnowledgeGraphViewProps> = ({
  snapshot,
  onSelectNode,
  onSynthesizeReport,
}) => {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [filterQuery, setFilterQuery] = useState("");
  const [selectedEcosystem, setSelectedEcosystem] = useState<string>("all");
  const [selectedNodeType, setSelectedNodeType] = useState<string>("all");
  const [zoom, setZoom] = useState<number>(1);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragOrigin, setDragOrigin] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  const svgRef = useRef<SVGSVGElement>(null);

  const nodes = snapshot?.nodes || [];
  const edges = snapshot?.edges || [];

  // Group nodes by ecosystem
  const ecosystems = useMemo(() => {
    const set = new Set<string>();
    nodes.forEach((n) => set.add(n.ecosystem));
    return Array.from(set);
  }, [nodes]);

  // Set of node IDs matching the search/filter criteria
  const matchingNodeIds = useMemo(() => {
    return new Set(
      nodes
        .filter((n) => {
          const matchQuery =
            !filterQuery.trim() ||
            n.name.toLowerCase().includes(filterQuery.toLowerCase()) ||
            n.id.toLowerCase().includes(filterQuery.toLowerCase());
          const matchEco = selectedEcosystem === "all" || n.ecosystem === selectedEcosystem;
          const matchType = selectedNodeType === "all" || n.node_type === selectedNodeType;
          return matchQuery && matchEco && matchType;
        })
        .map((n) => n.id)
    );
  }, [nodes, filterQuery, selectedEcosystem, selectedNodeType]);

  // Compute node layout positions deterministically with balanced clustering
  const positionedNodes = useMemo(() => {
    const total = nodes.length;
    if (total === 0) return [];
    const width = 800;
    const height = 520;
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = 210;

    return nodes.map((node, i) => {
      const angle = (i / total) * 2 * Math.PI;
      const ecoOffset =
        node.ecosystem === "python" ? 0.85 : node.ecosystem === "node" ? 1.05 : 0.95;
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

  // Set of connected nodes to selected
  const connectedNodeIds = useMemo(() => {
    if (!selectedNodeId) return null;
    const set = new Set<string>([selectedNodeId]);
    edges.forEach((e) => {
      if (e.target === selectedNodeId) set.add(e.source);
      if (e.source === selectedNodeId) set.add(e.target);
    });
    return set;
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

  const handleZoomIn = () => setZoom((prev) => Math.min(prev + 0.2, 2.0));
  const handleZoomOut = () => setZoom((prev) => Math.max(prev - 0.2, 0.5));
  const handleResetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  // Canvas Drag / Pan
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    setIsDragging(true);
    setDragOrigin({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPan({
      x: e.clientX - dragOrigin.x,
      y: e.clientY - dragOrigin.y,
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  return (
    <div className="space-y-4">
      {/* Top Filter and Controls */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 p-4 bg-slate-900/60 border border-slate-800 rounded-xl backdrop-blur-sm">
        <div className="flex items-center space-x-2 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-56">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Find entity node..."
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>

          <select
            value={selectedEcosystem}
            onChange={(e) => setSelectedEcosystem(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-cyan-500 font-mono"
          >
            <option value="all">All Ecosystems</option>
            {ecosystems.map((eco) => (
              <option key={eco} value={eco}>
                {eco.toUpperCase()}
              </option>
            ))}
          </select>

          <select
            value={selectedNodeType}
            onChange={(e) => setSelectedNodeType(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-cyan-500 font-mono hidden md:block"
          >
            <option value="all">All Types</option>
            <option value="technology">Technology</option>
            <option value="package">Package</option>
            <option value="database">Database</option>
            <option value="service">Service</option>
            <option value="specification">Specification</option>
          </select>
        </div>

        {/* Legend */}
        <div className="flex items-center space-x-3 text-xs font-mono text-slate-400">
          <span className="flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded-full bg-sky-400" />
            <span>Python</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
            <span>Node.js</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded-full bg-violet-400" />
            <span>Cloud</span>
          </span>
          <span className="flex items-center space-x-1">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
            <span>Database</span>
          </span>
        </div>
      </div>

      {/* Main Graph Canvas and Side Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Graph SVG Visualizer */}
        <div
          className={`lg:col-span-2 relative bg-slate-950/80 border border-slate-800/80 rounded-xl overflow-hidden min-h-[520px] flex items-center justify-center cyber-grid ${
            isDragging ? "cursor-grabbing" : "cursor-grab"
          }`}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
          {/* Zoom & Pan Controls Overlay */}
          <div className="absolute top-3 right-3 z-10 flex items-center space-x-1.5 p-1 rounded-lg bg-slate-900/90 border border-slate-800 backdrop-blur-md">
            <button
              onClick={handleZoomIn}
              className="p-1.5 rounded hover:bg-slate-800 text-slate-300 hover:text-white"
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              onClick={handleZoomOut}
              className="p-1.5 rounded hover:bg-slate-800 text-slate-300 hover:text-white"
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <button
              onClick={handleResetView}
              className="p-1.5 rounded hover:bg-slate-800 text-slate-300 hover:text-white"
              title="Reset Zoom & Pan"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            <span className="text-[10px] font-mono text-slate-400 px-1">
              {Math.round(zoom * 100)}%
            </span>
          </div>

          {/* Pan hint banner */}
          <div className="absolute bottom-3 left-3 z-10 flex items-center space-x-2 px-2.5 py-1 rounded-lg bg-slate-900/80 border border-slate-800 text-[10px] font-mono text-slate-400 backdrop-blur-sm pointer-events-none">
            <Move className="w-3 h-3 text-cyan-400" />
            <span>Click & Drag to Pan Canvas</span>
          </div>

          <svg
            ref={svgRef}
            className="w-full h-[520px] select-none"
            viewBox="0 0 800 520"
          >
            <defs>
              <marker
                id="arrowhead-dim"
                markerWidth="8"
                markerHeight="6"
                refX="18"
                refY="3"
                orient="auto"
              >
                <polygon points="0 0, 8 3, 0 6" fill="#1e293b" />
              </marker>
              <marker
                id="arrowhead-normal"
                markerWidth="8"
                markerHeight="6"
                refX="18"
                refY="3"
                orient="auto"
              >
                <polygon points="0 0, 8 3, 0 6" fill="#334155" />
              </marker>
              <marker
                id="arrowhead-cyan"
                markerWidth="8"
                markerHeight="6"
                refX="18"
                refY="3"
                orient="auto"
              >
                <polygon points="0 0, 8 3, 0 6" fill="#00f0ff" />
              </marker>
              <marker
                id="arrowhead-emerald"
                markerWidth="8"
                markerHeight="6"
                refX="18"
                refY="3"
                orient="auto"
              >
                <polygon points="0 0, 8 3, 0 6" fill="#34d399" />
              </marker>
            </defs>

            {/* Transform Group with Pan & Zoom */}
            <g
              transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}
              style={{ transformOrigin: "400px 260px" }}
            >
              {/* Render Edges */}
              {edges.map((edge, idx) => {
                const srcPos = nodePosMap.get(edge.source);
                const tgtPos = nodePosMap.get(edge.target);
                if (!srcPos || !tgtPos) return null;

                const isConnectedToSelected =
                  selectedNodeId === edge.source || selectedNodeId === edge.target;
                const isConnectedToHovered =
                  hoveredNodeId === edge.source || hoveredNodeId === edge.target;

                // Color based on role
                let strokeColor = "#1e293b";
                let markerId = "url(#arrowhead-normal)";
                let strokeWidth = 1;
                let opacity = 0.85;

                if (selectedNodeId) {
                  if (edge.source === selectedNodeId) {
                    // Outgoing dependency
                    strokeColor = "#00f0ff";
                    markerId = "url(#arrowhead-cyan)";
                    strokeWidth = 2.4;
                    opacity = 1;
                  } else if (edge.target === selectedNodeId) {
                    // Incoming dependent
                    strokeColor = "#34d399";
                    markerId = "url(#arrowhead-emerald)";
                    strokeWidth = 2.4;
                    opacity = 1;
                  } else {
                    opacity = 0.15;
                    markerId = "url(#arrowhead-dim)";
                  }
                } else if (hoveredNodeId) {
                  if (isConnectedToHovered) {
                    strokeColor = "#38bdf8";
                    markerId = "url(#arrowhead-cyan)";
                    strokeWidth = 2;
                    opacity = 1;
                  } else {
                    opacity = 0.2;
                  }
                }

                return (
                  <line
                    key={`${edge.source}-${edge.target}-${idx}`}
                    x1={srcPos.x}
                    y1={srcPos.y}
                    x2={tgtPos.x}
                    y2={tgtPos.y}
                    stroke={strokeColor}
                    strokeWidth={strokeWidth}
                    strokeOpacity={opacity}
                    strokeDasharray={edge.edge_type === "integrates_with" ? "4 4" : undefined}
                    markerEnd={markerId}
                    className="transition-all duration-200"
                  >
                    <title>{`${edge.source} -> ${edge.target} (${edge.version_constraint || edge.edge_type})`}</title>
                  </line>
                );
              })}

              {/* Render Nodes */}
              {positionedNodes.map((node) => {
                const isSelected = selectedNodeId === node.id;
                const isHovered = hoveredNodeId === node.id;
                const color = getNodeColor(node.ecosystem);

                const isConnected =
                  !connectedNodeIds || connectedNodeIds.has(node.id);
                const isMatch = matchingNodeIds.has(node.id);

                let nodeOpacity = 1;
                if (selectedNodeId && !isConnected) {
                  nodeOpacity = 0.2;
                } else if (!isMatch) {
                  nodeOpacity = 0.3;
                }

                return (
                  <g
                    key={node.id}
                    transform={`translate(${node.x}, ${node.y})`}
                    opacity={nodeOpacity}
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedNodeId(node.id);
                      onSelectNode(node.id);
                    }}
                    onMouseEnter={() => setHoveredNodeId(node.id)}
                    onMouseLeave={() => setHoveredNodeId(null)}
                    className="cursor-pointer group transition-opacity duration-200"
                  >
                    {/* Outer pulse if selected */}
                    {isSelected && (
                      <circle
                        r="24"
                        fill="none"
                        stroke="#00f0ff"
                        strokeWidth="2"
                        className="animate-ping opacity-40"
                      />
                    )}

                    {/* Filter match highlight halo */}
                    {isMatch && !isSelected && filterQuery && (
                      <circle
                        r="18"
                        fill="none"
                        stroke={color}
                        strokeWidth="1.5"
                        strokeDasharray="2 2"
                        className="opacity-70"
                      />
                    )}

                    {/* Node Circle */}
                    <circle
                      r={isSelected ? 16 : isHovered ? 14 : 12}
                      fill="#090d16"
                      stroke={isSelected ? "#00f0ff" : isHovered ? "#ffffff" : color}
                      strokeWidth={isSelected ? 2.5 : 1.5}
                      className="transition-all duration-200"
                    />

                    {/* Inner color dot */}
                    <circle r="4" fill={color} />

                    {/* Label */}
                    <text
                      y="24"
                      textAnchor="middle"
                      fill={isSelected ? "#00f0ff" : isHovered ? "#ffffff" : "#94a3b8"}
                      fontSize="11"
                      fontFamily="monospace"
                      className="select-none font-semibold transition-colors"
                    >
                      {node.name}
                    </text>
                  </g>
                );
              })}
            </g>
          </svg>
        </div>

        {/* Selected Node Details & Blast Radius Actions */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-5 flex flex-col justify-between backdrop-blur-sm">
          {selectedNode ? (
            <div className="space-y-4">
              <div className="flex items-start justify-between">
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

                <button
                  onClick={() => setSelectedNodeId(null)}
                  className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                  title="Clear Selection"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {selectedNode.description && (
                <p className="text-xs text-slate-300 font-sans leading-relaxed bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                  {selectedNode.description}
                </p>
              )}

              {/* Direct Dependents (Incoming) */}
              <div className="space-y-2">
                <span className="text-xs font-semibold uppercase text-slate-400 font-mono flex items-center justify-between">
                  <span>Direct Dependents ({incomingEdges.length})</span>
                  <span className="text-[10px] text-emerald-400 font-normal">relies on this</span>
                </span>
                <div className="space-y-1 max-h-28 overflow-y-auto">
                  {incomingEdges.length === 0 ? (
                    <p className="text-xs text-slate-500 italic">No incoming dependents in graph.</p>
                  ) : (
                    incomingEdges.map((e, i) => (
                      <div
                        key={i}
                        onClick={() => {
                          setSelectedNodeId(e.source);
                          onSelectNode(e.source);
                        }}
                        className="flex items-center justify-between text-xs font-mono p-1.5 rounded bg-slate-950 border border-slate-800 text-slate-300 hover:border-cyan-500/50 cursor-pointer transition-colors"
                      >
                        <span className="text-emerald-400 font-semibold">{e.source}</span>
                        <span className="text-[10px] text-slate-500">{e.edge_type}</span>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Dependencies (Outgoing) */}
              <div className="space-y-2">
                <span className="text-xs font-semibold uppercase text-slate-400 font-mono flex items-center justify-between">
                  <span>Depends On ({outgoingEdges.length})</span>
                  <span className="text-[10px] text-cyan-400 font-normal">prerequisite</span>
                </span>
                <div className="space-y-1 max-h-28 overflow-y-auto">
                  {outgoingEdges.length === 0 ? (
                    <p className="text-xs text-slate-500 italic">No external dependencies.</p>
                  ) : (
                    outgoingEdges.map((e, i) => (
                      <div
                        key={i}
                        onClick={() => {
                          setSelectedNodeId(e.target);
                          onSelectNode(e.target);
                        }}
                        className="flex items-center justify-between text-xs font-mono p-1.5 rounded bg-slate-950 border border-slate-800 text-slate-300 hover:border-cyan-500/50 cursor-pointer transition-colors"
                      >
                        <span className="text-cyan-400 font-semibold">{e.target}</span>
                        <span className="text-[10px] text-slate-500">{e.version_constraint || e.edge_type}</span>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Blast Radius Action */}
              <div className="pt-2 space-y-2">
                <button
                  onClick={() => onSelectNode(selectedNode.id)}
                  className="w-full flex items-center justify-center space-x-2 py-2 px-3 rounded-lg text-xs font-semibold bg-cyan-500 text-slate-950 hover:bg-cyan-400 shadow-glow transition-all"
                >
                  <Layers className="w-4 h-4" />
                  <span>Calculate Blast Radius</span>
                </button>

                {onSynthesizeReport && (
                  <button
                    onClick={() => onSynthesizeReport(selectedNode.id)}
                    className="w-full flex items-center justify-center space-x-2 py-2 px-3 rounded-lg text-xs font-semibold bg-slate-800 text-slate-200 hover:bg-slate-700 transition-colors"
                  >
                    <Sparkles className="w-4 h-4 text-cyan-400" />
                    <span>Synthesize Impact Dossier</span>
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div className="p-8 text-center text-slate-500 space-y-3 my-auto">
              <Cpu className="w-10 h-10 mx-auto text-slate-600 animate-pulse" />
              <p className="text-sm font-medium text-slate-300 font-mono">Entity Node Inspector</p>
              <p className="text-xs leading-relaxed max-w-xs mx-auto">
                Click any node in the canvas to inspect its direct dependents, dependencies, and blast radius explosion.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
