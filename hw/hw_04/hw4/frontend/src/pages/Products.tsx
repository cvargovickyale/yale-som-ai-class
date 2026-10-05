import { useEffect, useState } from 'react'
import { getProducts } from '../api'
import ProductCard from '../components/ProductCard'
import type { ProductSummary } from '../types'

export default function Products() {
  const [products, setProducts] = useState<ProductSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getProducts()
      .then(setProducts)
      .catch((e: Error) => setError(e.message))
  }, [])

  if (error) return <p className="status error">Couldn't load products: {error}</p>
  if (!products) return <p className="status">Loading products…</p>

  return (
    <>
      <h1>All products</h1>
      <p className="muted">{products.length} items</p>
      <div className="product-grid">
        {products.map((p) => (
          <ProductCard key={p.product_id} product={p} />
        ))}
      </div>
    </>
  )
}
