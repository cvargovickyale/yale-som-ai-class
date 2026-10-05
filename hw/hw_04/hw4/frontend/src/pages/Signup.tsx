import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'

// Form only for now — the backend signup endpoint arrives in P4.
export default function Signup() {
  const [notice, setNotice] = useState<string | null>(null)

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setNotice('Account creation is coming soon. Accounts are not connected yet.')
  }

  return (
    <section className="form-card">
      <h1>Create account</h1>
      <form onSubmit={handleSubmit}>
        <div className="form-row">
          <label>
            First name
            <input name="first_name" autoComplete="given-name" required />
          </label>
          <label>
            Last name
            <input name="last_name" autoComplete="family-name" required />
          </label>
        </div>
        <label>
          Email
          <input type="email" name="email" autoComplete="email" required />
        </label>
        <label>
          Password
          <input type="password" name="password" autoComplete="new-password" minLength={8} required />
        </label>
        <button type="submit" className="button">
          Create account
        </button>
      </form>
      {notice && <p className="notice">{notice}</p>}
      <p className="muted">
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </section>
  )
}
