import { createContext, useContext, useMemo, type ReactNode } from 'react'
import { barbershopApi } from '../api/endpoints'
import { useAsyncData } from '../hooks/useAsyncData'
import type { Barbershop } from '../types'

interface BarbershopContextValue {
  barbershop: Barbershop | null
  isLoading: boolean
  error: unknown
  reload: () => Promise<void>
  setBarbershop: (barbershop: Barbershop) => void
}

const BarbershopContext = createContext<BarbershopContextValue | undefined>(undefined)

/** Barbearia (tenant) do usuário autenticado, carregada uma vez para todo o painel. */
export function BarbershopProvider({ children }: { children: ReactNode }) {
  const { data, isLoading, error, reload, setData } = useAsyncData(() => barbershopApi.current(), [])
  const value = useMemo<BarbershopContextValue>(() => ({
    barbershop: data,
    isLoading,
    error,
    reload,
    setBarbershop: (barbershop) => setData(() => barbershop),
  }), [data, isLoading, error, reload, setData])
  return <BarbershopContext.Provider value={value}>{children}</BarbershopContext.Provider>
}

export function useBarbershop(): BarbershopContextValue {
  const context = useContext(BarbershopContext)
  if (!context) throw new Error('useBarbershop deve ser usado dentro de BarbershopProvider.')
  return context
}
