import { useEffect, useRef, useState, type FormEvent } from 'react'
import { sendChat } from '../api'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

const GREETING: Message = {
  role: 'assistant',
  content: "Hi! I'm the Campus Customs assistant. Ask me about our Yale gear.",
}

export default function ChatWidget() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([GREETING])
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, open])

  async function handleSend(e: FormEvent) {
    e.preventDefault()
    const text = draft.trim()
    if (!text || sending) return
    setMessages((m) => [...m, { role: 'user', content: text }])
    setDraft('')
    setSending(true)
    try {
      const res = await sendChat(text)
      setMessages((m) => [...m, { role: 'assistant', content: res.reply }])
    } catch (err) {
      const reason = err instanceof Error ? err.message : 'unknown error'
      setMessages((m) => [...m, { role: 'assistant', content: `Sorry, I couldn't reach the store (${reason}).` }])
    } finally {
      setSending(false)
    }
  }

  if (!open) {
    return (
      <button className="chat-launcher" onClick={() => setOpen(true)}>
        💬 Chat with us
      </button>
    )
  }

  return (
    <section className="chat-panel" aria-label="Chat with Campus Customs">
      <header className="chat-header">
        <span>Campus Customs Assistant</span>
        <button className="chat-close" onClick={() => setOpen(false)} aria-label="Close chat">
          ×
        </button>
      </header>
      <div className="chat-messages">
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg ${m.role}`}>
            {m.content}
          </div>
        ))}
        {sending && <div className="chat-msg assistant typing">…</div>}
        <div ref={bottomRef} />
      </div>
      <form className="chat-input" onSubmit={handleSend}>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Ask about products, sizes, stock…"
          aria-label="Chat message"
        />
        <button type="submit" disabled={sending || !draft.trim()}>
          Send
        </button>
      </form>
    </section>
  )
}
