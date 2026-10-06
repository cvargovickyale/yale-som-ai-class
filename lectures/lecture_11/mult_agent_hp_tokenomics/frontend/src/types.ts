export type AgentStatus = 'idle' | 'working' | 'done' | 'error'

export type ModelName = 'gpt-6-luna' | 'gpt-6-astra'

export interface SpecialistMeta {
  book_number: number
  agent_key: string // "book-1" … "book-7"
  character: string
  emoji: string
  title: string
  short: string
  specialty: string
  accent: string
  house_hint: string
  wand: string
  page_count?: number
  token_count?: number
}

export interface Delegation {
  agent: string
  book_number: number
  book_title: string
  question: string
  reply: string
  status: 'pending' | 'running' | 'done' | 'error'
}

export interface Usage {
  requests?: number
  input_tokens: number
  output_tokens: number
  cache_read_tokens: number
  cache_write_tokens: number
  cost_usd?: number
}

/** One row in the live trace: a model call, a book search, or a delegation. */
export interface Step {
  step_id: number
  agent_key: string
  agent: string
  kind: 'llm' | 'search' | 'delegate'
  label: string
  input: string
  started: number // seconds since the job started
  output?: string
  status?: 'done' | 'error'
  duration_ms?: number
  usage?: Usage
  passages?: number
  model?: string
}

/** Payload of the backend's `spend` event (and the `spend` field on final/error). */
export interface Spend {
  model: string
  budget_usd: number | null
  total_usd: number
  budget_exceeded: boolean
  agents: Record<string, Usage>
  total: Usage
}

export interface Pricing {
  unit: string
  source: string
  default_model: ModelName
  models: Record<ModelName, { input: number; cached: number; cache_write: number; output: number }>
}

export interface ChatResult {
  answer: string
  delegations: Delegation[]
  boss_name: string
  usage?: { total: Usage } | null
  spend?: Spend | null
  budget_exceeded?: boolean
  error?: string
}

export interface ProgressEvent {
  type: string
  data: Record<string, unknown>
}
