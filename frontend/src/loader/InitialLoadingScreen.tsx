import React, { lazy, Suspense, useState } from "react";
import "./loader.css";
import GlowPillButton from "./GlowPillButton";
import type { Phase, Task } from "./types";

// Lazy-load the canvas globe (Canvas 2D only; no Three.js)
const GlobeCanvas = lazy(() => import("./GlobeCanvas"));

const AccentDot: React.FC = () => (
  <svg width="8" height="8" viewBox="0 0 8 8" fill="none" aria-hidden="true">
    <circle cx="4" cy="4" r="4" fill="#d97757" />
  </svg>
);

export interface InitialLoadingScreenProps {
  tasks: Task[];
  completedIds: Set<string>;
  currentLabel: string;
  errorMsg: string | null;
  phase: Phase;
  onEnter: () => void;
  onRetry: () => void;
  retryButtonRef: React.RefObject<HTMLButtonElement>;
}

const InitialLoadingScreen: React.FC<InitialLoadingScreenProps> = ({
  tasks,
  completedIds,
  currentLabel,
  errorMsg,
  phase,
  onEnter,
  onRetry,
  retryButtonRef,
}) => {
  const [globeUnsupported, setGlobeUnsupported] = useState(false);
  const isReady = phase === "ready";

  return (
    <section
      className="loader-root"
      aria-label="ORACLE initializing"
      aria-live="polite"
    >
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header className="loader-header">
        <div className="loader-brand">
          <AccentDot />
          <span className="loader-brand-name">ORACLE</span>
        </div>
        <span className="loader-counter" aria-hidden="true">
          {completedIds.size}/{tasks.length}
        </span>
      </header>

      {/* ── Center ─────────────────────────────────────────────────────── */}
      <div className="loader-center">
        {/* Globe */}
        <div className="loader-globe-wrap" aria-hidden="true">
          {globeUnsupported ? (
            <div className="loader-globe-fallback" />
          ) : (
            <Suspense fallback={<div className="loader-globe-fallback" />}>
              <GlobeCanvas onUnsupported={() => setGlobeUnsupported(true)} />
            </Suspense>
          )}
        </div>

        {/* Status message */}
        {errorMsg ? (
          <p className="loader-error" role="alert">
            {errorMsg}
          </p>
        ) : (
          <p className="loader-status">
            {isReady ? "Systems nominal" : currentLabel || "Initialising…"}
          </p>
        )}

        {/* Segmented progress bar */}
        <div
          className="loader-progress"
          role="progressbar"
          aria-valuenow={completedIds.size}
          aria-valuemin={0}
          aria-valuemax={tasks.length}
          aria-label="Initialisation progress"
        >
          {tasks.map((t) => {
            const done = completedIds.has(t.id);
            return (
              <div
                key={t.id}
                className={`loader-progress-seg${done ? " loader-progress-seg--done" : ""}`}
              >
                <div className="loader-progress-seg-fill" />
              </div>
            );
          })}
        </div>

        {/* CTA */}
        {errorMsg ? (
          <button
            ref={retryButtonRef}
            className="glow-pill"
            onClick={onRetry}
            type="button"
            style={{ marginTop: 4 }}
          >
            <span className="glow-pill__disc">
              <span className="glow-ring" aria-hidden="true" />
              <span className="glow-pill__arrow">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                  <path
                    d="M2 7a5 5 0 1 1 2.3 4.2M2 7V3m0 4H6"
                    stroke="rgba(255,255,255,0.75)"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </span>
            </span>
            <span className="glow-pill__label">Retry</span>
          </button>
        ) : (
          <GlowPillButton
            label={isReady ? "Enter ORACLE" : "Initialising…"}
            disabled={!isReady}
            onClick={onEnter}
          />
        )}
      </div>

      {/* ── Footer ─────────────────────────────────────────────────────── */}
      <footer className="loader-footer" aria-hidden="true">
        Live Intelligence Copilot · v0.1.0
      </footer>
    </section>
  );
};

export default InitialLoadingScreen;
