import { act, renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { useCycle } from '../useCycle';

import { server } from '../../test-setup';

const BASE = 'http://127.0.0.1:8000';
const BRIEF_ENVELOPE = { data: { generated_at: 't', headline_facts: [], insights_top5: [], safety_open_sev1: 0, actions_top3: [] }, warning: null };

function briefingHandler(responder) {
  let calls = 0;
  server.use(
    http.get(`${BASE}/briefing`, async ({ request }) => {
      calls += 1;
      return responder(new URL(request.url).searchParams.get('cycle'), calls);
    }),
  );
  return () => calls;
}

describe('useCycle', () => {
  it('200 probe → default cycle kept, cycles stays null', async () => {
    const getCalls = briefingHandler(() => HttpResponse.json(BRIEF_ENVELOPE));
    const { result } = renderHook(() => useCycle());
    await waitFor(() => expect(getCalls()).toBe(1));
    expect(result.current.cycle).toBe('2026-06-H1');
    expect(result.current.cycles).toBeNull();
  });

  it('404 with valid_cycles → cycle = valid_cycles[0], cycles = list', async () => {
    const getCalls = briefingHandler(() =>
      HttpResponse.json(
        { detail: 'unknown cycle', cycle: '2026-06-H1', valid_cycles: ['2026-07-H1', '2026-07-H2'] },
        { status: 404 },
      ),
    );
    const { result } = renderHook(() => useCycle());
    await waitFor(() => expect(result.current.cycle).toBe('2026-07-H1'));
    expect(getCalls()).toBe(1);
    expect(result.current.cycles).toEqual(['2026-07-H1', '2026-07-H2']);
  });

  it('404 with empty valid_cycles → cycle unchanged, cycles = []', async () => {
    const getCalls = briefingHandler(() =>
      HttpResponse.json({ detail: 'unknown cycle', cycle: '2026-06-H1', valid_cycles: [] }, { status: 404 }),
    );
    const { result } = renderHook(() => useCycle());
    await waitFor(() => expect(getCalls()).toBe(1));
    await waitFor(() => expect(result.current.cycles).toEqual([]));
    expect(result.current.cycle).toBe('2026-06-H1');
  });

  it('network failure → cycle unchanged, cycles null, silent', async () => {
    const getCalls = briefingHandler(() => HttpResponse.error());
    const { result } = renderHook(() => useCycle());
    await waitFor(() => expect(getCalls()).toBe(1));
    await new Promise((r) => setTimeout(r, 20));
    expect(result.current.cycle).toBe('2026-06-H1');
    expect(result.current.cycles).toBeNull();
  });

  it('setCycle overrides without re-probing', async () => {
    const getCalls = briefingHandler(() => HttpResponse.json(BRIEF_ENVELOPE));
    const { result } = renderHook(() => useCycle());
    await waitFor(() => expect(getCalls()).toBe(1));
    act(() => result.current.setCycle('2026-05-H1'));
    expect(result.current.cycle).toBe('2026-05-H1');
    await new Promise((r) => setTimeout(r, 20));
    expect(getCalls()).toBe(1);
  });
});
