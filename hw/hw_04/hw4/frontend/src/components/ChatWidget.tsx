import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { formatPrice, getChatHistory, resultsUrl, sendBored, sendChat } from '../api'
import { useAuth } from '../auth'
import type { ChatHistoryMessage, ProductSummary } from '../types'

interface Message {
  role: 'user' | 'assistant'
  content: string
  products?: ProductSummary[]
  resultsLink?: { label: string; url: string } // search replies: link to the filtered page
}

const GREETING: Message = {
  role: 'assistant',
  content: "Woof! 🐶 I'm the Campus Customs bulldog. Ask me about Yale gear, sizes, or the shop.",
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
          : { role: 'assistant', content: `Woof! Hi ${user.first_name} 🐶 Ask me about Yale gear, sizes, or the shop.` }
        setMessages(saved.length ? [...saved.map(fromHistory), welcome] : [welcome])
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
        <span>
          Campus Customs Bulldog
          <small className="chat-saved">{user ? 'Chat saved to your account' : 'Guest chat · not saved'}</small>
        </span>
        <button className="chat-close" onClick={() => setOpen(false)} aria-label="Close chat">
          ×
        </button>
      </header>
      <div className="chat-messages">
        {messages.map((m, i) => (
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
        ))}
        {sending && <div className="chat-msg assistant typing">…</div>}
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
