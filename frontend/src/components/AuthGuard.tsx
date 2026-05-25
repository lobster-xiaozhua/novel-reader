import { useEffect, useRef, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useUserStore } from '@/stores/userStore'
import { get, getAccessToken, setTokens } from '@/utils/http'
import axios from 'axios'

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate()
  const location = useLocation()
  const { isLoggedIn, login } = useUserStore()
  const [authChecked, setAuthChecked] = useState(isLoggedIn)
  const hasFetchedRef = useRef(false)

  useEffect(() => {
    if (isLoggedIn) return
    if (hasFetchedRef.current) return
    hasFetchedRef.current = true

    const controller = new AbortController()

    const tryAuth = async () => {
      try {
        if (!getAccessToken()) {
          try {
            const refreshRes = await axios.post('/api/v1/auth/refresh/', null, {
              withCredentials: true,
              signal: controller.signal,
            })
            const newToken: string = refreshRes.data?.access_token
            if (newToken) setTokens(newToken)
          } catch {
            navigate('/login', { state: { from: location.pathname }, replace: true })
            return
          }
        }

        const res = await get<{ success: boolean; user?: { id: number; username: string; email: string; is_staff: boolean } }>('/auth/me/', { signal: controller.signal } as Record<string, unknown>)
        if (res.success && res.user) {
          login(res.user)
          setAuthChecked(true)
        } else {
          navigate('/login', { state: { from: location.pathname }, replace: true })
        }
      } catch {
        navigate('/login', { state: { from: location.pathname }, replace: true })
      }
    }

    tryAuth()
    return () => controller.abort()
  }, [isLoggedIn, navigate, login, location.pathname])

  if (!authChecked) {
    return (
      <div className="h-screen flex items-center justify-center bg-content-bg">
        <div className="w-8 h-8 border-2 border-primary-500 border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return <>{children}</>
}
