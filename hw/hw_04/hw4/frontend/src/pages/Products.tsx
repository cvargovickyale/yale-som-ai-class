import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getProducts } from '../api'
import ProductCard from '../components/ProductCard'
import type { ProductSummary } from '../types'

// Tab order. Names match backend/main.py CATEGORIES; empty ones are hidden.
const CATEGORIES = ['Hoodies', 'Crewnecks', 'T-Shirts', 'Quarter-Zips', 'Jackets', 'Long Sleeves', 'Other']
const slug = (name: string) => name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')

export default function Products() {
  const [products, setProducts] = useState<ProductSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [params, setParams] = useSearchParams()

  useEffect(() => {
    getProducts()
      .then(setProducts)
      .catch((e: Error) => setError(e.message))
  }, [])

  // Two ways to filter, both kept in the URL:
  //   ?q=<label>&ids=<id,...>  chat search results (set by the chat panel)
  //   ?category=<slug>         a category tab
  const label = params.get('q')
  const ids = useMemo(() => params.get('ids')?.split(',').filter(Boolean) ?? null, [params])
  const activeCategory = ids ? null : (CATEGORIES.find((c) => slug(c) === params.get('category')) ?? null)

  const counts = useMemo(() => {
    const c = new Map<string, number>()
    products?.forEach((p) => c.set(p.category, (c.get(p.category) ?? 0) + 1))
    return c
  }, [products])

  const shown = useMemo(() => {
    if (!products) return null
    if (ids) {
      const byId = new Map(products.map((p) => [p.product_id, p]))
      return ids.map((id) => byId.get(id)).filter((p): p is ProductSummary => p !== undefined)
    }
    return activeCategory ? products.filter((p) => p.category === activeCategory) : products
  }, [products, ids, activeCategory])

  if (error) return <p className="status error">Couldn't load products: {error}</p>
  if (!shown || !products) return <p className="status">Loading products…</p>

  const tabs = [{ name: 'All', count: products.length }, ...CATEGORIES.filter((c) => counts.get(c)).map((c) => ({ name: c, count: counts.get(c)! }))]

  return (
    <>
      <nav className="category-tabs" aria-label="Product categories">
        {tabs.map((t) => {
          const active = t.name === 'All' ? !ids && !activeCategory : t.name === activeCategory
          return (
            <button
              key={t.name}
              className={active ? 'category-tab active' : 'category-tab'}
              aria-pressed={active}
              onClick={() => setParams(t.name === 'All' ? {} : { category: slug(t.name) })}
            >
              {t.name} <span className="tab-count">{t.count}</span>
            </button>
          )
        })}
        {ids && <span className="category-tab active chat-tab">💬 Chat results</span>}
      </nav>

      {ids ? (
        <div className="results-header">
          <div>
            <p className="eyebrow">Results from chat</p>
            <h1>{label || 'Search results'}</h1>
            <p className="muted">
              {shown.length} {shown.length === 1 ? 'item' : 'items'} of {products.length}
            </p>
          </div>
          <button className="button secondary" onClick={() => setParams({})}>
            Show all products
          </button>
        </div>
      ) : (
        <div className="results-header plain">
          <div>
            <h1>{activeCategory ?? 'All products'}</h1>
            <p className="muted">
              {shown.length} items{!activeCategory && ' · Ask the chat to filter, e.g. "show me hoodies"'}
            </p>
          </div>
        </div>
      )}
      <div className="product-grid" key={params.toString()}>
        {shown.map((p) => (
          <ProductCard key={p.product_id} product={p} />
        ))}
      </div>
    </>
  )
}
