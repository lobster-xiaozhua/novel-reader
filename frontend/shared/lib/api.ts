'use client';

const BASE_URL = '/api/v2';

const TOKEN_KEY = 'access_token';

function getCookie(name: string): string | null {
  if (typeof window === 'undefined') return null;
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop()?.split(';').shift() || null;
  return null;
}

function setCookie(name: string, value: string, days: number = 1): void {
  if (typeof window === 'undefined') return;
  const date = new Date();
  date.setTime(date.getTime() + days * 24 * 60 * 60 * 1000);
  const expires = `expires=${date.toUTCString()}`;
  document.cookie = `${name}=${value};${expires};path=/;SameSite=Lax`;
}

function deleteCookie(name: string): void {
  if (typeof window === 'undefined') return;
  document.cookie = `${name}=;path=/;expires=Thu, 01 Jan 1970 00:00:01 GMT`;
}

function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  // 优先从 localStorage 读取，降级到 cookie
  return localStorage.getItem(TOKEN_KEY) || getCookie(TOKEN_KEY);
}

function setToken(token: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(TOKEN_KEY, token);
  setCookie(TOKEN_KEY, token, 1);
}

function clearToken(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
  deleteCookie(TOKEN_KEY);
}

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

async function request<T = unknown>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  const token = getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body != null ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401) {
    clearToken();
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
  setToken,
  clearToken,
  getToken,

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