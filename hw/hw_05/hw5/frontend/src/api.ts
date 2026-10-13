// Typed calls to the P7 FastAPI routes (proxied by Vite from /api to :8000).

export type AgentName = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'

export interface PaymentRequest {
  id: number; ticket_id: number; kind: 'invoice' | 'rent'; ref_id: number; payee: string
  amount: number; account: string; reason: string; status: string; created_at: string
  decided_by?: string | null
}
export interface Draft { id: number; ticket_id: number; to_name: string; subject: string; body: string; status: string }
export interface Hold { id: number; sku: string; size: string; qty: number; status: string }
export interface Reprint {
  id: number; vendor_id: number; sku: string; size: string; qty: number
  est_cost: number; expected_arrival: string; status: string
}
export interface DecisionRow { id: number; ticket_id: number; summary: string; reasoning: string; status: string; decided_by?: string | null }

export interface Pending {
  payment_request_ids: number[]; reprint_request_ids: number[]; hold_ids: number[]; draft_ids: number[]
  decision_id: number | null
}
export interface BossDecision {
  ticket_id: number
  outcome: 'fulfil' | 'partial' | 'alternative' | 'waiting' | 'pay' | 'decline'
  summary: string; reasoning: string; agents_used: AgentName[]; pending: Pending; risks: string[]
}
export interface RunStatus {
  status: 'running' | 'ok' | 'error' | 'usage_limit' | 'timeout' | 'wrong_model'
  started_at?: string; duration_s?: number; error?: string | null
  totals?: { agent_runs: number; model_requests: number; input_tokens: number; output_tokens: number; tool_calls: number; delegations: number }
  decision?: BossDecision | null
}

export interface Ticket {
  id: number; type: string; requester: string; subject: string
  sku: string | null; size: string | null; qty: number | null
  lease_id: number | null; invoice_id: number | null
  status: 'open' | 'resolved'; notes: string; created_at: string
  records: {
    payment_requests: PaymentRequest[]; reprint_requests: Reprint[]; stock_holds: Hold[]
    message_drafts: Draft[]; decisions: DecisionRow[]
  }
  run: RunStatus | null
}
export interface Board {
  date_today: string; tickets: Ticket[]
  cash_accounts: { name: string; balance: number; as_of: string }[]
  payments: { id: number; kind: string; ref_id: number; amount: number; paid_at: string; approved_by: string }[]
  counts: { open: number; resolved: number }
}
export interface Cash {
  date_today: string
  checking: { name: string; balance: number; as_of: string; pending_payments: number; cash_after_pending: number } | null
  pending_payment_requests: PaymentRequest[]
}
export interface AgentEvent {
  seq: number; at: string; type: string; ticket_id: number | null; agent: AgentName | null
  tool?: string; to_agent?: AgentName; task?: string; status?: string; result?: string; args?: string
  recommendation?: string | null; tokens?: number; by?: string; amount?: number; payee?: string
  balance_after?: number; checking_balance?: number; error?: string
}
export interface AgentWork {
  run_id: string; agent: AgentName; chain: AgentName[]; status: string; task: string; duration_s: number
  tokens: number; model_requests: number; tools: { tool: string; status: string }[]
  findings: string[]; recommendation: string | null; actions_taken: string[]; blocked: string[]
}
export interface History {
  ticket_id: number
  run: { started_at: string; duration_s: number; status: string; totals: RunStatus['totals']; decision: BossDecision | null; error: string | null } | null
  agents: AgentWork[]
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) { super(message); this.status = status }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...init,
    headers: init?.body ? { 'content-type': 'application/json' } : undefined,
  })
  const text = await res.text()
  const data = text ? JSON.parse(text) : null
  if (!res.ok) {
    const detail = data?.detail
    const msg = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((d: { msg: string }) => d.msg).join('; ') : res.statusText
    throw new ApiError(res.status, msg || `Request failed (${res.status})`)
  }
  return data as T
}

const post = (body: unknown) => ({ method: 'POST', body: JSON.stringify(body) })

export const api = {
  board: () => call<Board>('/tickets'),
  cash: () => call<Cash>('/cash'),
  events: (since: number) => call<{ events: AgentEvent[]; last_seq: number }>(`/events?since=${since}&limit=300`),
  history: (id: number) => call<History>(`/tickets/${id}/history`),
  run: (id: number) => call<{ ticket_id: number; status: string }>(`/tickets/${id}/run`, { method: 'POST' }),
  approvePayment: (id: number, approved_by: string) =>
    call<{ amount: number; payee: string; balance_before: number; balance_after: number }>(`/payments/${id}/approve`, post({ approved_by })),
  rejectPayment: (id: number, rejected_by: string, reason = '') => call(`/payments/${id}/reject`, post({ rejected_by, reason })),
  approveDecision: (id: number, approved_by: string) => call<{ ticket_id: number }>(`/decisions/${id}/approve`, post({ approved_by })),
  reset: () => call<{ checking_balance: number }>('/reset', post({ confirm: true })),
}
