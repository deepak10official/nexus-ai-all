/** Thin API client for the Social Calendar. Vite proxies /api to FastAPI. */

async function req(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(body.detail || `${res.status} ${res.statusText}`);
  }
  return body;
}

export const getPosts = (week) =>
  req(`/api/calendar/posts${week ? `?week=${week}` : ""}`);

export const schedulePost = (data) =>
  req("/api/calendar/schedule", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const updatePost = (id, patch) =>
  req(`/api/calendar/posts/${id}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });

export const publishPost = (id) =>
  req(`/api/calendar/publish/${id}`, { method: "POST" });

export const deletePost = (id) =>
  req(`/api/calendar/posts/${id}`, { method: "DELETE" });

export const getQueue = () => req("/api/calendar/queue");

export const addToQueue = (data) =>
  req("/api/calendar/queue", {
    method: "POST",
    body: JSON.stringify(data),
  });

export const approveQueueItem = (id) =>
  req(`/api/calendar/queue/${id}/approve`, { method: "POST" });

export const rejectQueueItem = (id) =>
  req(`/api/calendar/queue/${id}/reject`, { method: "POST" });
