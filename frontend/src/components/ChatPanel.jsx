import React, { useState } from 'react'

import { ApiError, ask } from '../lib/ops'

function valueLabel(value) {
  if (value === null || value === undefined) return '—'
  return typeof value === 'object' ? JSON.stringify(value) : String(value)
}

function resultTable(rows) {
  const visibleRows = rows.slice(0, 50)
  if (!visibleRows.length) return <p className="text-xs text-neutral-muted">No matching mart rows for this question.</p>
  const columns = [...new Set(visibleRows.flatMap((row) => Object.keys(row)))]
  return (
    <div className="overflow-x-auto rounded-lg border border-border-light">
      <table className="min-w-full text-left text-[11px]">
        <thead className="bg-surface-panel text-neutral-muted uppercase tracking-wide">
          <tr>{columns.map((column) => <th key={column} className="px-3 py-2 font-semibold">{column}</th>)}</tr>
        </thead>
        <tbody>
          {visibleRows.map((row, index) => (
            <tr key={index} className="border-t border-border-light text-neutral-body">
              {columns.map((column) => <td key={column} className="px-3 py-2 whitespace-nowrap">{valueLabel(row[column])}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function ChatPanel({ cycle }) {
  const [open, setOpen] = useState(false)
  const [question, setQuestion] = useState('')
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [unsupported, setUnsupported] = useState(null)

  const submit = async (event) => {
    event.preventDefault()
    const nextQuestion = question.trim()
    if (!nextQuestion || loading) return
    setLoading(true)
    setError(null)
    setUnsupported(null)
    try {
      const response = await ask(nextQuestion, cycle)
      setHistory((current) => [...current, { question: nextQuestion, response }].slice(-10))
      setQuestion('')
    } catch (nextError) {
      if (nextError instanceof ApiError && nextError.status === 422 && Array.isArray(nextError.body?.supported_intents)) {
        setUnsupported(nextError.body.supported_intents)
      } else {
        setError('Could not reach Actuate. Check the API connection and try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  const latest = history[history.length - 1]?.response
  return (
    <>
      {!open && <button
        type="button"
        aria-expanded={open}
        aria-label="Ask Actuate"
        onClick={() => setOpen(true)}
        className="fixed right-5 bottom-5 z-40 inline-flex items-center gap-2 rounded-full bg-secondary px-4 py-3 text-sm font-bold text-surface shadow-lg hover:bg-primary-hover"
      >
        <span className="material-symbols-outlined text-[18px]">chat</span>
        Ask Actuate
      </button>}
      {open && (
        <div className="fixed inset-0 z-50 bg-neutral-title/20" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && setOpen(false)}>
          <aside role="dialog" aria-label="Ask Actuate" className="absolute bottom-0 left-0 right-0 top-auto flex h-[85vh] max-h-[85vh] w-full flex-col bg-surface shadow-2xl sm:bottom-auto sm:left-auto sm:right-0 sm:top-0 sm:h-full sm:max-h-none sm:w-[min(100%,32rem)]">
            <header className="flex items-center justify-between border-b border-border-light px-5 py-4">
              <div>
                <p className="text-sm font-bold tracking-wide text-neutral-title">ASK ACTUATE</p>
                <p className="mt-1 text-xs text-neutral-muted">Grounded in {cycle} mart data</p>
              </div>
              <button type="button" aria-label="Close Ask Actuate" onClick={() => setOpen(false)} className="rounded-full p-2 text-neutral-muted hover:bg-surface-panel">
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            </header>
            <div className="flex-1 overflow-y-auto px-5 py-4">
              {history.length === 0 && !loading && <p className="rounded-lg border border-border-light bg-surface-panel p-4 text-sm leading-relaxed text-neutral-body">Ask about OTA by vendor or office, cost outliers by vendor, open Sev-1 alerts by vendor or office, customer ratings by vendor or office, or no-shows by shift or office.</p>}
              {history.map((entry, index) => (
                <div key={`${entry.question}-${index}`} className="mb-5">
                  <p className="mb-2 text-xs font-semibold text-secondary">{entry.question}</p>
                  <div className="rounded-lg border border-border-light bg-surface-panel p-4">
                    <p className="text-sm leading-relaxed text-neutral-body">{entry.response.narrative}</p>
                    {index === history.length - 1 && <div className="mt-4">{resultTable(entry.response.rows)}</div>}
                    {index === history.length - 1 && <>
                      <details className="mt-4 border-t border-border-light pt-3 text-xs text-neutral-body">
                        <summary className="cursor-pointer font-semibold text-secondary">SQL</summary>
                        <pre className="mt-2 overflow-x-auto whitespace-pre-wrap rounded bg-neutral-title p-3 text-[11px] text-surface">{entry.response.sql}</pre>
                      </details>
                      <details className="mt-3 text-xs text-neutral-body">
                        <summary className="cursor-pointer font-semibold text-secondary">Sources</summary>
                        <p className="mt-2">{entry.response.grounded_from.marts.join(', ')} · {entry.response.grounded_from.cycle}</p>
                      </details>
                    </>}
                  </div>
                </div>
              ))}
              {loading && <p role="status" className="text-sm text-neutral-muted">Thinking from the operational marts…</p>}
              {unsupported && <div role="alert" className="rounded-lg border border-warning/30 bg-warning-bg p-4 text-sm text-warning"><p className="font-semibold">Please ask a supported operational question.</p><p className="mt-2 text-xs">Include a vendor, office, or shift in the question. Try one of:</p><ul className="mt-1 list-disc pl-5 text-xs">{unsupported.map((intent) => <li key={intent}>{intent}</li>)}</ul></div>}
              {error && <p role="alert" className="rounded-lg border border-error/30 bg-error-bg p-4 text-sm text-error">{error}</p>}
              {latest && latest.rows.length === 0 && <p className="sr-only">Empty result</p>}
            </div>
            <form onSubmit={submit} className="border-t border-border-light bg-surface px-5 py-4">
              <label htmlFor="ask-question" className="sr-only">Operational question</label>
              <div className="flex items-end gap-2">
                <textarea id="ask-question" aria-label="Operational question" value={question} onChange={(event) => setQuestion(event.target.value)} rows={2} placeholder="Ask an operational question…" className="min-h-10 flex-1 resize-none rounded-lg border border-border-light bg-surface-panel px-3 py-2 text-sm text-neutral-title outline-none focus:border-secondary" />
                <button type="submit" aria-label="Send" disabled={loading || !question.trim()} className="rounded-lg bg-secondary px-4 py-2 text-sm font-bold text-surface disabled:cursor-not-allowed disabled:opacity-50">Send</button>
              </div>
              <p className="mt-2 text-[11px] text-neutral-muted">Cycle: {cycle}. No chat history is persisted.</p>
            </form>
          </aside>
        </div>
      )}
    </>
  )
}
