import React, { useState } from 'react'

import { fmtKpiValue, fmtShare } from '../lib/adapters'
import { useVendors } from '../lib/useVendors'

const SORTS = [
  ['ota', 'OTA'],
  ['cost', 'Cost'],
  ['alerts', 'Alerts'],
  ['csat', 'CSAT']
]

function numberText(value) {
  return typeof value === 'number' && Number.isFinite(value) ? value.toLocaleString('en-IN') : '—'
}

function VendorCell({ row, selected, onSelect }) {
  const name = row.vendor || '—'
  return (
    <button
      type="button"
      className={`w-full text-left px-3 py-3 transition ${selected ? 'bg-blue-50/70' : 'hover:bg-surface-panel'}`}
      onClick={(event) => {
        event.stopPropagation()
        if (row.vendor) onSelect(row.vendor)
      }}
    >
      <span className="font-semibold text-neutral-title block">{name}</span>
      {(row.zero_km_count != null || row.unslabbed_count != null) && (
        <span className="text-[11px] text-neutral-muted block mt-0.5">Zero-km: {numberText(row.zero_km_count)} | Unslabbed: {numberText(row.unslabbed_count)}</span>
      )}
    </button>
  )
}

export default function VendorTable({ cycle, selectedVendor, onSelectVendor }) {
  const [sort, setSort] = useState('ota')
  const { data, warning, loading, error } = useVendors(cycle, sort)

  const sortError = error?.body?.allowed ? `Invalid vendor sort. Allowed: ${error.body.allowed.join(', ')}` : error?.message

  return (
    <section className="flex flex-col gap-4" aria-label="Vendor performance">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-bold text-neutral-title tracking-tight">VENDOR PERFORMANCE</h3>
          <span className="text-xs text-neutral-muted">Server-ranked rows for {cycle}.</span>
        </div>
        <div className="flex items-center gap-1.5 overflow-x-auto">
          <span className="text-[11px] font-bold text-neutral-muted uppercase">Sort:</span>
          {SORTS.map(([key, label]) => (
            <button
              type="button"
              key={key}
              aria-pressed={sort === key}
              className={`px-3 py-1 rounded-full text-xs font-bold border transition ${sort === key ? 'bg-secondary text-surface border-secondary' : 'bg-surface text-neutral-muted border-border-light hover:border-secondary'}`}
              onClick={() => setSort(key)}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {warning && <div className="bg-warning-bg border border-warning/30 text-warning rounded-lg px-4 py-3 text-xs font-semibold">{warning}</div>}
      {loading && (
        <div className="bg-surface border border-border-light rounded-lg p-5 animate-pulse text-xs text-neutral-muted">Loading vendor performance…</div>
      )}
      {!loading && error && <div role="alert" className="bg-error-bg border border-error/30 text-error rounded-lg px-4 py-3 text-xs font-semibold">{sortError || 'Unable to load vendors.'}</div>}
      {!loading && !error && data && data.length === 0 && <div className="bg-surface border border-border-light rounded-lg p-5 text-xs text-neutral-muted">No vendor data for this cycle.</div>}
      {!loading && !error && Array.isArray(data) && data.length > 0 && (
        <div className="bg-surface border border-border-light rounded-lg overflow-x-auto shadow-sm">
          <table className="w-full text-left text-xs min-w-[900px]">
            <thead className="bg-surface-panel border-b border-border-light text-[11px] uppercase tracking-wider text-neutral-muted">
              <tr>
                <th className="px-3 py-3 font-bold">Vendor</th>
                <th className="px-3 py-3 font-bold">Peer rank</th>
                <th className="px-3 py-3 font-bold">Trips</th>
                <th className="px-3 py-3 font-bold">OTA</th>
                <th className="px-3 py-3 font-bold">Cost / trip</th>
                <th className="px-3 py-3 font-bold">Alerts / 1k</th>
                <th className="px-3 py-3 font-bold">CSAT</th>
                <th className="px-3 py-3 font-bold">Contribution</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-light">
              {data.map((row, index) => {
                const selected = selectedVendor === row.vendor
                return (
                  <tr
                    key={`${row.vendor || 'vendor'}:${index}`}
                    className={`${selected ? 'bg-blue-50/40' : ''} cursor-pointer`}
                    data-testid={`vendor-row-${index}`}
                    onClick={() => row.vendor && onSelectVendor(row.vendor)}
                  >
                    <td className="p-0"><VendorCell row={row} selected={selected} onSelect={onSelectVendor} /></td>
                    <td className="px-3 py-3 font-semibold text-neutral-body">{numberText(row.peer_rank)}</td>
                    <td className="px-3 py-3 text-neutral-body">{numberText(row.trips)}</td>
                    <td className="px-3 py-3 text-neutral-body">{fmtKpiValue('ota', row.ota_pct)}</td>
                    <td className="px-3 py-3 text-neutral-body">{fmtKpiValue('cost', row.cost_per_trip)}</td>
                    <td className="px-3 py-3 text-neutral-body">{typeof row.alert_rate_per_1k === 'number' ? row.alert_rate_per_1k.toLocaleString('en-IN', { maximumFractionDigits: 2 }) : '—'}</td>
                    <td className="px-3 py-3 text-neutral-body">{fmtKpiValue('csat', row.csat_avg)}</td>
                    <td className="px-3 py-3 text-neutral-body">{fmtShare(row.contribution_share)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
