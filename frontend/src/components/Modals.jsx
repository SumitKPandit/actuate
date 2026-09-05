import React from 'react'

function ModalShell({ open, onClose, maxWidth = 'max-w-lg', children }) {
  if (!open) return null
  return (
    <div
      className="fixed inset-0 z-50 bg-neutral-title/60 backdrop-blur-xs flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className={`bg-surface w-full ${maxWidth} rounded-lg border border-border-light shadow-2xl p-6 flex flex-col gap-4 max-h-[90vh] overflow-y-auto animate-in fade-in zoom-in-95 duration-200`}
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </div>
    </div>
  )
}

export function AuditModal({ open, onClose, actionTitle, timestamp }) {
  return (
    <ModalShell open={open} onClose={onClose}>
      <div className="flex items-center justify-between pb-3 border-b border-border-light">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-secondary text-[22px]">verified_user</span>
          <h3 className="text-base font-bold text-neutral-title">Operational Audit Trail</h3>
        </div>
        <button className="p-1 text-neutral-muted hover:text-neutral-title rounded-full hover:bg-surface-panel transition" onClick={onClose}>
          <span className="material-symbols-outlined text-[20px]">close</span>
        </button>
      </div>
      <div className="flex flex-col gap-3 text-xs">
        <div className="bg-surface-panel p-3.5 rounded-lg border border-border-light flex flex-col gap-1.5">
          <div className="flex justify-between items-center text-[11px] font-bold text-neutral-muted uppercase">
            <span>Action Reference: ACT-2026-06-8902</span>
            <span className="text-primary font-semibold">Verified &amp; Logged</span>
          </div>
          <p className="text-neutral-title font-semibold text-sm">Action Execution Confirmed</p>
          <span className="text-neutral-muted">Acknowledged just now by Transport Manager (Desk Lead IST).</span>
        </div>
        <div className="border border-border-light rounded-lg overflow-hidden font-mono text-[11px]">
          <div className="bg-surface-panel px-3 py-2 border-b border-border-light font-bold text-neutral-muted uppercase">
            Execution Parameters
          </div>
          <div className="p-3 space-y-1.5 bg-surface text-neutral-body">
            <div><span className="text-neutral-muted">Timestamp:</span> {timestamp}</div>
            <div><span className="text-neutral-muted">Operator:</span> Transport Manager (Role: Dispatch Ops Supervisor)</div>
            <div><span className="text-neutral-muted">Action:</span> {actionTitle || 'Action Execution Confirmed'}</div>
            <div><span className="text-neutral-muted">Governance State:</span> Dispatched to Vendor Extranet &amp; Mart Log</div>
            <div><span className="text-neutral-muted">SLA State:</span> Corrective directive active (Grace period: 45m)</div>
          </div>
        </div>
      </div>
      <div className="flex justify-end pt-2">
        <button className="px-4 py-2 rounded-full bg-secondary text-surface text-xs font-bold hover:bg-primary-hover transition" onClick={onClose}>
          Close Audit
        </button>
      </div>
    </ModalShell>
  )
}

export function SafetyModal({ open, onClose, unackCount, totalOpen, incidents, onAckIncident }) {
  return (
    <ModalShell open={open} onClose={onClose} maxWidth="max-w-2xl">
      <div className="flex items-center justify-between pb-3 border-b border-border-light">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-error animate-ping"></span>
          <h3 className="text-base font-bold text-neutral-title">Sev-1 Incident Telemetry &amp; Ack Desk</h3>
        </div>
        <button className="p-1 text-neutral-muted hover:text-neutral-title rounded-full hover:bg-surface-panel transition" onClick={onClose}>
          <span className="material-symbols-outlined text-[20px]">close</span>
        </button>
      </div>
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-surface-panel p-3 rounded-lg border border-border-light">
          <span className="text-[11px] font-bold text-neutral-muted uppercase">Total Open Sev-1</span>
          <div className="text-xl font-bold text-error mt-0.5">{totalOpen}</div>
        </div>
        <div className="bg-surface-panel p-3 rounded-lg border border-border-light">
          <span className="text-[11px] font-bold text-neutral-muted uppercase">Unacknowledged</span>
          <div className="text-xl font-bold text-error mt-0.5">{unackCount}</div>
        </div>
        <div className="bg-surface-panel p-3 rounded-lg border border-border-light">
          <span className="text-[11px] font-bold text-neutral-muted uppercase">Oldest Breach</span>
          <div className="text-xl font-bold text-neutral-title mt-0.5">47 min</div>
        </div>
      </div>
      <div className="flex flex-col gap-2">
        <span className="text-xs font-bold text-neutral-muted uppercase tracking-wider">Active Incident Queue</span>
        <div className="border border-border-light rounded-lg divide-y divide-border-light overflow-hidden text-xs">
          {incidents.map((inc) => (
            <div
              key={inc.id}
              className={`p-3 flex items-center justify-between gap-3 ${inc.acked ? 'bg-surface-panel/50 opacity-80' : 'bg-surface'}`}
            >
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-neutral-title">{inc.code}</span>
                  <span
                    className={
                      inc.acked
                        ? 'bg-surface border border-border-light text-neutral-muted text-[10px] font-bold px-2 py-0.5 rounded-full'
                        : 'bg-error-bg text-error text-[10px] font-bold px-2 py-0.5 rounded-full'
                    }
                  >
                    Sev-1
                  </span>
                  <span className={`text-[11px] font-medium ${inc.acked ? 'text-neutral-muted' : 'text-error'}`}>{inc.waiting}</span>
                </div>
                <p className="text-neutral-body text-xs">{inc.desc}</p>
              </div>
              {inc.acked ? (
                <span className="px-3 py-1 text-[11px] font-bold text-primary bg-success-bg border border-primary/20 rounded-full shrink-0">
                  ✓ Acknowledged
                </span>
              ) : (
                <button
                  className="px-3 py-1.5 rounded-full bg-primary text-surface text-xs font-bold hover:bg-primary-hover transition shrink-0"
                  onClick={() => onAckIncident(inc.id)}
                >
                  Acknowledge
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
      <div className="flex justify-between items-center pt-2">
        <span className="text-[11px] text-neutral-muted">Ack SLA requires dispatcher intervention within 30 min.</span>
        <button
          className="px-4 py-2 rounded-full bg-surface border border-border-light text-neutral-title text-xs font-bold hover:bg-surface-panel transition"
          onClick={onClose}
        >
          Dismiss
        </button>
      </div>
    </ModalShell>
  )
}

export function DataQualityModal({ open, onClose }) {
  return (
    <ModalShell open={open} onClose={onClose} maxWidth="max-w-xl">
      <div className="flex items-center justify-between pb-3 border-b border-border-light">
        <div className="flex items-center gap-2">
          <span className="material-symbols-outlined text-primary text-[22px]">verified</span>
          <h3 className="text-base font-bold text-neutral-title">Data Quality &amp; Telemetry Standard</h3>
        </div>
        <button className="p-1 text-neutral-muted hover:text-neutral-title rounded-full hover:bg-surface-panel transition" onClick={onClose}>
          <span className="material-symbols-outlined text-[20px]">close</span>
        </button>
      </div>
      <div className="flex flex-col gap-3 text-xs">
        <div className="bg-success-bg/40 border border-primary/20 p-3 rounded-lg flex items-center justify-between">
          <span className="font-bold text-neutral-title">Pipeline Health Score: 97.8% Trust Factor</span>
          <span className="px-2 py-0.5 bg-success-bg text-primary font-bold text-[10px] rounded-full">PASSED AUDIT</span>
        </div>
        <div className="border border-border-light rounded-lg divide-y divide-border-light">
          <div className="p-3 flex items-start gap-2.5">
            <span className="material-symbols-outlined text-primary text-[18px]">check_circle</span>
            <div>
              <span className="font-bold text-neutral-title">Trip IDs Normalized</span>
              <p className="text-neutral-muted mt-0.5">MoveInSync and FleetOps UUIDs mapped to canonical unified key.</p>
            </div>
          </div>
          <div className="p-3 flex items-start gap-2.5">
            <span className="material-symbols-outlined text-primary text-[18px]">check_circle</span>
            <div>
              <span className="font-bold text-neutral-title">Zero-km Bills Retained</span>
              <p className="text-neutral-muted mt-0.5">Cancelled-at-gate dispatches preserved for vendor reconciliation billing.</p>
            </div>
          </div>
          <div className="p-3 flex items-start gap-2.5">
            <span className="material-symbols-outlined text-primary text-[18px]">check_circle</span>
            <div>
              <span className="font-bold text-neutral-title">UNSLABBED Bills Retained</span>
              <p className="text-neutral-muted mt-0.5">Tariff lines without matched distance slabs flagged to Ops audit, not dropped.</p>
            </div>
          </div>
          <div className="p-3 flex items-start gap-2.5">
            <span className="material-symbols-outlined text-warning text-[18px]">warning</span>
            <div>
              <span className="font-bold text-neutral-title">Unclassified Severity Handling</span>
              <p className="text-neutral-muted mt-0.5">Null severity values default to '—' standard representation (never masked as 0).</p>
            </div>
          </div>
          <div className="p-3 flex items-start gap-2.5">
            <span className="material-symbols-outlined text-secondary text-[18px]">info</span>
            <div>
              <span className="font-bold text-neutral-title">Unrated Feedback Filter</span>
              <p className="text-neutral-muted mt-0.5">Rider sessions without stars are excluded from mathematical mean calculations.</p>
            </div>
          </div>
        </div>
      </div>
      <div className="flex justify-end pt-2">
        <button className="px-4 py-2 rounded-full bg-secondary text-surface text-xs font-bold hover:bg-primary-hover transition" onClick={onClose}>
          Close Schema
        </button>
      </div>
    </ModalShell>
  )
}
