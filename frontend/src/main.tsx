import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { api } from "./api/client";
import "./index.css";
import "./loader/loader.css";
import LoadingGate from "./loader/LoadingGate";
import type { Task } from "./loader/types";

// Real initialization tasks with automatic live/mock detection
const INIT_TASKS: Task[] = [
  {
    id: "pipeline",
    label: "Checking intelligence pipeline connection…",
    run: async () => {
      await api.probeBackend();
    },
  },
  {
    id: "telemetry",
    label: "Verifying system telemetry…",
    run: async () => {
      await api.getHealth();
    },
  },
  {
    id: "sources",
    label: "Loading intelligence sources…",
    run: async () => {
      await api.getSources();
    },
  },
  {
    id: "events",
    label: "Fetching live signals & events…",
    run: async () => {
      await api.getEvents({ limit: 20 });
    },
  },
  {
    id: "graph",
    label: "Mapping temporal knowledge graph…",
    run: async () => {
      await api.getGraphSnapshot();
    },
  },
];

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <LoadingGate tasks={INIT_TASKS} minDurationMs={1000} timeoutMs={10000}>
      <App />
    </LoadingGate>
  </React.StrictMode>
);
