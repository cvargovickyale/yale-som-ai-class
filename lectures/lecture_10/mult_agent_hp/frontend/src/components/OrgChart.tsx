import type { AgentStatus } from '../types'
import './OrgChart.css'

export interface ChartNode {
  agent_id: string
  name: string
  emoji: string
  subtitle: string
  accent: string
  wand: string
}

export interface AgentState {
  status: AgentStatus
  /** Increments on every new step so the wand flares again. */
  flare: number
  steps: number
  busyMs: number
  tokens: number
}

/** A spark travelling along one edge: 'down' = task delegated, 'up' = result returned. */
export interface Spark {
  id: number
  edge: string // agent_id at the lower end of the edge ('boss' for the user → boss edge)
  dir: 'down' | 'up'
}

// Chart coordinates (viewBox 1000 × 440); HTML nodes use the same numbers as percentages.
const W = 1000
const H = 440
const USER = { x: 500, y: 50 }
const BOSS = { x: 500, y: 172 }
const WORKER_Y = 352

function workerX(i: number, n: number) {
  return (W * (i + 0.5)) / n
}

function edgePath(edge: string, workers: ChartNode[]): string {
  if (edge === 'boss') return `M${USER.x},${USER.y + 30} L${BOSS.x},${BOSS.y - 50}`
  const i = workers.findIndex((w) => w.agent_id === edge)
  const x = workerX(i, workers.length)
  const top = BOSS.y + 46
  const bottom = WORKER_Y - 52
  return `M${BOSS.x},${top} C${BOSS.x},${top + 60} ${x},${bottom - 60} ${x},${bottom}`
}

function Wand({ color, lit, flare, accent }: { color: string; lit: boolean; flare: number; accent: string }) {
  return (
    <svg className={`wand ${lit ? 'lit' : ''}`} viewBox="0 0 64 24" aria-hidden>
      <g transform="rotate(-28 32 12)">
        <rect x="4" y="10" width="16" height="5" rx="2" fill={color} stroke="#000" strokeWidth="0.8" />
        <rect x="19" y="10.8" width="34" height="3.4" rx="1.5" fill={color} stroke="#000" strokeWidth="0.6" />
        <circle className="wand-tip" cx="55" cy="12.5" r={lit ? 3.4 : 1.6} />
      </g>
      {lit && (
        <g key={flare} className="wand-sparkles" style={{ color: accent }}>
          <circle cx="58" cy="2" r="1.4" />
          <circle cx="62" cy="7" r="1" />
          <circle cx="52" cy="1" r="0.9" />
        </g>
      )}
    </svg>
  )
}

function Node({
  node,
  x,
  y,
  state,
  big,
  small,
  selected,
  onSelect,
}: {
  node: ChartNode
  x: number
  y: number
  state?: AgentState
  big?: boolean
  small?: boolean
  selected?: boolean
  onSelect?: () => void
}) {
  const status = state?.status ?? 'idle'
  const lit = status === 'working'
  return (
    <button
      type="button"
      className={`node ${big ? 'big' : ''} ${small ? 'small' : ''} ${status} ${selected ? 'selected' : ''}`}
      style={{ left: `${(x / W) * 100}%`, top: `${(y / H) * 100}%`, ['--accent' as string]: node.accent }}
      onClick={onSelect}
      title={onSelect ? 'Click to filter the trace to this agent' : undefined}
    >
      <span className="portrait">
        <span className="emoji">{node.emoji}</span>
        {node.agent_id !== 'user' && <Wand color={node.wand} lit={lit} flare={state?.flare ?? 0} accent={node.accent} />}
      </span>
      <span className="name">{node.name}</span>
      <span className="subtitle">{node.subtitle}</span>
      {state && state.steps > 0 && (
        <span className="stats">
          {state.steps} steps · {(state.busyMs / 1000).toFixed(1)}s
          {state.tokens > 0 && ` · ${(state.tokens / 1000).toFixed(1)}k tok`}
        </span>
      )}
    </button>
  )
}

export function OrgChart({
  boss,
  workers,
  agents,
  activeEdges,
  sparks,
  selected,
  onSelect,
}: {
  boss: ChartNode
  workers: ChartNode[]
  agents: Record<string, AgentState>
  activeEdges: Record<string, number>
  sparks: Spark[]
  selected: string | null
  onSelect: (agentId: string) => void
}) {
  const user: ChartNode = { agent_id: 'user', name: 'You', emoji: '🦉', subtitle: 'sends the owl', accent: '#d8cfb8', wand: '' }
  const edges = ['boss', ...workers.map((w) => w.agent_id)]

  return (
    <div className="orgchart">
      <svg className="edges" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" aria-hidden>
        {edges.map((e) => (
          <path
            key={e}
            d={edgePath(e, workers)}
            className={`edge ${activeEdges[e] ? 'active' : ''}`}
            vectorEffect="non-scaling-stroke"
          />
        ))}
        {sparks.map((s) => (
          <g key={s.id}>
            <path d={edgePath(s.edge, workers)} className={`edge-flash ${s.dir}`} vectorEffect="non-scaling-stroke" />
            <path
              d={edgePath(s.edge, workers)}
              className={`spark ${s.dir}`}
              pathLength={100}
              vectorEffect="non-scaling-stroke"
            />
          </g>
        ))}
      </svg>

      <Node node={user} x={USER.x} y={USER.y} small />
      <Node
        node={boss}
        x={BOSS.x}
        y={BOSS.y}
        big
        state={agents[boss.agent_id]}
        selected={selected === boss.agent_id}
        onSelect={() => onSelect(boss.agent_id)}
      />
      {workers.map((w, i) => (
        <Node
          key={w.agent_id}
          node={w}
          x={workerX(i, workers.length)}
          y={WORKER_Y}
          state={agents[w.agent_id]}
          selected={selected === w.agent_id}
          onSelect={() => onSelect(w.agent_id)}
        />
      ))}
    </div>
  )
}
