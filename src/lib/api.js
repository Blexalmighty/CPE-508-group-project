/**
 * Minimal HTTP client for the OncoPredict API.
 *
 * The API origin is set at build time via VITE_API_URL so the static host can
 * call the FastAPI service anywhere. When unset (local `npm run dev`), requests
 * go to /api and the Vite dev server proxies them to 127.0.0.1:8000.
 */

// In production the static host (Vercel, Netlify, ...) cannot proxy to the API
// host, so the full origin must be baked in at build time:
//   VITE_API_URL=https://api.example.com npm run build
const BASE = import.meta.env.VITE_API_URL ?? '';

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

export async function apiRequest(path, { method = 'GET', body, token } = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: {
      ...(body ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const payload = await res.json().catch(() => null);
    throw new ApiError(describeError(payload) ?? `Request failed (${res.status})`, res.status);
  }
  return res.json();
}

/** FastAPI sends a string for our own aborts and a list for schema failures. */
function describeError(body) {
  const detail = body?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => `${item.loc?.at(-1) ?? 'field'}: ${item.msg}`).join('; ');
  }
  return null;
}
