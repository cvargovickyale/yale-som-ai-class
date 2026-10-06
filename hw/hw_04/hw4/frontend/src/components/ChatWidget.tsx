import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ApiError, formatPrice, getChatHistory, resultsUrl, sendBored, sendChat } from '../api'
import { useAuth } from '../auth'
import type { ChatHistoryMessage, ProductSummary } from '../types'

interface Message {
  role: 'user' | 'assistant' | 'divider'
  content: string
  products?: ProductSummary[]
  resultsLink?: { label: string; url: string } // search replies: link to the filtered page
}

const GREETING: Message = {
  role: 'assistant',
  content: "Woof! 🐶 I'm Handsome Dan, the Campus Customs bulldog. Ask me about Yale gear, sizes, or the shop.",
}

// A divider before each day of reloaded history, so old prices and stock in
// past replies read as old. (The cards under them are re-read and current.)
function withDayDividers(saved: ChatHistoryMessage[]): Message[] {
  const out: Message[] = []
  let lastDay = ''
  for (const m of saved) {
    const day = new Date(m.created_at.replace(' ', 'T') + 'Z').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    if (day !== lastDay) {
      out.push({ role: 'divider', content: `Earlier chat · ${day} · prices and stock may have changed since` })
      lastDay = day
    }
    out.push(fromHistory(m))
  }
  return out
}

// Saved messages (logged-in customers) render like live ones, minus navigation.
function fromHistory(m: ChatHistoryMessage): Message {
  if (m.role === 'assistant' && m.results_label && m.products.length > 0) {
    const url = resultsUrl(m.results_label, m.products.map((p) => p.product_id))
    return { role: 'assistant', content: m.content, resultsLink: { label: m.results_label, url } }
  }
  return { role: m.role, content: m.content, products: m.products }
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
  const navigate = useNavigate()
  const location = useLocation()
  const { user, ready } = useAuth()

  // Logged in: reload saved history. Logged out / guest: start fresh.
  useEffect(() => {
    if (!ready) return
    let cancelled = false
    const reset = () => setMessages([GREETING])
    if (!user) {
      reset()
      return
    }
    getChatHistory()
      .then((saved) => {
        if (cancelled) return
        const welcome: Message = saved.length
          ? { role: 'assistant', content: `Woof! Welcome back, ${user.first_name}. Here's our chat so far.` }
          : { role: 'assistant', content: `Woof! Hi ${user.first_name}, I'm Handsome Dan 🐶 Ask me about Yale gear, sizes, or the shop.` }
        setMessages(saved.length ? [...withDayDividers(saved), welcome] : [welcome])
      })
      .catch(reset)
    return () => {
      cancelled = true
    }
  }, [user, ready])

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
      const res = await sendChat(text, location.pathname + location.search)
      if (res.results_label && res.products.length > 0) {
        // Search: filter the Products page to exactly these cards.
        const url = resultsUrl(res.results_label, res.products.map((p) => p.product_id))
        setMessages((m) => [...m, { role: 'assistant', content: res.reply, resultsLink: { label: res.results_label!, url } }])
        navigate(url)
      } else {
        // Answer about specific products: small cards in the chat, page unchanged.
        setMessages((m) => [...m, { role: 'assistant', content: res.reply, products: res.products }])
      }
    } catch (err) {
      // 429 = rate limit: the server's message already says when to try again.
      const content =
        err instanceof ApiError && err.status === 429
          ? `🐾 ${err.message}`
          : `*whimpers* Couldn't reach the store (${err instanceof Error ? err.message : 'unknown error'}).`
      setMessages((m) => [...m, { role: 'assistant', content }])
    } finally {
      setSending(false)
    }
  }

  if (!open) {
    return (
      <button className="chat-launcher" onClick={() => setOpen(true)}>
        🐶 Ask Handsome Dan
      </button>
    )
  }

  return (
    <section className="chat-panel" aria-label="Chat with Handsome Dan">
      <header className="chat-header">
        <span>
          Handsome Dan · Campus Customs
          <small className="chat-saved">{user ? 'Chat saved to your account' : 'Guest chat · not saved'}</small>
        </span>
        <button className="chat-close" onClick={() => setOpen(false)} aria-label="Close chat">
          ×
        </button>
      </header>
      <div className="chat-messages">
        {messages.map((m, i) =>
          m.role === 'divider' ? (
            <div key={i} className="chat-divider">
              {m.content}
            </div>
          ) : (
          <div key={i} className={`chat-msg ${m.role}`}>
            {m.content}
            {m.resultsLink && (
              <Link className="chat-results-link" to={m.resultsLink.url}>
                View “{m.resultsLink.label}” on the page →
              </Link>
            )}
            {m.products && m.products.length > 0 && (
              <ul className="chat-products">
                {m.products.map((p) => (
                  <li key={p.product_id}>
                    <Link to={`/products/${p.product_id}`} state={{ backgroundLocation: location }}>
                      <img src={p.image_url} alt="" />
                      <span>{p.name}</span>
                      <strong>{formatPrice(p.price)}</strong>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
          ),
        )}
        {sending && (
          <div className="chat-msg assistant typing" aria-label="Handsome Dan is fetching an answer">
            <span />
            <span />
            <span />
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <form className="chat-input" onSubmit={handleSend}>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Ask about products, sizes, the shop…"
          aria-label="Chat message"
        />
        <button type="submit" disabled={sending || !draft.trim()}>
          Send
        </button>
      </form>
    </section>
  )
}
