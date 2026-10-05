import type { AuthResponse, ChatResponse, ProductDetail, ProductSummary, SignupInput, User } from './types'

const TOKEN_KEY = 'cc_token'

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (token: string | null) =>
  token ? localStorage.setItem(TOKEN_KEY, token) : localStorage.removeItem(TOKEN_KEY)

// FastAPI errors are either {detail: "message"} or {detail: [{field, msg}, ...]}.
function errorMessage(body: unknown, status: number): string {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((d: { msg?: string }) => d.msg).join('. ')
  return `Request failed (${status})`
}

// Relative URLs: Vite proxies /api and /images to the FastAPI backend.
async function request<T>(url: string, init: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers = new Headers(init.headers)
  if (init.body) headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const res = await fetch(url, { ...init, headers })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(errorMessage(body, res.status))
  }
  return res.json() as Promise<T>
}

const post = <T>(url: string, body?: unknown) =>
  request<T>(url, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })

export const getProducts = () => request<ProductSummary[]>('/api/products')

export const getProduct = (productId: string) =>
  request<ProductDetail>(`/api/products/${encodeURIComponent(productId)}`)

export const login = (email: string, password: string) => post<AuthResponse>('/api/auth/login', { email, password })
export const signup = (input: SignupInput) => post<AuthResponse>('/api/auth/signup', input)
export const getMe = () => request<User>('/api/auth/me')

export const sendChat = (message: string) => post<ChatResponse>('/api/chat', { message })
export const sendBored = () => post<ChatResponse>('/api/chat/bored')

export const formatPrice = (price: number) =>
  price.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
