import { usd } from '../money'
import type { Usage } from '../types'
import './SpendMeter.css'

/** One thermometer: a tube that fills toward `scale`, plus a bulb that turns red past the budget. */
export function SpendMeter({
  label,
  emoji,
  usage,
  scale,
  accent,
  over,
  active,
  isTotal,
}: {
  label: string
  emoji: string
  usage?: Usage
  scale: number
  accent: string
  over?: boolean
  active?: boolean
  isTotal?: boolean
}) {
  const cost = usage?.cost_usd ?? 0
  const pct = Math.min(100, scale > 0 ? (cost / scale) * 100 : 0)
  const title = usage
    ? `${label}: ${usd(cost)}\n${usage.input_tokens.toLocaleString()} in (${usage.cache_read_tokens.toLocaleString()} cached, ${usage.cache_write_tokens.toLocaleString()} cache write)\n${usage.output_tokens.toLocaleString()} out`
    : `${label}: no spend yet`
  return (
    <div
      className={`meter ${isTotal ? 'total' : ''} ${over ? 'over' : ''} ${active ? 'active' : ''}`}
      style={{ ['--accent' as string]: accent }}
      title={title}
    >
      <span className="meter-value">{usd(cost)}</span>
      <div className="tube" role="meter" aria-valuenow={cost} aria-valuemin={0} aria-valuemax={scale} aria-label={`${label} spend`}>
        <div className="ticks" aria-hidden />
        <div className="fill" style={{ height: `${pct}%` }} />
      </div>
      <div className="bulb" aria-hidden />
      <span className="meter-label">
        {emoji} {label}
      </span>
      <span className="meter-tokens">
        {usage ? `${(usage.input_tokens / 1000).toFixed(1)}k in · ${(usage.output_tokens / 1000).toFixed(1)}k out` : '—'}
      </span>
    </div>
  )
}
