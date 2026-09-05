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

function AlertCard({
  alert,
  hidden,
  highlighted,
  forwardedRef,
  unackText,
  ackTier,
  onWhyToggle,
  whyOpen,
  onCopyVendor,
  onApproveDirect,
  approved,
  onReviewAlerts,
  onAck,
  acked,
  isAlert1,
  alert1BreakdownOpen,
  onAlert1Toggle
}) {
  return (
    <div
      ref={forwardedRef}
      className={`bg-surface rounded-lg border shadow-sm p-5 flex flex-col gap-4 transition alert-card ${
        highlighted ? 'ring-2 ring-secondary' : 'border-border-light hover:border-neutral-muted/40'
      } ${hidden ? 'hidden' : ''}`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold tracking-wider ${sevBadge[alert.severity]}`}>
            <span className={`h-1.5 w-1.5 rounded-full ${alert.severity === 'high' ? 'bg-error' : alert.severity === 'medium' ? 'bg-warning' : 'bg-neutral-muted'} ${alert.severity === 'high' && alert.id === 2 ? 'animate-ping' : ''}`}></span>
            {alert.severity.toUpperCase()} SEVERITY
          </span>
          <span className="text-base font-bold text-neutral-title">{alert.title}</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs">
          <span className="text-neutral-muted">{alert.scopeLabel}:</span>
          <span className="font-semibold text-neutral-title bg-surface-panel border border-border-light px-2 py-0.5 rounded-full">{alert.scope}</span>
        </div>
      </div>

      <div className={`grid grid-cols-1 gap-4 bg-surface-panel p-4 rounded-lg border border-border-light ${alert.metrics.length === 4 ? 'md:grid-cols-4' : 'md:grid-cols-3'}`}>
        {alert.metrics.map((m, i) => (
          <div key={i}>
            <span className="text-[11px] font-bold text-neutral-muted uppercase tracking-wider">{m.label}</span>
            <div className="flex items-baseline gap-1.5 mt-1">
              <span
                className={`${m.bigSmall ? 'text-xs font-semibold' : 'text-2xl font-bold'} ${
                  m.id === 'alert2-status' ? (acked ? 'text-primary' : 'text-warning') : bigTone[m.bigTone] || bigTone.default
                }`}
              >
                {m.id === 'alert2-status' ? ackTier : m.big}
              </span>
              {m.small && <span className="text-xs text-neutral-muted">{m.small}</span>}
              {m.inlineNote && <span className="text-xs text-error font-semibold">{m.inlineNoteId === 'card2-unack-text' ? unackText : m.inlineNote}</span>}
            </div>
            {m.note && <span className={`text-xs ${noteTone[m.noteTone] || noteTone.default}`}>{m.note}</span>}
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
        <div className="flex items-center gap-2 shrink-0">
          <button
            className="px-3 py-1.5 rounded-full text-secondary hover:bg-surface-panel font-semibold text-xs flex items-center gap-1 transition"
            onClick={isAlert1 ? onAlert1Toggle : onWhyToggle}
          >
            <span>{isAlert1 ? (alert1BreakdownOpen ? 'Collapse insight' : 'Why did Actuate flag this?') : 'Why did Actuate flag this?'}</span>
            <span className="material-symbols-outlined text-[16px]">
              {isAlert1 ? (alert1BreakdownOpen ? 'expand_less' : 'expand_more') : whyOpen ? 'expand_less' : 'expand_more'}
            </span>
          </button>

          {alert.hasCopyForVendor && (
            <button
              className="px-4 py-2 rounded-full bg-surface border border-border-light hover:border-neutral-muted text-neutral-body font-semibold text-xs flex items-center gap-1.5 transition shadow-sm"
              onClick={() => onCopyVendor(alert.vendorName, alert.vendorOta)}
            >
              <span className="material-symbols-outlined text-[16px]">content_copy</span>
              <span>Copy for vendor</span>
            </button>
          )}

          {alert.hasReviewAlerts && (
            <button
              className="px-4 py-2 rounded-full bg-surface border border-border-light hover:border-neutral-muted text-neutral-body font-semibold text-xs transition shadow-sm"
              onClick={onReviewAlerts}
            >
              Review alerts
            </button>
          )}

          {alert.hasAckButton ? (
            <button
              disabled={acked}
              className={`px-5 py-2 rounded-full text-xs font-bold shadow-sm transition flex items-center gap-1 ${
                acked ? 'bg-surface-panel border border-border-light text-neutral-title cursor-default' : 'bg-primary text-surface hover:bg-primary-hover'
              }`}
              onClick={onAck}
            >
              {acked && <span className="material-symbols-outlined text-[15px] text-primary">check_circle</span>}
              {acked ? '✓ Acked' : 'Acknowledge'}
            </button>
          ) : alert.actionLabel ? (
            <button
              disabled={approved}
              className={`px-5 py-2 rounded-full text-xs font-bold shadow-sm transition flex items-center gap-1 ${
                approved ? 'bg-surface-panel border border-border-light text-neutral-title cursor-default' : 'bg-primary text-surface hover:bg-primary-hover'
              }`}
              onClick={() => onApproveDirect(alert.actionTitle || alert.actionLabel, alert.badgeId)}
            >
              {approved && <span className="material-symbols-outlined text-[15px] text-primary">check_circle</span>}
              {approved ? '✓ ACKED' : alert.actionLabel}
            </button>
          ) : (
            <button
              disabled={approved}
              className={`px-5 py-2 rounded-full text-xs font-bold shadow-sm transition ${
                approved ? 'bg-surface-panel border border-border-light text-neutral-title cursor-default' : 'bg-primary text-surface hover:bg-primary-hover'
              }`}
              onClick={() => onApproveDirect('Review Vendor X penalty')}
            >
              {approved ? '✓ ACKED' : 'Approve action'}
            </button>
          )}
        </div>
      </div>

      {isAlert1 && alert1BreakdownOpen && alert.breakdown && (
        <div className="pt-4 border-t border-border-light flex flex-col gap-3">
          <div className="bg-surface-panel p-4 rounded-lg border border-border-light flex flex-col gap-3">
            <div className="flex items-center justify-between pb-2 border-b border-border-light">
              <span className="text-xs font-bold text-neutral-title uppercase tracking-wider">Deep Dive Operational Breakdown</span>
              <span className="text-[11px] font-semibold text-primary">High Confidence Model ({alert.breakdown.confidence})</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              {alert.breakdown.rows.map(([label, val], i) => (
                <div key={i}>
                  <span className="text-neutral-muted block text-[11px]">{label}</span>{' '}
                  <strong className={val.includes('93.0') || val.includes('42%') ? 'text-error' : ''}>{val}</strong>
                </div>
              ))}
            </div>
            <p className="text-xs text-neutral-muted pt-2 border-t border-border-light leading-relaxed">
              <strong>AI Reasoning &amp; Direct Action:</strong> {alert.breakdown.note}
            </p>
          </div>
        </div>
      )}

      {!isAlert1 && whyOpen && alert.breakdownSimple && (
        <div className="pt-4 border-t border-border-light flex flex-col gap-2">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs bg-surface-panel p-3 rounded-lg border border-border-light font-mono">
            {alert.breakdownSimple.map(([label, val], i) => (
              <div key={i}>
                <span className="text-neutral-muted block text-[11px]">{label}</span> {val}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default function AlertsSection({
  alerts,
  unackCount,
  onCopyVendor,
  onApproveDirect,
  approvedDirect,
  onOpenSafety,
  onAckSev1,
  sev1Acked,
  alert1Ref,
  alert1Highlighted,
  alert1BreakdownOpen,
  onAlert1Toggle
}) {
  const [filter, setFilter] = useState('all')
  const [whyOpenMap, setWhyOpenMap] = useState({})

  const counts = {
    all: alerts.length,
    critical: alerts.filter((a) => a.severity === 'critical').length,
    high: alerts.filter((a) => a.severity === 'high').length,
    medium: alerts.filter((a) => a.severity === 'medium').length,
    low: alerts.filter((a) => a.severity === 'low').length
  }

  const toggleWhy = (id) => setWhyOpenMap((m) => ({ ...m, [id]: !m[id] }))

  return (
    <div className="flex flex-col gap-4" id="priority-alerts-section">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-1">
        <div className="flex flex-col">
          <h3 className="text-lg font-bold text-neutral-title tracking-tight">PRIORITY ALERTS</h3>
          <span className="text-xs text-neutral-muted">AI-ranked exceptions requiring operational attention.</span>
        </div>
        <div className="flex items-center gap-2 overflow-x-auto">
          <div className="flex items-center bg-surface border border-border-light p-1 rounded-full gap-1 shadow-xs">
            {['all', 'critical', 'high', 'medium', 'low'].map((sev) => (
              <button
                key={sev}
                className={`px-3 py-1 rounded-full text-xs font-bold transition ${
                  filter === sev ? 'bg-secondary text-surface shadow-2xs' : 'font-semibold text-neutral-muted hover:text-neutral-title'
                }`}
                onClick={() => setFilter(sev)}
              >
                {sev[0].toUpperCase() + sev.slice(1)} ({counts[sev]})
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
        {alerts.map((alert) => {
          const isAlert1 = alert.id === 1
          const isAlert2 = alert.id === 2
          const hidden = filter !== 'all' && filter !== alert.severity && !(isAlert1 && alert1Highlighted)
          return (
            <AlertCard
              key={alert.id}
              alert={alert}
              hidden={hidden}
              highlighted={isAlert1 && alert1Highlighted}
              forwardedRef={isAlert1 ? alert1Ref : null}
              unackText={`(${unackCount} unacknowledged)`}
              ackTier={sev1Acked ? '✓ ACKNOWLEDGED' : 'Tier 2 Ops'}
              whyOpen={!!whyOpenMap[alert.id]}
              onWhyToggle={() => toggleWhy(alert.id)}
              onCopyVendor={onCopyVendor}
              onApproveDirect={onApproveDirect}
              approved={!!approvedDirect[alert.id]}
              onReviewAlerts={onOpenSafety}
              onAck={() => onAckSev1(isAlert2)}
              acked={isAlert2 && sev1Acked}
              isAlert1={isAlert1}
              alert1BreakdownOpen={alert1BreakdownOpen}
              onAlert1Toggle={onAlert1Toggle}
            />
          )
        })}
      </div>
    </div>
  )
}
