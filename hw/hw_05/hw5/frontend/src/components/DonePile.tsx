import type { Ticket } from '../api'
import { ticketType } from '../format'
import { Icon } from './Icon'

const tilt = (id: number) => ((id * 37) % 7) - 3 // a gentle, stable lean per ticket

/** Closed tickets land here, stacked like paper on a desk. */
export function DonePile({ tickets, landed, onOpen }: { tickets: Ticket[]; landed: number | null; onOpen: (t: Ticket) => void }) {
  return (
    <section className="panel done" aria-labelledby="done-h">
      <div className="panel-head">
        <h2 id="done-h">Done</h2>
        <span className="count">{tickets.length}</span>
      </div>
      {tickets.length === 0 ? (
        <div className="done-empty">
          <span className="done-tray" aria-hidden="true" />
          <p>Closed tickets land here.</p>
        </div>
      ) : (
        <ol className="done-stack">
          {tickets.map(t => (
            <li key={t.id} className={landed === t.id ? 'landed' : ''} style={{ ['--tilt' as string]: `${tilt(t.id)}deg` }}>
              <button className="done-card" onClick={() => onOpen(t)}>
                <span className="done-check"><Icon name="check" size={16} /></span>
                <span>
                  <span className="eyebrow">#{t.id} · {ticketType(t).label}</span>
                  <span className="done-name">{t.requester}</span>
                </span>
              </button>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
