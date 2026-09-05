import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from '../App'
import { server } from '../test-setup'

import briefing from '../../../stories/05-brief-ui/sample-briefing.json'
import insights from '../../../stories/06-dashboard-ui/sample-insights.json'
import overview from '../../../stories/06-dashboard-ui/sample-overview.json'
import vendors from '../../../stories/06-dashboard-ui/sample-vendors.json'

const BASE = 'http://127.0.0.1:8000'

function installHandlers(postHandler) {
  server.use(
    http.get(`${BASE}/briefing`, () => HttpResponse.json(briefing)),
    http.get(`${BASE}/actions`, () => HttpResponse.json({ data: briefing.data.actions_top3, warning: null })),
    http.get(`${BASE}/overview`, () => HttpResponse.json(overview)),
    http.get(`${BASE}/insights`, () => HttpResponse.json(insights)),
    http.get(`${BASE}/vendors`, () => HttpResponse.json(vendors)),
    http.post(`${BASE}/actions/:id/ack`, postHandler)
  )
}

beforeEach(() => {
  window.history.replaceState({}, '', '/?cycle=2026-06-H1')
})
afterEach(cleanup)

describe('ack and copy flows', () => {
  it('optimistically acknowledges an action, sends the fixed actor, and keeps it acked', async () => {
    let captured
    let release
    installHandlers(async ({ request }) => {
      captured = await request.json()
      await new Promise((resolve) => { release = resolve })
      return HttpResponse.json({ id: 'ack_vs_sla_2026_06_h1_all', status: 'acked', actor: 'Transport Manager', acked_at: 'now' })
    })
    render(<App />)
    await screen.findAllByText('96.9%')
    fireEvent.click(screen.getAllByRole('button', { name: 'Approve' })[0])
    expect((await screen.findAllByText('Acknowledging...')).length).toBeGreaterThan(0)
    expect(captured).toEqual({ actor: 'Transport Manager' })
    release()
    await waitFor(() => expect(screen.getByText('View audit')).toBeInTheDocument())
  })

  it('rolls back on an ack failure and shows the backend message', async () => {
    installHandlers(() => HttpResponse.json({ detail: 'unknown action id' }, { status: 404 }))
    render(<App />)
    await screen.findAllByText('96.9%')
    fireEvent.click(screen.getAllByRole('button', { name: 'Approve' })[0])
    expect(await screen.findByText('unknown action id')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Approve' }).length).toBeGreaterThan(0)
  })

  it('copies the exact API copy_for_vendor value', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } })
    installHandlers(() => HttpResponse.json({ id: 'ack_vs_sla_2026_06_h1_all', status: 'acked', actor: 'Transport Manager', acked_at: 'now' }))
    render(<App />)
    await screen.findAllByText('96.9%')
    fireEvent.click(screen.getAllByTitle('Copy for Vendor')[0])
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(briefing.data.actions_top3[0].copy_for_vendor))
  })
})
