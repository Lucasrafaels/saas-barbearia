import { Navigate, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { PageLoader } from '../components/PageLoader'
import type { UserRole } from '../types'

interface ProtectedRouteProps {
  children: ReactNode
  allowedRoles?: UserRole[]
  requiresBarbershop?: boolean
}

export function ProtectedRoute({ children, allowedRoles, requiresBarbershop = true }: ProtectedRouteProps) {
  const { user, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) return <PageLoader label="Validando sua sessão..." />
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />
  if (requiresBarbershop && !user.barbershop) return <Navigate to="/onboarding" replace />
  if (!requiresBarbershop && user.barbershop) return <Navigate to="/" replace />
  if (allowedRoles && !allowedRoles.includes(user.tipo_perfil)) return <Navigate to="/" replace />
  return <>{children}</>
}
