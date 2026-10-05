import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'

// Form only for now — the backend login endpoint arrives in P4.
export default function Login() {
  const [notice, setNotice] = useState<string | null>(null)

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setNotice('Sign-in is coming soon. Accounts are not connected yet.')
  }

  return (
    <section className="form-card">
      <h1>Log in</h1>
      <form onSubmit={handleSubmit}>
        <label>
          Email
          <input type="email" name="email" autoComplete="email" required />
        </label>
        <label>
          Password
          <input type="password" name="password" autoComplete="current-password" required />
        </label>
        <button type="submit" className="button">
          Log in
        </button>
      </form>
      {notice && <p className="notice">{notice}</p>}
      <p className="muted">
        New here? <Link to="/signup">Create an account</Link>
      </p>
    </section>
  )
}
