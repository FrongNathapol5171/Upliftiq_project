// API client for the UpliftIQ FastAPI serve plane.
const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export type PolicyResult = { incremental_conversions: number; incremental_profit: number };
export type Point = { x: number; y: number };
export type SweepPoint = { budget: number; uplift: number; propensity: number; random: number };
export type Segments = Record<string, number>;

export interface SimulateResponse {
  budget: number;
  population: number;
  cost_per_contact: number;
  value_per_conversion: number;
  uplift: PolicyResult;
  propensity: PolicyResult;
  random: PolicyResult;
  profit_lift_vs_propensity: number;
  profit_lift_vs_random: number;
  selected_segments: Segments;
  total_segments: Segments;
  qini_points: Point[];
  uplift_points: Point[];
  profit_sweep: SweepPoint[];
}

export interface HealthResponse {
  status: string;
  datasets: string[];
  supabase: boolean;
  gemini: boolean;
}

async function jpost<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${path} → ${r.status}: ${await r.text()}`);
  return r.json();
}

export const api = {
  base: BASE,
  health: () => fetch(`${BASE}/api/health`).then((r) => r.json() as Promise<HealthResponse>),
  datasets: () => fetch(`${BASE}/api/datasets`).then((r) => r.json()),
  metrics: (dataset: string) =>
    fetch(`${BASE}/api/metrics?dataset=${dataset}`).then((r) => r.json()),
  simulate: (body: { budget: number; cost: number; value: number; dataset: string }) =>
    jpost<SimulateResponse>("/api/simulate", body),
  explain: (body: { segment: string; dataset: string }) =>
    jpost<{ text: string; source: string }>("/api/explain", body),
  batchUrl: (dataset: string) => `${BASE}/api/batch?dataset=${dataset}`,
};
