import { useEffect, useRef, useState, useCallback } from "react";
import { api } from "./api";
import type { Check, RunDetail, StageKey } from "./types";

export interface LogEntry {
  id: number;
  time: string;
  type: string;
  stageKey?: string;
  status?: string;
  durationMs?: number;
  message?: string;
}

export function useRunStream(runId: string | undefined) {
  const [run, setRun] = useState<RunDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [liveEventLog, setLiveEventLog] = useState<LogEntry[]>([]);
  const [elapsedMs, setElapsedMs] = useState(0);

  const eventSourceRef = useRef<EventSource | null>(null);
  const stageStartTimeRef = useRef<Record<string, number>>({});
  const timerIntervalRef = useRef<any>(null);
  const queueTimeoutRef = useRef<any>(null);
  const errorCountRef = useRef(0);

  // Initial fetch
  const fetchRun = useCallback(async () => {
    if (!runId) return;
    try {
      const data = await api.getRun(runId);
      setRun(data);
      if (data.duration_ms) {
        setElapsedMs(data.duration_ms);
      }
      setIsLoading(false);
      return data;
    } catch (err: any) {
      setError(err.message || "Failed to load run");
      setIsLoading(false);
      return null;
    }
  }, [runId]);

  useEffect(() => {
    let isMounted = true;

    async function init() {
      const initialRun = await fetchRun();
      if (!initialRun || !isMounted) return;

      // If already finished, no need to connect SSE
      if (initialRun.status === "COMPLETED" || initialRun.status === "FAILED") {
        return;
      }

      // Start elapsed timer
      const startTime = initialRun.created_at
        ? new Date(initialRun.created_at).getTime()
        : Date.now();

      timerIntervalRef.current = setInterval(() => {
        setElapsedMs(Date.now() - startTime);
      }, 100);

      // Connect to SSE
      const apiBase =
        import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || "";
      const sseUrl = `${apiBase}/api/runs/${runId}/events`;
      const es = new EventSource(sseUrl);
      eventSourceRef.current = es;

      const formatNow = () => {
        const d = new Date();
        return (
          d.toTimeString().split(" ")[0] +
          "." +
          String(d.getMilliseconds()).padStart(3, "0")
        );
      };

      const handleEvent = (event: MessageEvent, type: string) => {
        if (!isMounted) return;
        let data: any = {};
        try {
          data = JSON.parse(event.data);
        } catch {
          data = {};
        }

        const seq = event.lastEventId ? parseInt(event.lastEventId, 10) : Date.now();

        // 1. Stage Started
        if (type === "stage.started") {
          const { stage_key } = data;
          stageStartTimeRef.current[stage_key] = Date.now();

          setRun((prev) => {
            if (!prev) return prev;
            const updatedStages = prev.stages.map((st) =>
              st.stage_key === stage_key
                ? { ...st, status: "RUNNING" as const, started_at: new Date().toISOString() }
                : st
            );
            return {
              ...prev,
              status: "RUNNING",
              current_stage: stage_key,
              stages: updatedStages,
            };
          });

          setLiveEventLog((prev) => [
            ...prev,
            {
              id: seq,
              time: formatNow(),
              type: "stage.started",
              stageKey: stage_key,
            },
          ]);
        }

        // 2. Check Result
        else if (type === "check.result") {
          const { stage_key, check_id, name, outcome, severity, message, evidence } = data;
          const newCheck: Check = {
            stage_key: stage_key as StageKey,
            check_id,
            name,
            outcome,
            severity,
            message,
            evidence: evidence || {},
          };

          setRun((prev) => {
            if (!prev) return prev;
            const updatedStages = prev.stages.map((st) => {
              if (st.stage_key !== stage_key) return st;
              const exists = st.checks.some((c) => c.check_id === check_id);
              return {
                ...st,
                checks: exists ? st.checks : [...st.checks, newCheck],
              };
            });
            return { ...prev, stages: updatedStages };
          });
        }

        // 3. Stage Completed (with 300ms pacing)
        else if (type === "stage.completed") {
          const { stage_key, status, summary, duration_ms, output } = data;
          const startedAt = stageStartTimeRef.current[stage_key] || Date.now();
          const elapsed = Date.now() - startedAt;
          const pacingDelay = Math.max(0, 300 - elapsed);

          queueTimeoutRef.current = setTimeout(() => {
            if (!isMounted) return;
            setRun((prev) => {
              if (!prev) return prev;
              const updatedStages = prev.stages.map((st) =>
                st.stage_key === stage_key
                  ? {
                      ...st,
                      status,
                      summary,
                      duration_ms,
                      output,
                      completed_at: new Date().toISOString(),
                    }
                  : st
              );
              return { ...prev, stages: updatedStages };
            });

            setLiveEventLog((prev) => [
              ...prev,
              {
                id: seq,
                time: formatNow(),
                type: "stage.completed",
                stageKey: stage_key,
                status,
                durationMs: duration_ms,
              },
            ]);
          }, pacingDelay);
        }

        // 4. Run Completed
        else if (type === "run.completed") {
          const { decision, headline, duration_ms } = data;

          if (timerIntervalRef.current) {
            clearInterval(timerIntervalRef.current);
          }
          if (duration_ms) {
            setElapsedMs(duration_ms);
          }

          setLiveEventLog((prev) => [
            ...prev,
            {
              id: seq,
              time: formatNow(),
              type: "run.completed",
              status: decision,
              durationMs: duration_ms,
              message: headline,
            },
          ]);

          // Fetch fresh full detail once completed
          setTimeout(() => {
            if (isMounted) {
              fetchRun();
              if (eventSourceRef.current) {
                eventSourceRef.current.close();
              }
            }
          }, 350);
        }

        // 5. Run Failed
        else if (type === "run.failed") {
          const { message } = data;
          if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);

          setRun((prev) => (prev ? { ...prev, status: "FAILED" } : prev));
          setLiveEventLog((prev) => [
            ...prev,
            { id: seq, time: formatNow(), type: "run.failed", message },
          ]);
          if (eventSourceRef.current) eventSourceRef.current.close();
        }

        // 6. Run Reviewed
        else if (type === "run.reviewed") {
          const { review_status, reviewer, note, reviewed_at } = data;
          setRun((prev) =>
            prev
              ? {
                  ...prev,
                  review_status,
                  reviewer,
                  review_note: note,
                  reviewed_at,
                }
              : prev
          );
        }
      };

      // Listen for named events
      [
        "run.started",
        "stage.started",
        "check.result",
        "stage.completed",
        "run.completed",
        "run.failed",
        "run.reviewed",
      ].forEach((evType) => {
        es.addEventListener(evType, (e) => handleEvent(e as MessageEvent, evType));
      });

      es.onerror = () => {
        errorCountRef.current += 1;
        if (errorCountRef.current >= 2) {
          es.close();
          // Fall back to polling
          const pollInterval = setInterval(async () => {
            const latest = await fetchRun();
            if (latest?.status === "COMPLETED" || latest?.status === "FAILED") {
              clearInterval(pollInterval);
            }
          }, 1000);
        }
      };
    }

    init();

    return () => {
      isMounted = false;
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
      if (queueTimeoutRef.current) clearTimeout(queueTimeoutRef.current);
      if (eventSourceRef.current) eventSourceRef.current.close();
    };
  }, [runId, fetchRun]);

  return {
    run,
    isLoading,
    error,
    liveEventLog,
    elapsedMs,
    refetch: fetchRun,
  };
}
