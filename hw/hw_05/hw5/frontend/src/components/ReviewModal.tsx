import { useEffect, useState } from 'react'
import { api, type Cash, type History, type Ticket } from '../api'
import { AGENTS, OUTCOMES, agentName, ticketLine, ticketType, toolVerb, usd } from '../format'
import { Icon } from './Icon'
import { Modal } from './Modal'

/** Everything about one ticket: the Boss's call, what each agent did, and the approvals waiting for you. */
export function ReviewModal({ ticket, cash, approver, onClose, onApprovePayment, onRejectPayment, onCloseTicket }: {
  ticket: Ticket; cash: Cash | null; approver: string; onClose: () => void
  onApprovePayment: (id: number) => Promise<void>; onRejectPayment: (id: number) => Promise<void>
  onCloseTicket: (decisionId: number) => Promise<void>
}) {
  const [history, setHistory] = useState<History | null>(null)
  const [working, setWorking] = useState<string | null>(null)
  useEffect(() => { api.history(ticket.id).then(setHistory).catch(() => setHistory(null)) }, [ticket.id])

  const resolved = ticket.status === 'resolved'
  const decisionRow = ticket.records.decisions.find(d => d.status === 'pending_approval')
    ?? ticket.records.decisions.at(-1)
  const boss = history?.run?.decision ?? ticket.run?.decision ?? null
  const waiting = ticket.records.payment_requests.filter(p => p.status === 'pending_approval')
  const settled = ticket.records.payment_requests.filter(p => p.status !== 'pending_approval')
  const draft = ticket.records.message_drafts.at(-1)
  const balance = cash?.checking?.balance ?? null
  const act = (key: string, fn: () => Promise<void>) => async () => {
    setWorking(key)
    try { await fn() } finally { setWorking(null) }
  }

  const footer = resolved ? (
    <p className="muted"><Icon name="check" size={16} /> Closed{decisionRow?.decided_by ? ` by ${decisionRow.decided_by}` : ''}.</p>
  ) : decisionRow?.status === 'pending_approval' ? (
    <>
      <p className="muted foot-hint">
        {waiting.length
          ? 'Approve or reject the payments above first.'
          : approver ? `Closing as ${approver}. Drafts are approved, never sent.` : 'Add your name at the top to approve.'}
      </p>
      <button className="btn btn-success" disabled={!!waiting.length || !approver || working !== null}
        onClick={act('close', () => onCloseTicket(decisionRow.id))}>
        <Icon name="check" size={16} /> {working === 'close' ? 'Closing…' : 'Approve and close ticket'}
      </button>
    </>
  ) : null

  return (
    <Modal wide onClose={onClose} eyebrow={`#${ticket.id} · ${ticketType(ticket).label}`} title={ticket.requester} footer={footer}>
      <p className="lede">{ticketLine(ticket)} · “{ticket.notes}”</p>

      {boss || decisionRow ? (
        <section className="block">
          <h3>The Boss's call {boss && <span className="pill">{OUTCOMES[boss.outcome] ?? boss.outcome}</span>}</h3>
          <p>{boss?.summary ?? decisionRow?.summary}</p>
          <details>
            <summary>Why</summary>
            <p>{boss?.reasoning ?? decisionRow?.reasoning}</p>
          </details>
          {boss && boss.risks.length > 0 && (
            <div className="risks">
              <p className="eyebrow"><Icon name="alert" size={14} /> Worth knowing before you approve</p>
              <ul>{boss.risks.map((r, i) => <li key={i}>{r}</li>)}</ul>
            </div>
          )}
        </section>
      ) : (
        <p className="muted">The team hasn't worked this ticket yet.</p>
      )}

      {(waiting.length > 0 || settled.length > 0) && (
        <section className="block">
          <h3><Icon name="coins" size={18} /> Payments</h3>
          <ul className="payments">
            {waiting.map(p => (
              <li key={p.id} className="payment">
                <div>
                  <p className="pay-amount">{usd(p.amount)} <span className="muted">to {p.payee}</span></p>
                  <p className="muted small">{p.kind === 'invoice' ? `Invoice ${p.ref_id}` : `Rent, lease ${p.ref_id}`} · {p.reason}</p>
                  {balance !== null && <p className="small">Checking after this: <strong>{usd(balance - p.amount)}</strong></p>}
                </div>
                <div className="pay-actions">
                  <button className="btn btn-quiet" disabled={!approver || working !== null}
                    onClick={act(`rej${p.id}`, () => onRejectPayment(p.id))}>Reject</button>
                  <button className="btn btn-primary" disabled={!approver || working !== null}
                    onClick={act(`pay${p.id}`, () => onApprovePayment(p.id))}>
                    {working === `pay${p.id}` ? 'Paying…' : 'Approve payment'}
                  </button>
                </div>
              </li>
            ))}
            {settled.map(p => (
              <li key={p.id} className={`payment settled ${p.status}`}>
                <p>{usd(p.amount)} <span className="muted">to {p.payee}</span></p>
                <span className={`pill ${p.status === 'paid' ? 'pill-ok' : ''}`}>
                  {p.status === 'paid' ? `Paid · ${p.decided_by}` : `Rejected · ${p.decided_by}`}
                </span>
              </li>
            ))}
          </ul>
          {!approver && waiting.length > 0 && <p className="hint">Add your name at the top of the desk to approve.</p>}
        </section>
      )}

      {draft && (
        <section className="block">
          <h3><Icon name="mail" size={18} /> Draft to {draft.to_name}</h3>
          <div className="letter">
            <p className="letter-subject">{draft.subject}</p>
            <p className="letter-body">{draft.body}</p>
          </div>
          <p className="muted small">{draft.status === 'draft' ? 'Draft only. Nothing is ever sent.' : 'Approved. Not sent: there is no send button by design.'}</p>
        </section>
      )}

      {(ticket.records.stock_holds.length > 0 || ticket.records.reprint_requests.length > 0) && (
        <section className="block">
          <h3><Icon name="box" size={18} /> Stock</h3>
          <ul className="plain">
            {ticket.records.stock_holds.map(h => <li key={`h${h.id}`}>{h.qty} × {h.sku} {h.size} {h.status === 'held' ? 'set aside' : 'taken off the shelf'}</li>)}
            {ticket.records.reprint_requests.map(r => <li key={`r${r.id}`}>Reprint {r.qty} × {r.sku} {r.size}, about {usd(r.est_cost)}, earliest {r.expected_arrival} ({r.status.replace(/_/g, ' ')})</li>)}
          </ul>
        </section>
      )}

      {history && history.agents.length > 0 && (
        <section className="block">
          <h3>What each agent did</h3>
          <ol className="work">
            {history.agents.map(a => (
              <li key={a.run_id}>
                <span className={`avatar sm av-${a.agent}`}>{AGENTS.find(x => x.id === a.agent)?.initial}</span>
                <div>
                  <p><strong>{agentName(a.agent)}</strong>
                    <span className="muted small"> · asked by {agentName(a.chain.at(-2) ?? null)}{a.chain.length === 1 ? ' (you)' : ''} · {a.duration_s.toFixed(0)}s · {a.tokens.toLocaleString()} tokens</span></p>
                  {a.recommendation && <p>{a.recommendation}</p>}
                  {a.tools.length > 0 && (
                    <p className="tools">{a.tools.map((t, i) => (
                      <span key={i} className={`tool ${t.status}`}>{t.tool === 'delegate' ? 'asked a teammate' : toolVerb(t.tool)}</span>
                    ))}</p>
                  )}
                </div>
              </li>
            ))}
          </ol>
          {history.run?.totals && (
            <p className="muted small">Whole team: {history.run.totals.model_requests} model requests, {(history.run.totals.input_tokens + history.run.totals.output_tokens).toLocaleString()} tokens, {history.run.duration_s.toFixed(0)}s, all on gpt-6-luna.</p>
          )}
        </section>
      )}
    </Modal>
  )
}
