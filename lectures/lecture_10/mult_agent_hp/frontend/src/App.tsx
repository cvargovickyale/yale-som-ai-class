import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { AuthError, fetchAuthStatus, fetchHealth, fetchRoster, login, savedPassword, streamChat } from './api'
import { OrgChart } from './components/OrgChart'
import type { AgentState, ChartNode, Spark } from './components/OrgChart'
import { TraceTable } from './components/TraceTable'
import { playReplyOut, playRequestIn, setMuted, unlockAudio } from './sounds'
import type { Delegation, ProgressEvent, SpecialistMeta, Step } from './types'
import './App.css'

const BOSS_ID = 'boss'

const SAMPLES = [
  'For each Horcrux, when and how is it found or destroyed across the books?',
  "How does Harry destroy Tom Riddle's diary?",
  'Good evening, Professor! What do you see in the Mirror of Erised?',
]

const FALLBACK_WORKERS: SpecialistMeta[] = [1, 2, 3, 4, 5, 6, 7].map((n) => ({
  book_number: n,
  agent_id: `book${n}`,
  character: `Book ${n}`,
  emoji: '📖',
  title: `Book ${n}`,
  short: `Book ${n}`,
  specialty: '',
  accent: '#888888',
  house_hint: '',
  wand: '#7a5a3a',
}))

const idleAgent = (): AgentState => ({ status: 'idle', flare: 0, steps: 0, busyMs: 0, tokens: 0 })

export default function App() {
  const [bossName, setBossName] = useState('Albus Dumbledore')
  const [workers, setWorkers] = useState<SpecialistMeta[]>([])
  const [health, setHealth] = useState<{ ok: boolean; model?: string; key?: boolean } | null>(null)

  const [message, setMessage] = useState(SAMPLES[0])
  const [asked, setAsked] = useState('')
  const [busy, setBusy] = useState(false)
  const [answer, setAnswer] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [delegations, setDelegations] = useState<Delegation[]>([])

  const [agents, setAgents] = useState<Record<string, AgentState>>({})
  const [steps, setSteps] = useState<Step[]>([])
  const [activeEdges, setActiveEdges] = useState<Record<string, number>>({})
  const [sparks, setSparks] = useState<Spark[]>([])
  const [filter, setFilter] = useState<string | null>(null)
  const [muted, setMutedState] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [needLogin, setNeedLogin] = useState(false)

  const sparkId = useRef(0)
  const running = useRef<Record<string, number>>({}) // open delegations per worker
  const startedAt = useRef(0)
  const textarea = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    fetchRoster()
      .then((r) => {
        setBossName(r.boss)
        setWorkers(r.specialists)
      })
      .catch(() => setWorkers(FALLBACK_WORKERS))
    fetchHealth()
      .then((h) => setHealth({ ok: h.ok, model: h.model, key: h.portkey_key_set }))
      .catch(() => setHealth({ ok: false }))
    fetchAuthStatus()
      .then((a) => setNeedLogin(a.password_required && !savedPassword()))
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!busy) return
    const id = window.setInterval(() => setElapsed((performance.now() - startedAt.current) / 1000), 100)
    return () => window.clearInterval(id)
  }, [busy])

  const boss: ChartNode = useMemo(
    () => ({ agent_id: BOSS_ID, name: bossName, emoji: '🧙‍♂️', subtitle: 'Headmaster · boss agent', accent: '#6b4fbf', wand: '#d8cfb8' }),
    [bossName],
  )
  const workerNodes: ChartNode[] = useMemo(
    () =>
      workers.map((w) => ({
        agent_id: w.agent_id,
        name: w.character,
        emoji: w.emoji,
        subtitle: `Book ${w.book_number} · ${w.short}`,
        accent: w.accent,
        wand: w.wand,
      })),
    [workers],
  )
  const emojiFor = useCallback(
    (id: string) => (id === BOSS_ID ? '🧙‍♂️' : workers.find((w) => w.agent_id === id)?.emoji ?? '❔'),
    [workers],
  )
  const pitchFor = useCallback(
    (id: string) => {
      const n = workers.find((w) => w.agent_id === id)?.book_number
      return n ? 1 + (n - 4) * 0.04 : 0.85
    },
    [workers],
  )

  function patchAgent(id: string, patch: (a: AgentState) => Partial<AgentState>) {
    setAgents((prev) => {
      const cur = prev[id] ?? idleAgent()
      return { ...prev, [id]: { ...cur, ...patch(cur) } }
    })
  }

  function bumpEdge(edge: string, delta: number) {
    setActiveEdges((prev) => ({ ...prev, [edge]: Math.max(0, (prev[edge] ?? 0) + delta) }))
  }

  function fireSpark(edge: string, dir: Spark['dir']) {
    sparkId.current += 1
    const id = sparkId.current
    setSparks((prev) => [...prev, { id, edge, dir }])
    window.setTimeout(() => setSparks((prev) => prev.filter((s) => s.id !== id)), 1000)
  }

  function onEvent(ev: ProgressEvent) {
    const d = ev.data as Record<string, unknown>
    const agentId = String(d.agent_id ?? '')

    switch (ev.type) {
      case 'boss_thinking':
        patchAgent(BOSS_ID, (a) => ({ status: 'working', flare: a.flare + 1 }))
        bumpEdge(BOSS_ID, 1)
        fireSpark(BOSS_ID, 'down')
        playRequestIn(pitchFor(BOSS_ID))
        break

      case 'step_started': {
        const step = d as unknown as Step
        setSteps((prev) => [...prev, step])
        patchAgent(agentId, (a) => ({ flare: a.flare + 1 }))
        break
      }

      case 'step_done': {
        const step = d as unknown as Step
        setSteps((prev) => prev.map((s) => (s.step_id === step.step_id ? { ...s, ...step } : s)))
        patchAgent(agentId, (a) => ({
          steps: a.steps + 1,
          // Delegation time is waiting on a worker, so it doesn't count as the boss's own work.
          busyMs: step.kind === 'delegate' ? a.busyMs : a.busyMs + (step.duration_ms ?? 0),
          tokens: a.tokens + (step.input_tokens ?? 0) + (step.output_tokens ?? 0),
        }))
        break
      }

      case 'specialist_started':
        setDelegations((prev) => [...prev, d as unknown as Delegation])
        running.current[agentId] = (running.current[agentId] ?? 0) + 1
        patchAgent(agentId, (a) => ({ status: 'working', flare: a.flare + 1 }))
        bumpEdge(agentId, 1)
        fireSpark(agentId, 'down')
        playRequestIn(pitchFor(agentId))
        break

      case 'specialist_done': {
        const idx = Number(d.index)
        setDelegations((prev) => prev.map((x, i) => (i === idx ? (d as unknown as Delegation) : x)))
        const left = Math.max(0, (running.current[agentId] ?? 1) - 1)
        running.current[agentId] = left
        bumpEdge(agentId, -1)
        patchAgent(agentId, () => ({ status: left > 0 ? 'working' : d.status === 'error' ? 'error' : 'done' }))
        fireSpark(agentId, 'up')
        playReplyOut(pitchFor(agentId))
        break
      }

      case 'final':
      case 'error':
        patchAgent(BOSS_ID, () => ({ status: ev.type === 'error' ? 'error' : 'done' }))
        setActiveEdges({})
        fireSpark(BOSS_ID, 'up')
        playReplyOut(pitchFor(BOSS_ID))
        break
    }
  }

  async function onSubmit(e?: FormEvent) {
    e?.preventDefault()
    const q = message.trim()
    if (!q || busy) return
    void unlockAudio()
    setAsked(q)
    setMessage('')
    setAnswer('')
    setError(null)
    setDelegations([])
    setSteps([])
    setAgents({})
    setActiveEdges({})
    running.current = {}
    setFilter(null)
    setElapsed(0)
    startedAt.current = performance.now()
    setBusy(true)
    try {
      const result = await streamChat(q, onEvent)
      setAnswer(result.answer)
      if (result.delegations) setDelegations(result.delegations)
    } catch (err) {
      if (err instanceof AuthError) {
        setNeedLogin(true)
        setMessage(q)
      }
      setError(err instanceof Error ? err.message : String(err))
      patchAgent(BOSS_ID, () => ({ status: 'error' }))
      setActiveEdges({})
    } finally {
      setElapsed((performance.now() - startedAt.current) / 1000)
      setBusy(false)
      textarea.current?.focus()
    }
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void onSubmit()
    }
  }

  const doneSteps = steps.filter((s) => s.status)
  const totalTokens = doneSteps.reduce((n, s) => n + (s.input_tokens ?? 0) + (s.output_tokens ?? 0), 0)
  const modelCalls = doneSteps.filter((s) => s.kind === 'llm').length

  return (
    <div className="desktop">
      {needLogin && <LoginDialog onDone={() => setNeedLogin(false)} />}
      <div className="window app-window">
        <div className="titlebar">
          <span className="title">🪄 Dumbledore's Office — Multi-Agent Dashboard</span>
          <span className="title-buttons" aria-hidden>
            <span>_</span>
            <span>□</span>
            <span>×</span>
          </span>
        </div>

        <div className="app-body">
          <fieldset className="group chart-group">
            <legend>Agent org chart — wands light while an agent works · gold spark = task sent · blue spark = result returned</legend>
            <div className="chart-scroll">
              <OrgChart
                boss={boss}
                workers={workerNodes.length ? workerNodes : FALLBACK_WORKERS.map((w) => ({ agent_id: w.agent_id, name: w.character, emoji: w.emoji, subtitle: w.short, accent: w.accent, wand: w.wand }))}
                agents={agents}
                activeEdges={activeEdges}
                sparks={sparks}
                selected={filter}
                onSelect={(id) => setFilter((cur) => (cur === id ? null : id))}
              />
            </div>
          </fieldset>

          <div className="columns">
            <div className="left-col">
              <fieldset className="group">
                <legend>Ask the Headmaster</legend>
                <form onSubmit={onSubmit} className="ask">
                  <textarea
                    ref={textarea}
                    rows={3}
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyDown={onKeyDown}
                    disabled={busy}
                    placeholder="Ask about the Harry Potter books…"
                  />
                  <div className="ask-row">
                    <button type="submit" className="btn default" disabled={busy || !message.trim()}>
                      {busy ? 'Owl in flight…' : 'Send owl'}
                    </button>
                    <span className="hint">Enter to send · Shift+Enter for a new line</span>
                  </div>
                  <div className="samples">
                    {SAMPLES.map((s) => (
                      <button key={s} type="button" className="btn small" disabled={busy} onClick={() => setMessage(s)}>
                        {s.length > 38 ? `${s.slice(0, 38)}…` : s}
                      </button>
                    ))}
                  </div>
                </form>
              </fieldset>

              <fieldset className="group answer-group">
                <legend>Dumbledore's answer</legend>
                <div className="answer-box">
                  {asked && <p className="asked">“{asked}”</p>}
                  {busy && !answer && (
                    <p className="pending">
                      <span className="hourglass">⌛</span> The Headmaster is consulting his staff…
                    </p>
                  )}
                  {error && <p className="error">{error}</p>}
                  {answer && (
                    <div className="markdown">
                      <Markdown remarkPlugins={[remarkGfm]}>{answer}</Markdown>
                    </div>
                  )}
                  {!asked && <p className="muted">Ask a question to begin.</p>}
                  {delegations.length > 0 && !busy && (
                    <details className="reports">
                      <summary>Specialist reports ({delegations.length})</summary>
                      {delegations.map((d, i) => (
                        <article key={i} className={`report ${d.status}`}>
                          <header>
                            {emojiFor(workers.find((w) => w.book_number === d.book_number)?.agent_id ?? '')} <b>{d.agent}</b> · {d.book_title}
                          </header>
                          <p>
                            <i>Asked:</i> {d.question}
                          </p>
                          <p>
                            <i>Replied:</i> {d.reply}
                          </p>
                        </article>
                      ))}
                    </details>
                  )}
                </div>
              </fieldset>
            </div>

            <fieldset className="group trace-group">
              <legend>Live trace — every step in every agent loop (click a row for full input/output)</legend>
              <TraceTable steps={steps} emojiFor={emojiFor} filter={filter} onClearFilter={() => setFilter(null)} />
            </fieldset>
          </div>
        </div>

        <div className="statusbar">
          <span className={`cell ${health?.ok ? '' : 'bad'}`}>API {health === null ? '…' : health.ok ? 'up' : 'down'}</span>
          <span className={`cell ${health?.key ? '' : 'bad'}`}>Portkey key {health?.key ? 'set' : 'missing'}</span>
          <span className="cell">Model: {health?.model ?? '…'}</span>
          <span className="cell">{busy ? '⏳ ' : ''}Elapsed {elapsed.toFixed(1)}s</span>
          <span className="cell">
            {steps.length} steps · {modelCalls} model calls · {totalTokens.toLocaleString()} tokens
          </span>
          <button
            type="button"
            className="cell sound-toggle"
            onClick={() => {
              setMuted(!muted)
              setMutedState(!muted)
              void unlockAudio()
            }}
          >
            {muted ? '🔇 Sound off' : '🔊 Sound on'}
          </button>
        </div>
      </div>
    </div>
  )
}

function LoginDialog({ onDone }: { onDone: () => void }) {
  const [password, setPassword] = useState('')
  const [checking, setChecking] = useState(false)
  const [wrong, setWrong] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setChecking(true)
    const ok = await login(password).catch(() => false)
    setChecking(false)
    if (ok) onDone()
    else setWrong(true)
  }

  return (
    <div className="modal-backdrop">
      <form className="window login" onSubmit={submit}>
        <div className="titlebar">
          <span className="title">🔒 Enter Password</span>
        </div>
        <div className="login-body">
          <p>
            <span className="login-icon">🦉</span>
            The Headmaster's office is password protected. Enter the password you were given.
          </p>
          <input
            type="password"
            autoFocus
            value={password}
            onChange={(e) => {
              setPassword(e.target.value)
              setWrong(false)
            }}
            aria-label="Password"
          />
          {wrong && <p className="error">That's not it. Try again.</p>}
          <div className="login-actions">
            <button type="submit" className="btn default" disabled={!password || checking}>
              {checking ? 'Checking…' : 'OK'}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
