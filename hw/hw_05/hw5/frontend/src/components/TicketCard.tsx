import type { AgentEvent, Ticket } from '../api'
import { AGENTS, OUTCOMES, agentName, describe, ticketLine, ticketType } from '../format'
import { Icon } from './Icon'

export type CardPhase = 'idle' | 'closing' | 'flying'

export function needsYou(t: Ticket) {
  const pay = t.records.payment_requests.filter(p => p.status === 'pending_approval').length
  const dec = t.records.decisions.filter(d => d.status === 'pending_approval').length
  return pay + dec
}

export function TicketCard({ ticket, lastEvent, busy, phase, onRun, onReview }: {
  ticket: Ticket; lastEvent?: AgentEvent; busy: boolean; phase: CardPhase
  onRun: () => void; onReview: () => void
}) {
  const type = ticketType(ticket)
  const running = ticket.run?.status === 'running'
  const decision = ticket.records.decisions.find(d => d.status === 'pending_approval')
  const runDecision = ticket.run?.decision
  const failed = ticket.run && !running && ticket.run.status !== 'ok'
  const count = needsYou(ticket)
  const used = runDecision?.agents_used ?? []

  return (
    <article className={`ticket ${running ? 'is-running' : ''} ${decision ? 'is-decided' : ''} phase-${phase}`}
      aria-label={`Ticket ${ticket.id}, ${type.label}, ${ticket.status}`}>
      <div className="stamp" aria-hidden="true"><Icon name="check" size={34} /></div>
      <header className="ticket-head">
        <span className="ticket-icon"><Icon name={type.icon} size={20} /></span>
        <div className="ticket-title">
          <p className="eyebrow">#{ticket.id} · {type.label}</p>
          <h3>{ticket.requester}</h3>
        </div>
        {count > 0 && !running && <span className="pill pill-attn">{count} need{count === 1 ? 's' : ''} you</span>}
        {running && <span className="pill pill-live"><span className="dot" />Team at work</span>}
      </header>

      <p className="ticket-line">{ticketLine(ticket)}</p>
      <p className="ticket-note">“{ticket.notes}”</p>

      {running && (
        <p className="ticket-live" aria-live="polite">
          {lastEvent && describe(lastEvent)
            ? <><strong>{agentName(lastEvent.agent)}</strong> {describe(lastEvent)}…</>
            : 'The Boss is reading the ticket…'}
        </p>
      )}

      {decision && !running && (
        <div className="ticket-summary">
          <p className="eyebrow">The Boss suggests{runDecision ? ` · ${OUTCOMES[runDecision.outcome] ?? runDecision.outcome}` : ''}</p>
          <p>{decision.summary}</p>
          {used.length > 0 && (
            <div className="avatars" aria-label={`Agents involved: ${used.map(agentName).join(', ')}`}>
              {['boss', ...used].map(a => (
                <span key={a} className={`avatar sm av-${a}`} title={agentName(a as never)}>
                  {AGENTS.find(x => x.id === a)?.initial}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {failed && (
        <p className="ticket-error"><Icon name="alert" size={16} /> The run stopped ({ticket.run!.status}). You can try again.</p>
      )}

      <footer className="ticket-foot">
        {decision && !running ? (
          <button className="btn btn-primary" onClick={onReview}>Review and approve</button>
        ) : !running ? (
          <button className="btn btn-primary" onClick={onRun} aria-describedby={busy ? `busy-${ticket.id}` : undefined}>
            <Icon name="play" size={16} /> {failed ? 'Try again' : 'Start the team'}
          </button>
        ) : null}
        {!running && (decision || ticket.run) && (
          <button className="btn btn-quiet" onClick={onReview}>Details</button>
        )}
        {busy && !running && !decision && <span className="hint" id={`busy-${ticket.id}`}>Another ticket is being worked. One at a time.</span>}
      </footer>
    </article>
  )
}
