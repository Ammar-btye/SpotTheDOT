export type FlagAction = "ACKNOWLEDGE" | "RESOLVE" | "ESCALATE";

export interface FlagDetailData {
  flag: {
    flag_id: number;
    title: string;
    status: string;
    severity: string;
    score: number;
    mission_id: string | null;
    action_id: string | null;
    asset_id: string | null;
    location_id: string | null;
    reasons: { rule: string; detail?: string }[];
  };
  acks: { ack_id: number; action: string; operator: string; note: string | null; created_at: string }[];
}

export interface FlagExplanation {
  answer: string | null;
  reasoning: string | null;
  recommended_action: string | null;
  source: "system2" | "template";
  model?: string | null;
}
