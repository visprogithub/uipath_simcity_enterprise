/**
 * Backend URL configuration for Maestro City.
 *
 * Set NEXT_PUBLIC_BACKEND_URL in your environment to point at a deployed backend.
 * In development this defaults to http://localhost:8000.
 *
 * On Vercel: add NEXT_PUBLIC_BACKEND_URL=https://your-backend.railway.app
 *            add NEXT_PUBLIC_WS_URL=wss://your-backend.railway.app/ws
 */
export const BACKEND_URL =
  (process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8000').replace(/\/$/, '');

export const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ??
  BACKEND_URL.replace(/^https?/, (s) => (s === 'https' ? 'wss' : 'ws')) + '/ws';

export function api(path: string, init?: RequestInit): Promise<Response> {
  const url = `${BACKEND_URL}${path.startsWith('/') ? path : `/${path}`}`;
  return fetch(url, init);
}
