import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { fetchHealth, fetchPricing, fetchRoster, streamChat } from './api'
import { OrgChart } from './components/OrgChart'
import type { AgentState, ChartNode, Spark } from './components/OrgChart'
import { SpendMeter } from './components/SpendMeter'
import { niceScale, usd } from './money'
import { TraceTable } from './components/TraceTable'
import { playReplyOut, playRequestIn, setMuted, unlockAudio } from './sounds'
import type { ChatResult, Delegation, ModelName, Pricing, ProgressEvent, SpecialistMeta, Spend, Step, Usage } from './types'
import './App.css'

const BOSS_KEY = 'boss'
const BOSS_EMOJI = '🧙‍♂️'
const MODELS: ModelName[] = ['gpt-6-luna', 'gpt-6-astra']

const SAMPLES = [
  'For each Horcrux, when and how is it found or destroyed across the books?',
  "How does Harry destroy Tom Riddle's diary?",
  'Good evening, Professor! What do you see in the Mirror of Erised?',
]

const FALLBACK_WORKERS: SpecialistMeta[] = [1, 2, 3, 4, 5, 6, 7].map((n) => ({
  book_number: n,
  agent_key: `book-${n}`,
  character: `Book ${n}`,
  emoji: '📖',
  title: `Book ${n}`,
  short: `Book ${n}`,
  specialty: '',
  accent: '#888888',
  house_hint: '',
  wand: '#7a5a3a',
}))

/** What each character is called on a meter label. */
const SHORT_NAME: Record<string, string> = {
  'Ron Weasley': 'Ron',
  'Hermione Granger': 'Hermione',
  'Remus Lupin': 'Lupin',
  'Fred & George Weasley': 'Fred & George',
  'Luna Lovegood': 'Luna',
  'Severus Snape': 'Snape',
  'Neville Longbottom': 'Neville',
}

const idleAgent = (): AgentState => ({ status: 'idle', flare: 0, steps: 0, busyMs: 0, cost: 0 })

/** Untangle LLM-jammed GFM tables so remark-gfm can parse them (from the course starter). */
function normalizeAnswerMarkdown(text: string): string {
  let s = text.replace(/\r\n/g, '\n').trim()
  // Separator row on its own line: "... | |---|---|---| | next"
  s = s.replace(/\s*(\|(?:\s*:?-{3,}:?\s*\|)+)\s*/g, '\n$1\n')
  // Split jammed data rows: "...last cell | | Next row..."
  s = s.replace(/\|\s*\|(?=\s*[^|\s\-:])/g, '|\n|')
  // Blank line before a table that follows prose
  s = s.replace(/([^\n|])\n?(\|[^\n]+\|\n\|(?:\s*:?-{3,}:?\s*\|)+)/g, '$1\n\n$2')
  return s.replace(/\n{3,}/g, '\n\n')
}

function describeRequest(d: Record<string, unknown>, firstPrompt: string): string {
  const returns = (d.tool_returns as { tool: string; content: string }[] | undefined) ?? []
  const retries = (d.retries as string[] | undefined) ?? []
  const lines = [
    ...returns.map((r) => `TOOL RESULT ${r.tool}: ${r.content}`),
    ...retries.map((r) => `RETRY: ${r}`),
  ]
  return lines.length ? lines.join('\n\n') : firstPrompt || '(prompt)'
}

function describeResponse(d: Record<string, unknown>): string {
  const calls = (d.tool_calls as { tool: string; args: unknown }[] | undefined) ?? []
  const text = String(d.text ?? '')
  return [text, ...calls.map((c) => `CALL ${c.tool}(${JSON.stringify(c.args)})`)].filter(Boolean).join('\n\n') || '(no text)'
}

function usageLine(u: Usage | undefined, model: string | undefined, requests?: number) {
  if (!u) return null
  return (
    <>
      <b>{usd(u.cost_usd)}</b> on {model ?? 'model'} · {u.input_tokens.toLocaleString()} input ({u.cache_read_tokens.toLocaleString()} cached,{' '}
      {u.cache_write_tokens.toLocaleString()} cache write) · {u.output_tokens.toLocaleString()} output
      {requests != null && ` · ${requests} model calls`}
    </>
  )
}

export default function App() {
  const [bossName, setBossName] = useState('Albus Dumbledore')
  const [workers, setWorkers] = useState<SpecialistMeta[]>([])
  const [health, setHealth] = useState<{ ok: boolean; key?: boolean } | null>(null)
  const [pricing, setPricing] = useState<Pricing | null>(null)

  const [model, setModel] = useState<ModelName>('gpt-6-luna')
  const [budgetText, setBudgetText] = useState('')
  const [message, setMessage] = useState(SAMPLES[0])
  const [asked, setAsked] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<ChatResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [agents, setAgents] = useState<Record<string, AgentState>>({})
  const [steps, setSteps] = useState<Step[]>([])
  const [spend, setSpend] = useState<Spend | null>(null)
  const [activeEdges, setActiveEdges] = useState<Record<string, number>>({})
  const [sparks, setSparks] = useState<Spark[]>([])
  const [filter, setFilter] = useState<string | null>(null)
  const [muted, setMutedState] = useState(false)
  const [elapsed, setElapsed] = useState(0)

  const sparkId = useRef(0)
  const rowId = useRef(0)
  const running = useRef<Record<string, number>>({}) // open delegations per worker
  const openLlm = useRef<Record<string, number[]>>({}) // agent_key → trace rows awaiting a model response
  const delegateRows = useRef<Record<number, { id: number; t: number }>>({}) // delegation index → trace row
  const firstPrompt = useRef<Record<string, string>>({})
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
      .then((h) => setHealth({ ok: h.ok, key: h.portkey_key_set }))
      .catch(() => setHealth({ ok: false }))
    fetchPricing()
      .then((p) => {
        setPricing(p)
        setModel(p.default_model)
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!busy) return
    const id = window.setInterval(() => setElapsed((performance.now() - startedAt.current) / 1000), 100)
    return () => window.clearInterval(id)
  }, [busy])

  const boss: ChartNode = useMemo(
    () => ({ agent_id: BOSS_KEY, name: bossName, emoji: BOSS_EMOJI, subtitle: 'Headmaster · boss agent', accent: '#6b4fbf', wand: '#d8cfb8' }),
    [bossName],
  )
  const roster = workers.length ? workers : FALLBACK_WORKERS
  const workerNodes: ChartNode[] = useMemo(
    () =>
      roster.map((w) => ({
        agent_id: w.agent_key,
        name: w.character,
        emoji: w.emoji,
        subtitle: `Book ${w.book_number} · ${w.short}`,
        accent: w.accent,
        wand: w.wand,
      })),
    [roster],
  )
  const emojiFor = useCallback(
    (key: string) => (key === BOSS_KEY ? BOSS_EMOJI : roster.find((w) => w.agent_key === key)?.emoji ?? '❔'),
    [roster],
  )
  const pitchFor = useCallback(
    (key: string) => {
      const n = roster.find((w) => w.agent_key === key)?.book_number
      return n ? 1 + (n - 4) * 0.04 : 0.85
    },
    [roster],
  )

  const budget = useMemo(() => {
    const v = Number.parseFloat(budgetText)
    return budgetText.trim() && Number.isFinite(v) && v > 0 ? v : null
  }, [budgetText])
  const budgetInvalid = budgetText.trim() !== '' && budget === null

  function patchAgent(key: string, patch: (a: AgentState) => Partial<AgentState>) {
    setAgents((prev) => {
      const cur = prev[key] ?? idleAgent()
      return { ...prev, [key]: { ...cur, ...patch(cur) } }
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

  function addRow(row: Omit<Step, 'step_id'>): number {
    rowId.current += 1
    const id = rowId.current
    setSteps((prev) => [...prev, { ...row, step_id: id }])
    return id
  }

  function patchRow(id: number, patch: Partial<Step>) {
    setSteps((prev) => prev.map((s) => (s.step_id === id ? { ...s, ...patch } : s)))
  }

  function onEvent(ev: ProgressEvent) {
    const d = ev.data as Record<string, unknown>
    const key = String(d.agent_key ?? '')
    const t = Number(d.t_ms ?? 0) / 1000

    switch (ev.type) {
      case 'boss_thinking':
        patchAgent(BOSS_KEY, (a) => ({ status: 'working', flare: a.flare + 1 }))
        bumpEdge(BOSS_KEY, 1)
        fireSpark(BOSS_KEY, 'down')
        playRequestIn(pitchFor(BOSS_KEY))
        break

      case 'agent_step': {
        const agent = String(d.agent ?? key)
        if (d.kind === 'user_prompt') {
          firstPrompt.current[key] = String(d.prompt ?? '')
        } else if (d.kind === 'model_request') {
          const id = addRow({ agent_key: key, agent, kind: 'llm', label: `model call · step ${d.step}`, input: describeRequest(d, firstPrompt.current[key]), started: t })
          ;(openLlm.current[key] ??= []).push(id)
          patchAgent(key, (a) => ({ flare: a.flare + 1 }))
        } else if (d.kind === 'model_response') {
          const id = openLlm.current[key]?.shift()
          const usage = d.usage as Usage | undefined
          const patch: Partial<Step> = { output: describeResponse(d), status: 'done', duration_ms: d.duration_ms as number, usage, model: String(d.model ?? '') }
          if (id) patchRow(id, patch)
          patchAgent(key, (a) => ({
            steps: a.steps + 1,
            busyMs: a.busyMs + Number(d.duration_ms ?? 0),
            cost: a.cost + (usage?.cost_usd ?? 0),
          }))
        } else if (d.kind === 'retrieval') {
          const chunks = (d.chunks as { chapter: string }[] | undefined) ?? []
          const chapters = [...new Set(chunks.map((c) => c.chapter))]
          addRow({
            agent_key: key,
            agent,
            kind: 'search',
            label: d.follow_up ? 'search_book' : 'initial retrieval',
            input: String(d.query ?? ''),
            started: t,
            output: `${chunks.length} passages · ${Number(d.evidence_chars ?? 0).toLocaleString()} chars\n${chapters.join('\n')}`,
            status: 'done',
            passages: chunks.length,
          })
          patchAgent(key, (a) => ({ steps: a.steps + 1, flare: a.flare + 1 }))
        }
        break
      }

      case 'specialist_started': {
        const id = addRow({ agent_key: BOSS_KEY, agent: bossName, kind: 'delegate', label: `ask ${d.agent}`, input: String(d.question ?? ''), started: t })
        delegateRows.current[Number(d.index)] = { id, t }
        running.current[key] = (running.current[key] ?? 0) + 1
        patchAgent(key, (a) => ({ status: 'working', flare: a.flare + 1 }))
        bumpEdge(key, 1)
        fireSpark(key, 'down')
        playRequestIn(pitchFor(key))
        break
      }

      case 'specialist_done': {
        const row = delegateRows.current[Number(d.index)]
        const failed = d.status === 'error'
        if (row) patchRow(row.id, { output: String(d.reply ?? ''), status: failed ? 'error' : 'done', duration_ms: Math.round((t - row.t) * 1000), passages: d.passages_used as number | undefined })
        const left = Math.max(0, (running.current[key] ?? 1) - 1)
        running.current[key] = left
        bumpEdge(key, -1)
        patchAgent(key, () => ({ status: left > 0 ? 'working' : failed ? 'error' : 'done' }))
        fireSpark(key, 'up')
        playReplyOut(pitchFor(key))
        break
      }

      case 'spend':
        setSpend(d as unknown as Spend)
        break

      case 'final':
      case 'error':
        if (d.spend) setSpend(d.spend as Spend)
        // Calls cut off by a budget stop (or an error) never report back; close their rows.
        setSteps((prev) => prev.map((s) => (s.status ? s : { ...s, status: 'error', output: s.output ?? 'Stopped before finishing.' })))
        patchAgent(BOSS_KEY, () => ({ status: ev.type === 'error' ? 'error' : 'done' }))
        setActiveEdges({})
        fireSpark(BOSS_KEY, 'up')
        playReplyOut(pitchFor(BOSS_KEY))
        break
    }
  }

  async function onSubmit(e?: FormEvent) {
    e?.preventDefault()
    const q = message.trim()
    if (!q || busy || budgetInvalid) return
    void unlockAudio()
    setAsked(q)
    setMessage('')
    setResult(null)
    setError(null)
    setSteps([])
    setSpend(null)
    setAgents({})
    setActiveEdges({})
    running.current = {}
    rowId.current = 0
    openLlm.current = {}
    delegateRows.current = {}
    firstPrompt.current = {}
    setFilter(null)
    setElapsed(0)
    startedAt.current = performance.now()
    setBusy(true)
    try {
      setResult(await streamChat(q, model, budget, onEvent))
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
      patchAgent(BOSS_KEY, () => ({ status: 'error' }))
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

  // Meter scales: the budget if one is set, otherwise a "nice" ceiling above the current spend.
  const total = spend?.total
  const jobBudget = spend?.budget_usd ?? budget
  const maxAgentCost = Math.max(0, ...Object.values(spend?.agents ?? {}).map((a) => a.cost_usd ?? 0))
  const totalScale = jobBudget ?? niceScale(total?.cost_usd ?? 0)
  const agentScale = jobBudget ?? niceScale(maxAgentCost)
  const exceeded = !!spend?.budget_exceeded
  const prices = pricing?.models[model]
  const delegations: Delegation[] = result?.delegations ?? []
  const modelCalls = steps.filter((s) => s.kind === 'llm' && s.status).length

  return (
    <div className="desktop">
      <div className="window app-window">
        <div className="titlebar">
          <span className="title">🪄 Dumbledore's Office — Tokenomics Dashboard</span>
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
                workers={workerNodes}
                agents={agents}
                activeEdges={activeEdges}
                sparks={sparks}
                selected={filter}
                onSelect={(id) => setFilter((cur) => (cur === id ? null : id))}
              />
            </div>
          </fieldset>

          <fieldset className="group meters-group">
            <legend>
              Gringotts ledger — live spend{' '}
              {jobBudget ? `· thermometers fill toward your ${usd(jobBudget)} budget` : `· no budget set, scale auto-adjusts (total ${usd(totalScale)}, agents ${usd(agentScale)})`}
            </legend>
            <div className="meters">
              <SpendMeter label="Total" emoji="💰" usage={total} scale={totalScale} accent="#e0a800" over={exceeded} active={busy} isTotal />
              <SpendMeter
                label="Dumbledore"
                emoji={BOSS_EMOJI}
                usage={spend?.agents[BOSS_KEY]}
                scale={agentScale}
                accent="#6b4fbf"
                over={exceeded}
                active={agents[BOSS_KEY]?.status === 'working'}
              />
              {roster.map((w) => (
                <SpendMeter
                  key={w.agent_key}
                  label={SHORT_NAME[w.character] ?? w.character}
                  emoji={w.emoji}
                  usage={spend?.agents[w.agent_key]}
                  scale={agentScale}
                  accent={w.accent}
                  over={exceeded}
                  active={agents[w.agent_key]?.status === 'working'}
                />
              ))}
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
                  <div className="controls">
                    <label>
                      Model{' '}
                      <select value={model} onChange={(e) => setModel(e.target.value as ModelName)} disabled={busy}>
                        {MODELS.map((m) => (
                          <option key={m} value={m}>
                            {m}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className={budgetInvalid ? 'invalid' : ''}>
                      Budget USD{' '}
                      <input
                        type="number"
                        min="0"
                        step="any"
                        inputMode="decimal"
                        placeholder="no cap"
                        value={budgetText}
                        onChange={(e) => setBudgetText(e.target.value)}
                        disabled={busy}
                        aria-describedby="budget-help"
                      />
                    </label>
                  </div>
                  <p id="budget-help" className="hint">
                    {budgetInvalid ? 'Enter a positive dollar amount, or leave it blank for no cap.' : 'The whole job stops once total spend reaches this. Leave blank for no cap.'}
                  </p>
                  {prices && (
                    <p className="price-legend">
                      <b>{model}</b> per 1M tokens: input ${prices.input} · cached ${prices.cached} · cache write ${prices.cache_write} · output ${prices.output}
                      {pricing && (
                        <>
                          {' '}
                          ·{' '}
                          <a href={pricing.source} target="_blank" rel="noreferrer">
                            source
                          </a>
                        </>
                      )}
                    </p>
                  )}
                  <div className="ask-row">
                    <button type="submit" className="btn default" disabled={busy || !message.trim() || budgetInvalid}>
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
                  {busy && (
                    <p className="pending">
                      <span className="hourglass">⌛</span> The Headmaster is consulting his staff… {usd(total?.cost_usd)} so far
                    </p>
                  )}
                  {error && <p className="error">{error}</p>}
                  {result?.budget_exceeded && (
                    <p className="budget-banner">
                      🛑 Budget reached: spent {usd(result.spend?.total_usd)} against a {usd(result.spend?.budget_usd)} cap. The run was stopped. (A call already in flight can push spend slightly past the cap.)
                    </p>
                  )}
                  {result && (
                    <div className="markdown">
                      <Markdown remarkPlugins={[remarkGfm]}>{normalizeAnswerMarkdown(result.answer)}</Markdown>
                    </div>
                  )}
                  {result?.usage?.total && <p className="usage-line">💰 {usageLine({ ...result.usage.total, cost_usd: result.usage.total.cost_usd ?? result.spend?.total_usd }, result.spend?.model, result.usage.total.requests)}</p>}
                  {!asked && <p className="muted">Ask a question to begin.</p>}
                  {delegations.length > 0 && !busy && (
                    <details className="reports" open={result?.budget_exceeded}>
                      <summary>Specialist reports ({delegations.length})</summary>
                      {delegations.map((d, i) => (
                        <article key={i} className={`report ${d.status}`}>
                          <header>
                            {emojiFor(`book-${d.book_number}`)} <b>{d.agent}</b> · {d.book_title} · {usd(spend?.agents[`book-${d.book_number}`]?.cost_usd)}
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
              <legend>Live trace — every step in every agent loop, with cost (click a row for details)</legend>
              <TraceTable steps={steps} emojiFor={emojiFor} filter={filter} onClearFilter={() => setFilter(null)} />
            </fieldset>
          </div>
        </div>

        <div className="statusbar">
          <span className={`cell ${health?.ok ? '' : 'bad'}`}>API {health === null ? '…' : health.ok ? 'up' : 'down'}</span>
          <span className={`cell ${health?.key ? '' : 'bad'}`}>Portkey key {health?.key ? 'set' : 'missing'}</span>
          <span className="cell">Model: {spend?.model ?? model}</span>
          <span className="cell">{busy ? '⏳ ' : ''}Elapsed {elapsed.toFixed(1)}s</span>
          <span className={`cell ${exceeded ? 'bad' : ''}`}>
            Spent {usd(total?.cost_usd)}
            {jobBudget ? ` / ${usd(jobBudget)}` : ''}
          </span>
          <span className="cell">
            {modelCalls} model calls · {(total?.input_tokens ?? 0).toLocaleString()} in ({(total?.cache_read_tokens ?? 0).toLocaleString()} cached) · {(total?.output_tokens ?? 0).toLocaleString()} out
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
