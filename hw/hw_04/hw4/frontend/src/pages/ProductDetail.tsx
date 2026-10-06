import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { formatPrice, getProduct } from '../api'
import type { ProductDetail as Product } from '../types'

export default function ProductDetail() {
  const { productId = '' } = useParams()
  // Opened from a filtered results view? Link back to it instead of the full list.
  const from = (useLocation().state as { from?: string } | null)?.from
  const backTo = from?.startsWith('/products?') ? from : '/products'
  // Tag each result with the id it was fetched for, so navigating to another
  // product shows "Loading…" instead of the previous item.
  const [result, setResult] = useState<{ id: string; product?: Product; error?: string } | null>(null)

  useEffect(() => {
    getProduct(productId)
      .then((product) => setResult({ id: productId, product }))
      .catch((e: Error) => setResult({ id: productId, error: e.message }))
  }, [productId])

  if (result?.id !== productId) return <p className="status">Loading…</p>
  if (result.error || !result.product) return <p className="status error">{result.error}</p>
  const { product } = result

  return (
    <>
      <Link to={backTo} className="back-link">
        {backTo === '/products' ? '← All products' : '← Back to results'}
      </Link>
      <article className="detail">
        <div className="detail-image">
          <img src={product.image_url} alt={product.name} />
        </div>
        <div className="detail-info">
          <p className="eyebrow">{product.garment_type}</p>
          <h1>{product.name}</h1>
          <p className="detail-price">{formatPrice(product.price)}</p>
          <p>{product.description}</p>

          {product.colors.length > 0 && (
            <p>
              <strong>Colors:</strong> {product.colors.join(', ')}
            </p>
          )}

          <h2>Sizes</h2>
          <ul className="sizes">
            {product.sizes.map((s) => (
              <li key={s.size} className={s.quantity > 0 ? 'size in-stock' : 'size sold-out'}>
                <span className="size-label">{s.size}</span>
                <span className="size-qty">{s.quantity > 0 ? `${s.quantity} in stock` : 'Sold out'}</span>
              </li>
            ))}
          </ul>
        </div>
      </article>
    </>
  )
}
