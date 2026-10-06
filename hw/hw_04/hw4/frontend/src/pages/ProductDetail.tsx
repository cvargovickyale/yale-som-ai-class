import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { formatPrice, getProduct } from '../api'
import { matchFrameToPhoto } from '../imageTone'
import type { ProductDetail as Product } from '../types'

// The single-item page, shown as a popup over the page it was opened from
// (P9). App.tsx keeps that page rendered behind it; see backgroundLocation.
export default function ProductDetail() {
  const { productId = '' } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const dialogRef = useRef<HTMLDivElement>(null)
  const openedInApp = Boolean((location.state as { backgroundLocation?: unknown } | null)?.backgroundLocation)

  // Tag each result with the id it was fetched for, so switching products
  // shows "Loading…" instead of the previous item.
  const [result, setResult] = useState<{ id: string; product?: Product; error?: string } | null>(null)

  useEffect(() => {
    getProduct(productId)
      .then((product) => setResult({ id: productId, product }))
      .catch((e: Error) => setResult({ id: productId, error: e.message }))
  }, [productId])

  // Opened from a card: go back to exactly where they were (scroll and filters
  // intact). Opened from a pasted/reloaded URL: fall back to all products.
  const close = useCallback(() => (openedInApp ? navigate(-1) : navigate('/products')), [openedInApp, navigate])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && close()
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden' // the page behind doesn't scroll
    dialogRef.current?.focus()
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [close])

  const product = result?.id === productId ? result.product : undefined
  const error = result?.id === productId ? result.error : undefined

  return (
    <div className="modal-backdrop" onClick={close}>
      <div
        ref={dialogRef}
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={product?.name ?? 'Product'}
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
      >
        <button className="modal-close" onClick={close} aria-label="Close">
          ×
        </button>
        {error ? (
          <p className="status error">{error}</p>
        ) : !product ? (
          <p className="status">Loading…</p>
        ) : (
          <article className="detail">
            <div className="detail-image">
              <img src={product.image_url} alt={product.name} onLoad={matchFrameToPhoto} />
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
        )}
      </div>
    </div>
  )
}
