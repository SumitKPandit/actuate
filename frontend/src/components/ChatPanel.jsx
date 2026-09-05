import React from 'react'

export default function ChatPanel() {
  return (
    <div className="xl:col-span-4 flex flex-col gap-4 sticky top-20">
      <div className="bg-surface rounded-lg border border-border-light shadow-sm flex flex-col h-[calc(100vh-6rem)] overflow-hidden">
        <div className="p-4 bg-surface border-b border-border-light flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-secondary text-surface flex items-center justify-center font-bold shadow-sm">
              <span className="material-symbols-outlined text-[18px]">smart_toy</span>
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-1.5">
                <span className="text-sm font-bold text-neutral-title">ASK ACTUATE</span>
                <span className="h-2 w-2 rounded-full bg-neutral-muted"></span>
              </div>
              <span className="text-[11px] text-neutral-muted">Mobility Ops Co-pilot</span>
            </div>
          </div>
          <span className="text-[11px] text-neutral-muted font-bold bg-surface-panel border border-border-light px-2.5 py-1 rounded-full">Story 07</span>
        </div>
        <div className="flex-1 p-4 flex items-center justify-center">
          <div className="bg-surface-panel p-5 rounded-lg border border-border-light text-center max-w-sm">
            <span className="material-symbols-outlined text-secondary text-[28px]">lock</span>
            <h3 className="text-sm font-bold text-neutral-title mt-2">Ask lands in Story 07</h3>
            <p className="text-xs text-neutral-muted leading-relaxed mt-1">Chat and narration are disabled until the Q&amp;A API is delivered.</p>
          </div>
        </div>
        <div className="p-3.5 bg-surface border-t border-border-light">
          <div className="relative flex items-center">
            <input disabled className="w-full bg-surface-panel text-neutral-title placeholder:text-neutral-muted rounded-full pl-4 pr-20 py-2 text-xs outline-none border border-border-light opacity-60" placeholder="Ask a follow-up…" />
            <button disabled className="absolute right-1 px-4 py-1.5 rounded-full bg-neutral-muted text-surface text-xs font-bold opacity-60 flex items-center gap-1">
              <span>Send</span>
              <span className="material-symbols-outlined text-[14px]">arrow_upward</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
