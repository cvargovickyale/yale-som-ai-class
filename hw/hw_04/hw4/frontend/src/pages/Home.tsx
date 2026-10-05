import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getProducts } from '../api'
import ProductCard from '../components/ProductCard'
import type { ProductSummary } from '../types'

const PANELS = [
  {
    title: 'Gear for every Bulldog',
    body: 'Students, alumni, and the whole family. Yes, there really is a Yale Grandpa hoodie.',
  },
  {
    title: 'Your college. Your team.',
    body: 'Residential colleges, varsity sports, and the graduate schools. Rep the corner of Yale that is yours.',
  },
  {
    title: 'Made to be worn',
    body: 'Hoodies, crewnecks, quarter-zips, and tees with a relaxed fit for class, the game, or the couch.',
  },
]

export default function Home() {
  const [featured, setFeatured] = useState<ProductSummary[]>([])

  useEffect(() => {
    getProducts()
      .then((all) => setFeatured([...all].sort((a, b) => b.total_stock - a.total_stock).slice(0, 4)))
      .catch(() => setFeatured([]))
  }, [])

  return (
    <>
      <section className="hero">
        <p className="eyebrow">Yale Bulldog Blue by Campus Customs</p>
        <h1>Officially licensed Yale gear, straight from New Haven.</h1>
        <p>
          We've been outfitting Yale from our shop across from campus since 1975. Browse the
          collection, or ask our assistant in the corner what's in stock in your size.
        </p>
        <Link to="/products" className="button">
          Shop all products
        </Link>
      </section>

      <section className="panels">
        {PANELS.map((p) => (
          <div key={p.title} className="panel">
            <h2>{p.title}</h2>
            <p>{p.body}</p>
          </div>
        ))}
      </section>

      {featured.length > 0 && (
        <section>
          <h2>Well stocked right now</h2>
          <div className="product-grid">
            {featured.map((p) => (
              <ProductCard key={p.product_id} product={p} />
            ))}
          </div>
        </section>
      )}
    </>
  )
}
