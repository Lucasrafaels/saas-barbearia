import axios, { type InternalAxiosRequestConfig } from 'axios'
import { clearStoredTokens, getStoredTokens, storeTokens } from '../utils/storage'
import type { AuthTokens } from '../types'

export const API_URL = (import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000/api/v1').replace(/\/$/, '')

interface RetriableRequest extends InternalAxiosRequestConfig {
  _retry?: boolean
}

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const access = getStoredTokens()?.access
  if (access) config.headers.Authorization = `Bearer ${access}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const request = error.config as RetriableRequest | undefined
    const url = request?.url ?? ''
    const cannotRefresh = url.includes('/auth/login/') || url.includes('/auth/refresh/')

    if (error.response?.status !== 401 || !request || request._retry || cannotRefresh) {
      return Promise.reject(error)
    }

    const currentTokens = getStoredTokens()
    if (!currentTokens?.refresh) {
      clearStoredTokens()
      window.dispatchEvent(new Event('auth:expired'))
      return Promise.reject(error)
    }

    request._retry = true
    try {
      const { data } = await axios.post<Partial<AuthTokens>>(`${API_URL}/auth/refresh/`, {
        refresh: currentTokens.refresh,
      })
      const tokens: AuthTokens = {
        access: data.access ?? currentTokens.access,
        refresh: data.refresh ?? currentTokens.refresh,
      }
      storeTokens(tokens)
      request.headers.Authorization = `Bearer ${tokens.access}`
      return api(request)
    } catch (refreshError) {
      clearStoredTokens()
      window.dispatchEvent(new Event('auth:expired'))
      return Promise.reject(refreshError)
    }
  },
)

export default api
