const AUTH_EXPIRED_EVENT = 'auth:expired'
const BASE_URL = '/api/v1'
const TIMEOUT = 30000

// Token 通过 HttpOnly Cookie 传输，前端无需手动管理
export function getAccessToken(): string | null {
  return null
}

export function setTokens(_accessToken: string, _refreshToken?: string): void {
  // Token 通过 HttpOnly Cookie 设置，前端无需存储
}

export function clearTokens(): void {
  // Cookie 由后端清除，前端无需操作
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
  readonly detail?: string
  readonly code?: string

  constructor(status: number, message: string, detail?: string, code?: string) {
    super(message)
    this.name = 'HttpError'
    this.status = status
    this.detail = detail
    this.code = code
  }

  get userMessage(): string {
    switch (this.status) {
      case 400: return '请求参数错误：' + this.message
      case 401: return '身份验证失败，请重新登录'
      case 403: return '权限不足，您没有执行此操作的权限'
      case 404: return '请求的资源不存在'
      case 409: return '数据冲突：' + this.message
      case 422: return '数据验证失败：' + this.message
      case 429: return '请求过于频繁，请稍后重试'
      case 500: return '服务器内部错误，请稍后重试或联系管理员'
      case 502: return '网关错误，服务器暂时不可用'
      case 503: return '服务暂时不可用，请稍后重试'
      case 504: return '请求超时，服务器响应太慢'
      default:
        if (this.status >= 500) return `服务器错误 (${this.status})：${this.message}`
        return this.message
    }
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
  if (!res.ok) {
    clearTokens()
    emitAuthExpired()
    throw new HttpError(res.status, await extractErrorMessage(res))
  }
  const data = await res.json()
  if (data?.access_token) {
    setTokens(data.access_token)
  }
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
    ? (typeof AbortSignal !== 'undefined' && 'any' in AbortSignal
        ? (AbortSignal as any).any([options.signal, controller.signal])
        : options.signal)
    : controller.signal

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
    ...options?.headers,
  }

  // Token 通过 HttpOnly Cookie 自动携带，无需手动添加 Authorization header

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

export async function del<T>(url: string, data?: unknown, options?: RequestOptions): Promise<T> {
  return request<T>('DELETE', url, data, options)
}

export async function upload<T>(url: string, formData: FormData, options?: RequestOptions): Promise<T> {
  return request<T>('POST', url, formData, options)
}
