import React from 'react'

export default function RecommendedActions({ actions, approvedMap, pendingCount, onApprove, onOpenSafety, onCopyVendor, onViewAudit }) {
  return (
    <div className="flex flex-col gap-4 pt-2">
      <div className="flex items-center justify-between">
        <div className="flex flex-col">
          <h3 className="text-lg font-bold text-neutral-title tracking-tight">RECOMMENDED ACTIONS</h3>
          <span className="text-xs text-neutral-muted">Decisions ready for human approval.</span>
        </div>
        <span className="text-xs font-bold text-primary bg-success-bg border border-primary/20 px-3 py-1 rounded-full">
          {pendingCount} Pending Operational Approvals
        </span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {actions.map((action) => {
          const approved = !!approvedMap[action.id]
          return (
            <div key={action.id} className="bg-surface p-4 rounded-lg border border-border-light shadow-sm flex flex-col justify-between gap-4">
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between">
                  <span
                    className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border ${
                      approved ? 'bg-success-bg text-primary border-primary/20' : 'bg-surface-panel border-border-light text-neutral-muted'
                    }`}
                  >
                    {approved ? '✓ ACKED' : 'PROPOSED'}
                  </span>
                  <span className={`text-xs font-semibold ${action.ownerTone === 'error' ? 'text-error' : 'text-secondary'}`}>
                    Owner: {action.owner}
                  </span>
                </div>
                <h4 className="text-sm font-bold text-neutral-title mt-1">{action.title}</h4>
                <p className="text-xs text-neutral-muted leading-relaxed">{action.reason}</p>
                {approved && (
                  <span className="text-[11px] text-primary font-medium">Acknowledged just now (Operator: Transport Manager)</span>
                )}
              </div>
              <div className="flex items-center gap-2 pt-2 border-t border-border-light">
                <button
                  className={
                    approved
                      ? 'flex-1 py-2 rounded-full bg-surface-panel border border-border-light text-secondary text-xs font-bold hover:bg-surface transition text-center shadow-xs cursor-pointer flex items-center justify-center gap-1'
                      : 'flex-1 py-2 rounded-full bg-primary text-surface hover:bg-primary-hover transition text-xs font-bold text-center shadow-sm'
                  }
                  onClick={() => (approved ? onViewAudit(action.title) : onApprove(action.id, action.title))}
                >
                  {approved && <span className="material-symbols-outlined text-[15px] text-primary">check_circle</span>}
                  {approved ? 'View audit' : 'Approve'}
                </button>
                {action.hasCopy && (
                  <button
                    className="px-3 py-2 rounded-full bg-surface border border-border-light hover:border-neutral-muted text-neutral-body text-xs transition shadow-sm"
                    onClick={() => onCopyVendor(action.vendorName, action.vendorOta)}
                    title="Copy for Vendor"
                  >
                    <span className="material-symbols-outlined text-[16px] block">content_copy</span>
                  </button>
                )}
                {action.hasReview && (
                  <button
                    className="px-4 py-2 rounded-full bg-surface border border-border-light hover:border-neutral-muted text-neutral-body text-xs font-semibold transition shadow-sm"
                    onClick={onOpenSafety}
                  >
                    Review
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
