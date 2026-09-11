/**
 * Shared domain types mirroring the backend schemas
 * (backend/app/agents/schemas.py + API response shapes).
 */

export interface PricingTier {
  name: string;
  price: string;
  limitations: string[];
  source_url: string;
}

export interface ChurnDriver {
  pain_point: string;
  exact_quote: string;
  source_platform: string;
  source_url: string;
  objection_rebuttal: string;
}

export interface SWOTAnalysis {
  strengths: string[];
  weaknesses: string[];
  opportunities: string[];
  threats: string[];
}

export interface BattlecardOutput {
  executive_summary: string;
  swot: SWOTAnalysis;
  pricing: PricingTier[];
  churn_drivers: ChurnDriver[];
  landmine_questions: string[];
}

export interface BattlecardRecord {
  id: string;
  job_id: string;
  user_id: string;
  target_company: string;
  competitor: string;
  report_data: BattlecardOutput;
  created_at: string;
}

export interface AppUser {
  id?: string;
  name?: string | null;
  email?: string | null;
  image?: string | null;
}

/** Steps emitted by the agent graph (SPEC.md §6). */
export type AgentStep = "planning" | "retrieving" | "verifying" | "synthesizing";

export interface ProgressEventPayload {
  step: string;
  message: string;
  msg?: string;
  data?: unknown;
}

export const AGENT_STEP_ORDER: AgentStep[] = [
  "planning",
  "retrieving",
  "verifying",
  "synthesizing",
];

export const STEP_LABELS: Record<AgentStep, string> = {
  planning: "Planning",
  retrieving: "Scraping",
  verifying: "Verifying Sources",
  synthesizing: "Synthesizing",
};