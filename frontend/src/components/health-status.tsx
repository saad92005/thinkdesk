"use client";

import { useEffect, useState } from "react";
import { fetchHealth, type HealthResponse } from "@/lib/api";

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "loaded"; data: HealthResponse };

export function HealthStatus() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;

    fetchHealth()
      .then((data) => {
        if (!cancelled) setState({ kind: "loaded", data });
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setState({
            kind: "error",
            message: error instanceof Error ? error.message : "Unknown error",
          });
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (state.kind === "loading") {
    return (
      <p className="text-sm text-neutral-400" role="status">
        Checking backend status…
      </p>
    );
  }

  if (state.kind === "error") {
    return (
      <p className="text-sm text-red-500" role="status">
        Backend unreachable — {state.message}
      </p>
    );
  }

  const { data } = state;
  const dotColor = data.status === "ok" ? "bg-emerald-500" : "bg-amber-500";

  return (
    <div
      className="flex items-center gap-2 rounded-full border border-neutral-200 px-4 py-1.5 text-sm dark:border-neutral-800"
      role="status"
    >
      <span className={`h-2 w-2 rounded-full ${dotColor}`} />
      <span className="text-neutral-600 dark:text-neutral-300">
        API: {data.status} · Database: {data.database}
      </span>
    </div>
  );
}
