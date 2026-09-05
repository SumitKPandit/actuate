import React, { useState } from 'react'

export default function TriggerBanner({ dismissed, onDismiss, onRestore, onReview, cardRef }) {
  const [expanded, setExpanded] = useState(false)
  const [pulse, setPulse] = useState(false)

  const handleReview = () => {
    setExpanded(true)
    onReview()
    setPulse(true)
    setTimeout(() => setPulse(false), 1600)
  }

  if (dismissed) {
    return (
      <div className="bg-surface border border-border-light rounded-lg p-3 shadow-xs flex items-center justify-between transition-all duration-300">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-error animate-pulse"></span>
          <span className="text-xs font-bold text-neutral-title">1 Active Operational Trigger Hidden</span>
          <span className="text-xs text-neutral-muted">• OTA 93.0% below SLA (Vendor X -42%)</span>
        </div>
        <button
          className="px-3 py-1 rounded-full bg-surface-panel border border-border-light text-secondary text-xs font-semibold hover:border-secondary transition flex items-center gap-1 shadow-2xs"
          onClick={onRestore}
        >
          <span className="material-symbols-outlined text-[14px]">replay</span>
          <span>Restore alert trigger</span>
        </button>
      </div>
    )
  }

  return (
    <div
      ref={cardRef}
      className={`relative overflow-hidden rounded-lg bg-surface border border-border-light shadow-sm p-5 flex flex-col gap-4 border-l-4 border-l-error transition-all duration-300 ${
        pulse ? 'ring-2 ring-secondary' : ''
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-bold uppercase bg-error-bg text-error px-2.5 py-1 rounded-full flex items-center gap-1.5 border border-error/20">
            <span className="h-2 w-2 rounded-full bg-error animate-ping"></span>
            ACTIVE OPERATIONAL TRIGGER
          </span>
          <span className="text-[11px] font-bold text-secondary bg-blue-50 px-2 py-0.5 rounded-full">AI DETECTED</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono text-neutral-muted">Mart cycle: 2026-06-H1 · Refresh 14m ago</span>
          <button
            className="text-neutral-muted hover:text-neutral-title p-1 rounded-full hover:bg-surface-panel transition flex items-center"
            onClick={onDismiss}
            title="Dismiss trigger banner"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>
      </div>
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <h2 className="text-xl text-neutral-title font-bold tracking-tight">
            OTA dropped below SLA: <span className="text-error font-bold">93.0%</span>{' '}
            <span className="text-sm text-neutral-muted font-normal">(vs 95.0% SLA, ↓ 2.0pp vs previous cycle)</span>
          </h2>
          <div className="flex items-center gap-2 text-sm text-neutral-body mt-0.5">
            <span className="font-semibold text-secondary">Top contributor: Vendor X</span>
            <span className="text-neutral-muted">—</span>
            <span className="bg-error-bg text-error px-2 py-0.5 rounded-full text-xs font-bold border border-error/20">42% of delay gap</span>
          </div>
          <p className="text-xs text-neutral-muted italic mt-1">
            "Actuate detected an SLA breach during the latest mart refresh across morning peak shifts."
          </p>
        </div>
        <div className="flex items-center gap-2 shrink-0 sm:self-center">
          <button
            className="px-4 py-2 rounded-full bg-surface border border-border-light text-neutral-body hover:border-neutral-muted transition text-xs font-semibold flex items-center gap-1.5 shadow-sm"
            onClick={handleReview}
          >
            <span className="material-symbols-outlined text-[16px] text-neutral-muted">visibility</span>
            <span>Review insight</span>
          </button>
          <button
            className="px-5 py-2 rounded-full bg-primary text-surface hover:bg-primary-hover transition text-xs font-bold flex items-center gap-1.5 shadow-sm"
            onClick={handleReview}
          >
            <span className="material-symbols-outlined text-[16px]">troubleshoot</span>
            <span>View evidence</span>
          </button>
        </div>
      </div>
      {expanded && (
        <div className="pt-4 mt-2 border-t border-border-light flex flex-col gap-3 bg-surface-panel -mx-5 -mb-5 p-5 rounded-b-lg">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="bg-surface p-3.5 rounded-lg border border-border-light shadow-sm">
              <span className="text-[11px] font-bold text-neutral-muted uppercase tracking-wide">Driver 1: Route 404 Bottleneck</span>
              <p className="text-xs mt-1 text-neutral-body leading-relaxed">Vendor X cabs delayed by 18.4m at Outer Ring Road cloverleaf.</p>
            </div>
            <div className="bg-surface p-3.5 rounded-lg border border-border-light shadow-sm">
              <span className="text-[11px] font-bold text-neutral-muted uppercase tracking-wide">Driver 2: Fleet Allocation Lag</span>
              <p className="text-xs mt-1 text-neutral-body leading-relaxed">34 scheduled dispatches delayed at driver staging yard.</p>
            </div>
            <div className="bg-surface p-3.5 rounded-lg border border-border-light shadow-sm">
              <span className="text-[11px] font-bold text-neutral-muted uppercase tracking-wide">Driver 3: Buffer Deficit</span>
              <p className="text-xs mt-1 text-neutral-body leading-relaxed">15-minute slotting insufficient under current monsoon rain speed reductions.</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
