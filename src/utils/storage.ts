const AUTH_KEY = 'barbearia.auth'

export function getStoredAccessToken(): string | null {
  try {
    const value = localStorage.getItem(AUTH_KEY)
    return value ? JSON.parse(value).access : null
  } catch {
    return null
  }
}

export function storeAccessToken(access: string): void {
  localStorage.setItem(AUTH_KEY, JSON.stringify({ access }))
}

export function clearStoredTokens(): void {
  localStorage.removeItem(AUTH_KEY)
}
