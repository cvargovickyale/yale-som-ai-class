import { Link, NavLink } from 'react-router-dom'

const MAIN_PAGES = [
  { to: '/', label: 'Home' },
  { to: '/products', label: 'Products' },
  { to: '/about', label: 'About Us' },
]

const ACCOUNT_PAGES = [
  { to: '/login', label: 'Log In' },
  { to: '/signup', label: 'Create Account' },
]

const linkClass = ({ isActive }: { isActive: boolean }) => (isActive ? 'nav-link active' : 'nav-link')

export default function NavBar() {
  return (
    <header className="navbar">
      <Link to="/" className="brand">
        Campus Customs <span className="brand-sub">Yale Bulldog Blue</span>
      </Link>
      <nav className="nav-links">
        {MAIN_PAGES.map((p) => (
          <NavLink key={p.to} to={p.to} end={p.to === '/'} className={linkClass}>
            {p.label}
          </NavLink>
        ))}
      </nav>
      <nav className="nav-links account">
        {ACCOUNT_PAGES.map((p) => (
          <NavLink key={p.to} to={p.to} className={linkClass}>
            {p.label}
          </NavLink>
        ))}
      </nav>
    </header>
  )
}
