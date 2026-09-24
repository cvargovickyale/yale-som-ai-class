import type { Course } from "./types"

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:8000"

export async function fetchCourses(): Promise<Course[]> {
  const res = await fetch(`${API_BASE}/api/courses`)
  if (!res.ok) throw new Error(`GET /api/courses failed (${res.status})`)
  const data = await res.json()
  return data.courses as Course[]
}

export async function sendChat(message: string): Promise<{ reply: string; toolsUsed: string[] }> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  })
  if (!res.ok) throw new Error(`POST /api/chat failed (${res.status})`)
  const data = await res.json()
  return { reply: data.reply as string, toolsUsed: (data.tools_used ?? []) as string[] }
}
