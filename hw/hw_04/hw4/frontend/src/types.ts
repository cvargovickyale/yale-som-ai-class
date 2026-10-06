// Mirrors backend/models.py — keep the two in sync.

export interface SizeStock {
  size: string
  quantity: number
}

export interface ProductSummary {
  product_id: string
  name: string
  garment_type: string
  price: number
  short_description: string
  image_url: string
  total_stock: number
}

export interface ProductDetail extends ProductSummary {
  description: string
  colors: string[]
  search_tags: string[]
  sizes: SizeStock[]
}

export interface User {
  id: number
  first_name: string
  last_name: string
  email: string
}

export interface AuthResponse {
  token: string
  user: User
}

export interface SignupInput {
  first_name: string
  last_name: string
  email: string
  password: string
  confirm_password: string
}

export interface ChatResponse {
  reply: string
  products: ProductSummary[]
  // Set when the shopper was browsing/searching: the Products page filters
  // to exactly `products` under this heading. Null = answer only.
  results_label: string | null
}
