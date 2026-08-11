/** Thin API client. Vite proxies /api to FastAPI on :8000. */

async function req(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    // FastAPI puts the human-readable reason in `detail`.
    throw new Error(body.detail || `${res.status} ${res.statusText}`);
  }
  return body;
}

export const getHealth = () => req("/api/health");
export const getTrends = (refresh = false) =>
  req(`/api/radar/trends?refresh=${refresh}`);
export const evaluateOne = (name) =>
  req(`/api/radar/evaluate?name=${encodeURIComponent(name)}`);
export const generate = (hashtag, force = false) =>
  req("/api/radar/generate", {
    method: "POST",
    body: JSON.stringify({ hashtag, force }),
  });
export const makeImage = (draft_id, prompt_override = null) =>
  req("/api/radar/image", {
    method: "POST",
    body: JSON.stringify({ draft_id, prompt_override }),
  });
export const editDraft = (draft_id, patch) =>
  req(`/api/radar/draft/${draft_id}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
// target: "post" | "image" | "final" — the two halves are judged apart.
export const decide = (draft_id, action, target = "final") =>
  req("/api/radar/decision", {
    method: "POST",
    body: JSON.stringify({ draft_id, action, target }),
  });
