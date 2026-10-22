import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Clock,
  Cpu,
  ExternalLink,
  FileText,
  Layers,
  MessageSquare,
  Radio,
  Search,
  ShieldAlert,
  Sparkles,
  X,
} from "lucide-react";
import {
  GraphSnapshot,
  ImpactReport,
  IntelligenceEvent,
  InvestigationSession,
  NavigationTab,
} from "../types";

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  events: IntelligenceEvent[];
  reports: ImpactReport[];
  snapshot: GraphSnapshot | null;
  investigations: InvestigationSession[];
  onNavigate: (tab: NavigationTab, targetId?: string) => void;
  onExploreBlastRadius: (tech: string) => void;
}

interface CommandItem {
  id: string;
  title: string;
  subtitle: string;
  category: "Signals" | "Reports" | "Entities" | "Investigations" | "Actions";
  icon: React.ElementType;
  action: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  events,
  reports,
  snapshot,
  investigations,
  onNavigate,
  onExploreBlastRadius,
}) => {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setSelectedIndex(0);
    }
  }, [isOpen]);

  const allItems: CommandItem[] = useMemo(() => {
    const list: CommandItem[] = [];

    // Quick Actions
    list.push({
      id: "act-new-inv",
      title: "Start New AI Copilot Investigation",
      subtitle: "Launch a conversational research thread on any library or change",
      category: "Actions",
      icon: MessageSquare,
      action: () => {
        onNavigate("investigations");
        onClose();
      },
    });

    list.push({
      id: "act-graph",
      title: "Open Knowledge Graph Explorer",
      subtitle: "Explore interactive dependency graph and blast radius models",
      category: "Actions",
      icon: Cpu,
      action: () => {
        onNavigate("graph");
        onClose();
      },
    });

    list.push({
      id: "act-timeline",
      title: "Open Event Lifecycle Timeline",
      subtitle: "View published, ingested, updated, and superseded milestones",
      category: "Actions",
      icon: Clock,
      action: () => {
        onNavigate("timeline");
        onClose();
      },
    });

    // Events / Signals
    events.forEach((ev) => {
      list.push({
        id: `ev-${ev.id}`,
        title: ev.title,
        subtitle: `${ev.severity.toUpperCase()} • ${ev.primary_technology} • ${ev.category}`,
        category: "Signals",
        icon: Radio,
        action: () => {
          onNavigate("signals", ev.id);
          onClose();
        },
      });
    });

    // Reports / Dossiers
    reports.forEach((rep) => {
      list.push({
        id: `rep-${rep.id}`,
        title: rep.event_title,
        subtitle: `Dossier • ${rep.primary_technology} • ${rep.impacted_components.length} impacted dependencies`,
        category: "Reports",
        icon: FileText,
        action: () => {
          onNavigate("reports", rep.id);
          onClose();
        },
      });
    });

    // Graph Entities
    (snapshot?.nodes || []).forEach((n) => {
      list.push({
        id: `node-${n.id}`,
        title: n.name,
        subtitle: `Graph Entity • ${n.ecosystem.toUpperCase()} • ${n.node_type}`,
        category: "Entities",
        icon: Cpu,
        action: () => {
          onExploreBlastRadius(n.id);
          onClose();
        },
      });
    });

    // Investigations
    investigations.forEach((inv) => {
      list.push({
        id: `inv-${inv.id}`,
        title: inv.title,
        subtitle: `Investigation Thread • ${inv.primary_technology}`,
        category: "Investigations",
        icon: MessageSquare,
        action: () => {
          onNavigate("investigations", inv.id);
          onClose();
        },
      });
    });

    return list;
  }, [events, reports, snapshot, investigations, onNavigate, onExploreBlastRadius, onClose]);

  const filteredItems = useMemo(() => {
    if (!query.trim()) return allItems.slice(0, 15);
    const q = query.toLowerCase();
    return allItems
      .filter((item) => item.title.toLowerCase().includes(q) || item.subtitle.toLowerCase().includes(q))
      .slice(0, 20);
  }, [allItems, query]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % filteredItems.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + filteredItems.length) % filteredItems.length);
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (filteredItems[selectedIndex]) {
        filteredItems[selectedIndex].action();
      }
    } else if (e.key === "Escape") {
      e.preventDefault();
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-black/75 backdrop-blur-sm animate-fade-in">
      <div
        className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div className="flex items-center px-4 border-b border-slate-800 bg-slate-950/80">
          <Search className="h-5 w-5 text-slate-400 mr-3" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search signals, dossiers, blast radius, investigations..."
            className="w-full py-4 bg-transparent text-sm text-slate-100 placeholder-slate-500 focus:outline-none"
          />
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-white transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Results List */}
        <div className="max-h-96 overflow-y-auto p-2 space-y-1">
          {filteredItems.length === 0 ? (
            <div className="p-8 text-center text-slate-500 text-xs">
              No matching intelligence artifacts found for "{query}".
            </div>
          ) : (
            filteredItems.map((item, idx) => {
              const Icon = item.icon;
              const isSelected = idx === selectedIndex;

              return (
                <div
                  key={item.id}
                  onClick={() => item.action()}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`flex items-center justify-between px-3 py-2.5 rounded-xl cursor-pointer transition-all ${
                    isSelected
                      ? "bg-cyan-500/10 text-cyan-200 border border-cyan-500/30"
                      : "text-slate-300 hover:bg-slate-800/40"
                  }`}
                >
                  <div className="flex items-center space-x-3 truncate mr-3">
                    <div
                      className={`p-2 rounded-lg ${
                        isSelected
                          ? "bg-cyan-500/20 text-cyan-300"
                          : "bg-slate-800 text-slate-400"
                      }`}
                    >
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="truncate">
                      <div className="text-xs font-semibold truncate">{item.title}</div>
                      <div className="text-[11px] text-slate-400 font-mono truncate">{item.subtitle}</div>
                    </div>
                  </div>

                  <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-950 border border-slate-800 text-slate-400 shrink-0">
                    {item.category}
                  </span>
                </div>
              );
            })
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="px-4 py-2 border-t border-slate-800/80 bg-slate-950/60 flex items-center justify-between text-[11px] font-mono text-slate-500">
          <div className="flex items-center space-x-3">
            <span>↑↓ Navigate</span>
            <span>↵ Select</span>
            <span>ESC Close</span>
          </div>
          <span>ORACLE Search Index</span>
        </div>
      </div>
    </div>
  );
};
