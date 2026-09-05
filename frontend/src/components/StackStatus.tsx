import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import {
  createExample,
  fetchHealth,
  fetchReadiness,
  getApiBaseUrl,
  listExamples,
} from '../lib/api'

function StatusDot({ ok }: { ok: boolean | undefined }) {
  const color =
    ok === undefined ? 'bg-[#E5E7EB]' : ok ? 'bg-[#43B02A]' : 'bg-[#D92D20]'
  return <span className={`inline-block h-2 w-2 rounded-full ${color}`} />
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'unknown error'
}

export default function StackStatus() {
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState('')

  const health = useQuery({
    queryKey: ['backend', 'health'],
    queryFn: ({ signal }) => fetchHealth(signal),
    retry: false,
  })
  const readiness = useQuery({
    queryKey: ['backend', 'ready'],
    queryFn: ({ signal }) => fetchReadiness(signal),
    retry: false,
  })
  const examples = useQuery({
    queryKey: ['backend', 'examples'],
    queryFn: ({ signal }) => listExamples(signal),
    retry: false,
  })
  const create = useMutation({
    mutationFn: (content: string) => createExample(content),
    onSuccess: () => {
      setDraft('')
      queryClient.invalidateQueries({ queryKey: ['backend', 'examples'] })
    },
  })

  const apiUp = health.data?.status === 'ok'
  const dbUp = readiness.data?.db === 'up'

  return (
    <section className="island-shell mt-20 rounded-lg p-6">
      <p className="island-kicker mb-2">FULL-STACK WIRING</p>
      <h2 className="mb-2 text-lg leading-[22px] font-semibold text-[#1F1F1F]">
        Backend &amp; database status
      </h2>
      <p className="m-0 mb-4 text-sm text-[#6B7280]">
        API: <code>{getApiBaseUrl()}</code>
      </p>
      <ul className="m-0 mb-4 list-none space-y-2 p-0 text-sm text-[#333333]">
        <li className="flex items-center gap-2">
          <StatusDot ok={health.data ? apiUp : undefined} />
          API <code>/health</code>:{' '}
          {health.isPending
            ? 'checking…'
            : health.data
              ? health.data.status
              : `unreachable (${errorMessage(health.error)})`}
        </li>
        <li className="flex items-center gap-2">
          <StatusDot ok={readiness.data ? dbUp : undefined} />
          DB <code>/ready</code>:{' '}
          {readiness.isPending
            ? 'checking…'
            : readiness.data
              ? `${readiness.data.status} (db: ${readiness.data.db})`
              : `unreachable (${errorMessage(readiness.error)})`}
        </li>
        <li className="flex items-center gap-2">
          <StatusDot ok={examples.data ? true : undefined} />
          DB read <code>/examples</code>:{' '}
          {examples.isPending
            ? 'checking…'
            : examples.data
              ? `${examples.data.length} row(s)`
              : `unreachable (${errorMessage(examples.error)})`}
        </li>
      </ul>
      {examples.data && examples.data.length > 0 && (
        <ul className="m-0 mb-4 list-disc space-y-1 pl-5 text-sm text-[#333333]">
          {examples.data.slice(-5).map((row) => (
            <li key={row.id}>{row.content}</li>
          ))}
        </ul>
      )}
      <form
        className="flex flex-wrap gap-3"
        onSubmit={(e) => {
          e.preventDefault()
          const content = draft.trim()
          if (content && !create.isPending) create.mutate(content)
        }}
      >
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Write a test row (proves DB write)"
          maxLength={280}
          className="demo-input min-w-52 flex-1"
        />
        <button
          type="submit"
          disabled={create.isPending || draft.trim().length === 0}
          className="demo-button"
        >
          {create.isPending ? 'Saving…' : 'Save row'}
        </button>
      </form>
      {create.isError && (
        <p className="m-0 mt-2 text-sm text-[#D92D20]">
          Write failed: {errorMessage(create.error)}
        </p>
      )}
    </section>
  )
}
