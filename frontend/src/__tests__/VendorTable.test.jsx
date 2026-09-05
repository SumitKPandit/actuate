import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import React from 'react'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import VendorTable from '../components/VendorTable'
import { server } from '../test-setup'

import vendors from '../../../stories/06-dashboard-ui/sample-vendors.json'

const BASE = 'http://127.0.0.1:8000'

function Harness() {
  const [selected, setSelected] = React.useState(new URLSearchParams(window.location.search).get('vendor'))
  return <VendorTable cycle="2026-06-H1" selectedVendor={selected} onSelectVendor={(vendor) => { const next = selected === vendor ? null : vendor; setSelected(next); const url = new URL(window.location.href); if (next) url.searchParams.set('vendor', next); else url.searchParams.delete('vendor'); window.history.replaceState({}, '', `${url.pathname}${url.search}`) }} />
}

beforeEach(() => {
  window.history.replaceState({}, '', '/?cycle=2026-06-H1')
})
afterEach(cleanup)

describe('vendor table', () => {
  it('requests ota by default, displays quality counts, and round-trips row selection', async () => {
    const sorts = []
    server.use(http.get(`${BASE}/vendors`, ({ request }) => { sorts.push(new URL(request.url).searchParams.get('sort')); return HttpResponse.json(vendors) }))
    render(<Harness />)
    expect(await screen.findByText('Meera Pavlov Travel')).toBeInTheDocument()
    expect(sorts[0]).toBe('ota')
    expect(screen.getByText('Zero-km: 5,344 | Unslabbed: 3')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Meera Pavlov Travel/ }))
    expect(new URLSearchParams(window.location.search).get('vendor')).toBe('Meera Pavlov Travel')
    expect(screen.getByTestId('vendor-row-0')).toHaveClass('bg-blue-50/40')
    fireEvent.click(screen.getByRole('button', { name: /Meera Pavlov Travel/ }))
    expect(new URLSearchParams(window.location.search).get('vendor')).toBeNull()
  })

  it('uses the server response for each supported sort', async () => {
    const rows = {
      ota: [{ vendor: 'OTA first', peer_rank: 1 }],
      cost: [{ vendor: 'Cost first', peer_rank: 1 }],
      alerts: [{ vendor: 'Alerts first', peer_rank: 1 }],
      csat: [{ vendor: 'CSAT first', peer_rank: 1 }]
    }
    const sorts = []
    server.use(http.get(`${BASE}/vendors`, ({ request }) => { const sort = new URL(request.url).searchParams.get('sort'); sorts.push(sort); return HttpResponse.json({ data: rows[sort], warning: null }) }))
    render(<Harness />)
    await screen.findByText('OTA first')
    for (const [label, name] of [['Cost', 'Cost first'], ['Alerts', 'Alerts first'], ['CSAT', 'CSAT first']]) {
      fireEvent.click(screen.getByRole('button', { name: label }))
      await waitFor(() => expect(screen.getByText(name)).toBeInTheDocument())
    }
    expect(sorts).toEqual(['ota', 'cost', 'alerts', 'csat'])
  })

  it('shows allowed sort values on a 422 and restores URL selection', async () => {
    window.history.replaceState({}, '', '/?cycle=2026-06-H1&vendor=Selected%20Vendor')
    server.use(http.get(`${BASE}/vendors`, () => HttpResponse.json({ detail: 'invalid sort', allowed: ['ota', 'cost', 'alerts', 'csat'] }, { status: 422 })))
    render(<Harness />)
    expect(await screen.findByRole('alert')).toHaveTextContent('ota, cost, alerts, csat')
  })
})
