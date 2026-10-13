import type { AgentEvent, AgentName, Ticket } from './api'

export const AGENTS: { id: AgentName; name: string; role: string; initial: string }[] = [
  { id: 'boss', name: 'Boss', role: 'Reads every ticket first and makes the final call', initial: 'B' },
  { id: 'inventory', name: 'Inventory', role: 'Stock by size, shortfalls, vendors, lead times', initial: 'I' },
  { id: 'accounting', name: 'Accounting', role: 'Cash, margins, and payments for your approval', initial: 'A' },
  { id: 'facilities', name: 'Facilities', role: 'The shop space, leases, and rent', initial: 'F' },
  { id: 'customer_service', name: 'Customer Service', role: 'Friendly, honest drafts to whoever asked', initial: 'C' },
]
export const agentName = (id: AgentName | null | undefined) => AGENTS.find(a => a.id === id)?.name ?? 'Desk'

const money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' })
export const usd = (n: number) => money.format(Math.round(n * 100) / 100)

export const TICKET_TYPES: Record<string, { label: string; icon: 'shirt' | 'key' | 'tag' }> = {
  customer_order: { label: 'Customer order', icon: 'shirt' },
  rent_notice: { label: 'Rent notice', icon: 'key' },
  price_override: { label: 'Discount request', icon: 'tag' },
}
export const ticketType = (t: Ticket) => TICKET_TYPES[t.type] ?? { label: t.type.replace(/_/g, ' '), icon: 'tag' as const }

export function ticketLine(t: Ticket) {
  if (t.sku) return `${t.qty} × ${t.sku} · size ${t.size}`
  if (t.lease_id) return `Lease ${t.lease_id}`
  return t.subject
}

export const OUTCOMES: Record<string, string> = {
  fulfil: 'Fill as requested', partial: 'Partly fill', alternative: 'Offer an alternative',
  waiting: 'Waiting', pay: 'Pay the bill', decline: 'Decline',
}

export function longDate(iso: string) {
  const d = new Date(`${iso}T12:00:00`)
  return d.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })
}

const TOOL_VERBS: Record<string, string> = {
  get_ticket: 'read the ticket',
  list_open_tickets: 'looked over the open tickets',
  record_decision: 'recorded a decision for you',
  check_stock: 'checked the shelf',
  find_vendor: 'looked up who can reprint',
  reserve_stock: 'set stock aside',
  request_reprint: 'asked for a reprint',
  price_and_margin: 'worked out price and margin',
  get_cash_and_bills: 'checked cash and bills',
  propose_payment: 'proposed a payment',
  get_lease: 'pulled up the lease',
  save_draft_message: 'drafted a reply',
}
export const toolVerb = (tool?: string) => (tool && TOOL_VERBS[tool]) || tool?.replace(/_/g, ' ') || 'used a tool'

/** One calm sentence per event, or null for events the feed doesn't need to show. */
export function describe(e: AgentEvent): string | null {
  switch (e.type) {
    case 'run_started': return `Team started on ticket ${e.ticket_id}`
    case 'agent_started': return 'started working'
    case 'tool_call': return toolVerb(e.tool)
    case 'tool_result': return e.status === 'error' ? `${toolVerb(e.tool)}, but the tool said no` : null
    case 'delegation': return `asked ${agentName(e.to_agent)} for help`
    case 'agent_finished': return e.status === 'ok' ? 'finished' : `stopped (${e.status})`
    case 'run_finished': return e.status === 'ok' ? `Ticket ${e.ticket_id} is ready for your review` : `Ticket ${e.ticket_id} run ended: ${e.status}`
    case 'payment_approved': return `${e.by} approved ${usd(e.amount ?? 0)} to ${e.payee}`
    case 'payment_rejected': return `${e.by} rejected a payment`
    case 'ticket_resolved': return `${e.by} closed ticket ${e.ticket_id}`
    case 'reset': return 'Desk reset to the original data'
    default: return null
  }
}

export function timeOf(iso: string) {
  return new Date(iso).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', second: '2-digit' })
}
