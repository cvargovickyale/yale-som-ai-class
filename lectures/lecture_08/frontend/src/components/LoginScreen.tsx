import { useState } from "react"
import { login, signup } from "../api"
import WindowChrome from "./WindowChrome"

interface LoginScreenProps {
  onAuthenticated: (token: string, email: string) => void
}

export default function LoginScreen({ onAuthenticated }: LoginScreenProps) {
  const [mode, setMode] = useState<"login" | "signup">("login")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const result = mode === "login" ? await login(email, password) : await signup(email, password)
      onAuthenticated(result.token, result.email)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Try again.")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="login-overlay">
      <WindowChrome title="SOM95 Sign In" icon="🔐" className="login-window">
        <form className="login-form" onSubmit={submit}>
          <div className="login-tabs">
            <button
              type="button"
              className={`login-tab ${mode === "login" ? "bevel-in chip-active" : "bevel-raised"}`}
              onClick={() => setMode("login")}
            >
              Log In
            </button>
            <button
              type="button"
              className={`login-tab ${mode === "signup" ? "bevel-in chip-active" : "bevel-raised"}`}
              onClick={() => setMode("signup")}
            >
              Create Account
            </button>
          </div>

          <label className="login-field">
            <span>Email</span>
            <input
              type="email"
              className="bevel-in"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
            />
          </label>

          <label className="login-field">
            <span>Password</span>
            <input
              type="password"
              className="bevel-in"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={mode === "signup" ? 8 : undefined}
              required
            />
          </label>
          {mode === "signup" && <p className="login-hint">At least 8 characters.</p>}

          {error && <p className="login-error bevel-in">⚠ {error}</p>}

          <button type="submit" className="bevel-raised login-submit" disabled={busy}>
            {busy ? "Please wait…" : mode === "login" ? "Log In" : "Create Account"}
          </button>
        </form>
      </WindowChrome>
    </div>
  )
}
