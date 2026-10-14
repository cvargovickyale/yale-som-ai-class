import { useEffect, useRef, useState } from 'react'
import type { Cash } from '../api'
import { usd } from '../format'
import { Icon } from './Icon'

/** A calm strip under the header: every overdue invoice, so an unpaid bill is never invisible. */
export function OverdueTicker({ cash }: { cash: Cash | null }) {
  const overdue = (cash?.open_invoices ?? []).filter(i => i.is_overdue)
  const track = useRef<HTMLDivElement>(null)
  const [scrolls, setScrolls] = useState(false)

  // Only scroll (ticker-style) when the items don't fit; otherwise sit still.
  useEffect(() => {
    const el = track.current
    if (!el) return
    const check = () => setScrolls(el.scrollWidth > el.clientWidth + 1)
    check()
    window.addEventListener('resize', check)
    return () => window.removeEventListener('resize', check)
  }, [overdue.length])

  if (!cash) return null
  if (overdue.length === 0) {
    return (
      <p className="ticker ticker-clear" role="status">
        <Icon name="check" size={16} /> No overdue invoices.
      </p>
    )
  }
  const total = overdue.reduce((n, i) => n + i.amount, 0)
  const items = overdue.map(i => (
    <span key={i.id} className="ticker-item">
      <strong>Invoice {i.id}</strong> · {i.vendor_name} · {usd(i.amount)} ·{' '}
      <strong>{i.days_overdue} day{i.days_overdue === 1 ? '' : 's'} overdue</strong> (due {i.due_date}) · {i.vendor_name} won't ship new product until it's paid
    </span>
  ))
  return (
    <section className="ticker" aria-label={`Overdue invoices: ${overdue.length}, ${usd(total)} total`}>
      <span className="ticker-label"><Icon name="alert" size={16} /> Overdue · {usd(total)}</span>
      <div className={`ticker-track ${scrolls ? 'scrolls' : ''}`} ref={track}>
        <div className="ticker-run">{items}{scrolls && <span aria-hidden="true">{items}</span>}</div>
      </div>
    </section>
  )
}
