import axios, { AxiosError, AxiosInstance, AxiosRequestConfig } from 'axios'

const http: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
    'X-Requested-With': 'XMLHttpRequest',
  },
})

http.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      const store = (window as any).__userStore
      if (store?.getState?.()?.isLoggedIn) {
        store.getState().logout()
      }
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
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
