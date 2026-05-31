import { StrictMode, useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, useNavigate } from 'react-router-dom'
import App from './App'
import { ToastProvider, useToast } from './components/Toast'
import { useUserStore } from './stores/userStore'
import { onAuthExpired, clearTokens, HttpError } from './utils/http'
import './styles/index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: 1,
    },
  },
})

function GlobalErrorHandler({ children }: { children: React.ReactNode }) {
  const toast = useToast()

  useEffect(() => {
    const handleError = (event: ErrorEvent) => {
      const error = event.error
      console.error('[全局错误]', error)

      if (error instanceof HttpError) {
        toast.error(error.userMessage)
        event.preventDefault()
        return
      }

      toast.error(`运行时错误: ${error?.message || '未知错误'}`)
      event.preventDefault()
    }

    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      const reason = event.reason
      console.error('[未捕获的Promise拒绝]', reason)

      if (reason instanceof HttpError) {
        toast.error(reason.userMessage)
        event.preventDefault()
        return
      }

      if (reason instanceof Error) {
        toast.error(`异步错误: ${reason.message}`)
      } else {
        toast.error('发生未知错误')
      }
      event.preventDefault()
    }

    window.addEventListener('error', handleError)
    window.addEventListener('unhandledrejection', handleUnhandledRejection)

    return () => {
      window.removeEventListener('error', handleError)
      window.removeEventListener('unhandledrejection', handleUnhandledRejection)
    }
  }, [toast])

  return <>{children}</>
}

function AuthExpiredHandler({ children }: { children: React.ReactNode }) {
  const logout = useUserStore((s) => s.logout)
  const navigate = useNavigate()

  useEffect(() => {
    return onAuthExpired(() => {
      const { isLoggedIn } = useUserStore.getState()
      if (isLoggedIn) {
        logout()
      }
      clearTokens()
      navigate('/login', { replace: true })
    })
  }, [logout, navigate])

  return <>{children}</>
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <ToastProvider>
          <GlobalErrorHandler>
            <AuthExpiredHandler>
              <App />
            </AuthExpiredHandler>
          </GlobalErrorHandler>
        </ToastProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
