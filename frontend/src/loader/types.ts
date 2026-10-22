// Shared types for the loader subsystem — no DOM, no React.

export interface Task {
  id: string;
  label: string;
  run: (signal: AbortSignal) => Promise<void>;
}

export type Phase = "loading" | "ready" | "exiting" | "done";
