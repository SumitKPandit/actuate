import { useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/mockup')({ component: MockupPage })

type Tab = 'brief' | 'dashboard'

const vendors = [
  {
    name: 'Sneha Travels',
    trips: 42000,
    ota: 91.2,
    cost: 1410,
    alert: 3.1,
    csat: 4.79,
    rank: 22,
    note: '68% of delay gap · 210 zero-km',
  },
  {
    name: 'Priya Mikhailov',
    trips: 38000,
    ota: 94.1,
    cost: 1620,
    alert: 1.8,
    csat: 4.91,
    rank: 15,
    note: 'UNSLABBED 340',
  },
  {
    name: 'CityRide',
    trips: 51000,
    ota: 96.2,
    cost: 1290,
    alert: 1.2,
    csat: 4.88,
    rank: 4,
    note: 'top peer',
  },
]

const kpis = [
  {
    label: 'OTA %',
    value: '93.0%',
    delta: '-2.0pp vs May',
    badge: 'Breach SLA 95%',
    bad: true,
  },
  {
    label: 'Avg delay + mix',
    value: '1.1 min',
    delta: 'traffic 52% · driver 28%',
    badge: 'peer #18/23',
    bad: false,
  },
  {
    label: 'No-show %',
    value: '0.8%',
    delta: '+0.2pp vs May',
    badge: 'office: Whitefield worst',
    bad: false,
  },
  {
    label: 'Cost / trip',
    value: '₹1,394',
    delta: '+₹58 · 3.1% zero-km',
    badge: 'cost/km ₹42',
    bad: true,
  },
  {
    label: 'Alerts / 1k',
    value: '2.4',
    delta: '656 Sev-1 · 8 unacked',
    badge: 'Breach ack SLA 30m',
    bad: true,
  },
  {
    label: 'CSAT',
    value: '4.85',
    delta: '1.2% low (<3)',
    badge: 'Trend flat',
    bad: false,
  },
]

function MockupPage() {
  const [tab, setTab] = useState<Tab>('brief')
  const [drawer, setDrawer] = useState(false)
  const [acked, setAcked] = useState<Record<string, boolean>>({})
  const [copied, setCopied] = useState(false)
  const [sort, setSort] = useState<'ota' | 'cost' | 'alerts' | 'csat'>('ota')

  const sorted = [...vendors].sort((a, b) => {
    if (sort === 'ota') return a.ota - b.ota
    if (sort === 'cost') return b.cost - a.cost
    if (sort === 'alerts') return b.alert - a.alert
    return a.csat - b.csat
  })

  return (
    <main className="page-wrap px-4 pb-24 pt-6">
      <section className="demo-alert-neutral demo-alert mb-4">
        <strong>Visual mockup only</strong> — static data from PLAN §2 (Jun:
        211k trips, OTA ~93%). No API calls. Real build: Stories 05–07.
      </section>

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <button
          className={`demo-button ${tab === 'brief' ? '' : 'demo-button-secondary'}`}
          onClick={() => setTab('brief')}
        >
          Brief
        </button>
        <button
          className={`demo-button ${tab === 'dashboard' ? '' : 'demo-button-secondary'}`}
          onClick={() => setTab('dashboard')}
        >
          Dashboard
        </button>
        <span className="demo-pill">cycle: Jun</span>
        <span className="demo-pill">generated 05-Jul 06:00</span>
        <span className="demo-pill">OTA SLA 95% · Ack 30m</span>
      </div>

      {tab === 'brief' ? (
        <div className="grid gap-8">
          <div className="demo-alert demo-alert-danger">
            <strong>TRIGGER: Sev-1 spike — BLR June-H2 (fired)</strong>
            <div className="mt-1 text-sm opacity-80">
              pull-proactive · from /briefing.triggers[] · hidden when empty
            </div>
          </div>

          <section className="island-shell rounded-lg p-4">
            <p className="island-kicker mb-2">HEADLINES — WHAT SLIPPED</p>
            <ul className="m-0 space-y-1 pl-5 text-base text-[#333333]">
              <li>OTA June 93.0% vs SLA 95% (-2.0pp vs May)</li>
              <li>2 vendors = 68% of delay gap (14.8k trips)</li>
              <li>Cost/trip ₹1,394 (+₹58, 3.1% zero-km bills)</li>
            </ul>
          </section>

          <section className="grid gap-8">
            <article className="demo-list-item">
              <div className="flex flex-wrap gap-2 items-center">
                <strong className="text-[#1F1F1F]">
                  OTA drop · Sneha Travels
                </strong>
                <span className="demo-pill demo-pill-danger">sev high</span>
                <span className="demo-pill">reach 8.2k trips</span>
              </div>
              <p className="demo-muted my-1 text-sm">
                91.2% vs 95% Δ-3.8pp · 2 vendors = 68% of gap
              </p>
              <p className="my-1 text-sm text-[#333333]">
                → Re-route / buffer → owner: vendor
              </p>
            </article>
            <article className="demo-list-item">
              <div className="flex flex-wrap gap-2 items-center">
                <strong className="text-[#1F1F1F]">
                  Cost outlier · Priya Mikhailov
                </strong>
                <span className="demo-pill demo-pill-info">sev med</span>
                <span className="demo-pill">reach 1.1k trips</span>
              </div>
              <p className="demo-muted my-1 text-sm">
                ₹1,620/trip vs ₹1,394 avg · UNSLABBED 340
              </p>
              <p className="my-1 text-sm text-[#333333]">
                → Hold bill + verify slab → owner: ops
              </p>
            </article>
          </section>

          <section className="island-shell flex flex-wrap items-center gap-3 rounded-lg p-4 text-sm text-[#333333]">
            <strong className="text-[#1F1F1F]">Safety:</strong>
            <span>12 open Sev-1 · 8 unacked · oldest 4h20m</span>
            <button
              className="demo-button demo-button-secondary !min-h-0 !px-5 !py-2.5 !text-sm"
              onClick={() => setTab('dashboard')}
            >
              View by vendor
            </button>
          </section>

          <section className="island-shell rounded-lg p-4">
            <p className="island-kicker mb-2">NEXT ACTIONS · TOP 3</p>
            {[
              {
                id: 'a1',
                text: 'Add standby cab — Whitefield',
                owner: 'ops',
                copy: 'Sneha Travels, OTA 91.2% in June (SLA 95%). Add buffer/standby.',
              },
              {
                id: 'a2',
                text: 'Escort audit — night shift BLR',
                owner: 'safety',
                copy: 'Night shift Sev-1 12 open. Audit escorts this week.',
              },
              {
                id: 'a3',
                text: 'Hold bill — Priya Mikhailov Jun-H2',
                owner: 'ops',
                copy: 'Priya Mikhailov ₹1,620/trip Jun. Hold + verify slab.',
              },
            ].map((a) => (
              <div
                key={a.id}
                className="demo-list-item mb-2 flex flex-wrap items-center gap-3"
              >
                <span className="text-sm text-[#333333]">
                  <strong className="text-[#1F1F1F]">{a.text}</strong> [
                  {a.owner}]
                </span>
                <span
                  className={`demo-pill ${acked[a.id] ? 'demo-pill-success' : ''}`}
                >
                  {acked[a.id] ? 'acked' : 'proposed'}
                </span>
                <button
                  className="demo-button demo-button-secondary !min-h-0 !px-5 !py-2.5 !text-sm"
                  onClick={() => {
                    setCopied(true)
                    setTimeout(() => setCopied(false), 1200)
                  }}
                >
                  Copy for vendor
                </button>
                <button
                  className="demo-button !min-h-0 !px-5 !py-2.5 !text-sm"
                  onClick={() => setAcked((s) => ({ ...s, [a.id]: !s[a.id] }))}
                >
                  {acked[a.id] ? 'Undo ack' : 'Ack'}
                </button>
              </div>
            ))}
            {copied && (
              <p className="text-sm text-[#43B02A]">
                Copied ≤500 chars (toast)
              </p>
            )}
          </section>
        </div>
      ) : (
        <div className="grid gap-8">
          <section className="grid gap-8 sm:grid-cols-3">
            {kpis.map((k) => (
              <article key={k.label} className="island-shell rounded-lg p-4">
                <p className="island-kicker">{k.label.toUpperCase()}</p>
                <p className="m-0 mt-1 text-[28px] leading-[34px] font-semibold text-[#1F1F1F]">
                  {k.value}
                </p>
                <p className="demo-muted my-1 text-sm">{k.delta}</p>
                <span
                  className={`demo-pill ${k.bad ? 'demo-pill-danger' : 'demo-pill-success'}`}
                >
                  {k.badge}
                </span>
              </article>
            ))}
          </section>

          <section className="demo-table-shell">
            <div className="flex flex-wrap items-center gap-2 border-b border-[#E5E7EB] bg-[#F7F8FA] p-3">
              <span className="text-sm font-semibold text-[#1F1F1F]">
                Vendors
              </span>
              {(['ota', 'cost', 'alerts', 'csat'] as const).map((k) => (
                <button
                  key={k}
                  className={`demo-button !min-h-0 !px-4 !py-2 !text-sm ${sort === k ? '' : 'demo-button-secondary'}`}
                  onClick={() => setSort(k)}
                >
                  sort:{k}
                </button>
              ))}
            </div>
            <table className="demo-table text-sm">
              <thead>
                <tr>
                  <th>vendor</th>
                  <th>trips</th>
                  <th>OTA</th>
                  <th>₹/trip</th>
                  <th>alt/1k</th>
                  <th>CSAT</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((v) => (
                  <tr key={v.name}>
                    <td>
                      <strong className="text-[#1F1F1F]">{v.name}</strong>
                      <br />
                      <span className="demo-muted">
                        {v.note} · rank #{v.rank}
                      </span>
                    </td>
                    <td>{(v.trips / 1000).toFixed(0)}k</td>
                    <td>{v.ota}%</td>
                    <td>₹{v.cost.toLocaleString('en-IN')}</td>
                    <td>{v.alert}</td>
                    <td>{v.csat}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </div>
      )}

      <button
        className="demo-button"
        style={{
          position: 'fixed',
          right: 16,
          bottom: 16,
          borderRadius: 30,
          padding: '15px 20px',
        }}
        onClick={() => setDrawer((d) => !d)}
      >
        Ask Actuate
      </button>

      {drawer && (
        <aside
          className="island-shell"
          style={{
            position: 'fixed',
            right: 12,
            bottom: 76,
            width: 'min(360px, calc(100vw - 24px))',
            borderRadius: 8,
            padding: 16,
            background: '#FFFFFF',
          }}
        >
          <div className="mb-2 flex items-center justify-between">
            <strong className="text-[#1F1F1F]">Ask Actuate</strong>
            <button
              className="demo-button demo-button-secondary !min-h-0 !px-4 !py-2 !text-sm"
              onClick={() => setDrawer(false)}
            >
              Close
            </button>
          </div>
          <div className="demo-list-item mb-2 text-sm">
            <strong>Q:</strong> Which vendor drove June OTA drop?
          </div>
          <div className="demo-list-item mb-2 text-sm">
            OTA June was 93% vs SLA 95%. Sneha drove 68% of the gap (2.1k/3.1k
            late trips).
          </div>
          <table className="demo-table mb-2 text-sm">
            <thead>
              <tr>
                <th>vendor</th>
                <th>late</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Sneha</td>
                <td>2.1k</td>
              </tr>
              <tr>
                <td>Priya</td>
                <td>0.6k</td>
              </tr>
            </tbody>
          </table>
          <details className="text-sm">
            <summary>SQL + sources</summary>
            <pre className="demo-code-block text-xs">
              SELECT vendor, COUNT(*) late FROM vendor_kpi WHERE cycle='2026-06'
              ORDER BY late DESC LIMIT 50{'\n'}-- grounded_from: vendor_kpi,
              cycle Jun
            </pre>
          </details>
          <input
            className="demo-input mt-2"
            placeholder="Ask about OTA, cost, Sev-1, CSAT, no-show…"
            disabled
          />
        </aside>
      )}
    </main>
  )
}
