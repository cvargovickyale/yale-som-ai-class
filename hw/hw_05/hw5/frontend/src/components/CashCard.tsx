import { useEffect, useRef, useState } from 'react'
import type { Cash } from '../api'
import { useAnimatedNumber } from '../hooks'
import { usd } from '../format'

/** The checking balance, front and center. Counts down when you approve a payment. */
export function CashCard({ cash }: { cash: Cash | null }) {
  const c = cash?.checking ?? null
  const shown = useAnimatedNumber(c ? c.balance : null)
  const prev = useRef<number | null>(null)
  const [delta, setDelta] = useState<{ amount: number; key: number } | null>(null)

  useEffect(() => {
    if (!c) return
    if (prev.current !== null && c.balance !== prev.current) {
      setDelta({ amount: c.balance - prev.current, key: Date.now() })
      const t = setTimeout(() => setDelta(null), 2600)
      prev.current = c.balance
      return () => clearTimeout(t)
    }
    prev.current = c.balance
  }, [c])

  return (
    <section className="cash-card" aria-labelledby="cash-label">
      <p className="eyebrow" id="cash-label">Checking balance</p>
      <div className="cash-amount" aria-live="polite">
        {shown === null ? '—' : usd(shown)}
        {delta && (
          <span key={delta.key} className={`cash-delta ${delta.amount < 0 ? 'down' : 'up'}`}>
            {delta.amount < 0 ? '−' : '+'}{usd(Math.abs(delta.amount))}
          </span>
        )}
      </div>
      {c && (
        <dl className="cash-sub">
          <div><dt>Waiting for your approval</dt><dd>{usd(c.pending_payments)}</dd></div>
          <div><dt>After those are paid</dt><dd className={c.cash_after_pending < 500 ? 'tight' : ''}>{usd(c.cash_after_pending)}</dd></div>
        </dl>
      )}
      <p className="cash-note">From <code>cash_accounts</code>. Money moves only when you approve.</p>
    </section>
  )
}
