// Domain and API types (detailed in P5/P6 from docs/08 §8.4)
export type Decision = "APPROVE" | "REVIEW" | "HOLD" | "REJECT";
export type StageStatus = "PENDING" | "RUNNING" | "PASSED" | "FLAGGED" | "FAILED" | "SKIPPED";
