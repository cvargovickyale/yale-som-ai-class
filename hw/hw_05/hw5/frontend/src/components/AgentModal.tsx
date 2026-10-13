import type { AgentEvent, AgentName } from '../api'
import { AGENTS, describe, timeOf } from '../format'
import { feedFor } from './AgentsPanel'
import { Modal } from './Modal'

/** One agent's full recent feed. */
export function AgentModal({ agent, events, onClose }: { agent: AgentName; events: AgentEvent[]; onClose: () => void }) {
  const a = AGENTS.find(x => x.id === agent)!
  const feed = feedFor(events, agent).reverse()
  return (
    <Modal onClose={onClose} eyebrow="Agent" title={a.name}>
      <div className="agent-hero">
        <span className={`avatar lg av-${a.id}`}>{a.initial}</span>
        <p>{a.role}.</p>
      </div>
      {feed.length === 0 ? (
        <p className="muted">Nothing yet. Start the team on a ticket and {a.name} will show up here when asked.</p>
      ) : (
        <ol className="feed">
          {feed.map(e => (
            <li key={e.seq}>
              <time>{timeOf(e.at)}</time>
              <div>
                <p>{e.ticket_id ? <span className="muted">#{e.ticket_id} · </span> : null}{describe(e)}</p>
                {e.type === 'delegation' && e.task && <p className="muted small">“{e.task}”</p>}
                {e.type === 'agent_finished' && e.recommendation && <p className="small">{e.recommendation}</p>}
                {e.type === 'tool_result' && e.status === 'error' && e.result && <p className="muted small">{e.result}</p>}
              </div>
            </li>
          ))}
        </ol>
      )}
    </Modal>
  )
}
