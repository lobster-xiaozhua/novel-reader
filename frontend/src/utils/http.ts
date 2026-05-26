const AUTH_EXPIRED_EVENT = 'auth:expired'
const ACCESS_TOKEN_KEY = 'access_token'
const BASE_URL = '/api/v1'
const TIMEOUT = 30000

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

export class HttpError extends Error {
  readonly status: number
  constructor(status: number, message: string) {
    super(message)
    this.name = 'HttpError'
    this.status = status
  }
}

interface RequestOptions {
  params?: Record<string, unknown>
  signal?: AbortSignal
  headers?: Record<string, string>
  _retried?: boolean
}

function buildURL(url: string, params?: Record<string, unknown>): string {
  const full = url.startsWith('http') ? url : `${BASE_URL}${url}`
  if (!params) return full
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null) sp.append(k, String(v))
  }
  const qs = sp.toString()
  return qs ? `${full}?${qs}` : full
}

async function extractErrorMessage(response: Response): Promise<string> {
  try {
    const data = await response.json()
    return data.detail || data.message || data.error || `请求失败 (${response.status})`
  } catch {
    return `请求失败 (${response.status})`
  }
}

let isRefreshing = false
let refreshSubscribers: Array<(token: string) => void> = []

function onRefreshed(token: string) {
  refreshSubscribers.forEach((cb) => cb(token))
  refreshSubscribers = []
}

function addRefreshSubscriber(cb: (token: string) => void) {
  refreshSubscribers.push(cb)
}

async function refreshAccessToken(): Promise<string> {
  const res = await fetch(`${BASE_URL}/auth/refresh/`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
    },
  })
  if (!res.ok) throw new HttpError(res.status, await extractErrorMessage(res))
  const data = await res.json()
  return data?.access_token
}

async function handleRefresh<T>(
  method: string,
  url: string,
  data: unknown,
  options: RequestOptions | undefined,
): Promise<T> {
  if (url === '/auth/refresh/') {
    clearTokens()
    emitAuthExpired()
    throw new HttpError(401, '认证已过期')
  }

  if (isRefreshing) {
    return new Promise<T>((resolve, reject) => {
      addRefreshSubscriber(() => {
        request<T>(method, url, data, { ...options, _retried: true }).then(resolve).catch(reject)
      })
    })
  }

  isRefreshing = true

  try {
    const newToken = await refreshAccessToken()
    setTokens(newToken)
    onRefreshed(newToken)
    return request<T>(method, url, data, { ...options, _retried: true })
  } catch (err) {
    clearTokens()
    emitAuthExpired()
    refreshSubscribers = []
    throw err instanceof HttpError ? err : new HttpError(401, '认证已过期')
  } finally {
    isRefreshing = false
  }
}

async function request<T>(
  method: string,
  url: string,
  data?: unknown,
  options?: RequestOptions,
): Promise<T> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUT)

  const signal = options?.signal
    ? AbortSignal.any([options.signal, controller.signal])
    : controller.signal

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
    ...options?.headers,
  }

  const token = getAccessToken()
  if (token) headers.Authorization = `Bearer ${token}`

  const fullURL = buildURL(url, options?.params)

  let body: BodyInit | undefined
  if (data !== undefined && data !== null) {
    if (data instanceof FormData) {
      delete headers['Content-Type']
      body = data
    } else {
      body = JSON.stringify(data)
    }
  }

  try {
    const response = await fetch(fullURL, { method, headers, body, signal, credentials: 'include' })

    if (response.status === 401 && !options?._retried) {
      return handleRefresh<T>(method, url, data, options)
    }

    if (!response.ok) {
      throw new HttpError(response.status, await extractErrorMessage(response))
    }

    if (response.status === 204 || response.headers.get('content-length') === '0') {
      return undefined as T
    }

    return response.json()
  } finally {
    clearTimeout(timeoutId)
  }
}

export async function get<T>(url: string, options?: RequestOptions): Promise<T> {
  return request<T>('GET', url, undefined, options)
}

export async function post<T>(url: string, data?: unknown, options?: RequestOptions): Promise<T> {
  return request<T>('POST', url, data, options)
}

export async function put<T>(url: string, data?: unknown, options?: RequestOptions): Promise<T> {
  return request<T>('PUT', url, data, options)
}

export async function del<T>(url: string, options?: RequestOptions): Promise<T> {
  return request<T>('DELETE', url, undefined, options)
}

export async function upload<T>(url: string, formData: FormData, options?: RequestOptions): Promise<T> {
  return request<T>('POST', url, formData, options)
}
