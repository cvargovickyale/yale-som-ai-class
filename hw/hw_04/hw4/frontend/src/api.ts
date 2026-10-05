import type { ChatResponse, ProductDetail, ProductSummary } from './types'

// Relative URLs: Vite proxies /api and /images to the FastAPI backend.
async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail ?? `Request failed (${res.status})`)
  }
  return res.json() as Promise<T>
}

export const getProducts = () => request<ProductSummary[]>('/api/products')

export const getProduct = (productId: string) =>
  request<ProductDetail>(`/api/products/${encodeURIComponent(productId)}`)

export const sendChat = (message: string) =>
  request<ChatResponse>('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  })

export const formatPrice = (price: number) =>
  price.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
