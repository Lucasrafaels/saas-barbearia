import { Navigate, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { ConnectionLost, PageLoader } from '../components/Feedback'
import type { UserRole } from '../types'

interface ProtectedRouteProps {
  children: ReactNode
  allowedRoles?: UserRole[]
  requiresBarbershop?: boolean
}

export function ProtectedRoute({ children, allowedRoles, requiresBarbershop = true }: ProtectedRouteProps) {
  const { user, isLoading, connectionError, retrySession } = useAuth()
  const location = useLocation()

  if (isLoading) return <PageLoader full label="Validando sua sessão…" />
  if (connectionError) return <ConnectionLost onRetry={retrySession} />
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />
  if (requiresBarbershop && !user.barbershop) return <Navigate to="/onboarding" replace />
  if (!requiresBarbershop && user.barbershop) return <Navigate to="/" replace />
  if (allowedRoles && !allowedRoles.includes(user.tipo_perfil)) return <Navigate to="/" replace />
  return <>{children}</>
}
