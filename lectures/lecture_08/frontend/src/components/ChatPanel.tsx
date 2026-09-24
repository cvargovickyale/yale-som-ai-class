import { useEffect, useRef, useState } from "react"
import { sendChat } from "../api"
import type { ChatMessage } from "../types"

const EXAMPLE_PROMPTS = [
  "Who teaches MGT 409?",
  "How many core courses are there?",
  "What are some good AI courses?",
]

const TOOL_ICONS: Record<string, string> = {
  search_courses: "🔎",
  web_search: "🌐",
}

let idCounter = 0
function nextId() {
  idCounter += 1
  return `msg-${idCounter}`
}

interface ChatPanelProps {
  initialMessages: ChatMessage[]
}

export default function ChatPanel({ initialMessages }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages)
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" })
  }, [messages, loading])

  async function submit(text: string) {
    const trimmed = text.trim()
    if (!trimmed || loading) return
    setMessages((prev) => [...prev, { id: nextId(), role: "user", text: trimmed }])
    setInput("")
    setLoading(true)
    try {
      const { reply, toolsUsed } = await sendChat(trimmed)
      setMessages((prev) => [...prev, { id: nextId(), role: "assistant", text: reply, toolsUsed }])
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: nextId(),
          role: "error",
          text: "The assistant desk didn't answer. Is the backend running on :8000?",
        },
      ])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  return (
    <div className="chat-panel">
      <div className="chat-history bevel-in" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="chat-empty">
            <p>Ask me about SOM courses — I can search the catalog and the web.</p>
            <div className="chat-examples">
              {EXAMPLE_PROMPTS.map((prompt) => (
                <button key={prompt} className="chip-btn bevel-raised" onClick={() => submit(prompt)}>
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`chat-bubble-row chat-role-${m.role}`}>
            <div className={`chat-bubble ${m.role === "user" ? "bevel-raised" : "bevel-in"}`}>
              <p>{m.text}</p>
              {m.toolsUsed && m.toolsUsed.length > 0 && (
                <div className="chat-tools">
                  <span className="chat-tools-label">Tools used:</span>
                  {m.toolsUsed.map((tool) => (
                    <span key={tool} className="tool-chip bevel-raised">
                      {TOOL_ICONS[tool] ?? "🛠"} {tool}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="chat-bubble-row chat-role-assistant">
            <div className="chat-bubble bevel-in chat-bubble-busy">
              <span className="busy-bar" aria-hidden />
              Consulting the registrar…
            </div>
          </div>
        )}
      </div>
      <form
        className="chat-input-row"
        onSubmit={(e) => {
          e.preventDefault()
          submit(input)
        }}
      >
        <input
          ref={inputRef}
          type="text"
          className="bevel-in"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about a course, faculty, or category..."
          disabled={loading}
        />
        <button type="submit" className="bevel-raised" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  )
}
