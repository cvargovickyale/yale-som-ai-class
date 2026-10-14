import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, ApiError, type AgentEvent, type AgentName, type Board, type Cash, type Ticket } from './api'
import { AgentModal } from './components/AgentModal'
import { AgentsPanel } from './components/AgentsPanel'
import { CashCard } from './components/CashCard'
import { OverdueTicker } from './components/OverdueTicker'
import { DonePile } from './components/DonePile'
import { Icon } from './components/Icon'
import { Modal } from './components/Modal'
import { ReviewModal } from './components/ReviewModal'
import { TicketCard, needsYou, type CardPhase } from './components/TicketCard'
import { agentName, describe, longDate, timeOf, usd } from './format'
import { prefersReducedMotion, useLocalStorage } from './hooks'

// Events that mean the board or the cash changed, so we refetch them.
const CHANGES = new Set(['agent_finished', 'run_finished', 'payment_approved', 'payment_rejected', 'ticket_resolved', 'reset'])

type Toast = { id: number; text: string; tone: 'ok' | 'warn' }

export default function App() {
  const [board, setBoard] = useState<Board | null>(null)
  const [cash, setCash] = useState<Cash | null>(null)
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [offline, setOffline] = useState(false)
  const [approver, setApprover] = useLocalStorage('cc-approver', '')
  const [reviewId, setReviewId] = useState<number | null>(null)
  const [agentOpen, setAgentOpen] = useState<AgentName | null>(null)
  const [confirmReset, setConfirmReset] = useState(false)
  const [about, setAbout] = useState(false)
  const [phases, setPhases] = useState<Record<number, CardPhase>>({})
  const [landed, setLanded] = useState<number | null>(null)
  const [toasts, setToasts] = useState<Toast[]>([])
  const lastSeq = useRef(0)

  const toast = useCallback((text: string, tone: Toast['tone'] = 'ok') => {
    const id = Date.now() + Math.random()
    setToasts(t => [...t, { id, text, tone }])
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 4500)
  }, [])

  const refresh = useCallback(async () => {
    try {
      const [b, c] = await Promise.all([api.board(), api.cash()])
      setBoard(b); setCash(c); setOffline(false)
    } catch { setOffline(true) }
  }, [])

  const running = board?.tickets.some(t => t.run?.status === 'running') ?? false

  // Poll the live event feed: quickly while the team works, gently otherwise.
  useEffect(() => {
    let stop = false
    let ticks = 0
    refresh()
    const loop = async () => {
      if (stop) return
      ticks++
      try {
        const { events: fresh, last_seq } = await api.events(lastSeq.current)
        if (last_seq < lastSeq.current) lastSeq.current = 0 // backend restarted
        if (fresh.length) {
          lastSeq.current = Math.max(lastSeq.current, fresh.at(-1)!.seq)
          // Two overlapping polls (the loop restarts when a run starts or ends) can fetch
          // the same events; keep each seq once, in order.
          setEvents(e => {
            const seen = new Set(e.map(x => x.seq))
            return [...e, ...fresh.filter(x => !seen.has(x.seq))].sort((a, b) => a.seq - b.seq).slice(-400)
          })
        }
        if (fresh.some(e => CHANGES.has(e.type)) || ticks % 4 === 0) await refresh()
        setOffline(false)
      } catch { setOffline(true) }
      if (!stop) setTimeout(loop, running ? 1200 : 3000)
    }
    const t = setTimeout(loop, 600)
    return () => { stop = true; clearTimeout(t) }
  }, [refresh, running])

  const tickets = board?.tickets ?? []
  const open = tickets.filter(t => t.status === 'open' || phases[t.id])
  const done = tickets.filter(t => t.status === 'resolved' && !phases[t.id])
  const waitingOnYou = open.reduce((n, t) => n + needsYou(t), 0)
  const reviewTicket = tickets.find(t => t.id === reviewId) ?? null
  const lastEventFor = useMemo(() => {
    const m = new Map<number, AgentEvent>()
    for (const e of events) if (e.ticket_id !== null && describe(e) && e.type !== 'run_started') m.set(e.ticket_id, e)
    return m
  }, [events])
  const recent = events.filter(e => describe(e)).slice(-8).reverse()

  const fail = (e: unknown) => toast(e instanceof ApiError ? e.message : 'Something went wrong. Is the backend running?', 'warn')
  const needName = () => { if (!approver.trim()) { toast('Add your name at the top first, so the approval is recorded.', 'warn'); return true } return false }

  async function startTeam(t: Ticket) {
    try { await api.run(t.id); toast(`The team is on ticket ${t.id}.`); await refresh() } catch (e) { fail(e) }
  }
  async function approvePayment(id: number) {
    if (needName()) return
    try {
      const r = await api.approvePayment(id, approver.trim())
      toast(`Paid ${usd(r.amount)} to ${r.payee}. Checking is now ${usd(r.balance_after)}.`)
      await refresh()
    } catch (e) { fail(e) }
  }
  async function rejectPayment(id: number) {
    if (needName()) return
    try { await api.rejectPayment(id, approver.trim()); toast('Payment rejected. No money moved.'); await refresh() } catch (e) { fail(e) }
  }
  async function closeTicket(decisionId: number) {
    if (needName() || reviewId === null) return
    const id = reviewId
    try {
      await api.approveDecision(decisionId, approver.trim())
    } catch (e) { fail(e); return }
    setReviewId(null)
    const still = prefersReducedMotion()
    setPhases(p => ({ ...p, [id]: 'closing' }))
    setTimeout(() => setPhases(p => ({ ...p, [id]: 'flying' })), still ? 0 : 1100)
    setTimeout(async () => {
      await refresh()
      setPhases(p => { const n = { ...p }; delete n[id]; return n })
      setLanded(id)
      toast(`Ticket ${id} is done.`)
      setTimeout(() => setLanded(l => (l === id ? null : l)), 1600)
    }, still ? 300 : 1750)
  }
  async function reset() {
    setConfirmReset(false)
    try { const r = await api.reset(); setPhases({}); toast(`Fresh start. Checking is back to ${usd(r.checking_balance)}.`); await refresh() } catch (e) { fail(e) }
  }

  return (
    <div className="desk">
      <header className="top">
        <div className="brand">
          <span className="logo" aria-hidden="true"><Icon name="check" size={18} /></span>
          <div>
            <h1>Campus Customs Desk</h1>
            <p className="muted">{board ? longDate(board.date_today) : 'Loading…'} · shop date</p>
          </div>
        </div>
        <div className="top-actions">
          <label className="approver">
            <span>Approving as</span>
            <input value={approver} onChange={e => setApprover(e.target.value)} placeholder="Your name" maxLength={80} />
          </label>
          <button className="btn btn-quiet" onClick={() => setAbout(true)}><Icon name="info" size={16} /> How it works</button>
          <button className="btn btn-quiet" onClick={() => setConfirmReset(true)} disabled={running}><Icon name="refresh" size={16} /> Reset</button>
        </div>
      </header>

      {offline && (
        <p className="banner" role="status"><Icon name="alert" size={16} /> Can't reach the backend. Start the MCP server and <code>uvicorn main:app --port 8000</code>, then this page reconnects by itself.</p>
      )}

      <OverdueTicker cash={cash} />

      <section className="hero">
        <CashCard cash={cash} />
        <div className="today">
          <p className="eyebrow">Today on the desk</p>
          <div className="stats">
            <div><strong>{open.length}</strong><span>open</span></div>
            <div className={waitingOnYou ? 'attn' : ''}><strong>{waitingOnYou}</strong><span>waiting on you</span></div>
            <div className="ok"><strong>{done.length}</strong><span>done</span></div>
          </div>
          <p className="muted">Pick a ticket and start the team. Agents look things up and propose; nothing is paid, ordered, or sent until you say so.</p>
        </div>
      </section>

      <main className="grid">
        <section className="panel" aria-labelledby="open-h">
          <div className="panel-head"><h2 id="open-h">On the desk</h2><span className="count">{open.length}</span></div>
          {open.length === 0 ? (
            <div className="all-clear"><Icon name="check" size={28} /><p>All clear. Every ticket is in the Done pile.</p></div>
          ) : (
            <div className="tickets">
              {open.map(t => (
                <TicketCard key={t.id} ticket={t} lastEvent={lastEventFor.get(t.id)} busy={running}
                  phase={phases[t.id] ?? 'idle'} onRun={() => startTeam(t)} onReview={() => setReviewId(t.id)} />
              ))}
            </div>
          )}
        </section>

        <AgentsPanel events={events} onOpen={setAgentOpen} />

        <DonePile tickets={done} landed={landed} onOpen={t => setReviewId(t.id)} />
      </main>

      <section className="panel activity" aria-labelledby="act-h">
        <div className="panel-head"><h2 id="act-h">Recent activity</h2></div>
        {recent.length === 0 ? <p className="muted">Quiet so far.</p> : (
          <ol className="feed">
            {recent.map(e => (
              <li key={e.seq}>
                <time>{timeOf(e.at)}</time>
                <p>{e.agent && !e.type.startsWith('run_') ? <strong>{agentName(e.agent)} </strong> : null}{describe(e)}{e.ticket_id && !e.type.startsWith('run_') && e.type !== 'ticket_resolved' ? <span className="muted"> · #{e.ticket_id}</span> : null}</p>
              </li>
            ))}
          </ol>
        )}
      </section>

      {reviewTicket && (
        <ReviewModal ticket={reviewTicket} cash={cash} approver={approver.trim()} onClose={() => setReviewId(null)}
          onApprovePayment={approvePayment} onRejectPayment={rejectPayment} onCloseTicket={closeTicket} />
      )}
      {agentOpen && <AgentModal agent={agentOpen} events={events} onClose={() => setAgentOpen(null)} />}
      {confirmReset && (
        <Modal title="Start fresh?" eyebrow="Reset" onClose={() => setConfirmReset(false)} footer={<>
          <button className="btn btn-quiet" onClick={() => setConfirmReset(false)}>Keep working</button>
          <button className="btn btn-primary" onClick={reset}>Reset the desk</button>
        </>}>
          <p>This copies the original shop data back over the working copy: all three tickets reopen, checking returns to $3,400, and every pending payment, draft, and decision is cleared.</p>
          <p className="muted">The audit trail is kept. It's append-only.</p>
        </Modal>
      )}
      {about && (
        <Modal title="How this desk works" eyebrow="Campus Customs" onClose={() => setAbout(false)}>
          <ol className="steps">
            <li><strong>Pick a ticket and start the team.</strong> The Boss reads it first and asks the teammates it needs.</li>
            <li><strong>Watch them work.</strong> Each agent's feed shows what it looked up and who it asked, as it happens.</li>
            <li><strong>Review.</strong> The Boss suggests a decision with its reasons and the numbers behind them.</li>
            <li><strong>Approve.</strong> Payments move money only when you click approve, and never below $0. Then close the ticket and it joins the Done pile.</li>
          </ol>
          <p className="muted">Every agent runs on gpt-6-luna, every fact comes from the shop database through the MCP server, and every step is written to the audit trail.</p>
        </Modal>
      )}

      <div className="toasts" aria-live="polite">
        {toasts.map(t => <div key={t.id} className={`toast ${t.tone}`}>{t.text}</div>)}
      </div>
    </div>
  )
}
