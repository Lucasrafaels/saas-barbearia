import { useCallback, useEffect, useState, type DependencyList } from 'react'

interface AsyncState<T> {
  data: T | null
  isLoading: boolean
  error: unknown
  reload: () => Promise<void>
}

/** Estado padronizado para listagens e carregamentos de tela. */
export function useAsyncData<T>(loader: () => Promise<T>, dependencies: DependencyList): AsyncState<T> {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<unknown>(null)
  const [isLoading, setIsLoading] = useState(true)

  const reload = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      setData(await loader())
    } catch (requestError) {
      setError(requestError)
    } finally {
      setIsLoading(false)
    }
  // loader is intentionally controlled by the consumer's dependencies.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencies)

  useEffect(() => {
    void reload()
  }, [reload])

  return { data, isLoading, error, reload }
}
