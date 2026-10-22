import React from "react";
import {
  Activity,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Clock,
  Compass,
  Cpu,
  FileText,
  Layers,
  MessageSquare,
  Radio,
  Rss,
  Settings,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { NavigationTab } from "../types";

interface SidebarProps {
  activeTab: NavigationTab;
  setActiveTab: (tab: NavigationTab) => void;
  isCollapsed: boolean;
  setIsCollapsed: (collapsed: boolean) => void;
  criticalCount?: number;
  reportCount?: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  setActiveTab,
  isCollapsed,
  setIsCollapsed,
  criticalCount = 0,
  reportCount = 0,
}) => {
  const navItems = [
    {
      id: "overview" as NavigationTab,
      label: "Overview",
      icon: Compass,
      shortcut: "1",
      badge: null,
    },
    {
      id: "signals" as NavigationTab,
      label: "Live Signals",
      icon: Radio,
      shortcut: "2",
      badge: criticalCount > 0 ? `${criticalCount} crit` : null,
      badgeColor: "bg-rose-500/20 text-rose-400 border border-rose-500/30",
    },
    {
      id: "investigations" as NavigationTab,
      label: "Investigations",
      icon: MessageSquare,
      shortcut: "3",
      badge: "Copilot",
      badgeColor: "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30",
    },
    {
      id: "graph" as NavigationTab,
      label: "Knowledge Graph",
      icon: Cpu,
      shortcut: "4",
      badge: null,
    },
    {
      id: "reports" as NavigationTab,
      label: "Impact Reports",
      icon: FileText,
      shortcut: "5",
      badge: reportCount > 0 ? `${reportCount}` : null,
      badgeColor: "bg-amber-500/20 text-amber-400 border border-amber-500/30",
    },
    {
      id: "timeline" as NavigationTab,
      label: "Event Timeline",
      icon: Clock,
      shortcut: "6",
      badge: null,
    },
    {
      id: "rules" as NavigationTab,
      label: "Monitoring Rules",
      icon: ShieldAlert,
      shortcut: "7",
      badge: null,
    },
    {
      id: "sources" as NavigationTab,
      label: "Data Ingestion",
      icon: Rss,
      shortcut: "8",
      badge: null,
    },
    {
      id: "settings" as NavigationTab,
      label: "System Settings",
      icon: Settings,
      shortcut: "9",
      badge: null,
    },
  ];

  return (
    <aside
      className={`relative z-30 flex flex-col border-r border-slate-800 bg-[#070b12]/95 backdrop-blur-md transition-all duration-300 select-none ${
        isCollapsed ? "w-16" : "w-64"
      }`}
    >
      {/* Brand Header */}
      <div className="flex h-16 items-center justify-between border-b border-slate-800/80 px-4">
        <div
          onClick={() => setActiveTab("overview")}
          className="flex items-center space-x-3 cursor-pointer group"
          title="ORACLE — Live Intelligence Copilot"
        >
          <div className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-tr from-cyan-600 via-sky-500 to-indigo-600 p-[1px] shadow-glow">
            <div className="flex h-full w-full items-center justify-center rounded-[7px] bg-[#090d16]">
              <Activity className="h-4 w-4 text-cyan-400 animate-pulse" />
            </div>
          </div>

          {!isCollapsed && (
            <div className="overflow-hidden">
              <div className="flex items-center space-x-2">
                <span className="font-mono text-base font-bold tracking-wider text-white group-hover:text-cyan-300 transition-colors">
                  ORACLE
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-cyan-950/80 text-cyan-400 border border-cyan-800/60 uppercase">
                  v2.4
                </span>
              </div>
              <p className="text-[10px] font-mono text-slate-400 truncate">Live Intel Workspace</p>
            </div>
          )}
        </div>
      </div>

      {/* Navigation Links */}
      <div className="flex-1 overflow-y-auto px-2 py-4 space-y-1">
        {!isCollapsed && (
          <div className="px-3 pb-2 text-[10px] font-mono font-semibold uppercase tracking-wider text-slate-500">
            Navigation
          </div>
        )}

        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;

          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              title={isCollapsed ? item.label : undefined}
              className={`group relative flex w-full items-center rounded-lg px-3 py-2 text-xs font-medium transition-all ${
                isActive
                  ? "bg-cyan-500/10 text-cyan-300 font-semibold border border-cyan-500/30 shadow-glow"
                  : "text-slate-400 hover:bg-slate-800/50 hover:text-slate-100"
              } ${isCollapsed ? "justify-center" : "justify-between"}`}
            >
              <div className="flex items-center space-x-3 truncate">
                <Icon
                  className={`h-4 w-4 shrink-0 transition-colors ${
                    isActive ? "text-cyan-400" : "text-slate-400 group-hover:text-slate-200"
                  }`}
                />
                {!isCollapsed && <span className="truncate">{item.label}</span>}
              </div>

              {!isCollapsed && (
                <div className="flex items-center space-x-1.5">
                  {item.badge && (
                    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${item.badgeColor}`}>
                      {item.badge}
                    </span>
                  )}
                  <span className="text-[10px] font-mono text-slate-600 group-hover:text-slate-400">
                    {item.shortcut}
                  </span>
                </div>
              )}

              {/* Active pill indicator */}
              {isActive && (
                <span className="absolute left-0 top-1.5 bottom-1.5 w-1 rounded-r bg-cyan-400" />
              )}
            </button>
          );
        })}
      </div>

      {/* Workspace Status Card / Toggle */}
      <div className="border-t border-slate-800/80 p-3 bg-slate-950/40">
        {!isCollapsed ? (
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="h-2 w-2 rounded-full bg-emerald-400 radar-live shrink-0" />
              <div className="overflow-hidden">
                <p className="text-[11px] font-mono font-medium text-slate-300 truncate">Autonomous Sentinel</p>
                <p className="text-[9px] font-mono text-slate-500">Telemetry Active</p>
              </div>
            </div>

            <button
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="p-1 rounded text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
              title="Collapse sidebar"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
          </div>
        ) : (
          <div className="flex justify-center">
            <button
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="p-1.5 rounded text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
              title="Expand sidebar"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>
    </aside>
  );
};
