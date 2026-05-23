import { StrictMode, useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, useNavigate } from 'react-router-dom'
import App from './App'
import { ToastProvider } from './components/Toast'
import { useUserStore } from './stores/userStore'
import { onAuthExpired } from './utils/http'
import './styles/index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      retry: 1,
    },
  },
})

function AuthExpiredHandler({ children }: { children: React.ReactNode }) {
  const logout = useUserStore((s) => s.logout)
  const navigate = useNavigate()

  useEffect(() => {
    return onAuthExpired(() => {
      const { isLoggedIn } = useUserStore.getState()
      if (isLoggedIn) {
        logout()
      }
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
          <AuthExpiredHandler>
            <App />
          </AuthExpiredHandler>
        </ToastProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
