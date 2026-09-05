import React from 'react'

export default function DataQualityBar({ onOpen }) {
  return (
    <div className="bg-surface border border-border-light rounded-lg p-3.5 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
      <div className="flex items-center gap-3 cursor-pointer" onClick={onOpen}>
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-primary"></span>
          <span className="text-xs font-bold text-neutral-title">
            DATA QUALITY: 97.8% trusted
          </span>
        </div>
        <div className="h-3.5 w-px bg-border-light hidden sm:block"></div>
        <div className="flex items-center gap-1.5 text-neutral-muted text-xs overflow-x-auto py-0.5">
          <span className="bg-surface-panel border border-border-light px-2 py-0.5 rounded-full">
            Trip IDs normalized
          </span>
          <span>•</span>
          <span className="bg-surface-panel border border-border-light px-2 py-0.5 rounded-full">
            Zero-km bills retained
          </span>
          <span>•</span>
          <span className="bg-surface-panel border border-border-light px-2 py-0.5 rounded-full">
            UNSLABBED bills retained
          </span>
          <span>•</span>
          <span className="bg-surface-panel border border-border-light px-2 py-0.5 rounded-full">
            Unclassified severity
          </span>
          <span>•</span>
          <span className="bg-surface-panel border border-border-light px-2 py-0.5 rounded-full">
            Unrated feedback excluded from CSAT
          </span>
        </div>
      </div>
      <div className="flex items-center gap-3 shrink-0">
        <span className="text-[11px] text-neutral-muted">
          Missing value standard:{' '}
          <code className="font-mono font-bold text-neutral-title">—</code>{' '}
          (never 0)
        </span>
        <button
          className="text-[11px] font-bold text-secondary hover:underline"
          onClick={onOpen}
        >
          View schema
        </button>
      </div>
    </div>
  )
}
