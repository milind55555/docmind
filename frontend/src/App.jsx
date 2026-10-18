import { useEffect, useRef, useState } from "react";
import { deleteDocument, listDocuments, streamChat, uploadDocument } from "./api.js";

const ACCEPT = ".pdf,.txt,.md,.csv,.xlsx";

function formatSize(bytes) {
  return bytes > 1048576 ? `${(bytes / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

function Sources({ sources }) {
  const [open, setOpen] = useState(false);
  if (!sources?.length) return null;
  return (
    <div className="sources">
      <button className="link" onClick={() => setOpen(!open)} aria-expanded={open}>
        {open ? "Hide" : "Show"} {sources.length} sources
      </button>
      {open && (
        <ol>
          {sources.map((s) => (
            <li key={s.n}>
              <strong>{s.source}</strong>
              {s.location ? ` (${s.location})` : ""}
              <p>{s.snippet}</p>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

export default function App() {
  const [docs, setDocs] = useState([]);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const bottom = useRef(null);

  const refresh = () => listDocuments().then(setDocs).catch((e) => setError(e.message));
  useEffect(() => { refresh(); }, []);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  async function onUpload(e) {
    const files = [...e.target.files];
    e.target.value = "";
    setError("");
    setUploading(true);
    for (const f of files) {
      try { await uploadDocument(f); } catch (err) { setError(`${f.name}: ${err.message}`); }
    }
    setUploading(false);
    refresh();
  }

  async function onRemove(id) {
    try { await deleteDocument(id); refresh(); } catch (err) { setError(err.message); }
  }

  async function onAsk(e) {
    e.preventDefault();
    const q = question.trim();
    if (!q || busy) return;
    setError("");
    setQuestion("");
    setBusy(true);
    const history = messages.map(({ role, content }) => ({ role, content }));
    setMessages((m) => [...m, { role: "user", content: q }, { role: "assistant", content: "", sources: [] }]);
    const patchLast = (fn) => setMessages((m) => m.map((x, i) => (i === m.length - 1 ? fn(x) : x)));
    try {
      await streamChat(q, history, {
        onSources: (sources) => patchLast((x) => ({ ...x, sources })),
        onToken: (t) => patchLast((x) => ({ ...x, content: x.content + t })),
        onError: (msg) => setError(msg),
      });
    } catch (err) {
      setError(err.message);
    }
    setBusy(false);
  }

  return (
    <div className="shell">
      <aside className="library">
        <h1>DocMind</h1>
        <p className="tagline">Ask questions about your own files. Answers cite the passage they came from.</p>
        <label className={`drop ${uploading ? "disabled" : ""}`}>
          <input type="file" accept={ACCEPT} multiple onChange={onUpload} disabled={uploading} />
          {uploading ? "Reading and indexing…" : "Add PDF, text, CSV or Excel files"}
        </label>
        {docs.length === 0 ? (
          <p className="empty">No documents yet. Add a file to start asking questions.</p>
        ) : (
          <ul className="doclist">
            {docs.map((d) => (
              <li key={d.id}>
                <div>
                  <span className="name">{d.filename}</span>
                  <span className="meta">{formatSize(d.size)}, {d.chunks} passages</span>
                </div>
                <button className="link danger" onClick={() => onRemove(d.id)} aria-label={`Remove ${d.filename}`}>Remove</button>
              </li>
            ))}
          </ul>
        )}
      </aside>

      <main className="chat">
        <div className="thread" aria-live="polite">
          {messages.length === 0 && (
            <div className="intro">
              <h2>What do you want to know?</h2>
              <p>Try “Summarise this document”, or ask about a number in a spreadsheet.</p>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.role}`}>
              <p>{m.content || (busy && i === messages.length - 1 ? "Searching your documents…" : "")}</p>
              {m.role === "assistant" && <Sources sources={m.sources} />}
            </div>
          ))}
          <div ref={bottom} />
        </div>
        {error && <div className="error" role="alert">{error}</div>}
        <form className="composer" onSubmit={onAsk}>
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask about your documents"
            aria-label="Your question"
          />
          <button type="submit" disabled={busy || !question.trim()}>Ask</button>
        </form>
      </main>
    </div>
  );
}
