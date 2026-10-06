import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getProducts } from '../api'
import ProductCard from '../components/ProductCard'
import type { ProductSummary } from '../types'

export default function Products() {
  const [products, setProducts] = useState<ProductSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [params, setParams] = useSearchParams()

  useEffect(() => {
    getProducts()
      .then(setProducts)
      .catch((e: Error) => setError(e.message))
  }, [])

  // Chat search results arrive as ?q=<label>&ids=<id,id,...> (set by the chat panel).
  const label = params.get('q')
  const ids = useMemo(() => params.get('ids')?.split(',').filter(Boolean) ?? null, [params])

  const shown = useMemo(() => {
    if (!products || !ids) return products
    const byId = new Map(products.map((p) => [p.product_id, p]))
    return ids.map((id) => byId.get(id)).filter((p): p is ProductSummary => p !== undefined)
  }, [products, ids])

  if (error) return <p className="status error">Couldn't load products: {error}</p>
  if (!shown) return <p className="status">Loading products…</p>

  return (
    <>
      {ids ? (
        <div className="results-header">
          <div>
            <p className="eyebrow">Results from chat</p>
            <h1>{label || 'Search results'}</h1>
            <p className="muted">
              {shown.length} {shown.length === 1 ? 'item' : 'items'} of {products!.length}
            </p>
          </div>
          <button className="button secondary" onClick={() => setParams({})}>
            Show all products
          </button>
        </div>
      ) : (
        <>
          <h1>All products</h1>
          <p className="muted">{shown.length} items · Ask the chat to filter, e.g. "show me hoodies"</p>
        </>
      )}
      <div className="product-grid" key={params.toString()}>
        {shown.map((p) => (
          <ProductCard key={p.product_id} product={p} />
        ))}
      </div>
    </>
  )
}
