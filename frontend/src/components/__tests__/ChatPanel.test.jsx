import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { afterEach, describe, expect, it } from 'vitest'

import ChatPanel from '../ChatPanel'
import { server } from '../../test-setup'

const BASE = 'http://127.0.0.1:8000'

afterEach(cleanup)

function openPanel() {
  render(<ChatPanel cycle="2026-06-H1" />)
  fireEvent.click(screen.getByRole('button', { name: /ask actuate/i }))
  return screen.getByRole('textbox', { name: /operational question/i })
}

describe('ChatPanel', () => {
  it('submits the active cycle and renders narrative, rows, SQL, and sources', async () => {
    let requestBody
    server.use(
      http.post(`${BASE}/ask`, async ({ request }) => {
        requestBody = await request.json()
        return HttpResponse.json({
          sql: 'SELECT vendor_kpi.vendor LIMIT 50',
          rows: [{ vendor: 'Vendor A', ota_pct: 91.2 }],
          narrative: 'Vendor A needs attention.',
          grounded_from: { marts: ['vendor_kpi'], cycle: '2026-06-H1' },
        })
      }),
    )
    const input = openPanel()
    expect(screen.getByRole('dialog')).toHaveClass('sm:right-0')
    fireEvent.change(input, { target: { value: 'show OTA by vendor' } })
    fireEvent.click(screen.getByRole('button', { name: /^send$/i }))
    expect(await screen.findByText('Vendor A needs attention.')).toBeInTheDocument()
    expect(screen.getByText('Vendor A')).toBeInTheDocument()
    expect(screen.getByText('Sources')).toBeInTheDocument()
    fireEvent.click(screen.getByText('SQL'))
    expect(screen.getByText('SELECT vendor_kpi.vendor LIMIT 50')).toBeInTheDocument()
    expect(requestBody).toEqual({ question: 'show OTA by vendor', cycle: '2026-06-H1' })
  })

  it('renders the unsupported-intent state', async () => {
    server.use(http.post(`${BASE}/ask`, () => HttpResponse.json({ detail: 'unsupported question', supported_intents: ['ota_by_vendor'] }, { status: 422 })))
    const input = openPanel()
    fireEvent.change(input, { target: { value: 'show something else' } })
    fireEvent.click(screen.getByRole('button', { name: /^send$/i }))
    expect(await screen.findByText(/supported operational question/i)).toBeInTheDocument()
    expect(screen.getByText('ota_by_vendor')).toBeInTheDocument()
  })

  it('renders loading and network-error states', async () => {
    server.use(http.post(`${BASE}/ask`, () => HttpResponse.error()))
    const input = openPanel()
    fireEvent.change(input, { target: { value: 'show OTA by vendor' } })
    fireEvent.click(screen.getByRole('button', { name: /^send$/i }))
    expect(screen.getByText(/thinking/i)).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText(/could not reach actuate/i)).toBeInTheDocument())
  })
})
