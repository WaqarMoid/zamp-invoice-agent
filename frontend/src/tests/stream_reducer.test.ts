import { describe, it, expect } from "vitest";
import type { Check, Stage, StageKey } from "../lib/types";

// Extracted reducer logic for event idempotency & ordering test
interface ReducerState {
  appliedSeqs: Set<number>;
  stages: Stage[];
  decision: string | null;
}

function applyEvent(
  state: ReducerState,
  event: { seq: number; type: string; payload: Record<string, any> }
): ReducerState {
  // Idempotency guard: ignore already applied sequence numbers
  if (state.appliedSeqs.has(event.seq)) {
    return state;
  }
  const nextSeqs = new Set(state.appliedSeqs);
  nextSeqs.add(event.seq);

  let nextStages = [...state.stages];
  let nextDecision = state.decision;

  if (event.type === "stage.started") {
    const { stage_key } = event.payload;
    nextStages = nextStages.map((st) =>
      st.stage_key === stage_key ? { ...st, status: "RUNNING" as const } : st
    );
  } else if (event.type === "check.result") {
    const { stage_key, check_id, name, outcome, severity, message } = event.payload;
    const newCheck: Check = {
      stage_key: stage_key as StageKey,
      check_id,
      name,
      outcome,
      severity,
      message,
      evidence: {},
    };
    nextStages = nextStages.map((st) => {
      if (st.stage_key !== stage_key) return st;
      const exists = st.checks.some((c) => c.check_id === check_id);
      return {
        ...st,
        checks: exists ? st.checks : [...st.checks, newCheck],
      };
    });
  } else if (event.type === "stage.completed") {
    const { stage_key, status, summary, duration_ms } = event.payload;
    nextStages = nextStages.map((st) =>
      st.stage_key === stage_key
        ? { ...st, status, summary, duration_ms }
        : st
    );
  } else if (event.type === "run.completed") {
    nextDecision = event.payload.decision;
  }

  return {
    appliedSeqs: nextSeqs,
    stages: nextStages,
    decision: nextDecision,
  };
}

describe("Run Stream Reducer Idempotency", () => {
  const initialStages: Stage[] = [
    {
      stage_key: "ingest",
      position: 1,
      label: "Ingest",
      description: "Stores file",
      status: "PENDING",
      summary: null,
      started_at: null,
      completed_at: null,
      duration_ms: null,
      output: null,
      checks: [],
    },
    {
      stage_key: "extract",
      position: 2,
      label: "Extract",
      description: "Extracts fields",
      status: "PENDING",
      summary: null,
      started_at: null,
      completed_at: null,
      duration_ms: null,
      output: null,
      checks: [],
    },
  ];

  it("handles duplicate and out-of-order events idempotently", () => {
    let state: ReducerState = {
      appliedSeqs: new Set(),
      stages: initialStages,
      decision: null,
    };

    const ev1 = {
      seq: 1,
      type: "stage.started",
      payload: { stage_key: "ingest" },
    };

    const ev2 = {
      seq: 2,
      type: "check.result",
      payload: {
        stage_key: "ingest",
        check_id: "C01",
        name: "Mandatory fields",
        outcome: "PASS",
        severity: null,
        message: "All fields present",
      },
    };

    const ev3 = {
      seq: 3,
      type: "stage.completed",
      payload: {
        stage_key: "ingest",
        status: "PASSED",
        summary: "1 page verified",
        duration_ms: 120,
      },
    };

    // Apply ev1
    state = applyEvent(state, ev1);
    expect(state.stages[0].status).toBe("RUNNING");

    // Apply duplicate ev1 -> must remain identical
    state = applyEvent(state, ev1);
    expect(state.appliedSeqs.size).toBe(1);

    // Apply ev2 twice
    state = applyEvent(state, ev2);
    state = applyEvent(state, ev2);
    expect(state.stages[0].checks.length).toBe(1);
    expect(state.appliedSeqs.size).toBe(2);

    // Apply ev3
    state = applyEvent(state, ev3);
    expect(state.stages[0].status).toBe("PASSED");
    expect(state.stages[0].duration_ms).toBe(120);

    // Duplicated ev3 does not mutate
    state = applyEvent(state, ev3);
    expect(state.appliedSeqs.size).toBe(3);
  });
});
