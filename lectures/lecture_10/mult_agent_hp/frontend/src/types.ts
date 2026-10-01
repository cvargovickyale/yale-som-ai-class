export type AgentStatus = 'idle' | 'working' | 'done' | 'error'

export interface SpecialistMeta {
  book_number: number
  agent_id: string
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

/** One timed step in any agent's loop: a model call, a book search, or a delegation. */
export interface Step {
  step_id: number
  agent_id: string
  agent: string
  kind: 'llm' | 'search' | 'delegate'
  label: string
  input: string
  started: number
  output?: string
  status?: 'done' | 'error'
  duration_ms?: number
  input_tokens?: number | null
  output_tokens?: number | null
  passages?: number
  model?: string
}

export interface ChatResult {
  answer: string
  delegations: Delegation[]
  trace?: Step[]
  boss_name: string
}

export interface ProgressEvent {
  type: string
  data: Record<string, unknown>
}
