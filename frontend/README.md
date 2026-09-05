# Actuate Web

Vite + React SPA for the transport manager brief, dashboard, and Ask Actuate drawer.

Stories 05b, 06, 07, 09, and 10 are implemented. Story 08 remains the pending trigger, documentation, and sample-artifact pass.

## Develop

```bash
npm install
npm run dev
```

The Vite development server is available at `http://localhost:5173`. Set `VITE_API_URL` in `.env` to override the backend URL; the default is `http://127.0.0.1:8000`.

## Verify

```bash
npm test -- --run
npm run lint
npm run typecheck
npm run build
```

The frontend reads live data through `src/lib/ops.ts` and the data hooks. The brief and dashboard are rendered by the shared single-page surface; acknowledgements call `POST /actions/{id}/ack`, and Ask Actuate calls `POST /ask` with the active cycle.
