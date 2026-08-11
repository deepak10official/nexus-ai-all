// All calls go to a relative /api path. In dev, Vite proxies /api to the
// FastAPI bridge (see vite.config.js). Set VITE_API_BASE to hit an absolute
// URL instead (e.g. in production).
const BASE = import.meta.env.VITE_API_BASE ?? "";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  health: () => request("/api/health"),
  personas: () => request("/api/panel/personas"),
  settings: () => request("/api/panel/settings"),
  state: (threadId) =>
    request(`/api/panel/state?thread_id=${encodeURIComponent(threadId)}`),
  run: (threadId, post) =>
    request("/api/panel/run", {
      method: "POST",
      body: JSON.stringify({ thread_id: threadId, post }),
    }),
  rework: (threadId) =>
    request("/api/panel/rework", {
      method: "POST",
      body: JSON.stringify({ thread_id: threadId }),
    }),
};
