import { clearAuthConfig, setAuthConfig } from '@/lib/api-client'
import { createContext, useCallback, useContext, useEffect, useState } from 'react'

type AuthState = {
  token: string
  email: string
  name: string
  role: string
}

type AuthContextValue = {
  auth: AuthState | null
  isAuthenticated: boolean
  isApproved: boolean
  login: (token: string, email: string, name: string, role?: string) => void
  logout: () => void
}

const STORAGE_KEYS = {
  token: 'pseudolab_auth_token',
  email: 'pseudolab_auth_email',
  name: 'pseudolab_auth_name',
  role: 'pseudolab_auth_role',
} as const

function loadFromStorage(): AuthState | null {
  const token = localStorage.getItem(STORAGE_KEYS.token)
  const email = localStorage.getItem(STORAGE_KEYS.email)
  const name = localStorage.getItem(STORAGE_KEYS.name)
  const role = localStorage.getItem(STORAGE_KEYS.role)
  if (token && email) {
    return { token, email, name: name ?? '', role: role ?? 'member' }
  }
  return null
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [auth, setAuth] = useState<AuthState | null>(() => {
    const saved = loadFromStorage()
    if (saved) {
      setAuthConfig(saved.token, saved.email, saved.name)
    }
    return saved
  })

  useEffect(() => {
    if (auth) {
      setAuthConfig(auth.token, auth.email, auth.name)
    }
  }, [auth])

  const login = useCallback((token: string, email: string, name: string, role = 'member') => {
    localStorage.setItem(STORAGE_KEYS.token, token)
    localStorage.setItem(STORAGE_KEYS.email, email)
    localStorage.setItem(STORAGE_KEYS.name, name)
    localStorage.setItem(STORAGE_KEYS.role, role)
    setAuthConfig(token, email, name)
    setAuth({ token, email, name, role })
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEYS.token)
    localStorage.removeItem(STORAGE_KEYS.email)
    localStorage.removeItem(STORAGE_KEYS.name)
    localStorage.removeItem(STORAGE_KEYS.role)
    clearAuthConfig()
    setAuth(null)
  }, [])

  const isApproved = auth !== null && auth.role !== 'pending'

  return (
    <AuthContext.Provider
      value={{ auth, isAuthenticated: auth !== null, isApproved, login, logout }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
