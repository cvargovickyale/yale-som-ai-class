import { Link } from 'react-router-dom'

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div>
          <p className="footer-brand">Campus Customs</p>
          <p>Yale Bulldog Blue · officially licensed Yale apparel, family-run in New Haven since 1975.</p>
        </div>
        <div>
          <p className="footer-head">Shop</p>
          <Link to="/products?category=hoodies">Hoodies</Link>
          <Link to="/products?category=crewnecks">Crewnecks</Link>
          <Link to="/products?category=t-shirts">T-Shirts</Link>
          <Link to="/products">All products</Link>
        </div>
        <div>
          <p className="footer-head">Visit</p>
          <p>
            57 Broadway
            <br />
            New Haven, CT
          </p>
          <Link to="/about">About us</Link>
        </div>
      </div>
      <p className="footer-fine">Yale School of Management class project demo, not the real Campus Customs store (yalebulldogblue.com).</p>
    </footer>
  )
}
