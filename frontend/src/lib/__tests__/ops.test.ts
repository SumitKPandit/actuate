import { afterEach, describe, expect, it, vi } from 'vitest';
import { http, HttpResponse } from 'msw';

import { ApiError, ask, getActions, getBriefing, getInsights, getOverview, getVendors, ackAction } from '../ops';

import { server } from '../../test-setup';

const BASE = 'http://127.0.0.1:8000';

afterEach(() => {
  vi.unstubAllEnvs();
});

describe('getOverview', () => {
  it('returns the envelope verbatim and sends the cycle param', async () => {
    let captured: URL | undefined;
    server.use(
      http.get(`${BASE}/overview`, ({ request }) => {
        captured = new URL(request.url);
        return HttpResponse.json({
          data: { trips: 12000, ota_pct: 92.7, benchmarks: { ota_sla: 95, ack_sla_min: 30 } },
          warning: null,
        });
      }),
    );
    const env = await getOverview('2026-06-H1');
    expect(captured?.searchParams.get('cycle')).toBe('2026-06-H1');
    expect(env).toEqual({
      data: { trips: 12000, ota_pct: 92.7, benchmarks: { ota_sla: 95, ack_sla_min: 30 } },
      warning: null,
    });
  });
});

describe('getBriefing / getInsights / getActions', () => {
  it('each GET hits its route with the cycle param and parses the envelope', async () => {
    const hits: string[] = [];
    const envelope = { data: null, warning: 'marts empty — run ingest' };
    server.use(
      http.get(`${BASE}/briefing`, ({ request }) => {
        hits.push(new URL(request.url).pathname);
        return HttpResponse.json(envelope);
      }),
      http.get(`${BASE}/insights`, ({ request }) => {
        hits.push(new URL(request.url).pathname);
        return HttpResponse.json(envelope);
      }),
      http.get(`${BASE}/actions`, ({ request }) => {
        hits.push(new URL(request.url).pathname);
        return HttpResponse.json(envelope);
      }),
    );
    expect(await getBriefing('c1')).toEqual(envelope);
    expect(await getInsights('c1')).toEqual(envelope);
    expect(await getActions('c1')).toEqual(envelope);
    expect(hits).toEqual(['/briefing', '/insights', '/actions']);
  });
});

describe('getVendors', () => {
  it('sends sort=cost when given and sort=ota by default', async () => {
    let sorts: (string | null)[] = [];
    server.use(
      http.get(`${BASE}/vendors`, ({ request }) => {
        sorts.push(new URL(request.url).searchParams.get('sort'));
        return HttpResponse.json({ data: [], warning: null });
      }),
    );
    await getVendors('c1', 'cost');
    await getVendors('c1');
    expect(sorts).toEqual(['cost', 'ota']);
  });
});

describe('empty-marts envelope', () => {
  it('returns {data: null, warning} verbatim — a warning is not an error', async () => {
    server.use(http.get(`${BASE}/overview`, () => HttpResponse.json({ data: null, warning: 'marts empty — run ingest' })));
    const env = await getOverview('c1');
    expect(env.data).toBeNull();
    expect(env.warning).toBe('marts empty — run ingest');
  });
});

describe('error mapping', () => {
  it('404 unknown cycle → ApiError with flat body', async () => {
    server.use(
      http.get(`${BASE}/overview`, () =>
        HttpResponse.json(
          { detail: 'unknown cycle', cycle: 'bogus', valid_cycles: ['2026-06-H1', '2026-07-H1'] },
          { status: 404 },
        ),
      ),
    );
    const err: ApiError = await getOverview('bogus').catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(404);
    expect(err.message).toBe('unknown cycle');
    expect(err.body).toEqual({ detail: 'unknown cycle', cycle: 'bogus', valid_cycles: ['2026-06-H1', '2026-07-H1'] });
  });

  it('422 invalid sort → ApiError with allowed list', async () => {
    server.use(
      http.get(`${BASE}/vendors`, () =>
        HttpResponse.json({ detail: 'invalid sort', allowed: ['ota', 'cost', 'alerts', 'csat'] }, { status: 422 }),
      ),
    );
    const err: ApiError = await getVendors('c1', 'bogus' as never).catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(422);
    expect(err.body).toEqual({ detail: 'invalid sort', allowed: ['ota', 'cost', 'alerts', 'csat'] });
  });

  it('non-JSON error body → ApiError body is {raw: text}', async () => {
    server.use(http.get(`${BASE}/overview`, () => new HttpResponse('boom', { status: 500 })));
    const err: ApiError = await getOverview('c1').catch((e) => e);
    expect(err.status).toBe(500);
    expect(err.body).toEqual({ raw: 'boom' });
  });

  it('malformed JSON on 2xx → throws, never a partial envelope', async () => {
    server.use(http.get(`${BASE}/overview`, () => new HttpResponse('not-json{', { status: 200 })));
    await expect(getOverview('c1')).rejects.toThrow();
  });

  it('network failure → fetch TypeError propagates', async () => {
    server.use(http.get(`${BASE}/overview`, () => HttpResponse.error()));
    await expect(getOverview('c1')).rejects.toThrow(TypeError);
  });
});

describe('ackAction', () => {
  it('POSTs exactly {actor} and returns the bare record', async () => {
    let captured: unknown;
    server.use(
      http.post(`${BASE}/actions/id-1/ack`, async ({ request }) => {
        captured = await request.json();
        return HttpResponse.json({
          id: 'id-1',
          status: 'acked',
          actor: 'Priya',
          acked_at: '2026-09-05T10:00:00+00:00',
        });
      }),
    );
    const rec = await ackAction('id-1', 'Priya');
    expect(captured).toEqual({ actor: 'Priya' });
    expect(rec).toEqual({ id: 'id-1', status: 'acked', actor: 'Priya', acked_at: '2026-09-05T10:00:00+00:00' });
  });

  it('blank actor sent as-is; backend 422 → ApiError', async () => {
    let captured: unknown;
    server.use(
      http.post(`${BASE}/actions/id-1/ack`, async ({ request }) => {
        captured = await request.json();
        return HttpResponse.json({ detail: 'actor must be non-blank' }, { status: 422 });
      }),
    );
    const err: ApiError = await ackAction('id-1', '  ').catch((e) => e);
    expect(captured).toEqual({ actor: '  ' });
    expect(err.status).toBe(422);
    expect(err.message).toBe('actor must be non-blank');
  });
});

describe('missing env', () => {
  it('rejects with the verbatim message when VITE_API_URL is empty', async () => {
    vi.stubEnv('VITE_API_URL', '');
    await expect(getOverview('c1')).rejects.toThrow('Set VITE_API_URL in frontend/.env');
  });
});

describe('ask', () => {
  it('POSTs the question, active cycle, and optional scope', async () => {
    let captured: { body: unknown; cycle: string | null } | undefined;
    server.use(
      http.post(`${BASE}/ask`, async ({ request }) => {
        captured = { body: await request.json(), cycle: new URL(request.url).searchParams.get('cycle') };
        return HttpResponse.json({
          sql: 'SELECT 1 LIMIT 50',
          rows: [{ vendor: 'Vendor A' }],
          narrative: 'Grounded answer.',
          grounded_from: { marts: ['vendor_kpi'], cycle: '2026-06-H1' },
        });
      }),
    );
    const response = await ask('show OTA by vendor', '2026-06-H1', { vendor: 'Vendor A' });
    expect(captured).toEqual({
      body: { question: 'show OTA by vendor', cycle: '2026-06-H1', scope: { vendor: 'Vendor A' } },
      cycle: null,
    });
    expect(response.narrative).toBe('Grounded answer.');
  });

  it('passes the 422 supported-intents body through ApiError', async () => {
    const body = { detail: 'unsupported question', supported_intents: ['ota_by_vendor'] };
    server.use(http.post(`${BASE}/ask`, () => HttpResponse.json(body, { status: 422 })));
    const error = await ask('show OTA', '2026-06-H1').then(
      () => { throw new Error('expected ask to reject'); },
      (value: unknown) => value as ApiError,
    );
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(422);
    expect(error.body).toEqual(body);
  });
});
