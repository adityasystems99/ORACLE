import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";
import "./loader/loader.css";
import LoadingGate from "./loader/LoadingGate";
import type { Task } from "./loader/types";

// ---------------------------------------------------------------------------
// Real initialisation tasks — no fake delays, no fake auth.
// Each task fetches from the actual backend; AbortSignal is respected.
// ---------------------------------------------------------------------------

const INIT_TASKS: Task[] = [
  {
    id: "health",
    label: "Verifying system health…",
    run: async (signal) => {
      const res = await fetch("/api/system/health", { signal });
      if (!res.ok) throw new Error(`Health check failed [${res.status}]`);
      await res.json();
    },
  },
  {
    id: "sources",
    label: "Loading intelligence sources…",
    run: async (signal) => {
      const res = await fetch("/api/ingest/sources", { signal });
      if (!res.ok) throw new Error(`Sources failed [${res.status}]`);
      await res.json();
    },
  },
  {
    id: "events",
    label: "Fetching live feed…",
    run: async (signal) => {
      const res = await fetch("/api/events?limit=20", { signal });
      if (!res.ok) throw new Error(`Events failed [${res.status}]`);
      await res.json();
    },
  },
  {
    id: "graph",
    label: "Mapping knowledge graph…",
    run: async (signal) => {
      const res = await fetch("/api/graph/snapshot", { signal });
      if (!res.ok) throw new Error(`Graph failed [${res.status}]`);
      await res.json();
    },
  },
];

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <LoadingGate tasks={INIT_TASKS} minDurationMs={1200} timeoutMs={15000}>
      <App />
    </LoadingGate>
  </React.StrictMode>,
);
