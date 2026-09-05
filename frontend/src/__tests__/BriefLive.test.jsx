import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import App from '../App'
import { server } from '../test-setup'

import briefing from '../../../stories/05-brief-ui/sample-briefing.json'
import insights from '../../../stories/06-dashboard-ui/sample-insights.json'
import overview from '../../../stories/06-dashboard-ui/sample-overview.json'
import vendors from '../../../stories/06-dashboard-ui/sample-vendors.json'

const BASE = 'http://127.0.0.1:8000'

function installHandlers({ briefingEnvelope = briefing, failPath } = {}) {
  server.use(
    http.get(`${BASE}/briefing`, ({ request }) => failPath === '/briefing' ? HttpResponse.json({ detail: 'briefing unavailable' }, { status: 500 }) : HttpResponse.json(briefingEnvelope)),
    http.get(`${BASE}/actions`, () => failPath === '/actions' ? HttpResponse.json({ detail: 'actions unavailable' }, { status: 500 }) : HttpResponse.json({ data: briefing.data.actions_top3, warning: null })),
    http.get(`${BASE}/overview`, () => failPath === '/overview' ? HttpResponse.json({ detail: 'overview unavailable' }, { status: 500 }) : HttpResponse.json(overview)),
    http.get(`${BASE}/insights`, () => HttpResponse.json(insights)),
    http.get(`${BASE}/vendors`, () => HttpResponse.json(vendors))
  )
}

beforeEach(() => {
  window.history.replaceState({}, '', '/?cycle=2026-06-H1')
})
afterEach(cleanup)

describe('live brief', () => {
  it('renders fixture KPI, alert, action, and vendor values', async () => {
    installHandlers()
    render(<App />)

    expect((await screen.findAllByText('96.9%')).length).toBeGreaterThan(0)
    expect(screen.getByText('252', { exact: true })).toBeInTheDocument()
    expect(screen.getAllByText('4.8', { exact: true }).length).toBeGreaterThan(0)
    expect(screen.getAllByText('Acknowledge open Sev-1s + escort audit').length).toBeGreaterThan(0)
    expect(screen.getByText('VENDOR PERFORMANCE')).toBeInTheDocument()
  })

  it('renders a fired trigger and no banner for an empty trigger list', async () => {
    const triggered = { ...briefing, data: { ...briefing.data, triggers: [{ fired: true, name: 'OTA threshold', scope: { vendor: 'Vendor X' } }] } }
    installHandlers({ briefingEnvelope: triggered })
    render(<App />)
    expect(await screen.findByText('OTA threshold')).toBeInTheDocument()
    expect(screen.getByText('Scope: Vendor X')).toBeInTheDocument()

    cleanup()
    window.history.replaceState({}, '', '/?cycle=2026-06-H1')
    installHandlers({ briefingEnvelope: { ...briefing, data: { ...briefing.data, triggers: [] } } })
    render(<App />)
    await waitFor(() => expect(screen.queryByText('OTA threshold')).not.toBeInTheDocument())
  })

  it('renders the empty-marts warning and API errors as surface states', async () => {
    installHandlers({ briefingEnvelope: { data: null, warning: 'marts empty — run ingest' } })
    render(<App />)
    expect(await screen.findByText('marts empty — run ingest')).toBeInTheDocument()

    window.history.replaceState({}, '', '/?cycle=2026-06-H1')
    installHandlers({ failPath: '/overview' })
    render(<App />)
    expect(await screen.findByRole('alert')).toHaveTextContent('overview unavailable')
  })

  it('sends the active cycle on all cycle-dependent GET requests', async () => {
    const cycles = []
    server.use(
      http.get(`${BASE}/briefing`, ({ request }) => { cycles.push(new URL(request.url).searchParams.get('cycle')); return HttpResponse.json(briefing) }),
      http.get(`${BASE}/actions`, ({ request }) => { cycles.push(new URL(request.url).searchParams.get('cycle')); return HttpResponse.json({ data: briefing.data.actions_top3, warning: null }) }),
      http.get(`${BASE}/overview`, ({ request }) => { cycles.push(new URL(request.url).searchParams.get('cycle')); return HttpResponse.json(overview) }),
      http.get(`${BASE}/insights`, ({ request }) => { cycles.push(new URL(request.url).searchParams.get('cycle')); return HttpResponse.json(insights) }),
      http.get(`${BASE}/vendors`, ({ request }) => { cycles.push(new URL(request.url).searchParams.get('cycle')); return HttpResponse.json(vendors) })
    )
    render(<App />)
    await screen.findAllByText('96.9%')
    expect(cycles).toEqual(expect.arrayContaining(['2026-06-H1']))
    expect(cycles).not.toContain(null)
  })
})
