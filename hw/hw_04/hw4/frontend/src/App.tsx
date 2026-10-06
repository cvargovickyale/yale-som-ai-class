import { matchPath, Route, Routes, useLocation, type Location } from 'react-router-dom'
import ChatWidget from './components/ChatWidget'
import NavBar from './components/NavBar'
import About from './pages/About'
import Home from './pages/Home'
import Login from './pages/Login'
import ProductDetail from './pages/ProductDetail'
import Products from './pages/Products'
import Signup from './pages/Signup'

// Product pages open as a popup over a "background" page (P9). A card or chat
// link passes the page it was clicked on as state.backgroundLocation; a
// pasted or reloaded product URL uses the full Products page instead. The
// background keeps rendering, so its filters and scroll position survive.
const PRODUCTS_PAGE = { pathname: '/products', search: '', hash: '', state: null, key: 'products' } as Location

export default function App() {
  const location = useLocation()
  const fromState = (location.state as { backgroundLocation?: Location } | null)?.backgroundLocation
  const isProductUrl = matchPath('/products/:productId', location.pathname) !== null
  const background = isProductUrl ? (fromState ?? PRODUCTS_PAGE) : undefined

  return (
    <>
      <NavBar />
      <main className="page">
        <Routes location={background ?? location}>
          <Route path="/" element={<Home />} />
          <Route path="/products" element={<Products />} />
          <Route path="/about" element={<About />} />
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="*" element={<p className="status">Page not found.</p>} />
        </Routes>
      </main>
      {background && (
        <Routes>
          <Route path="/products/:productId" element={<ProductDetail />} />
        </Routes>
      )}
      <ChatWidget />
    </>
  )
}
