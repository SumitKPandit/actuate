import { describe, expect, it } from 'vitest'

import {
  buildActions,
  buildAlerts,
  buildKpis,
  findPriorInsight,
  fmtDelta,
  fmtKpiValue,
  fmtShare,
  getFiredTriggers
} from '../adapters'

const overview = {
  ota_pct: 96.9,
  avg_delay_min: 1.7,
  no_show_rate: 6.9,
  cost_per_trip: 1339.18,
  csat_avg: 4.8,
  low_rating_share: 1.7,
  benchmarks: { ota_sla: 95, ack_sla_min: 30 }
}

const insights = [
  { id: 'peer', kpi: 'no_show', reason: 'vs_peer', scope: { vendor: 'Vendor X', office: null }, current: 8, baseline: 7, delta_pp: 1 },
  { id: 'prior', kpi: 'no_show', reason: 'vs_prior', scope: { vendor: null, office: null }, current: 6.9, baseline: 6.2, delta_pp: 0.7 },
  { id: 'ota-prior', kpi: 'ota_pct', reason: 'vs_prior', scope: { vendor: null, office: null }, current: 96.9, baseline: 99.1, delta_pp: -2.2 }
]

describe('adapters', () => {
  it('formats KPI values, shares, and cost deltas without converting zero to missing', () => {
    expect(fmtKpiValue('ota', 96.9)).toBe('96.9%')
    expect(fmtKpiValue('avg-delay', 0)).toBe('0')
    expect(fmtKpiValue('cost', 1339.18)).toContain('1,339.18')
    expect(fmtKpiValue('cost', 0)).toContain('0.00')
    expect(fmtKpiValue('csat', null)).toBe('—')
    expect(fmtShare(0.31)).toBe('31%')
    expect(fmtShare(null)).toBe('—')
    expect(fmtDelta('cost', 8.2)).toBe('+8.2%')
    expect(fmtDelta('ota', -2.2)).toBe('-2.2pp')
  })

  it('selects only the first all-scope prior insight', () => {
    expect(findPriorInsight(insights, 'no_show')).toEqual(insights[1])
    expect(findPriorInsight(insights, 'csat')).toBeNull()
  })

  it('maps the six live KPI cards and keeps unavailable deltas neutral', () => {
    const kpis = buildKpis(overview, insights, 252)
    expect(kpis).toHaveLength(6)
    expect(kpis[0]).toMatchObject({ id: 'ota', value: '96.9%', tag: { text: 'On SLA' } })
    expect(kpis[0].delta).toBe('-2.2pp')
    expect(kpis[1]).toMatchObject({ id: 'avg-delay', value: '1.7', valueUnit: 'min' })
    expect(kpis[1].delta).toBeUndefined()
    expect(kpis[4]).toMatchObject({ id: 'safety', value: '252', valueUnit: 'Open' })
    expect(kpis[5].deltaNote).toBe('Prior cycle: —')
  })

  it('does not invent a benchmark status or zero values for an empty overview', () => {
    const kpis = buildKpis({ ota_pct: null, benchmarks: null, sev1_count: null }, [], null)
    expect(kpis[0]).toMatchObject({ value: '—', tag: { text: '—', tone: 'neutral' } })
    expect(kpis[4].value).toBe('—')
  })

  it('maps alerts with stable duplicate-safe keys and API fields', () => {
    const source = [
      {
        id: 'same',
        kpi: 'ota_pct',
        scope: { vendor: null, office: null },
        current: 96.9,
        baseline: 99.1,
        delta_pp: -2.2,
        contribution_share: 0.31,
        severity: 'high',
        reach_trips: 120,
        reason: 'vs_prior',
        recommended_action: 'Review routes',
        owner: 'vendor'
      },
      { id: 'same', kpi: 'cost', scope: {}, current: 10, baseline: 8, delta_pp: 25, contribution_share: null, severity: 'low', reach_trips: 0, reason: 'anomaly', recommended_action: 'Check bills', owner: 'ops' }
    ]
    const alerts = buildAlerts(source)
    expect(alerts.map((alert) => alert.key)).toEqual(['same:0', 'same:1'])
    expect(alerts[0]).toMatchObject({ ackId: 'same', severity: 'high', scope: 'All', owner: 'vendor', recommended: 'Review routes' })
    expect(alerts[0].metrics).toEqual(expect.arrayContaining([expect.objectContaining({ label: 'Contribution', big: '31%' })]))
  })

  it('prefers top actions, resolves optimistic status, and falls back to full actions', () => {
    const top = [{ id: 'a1', action: 'Top action', owner: 'ops', due_hint: 'today', copy_for_vendor: 'Exact API copy', status: 'proposed' }]
    const full = [{ id: 'a2', action: 'Fallback action', owner: 'vendor', due_hint: 'tomorrow', copy_for_vendor: '', status: 'proposed' }]
    expect(buildActions(top, full, { a1: 'proposed' }, { a1: 'acked' })[0]).toMatchObject({ id: 'a1', status: 'acked', copyForVendor: 'Exact API copy' })
    expect(buildActions([], full, {}, {})[0]).toMatchObject({ id: 'a2', title: 'Fallback action' })
  })

  it('returns only fired triggers and tolerates missing or unexpected values', () => {
    expect(getFiredTriggers({ triggers: [{ fired: false }, { fired: true, name: 'OTA', scope: 'All' }] })).toHaveLength(1)
    expect(getFiredTriggers({})).toEqual([])
    expect(getFiredTriggers({ triggers: null })).toEqual([])
    expect(getFiredTriggers({ triggers: [{ fired: false }] })).toEqual([])
  })
})
