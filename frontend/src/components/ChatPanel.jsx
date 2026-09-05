import React, { useEffect, useRef, useState } from 'react'
import { suggestionPills } from '../data'

function OTAResponseBody({ onCopyVendor }) {
  const [sqlOpen, setSqlOpen] = useState(false)
  return (
    <div className="bg-surface-panel p-3.5 rounded-lg rounded-tl-none border border-border-light flex flex-col gap-3 text-neutral-body">
      <p className="text-xs leading-relaxed">
        OTA fell to <span className="font-bold text-error">93.0%</span>, which
        is 2.0pp below the{' '}
        <span className="font-semibold text-neutral-title">95.0% SLA</span>.{' '}
        <span className="font-bold text-secondary">Vendor X</span> contributed{' '}
        <span className="font-bold text-error">42% of the delay gap</span>,
        followed by{' '}
        <span className="font-semibold text-neutral-title">Vendor Y</span> at
        21%.
      </p>
      <div className="overflow-hidden rounded-lg border border-border-light bg-surface">
        <table className="w-full text-left text-xs">
          <thead className="bg-surface-panel text-[11px] font-bold text-neutral-muted uppercase border-b border-border-light">
            <tr>
              <th className="px-3 py-2">Vendor</th>
              <th className="px-3 py-2">OTA</th>
              <th className="px-3 py-2">Contribution</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-light font-mono text-[11px]">
            <tr>
              <td className="px-3 py-2 font-semibold text-neutral-title">
                Vendor X
              </td>
              <td className="px-3 py-2 text-error font-bold">91.2%</td>
              <td className="px-3 py-2 text-error font-semibold">42%</td>
            </tr>
            <tr>
              <td className="px-3 py-2 font-semibold text-neutral-title">
                Vendor Y
              </td>
              <td className="px-3 py-2 text-neutral-body">93.1%</td>
              <td className="px-3 py-2 text-neutral-body">21%</td>
            </tr>
            <tr>
              <td className="px-3 py-2 font-semibold text-neutral-title">
                Others (FleetOps)
              </td>
              <td className="px-3 py-2 text-primary font-bold">96.4%</td>
              <td className="px-3 py-2 text-neutral-muted">37%</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div className="flex flex-col gap-1 pt-1 border-t border-border-light">
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-neutral-muted flex items-center gap-1">
            <span className="material-symbols-outlined text-[14px] text-primary">
              verified
            </span>
            Grounded from:{' '}
            <code className="font-mono text-neutral-title font-medium">
              daily_kpi, vendor_kpi, insight_cache
            </code>
          </span>
          <button
            className="text-[11px] text-secondary font-semibold hover:underline"
            onClick={() => setSqlOpen((v) => !v)}
          >
            {sqlOpen ? 'Hide query' : 'View query'}
          </button>
        </div>
        {sqlOpen && (
          <div className="mt-1.5 bg-neutral-title text-surface p-3 rounded-lg font-mono text-[11px] overflow-x-auto">
            <pre className="text-emerald-400">{`SELECT vendor_name, ota, contribution_share
FROM vendor_kpi
WHERE cycle = '2026-06-H1'
LIMIT 50;`}</pre>
          </div>
        )}
      </div>
      <div className="flex items-center justify-between pt-1">
        <span className="text-[11px] text-neutral-muted">
          Recommended Next Step:
        </span>
        <button
          className="px-3 py-1 rounded-full bg-surface border border-secondary/30 text-secondary hover:bg-secondary hover:text-surface text-xs font-bold transition flex items-center gap-1 shadow-xs"
          onClick={() => onCopyVendor('Vendor X', '91.2%')}
        >
          <span className="material-symbols-outlined text-[14px]">send</span>
          Draft Vendor X Notice
        </button>
      </div>
    </div>
  )
}

function RoutesResponseBody() {
  const [sqlOpen, setSqlOpen] = useState(false)
  return (
    <div className="bg-surface-panel p-3.5 rounded-lg rounded-tl-none border border-border-light flex flex-col gap-3 text-neutral-body">
      <p className="text-xs leading-relaxed">
        <span className="font-bold text-neutral-title">Route 42</span> and{' '}
        <span className="font-bold text-neutral-title">Route 18</span> account
        for the largest share of delayed trips associated with Vendor X.
      </p>
      <div className="overflow-hidden rounded-lg border border-border-light bg-surface">
        <table className="w-full text-left text-xs">
          <thead className="bg-surface-panel text-[11px] font-bold text-neutral-muted uppercase border-b border-border-light">
            <tr>
              <th className="px-3 py-2">Route</th>
              <th className="px-3 py-2">Trips</th>
              <th className="px-3 py-2">OTA</th>
              <th className="px-3 py-2">Avg Delay</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-light font-mono text-[11px]">
            <tr>
              <td className="px-3 py-2 font-semibold text-neutral-title">
                Route 42
              </td>
              <td className="px-3 py-2">1,284</td>
              <td className="px-3 py-2 text-error font-bold">89.4%</td>
              <td className="px-3 py-2 text-error">4.8 min</td>
            </tr>
            <tr>
              <td className="px-3 py-2 font-semibold text-neutral-title">
                Route 18
              </td>
              <td className="px-3 py-2">932</td>
              <td className="px-3 py-2 text-warning font-bold">91.1%</td>
              <td className="px-3 py-2 text-neutral-body">3.7 min</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div className="flex flex-col gap-1 pt-1 border-t border-border-light">
        <div className="flex items-center justify-between">
          <span className="text-[11px] text-neutral-muted flex items-center gap-1">
            <span className="material-symbols-outlined text-[14px] text-primary">
              verified
            </span>
            Grounded from:{' '}
            <code className="font-mono text-neutral-title font-medium">
              mart.route_telemetry, trip_corridors
            </code>
          </span>
          <button
            className="text-[11px] text-secondary font-semibold hover:underline"
            onClick={() => setSqlOpen((v) => !v)}
          >
            {sqlOpen ? 'Hide query' : 'View query'}
          </button>
        </div>
        {sqlOpen && (
          <div className="mt-1.5 bg-neutral-title text-surface p-3 rounded-lg font-mono text-[11px] overflow-x-auto">
            <pre className="text-emerald-400">{`SELECT route_id, count(trip_id) as trips, ota_rate, avg_delay_mins
FROM mart.route_telemetry
WHERE vendor = 'Vendor X' AND ota_rate < 0.95
LIMIT 50;`}</pre>
          </div>
        )}
      </div>
    </div>
  )
}

function Sev1ResponseBody({ unackCount, onOpenSafety }) {
  return (
    <div className="bg-surface-panel p-3.5 rounded-lg rounded-tl-none border border-border-light flex flex-col gap-2.5 text-neutral-body">
      <p className="text-xs leading-relaxed">
        Currently tracking{' '}
        <span className="font-bold text-error">18 Open Sev-1 alerts</span>{' '}
        across central dispatch.{' '}
        <span className="font-bold text-error">
          {unackCount} incidents are unacknowledged
        </span>{' '}
        past the 30-minute operational threshold.
      </p>
      <div className="flex items-center gap-2 pt-1">
        <button
          onClick={onOpenSafety}
          className="px-3.5 py-1.5 rounded-full bg-secondary text-surface text-xs font-bold hover:bg-primary-hover transition"
        >
          Open Safety Incident Desk
        </button>
      </div>
    </div>
  )
}

function CostResponseBody() {
  return (
    <div className="bg-surface-panel p-3.5 rounded-lg rounded-tl-none border border-border-light flex flex-col gap-2 text-neutral-body">
      <p className="text-xs leading-relaxed">
        <span className="font-bold text-secondary">Vendor Y</span> has 14
        extreme billing lines exceeding the ₹16,000 threshold (+3.2σ outlier vs
        baseline ₹1,236). Recommend placing a hold on unslabbed km lines.
      </p>
    </div>
  )
}

function NoShowResponseBody() {
  return (
    <div className="bg-surface-panel p-3.5 rounded-lg rounded-tl-none border border-border-light flex flex-col gap-2 text-neutral-body">
      <p className="text-xs leading-relaxed">
        <span className="font-bold text-neutral-title">
          Office B (Tech Hub)
        </span>{' '}
        has the highest no-show rate at{' '}
        <span className="font-bold text-warning">4.1%</span> (vs corporate peer
        average 2.3%). Concentrated along late evening shifts.
      </p>
    </div>
  )
}

function FallbackResponseBody({ query }) {
  return (
    <div className="bg-error-bg/60 border border-error/30 p-4 rounded-lg flex flex-col gap-2.5">
      <div className="flex items-center gap-1.5 text-error">
        <span className="material-symbols-outlined text-[18px]">
          error_outline
        </span>
        <span className="text-xs font-bold uppercase">
          422 — Intent Out of Scope
        </span>
      </div>
      <p className="text-xs text-neutral-body leading-relaxed">
        Actuate couldn't answer "{query}".
      </p>
      <div className="flex flex-col gap-1 bg-surface p-3 rounded-lg border border-border-light">
        <span className="text-[11px] font-bold text-neutral-muted uppercase">
          I can help with:
        </span>
        <ul className="text-xs text-neutral-body list-disc pl-4 space-y-0.5">
          <li>OTA by vendor or office</li>
          <li>Cost outliers</li>
          <li>Open Sev-1 alerts</li>
          <li>CSAT clusters</li>
          <li>No-show by shift or office</li>
        </ul>
      </div>
    </div>
  )
}

function classify(query) {
  const lower = query.toLowerCase()
  if (
    lower.includes('weather') ||
    lower.includes('driver phone') ||
    lower.includes('pii') ||
    lower.includes('joke')
  )
    return 'fallback'
  if (lower.includes('route') || lower.includes('corridor')) return 'routes'
  if (
    lower.includes('sev-1') ||
    lower.includes('safety') ||
    lower.includes('incident')
  )
    return 'sev1'
  if (lower.includes('cost') || lower.includes('outlier')) return 'cost'
  if (lower.includes('no-show') || lower.includes('office')) return 'noshow'
  return 'ota'
}

export default function ChatPanel({ unackCount, onOpenSafety, onCopyVendor }) {
  const [turns, setTurns] = useState([
    { type: 'ota-default', user: 'Why did OTA drop?', ts: '06:31 IST' },
  ])
  const [loading, setLoading] = useState(false)
  const [input, setInput] = useState('')
  const [fallbackPreview, setFallbackPreview] = useState(false)
  const streamRef = useRef(null)

  useEffect(() => {
    if (streamRef.current)
      streamRef.current.scrollTop = streamRef.current.scrollHeight
  }, [turns, loading, fallbackPreview])

  const submit = (query) => {
    const q = (query ?? input).trim()
    if (!q) return
    setFallbackPreview(false)
    setInput('')
    setTurns((t) => [...t, { type: 'user', text: q }])
    setLoading(true)
    setTimeout(() => {
      const kind = classify(q)
      setTurns((t) => [...t, { type: kind, query: q }])
      setLoading(false)
    }, 700)
  }

  const renderTurn = (turn, idx) => {
    if (turn.type === 'user') {
      return (
        <div className="flex justify-end" key={idx}>
          <div className="bg-secondary text-surface px-4 py-2 rounded-2xl rounded-tr-none max-w-[85%] text-xs shadow-sm font-medium">
            {turn.text}
          </div>
        </div>
      )
    }
    if (turn.type === 'ota-default') {
      return (
        <React.Fragment key={idx}>
          <div className="flex justify-end">
            <div className="bg-secondary text-surface px-4 py-2 rounded-2xl rounded-tr-none max-w-[85%] text-xs shadow-sm font-medium">
              {turn.user}
            </div>
          </div>
          <div className="flex flex-col gap-1.5 max-w-[95%]">
            <div className="flex items-center gap-1.5">
              <span className="text-[11px] font-bold text-secondary">
                ACTUATE CO-PILOT
              </span>
              <span className="text-[11px] text-neutral-muted">{turn.ts}</span>
            </div>
            <OTAResponseBody onCopyVendor={onCopyVendor} />
          </div>
        </React.Fragment>
      )
    }

    const bodies = {
      ota: <OTAResponseBody onCopyVendor={onCopyVendor} />,
      routes: <RoutesResponseBody />,
      sev1: (
        <Sev1ResponseBody unackCount={unackCount} onOpenSafety={onOpenSafety} />
      ),
      cost: <CostResponseBody />,
      noshow: <NoShowResponseBody />,
      fallback: <FallbackResponseBody query={turn.query} />,
    }

    if (turn.type === 'fallback') {
      return (
        <div className="flex flex-col gap-1.5 max-w-[95%]" key={idx}>
          {bodies.fallback}
        </div>
      )
    }

    return (
      <div className="flex flex-col gap-1.5 max-w-[95%]" key={idx}>
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] font-bold text-secondary">
            ACTUATE CO-PILOT
          </span>
          <span className="text-[11px] text-neutral-muted">Just now</span>
        </div>
        {bodies[turn.type]}
      </div>
    )
  }

  return (
    <div className="xl:col-span-4 flex flex-col gap-4 sticky top-20">
      <div className="bg-surface rounded-lg border border-border-light shadow-sm flex flex-col h-[calc(100vh-6rem)] overflow-hidden">
        <div className="p-4 bg-surface border-b border-border-light flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-secondary text-surface flex items-center justify-center font-bold shadow-sm">
              <span className="material-symbols-outlined text-[18px]">
                smart_toy
              </span>
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-1.5">
                <span className="text-sm font-bold text-neutral-title">
                  ASK ACTUATE
                </span>
                <span className="h-2 w-2 rounded-full bg-primary"></span>
              </div>
              <span className="text-[11px] text-neutral-muted">
                Mobility Ops Co-pilot
              </span>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <button
              className="text-[11px] px-2.5 py-1 rounded-full bg-surface-panel border border-border-light text-neutral-body hover:border-neutral-muted transition font-medium"
              onClick={() => setFallbackPreview((v) => !v)}
              title="Preview 422 Unhandled Intent State"
            >
              {fallbackPreview ? 'Return to Chat' : 'Preview 422 Mode'}
            </button>
            <span className="text-[11px] text-primary font-bold bg-success-bg border border-primary/20 px-2.5 py-1 rounded-full flex items-center gap-1">
              ● Mart-grounded
            </span>
          </div>
        </div>

        <div
          className="flex-1 p-4 overflow-y-auto flex flex-col gap-4"
          ref={streamRef}
        >
          {!fallbackPreview ? (
            <>
              <div className="bg-surface-panel p-3.5 rounded-lg border border-border-light flex flex-col gap-2">
                <span className="text-[11px] font-bold text-secondary uppercase tracking-wider">
                  Operations Synthesis
                </span>
                <p className="text-xs text-neutral-body leading-relaxed">
                  Your operation has{' '}
                  <span className="font-bold text-error">
                    5 priority exceptions
                  </span>
                  . I can explain what changed, identify root causes, and
                  prepare vendor communications.
                </p>
                <div className="flex flex-wrap gap-1.5 mt-1">
                  {suggestionPills.map((pill) => (
                    <button
                      key={pill}
                      className="text-[11px] bg-surface hover:border-secondary text-neutral-body border border-border-light px-2.5 py-1 rounded-full transition shadow-xs"
                      onClick={() => submit(pill)}
                    >
                      {pill}
                    </button>
                  ))}
                </div>
              </div>

              {turns.map(renderTurn)}

              {loading && (
                <div className="flex items-center gap-2 text-xs text-neutral-muted py-2 px-1">
                  <span className="material-symbols-outlined text-[16px] text-secondary animate-spin">
                    progress_activity
                  </span>
                  <span className="italic">
                    Actuate is analyzing operational data from marts...
                  </span>
                </div>
              )}
            </>
          ) : (
            <div className="flex flex-col gap-4">
              <div className="flex justify-end">
                <div className="bg-secondary text-surface px-4 py-2 rounded-2xl rounded-tr-none max-w-[85%] text-xs">
                  What is the driver's personal phone number on trip #8921?
                </div>
              </div>
              <div className="bg-error-bg/60 border border-error/30 p-4 rounded-lg flex flex-col gap-3">
                <div className="flex items-center gap-1.5 text-error">
                  <span className="material-symbols-outlined text-[18px]">
                    error_outline
                  </span>
                  <span className="text-xs font-bold uppercase">
                    422 — Intent Out of Scope
                  </span>
                </div>
                <p className="text-xs text-neutral-body leading-relaxed">
                  Actuate couldn't answer that question. I can help with:
                </p>
                <div className="flex flex-col gap-1 bg-surface p-3 rounded-lg border border-border-light">
                  <span className="text-[11px] font-bold text-neutral-muted uppercase">
                    I am grounded to answer:
                  </span>
                  <ul className="text-xs text-neutral-body list-disc pl-4 space-y-1">
                    <li>OTA by vendor or office</li>
                    <li>Cost outliers</li>
                    <li>Open Sev-1 alerts</li>
                    <li>CSAT clusters</li>
                    <li>No-show by shift or office</li>
                  </ul>
                </div>
                <button
                  className="self-start px-3 py-1.5 rounded-full bg-surface border border-border-light text-neutral-body text-xs font-medium hover:border-neutral-muted transition"
                  onClick={() => setFallbackPreview(false)}
                >
                  ← Return to active conversation
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="p-3.5 bg-surface border-t border-border-light flex flex-col gap-1.5">
          <div className="relative flex items-center">
            <input
              className="w-full bg-surface-panel text-neutral-title placeholder:text-neutral-muted rounded-full pl-4 pr-20 py-2 text-xs outline-none border border-border-light focus:border-secondary transition"
              placeholder="Ask a follow-up… (e.g. Which routes are affected?)"
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') submit()
              }}
            />
            <button
              className="absolute right-1 px-4 py-1.5 rounded-full bg-primary text-surface hover:bg-primary-hover text-xs font-bold transition flex items-center gap-1 shadow-xs"
              onClick={() => submit()}
            >
              <span>Send</span>
              <span className="material-symbols-outlined text-[14px]">
                arrow_upward
              </span>
            </button>
          </div>
          <div className="flex items-center justify-between px-1 text-[11px] text-neutral-muted">
            <span>Grounded answers only • ≤50 rows • No raw CSV</span>
            <span
              className="hover:text-secondary cursor-pointer font-medium"
              onClick={() => submit('Which routes are affected?')}
            >
              Hint: "Which routes are affected?"
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
