import React from 'react'

export default function Toast({ toast }) {
  const visible = !!toast
  return (
    <div
      className={`fixed bottom-6 right-6 z-[60] transform transition-all duration-300 flex items-start gap-3 bg-neutral-title text-surface p-4 rounded-lg shadow-2xl max-w-md border border-neutral-muted/40 ${
        visible
          ? 'translate-y-0 opacity-100'
          : 'translate-y-20 opacity-0 pointer-events-none'
      }`}
    >
      <span className="material-symbols-outlined text-primary text-[20px] shrink-0">
        check_circle
      </span>
      <div className="flex flex-col gap-0.5 min-w-0">
        <span className="text-xs font-semibold text-surface">
          {toast?.title || ''}
        </span>
        <p className="text-xs text-neutral-muted leading-tight line-clamp-3 text-gray-200">
          {toast?.message || ''}
        </p>
      </div>
    </div>
  )
}
