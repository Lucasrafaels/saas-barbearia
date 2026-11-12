import { useEffect, useState } from 'react'

/** Define o título da aba do navegador para a página atual. */
export function useDocumentTitle(title: string): void {
  useEffect(() => {
    const previous = document.title
    document.title = title ? `${title} — BarberPro` : 'BarberPro'
    return () => { document.title = previous }
  }, [title])
}

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => typeof window !== 'undefined' && window.matchMedia(query).matches)
  useEffect(() => {
    const media = window.matchMedia(query)
    const update = () => setMatches(media.matches)
    update()
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [query])
  return matches
}

/** Paginação local para listas já carregadas. Volta à página 1 quando `resetKey` muda. */
export function useLocalPagination<T>(items: T[], pageSize: number, resetKey: string) {
  const [page, setPage] = useState(1)
  const [lastKey, setLastKey] = useState(resetKey)
  if (lastKey !== resetKey) {
    setLastKey(resetKey)
    setPage(1)
  }
  const totalPages = Math.max(1, Math.ceil(items.length / pageSize))
  const current = Math.min(page, totalPages)
  const start = (current - 1) * pageSize
  return {
    page: current,
    setPage,
    pageItems: items.slice(start, start + pageSize),
    total: items.length,
    pageSize,
  }
}

/** Relógio que atualiza a cada `intervalMs` (para a linha do "agora" na agenda). */
export function useNow(intervalMs = 60_000): Date {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), intervalMs)
    return () => window.clearInterval(timer)
  }, [intervalMs])
  return now
}
