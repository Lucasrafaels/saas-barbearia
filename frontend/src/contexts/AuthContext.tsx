import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { authApi } from '../api/endpoints'
import type { LoginInput, RegisterInput, User } from '../types'
import { clearStoredTokens, getStoredTokens, storeTokens } from '../utils/storage'

interface AuthContextValue {
  user: User | null
  isLoading: boolean
  login: (input: LoginInput) => Promise<User>
  register: (input: RegisterInput) => Promise<void>
  logout: () => Promise<void>
  refreshUser: () => Promise<User>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const refreshUser = useCallback(async () => {
    const { data } = await authApi.me()
    setUser(data)
    return data
  }, [])

  const clearSession = useCallback(() => {
    clearStoredTokens()
    setUser(null)
  }, [])

  useEffect(() => {
    const bootstrap = async () => {
      if (!getStoredTokens()) {
        setIsLoading(false)
        return
      }
      try {
        await refreshUser()
      } catch {
        clearSession()
      } finally {
        setIsLoading(false)
      }
    }
    void bootstrap()

    window.addEventListener('auth:expired', clearSession)
    return () => window.removeEventListener('auth:expired', clearSession)
  }, [clearSession, refreshUser])

  const login = useCallback(async (input: LoginInput) => {
    const { data: tokens } = await authApi.login(input)
    storeTokens(tokens)
    try {
      return await refreshUser()
    } catch (error) {
      clearSession()
      throw error
    }
  }, [clearSession, refreshUser])

  const register = useCallback(async (input: RegisterInput) => {
    await authApi.register(input)
  }, [])

  const logout = useCallback(async () => {
    const refresh = getStoredTokens()?.refresh
    try {
      if (refresh) await authApi.logout(refresh)
    } finally {
      clearSession()
    }
  }, [clearSession])

  const value = useMemo(() => ({ user, isLoading, login, register, logout, refreshUser }), [user, isLoading, login, register, logout, refreshUser])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth deve ser usado dentro de AuthProvider.')
  return context
}
