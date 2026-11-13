import { createContext, useCallback, useContext, useEffect, useMemo, useRef, type ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
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

/**
 * Barbearia (tenant) do usuário autenticado, compartilhada por todo o painel.
 *
 * É carregada ao entrar e conferida de novo a cada navegação e quando a aba
 * volta a ficar visível. Assim, uma mudança feita em outra sessão (dias de
 * funcionamento, horário, desativação) chega à barra lateral, ao calendário e
 * ao aviso de barbearia desativada sem recarregar a página (FE-14). Se nada
 * mudou, o estado não é trocado e nenhuma tela é redesenhada; se a consulta
 * falhar, os dados atuais são mantidos.
 */
export function BarbershopProvider({ children }: { children: ReactNode }) {
  const { data, isLoading, error, reload, setData } = useAsyncData(() => barbershopApi.current(), [])
  const location = useLocation()

  const refresh = useCallback(async () => {
    try {
      const fresh = await barbershopApi.current()
      setData((current) => (current && fresh && JSON.stringify(current) === JSON.stringify(fresh) ? current : fresh))
    } catch {
      // Mantém os dados atuais; a próxima navegação tenta de novo.
    }
  }, [setData])

  const isFirstPath = useRef(true)
  useEffect(() => {
    if (isFirstPath.current) {
      isFirstPath.current = false
      return
    }
    void refresh()
  }, [location.pathname, refresh])

  useEffect(() => {
    const onVisible = () => { if (document.visibilityState === 'visible') void refresh() }
    document.addEventListener('visibilitychange', onVisible)
    return () => document.removeEventListener('visibilitychange', onVisible)
  }, [refresh])
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
