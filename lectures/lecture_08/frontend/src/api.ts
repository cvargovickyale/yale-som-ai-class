import type { ChatMessage, Course } from "./types"

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000"
const TOKEN_KEY = "som_explorer_token"

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

async function parseError(res: Response, fallback: string): Promise<string> {
  try {
    const data = await res.json()
    return data?.detail ?? fallback
  } catch {
    return fallback
  }
}

async function authedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const token = getToken()
  const headers = new Headers(init.headers)
  if (token) headers.set("Authorization", `Bearer ${token}`)
  return fetch(`${API_BASE}${path}`, { ...init, headers })
}

export async function signup(email: string, password: string): Promise<{ token: string; email: string }> {
  const res = await fetch(`${API_BASE}/api/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) throw new Error(await parseError(res, `Sign up failed (${res.status})`))
  return res.json()
}

export async function login(email: string, password: string): Promise<{ token: string; email: string }> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) throw new Error(await parseError(res, `Log in failed (${res.status})`))
  return res.json()
}

export async function fetchMe(): Promise<{ email: string }> {
  const res = await authedFetch("/api/auth/me")
  if (!res.ok) throw new Error(`GET /api/auth/me failed (${res.status})`)
  return res.json()
}

export async function fetchCourses(): Promise<Course[]> {
  const res = await authedFetch("/api/courses")
  if (!res.ok) throw new Error(`GET /api/courses failed (${res.status})`)
  const data = await res.json()
  return data.courses as Course[]
}

interface ChatHistoryRow {
  role: string
  content: string
  tools_used: string[]
}

export async function fetchChatHistory(): Promise<ChatMessage[]> {
  const res = await authedFetch("/api/chat/history")
  if (!res.ok) throw new Error(`GET /api/chat/history failed (${res.status})`)
  const data = (await res.json()) as ChatHistoryRow[]
  return data.map((m, i) => ({
    id: `hist-${i}`,
    role: m.role === "user" ? "user" : "assistant",
    text: m.content,
    toolsUsed: m.tools_used,
  }))
}

export async function sendChat(message: string): Promise<{ reply: string; toolsUsed: string[] }> {
  const res = await authedFetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  })
  if (!res.ok) throw new Error(`POST /api/chat failed (${res.status})`)
  const data = await res.json()
  return { reply: data.reply as string, toolsUsed: (data.tools_used ?? []) as string[] }
}
