import type { CSSProperties } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { formatPrice } from '../api'
import { matchFrameToPhoto } from '../imageTone'
import type { ProductSummary } from '../types'

const LOW_STOCK = 25 // total units across sizes; 8 of 102 products qualify

export default function ProductCard({ product, index = 0 }: { product: ProductSummary; index?: number }) {
  // The page this card sits on stays visible behind the product popup (P9).
  const location = useLocation()
  const badge =
    product.total_stock === 0 ? 'Sold out' : product.total_stock <= LOW_STOCK ? `Only ${product.total_stock} left` : null
  return (
    <Link
      to={`/products/${product.product_id}`}
      state={{ backgroundLocation: location }}
      className="product-card"
      // Staggered fade-in: each card starts a little after the one before (capped).
      style={{ '--i': Math.min(index, 12) } as CSSProperties}
    >
      <div className="product-card-media">
        <img src={product.image_url} alt={product.name} loading="lazy" onLoad={matchFrameToPhoto} />
        {badge && <span className="stock-badge">{badge}</span>}
      </div>
      <div className="product-card-body">
        <p className="card-category">{product.category}</p>
        <h3>{product.name}</h3>
        <p className="short-desc">{product.short_description}</p>
        <p className="price">{formatPrice(product.price)}</p>
      </div>
    </Link>
  )
}
