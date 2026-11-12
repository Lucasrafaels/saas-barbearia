import axios from 'axios'
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { authApi } from '../api/endpoints'
import type { LoginInput, RegisterInput, User } from '../types'
import { clearStoredTokens, getStoredAccessToken, storeAccessToken } from '../utils/storage'
import { useToast } from './ToastContext'

interface AuthContextValue {
  user: User | null
  isLoading: boolean
  /** Falha de rede ao validar a sessão salva (a sessão é mantida para nova tentativa). */
  connectionError: boolean
  retrySession: () => void
  login: (input: LoginInput) => Promise<User>
  register: (input: RegisterInput) => Promise<void>
  /** Encerra a sessão no servidor (quando possível) e localmente. Nunca lança erro. */
  logout: () => Promise<void>
  /** Encerra só a sessão local (ex.: após trocar a senha, quando o servidor já revogou os tokens). */
  endLocalSession: () => void
  refreshUser: () => Promise<User>
  setCurrentUser: (user: User) => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const { showToast } = useToast()
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [connectionError, setConnectionError] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const hasSession = useRef(false)

  useEffect(() => {
    hasSession.current = user !== null
  }, [user])

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
      if (!getStoredAccessToken()) {
        setIsLoading(false)
        return
      }
      try {
        await refreshUser()
        setConnectionError(false)
      } catch (error) {
        // Sem resposta do servidor: problema de conexão, não de sessão.
        // Mantém o token salvo para tentar de novo em vez de deslogar.
        if (axios.isAxiosError(error) && !error.response) setConnectionError(true)
        else clearSession()
      } finally {
        setIsLoading(false)
      }
    }
    void bootstrap()

    const handleExpired = () => {
      const hadSession = hasSession.current
      clearSession()
      if (hadSession) showToast('Sua sessão expirou. Entre novamente para continuar.', 'info')
    }
    window.addEventListener('auth:expired', handleExpired)
    return () => window.removeEventListener('auth:expired', handleExpired)
  }, [clearSession, refreshUser, showToast, attempt])

  const retrySession = useCallback(() => {
    setIsLoading(true)
    setConnectionError(false)
    setAttempt((value) => value + 1)
  }, [])

  const login = useCallback(async (input: LoginInput) => {
    const { data } = await authApi.login(input)
    storeAccessToken(data.access)
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
    try {
      await authApi.logout()
    } catch {
      // O cookie pode já ter expirado; a sessão local é encerrada de qualquer forma.
    } finally {
      clearSession()
    }
  }, [clearSession])

  const value = useMemo(() => ({
    user,
    isLoading,
    connectionError,
    retrySession,
    login,
    register,
    logout,
    endLocalSession: clearSession,
    refreshUser,
    setCurrentUser: setUser,
  }), [user, isLoading, connectionError, retrySession, login, register, logout, clearSession, refreshUser])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth deve ser usado dentro de AuthProvider.')
  return context
}

export const roleLabels: Record<User['tipo_perfil'], string> = {
  admin: 'Administrador',
  barbeiro: 'Barbeiro',
  cliente: 'Cliente',
}
