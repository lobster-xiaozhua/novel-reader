import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, InternalAxiosRequestConfig } from 'axios'

const AUTH_EXPIRED_EVENT = 'auth:expired'
const ACCESS_TOKEN_KEY = 'access_token'

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function setTokens(accessToken: string, _refreshToken?: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
}

export function clearTokens(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
}

export function onAuthExpired(callback: () => void): () => void {
  const handler = () => callback()
  window.addEventListener(AUTH_EXPIRED_EVENT, handler)
  return () => window.removeEventListener(AUTH_EXPIRED_EVENT, handler)
}

function emitAuthExpired() {
  window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT))
}

const http: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
  },
})

http.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getAccessToken()
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let isRefreshing = false
let refreshSubscribers: Array<(token: string) => void> = []

function onRefreshed(token: string) {
  refreshSubscribers.forEach((cb) => cb(token))
  refreshSubscribers = []
}

function addRefreshSubscriber(cb: (token: string) => void) {
  refreshSubscribers.push(cb)
}

http.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (originalRequest.url === '/auth/refresh/') {
        clearTokens()
        emitAuthExpired()
        return Promise.reject(error)
      }

      if (isRefreshing) {
        return new Promise((resolve) => {
          addRefreshSubscriber((newToken: string) => {
            originalRequest.headers.Authorization = `Bearer ${newToken}`
            resolve(http(originalRequest))
          })
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const res = await axios.post('/api/v1/auth/refresh/', null, { withCredentials: true })
        const newToken: string = res.data?.access_token
        if (newToken) {
          setTokens(newToken)
          onRefreshed(newToken)
          originalRequest.headers.Authorization = `Bearer ${newToken}`
          return http(originalRequest)
        }
        clearTokens()
        emitAuthExpired()
        return Promise.reject(error)
      } catch {
        clearTokens()
        emitAuthExpired()
        return Promise.reject(error)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  }
)

export async function get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const res = await http.get(url, config)
  return res.data
}

export async function post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  const res = await http.post(url, data, config)
  return res.data
}

export async function put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
  const res = await http.put(url, data, config)
  return res.data
}

export async function del<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const res = await http.delete(url, config)
  return res.data
}

export async function upload<T>(url: string, formData: FormData, config?: AxiosRequestConfig): Promise<T> {
  const res = await http.post(url, formData, {
    ...config,
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export default http
