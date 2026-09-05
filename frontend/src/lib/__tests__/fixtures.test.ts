import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

const ROOT = resolve(import.meta.dirname, '../../../..');

const OVERVIEW_KEYS = [
  'trips',
  'ota_pct',
  'avg_delay_min',
  'delay_reason_mix',
  'no_show_rate',
  'cost_per_trip',
  'cost_per_km',
  'zero_km_share',
  'alert_rate_per_1k',
  'sev1_count',
  'ack_sla_met_share',
  'csat_avg',
  'low_rating_share',
  'benchmarks',
] as const;

const VENDOR_KEYS = [
  'vendor',
  'trips',
  'ota_pct',
  'cost_per_trip',
  'cost_per_km',
  'alert_rate_per_1k',
  'csat_avg',
  'low_rating_share',
  'peer_rank',
  'contribution_share',
  'zero_km_count',
  'unslabbed_count',
] as const;

const INSIGHT_KEYS = [
  'id',
  'kpi',
  'scope',
  'current',
  'baseline',
  'delta_pp',
  'severity',
  'reach_trips',
  'contribution_share',
  'reason',
  'recommended_action',
  'owner',
] as const;

type Envelope = { data: unknown; warning: unknown };

function load(rel: string): Envelope {
  return JSON.parse(readFileSync(resolve(ROOT, rel), 'utf8'));
}

function expectEnvelope(env: Envelope): asserts env is { data: Record<string, unknown>; warning: string | null } {
  expect(env).toHaveProperty('data');
  expect(env).toHaveProperty('warning');
  expect(env.warning === null || typeof env.warning === 'string').toBe(true);
  expect(env.data).not.toBeNull();
}

describe('fixture snapshots (real API responses)', () => {
  const paths = {
    overview: 'stories/06-dashboard-ui/sample-overview.json',
    briefing: 'stories/05-brief-ui/sample-briefing.json',
    vendors: 'stories/06-dashboard-ui/sample-vendors.json',
    insights: 'stories/06-dashboard-ui/sample-insights.json',
  };

  it('overview: envelope + all 14 OverviewData keys + benchmarks', () => {
    const env = load(paths.overview);
    expectEnvelope(env);
    for (const key of OVERVIEW_KEYS) expect(env.data, key).toHaveProperty(key);
    expect(env.data.benchmarks).toMatchObject({ ota_sla: expect.any(Number), ack_sla_min: expect.any(Number) });
  });

  it('briefing: envelope + facts ≥3 + top5 shape + actions ≤500 chars', () => {
    const env = load(paths.briefing);
    expectEnvelope(env);
    expect(typeof env.data.generated_at).toBe('string');
    expect((env.data.headline_facts as string[]).length).toBeGreaterThanOrEqual(3);
    const top5 = env.data.insights_top5 as Record<string, unknown>[];
    expect(top5.length).toBeLessThanOrEqual(5);
    for (const ins of top5) {
      for (const key of ['id', 'kpi', 'scope', 'severity', 'reach_trips']) {
        expect(ins, key).toHaveProperty(key);
      }
    }
    expect(typeof env.data.safety_open_sev1).toBe('number');
    for (const action of env.data.actions_top3 as Record<string, unknown>[]) {
      expect(String(action.copy_for_vendor).length).toBeLessThanOrEqual(500);
    }
  });

  it('vendors: non-empty, every row has vendor + peer_rank ≥1 + 12 keys', () => {
    const env = load(paths.vendors);
    expectEnvelope(env);
    const rows = env.data as unknown as Record<string, unknown>[];
    expect(rows.length).toBeGreaterThan(0);
    for (const row of rows) {
      expect(typeof row.vendor).toBe('string');
      expect(Number.isInteger(row.peer_rank)).toBe(true);
      expect(row.peer_rank as number).toBeGreaterThanOrEqual(1);
      for (const key of VENDOR_KEYS) expect(row, key).toHaveProperty(key);
    }
  });

  it('insights: non-empty, every item has the 12 frozen keys + valid severity', () => {
    const env = load(paths.insights);
    expectEnvelope(env);
    const items = env.data as unknown as Record<string, unknown>[];
    expect(items.length).toBeGreaterThan(0);
    for (const item of items) {
      for (const key of INSIGHT_KEYS) expect(item, key).toHaveProperty(key);
      expect(['high', 'medium', 'low']).toContain(item.severity);
    }
  });
});
