import { useEffect, useRef, useState, type FormEvent } from 'react'
import { sendBored, sendChat } from '../api'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

const GREETING: Message = {
  role: 'assistant',
  content: "Woof! 🐶 I'm the Campus Customs bulldog. Say something!",
}

// The bulldog gets bored if you go quiet: after BORED_AFTER_MS it wags its
// tail or brings a ball, at most MAX_BORED times in a row until you talk again.
const BORED_AFTER_MS = 15_000
const MAX_BORED = 3

export default function ChatWidget() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([GREETING])
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [boredStreak, setBoredStreak] = useState(0)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, open])

  // Restarts whenever a message arrives; fires only while the panel is open and idle.
  useEffect(() => {
    if (!open || sending || boredStreak >= MAX_BORED) return
    const timer = setTimeout(() => {
      sendBored()
        .then((res) => {
          setMessages((m) => [...m, { role: 'assistant', content: res.reply }])
          setBoredStreak((n) => n + 1)
        })
        .catch(() => setBoredStreak(MAX_BORED)) // backend down — stop trying
    }, BORED_AFTER_MS)
    return () => clearTimeout(timer)
  }, [open, sending, boredStreak, messages])

  async function handleSend(e: FormEvent) {
    e.preventDefault()
    const text = draft.trim()
    if (!text || sending) return
    setMessages((m) => [...m, { role: 'user', content: text }])
    setDraft('')
    setBoredStreak(0)
    setSending(true)
    try {
      const res = await sendChat(text)
      setMessages((m) => [...m, { role: 'assistant', content: res.reply }])
    } catch (err) {
      const reason = err instanceof Error ? err.message : 'unknown error'
      setMessages((m) => [...m, { role: 'assistant', content: `*whimpers* Couldn't reach the store (${reason}).` }])
    } finally {
      setSending(false)
    }
  }

  if (!open) {
    return (
      <button className="chat-launcher" onClick={() => setOpen(true)}>
        🐶 Chat with us
      </button>
    )
  }

  return (
    <section className="chat-panel" aria-label="Chat with Campus Customs">
      <header className="chat-header">
        <span>Campus Customs Bulldog</span>
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
          placeholder="Say something to the bulldog…"
          aria-label="Chat message"
        />
        <button type="submit" disabled={sending || !draft.trim()}>
          Send
        </button>
      </form>
    </section>
  )
}
