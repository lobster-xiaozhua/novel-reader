'use client';

const BASE_URL = '/api/v2';

class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(message: string, status: number, data?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

let _isRefreshing = false;

async function tryRefreshToken(): Promise<boolean> {
  if (_isRefreshing) return false;
  _isRefreshing = true;
  try {
    const res = await fetch(`${BASE_URL}/auth/refresh`, {
      method: 'POST',
      credentials: 'Include',
    });
    return res.ok;
  } catch {
    return false;
  } finally {
    _isRefreshing = false;
  }
}

async function request<T = unknown>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body != null ? JSON.stringify(body) : undefined,
    credentials: 'include',
  });

  if (res.status === 401) {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      const retryRes = await fetch(`${BASE_URL}${path}`, {
        method,
        headers,
        body: body != null ? JSON.stringify(body) : undefined,
        credentials: 'include',
      });
      if (retryRes.ok) {
        return retryRes.json();
      }
    }
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
    throw new ApiError('未授权，请重新登录', 401);
  }

  if (!res.ok) {
    let data: unknown;
    try { data = await res.json(); } catch { data = null; }
    throw new ApiError(
      (data as { error?: string })?.error || `请求失败 (${res.status})`,
      res.status,
      data,
    );
  }

  return res.json();
}

export const api = {
  get<T = unknown>(path: string): Promise<T> {
    return request<T>('GET', path);
  },

  post<T = unknown>(path: string, body?: unknown): Promise<T> {
    return request<T>('POST', path, body);
  },

  put<T = unknown>(path: string, body?: unknown): Promise<T> {
    return request<T>('PUT', path, body);
  },

  delete<T = unknown>(path: string): Promise<T> {
    return request<T>('DELETE', path);
  },
};

export { ApiError, BASE_URL };
export default api;
