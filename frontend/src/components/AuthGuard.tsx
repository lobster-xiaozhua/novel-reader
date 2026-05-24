import { useEffect, useRef, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useUserStore } from '@/stores/userStore'
import { get } from '@/utils/http'

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
    get<{ success: boolean; user?: { id: number; username: string; email: string; is_staff: boolean } }>('/auth/me/', { signal: controller.signal } as Record<string, unknown>)
      .then((res) => {
        if (res.success && res.user) {
          login(res.user)
        } else {
          navigate('/login', { state: { from: location.pathname }, replace: true })
          return
        }
        setAuthChecked(true)
      })
      .catch(() => {
        navigate('/login', { state: { from: location.pathname }, replace: true })
      })
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
