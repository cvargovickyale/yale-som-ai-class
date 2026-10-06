import { useEffect, useRef, useState } from 'react'
import type { Step } from '../types'
import { usd } from '../money'
import './TraceTable.css'

const KIND_LABEL: Record<Step['kind'], string> = {
  llm: '🧠 model',
  search: '🔎 search',
  delegate: '📨 delegate',
}

function oneLine(text: string | undefined, max = 90) {
  if (!text) return ''
  const flat = text.replace(/\s+/g, ' ').trim()
  return flat.length > max ? `${flat.slice(0, max)}…` : flat
}

function tokenCell(s: Step) {
  const u = s.usage
  if (u) {
    const cached = u.cache_read_tokens ? ` (${u.cache_read_tokens.toLocaleString()} cached)` : ''
    return `${u.input_tokens.toLocaleString()}${cached} / ${u.output_tokens.toLocaleString()}`
  }
  return s.passages != null ? `${s.passages} passages` : ''
}

export function TraceTable({
  steps,
  emojiFor,
  filter,
  onClearFilter,
}: {
  steps: Step[]
  emojiFor: (agentKey: string) => string
  filter: string | null
  onClearFilter: () => void
}) {
  const [open, setOpen] = useState<number | null>(null)
  const scroller = useRef<HTMLDivElement>(null)
  const pinned = useRef(true)

  const rows = filter ? steps.filter((s) => s.agent_key === filter) : steps

  // Follow new rows while the user is scrolled to the bottom.
  useEffect(() => {
    const el = scroller.current
    if (el && pinned.current) el.scrollTop = el.scrollHeight
  }, [rows.length])

  return (
    <div className="trace">
      {filter && (
        <div className="trace-filter">
          Showing {emojiFor(filter)} {rows[0]?.agent ?? filter} only ·{' '}
          <button type="button" className="linkish" onClick={onClearFilter}>
            show all
          </button>
        </div>
      )}
      <div
        className="trace-scroll"
        ref={scroller}
        onScroll={(e) => {
          const el = e.currentTarget
          pinned.current = el.scrollHeight - el.scrollTop - el.clientHeight < 24
        }}
      >
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Start</th>
              <th>Agent</th>
              <th>Step</th>
              <th>Input</th>
              <th>Output</th>
              <th>Time</th>
              <th>Tokens in/out</th>
              <th>Cost</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={9} className="muted">
                  Every model call, book search, and delegation will appear here as it happens, with its cost.
                </td>
              </tr>
            )}
            {rows.map((s) => {
              const running = s.status === undefined
              const expanded = open === s.step_id
              return [
                <tr
                  key={s.step_id}
                  className={`row ${s.kind} ${running ? 'running' : s.status}`}
                  onClick={() => setOpen(expanded ? null : s.step_id)}
                >
                  <td className="num">{s.step_id}</td>
                  <td className="num">{s.started.toFixed(2)}s</td>
                  <td className="agent">
                    {emojiFor(s.agent_key)} {s.agent}
                  </td>
                  <td>
                    {KIND_LABEL[s.kind]}
                    <div className="sub">{s.label}</div>
                  </td>
                  <td className="text">{oneLine(s.input)}</td>
                  <td className="text">{running ? <span className="working">working…</span> : oneLine(s.output)}</td>
                  <td className="num">{running || s.duration_ms == null ? (running ? '…' : '') : `${(s.duration_ms / 1000).toFixed(2)}s`}</td>
                  <td className="num">{tokenCell(s)}</td>
                  <td className="num cost">{s.usage?.cost_usd != null ? usd(s.usage.cost_usd) : ''}</td>
                </tr>,
                expanded && (
                  <tr key={`${s.step_id}-detail`} className="detail">
                    <td colSpan={9}>
                      {s.usage && (
                        <p className="usage-detail">
                          {s.model ? `${s.model} · ` : ''}
                          {s.usage.input_tokens.toLocaleString()} input = {(s.usage.input_tokens - s.usage.cache_read_tokens - s.usage.cache_write_tokens).toLocaleString()} uncached +{' '}
                          {s.usage.cache_read_tokens.toLocaleString()} cache read + {s.usage.cache_write_tokens.toLocaleString()} cache write ·{' '}
                          {s.usage.output_tokens.toLocaleString()} output · {usd(s.usage.cost_usd)}
                        </p>
                      )}
                      <div className="detail-grid">
                        <section>
                          <h4>Input</h4>
                          <pre>{s.input}</pre>
                        </section>
                        <section>
                          <h4>Output</h4>
                          <pre>{s.output ?? 'working…'}</pre>
                        </section>
                      </div>
                    </td>
                  </tr>
                ),
              ]
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
