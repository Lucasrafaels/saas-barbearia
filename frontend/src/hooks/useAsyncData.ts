import { useCallback, useEffect, useRef, useState, type DependencyList } from 'react'

interface AsyncState<T> {
  data: T | null
  /** Verdadeiro apenas enquanto ainda não há dados para exibir. */
  isLoading: boolean
  /** Verdadeiro quando uma recarga acontece com dados já na tela. */
  isRefreshing: boolean
  error: unknown
  reload: () => Promise<void>
  setData: (updater: (current: T | null) => T | null) => void
}

/**
 * Estado padronizado para carregamentos de tela.
 * - Ignora respostas antigas quando as dependências mudam (evita condição de corrida).
 * - Mantém os dados atuais durante recargas, para não piscar a tela inteira.
 */
export function useAsyncData<T>(loader: () => Promise<T>, dependencies: DependencyList): AsyncState<T> {
  const [data, setDataState] = useState<T | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [isPending, setIsPending] = useState(true)
  const requestId = useRef(0)

  const reload = useCallback(async () => {
    const id = ++requestId.current
    setIsPending(true)
    setError(null)
    try {
      const result = await loader()
      if (id === requestId.current) setDataState(result)
    } catch (requestError) {
      if (id === requestId.current) setError(requestError)
    } finally {
      if (id === requestId.current) setIsPending(false)
    }
  // O loader é controlado pelas dependências declaradas pelo consumidor.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies)

  useEffect(() => {
    void reload()
  }, [reload])

  const setData = useCallback((updater: (current: T | null) => T | null) => setDataState(updater), [])

  return {
    data,
    isLoading: isPending && data === null,
    isRefreshing: isPending && data !== null,
    error,
    reload,
    setData,
  }
}
