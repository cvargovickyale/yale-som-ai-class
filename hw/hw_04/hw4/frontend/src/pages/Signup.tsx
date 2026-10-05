import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'
import type { SignupInput } from '../types'

const MIN_PASSWORD = 8

export default function Signup() {
  const { signup } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = new FormData(e.currentTarget)
    const input = Object.fromEntries(
      ['first_name', 'last_name', 'email', 'password', 'confirm_password'].map((k) => [k, String(form.get(k) ?? '')]),
    ) as unknown as SignupInput

    // Quick checks here; the backend re-checks everything.
    if (input.password.length < MIN_PASSWORD) return setError(`Password must be at least ${MIN_PASSWORD} characters.`)
    if (input.password !== input.confirm_password) return setError('Passwords do not match.')

    setError(null)
    setBusy(true)
    try {
      await signup(input)
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create account')
    } finally {
      setBusy(false)
    }
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
          <input type="password" name="password" autoComplete="new-password" minLength={MIN_PASSWORD} required />
        </label>
        <label>
          Confirm password
          <input type="password" name="confirm_password" autoComplete="new-password" required />
        </label>
        {error && <p className="form-error">{error}</p>}
        <button type="submit" className="button" disabled={busy}>
          {busy ? 'Creating account…' : 'Create account'}
        </button>
      </form>
      <p className="muted">
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </section>
  )
}
