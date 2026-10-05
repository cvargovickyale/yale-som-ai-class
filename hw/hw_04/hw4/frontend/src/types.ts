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

export interface ChatResponse {
  reply: string
  products: ProductSummary[]
}
