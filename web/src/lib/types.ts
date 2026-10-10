// ─────────────────────────────────────────────────────────────────────────────
// The shapes the dashboard renders.
//
// Deliberately free of imports: a Client Component can take these types
// without dragging the loader — and `node:fs` with it — into the browser
// bundle. The data that fills them is computed in @/lib/analysis.
//
// These mirror the columns in db/schema.sql (`flags`, `insights`), so the same
// shapes survive the move from CSV to Neon.
// ─────────────────────────────────────────────────────────────────────────────

export type Severity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

/** One rule that fired, and what it contributed to the score. */
export interface Reason {
  /** Stable rule id, e.g. "status.mismatch". Lets a flag be audited. */
  rule: string;
  /** The operator-readable sentence. */
  detail: string;
  /** Points this rule added — the score is the sum, nothing hidden. */
  weight: number;
}

export interface Flag {
  id: string;
  missionId: string;
  severity: Severity;
  /** 0–100 priority. */
  score: number;
  title: string;
  assetName: string;
  locationName: string;
  reasons: Reason[];
}

export interface Stat {
  label: string;
  value: string;
  unit?: string;
  note: string;
}

export interface BatteryBand {
  band: string;
  successRate: number;
  sampleSize: number;
}
