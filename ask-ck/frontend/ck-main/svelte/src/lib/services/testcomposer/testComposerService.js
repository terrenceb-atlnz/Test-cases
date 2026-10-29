//@ts-nocheck

export const TC_API = "/api/test-composer";

async function json(r) {
  const d = await r.json().catch(() => ({}));
  if (!r.ok) {
    const det = d.detail;
    throw new Error(
      typeof det === "string"
        ? det
        : det && det.error
          ? det.error
          : d.error || `HTTP ${r.status}`,
    );
  }
  return d;
}

export function httpServer(base = TC_API) {
  return async function server(path, opts = {}) {
    const r = await fetch(
      base + path,
      Object.assign({ headers: { "Content-Type": "application/json" } }, opts),
    );
    return json(r);
  };
}

/** The seat agent's session routes. Every POST is JSON (the agent refuses anything else). */
export function httpAgent(base = "http://127.0.0.1:8765") {
  const post = async (path, body) =>
    json(
      await fetch(base + path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body || {}),
      }),
    );
  return {
    base,
    health: async () => json(await fetch(base + "/health")),
    start: (body) => post("/session/start", body),
    events: async (sid, after, wait = 20) =>
      json(
        await fetch(
          `${base}/session/${encodeURIComponent(sid)}/events?after=${after}&wait=${wait}`,
        ),
      ),
    answer: (sid, body) =>
      post(`/session/${encodeURIComponent(sid)}/answer`, body),
    message: (sid, text) =>
      post(`/session/${encodeURIComponent(sid)}/message`, { text }),
    stop: (sid) => post(`/session/${encodeURIComponent(sid)}/stop`, {}),
    sessions: async () => json(await fetch(base + "/sessions")),
  };
}
