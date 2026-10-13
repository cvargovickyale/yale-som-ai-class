import { Fragment, useEffect, useReducer, useRef, useState } from 'react'
import { PEOPLE_INFO } from './talk.js'

// Chat with an AI avatar through the FastAPI backend (backend/main.py).
// '' uses the Vite /api proxy in dev; set VITE_API_URL to point somewhere else.
const API = import.meta.env.VITE_API_URL ?? ''
const MAX_CHARS = 2000
const OFFLINE = "Can't reach the backend, so this avatar can't talk right now. Start it with: backend/.venv/bin/python -m uvicorn main:app --app-dir backend --port 8000"

// one conversation per person, kept across closing and reopening the panel
// id -> { messages: [{ who: 'you' | 'them' | 'system', text }], sessionId, pending }
const CONVOS = new Map()
const convo = (id) => {
  if (!CONVOS.has(id)) CONVOS.set(id, { messages: [], sessionId: null, pending: false })
  return CONVOS.get(id)
}

// tiny markdown: ``` code blocks, `code`, **bold**
function Inline({ text }) {
  return text.split(/(`[^`\n]+`|\*\*[^*\n]+\*\*)/).map((part, i) =>
    part.startsWith('`') && part.endsWith('`') && part.length > 1 ? (
      <code key={i}>{part.slice(1, -1)}</code>
    ) : part.startsWith('**') && part.endsWith('**') && part.length > 3 ? (
      <b key={i}>{part.slice(2, -2)}</b>
    ) : (
      <Fragment key={i}>{part}</Fragment>
    ),
  )
}

function Markdown({ text }) {
  // split() with a capture group alternates: text, code, text, code, ...
  return text.split(/```[\w-]*\n?([\s\S]*?)```/).map((part, i) =>
    i % 2 ? <pre key={i}>{part.replace(/\n$/, '')}</pre> : <Inline key={i} text={part} />,
  )
}

export default function ChatPanel({ id, onClose }) {
  const info = PEOPLE_INFO[id]
  const c = convo(id)
  const [, rerender] = useReducer((n) => n + 1, 0)
  const [draft, setDraft] = useState('')
  const listRef = useRef()
  const inputRef = useRef()

  useEffect(() => {
    inputRef.current?.focus()
    const esc = (e) => e.key === 'Escape' && onClose(false) // a key press can't re-grab the mouse
    window.addEventListener('keydown', esc)
    return () => window.removeEventListener('keydown', esc)
  }, [onClose])

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight })
  })

  const send = async () => {
    const text = draft.trim()
    if (!text || c.pending) return
    c.messages.push({ who: 'you', text })
    c.pending = true
    setDraft('')
    rerender()
    try {
      const r = await fetch(`${API}/api/people/${id}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, session_id: c.sessionId }),
      })
      const data = await r.json().catch(() => null)
      if (r.ok && data?.reply) {
        c.sessionId = data.session_id
        c.messages.push({ who: 'them', text: data.reply })
      } else {
        // FastAPI errors come back as { detail }; anything else means no backend behind /api
        c.messages.push({ who: 'system', text: typeof data?.detail === 'string' ? data.detail : OFFLINE })
      }
    } catch {
      c.messages.push({ who: 'system', text: OFFLINE })
    }
    c.pending = false
    rerender()
  }

  return (
    <aside className="chat">
      <header>
        <div>
          <div className="chat-name">{info.name}</div>
          <div className="chat-sub">
            AI avatar · {info.course} · {info.room}
          </div>
        </div>
        <button className="chat-x" onClick={() => onClose(true)} aria-label="Close chat">
          ×
        </button>
      </header>
      <div className="chat-log" ref={listRef}>
        {c.messages.length === 0 && (
          <div className="msg system">You're chatting with an AI avatar, not the real professor. Say hi or ask about the course.</div>
        )}
        {c.messages.map((msg, i) => (
          <div key={i} className={`msg ${msg.who}`}>
            {msg.who === 'them' ? <Markdown text={msg.text} /> : msg.text}
          </div>
        ))}
        {c.pending && <div className="msg them typing">…</div>}
      </div>
      <form
        className="chat-input"
        onSubmit={(e) => {
          e.preventDefault()
          send()
        }}
      >
        <textarea
          ref={inputRef}
          value={draft}
          maxLength={MAX_CHARS}
          rows={2}
          placeholder={`Message ${info.name}…`}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              send()
            }
          }}
        />
        <button type="submit" disabled={!draft.trim() || c.pending}>
          Send
        </button>
      </form>
    </aside>
  )
}
