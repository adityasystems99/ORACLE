import React, { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  Bot,
  Check,
  ChevronRight,
  Copy,
  ExternalLink,
  MessageSquare,
  Paperclip,
  Plus,
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
}

export const InvestigationCopilot: React.FC<InvestigationCopilotProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onCreateSession,
  onExploreBlastRadius,
}) => {
  const currentSession = sessions.find((s) => s.id === activeSessionId) || sessions[0] || null;

  const [inputPrompt, setInputPrompt] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamedText, setStreamedText] = useState("");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<EvidenceRef | null>(null);
  const [isInspectorOpen, setIsInspectorOpen] = useState(true);

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
    setIsStreaming(true);
    setStreamedText("");

    try {
      await api.sendInvestigationMessage(currentSession.id, text, (token) => {
        setStreamedText((prev) => prev + token);
      });
    } catch (e: any) {
      console.error("Failed to stream copilot response:", e);
    } finally {
      setIsStreaming(false);
      setStreamedText("");
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
                <span className="hidden sm:inline">Evidence</span>
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
                          className="flex items-center space-x-1 px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-[10px] font-mono text-cyan-400 hover:border-cyan-500 transition-colors"
                        >
                          <Shield className="w-3 h-3 text-cyan-400" />
                          <span className="truncate max-w-[150px]">{cite.title}</span>
                        </button>
                      ))}
                    </div>
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
                  {streamedText || "Analyzing knowledge graph..."}
                  <span className="inline-block w-1.5 h-3.5 bg-cyan-400 animate-pulse ml-1" />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

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
              <div className="p-3.5 rounded-xl bg-slate-950/80 border border-cyan-500/40 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800">
                    {selectedCitation.source_type}
                  </span>
                  <a
                    href={selectedCitation.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center space-x-1 text-cyan-400 hover:text-cyan-300 text-xs font-mono"
                  >
                    <span>URL</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>

                <h4 className="text-xs font-bold text-white">{selectedCitation.title}</h4>
                <p className="text-xs text-slate-300 italic bg-slate-900/80 p-2.5 rounded border border-slate-800 font-mono">
                  "{selectedCitation.snippet}"
                </p>

                <div className="space-y-1 text-[10px] font-mono text-slate-500 pt-2 border-t border-slate-800">
                  <div>Published: {selectedCitation.published_at || "Recent stream"}</div>
                  <div className="break-all">Hash: {selectedCitation.content_hash}</div>
                </div>
              </div>
            ) : (
              <div className="p-4 text-center text-slate-500 text-xs">
                Click any citation badge in the copilot conversation to inspect cryptographic proof and raw snippets.
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
