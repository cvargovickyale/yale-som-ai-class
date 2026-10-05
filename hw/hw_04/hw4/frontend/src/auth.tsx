import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import * as api from './api'
import type { SignupInput, User } from './types'

interface AuthState {
  user: User | null
  ready: boolean // false until a saved token has been checked
  login: (email: string, password: string) => Promise<void>
  signup: (input: SignupInput) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [ready, setReady] = useState(!api.getToken())

  // Restore the session from a saved token (it may have expired).
  useEffect(() => {
    if (!api.getToken()) return
    api
      .getMe()
      .then(setUser)
      .catch(() => api.setToken(null))
      .finally(() => setReady(true))
  }, [])

  async function login(email: string, password: string) {
    const res = await api.login(email, password)
    api.setToken(res.token)
    setUser(res.user)
  }

  async function signup(input: SignupInput) {
    const res = await api.signup(input)
    api.setToken(res.token)
    setUser(res.user)
  }

  function logout() {
    api.setToken(null)
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, ready, login, signup, logout }}>{children}</AuthContext.Provider>
}

// Hook lives beside its provider on purpose (only costs fast-refresh on this file).
// oxlint-disable-next-line react/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
