import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { PageLoader } from '../components/PageLoader'
import { useAuth } from '../contexts/AuthContext'

export function PublicRoute({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth()
  if (isLoading) return <PageLoader label="Carregando..." />
  if (user) return <Navigate to={user.barbershop ? '/' : '/onboarding'} replace />
  return <>{children}</>
}
