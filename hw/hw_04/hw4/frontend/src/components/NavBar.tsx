import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

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
  const { user, ready, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/')
  }

  return (
    <>
    <div className="announce-bar">Officially licensed Yale apparel · Family-run in New Haven since 1975 · Ask Handsome Dan 🐶</div>
    <header className="navbar">
      <Link to="/" className="brand">
        <span className="brand-name">Campus Customs</span>
        <span className="brand-sub">Yale Bulldog Blue</span>
      </Link>
      <nav className="nav-links">
        {MAIN_PAGES.map((p) => (
          <NavLink key={p.to} to={p.to} end={p.to === '/'} className={linkClass}>
            {p.label}
          </NavLink>
        ))}
      </nav>
      <nav className="nav-links account">
        {!ready ? null : user ? (
          <>
            <span className="greeting">Hi, {user.first_name}</span>
            <button className="nav-link link-button" onClick={handleLogout}>
              Log Out
            </button>
          </>
        ) : (
          ACCOUNT_PAGES.map((p) => (
            <NavLink key={p.to} to={p.to} className={linkClass}>
              {p.label}
            </NavLink>
          ))
        )}
      </nav>
    </header>
    </>
  )
}
