import React, { useEffect, useState } from "react";
import { api } from "./api/client";
import { BlastRadiusModal } from "./components/BlastRadiusModal";
import { CommandPalette } from "./components/CommandPalette";
import { EventTimeline } from "./components/EventTimeline";
import { ImpactDossier } from "./components/ImpactDossier";
import { InvestigationCopilot } from "./components/InvestigationCopilot";
import { KnowledgeGraphView } from "./components/KnowledgeGraphView";
import { LiveFeed } from "./components/LiveFeed";
import { MonitoringRulesView } from "./components/MonitoringRulesView";
import { OverviewDashboard } from "./components/OverviewDashboard";
import { SettingsView } from "./components/SettingsView";
import { Sidebar } from "./components/Sidebar";
import { SourceManager } from "./components/SourceManager";
import { TopNav } from "./components/TopNav";
import {
  BlastRadiusReport,
  ConnectionMode,
  GraphSnapshot,
  ImpactReport,
  IngestionSource,
  IntelligenceEvent,
  InvestigationSession,
  MonitoringRule,
  NavigationTab,
  NotificationItem,
  SystemHealth,
  TimelineEvent,
} from "./types";

export function App() {
  const [activeTab, setActiveTab] = useState<NavigationTab>("overview");
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [events, setEvents] = useState<IntelligenceEvent[]>([]);
  const [graphSnapshot, setGraphSnapshot] = useState<GraphSnapshot | null>(null);
  const [reports, setReports] = useState<ImpactReport[]>([]);
  const [sources, setSources] = useState<IngestionSource[]>([]);
  const [timelineEvents, setTimelineEvents] = useState<TimelineEvent[]>([]);
  const [monitoringRules, setMonitoringRules] = useState<MonitoringRule[]>([]);
  const [investigations, setInvestigations] = useState<InvestigationSession[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);

  // Navigation & Shell State
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [connectionMode, setConnectionMode] = useState<ConnectionMode>(api.getConnectionMode());
  const [isProbing, setIsProbing] = useState(false);

  // Operations state
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncingSourceId, setSyncingSourceId] = useState<string | null>(null);
  const [isGeneratingReport, setIsGeneratingReport] = useState<string | null>(null);

  // Blast Radius Modal state
  const [blastReport, setBlastReport] = useState<BlastRadiusReport | null>(null);
  const [isBlastModalOpen, setIsBlastModalOpen] = useState(false);

  // Selected sub-items state
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
  const [selectedInvestigationId, setSelectedInvestigationId] = useState<string | null>(null);

  // Toast notification
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  // Initial Data Fetch
  const loadAllData = async () => {
    try {
      const [h, evs, snap, rpts, srcs, tl, rules, invs, notifs] = await Promise.all([
        api.getHealth(),
        api.getEvents({ limit: 50 }),
        api.getGraphSnapshot(),
        api.getReports(),
        api.getSources(),
        api.getTimelineEvents(),
        api.getMonitoringRules(),
        api.getInvestigationSessions(),
        api.getNotifications(),
      ]);

      setHealth(h);
      setEvents(evs);
      setGraphSnapshot(snap);
      setReports(rpts);
      setSources(srcs);
      setTimelineEvents(tl);
      setMonitoringRules(rules);
      setInvestigations(invs);
      setNotifications(notifs);
      setConnectionMode(api.getConnectionMode());
    } catch (e: any) {
      console.error("Failed to load ORACLE intelligence data:", e);
    }
  };

  useEffect(() => {
    loadAllData();
  }, []);

  // Keyboard navigation shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger navigation shortcuts if user is typing in an input or textarea
      const target = e.target as HTMLElement;
      const isInput =
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable;

      // Cmd+K or Ctrl+K or '/' to open search
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setIsSearchOpen((prev) => !prev);
        return;
      }
      if (e.key === "/" && !isInput) {
        e.preventDefault();
        setIsSearchOpen(true);
        return;
      }

      if (!isInput && !e.metaKey && !e.ctrlKey && !e.altKey) {
        const tabs: NavigationTab[] = [
          "overview",
          "signals",
          "investigations",
          "graph",
          "reports",
          "timeline",
          "rules",
          "sources",
          "settings",
        ];
        const num = parseInt(e.key, 10);
        if (num >= 1 && num <= 9) {
          e.preventDefault();
          setActiveTab(tabs[num - 1]);
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Probe backend
  const handleProbeBackend = async () => {
    setIsProbing(true);
    const isOnline = await api.probeBackend();
    setIsProbing(false);
    setConnectionMode(api.getConnectionMode());
    if (isOnline) {
      showToast("Live FastAPI backend connected at http://127.0.0.1:8000!");
      await loadAllData();
    } else {
      showToast("Backend unreachable at port 8000. Operating in Demo Mode with typed fixtures.");
    }
  };

  // Sync Trigger
  const handleSyncAll = async () => {
    setIsSyncing(true);
    try {
      const res = await api.triggerSync();
      showToast(
        `Sync completed: ${res.signals_ingested} raw signals ingested, ${res.events_detected} intelligence events classified.`
      );
      await loadAllData();
    } catch (e: any) {
      showToast(`Sync failed: ${e.message}`);
    } finally {
      setIsSyncing(false);
    }
  };

  const handleSourceSync = async (sourceId: string) => {
    setSyncingSourceId(sourceId);
    try {
      const res = await api.triggerSync(sourceId);
      showToast(`Source synced: ${res.events_detected} new events detected.`);
      await loadAllData();
    } catch (e: any) {
      showToast(`Source sync failed: ${e.message}`);
    } finally {
      setSyncingSourceId(null);
    }
  };

  // Blast Radius Exploration
  const handleExploreBlastRadius = async (tech: string, eventId?: string) => {
    try {
      const report = await api.getBlastRadius(tech, 3, eventId);
      setBlastReport(report);
      setIsBlastModalOpen(true);
    } catch (e: any) {
      showToast(`Blast radius calculation failed: ${e.message}`);
    }
  };

  // Generate Impact Dossier
  const handleGenerateReport = async (eventId: string) => {
    setIsGeneratingReport(eventId);
    try {
      const report = await api.analyzeImpact(eventId, 3);
      setReports((prev) => [report, ...prev]);
      setSelectedReportId(report.id);
      setActiveTab("reports");
      showToast(`Impact dossier synthesized for ${report.primary_technology}.`);
    } catch (e: any) {
      showToast(`Report synthesis failed: ${e.message}`);
    } finally {
      setIsGeneratingReport(null);
    }
  };

  // Export Markdown
  const handleExportMarkdown = async (reportId: string) => {
    try {
      const markdown = await api.getReportMarkdown(reportId);
      const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `${reportId}.md`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      showToast(`Exported ${reportId}.md`);
    } catch (e: any) {
      showToast(`Export failed: ${e.message}`);
    }
  };

  // Monitoring Rule Handlers
  const handleToggleRule = async (ruleId: string) => {
    try {
      const updated = await api.toggleMonitoringRule(ruleId);
      setMonitoringRules((prev) => prev.map((r) => (r.id === ruleId ? updated : r)));
      showToast(`Rule "${updated.name}" is now ${updated.enabled ? "Active" : "Paused"}.`);
    } catch (e: any) {
      showToast(`Failed to toggle rule: ${e.message}`);
    }
  };

  const handleCreateRule = async (
    rule: Omit<MonitoringRule, "id" | "trigger_count" | "last_triggered_at">
  ) => {
    try {
      const created = await api.createMonitoringRule(rule);
      setMonitoringRules((prev) => [created, ...prev]);
      showToast(`Monitoring rule "${created.name}" created.`);
    } catch (e: any) {
      showToast(`Failed to create rule: ${e.message}`);
    }
  };

  // Investigation Handlers
  const handleCreateInvestigation = async (title: string, tech: string) => {
    try {
      const session = await api.createInvestigationSession(title, tech);
      setInvestigations((prev) => [session, ...prev]);
      setSelectedInvestigationId(session.id);
      setActiveTab("investigations");
      showToast(`Investigation session started for ${tech}.`);
    } catch (e: any) {
      showToast(`Failed to initialize session: ${e.message}`);
    }
  };

  const criticalCount = events.filter((e) => e.severity === "critical").length;

  return (
    <div className="min-h-screen flex bg-[#090d16] text-slate-100 cyber-grid overflow-hidden">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-5 right-5 z-50 px-4 py-2.5 rounded-xl bg-slate-900 border border-cyan-500/50 text-cyan-300 text-xs font-mono shadow-glow animate-fade-in flex items-center space-x-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Global Command Palette */}
      <CommandPalette
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        events={events}
        reports={reports}
        snapshot={graphSnapshot}
        investigations={investigations}
        onNavigate={(tab, targetId) => {
          setActiveTab(tab);
          if (tab === "reports" && targetId) setSelectedReportId(targetId);
          if (tab === "investigations" && targetId) setSelectedInvestigationId(targetId);
        }}
        onExploreBlastRadius={handleExploreBlastRadius}
      />

      {/* Mobile Drawer Backdrop */}
      {isMobileMenuOpen && (
        <div
          onClick={() => setIsMobileMenuOpen(false)}
          className="fixed inset-0 z-40 bg-black/80 backdrop-blur-sm md:hidden"
        />
      )}

      {/* Collapsible Left Sidebar */}
      <div
        className={`fixed md:static inset-y-0 left-0 z-50 transform md:transform-none transition-transform duration-300 ${
          isMobileMenuOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        }`}
      >
        <Sidebar
          activeTab={activeTab}
          setActiveTab={(tab) => {
            setActiveTab(tab);
            setIsMobileMenuOpen(false);
          }}
          isCollapsed={isSidebarCollapsed}
          setIsCollapsed={setIsSidebarCollapsed}
          criticalCount={criticalCount}
          reportCount={reports.length}
        />
      </div>

      {/* Main App Workspace */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-hidden">
        {/* Top Navigation */}
        <TopNav
          health={health}
          connectionMode={connectionMode}
          onProbeBackend={handleProbeBackend}
          isProbing={isProbing}
          onSync={handleSyncAll}
          isSyncing={isSyncing}
          notifications={notifications}
          onOpenSearch={() => setIsSearchOpen(true)}
          onNavigateTab={(tab, targetId) => {
            setActiveTab(tab);
            if (tab === "reports" && targetId) setSelectedReportId(targetId);
            if (tab === "investigations" && targetId) setSelectedInvestigationId(targetId);
          }}
          onToggleMobileMenu={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
        />

        {/* Scrollable View Area */}
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          <div className="max-w-7xl mx-auto">
            {activeTab === "overview" && (
              <OverviewDashboard
                health={health}
                events={events}
                reports={reports}
                sources={sources}
                snapshot={graphSnapshot}
                investigations={investigations}
                onNavigateTab={(tab, targetId) => {
                  setActiveTab(tab);
                  if (tab === "reports" && targetId) setSelectedReportId(targetId);
                  if (tab === "investigations" && targetId) setSelectedInvestigationId(targetId);
                }}
                onExploreBlastRadius={handleExploreBlastRadius}
                onGenerateReport={handleGenerateReport}
                isGeneratingReport={isGeneratingReport}
              />
            )}

            {activeTab === "signals" && (
              <LiveFeed
                events={events}
                onExploreBlastRadius={handleExploreBlastRadius}
                onGenerateReport={handleGenerateReport}
                isGeneratingReport={isGeneratingReport}
              />
            )}

            {activeTab === "investigations" && (
              <InvestigationCopilot
                sessions={investigations}
                activeSessionId={selectedInvestigationId}
                onSelectSession={(id) => setSelectedInvestigationId(id)}
                onCreateSession={handleCreateInvestigation}
                onExploreBlastRadius={handleExploreBlastRadius}
              />
            )}

            {activeTab === "graph" && (
              <KnowledgeGraphView
                snapshot={graphSnapshot}
                onSelectNode={(nodeId) => handleExploreBlastRadius(nodeId)}
                onSynthesizeReport={(nodeId) => {
                  const match = events.find((e) => e.primary_technology === nodeId);
                  if (match) handleGenerateReport(match.id);
                  else showToast(`No active detected event found for ${nodeId}.`);
                }}
              />
            )}

            {activeTab === "reports" && (
              <ImpactDossier
                reports={reports}
                selectedReportId={selectedReportId}
                onSelectReport={(id) => setSelectedReportId(id)}
                onExportMarkdown={handleExportMarkdown}
              />
            )}

            {activeTab === "timeline" && (
              <EventTimeline
                events={timelineEvents}
                onSelectTechnology={(tech) => handleExploreBlastRadius(tech)}
              />
            )}

            {activeTab === "rules" && (
              <MonitoringRulesView
                rules={monitoringRules}
                onToggleRule={handleToggleRule}
                onCreateRule={handleCreateRule}
              />
            )}

            {activeTab === "sources" && (
              <SourceManager
                sources={sources}
                onTriggerSourceSync={handleSourceSync}
                isSyncingId={syncingSourceId}
              />
            )}

            {activeTab === "settings" && (
              <SettingsView
                health={health}
                connectionMode={connectionMode}
                onSetConnectionMode={(mode) => {
                  api.setConnectionMode(mode);
                  setConnectionMode(mode);
                  showToast(`Switched runtime adapter to ${mode}.`);
                }}
                onProbeBackend={handleProbeBackend}
                isProbing={isProbing}
                onShowToast={showToast}
              />
            )}
          </div>
        </main>
      </div>

      {/* Blast Radius Modal */}
      <BlastRadiusModal
        report={blastReport}
        isOpen={isBlastModalOpen}
        onClose={() => setIsBlastModalOpen(false)}
        onSynthesizeReport={(tech) => {
          const matchingEvent = events.find((e) => e.primary_technology === tech);
          if (matchingEvent) {
            handleGenerateReport(matchingEvent.id);
          } else {
            showToast(`No active detected event found for ${tech}.`);
          }
        }}
      />
    </div>
  );
}

export default App;
