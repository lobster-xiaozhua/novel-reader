import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { BookOpen, Eye, EyeOff } from 'lucide-react'
import { post } from '@/utils/http'
import { useUserStore } from '@/stores/userStore'

interface AuthResponse {
  success: boolean
  user?: { id: number; username: string; email: string; is_staff: boolean }
  error?: string
  access_token?: string
  refresh_token?: string
}

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login: loginUser } = useUserStore()
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [email, setEmail] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const endpoint = mode === 'login' ? '/auth/login/' : '/auth/register/'
      const payload: Record<string, string> = { username, password }
      if (mode === 'register' && email) payload.email = email

      const res = await post<AuthResponse>(endpoint, payload)

      if (res.success && res.user) {
        loginUser(res.user, res.access_token, res.refresh_token)
        const from = (location.state as { from?: string })?.from || '/dashboard'
        navigate(from, { replace: true })
      } else {
        setError(res.error || '操作失败')
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '网络错误'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-content-bg">
      <div className="w-full max-w-md p-8 bg-card-bg border border-card-border rounded-2xl shadow-xl">
        <div className="flex flex-col items-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-primary-500/10 flex items-center justify-center mb-4">
            <BookOpen className="w-8 h-8 text-primary-500" />
          </div>
          <h1 className="text-2xl font-bold text-text-primary">小说阅读器</h1>
          <p className="text-sm text-text-muted mt-1">{mode === 'login' ? '登录您的账户' : '创建新账户'}</p>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-danger/10 text-danger text-sm">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="login-username" className="block text-sm font-medium text-text-secondary mb-1.5">用户名</label>
            <input
              id="login-username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoComplete="username"
              className="w-full h-11 px-4 rounded-lg bg-content-bg border border-card-border text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-500/50 transition-colors"
              placeholder="输入用户名"
            />
          </div>

          {mode === 'register' && (
            <div>
              <label htmlFor="login-email" className="block text-sm font-medium text-text-secondary mb-1.5">邮箱</label>
              <input
                id="login-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                className="w-full h-11 px-4 rounded-lg bg-content-bg border border-card-border text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-500/50 transition-colors"
                placeholder="输入邮箱（可选）"
              />
            </div>
          )}

          <div>
            <label htmlFor="login-password" className="block text-sm font-medium text-text-secondary mb-1.5">密码</label>
            <div className="relative">
              <input
                id="login-password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                className="w-full h-11 px-4 pr-11 rounded-lg bg-content-bg border border-card-border text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-500/50 transition-colors"
                placeholder="输入密码"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full h-11 rounded-lg bg-primary-500 text-white font-medium hover:bg-primary-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? '处理中...' : mode === 'login' ? '登录' : '注册'}
          </button>
        </form>

        <div className="mt-6 text-center">
          <button
            onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}
            className="text-sm text-primary-500 hover:text-primary-400 transition-colors"
          >
            {mode === 'login' ? '没有账户？立即注册' : '已有账户？立即登录'}
          </button>
        </div>
      </div>
    </div>
  )
}
