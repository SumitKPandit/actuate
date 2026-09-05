import React from 'react'

export default function Header({ cycle, cycles, onCycleChange }) {
  const cycleOptions = cycles?.length ? cycles : [cycle]

  return (
    <header className="fixed top-0 left-0 right-0 w-full z-50 bg-surface border-b border-border-light shadow-sm">
      <div className="h-16 w-full px-6 flex items-center justify-between gap-4">
        <div className="flex items-center gap-6 shrink-0">
          <div className="flex items-center gap-3">
            <span className="font-bold text-lg text-secondary tracking-tight">ACTUATE</span>
          </div>
          <div className="h-4 w-px bg-border-light hidden md:block"></div>
          <div className="hidden sm:flex items-center gap-1.5 text-neutral-title font-semibold text-sm">
            <span className="material-symbols-outlined text-secondary text-[18px]">space_dashboard</span>
            <span>Operations Brief</span>
          </div>
        </div>
        <div className="flex items-center gap-3 overflow-x-auto justify-end width-[50px]">
          <div className="flex items-center gap-1.5">
            <div className="flex items-center bg-surface-panel border border-border-light px-2.5 py-1 rounded-full">
              <span className="text-[11px] font-semibold text-neutral-muted mr-1.5 uppercase tracking-wider">Cycle:</span>
              <select
                aria-label="Cycle"
                value={cycle}
                onChange={(event) => onCycleChange(event.target.value)}
                className="bg-transparent text-xs font-semibold text-neutral-body outline-none cursor-pointer"
              >
                {cycleOptions.map((option) => <option key={option}>{option}</option>)}
              </select>
            </div>
            <div className="flex items-center bg-surface-panel border border-border-light px-2.5 py-1 rounded-full">
              <span className="text-[11px] font-semibold text-neutral-muted mr-1.5 uppercase tracking-wider">Office:</span>
              <select className="bg-transparent text-xs font-semibold text-neutral-body outline-none cursor-pointer">
                <option>All Hubs</option>
                <option>North Hub</option>
                <option>South Campus</option>
              </select>
            </div>
            <div className="flex items-center bg-surface-panel border border-border-light px-2.5 py-1 rounded-full">
              <span className="text-[11px] font-semibold text-neutral-muted mr-1.5 uppercase tracking-wider">Vendor:</span>
              <select className="bg-transparent text-xs font-semibold text-neutral-body outline-none cursor-pointer">
                <option>All</option>
                <option>MoveInSync</option>
                <option>FleetOps</option>
              </select>
            </div>
            <div className="hidden lg:flex items-center bg-surface-panel border border-border-light px-2.5 py-1 rounded-full">
              <span className="text-[11px] font-semibold text-neutral-muted mr-1.5 uppercase tracking-wider">BU:</span>
              <select className="bg-transparent text-xs font-semibold text-neutral-body outline-none cursor-pointer">
                <option>All</option>
                <option>Engineering</option>
                <option>Operations</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </header>
  )
}
