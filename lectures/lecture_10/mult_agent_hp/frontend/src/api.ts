import type { ChatResult, ProgressEvent, SpecialistMeta } from './types'

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, '') || ''

const PASSWORD_KEY = 'hp-agents-password'

export class AuthError extends Error {}

export function savedPassword(): string {
  return localStorage.getItem(PASSWORD_KEY) || ''
}

export function forgetPassword() {
  localStorage.removeItem(PASSWORD_KEY)
}

export async function fetchAuthStatus(): Promise<{ password_required: boolean }> {
  const res = await apiFetch('/api/auth/status')
  return res.json()
}

/** Check a password with the backend; remember it if it's right. */
export async function login(password: string): Promise<boolean> {
  const res = await fetch(`${API_BASE}/api/auth/check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password }),
  })
  if (res.ok) localStorage.setItem(PASSWORD_KEY, password)
  return res.ok
}

async function apiFetch(path: string, init?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, init)
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  return res
}

export async function fetchHealth(): Promise<{ ok: boolean; boss?: string; model?: string; portkey_key_set?: boolean }> {
  const res = await apiFetch('/api/health')
  return res.json()
}

export async function fetchRoster(): Promise<{ boss: string; specialists: SpecialistMeta[] }> {
  const res = await apiFetch('/api/roster')
  return res.json()
}

/** POST the question, then read the SSE stream, calling onEvent for every queued event. */
export async function streamChat(
  message: string,
  onEvent: (ev: ProgressEvent) => void,
): Promise<ChatResult> {
  const res = await fetch(`${API_BASE}/api/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-App-Password': savedPassword() },
    body: JSON.stringify({ message }),
  })
  if (res.status === 401) {
    forgetPassword()
    throw new AuthError('Password required')
  }
  if (!res.ok || !res.body) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let finalResult: ChatResult | null = null

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() || ''
    for (const block of parts) {
      const dataLine = block.split('\n').find((l) => l.startsWith('data: '))
      if (!dataLine) continue
      const payload = JSON.parse(dataLine.slice(6)) as ProgressEvent
      onEvent(payload)
      if (payload.type === 'final' || payload.type === 'error') {
        finalResult = payload.data as unknown as ChatResult
      }
    }
  }

  if (!finalResult) {
    throw new Error('Stream ended without a final answer')
  }
  return finalResult
}
