import { Link } from 'react-router-dom'
import { formatPrice } from '../api'
import type { ProductSummary } from '../types'

export default function ProductCard({ product }: { product: ProductSummary }) {
  return (
    <Link to={`/products/${product.product_id}`} className="product-card">
      <img src={product.image_url} alt={product.name} loading="lazy" />
      <div className="product-card-body">
        <h3>{product.name}</h3>
        <p className="price">{formatPrice(product.price)}</p>
        <p className="short-desc">{product.short_description}</p>
      </div>
    </Link>
  )
}
