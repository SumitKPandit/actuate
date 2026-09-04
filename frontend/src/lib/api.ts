/** Typed FastAPI client. Base URL comes from `VITE_API_URL` (see `.env.example`). */

export interface HealthStatus {
  status: string
}

export interface ReadinessStatus {
  status: string
  db: string
}

export interface ExampleItem {
  id: number
  content: string
  created_at: string
}

export function getApiBaseUrl(): string {
  const raw = import.meta.env.VITE_API_URL as string | undefined
  if (!raw) return 'http://127.0.0.1:8000'
  return raw.replace(/\/+$/, '')
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${getApiBaseUrl()}${path}`, init)
  if (!res.ok) {
    throw new Error(`${init?.method ?? 'GET'} ${path} failed: ${res.status}`)
  }
  return res.json() as Promise<T>
}

export function fetchHealth(signal?: AbortSignal): Promise<HealthStatus> {
  return request<HealthStatus>('/health', { signal })
}

export function fetchReadiness(signal?: AbortSignal): Promise<ReadinessStatus> {
  return request<ReadinessStatus>('/ready', { signal })
}

export function listExamples(signal?: AbortSignal): Promise<Array<ExampleItem>> {
  return request<Array<ExampleItem>>('/examples', { signal })
}

export function createExample(content: string): Promise<ExampleItem> {
  return request<ExampleItem>('/examples', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  })
}
