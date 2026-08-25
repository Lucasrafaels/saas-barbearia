import type { AuthTokens } from '../types'

const AUTH_KEY = 'barbearia.auth'

export function getStoredTokens(): AuthTokens | null {
  try {
    const value = localStorage.getItem(AUTH_KEY)
    return value ? (JSON.parse(value) as AuthTokens) : null
  } catch {
    return null
  }
}

export function storeTokens(tokens: AuthTokens): void {
  localStorage.setItem(AUTH_KEY, JSON.stringify(tokens))
}

export function clearStoredTokens(): void {
  localStorage.removeItem(AUTH_KEY)
}
