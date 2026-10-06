import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getProducts } from '../api'
import FitPicker from '../components/FitPicker'
import ProductCard from '../components/ProductCard'
import { matchFrameToPhoto } from '../imageTone'
import type { ProductSummary } from '../types'

// Hero collage and category tiles use catalogue photos measured (P10) to have
// clean white backgrounds. Only 28 of 102 do; quarter-zips and jackets have none,
// so those tiles fall back to their best-stocked photo in a dark frame.
const HERO_IDS = ['champion-reverse-weave-hoodie-1', 'champion-reverse-weave-crewneck', '2025-yale-vs-harvard-t-shirt', 'district-vit-crewneck-vintage-bulldog']
const TILE_COVERS: Record<string, string> = {
  Hoodies: 'champion-reverse-weave-hoodie-1',
  Crewnecks: 'champion-reverse-weave-crewneck',
  'T-Shirts': '2025-yale-vs-harvard-t-shirt',
  'Long Sleeves': 'ua-mens-tech-l-s-2-0',
}
const CATEGORY_ORDER = ['Hoodies', 'Crewnecks', 'T-Shirts', 'Quarter-Zips', 'Jackets', 'Long Sleeves']
const slug = (name: string) => name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')

const PANELS = [
  { title: 'Gear for every Bulldog', body: 'Students, alumni, and the whole family. Yes, there really is a Yale Grandpa hoodie.' },
  { title: 'Your college. Your team.', body: 'Residential colleges, varsity sports, and the graduate schools. Rep the corner of Yale that is yours.' },
  { title: 'Made to be worn', body: 'Hoodies, crewnecks, quarter-zips, and tees with a relaxed fit for class, the game, or the couch.' },
]

export default function Home() {
  const [products, setProducts] = useState<ProductSummary[]>([])
  const navigate = useNavigate()

  useEffect(() => {
    getProducts()
      .then(setProducts)
      .catch(() => setProducts([]))
  }, [])

  const byId = useMemo(() => new Map(products.map((p) => [p.product_id, p])), [products])
  const counts = useMemo(() => {
    const c = new Map<string, number>()
    products.forEach((p) => c.set(p.category, (c.get(p.category) ?? 0) + 1))
    return c
  }, [products])
  const tiles = CATEGORY_ORDER.map((name) => ({
    name,
    count: counts.get(name) ?? 0,
    cover:
      byId.get(TILE_COVERS[name]) ??
      products.filter((p) => p.category === name).sort((a, b) => b.total_stock - a.total_stock)[0],
  })).filter((t) => t.count > 0)
  const featured = [...products].sort((a, b) => b.total_stock - a.total_stock).slice(0, 4)
  const heroShots = HERO_IDS.map((id) => byId.get(id)).filter((p): p is ProductSummary => !!p)
  const pickCategory = (name: string) => navigate(`/products?category=${slug(name)}`)

  return (
    <>
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Yale Bulldog Blue by Campus Customs</p>
          <h1>Officially licensed Yale gear, straight from New Haven.</h1>
          <p className="hero-lede">
            We've been outfitting Yale from our shop across from campus since 1975. Browse the collection, or ask
            Handsome Dan in the corner what's in stock in your size.
          </p>
          <div className="hero-actions">
            <Link to="/products" className="button">
              Shop all products
            </Link>
            <Link to="/products?category=hoodies" className="button secondary">
              Shop hoodies
            </Link>
          </div>
        </div>
        <div className="hero-collage" aria-hidden="true">
          {heroShots.map((p, i) => (
            <div key={p.product_id} className={`collage-card c${i}`}>
              <img src={p.image_url} alt="" onLoad={matchFrameToPhoto} />
            </div>
          ))}
        </div>
      </section>

      <section className="home-section">
        <div className="section-head">
          <h2>Shop by category</h2>
          <Link to="/products">View all</Link>
        </div>
        <div className="category-tiles">
          {tiles.map((t) => (
            <Link key={t.name} to={`/products?category=${slug(t.name)}`} className="tile">
              {t.cover && <img src={t.cover.image_url} alt="" loading="lazy" onLoad={matchFrameToPhoto} />}
              <span className="tile-label">
                {t.name} <span className="tile-count">{t.count}</span>
              </span>
            </Link>
          ))}
        </div>
      </section>

      <section className="home-section fit-section">
        <div className="fit-copy">
          <p className="eyebrow">New · Find your fit</p>
          <h2>Tap what you want to wear.</h2>
          <p>
            Hood, zip, sleeves, or an outer layer: tap the part of the outfit you're shopping for and we'll show you
            every match in stock.
          </p>
        </div>
        <FitPicker counts={counts} onPick={pickCategory} />
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
        <section className="home-section">
          <div className="section-head">
            <h2>Well stocked right now</h2>
          </div>
          <div className="product-grid">
            {featured.map((p, i) => (
              <ProductCard key={p.product_id} product={p} index={i} />
            ))}
          </div>
        </section>
      )}
    </>
  )
}
