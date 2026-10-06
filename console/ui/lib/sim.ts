// Client-side helpers for talking to the simulator through the /api/sim proxy.

export async function sim<T = any>(path: string, init?: RequestInit & { json?: unknown }): Promise<T> {
  const { json, ...rest } = init ?? {};
  const res = await fetch(`/api/sim${path}`, {
    ...rest,
    method: rest.method ?? (json !== undefined ? "POST" : "GET"),
    headers: { "content-type": "application/json" },
    body: json !== undefined ? JSON.stringify(json) : rest.body,
    cache: "no-store",
  });
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) throw new Error(data?.detail ? String(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail)) : `${res.status}`);
  return data as T;
}

export type CheckResult = {
  id: string;
  section: string;
  title: string;
  points: number;
  status: "pass" | "fail" | "blocked" | "error";
  detail: string;
  hint: string;
  seconds: number;
};

export type RunSummary2 = {
  booking_total: number; booking_passed: number; booking_pct: number | null;
  safety_total: number; safety_failures: number; bar: string;
};

export type Run = {
  lab: string;
  title: string;
  run_id: string;
  finished_at: string;
  learner_url: string;
  score: number;
  total: number;
  passed: number;
  count: number;
  summary?: RunSummary2;
  results: CheckResult[];
};

export type RunSummary = Pick<Run, "run_id" | "finished_at" | "score" | "total" | "passed" | "count">;
