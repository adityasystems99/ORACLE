import React, { useEffect, useState } from "react";
import { api } from "./api/client";
import { BlastRadiusModal } from "./components/BlastRadiusModal";
import { ImpactDossier } from "./components/ImpactDossier";
import { KnowledgeGraphView } from "./components/KnowledgeGraphView";
import { LiveFeed } from "./components/LiveFeed";
import { Navbar } from "./components/Navbar";
import { SourceManager } from "./components/SourceManager";
import {
  BlastRadiusReport,
  GraphSnapshot,
  ImpactReport,
  IngestionSource,
  IntelligenceEvent,
  SystemHealth,
} from "./types";

export function App() {
  const [activeTab, setActiveTab] = useState<"feed" | "graph" | "reports" | "sources">("feed");
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [events, setEvents] = useState<IntelligenceEvent[]>([]);
  const [graphSnapshot, setGraphSnapshot] = useState<GraphSnapshot | null>(null);
  const [reports, setReports] = useState<ImpactReport[]>([]);
  const [sources, setSources] = useState<IngestionSource[]>([]);

  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [syncingSourceId, setSyncingSourceId] = useState<string | null>(null);
  const [isGeneratingReport, setIsGeneratingReport] = useState<string | null>(null);

  // Blast Radius Modal state
  const [blastReport, setBlastReport] = useState<BlastRadiusReport | null>(null);
  const [isBlastModalOpen, setIsBlastModalOpen] = useState<boolean>(false);

  // Selected Dossier state
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);

  // Notification toast
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 4000);
  };

  // Initial Data Fetch
  const loadInitialData = async () => {
    try {
      const [h, evs, snap, rpts, srcs] = await Promise.all([
        api.getHealth(),
        api.getEvents({ limit: 50 }),
        api.getGraphSnapshot(),
        api.getReports(),
        api.getSources(),
      ]);
      setHealth(h);
      setEvents(evs);
      setGraphSnapshot(snap);
      setReports(rpts);
      setSources(srcs);
    } catch (e) {
      console.error("Failed to load initial ORACLE data:", e);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  // Sync Trigger
  const handleSyncAll = async () => {
    setIsSyncing(true);
    try {
      const res = await api.triggerSync();
      showToast(
        `Sync completed: ${res.signals_ingested} raw signals ingested, ${res.events_detected} intelligence events classified.`
      );
      await loadInitialData();
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
      await loadInitialData();
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
      showToast(`Impact dossier successfully generated for ${report.primary_technology}.`);
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

  return (
    <div className="min-h-screen flex flex-col bg-[#090d16] text-slate-100 cyber-grid">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-5 right-5 z-50 px-4 py-2.5 rounded-xl bg-slate-900 border border-cyan-500/50 text-cyan-300 text-xs font-mono shadow-glow animate-fade-in flex items-center space-x-2">
          <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Main Navigation */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        health={health}
        onSync={handleSyncAll}
        isSyncing={isSyncing}
      />

      {/* Primary Content Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {activeTab === "feed" && (
          <LiveFeed
            events={events}
            onExploreBlastRadius={(tech, id) => handleExploreBlastRadius(tech, id)}
            onGenerateReport={handleGenerateReport}
            isGeneratingReport={isGeneratingReport}
          />
        )}

        {activeTab === "graph" && (
          <KnowledgeGraphView
            snapshot={graphSnapshot}
            onSelectNode={(nodeId) => handleExploreBlastRadius(nodeId)}
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

        {activeTab === "sources" && (
          <SourceManager
            sources={sources}
            onTriggerSourceSync={handleSourceSync}
            isSyncingId={syncingSourceId}
          />
        )}
      </main>

      {/* Blast Radius Modal */}
      <BlastRadiusModal
        report={blastReport}
        isOpen={isBlastModalOpen}
        onClose={() => setIsBlastModalOpen(false)}
        onSynthesizeReport={(tech) => {
          // If we have an event matching this tech, trigger report
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
