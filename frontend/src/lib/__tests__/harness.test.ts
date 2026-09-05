import { expect, it } from 'vitest';

it('harness: jsdom + setupFiles + env pin are wired', () => {
  expect(import.meta.env.VITE_API_URL).toBe('http://127.0.0.1:8000');
});
