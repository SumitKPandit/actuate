import { act, renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import { ApiError } from '../ops';
import { useOpsData } from '../useOpsData';

import { server } from '../../test-setup';

const BASE = 'http://127.0.0.1:8000';
const delay = (ms) => new Promise((r) => setTimeout(r, ms));

const ENVELOPES = {
  briefing: { data: { generated_at: 't' }, warning: null },
  actions: { data: [{ id: 'a1' }], warning: null },
  overview: { data: { trips: 1 }, warning: null },
};

function useOpsRoutes({ warnOn, failOn, markerDelay = 0 } = {}) {
  let calls = 0;
  const route = (path, key) =>
    http.get(`${BASE}${path}`, async ({ request }) => {
      calls += 1;
      const cycle = new URL(request.url).searchParams.get('cycle');
      if (cycle === 'c1' && markerDelay) await delay(markerDelay);
      if (key === failOn) return HttpResponse.json({ detail: 'boom' }, { status: 500 });
      if (key === 'overview') return HttpResponse.json({ data: { marker: cycle }, warning: null });
      const env = ENVELOPES[key];
      return HttpResponse.json(key === warnOn ? { ...env, warning: 'marts empty — run ingest' } : env);
    });
  server.use(route('/briefing', 'briefing'), route('/actions', 'actions'), route('/overview', 'overview'));
  return () => calls;
}

describe('useOpsData', () => {
  it('all three 200 → single settle with all keys, warning null', async () => {
    useOpsRoutes();
    const { result } = renderHook(() => useOpsData('c1'));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(Object.keys(result.current.data)).toEqual(['briefing', 'actions', 'overview']);
    expect(result.current.warning).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('one envelope warning → surfaced verbatim, data still set', async () => {
    useOpsRoutes({ warnOn: 'actions' });
    const { result } = renderHook(() => useOpsData('c1'));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.warning).toBe('marts empty — run ingest');
    expect(result.current.data.actions).toEqual({ data: [{ id: 'a1' }], warning: 'marts empty — run ingest' });
  });

  it('one route 500 → error set, data null, loading false', async () => {
    useOpsRoutes({ failOn: 'actions' });
    const { result } = renderHook(() => useOpsData('c1'));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBeInstanceOf(ApiError);
    expect(result.current.error.status).toBe(500);
    expect(result.current.data).toBeNull();
  });

  it('refetch() re-issues all three GETs', async () => {
    const getCalls = useOpsRoutes();
    const { result } = renderHook(() => useOpsData('c1'));
    await waitFor(() => expect(result.current.loading).toBe(false));
    act(() => result.current.refetch());
    await waitFor(() => expect(getCalls()).toBe(6));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBeNull();
    expect(result.current.data).not.toBeNull();
  });

  it('cycle change mid-flight → new fetch, stale resolution ignored', async () => {
    useOpsRoutes({ markerDelay: 150 });
    const { result, rerender } = renderHook(({ cycle }) => useOpsData(cycle), { initialProps: { cycle: 'c1' } });
    rerender({ cycle: 'c2' });
    await waitFor(() => expect(result.current.data?.overview?.data?.marker).toBe('c2'));
    await delay(200);
    expect(result.current.data.overview.data.marker).toBe('c2');
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });
});
