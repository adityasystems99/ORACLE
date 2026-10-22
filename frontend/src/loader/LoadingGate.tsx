import React, {
  useCallback,
  useEffect,
  useReducer,
  useRef,
  useState,
} from "react";
import InitialLoadingScreen from "./InitialLoadingScreen";
import type { Phase, Task } from "./types";

export type { Task, Phase };

interface LoadingGateProps {
  tasks: Task[];
  children: React.ReactNode;
  minDurationMs?: number;
  timeoutMs?: number;
}

interface State {
  phase: Phase;
  completedIds: Set<string>;
  currentLabel: string;
  errorMsg: string | null;
}

type Action =
  | { type: "TASK_DONE"; id: string; nextLabel: string }
  | { type: "ALL_DONE" }
  | { type: "ERROR"; msg: string }
  | { type: "RETRY" }
  | { type: "EXIT" }
  | { type: "COMPLETE" };

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "TASK_DONE":
      return {
        ...state,
        completedIds: new Set([...state.completedIds, action.id]),
        currentLabel: action.nextLabel,
      };
    case "ALL_DONE":
      return { ...state, phase: "ready", errorMsg: null };
    case "ERROR":
      return { ...state, phase: "loading", errorMsg: action.msg };
    case "RETRY":
      return {
        phase: "loading",
        completedIds: new Set(),
        currentLabel: "",
        errorMsg: null,
      };
    case "EXIT":
      return { ...state, phase: "exiting" };
    case "COMPLETE":
      return { ...state, phase: "done" };
    default:
      return state;
  }
}

const LoadingGate: React.FC<LoadingGateProps> = ({
  tasks,
  children,
  minDurationMs = 900,
  timeoutMs = 12000,
}) => {
  const [state, dispatch] = useReducer(reducer, {
    phase: "loading" as Phase,
    completedIds: new Set<string>(),
    currentLabel: tasks[0]?.label ?? "Initialising…",
    errorMsg: null,
  });

  const [runKey, setRunKey] = useState(0);

  const abortRef = useRef<AbortController | null>(null);
  const startTimeRef = useRef(performance.now());
  const enterClicked = useRef(false);
  const retryButtonRef = useRef<HTMLButtonElement>(null);

  const runTasks = useCallback(async () => {
    if (abortRef.current) abortRef.current.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    startTimeRef.current = performance.now();
    enterClicked.current = false;

    const timeoutId = setTimeout(() => {
      ctrl.abort();
      dispatch({
        type: "ERROR",
        msg: "Initialisation timed out. Check your connection.",
      });
    }, timeoutMs);

    try {
      for (let i = 0; i < tasks.length; i++) {
        const task = tasks[i];
        if (ctrl.signal.aborted) throw new DOMException("Aborted", "AbortError");
        await task.run(ctrl.signal);
        const nextLabel = tasks[i + 1]?.label ?? "";
        dispatch({ type: "TASK_DONE", id: task.id, nextLabel });
      }
      clearTimeout(timeoutId);
      if (!ctrl.signal.aborted) dispatch({ type: "ALL_DONE" });
    } catch (err) {
      clearTimeout(timeoutId);
      if (ctrl.signal.aborted) return;
      const msg =
        err instanceof Error ? err.message : "An unexpected error occurred.";
      dispatch({ type: "ERROR", msg });
    }
  }, [tasks, timeoutMs]);

  // Run tasks whenever runKey changes (initial mount + retry)
  useEffect(() => {
    runTasks();
    return () => {
      abortRef.current?.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runKey]);

  // Honour minimum display duration
  useEffect(() => {
    if (state.phase !== "ready") return;
    if (enterClicked.current) {
      dispatch({ type: "EXIT" });
      return;
    }
    const elapsed = performance.now() - startTimeRef.current;
    const remaining = Math.max(0, minDurationMs - elapsed);
    const id = setTimeout(() => {
      if (!enterClicked.current) dispatch({ type: "EXIT" });
    }, remaining);
    return () => clearTimeout(id);
  }, [state.phase, minDurationMs]);

  // Fade duration then unmount
  useEffect(() => {
    if (state.phase !== "exiting") return;
    const id = setTimeout(() => dispatch({ type: "COMPLETE" }), 800);
    return () => clearTimeout(id);
  }, [state.phase]);

  // Move focus to retry button when an error appears
  useEffect(() => {
    if (state.errorMsg && retryButtonRef.current) {
      retryButtonRef.current.focus();
    }
  }, [state.errorMsg]);

  const handleEnter = useCallback(() => {
    enterClicked.current = true;
    dispatch({ type: "EXIT" });
  }, []);

  const handleRetry = useCallback(() => {
    dispatch({ type: "RETRY" });
    setRunKey((k) => k + 1);
  }, []);

  if (state.phase === "done") {
    return <>{children}</>;
  }

  return (
    <>
      {/* Mount children beneath the loader during fade-out for instant swap */}
      {state.phase === "exiting" && <>{children}</>}

      <div
        style={{ position: "fixed", inset: 0, zIndex: 9999 }}
        className={
          state.phase === "exiting" ? "loader-fade-exit" : "loader-fade-enter"
        }
      >
        <InitialLoadingScreen
          tasks={tasks}
          completedIds={state.completedIds}
          currentLabel={state.currentLabel}
          errorMsg={state.errorMsg}
          phase={state.phase}
          onEnter={handleEnter}
          onRetry={handleRetry}
          retryButtonRef={retryButtonRef}
        />
      </div>
    </>
  );
};

export default LoadingGate;
