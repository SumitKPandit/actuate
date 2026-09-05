import React, { useState } from 'react'

const tagClasses = {
  error: 'bg-error-bg text-error border border-error/20',
  'error-solid': 'bg-error text-surface animate-pulse',
  warning: 'bg-warning-bg text-warning border border-warning/20',
  success: 'bg-success-bg text-primary border border-primary/20',
  neutral: 'bg-surface-panel border border-border-light text-neutral-body',
}

const valueToneClasses = {
  error: 'text-error',
  default: 'text-neutral-title',
}

const deltaToneClasses = {
  error: 'text-error',
  warning: 'text-warning',
  default: 'text-neutral-muted',
}

function KpiCard({ kpi, unackCount, onClick }) {
  return (
    <div
      className={`bg-surface p-4 rounded-lg border shadow-sm flex flex-col justify-between transition group ${
        kpi.safety
          ? 'border-l-2 border-l-error cursor-pointer hover:border-error hover:shadow'
          : 'border-border-light'
      } ${kpi.drilldown ? 'cursor-pointer hover:border-secondary hover:shadow' : ''}`}
      onClick={onClick}
    >
      <div className="flex items-center justify-between">
        <span
          className={`text-[11px] font-bold text-neutral-muted uppercase tracking-wider ${
            kpi.safety
              ? 'group-hover:text-error'
              : kpi.drilldown
                ? 'group-hover:text-secondary'
                : ''
          }`}
        >
          {kpi.label}
        </span>
        <span
          className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${tagClasses[kpi.tag.tone]}`}
        >
          {kpi.tag.text}
        </span>
      </div>
      <div className="my-2">
        <span
          className={`text-2xl font-bold tracking-tight ${valueToneClasses[kpi.valueTone] || valueToneClasses.default}`}
        >
          {kpi.value}
          {kpi.valueUnit && (
            <span className="text-sm font-normal text-neutral-muted">
              {' '}
              {kpi.valueUnit}
            </span>
          )}
        </span>
        {kpi.delta ? (
          <div
            className={`flex items-center gap-1 text-xs font-semibold mt-0.5 ${deltaToneClasses[kpi.deltaTone] || deltaToneClasses.default}`}
          >
            {kpi.deltaIcon && (
              <span className="material-symbols-outlined text-[14px]">
                {kpi.deltaIcon}
              </span>
            )}
            <span>{kpi.delta}</span>
            <span className="text-neutral-muted font-normal text-[11px]">
              {kpi.deltaNote}
            </span>
          </div>
        ) : kpi.safety ? (
          <div className="flex items-center gap-1 text-xs text-error font-semibold mt-0.5">
            <span>{unackCount} unacked</span>
            <span className="text-neutral-muted font-normal text-[11px]">
              | 47m max
            </span>
          </div>
        ) : (
          <div className="flex items-center gap-1 text-xs text-neutral-muted font-medium mt-0.5">
            {kpi.id === 'csat' && (
              <span className="text-warning font-semibold">↓ 0.08</span>
            )}
            <span className="text-[11px]">{kpi.deltaNote}</span>
          </div>
        )}
      </div>
      <div className="flex items-center justify-between pt-2 border-t border-border-light text-xs text-neutral-muted">
        <span>{kpi.footLabel}</span>
        <span
          className={`font-semibold ${kpi.footTone === 'error' ? 'text-error' : 'text-secondary'}`}
        >
          {kpi.footValue}
        </span>
      </div>
    </div>
  )
}

export default function KpiPulse({
  kpis,
  unackCount,
  onOpenSafety,
  onAskCopilot,
}) {
  const [drilldownOpen, setDrilldownOpen] = useState(false)

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between px-1">
        <span className="text-xs font-bold text-neutral-title uppercase tracking-wider">
          Executive Operations Pulse
        </span>
        <span className="text-xs text-neutral-muted font-medium">
          Click KPI card for drilldown • Realtime Aggregation
        </span>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {kpis.map((kpi) => (
          <KpiCard
            key={kpi.id}
            kpi={kpi}
            unackCount={unackCount}
            onClick={() => {
              if (kpi.drilldown) setDrilldownOpen((v) => !v)
              else if (kpi.safety) onOpenSafety()
            }}
          />
        ))}
      </div>

      {drilldownOpen && (
        <div className="bg-surface border border-secondary/30 rounded-lg p-4 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mt-1 transition-all">
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-secondary uppercase tracking-wider">
                OTA Metric Drilldown
              </span>
              <span className="text-[11px] font-semibold text-neutral-muted">
                Mart table: mart.vendor_kpi
              </span>
            </div>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-neutral-body">
              <span>
                <strong>Current:</strong>{' '}
                <span className="text-error font-semibold">93.0%</span>
              </span>
              <span className="text-neutral-muted">|</span>
              <span>
                <strong>SLA:</strong> 95.0%
              </span>
              <span className="text-neutral-muted">|</span>
              <span>
                <strong>Previous cycle:</strong> 95.0% (Δ −2.0pp)
              </span>
              <span className="text-neutral-muted">|</span>
              <span>
                <strong>Peer comparison:</strong> 96.2%
              </span>
              <span className="text-neutral-muted">|</span>
              <span>
                <strong>Top contributor:</strong> Vendor X (
                <span className="text-error font-semibold">42% gap share</span>)
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              className="px-3.5 py-1.5 rounded-full bg-secondary text-surface text-xs font-bold hover:bg-primary-hover transition flex items-center gap-1.5 shadow-xs"
              onClick={() => onAskCopilot('Why did OTA drop?')}
            >
              <span className="material-symbols-outlined text-[15px]">
                smart_toy
              </span>
              <span>Ask Actuate about OTA</span>
            </button>
            <button
              className="p-1 rounded-full text-neutral-muted hover:text-neutral-title hover:bg-surface-panel transition"
              onClick={() => setDrilldownOpen(false)}
            >
              <span className="material-symbols-outlined text-[18px]">
                close
              </span>
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
