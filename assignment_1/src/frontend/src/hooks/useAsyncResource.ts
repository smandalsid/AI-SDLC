import { useCallback, useEffect, useState } from "react";

export type AsyncResource<T> =
  | { status: "loading"; refresh: () => void }
  | { status: "ready"; data: T; refresh: () => void }
  | { status: "error"; error: unknown; refresh: () => void };

type Outcome<T> = { kind: "ready"; data: T } | { kind: "error"; error: unknown };

interface Settled<T> {
  source: () => Promise<T>;
  outcome: Outcome<T>;
}

/** `load` must be referentially stable (module function or useCallback); a new `load` restarts loading. */
export function useAsyncResource<T>(load: () => Promise<T>): AsyncResource<T> {
  const [settled, setSettled] = useState<Settled<T> | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let cancelled = false;
    load().then(
      (data) => {
        if (!cancelled) setSettled({ source: load, outcome: { kind: "ready", data } });
      },
      (error: unknown) => {
        if (!cancelled) setSettled({ source: load, outcome: { kind: "error", error } });
      },
    );
    return () => {
      cancelled = true;
    };
  }, [load, version]);

  const refresh = useCallback(() => {
    // A retry after an error shows the loading state; a refresh of good data keeps it on screen.
    setSettled((current) => (current?.outcome.kind === "error" ? null : current));
    setVersion((value) => value + 1);
  }, []);

  const outcome = settled !== null && settled.source === load ? settled.outcome : null;
  if (outcome === null) return { status: "loading", refresh };
  if (outcome.kind === "error") return { status: "error", error: outcome.error, refresh };
  return { status: "ready", data: outcome.data, refresh };
}
