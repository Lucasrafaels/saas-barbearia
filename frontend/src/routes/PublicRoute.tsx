import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { ConnectionLost, PageLoader } from '../components/Feedback'
import { useAuth } from '../contexts/AuthContext'

export function PublicRoute({ children }: { children: ReactNode }) {
  const { user, isLoading, connectionError, retrySession } = useAuth()
  if (isLoading) return <PageLoader full label="Carregando…" />
  if (connectionError) return <ConnectionLost onRetry={retrySession} />
  if (user) return <Navigate to={user.barbershop ? '/' : '/onboarding'} replace />
  return <>{children}</>
}
