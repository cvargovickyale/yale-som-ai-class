import type { AgentEvent, AgentName } from '../api'
import { AGENTS, describe, timeOf } from '../format'

export function activeAgents(events: AgentEvent[]): Map<AgentName, number> {
  // agent -> ticket it's working on right now
  const live = new Map<AgentName, number>()
  for (const e of events) {
    if (e.type === 'run_started' || e.type === 'reset') live.clear()
    if (!e.agent || e.ticket_id === null) continue
    if (e.type === 'agent_started') live.set(e.agent, e.ticket_id)
    if (e.type === 'agent_finished') live.delete(e.agent)
  }
  return live
}

export const feedFor = (events: AgentEvent[], agent: AgentName) =>
  events.filter(e => e.agent === agent && !e.type.startsWith('run_') && describe(e))

/** The five agents, each with what they're doing now and their last few steps. */
export function AgentsPanel({ events, onOpen }: { events: AgentEvent[]; onOpen: (a: AgentName) => void }) {
  const live = activeAgents(events)
  return (
    <section className="panel" aria-labelledby="agents-h">
      <div className="panel-head">
        <h2 id="agents-h">The team</h2>
        <span className="muted">{live.size ? `${live.size} working` : 'Resting'}</span>
      </div>
      <ul className="agents">
        {AGENTS.map(a => {
          const feed = feedFor(events, a.id).slice(-3).reverse()
          const ticket = live.get(a.id)
          return (
            <li key={a.id}>
              <button className={`agent ${ticket !== undefined ? 'is-live' : ''}`} onClick={() => onOpen(a.id)}
                aria-label={`${a.name}: ${ticket !== undefined ? `working on ticket ${ticket}` : 'idle'}. Open feed.`}>
                <span className={`avatar av-${a.id}`}>{a.initial}{ticket !== undefined && <span className="ring" />}</span>
                <span className="agent-body">
                  <span className="agent-name">{a.name}
                    <span className="agent-status">{ticket !== undefined ? `on #${ticket}` : 'idle'}</span>
                  </span>
                  {feed.length === 0
                    ? <span className="agent-role">{a.role}</span>
                    : <ul className="mini-feed">
                        {feed.map(e => <li key={e.seq}><time>{timeOf(e.at)}</time>{describe(e)}</li>)}
                      </ul>}
                </span>
              </button>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
