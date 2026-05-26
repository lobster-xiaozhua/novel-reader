import { useEffect, useRef, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useUserStore } from '@/stores/userStore'
import { get, post, getAccessToken, setTokens } from '@/utils/http'

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
    let cancelled = false

    const tryAuth = async () => {
      try {
        if (!getAccessToken()) {
          try {
            const refreshRes = await post<{ access_token?: string }>('/auth/refresh/', null, {
              signal: controller.signal,
            })
            if (refreshRes.access_token) setTokens(refreshRes.access_token)
          } catch {
            if (!cancelled) navigate('/login', { state: { from: location.pathname }, replace: true })
            return
          }
        }

        const res = await get<{
          success: boolean
          user?: { id: number; username: string; email: string; is_staff: boolean }
        }>('/auth/me/', { signal: controller.signal })

        if (cancelled) return

        if (res.success && res.user) {
          login(res.user)
          setAuthChecked(true)
        } else {
          navigate('/login', { state: { from: location.pathname }, replace: true })
        }
      } catch {
        if (!cancelled) navigate('/login', { state: { from: location.pathname }, replace: true })
      }
    }

    tryAuth()

    return () => {
      cancelled = true
      controller.abort()
    }
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
