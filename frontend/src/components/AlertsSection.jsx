import React, { useState } from 'react'

const sevBadge = {
  high: 'bg-error-bg text-error border border-error/20',
  medium: 'bg-warning-bg text-warning border border-warning/20',
  low: 'bg-surface-panel border border-border-light text-neutral-muted'
}

const bigTone = {
  error: 'text-error',
  warning: 'text-warning',
  title: 'text-neutral-title',
  default: 'text-neutral-title'
}

const noteTone = {
  error: 'text-error font-semibold',
  warning: 'text-warning font-semibold',
  title: 'text-neutral-title font-semibold',
  default: 'text-neutral-muted'
}

function AlertCard({ alert, highlighted, forwardedRef, status, pending, onApprove }) {
  const acked = status === 'acked'
  return (
    <div
      ref={forwardedRef}
      className={`bg-surface rounded-lg border shadow-sm p-5 flex flex-col gap-4 transition alert-card ${highlighted ? 'ring-2 ring-secondary' : 'border-border-light hover:border-neutral-muted/40'}`}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold tracking-wider ${sevBadge[alert.severity] || sevBadge.low}`}>
            <span className={`h-1.5 w-1.5 rounded-full ${alert.severity === 'high' ? 'bg-error' : alert.severity === 'medium' ? 'bg-warning' : 'bg-neutral-muted'}`}></span>
            {(alert.severity || 'unknown').toUpperCase()} SEVERITY
          </span>
          <span className="text-base font-bold text-neutral-title truncate">{alert.title}</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs shrink-0">
          <span className="text-neutral-muted">{alert.scopeLabel}:</span>
          <span className="font-semibold text-neutral-title bg-surface-panel border border-border-light px-2 py-0.5 rounded-full">{alert.scope}</span>
        </div>
      </div>

      <div className={`grid grid-cols-1 gap-4 bg-surface-panel p-4 rounded-lg border border-border-light ${alert.metrics.length === 4 ? 'md:grid-cols-4' : 'md:grid-cols-3'}`}>
        {alert.metrics.map((metric, index) => (
          <div key={`${metric.label}:${index}`}>
            <span className="text-[11px] font-bold text-neutral-muted uppercase tracking-wider">{metric.label}</span>
            <div className="flex items-baseline gap-1.5 mt-1">
              <span className={`${metric.bigSmall ? 'text-xs font-semibold' : 'text-2xl font-bold'} ${bigTone[metric.bigTone] || bigTone.default}`}>
                {metric.big}
              </span>
              {metric.small && <span className="text-xs text-neutral-muted">{metric.small}</span>}
            </div>
            {metric.note && <span className={`text-xs ${noteTone[metric.noteTone] || noteTone.default}`}>{metric.note}</span>}
          </div>
        ))}
      </div>

      <div className="flex items-start gap-3 bg-blue-50/50 p-4 rounded-lg border border-secondary/20 border-l-4 border-l-secondary">
        <span className="material-symbols-outlined text-secondary text-[20px] shrink-0 mt-0.5">auto_awesome</span>
        <div className="flex flex-col gap-1">
          <span className="text-[11px] text-secondary font-bold uppercase tracking-wider">Actuate Reasoning</span>
          <p className="text-xs text-neutral-body leading-relaxed">{alert.reasoning}</p>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between pt-1 gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[11px] uppercase font-bold text-neutral-muted">Recommended Action:</span>
          <span className="text-xs font-medium text-neutral-body">{alert.recommended}</span>
          <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${alert.ownerTone === 'error' ? 'bg-error-bg text-error border-error/20' : 'bg-blue-50 text-secondary border-secondary/20'}`}>
            Owner: {alert.owner}
          </span>
        </div>
        <button
          disabled={acked || pending}
          className={`px-5 py-2 rounded-full text-xs font-bold shadow-sm transition flex items-center gap-1 shrink-0 ${acked ? 'bg-surface-panel border border-border-light text-neutral-title cursor-default' : 'bg-primary text-surface hover:bg-primary-hover disabled:opacity-60'}`}
          onClick={() => onApprove(alert.ackId)}
        >
          {acked && <span className="material-symbols-outlined text-[15px] text-primary">check_circle</span>}
          {pending ? 'Acknowledging...' : acked ? '✓ ACKED' : 'Approve action'}
        </button>
      </div>
    </div>
  )
}

export default function AlertsSection({ alerts, statusById, ackPending, onApprove, alert1Ref, alert1Highlighted }) {
  const [filter, setFilter] = useState('all')
  const counts = {
    all: alerts.length,
    high: alerts.filter((alert) => alert.severity === 'high').length,
    medium: alerts.filter((alert) => alert.severity === 'medium').length,
    low: alerts.filter((alert) => alert.severity === 'low').length
  }
  const filters = ['all', 'high', 'medium', 'low']

  return (
    <div className="flex flex-col gap-4" id="priority-alerts-section">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-1">
        <div className="flex flex-col">
          <h3 className="text-lg font-bold text-neutral-title tracking-tight">PRIORITY ALERTS</h3>
          <span className="text-xs text-neutral-muted">AI-ranked exceptions requiring operational attention.</span>
        </div>
        <div className="flex items-center gap-2 overflow-x-auto">
          <div className="flex items-center bg-surface border border-border-light p-1 rounded-full gap-1 shadow-xs">
            {filters.map((severity) => (
              <button
                key={severity}
                className={`px-3 py-1 rounded-full text-xs font-bold transition ${filter === severity ? 'bg-secondary text-surface shadow-2xs' : 'font-semibold text-neutral-muted hover:text-neutral-title'}`}
                onClick={() => setFilter(severity)}
              >
                {severity[0].toUpperCase() + severity.slice(1)} ({counts[severity]})
              </button>
            ))}
          </div>
          <div className="hidden md:flex items-center gap-1.5 bg-surface px-3 py-1.5 rounded-full border border-border-light shrink-0">
            <span className="text-[11px] text-neutral-muted uppercase font-semibold">Sort:</span>
            <span className="text-xs font-bold text-secondary">Impact (Severity × Vol)</span>
          </div>
        </div>
      </div>
      <div className="flex flex-col gap-4">
        {alerts.map((alert, index) => {
          const hidden = filter !== 'all' && filter !== alert.severity
          return (
            <div key={alert.key} className={hidden ? 'hidden' : ''}>
              <AlertCard
                alert={alert}
                highlighted={index === 0 && alert1Highlighted}
                forwardedRef={index === 0 ? alert1Ref : null}
                status={statusById[alert.ackId] || 'proposed'}
                pending={ackPending.has(alert.ackId)}
                onApprove={onApprove}
              />
            </div>
          )
        })}
      </div>
    </div>
  )
}
