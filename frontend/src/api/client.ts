import axios, { type InternalAxiosRequestConfig } from 'axios'
import { clearStoredTokens, getStoredAccessToken, storeAccessToken } from '../utils/storage'

export const API_URL = (import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000/api/v1').replace(/\/$/, '')

interface RetriableRequest extends InternalAxiosRequestConfig {
  _retry?: boolean
}

const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
})

api.interceptors.request.use((config) => {
  const access = getStoredAccessToken()
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

    request._retry = true
    try {
      // Backend reads refresh token from HttpOnly cookie, not request body
      const { data } = await axios.post<{ access: string }>(`${API_URL}/auth/refresh/`, {}, { withCredentials: true })
      storeAccessToken(data.access)
      request.headers.Authorization = `Bearer ${data.access}`
      return api(request)
    } catch (refreshError) {
      // Só encerra a sessão quando o servidor recusa a renovação;
      // uma falha de rede não deve deslogar o usuário.
      if (axios.isAxiosError(refreshError) && refreshError.response) {
        clearStoredTokens()
        window.dispatchEvent(new Event('auth:expired'))
      }
      return Promise.reject(refreshError)
    }
  },
)

export default api
