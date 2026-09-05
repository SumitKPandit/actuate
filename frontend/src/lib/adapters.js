const KPI_LABELS = {
  ota_pct: 'OTA',
  ota: 'OTA',
  avg_delay_min: 'Avg Delay',
  'avg-delay': 'Avg Delay',
  no_show: 'No-show',
  'no-show': 'No-show',
  cost: 'Cost / Trip',
  sev1: 'Safety Sev-1',
  ack: 'Ack',
  csat: 'CSAT'
}

function isNumber(value) {
  return typeof value === 'number' && Number.isFinite(value)
}

function numberText(value, maximumFractionDigits = 2, minimumFractionDigits = 0) {
  if (!isNumber(value)) return '—'
  return value.toLocaleString('en-IN', { maximumFractionDigits, minimumFractionDigits })
}

function countText(value) {
  return numberText(value, 0)
}

function insightKpi(kpi) {
  if (kpi === 'ota') return 'ota_pct'
  if (kpi === 'no-show') return 'no_show'
  if (kpi === 'avg-delay') return 'avg_delay_min'
  return kpi
}

export function fmtKpiValue(kpi, value) {
  if (!isNumber(value)) return '—'
  const normalized = insightKpi(kpi)
  if (normalized === 'ota_pct' || normalized === 'no_show') return `${numberText(value, 1)}%`
  if (normalized === 'cost') return `₹${numberText(value, 2, 2)}`
  if (normalized === 'avg_delay_min') return numberText(value, 1)
  if (normalized === 'csat') return numberText(value, 2)
  if (normalized === 'sev1') return countText(value)
  return numberText(value, 2)
}

export function fmtShare(value) {
  return isNumber(value) ? `${numberText(value * 100, 2)}%` : '—'
}

export function fmtDelta(kpi, deltaPp) {
  if (!isNumber(deltaPp)) return '—'
  const unit = insightKpi(kpi) === 'cost' ? '%' : 'pp'
  const sign = deltaPp > 0 ? '+' : ''
  return `${sign}${numberText(deltaPp, 2)}${unit}`
}

export function findPriorInsight(insights, kpi) {
  const targetKpi = insightKpi(kpi)
  if (!Array.isArray(insights)) return null
  return (
    insights.find((insight) => {
      const scope = insight?.scope || {}
      return insight?.kpi === targetKpi && insight.reason === 'vs_prior' && scope.vendor == null && scope.office == null
    }) || null
  )
}

function isAdverse(kpi, delta) {
  if (!isNumber(delta) || delta === 0) return false
  const normalized = insightKpi(kpi)
  return ['ota_pct', 'csat'].includes(normalized) ? delta < 0 : delta > 0
}

function deltaProps(kpi, prior) {
  if (!prior || !isNumber(prior.delta_pp) || !isNumber(prior.baseline)) {
    return { deltaNote: 'Prior cycle: —' }
  }
  const delta = prior.delta_pp
  return {
    delta: fmtDelta(kpi, delta),
    deltaIcon: delta < 0 ? 'arrow_downward' : 'arrow_upward',
    deltaTone: isAdverse(kpi, delta) ? 'error' : 'default',
    deltaNote: 'Prior cycle'
  }
}

export function buildKpis(overview, insights, safetyOpenSev1) {
  const data = overview || {}
  const benchmark = data.benchmarks?.ota_sla
  const otaHasBenchmark = isNumber(data.ota_pct) && isNumber(benchmark)
  const otaBelowSla = otaHasBenchmark && data.ota_pct < benchmark
  const safetyValue = isNumber(safetyOpenSev1) ? safetyOpenSev1 : data.sev1_count
  const otaPrior = findPriorInsight(insights, 'ota_pct')
  const otaDelta = deltaProps('ota_pct', otaPrior)

  return [
    {
      id: 'ota',
      label: 'OTA',
      tag: { text: !otaHasBenchmark ? '—' : otaBelowSla ? 'Below SLA' : 'On SLA', tone: !otaHasBenchmark ? 'neutral' : otaBelowSla ? 'error' : 'success' },
      value: fmtKpiValue('ota', data.ota_pct),
      valueTone: otaBelowSla ? 'error' : 'default',
      footLabel: 'SLA',
      footValue: fmtKpiValue('ota', benchmark),
      drilldown: true,
      drilldownData: {
        current: fmtKpiValue('ota', data.ota_pct),
        sla: fmtKpiValue('ota', benchmark),
        prior: otaPrior?.baseline,
        delta: otaPrior?.delta_pp,
        contributionShare: otaPrior?.contribution_share
      },
      ...otaDelta
    },
    {
      id: 'avg-delay',
      label: 'Avg Delay',
      tag: { text: 'Active', tone: 'neutral' },
      value: fmtKpiValue('avg-delay', data.avg_delay_min),
      valueUnit: 'min',
      footLabel: 'Primary',
      footValue: 'Traffic',
      ...deltaProps('avg-delay', null)
    },
    {
      id: 'no-show',
      label: 'No-show',
      tag: { text: 'Variance', tone: 'warning' },
      value: fmtKpiValue('no-show', data.no_show_rate),
      footLabel: 'Owner',
      footValue: 'Office',
      ...deltaProps('no_show', findPriorInsight(insights, 'no_show'))
    },
    {
      id: 'cost',
      label: 'Cost / Trip',
      tag: { text: 'Audit', tone: 'neutral' },
      value: fmtKpiValue('cost', data.cost_per_trip),
      footLabel: 'Owner',
      footValue: 'Ops',
      ...deltaProps('cost', findPriorInsight(insights, 'cost'))
    },
    {
      id: 'safety',
      label: 'Safety Sev-1',
      tag: { text: 'Critical', tone: 'error-solid', pulse: true },
      value: fmtKpiValue('sev1', safetyValue),
      valueUnit: 'Open',
      valueTone: isNumber(safetyValue) && safetyValue > 0 ? 'error' : 'default',
      footLabel: 'Owner',
      footValue: 'Ops Desk',
      footTone: 'error',
      safety: true,
      ...deltaProps('sev1', findPriorInsight(insights, 'sev1'))
    },
    {
      id: 'csat',
      label: 'CSAT',
      tag: { text: 'Stable', tone: 'success' },
      value: fmtKpiValue('csat', data.csat_avg),
      valueUnit: '/5',
      footLabel: 'Low ratings',
      footValue: isNumber(data.low_rating_share) ? `${numberText(data.low_rating_share, 2)}%` : '—',
      ...deltaProps('csat', findPriorInsight(insights, 'csat'))
    }
  ]
}

function formatAlertValue(kpi, value) {
  if (!isNumber(value)) return '—'
  if (kpi === 'ota_pct' || kpi === 'no_show') return fmtKpiValue(kpi, value)
  if (kpi === 'cost') return fmtKpiValue(kpi, value)
  return numberText(value, 2)
}

function scopeText(scope) {
  return scope?.vendor || scope?.office || 'All'
}

function reasonText(reason) {
  const labels = {
    vs_sla: 'vs SLA',
    vs_prior: 'vs prior cycle',
    vs_peer: 'peer comparison',
    anomaly: 'anomaly',
    z_score: 'z-score'
  }
  return labels[reason] || reason || '—'
}

export function buildAlerts(insightsTop5) {
  if (!Array.isArray(insightsTop5)) return []
  return insightsTop5.map((insight, index) => {
    const reason = reasonText(insight.reason)
    const current = formatAlertValue(insight.kpi, insight.current)
    const baseline = formatAlertValue(insight.kpi, insight.baseline)
    return {
      key: `${insight.id}:${index}`,
      id: insight.id,
      ackId: insight.id,
      severity: insight.severity,
      title: `ALERT ${String(index + 1).padStart(2, '0')}: ${KPI_LABELS[insight.kpi] || insight.kpi} (${reason})`,
      scopeLabel: 'Scope',
      scope: scopeText(insight.scope),
      metrics: [
        {
          label: 'Current vs Baseline',
          big: current,
          bigTone: isAdverse(insight.kpi, insight.delta_pp) ? 'error' : 'title',
          small: baseline === '—' ? '' : `/ ${baseline} baseline`,
          note: isNumber(insight.delta_pp) ? `Δ ${fmtDelta(insight.kpi, insight.delta_pp)}` : 'Δ —',
          noteTone: isAdverse(insight.kpi, insight.delta_pp) ? 'error' : 'default'
        },
        { label: 'Operational Impact', big: countText(insight.reach_trips), small: 'trips affected' },
        { label: 'Contribution', big: fmtShare(insight.contribution_share), bigTone: 'title', note: 'contribution share' },
        { label: 'Reason', big: reason, bigSmall: true, note: 'ranked insight' }
      ],
      reasoning: `Actuate flagged this ${reason} insight for ${scopeText(insight.scope)}.`,
      recommended: insight.recommended_action || '—',
      owner: insight.owner || '—',
      ownerTone: insight.owner === 'ops' ? 'error' : 'secondary',
      actionLabel: 'Approve action'
    }
  })
}

export function buildActions(actionsTop3, actionsList, statusById = {}, ackOverrides = {}) {
  const source = Array.isArray(actionsTop3) && actionsTop3.length > 0 ? actionsTop3 : Array.isArray(actionsList) ? actionsList.slice(0, 3) : []
  return source.map((action) => {
    const status = ackOverrides[action.id] ?? statusById[action.id] ?? action.status ?? 'proposed'
    return {
      id: action.id,
      owner: action.owner || '—',
      ownerTone: action.owner === 'ops' ? 'error' : 'secondary',
      title: action.action || '—',
      reason: action.due_hint ? `Due: ${action.due_hint}` : 'Due: —',
      copyForVendor: action.copy_for_vendor || '',
      hasCopy: typeof action.copy_for_vendor === 'string' && action.copy_for_vendor.length > 0,
      status,
      approved: status === 'acked'
    }
  })
}

export function getFiredTriggers(briefing) {
  return Array.isArray(briefing?.triggers) ? briefing.triggers.filter((trigger) => trigger?.fired === true) : []
}
