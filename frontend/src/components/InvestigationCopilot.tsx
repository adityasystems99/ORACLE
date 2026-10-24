import React, { useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  BookmarkCheck,
  Bot,
  Calendar,
  Check,
  CheckCircle2,
  ChevronRight,
  Copy,
  ExternalLink,
  GitBranch,
  Hash,
  MessageSquare,
  Paperclip,
  Plus,
  RefreshCw,
  Send,
  Shield,
  ShieldAlert,
  Sparkles,
  Terminal,
  User,
  X,
} from "lucide-react";
import { api } from "../api/client";
import { EvidenceRef, InvestigationMessage, InvestigationSession } from "../types";

interface InvestigationCopilotProps {
  sessions: InvestigationSession[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onCreateSession: (title: string, tech: string) => void;
  onExploreBlastRadius: (tech: string) => void;
  onUpdateSession?: (session: InvestigationSession) => void;
}

export const InvestigationCopilot: React.FC<InvestigationCopilotProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onCreateSession,
  onExploreBlastRadius,
  onUpdateSession,
}) => {
  const currentSession = sessions.find((s) => s.id === activeSessionId) || sessions[0] || null;

  const [inputPrompt, setInputPrompt] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamedText, setStreamedText] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<EvidenceRef | null>(null);
  const [isInspectorOpen, setIsInspectorOpen] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastFailedPrompt, setLastFailedPrompt] = useState<string | null>(null);

  // All citations across current session messages
  const allSessionCitations = React.useMemo(() => {
    if (!currentSession) return [];
    const list: EvidenceRef[] = [];
    const seenUrls = new Set<string>();
    currentSession.messages.forEach((m) => {
      m.citations?.forEach((c) => {
        if (!seenUrls.has(c.source_url)) {
          seenUrls.add(c.source_url);
          list.push(c);
        }
      });
    });
    return list;
  }, [currentSession]);

  // New session modal
  const [isNewModalOpen, setIsNewModalOpen] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newTech, setNewTech] = useState("");

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [currentSession?.messages, streamedText]);

  const handleSendMessage = async (textToSend?: string) => {
    const text = textToSend || inputPrompt;
    if (!text.trim() || !currentSession || isStreaming) return;

    setInputPrompt("");
    setErrorMessage(null);
    setLastFailedPrompt(null);
    setIsStreaming(true);
    setStreamedText("");

    try {
      const assistantMsg = await api.sendInvestigationMessage(currentSession.id, text, (token) => {
        setStreamedText((prev) => prev + token);
      });
      if (onUpdateSession && currentSession) {
        onUpdateSession({
          ...currentSession,
          messages: [...currentSession.messages, assistantMsg],
          updated_at: new Date().toISOString(),
        });
      }
    } catch (e: any) {
      console.error("Failed to stream copilot response:", e);
      setErrorMessage(e.message || "Network request failed. Verify backend connectivity.");
      setLastFailedPrompt(text);
    } finally {
      setIsStreaming(false);
      setStreamedText("");
    }
  };

  const handleRetry = () => {
    if (lastFailedPrompt) {
      handleSendMessage(lastFailedPrompt);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const copyCode = (code: string, id: string) => {
    navigator.clipboard.writeText(code);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleCreateNew = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim() || !newTech.trim()) return;
    onCreateSession(newTitle.trim(), newTech.trim().toLowerCase());
    setNewTitle("");
    setNewTech("");
    setIsNewModalOpen(false);
  };

  return (
    <div className="h-[calc(100vh-8.5rem)] flex flex-col md:flex-row gap-4">
      {/* Left Column: Sessions List */}
      <div className="w-full md:w-72 shrink-0 flex flex-col rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm overflow-hidden">
        {/* Header & New Button */}
        <div className="p-3.5 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <MessageSquare className="w-4 h-4 text-cyan-400" />
            <span className="text-xs font-bold font-mono text-white uppercase tracking-wider">
              Investigations
            </span>
          </div>

          <button
            onClick={() => setIsNewModalOpen(true)}
            className="flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-cyan-500 text-slate-950 hover:bg-cyan-400 text-xs font-bold font-mono transition-all shadow-glow"
            title="Create New Investigation"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New</span>
          </button>
        </div>

        {/* Sessions scrollable list */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
          {sessions.map((sess) => {
            const isSelected = sess.id === currentSession?.id;
            return (
              <div
                key={sess.id}
                onClick={() => onSelectSession(sess.id)}
                className={`p-3 rounded-xl cursor-pointer transition-all space-y-1.5 ${
                  isSelected
                    ? "bg-cyan-500/10 border border-cyan-500/40 shadow-glow"
                    : "bg-slate-950/40 border border-slate-800/80 hover:border-slate-700"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-slate-800 text-cyan-400">
                    {sess.primary_technology}
                  </span>
                  <span className="text-[10px] font-mono text-slate-500">
                    {new Date(sess.updated_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </span>
                </div>
                <h4 className="text-xs font-semibold text-slate-200 line-clamp-1">{sess.title}</h4>
                <div className="text-[10px] font-mono text-slate-400 truncate">
                  {sess.messages.length} messages • {sess.status}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Center Column: Active Chat Thread */}
      <div className="flex-1 flex flex-col rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm overflow-hidden">
        {/* Thread Header */}
        {currentSession && (
          <div className="p-4 border-b border-slate-800 bg-slate-950/40 flex items-center justify-between">
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
                  {currentSession.primary_technology}
                </span>
                <span className="text-xs font-mono text-slate-400 font-bold uppercase">
                  {currentSession.severity}
                </span>
              </div>
              <h3 className="text-sm font-bold text-white mt-1 font-mono">{currentSession.title}</h3>
            </div>

            <div className="flex items-center space-x-2">
              <button
                onClick={() => onExploreBlastRadius(currentSession.primary_technology)}
                className="px-2.5 py-1.5 rounded-lg text-xs font-mono bg-slate-800 text-slate-200 hover:bg-slate-700 transition-colors"
              >
                Blast Radius
              </button>

              <button
                onClick={() => setIsInspectorOpen(!isInspectorOpen)}
                className={`px-2.5 py-1.5 rounded-lg text-xs font-mono transition-colors flex items-center space-x-1.5 ${
                  isInspectorOpen
                    ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                    : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                }`}
              >
                <Shield className="w-3.5 h-3.5 text-cyan-400" />
                <span className="hidden sm:inline">Evidence ({allSessionCitations.length})</span>
              </button>
            </div>
          </div>
        )}

        {/* Message Stream */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {currentSession?.messages.map((msg) => {
            const isUser = msg.role === "user";

            return (
              <div
                key={msg.id}
                className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}
              >
                {!isUser && (
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-600 to-sky-400 p-[1px] shrink-0 mt-0.5">
                    <div className="w-full h-full bg-[#090d16] rounded-[7px] flex items-center justify-center">
                      <Bot className="w-4 h-4 text-cyan-400" />
                    </div>
                  </div>
                )}

                <div
                  className={`max-w-2xl rounded-2xl p-4 space-y-3 ${
                    isUser
                      ? "bg-cyan-950/30 border border-cyan-800/40 text-slate-100"
                      : "bg-slate-950/80 border border-slate-800/90 text-slate-200"
                  }`}
                >
                  {/* Grounding Status Header for Assistant */}
                  {!isUser && msg.grounding_status && (
                    <div className="pb-1 border-b border-slate-800/70">
                      {msg.grounding_status === "insufficient_evidence" ? (
                        <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-amber-500/10 border border-amber-500/30 text-amber-400 text-[10px] font-mono">
                          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                          <span>Insufficient Evidence in Monitored Sources</span>
                        </div>
                      ) : (
                        <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-[10px] font-mono">
                          <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                          <span>Grounded in Live RAG & Temporal Knowledge Graph</span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Message Content */}
                  <div className="text-xs sm:text-sm leading-relaxed whitespace-pre-wrap font-sans">
                    {msg.content}
                  </div>

                  {/* Code Snippets */}
                  {msg.codeSnippets &&
                    msg.codeSnippets.map((cs, i) => (
                      <div key={i} className="relative group rounded-xl overflow-hidden border border-slate-800 bg-slate-900">
                        {cs.filename && (
                          <div className="px-3 py-1.5 bg-slate-950 border-b border-slate-800 text-[10px] font-mono text-slate-400 flex items-center justify-between">
                            <span>{cs.filename}</span>
                            <span className="uppercase text-slate-500">{cs.language}</span>
                          </div>
                        )}
                        <pre className="p-3 text-xs font-mono text-cyan-300 overflow-x-auto">
                          {cs.code}
                        </pre>
                        <button
                          onClick={() => copyCode(cs.code, `${msg.id}-${i}`)}
                          className="absolute right-2 top-2 p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
                          title="Copy Code"
                        >
                          {copiedId === `${msg.id}-${i}` ? (
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                      </div>
                    ))}

                  {/* Explainable Graph Paths */}
                  {msg.graph_paths && msg.graph_paths.length > 0 && (
                    <div className="pt-2 border-t border-slate-800/80 space-y-1.5">
                      <div className="flex items-center space-x-1 text-[10px] font-mono text-cyan-400 uppercase font-bold">
                        <GitBranch className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                        <span>Explainable Graph Paths ({msg.graph_paths.length}):</span>
                      </div>
                      <div className="space-y-1">
                        {msg.graph_paths.map((gp, gIdx) => (
                          <div
                            key={gIdx}
                            className="px-2.5 py-1 rounded-lg bg-slate-900/90 border border-slate-800 text-[11px] font-mono text-cyan-200"
                          >
                            {gp}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Citations badges */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="pt-2 border-t border-slate-800/80 flex flex-wrap items-center gap-2">
                      <span className="text-[10px] font-mono text-slate-500">Citations:</span>
                      {msg.citations.map((cite, idx) => (
                        <button
                          key={idx}
                          onClick={() => {
                            setSelectedCitation(cite);
                            setIsInspectorOpen(true);
                          }}
                          className="flex items-center space-x-1 px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-[10px] font-mono text-cyan-400 hover:border-cyan-500 hover:bg-cyan-950/20 transition-colors"
                          title="Click to inspect ground-truth snippet and SHA256"
                        >
                          <Shield className="w-3 h-3 text-cyan-400" />
                          <span className="truncate max-w-[150px]">{cite.title}</span>
                          {cite.document_version && (
                            <span className="text-[9px] text-slate-400 font-mono">v{cite.document_version}</span>
                          )}
                        </button>
                      ))}
                    </div>
                  )}

                  {/* Epistemic Uncertainty & Boundaries */}
                  {msg.uncertainty_notes && msg.uncertainty_notes.length > 0 && (
                    <details className="pt-2 border-t border-slate-800/60 text-[11px] font-mono group">
                      <summary className="cursor-pointer text-amber-400 hover:text-amber-300 font-bold flex items-center space-x-1.5 select-none">
                        <AlertCircle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                        <span>Epistemic Uncertainty & Epistemic Boundaries ({msg.uncertainty_notes.length})</span>
                      </summary>
                      <ul className="list-disc pl-5 mt-2 space-y-1 text-slate-400 leading-relaxed">
                        {msg.uncertainty_notes.map((note, nIdx) => (
                          <li key={nIdx}>{note}</li>
                        ))}
                      </ul>
                    </details>
                  )}

                  {/* Suggested Follow-up Questions */}
                  {msg.suggestedFollowUps && msg.suggestedFollowUps.length > 0 && (
                    <div className="pt-2 border-t border-slate-800/60 space-y-1.5">
                      <span className="text-[10px] font-mono uppercase text-slate-500">
                        Suggested Follow-ups:
                      </span>
                      <div className="flex flex-wrap gap-1.5">
                        {msg.suggestedFollowUps.map((prompt, pIdx) => (
                          <button
                            key={pIdx}
                            onClick={() => handleSendMessage(prompt)}
                            disabled={isStreaming}
                            className="px-2.5 py-1 rounded-lg bg-slate-900/90 border border-slate-800 text-[11px] text-slate-300 hover:border-cyan-500/50 hover:text-cyan-300 transition-all font-mono text-left flex items-center space-x-1.5"
                          >
                            <Sparkles className="w-3 h-3 text-cyan-400 shrink-0" />
                            <span>{prompt}</span>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="text-[9px] font-mono text-slate-500 text-right">
                    {new Date(msg.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </div>
                </div>

                {isUser && (
                  <div className="w-8 h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 shrink-0 mt-0.5">
                    <User className="w-4 h-4" />
                  </div>
                )}
              </div>
            );
          })}

          {/* Active Streaming Token Render */}
          {isStreaming && (
            <div className="flex gap-3 justify-start">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-600 to-sky-400 p-[1px] shrink-0 mt-0.5">
                <div className="w-full h-full bg-[#090d16] rounded-[7px] flex items-center justify-center">
                  <Bot className="w-4 h-4 text-cyan-400 animate-spin" />
                </div>
              </div>
              <div className="max-w-2xl rounded-2xl p-4 bg-slate-950/80 border border-cyan-500/30 text-slate-200 space-y-2">
                <div className="text-xs sm:text-sm leading-relaxed whitespace-pre-wrap font-sans">
                  {streamedText || "Retrieving live RAG evidence and traversing temporal graph..."}
                  <span className="inline-block w-1.5 h-3.5 bg-cyan-400 animate-pulse ml-1" />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Error and Retry Banner */}
        {errorMessage && (
          <div className="px-4 py-2 bg-red-950/50 border-t border-red-800/60 flex items-center justify-between text-xs font-mono text-red-200">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-red-400 shrink-0" />
              <span>{errorMessage}</span>
            </div>
            {lastFailedPrompt && (
              <button
                onClick={handleRetry}
                className="px-2.5 py-1 rounded bg-red-900 hover:bg-red-800 text-white font-bold flex items-center space-x-1"
              >
                <RefreshCw className="w-3 h-3" />
                <span>Retry</span>
              </button>
            )}
          </div>
        )}

        {/* Input Bar */}
        <div className="p-3 border-t border-slate-800 bg-slate-950/80">
          <div className="relative flex items-center">
            <textarea
              rows={2}
              value={inputPrompt}
              onChange={(e) => setInputPrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask ORACLE Copilot about breaking changes, blast radius, migration steps... (Enter to send)"
              className="w-full pl-4 pr-24 py-2.5 bg-slate-900 border border-slate-800 rounded-xl text-xs sm:text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 resize-none"
            />
            <div className="absolute right-3 flex items-center space-x-2">
              <button
                onClick={() => handleSendMessage()}
                disabled={!inputPrompt.trim() || isStreaming}
                className={`p-2 rounded-lg font-mono text-xs font-semibold transition-all ${
                  inputPrompt.trim() && !isStreaming
                    ? "bg-cyan-500 text-slate-950 hover:bg-cyan-400 shadow-glow"
                    : "bg-slate-800 text-slate-500 cursor-not-allowed"
                }`}
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Right Drawer: Ground-Truth Evidence & Source Inspector */}
      {isInspectorOpen && (
        <div className="w-full md:w-80 shrink-0 flex flex-col rounded-2xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm overflow-hidden animate-fade-in">
          <div className="p-3.5 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Shield className="w-4 h-4 text-cyan-400" />
              <span className="text-xs font-bold font-mono text-white uppercase tracking-wider">
                Source Inspector
              </span>
            </div>
            <button
              onClick={() => setIsInspectorOpen(false)}
              className="p-1 rounded text-slate-400 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-3">
            {selectedCitation ? (
              <div className="space-y-3">
                <button
                  onClick={() => setSelectedCitation(null)}
                  className="text-[11px] font-mono text-cyan-400 hover:text-cyan-300 flex items-center space-x-1"
                >
                  <span>← All Session Citations ({allSessionCitations.length})</span>
                </button>

                <div className="p-3.5 rounded-xl bg-slate-950/80 border border-cyan-500/40 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800 font-bold">
                      {selectedCitation.publisher || selectedCitation.source_type || "Source"}
                    </span>
                    <a
                      href={selectedCitation.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center space-x-1 text-cyan-400 hover:text-cyan-300 text-xs font-mono"
                    >
                      <span>External URL</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>

                  <h4 className="text-xs font-bold text-white">{selectedCitation.title}</h4>

                  {selectedCitation.is_superseded && (
                    <div className="p-2 rounded bg-amber-950/60 border border-amber-800/60 text-[10px] font-mono text-amber-300 flex items-center space-x-1">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                      <span>Superseded by newer release version</span>
                    </div>
                  )}

                  <p className="text-xs text-slate-300 italic bg-slate-900/80 p-2.5 rounded border border-slate-800 font-mono leading-relaxed">
                    "{selectedCitation.snippet}"
                  </p>

                  <div className="space-y-1 text-[10px] font-mono text-slate-400 pt-2 border-t border-slate-800">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Document Version:</span>
                      <span className="text-slate-200">v{selectedCitation.document_version || 1}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Published:</span>
                      <span className="text-slate-200">{selectedCitation.published_at || "Recent stream"}</span>
                    </div>
                    {selectedCitation.retrieved_at && (
                      <div className="flex items-center justify-between">
                        <span className="text-slate-500">Ingested:</span>
                        <span className="text-slate-200">{new Date(selectedCitation.retrieved_at).toLocaleString()}</span>
                      </div>
                    )}
                    <div className="break-all font-mono text-[9px] text-slate-500 pt-1">
                      SHA256: {selectedCitation.content_hash}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-xs space-y-1">
                  <div className="flex items-center space-x-1.5 text-cyan-400 font-mono font-bold text-[11px]">
                    <Shield className="w-3.5 h-3.5" />
                    <span>Evidence Provenance</span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-snug">
                    Ground-truth citations referenced by ORACLE in this thread. Click any citation to inspect cryptographic proof, document versions, and excerpt text.
                  </p>
                </div>

                <div className="space-y-2">
                  {allSessionCitations.length === 0 ? (
                    <div className="p-4 text-center text-slate-500 text-xs font-mono">
                      No citations referenced in this conversation yet.
                    </div>
                  ) : (
                    allSessionCitations.map((cite, idx) => (
                      <div
                        key={idx}
                        onClick={() => setSelectedCitation(cite)}
                        className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 hover:border-cyan-500/40 cursor-pointer transition-all space-y-1.5 group"
                      >
                        <div className="flex items-center justify-between text-[10px] font-mono">
                          <span className="text-cyan-400 uppercase font-bold">
                            {cite.publisher || cite.source_type || "Source"}
                          </span>
                          <span className="text-slate-500">
                            {cite.document_version ? `v${cite.document_version}` : "v1"}
                          </span>
                        </div>
                        <h5 className="text-xs font-semibold text-slate-200 group-hover:text-cyan-300 transition-colors line-clamp-1">
                          {cite.title}
                        </h5>
                        <p className="text-[11px] text-slate-400 italic line-clamp-2 leading-relaxed">
                          "{cite.snippet}"
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* New Investigation Modal */}
      {isNewModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="w-full max-w-md rounded-2xl bg-slate-900 border border-slate-800 p-6 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-base font-bold font-mono text-white">Start Investigation</h3>
              <button onClick={() => setIsNewModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateNew} className="space-y-4 text-xs font-mono">
              <div className="space-y-1">
                <label className="text-slate-400">Investigation Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Next.js 15 Server Actions Migration"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-slate-400">Primary Technology / Package</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. nextjs, pydantic, fastapi, langchain"
                  value={newTech}
                  onChange={(e) => setNewTech(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="flex items-center justify-end space-x-2 pt-3">
                <button
                  type="button"
                  onClick={() => setIsNewModalOpen(false)}
                  className="px-4 py-2 rounded-lg text-slate-400 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-cyan-500 text-slate-950 hover:bg-cyan-400 font-bold shadow-glow"
                >
                  Initialize Copilot
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
