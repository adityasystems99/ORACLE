import React, { useState } from "react";
import {
  Bell,
  CheckCircle,
  Database,
  ExternalLink,
  Layers,
  Menu,
  RefreshCw,
  Search,
  ShieldAlert,
  Sparkles,
  User,
  Wifi,
  WifiOff,
  X,
} from "lucide-react";
import { ConnectionMode, NavigationTab, NotificationItem, SystemHealth } from "../types";

interface TopNavProps {
  health: SystemHealth | null;
  connectionMode: ConnectionMode;
  onProbeBackend: () => void;
  isProbing: boolean;
  onSync: () => void;
  isSyncing: boolean;
  notifications: NotificationItem[];
  onOpenSearch: () => void;
  onNavigateTab: (tab: NavigationTab, targetId?: string) => void;
  onToggleMobileMenu: () => void;
}

export const TopNav: React.FC<TopNavProps> = ({
  health,
  connectionMode,
  onProbeBackend,
  isProbing,
  onSync,
  isSyncing,
  notifications,
  onOpenSearch,
  onNavigateTab,
  onToggleMobileMenu,
}) => {
  const [isNotifOpen, setIsNotifOpen] = useState(false);
  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <header className="sticky top-0 z-40 border-b border-slate-800 bg-[#090d16]/90 backdrop-blur-md">
      <div className="flex h-16 items-center justify-between px-4 sm:px-6">
        {/* Left: Mobile Toggle & Workspace Name */}
        <div className="flex items-center space-x-3">
          <button
            onClick={onToggleMobileMenu}
            className="md:hidden p-1.5 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white"
            title="Toggle Menu"
          >
            <Menu className="h-5 w-5" />
          </button>

          <div className="hidden sm:flex items-center space-x-2">
            <span className="text-xs font-mono font-semibold uppercase text-slate-400">Workspace:</span>
            <div className="flex items-center space-x-1.5 px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-xs font-mono text-slate-200">
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
              <span>Production Intel Pipeline</span>
            </div>
          </div>
        </div>

        {/* Center: Global Search Bar */}
        <div className="flex-1 max-w-md mx-4">
          <button
            onClick={onOpenSearch}
            className="w-full flex items-center justify-between px-3 py-1.5 rounded-lg bg-slate-950/70 border border-slate-800 text-xs text-slate-400 hover:border-slate-700 hover:text-slate-200 transition-all shadow-inner group"
          >
            <div className="flex items-center space-x-2 truncate">
              <Search className="h-3.5 w-3.5 text-slate-500 group-hover:text-cyan-400 transition-colors" />
              <span className="truncate">Search intelligence, CVEs, graph entities...</span>
            </div>
            <kbd className="hidden sm:inline-flex items-center space-x-1 px-1.5 py-0.5 text-[10px] font-mono rounded bg-slate-900 border border-slate-700 text-slate-400">
              <span>⌘</span>
              <span>K</span>
            </kbd>
          </button>
        </div>

        {/* Right: Telemetry, Connection, Notifications, Sync, Profile */}
        <div className="flex items-center space-x-2 sm:space-x-3">
          {/* Connection Mode Indicator */}
          {connectionMode === "connected" ? (
            <div
              className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-emerald-950/40 border border-emerald-800/60 text-emerald-400 text-xs font-mono"
              title="Connected to Live FastAPI Backend"
            >
              <Wifi className="h-3.5 w-3.5 text-emerald-400 animate-pulse" />
              <span className="hidden lg:inline">Live API</span>
            </div>
          ) : (
            <div className="flex items-center space-x-1.5">
              <div
                className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-amber-950/40 border border-amber-800/60 text-amber-300 text-xs font-mono"
                title="Backend offline: Operating on typed demo intelligence fixtures"
              >
                <WifiOff className="h-3.5 w-3.5 text-amber-400" />
                <span className="hidden md:inline">Demo Fixtures</span>
              </div>
              <button
                onClick={onProbeBackend}
                disabled={isProbing}
                className="px-2 py-1 rounded text-[11px] font-mono text-slate-400 hover:text-cyan-400 hover:bg-slate-800 transition-colors"
                title="Probe backend connection at /api/system/health"
              >
                {isProbing ? "Probing..." : "Retry"}
              </button>
            </div>
          )}

          {/* Sync Trigger Button */}
          <button
            onClick={onSync}
            disabled={isSyncing}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold font-mono transition-all ${
              isSyncing
                ? "bg-slate-800 text-slate-400 cursor-not-allowed"
                : "bg-cyan-500 text-slate-950 hover:bg-cyan-400 shadow-glow"
            }`}
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isSyncing ? "animate-spin" : ""}`} />
            <span className="hidden sm:inline">{isSyncing ? "Syncing..." : "Sync Live"}</span>
          </button>

          {/* Notifications Dropdown */}
          <div className="relative">
            <button
              onClick={() => setIsNotifOpen(!isNotifOpen)}
              className="relative p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/60 transition-colors"
              title="Notifications"
            >
              <Bell className="h-4 w-4" />
              {unreadCount > 0 && (
                <span className="absolute top-1.5 right-1.5 flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500" />
                </span>
              )}
            </button>

            {isNotifOpen && (
              <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-xl bg-slate-900 border border-slate-800 shadow-2xl py-2 z-50 animate-fade-in">
                <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800">
                  <span className="text-xs font-bold font-mono text-slate-200 uppercase tracking-wider">
                    Intelligence Alerts ({notifications.length})
                  </span>
                  <button
                    onClick={() => setIsNotifOpen(false)}
                    className="text-slate-500 hover:text-slate-300"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>

                <div className="max-h-80 overflow-y-auto divide-y divide-slate-800/60">
                  {notifications.map((item) => (
                    <div
                      key={item.id}
                      onClick={() => {
                        setIsNotifOpen(false);
                        if (item.targetTab) onNavigateTab(item.targetTab, item.targetId);
                      }}
                      className="p-3 hover:bg-slate-800/40 cursor-pointer transition-colors space-y-1"
                    >
                      <div className="flex items-center justify-between text-xs">
                        <span
                          className={`font-semibold ${
                            item.severity === "critical"
                              ? "text-rose-400"
                              : item.severity === "high"
                              ? "text-amber-400"
                              : "text-cyan-400"
                          }`}
                        >
                          {item.title}
                        </span>
                        <span className="text-[10px] font-mono text-slate-500">
                          {new Date(item.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-300 leading-snug">{item.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* User Profile Menu */}
          <div className="flex items-center space-x-2 pl-2 border-l border-slate-800">
            <div className="h-8 w-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 text-xs font-mono font-bold">
              OP
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};
