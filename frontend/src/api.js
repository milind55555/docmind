const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function listDocuments() {
  const r = await fetch(`${BASE}/api/documents`);
  if (!r.ok) throw new Error("Could not load documents.");
  return r.json();
}

export async function uploadDocument(file) {
  const body = new FormData();
  body.append("file", file);
  const r = await fetch(`${BASE}/api/documents`, { method: "POST", body });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail || "Upload failed.");
  }
  return r.json();
}

export async function deleteDocument(id) {
  const r = await fetch(`${BASE}/api/documents/${id}`, { method: "DELETE" });
  if (!r.ok) throw new Error("Could not remove the document.");
}

/** Streams a chat answer. Calls onSources(list), onToken(text), onError(msg). */
export async function streamChat(question, history, { onSources, onToken, onError }) {
  const r = await fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, history }),
  });
  if (!r.ok || !r.body) throw new Error("The server did not answer.");
  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const frames = buffer.split("\n\n");
    buffer = frames.pop();
    for (const frame of frames) {
      const event = /event: (.+)/.exec(frame)?.[1];
      const data = /data: (.+)/s.exec(frame)?.[1];
      if (!event || !data) continue;
      const payload = JSON.parse(data);
      if (event === "sources") onSources(payload);
      else if (event === "token") onToken(payload);
      else if (event === "error") onError(payload);
    }
  }
}
