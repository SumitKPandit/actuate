export type VendorSort = 'ota' | 'cost' | 'alerts' | 'csat';

export interface OverviewData {
  trips: number | null;
  ota_pct: number | null;
  avg_delay_min: number | null;
  delay_reason_mix: Record<string, { count: number | null; share: number | null }> | null;
  no_show_rate: number | null;
  cost_per_trip: number | null;
  cost_per_km: number | null;
  zero_km_share: number | null;
  alert_rate_per_1k: number | null;
  sev1_count: number | null;
  ack_sla_met_share: number | null;
  csat_avg: number | null;
  low_rating_share: number | null;
  benchmarks: { ota_sla: number; ack_sla_min: number } | null;
}

export interface InsightSchema {
  id: string;
  kpi: string;
  scope: Record<string, unknown>;
  current: number | null;
  baseline: number | null;
  delta_pp: number | null;
  contribution_share: number | null;
  severity: string;
  reach_trips: number;
  reason: string;
  recommended_action: string;
  owner: string;
}

export interface ActionItem {
  id: string;
  action: string;
  owner: string;
  due_hint: string;
  copy_for_vendor: string;
  status: string;
}

export interface BriefingData {
  generated_at: string;
  headline_facts: string[];
  insights_top5: InsightSchema[];
  safety_open_sev1: number;
  actions_top3: ActionItem[];
  triggers?: unknown[];
  narrative?: string | null;
}

export interface AskScope {
  vendor?: string | null;
  office?: string | null;
}

export interface GroundedFrom {
  marts: string[];
  cycle: string;
}

export interface AskResponse {
  sql: string;
  rows: Record<string, unknown>[];
  narrative: string;
  grounded_from: GroundedFrom;
}

export interface VendorRow {
  vendor: string;
  trips: number | null;
  ota_pct: number | null;
  cost_per_trip: number | null;
  cost_per_km: number | null;
  alert_rate_per_1k: number | null;
  csat_avg: number | null;
  low_rating_share: number | null;
  peer_rank: number | null;
  contribution_share: number | null;
  zero_km_count: number | null;
  unslabbed_count: number | null;
}

export interface AckRequest {
  actor: string;
}

export interface AckResponse {
  id: string;
  status: string;
  actor: string;
  acked_at: string;
}

export interface Envelope<T> {
  data: T | null;
  warning: string | null;
}

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, body: unknown) {
    const detail = (body as { detail?: unknown } | null)?.detail;
    super(typeof detail === 'string' ? detail : `HTTP ${status}`);
    this.name = 'ApiError';
    this.status = status;
    this.body = body;
  }
}

function apiBase(): string {
  const base: string | undefined = import.meta.env.VITE_API_URL;
  if (!base) throw new Error('Set VITE_API_URL in frontend/.env');
  return base;
}

async function parseBody(res: Response): Promise<unknown> {
  const text = await res.text();
  try {
    return JSON.parse(text);
  } catch {
    return { raw: text };
  }
}

function withQuery(path: string, params: Record<string, string>): string {
  const qs = new URLSearchParams(params).toString();
  return `${path}?${qs}`;
}

async function request<T>(path: string): Promise<Envelope<T>> {
  const res = await fetch(`${apiBase()}${path}`);
  if (!res.ok) throw new ApiError(res.status, await parseBody(res));
  return JSON.parse(await res.text()) as Envelope<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${apiBase()}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ApiError(res.status, await parseBody(res));
  return JSON.parse(await res.text()) as T;
}

export function getOverview(cycle: string): Promise<Envelope<OverviewData>> {
  return request(withQuery('/overview', { cycle }));
}

export function getBriefing(cycle: string): Promise<Envelope<BriefingData>> {
  return request(withQuery('/briefing', { cycle }));
}

export function getInsights(cycle: string): Promise<Envelope<InsightSchema[]>> {
  return request(withQuery('/insights', { cycle }));
}

export function getActions(cycle: string): Promise<Envelope<ActionItem[]>> {
  return request(withQuery('/actions', { cycle }));
}

export function getVendors(cycle: string, sort: VendorSort = 'ota'): Promise<Envelope<VendorRow[]>> {
  return request(withQuery('/vendors', { cycle, sort }));
}

export function ask(question: string, cycle: string, scope?: AskScope): Promise<AskResponse> {
  const body: { question: string; cycle: string; scope?: AskScope } = { question, cycle };
  if (scope !== undefined) body.scope = scope;
  return post<AskResponse>('/ask', body);
}

export async function ackAction(id: string, actor: string): Promise<AckResponse> {
  const res = await fetch(`${apiBase()}/actions/${encodeURIComponent(id)}/ack`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ actor } satisfies AckRequest),
  });
  if (!res.ok) throw new ApiError(res.status, await parseBody(res));
  return JSON.parse(await res.text()) as AckResponse;
}
