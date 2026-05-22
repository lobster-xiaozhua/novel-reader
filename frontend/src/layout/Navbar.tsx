import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Bell, User, LogOut, Menu } from 'lucide-react'
import { useUserStore } from '@/stores/userStore'
import { useAppStore } from '@/stores/appStore'

export default function Navbar() {
  const [searchQuery, setSearchQuery] = useState('')
  const navigate = useNavigate()
  const { user, logout } = useUserStore()
  const { toggleSidebar } = useAppStore()

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    if (searchQuery.trim()) {
      navigate(`/books?search=${encodeURIComponent(searchQuery.trim())}`)
      setSearchQuery('')
    }
  }

  return (
    <header className="h-16 bg-card-bg/80 backdrop-blur-xl border-b border-white/[0.06] flex items-center justify-between px-6 sticky top-0 z-30">
      <div className="flex items-center gap-4">
        <button
          onClick={toggleSidebar}
          className="p-2 rounded-lg hover:bg-white/5 text-text-secondary hover:text-text-primary transition-colors lg:hidden"
        >
          <Menu className="w-5 h-5" />
        </button>
        <form onSubmit={handleSearch} className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
          <input
            type="text"
            placeholder="搜索书籍、作者..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-64 lg:w-80 h-9 pl-9 pr-4 rounded-lg bg-white/5 border border-white/[0.06] text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-500/50 transition-colors"
          />
        </form>
      </div>

      <div className="flex items-center gap-3">
        <button className="relative p-2 rounded-lg hover:bg-white/5 text-text-secondary hover:text-text-primary transition-colors">
          <Bell className="w-5 h-5" />
        </button>

        <div className="w-px h-6 bg-white/[0.06]" />

        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-primary-500/20 flex items-center justify-center">
            <User className="w-4 h-4 text-primary-500" />
          </div>
          <div className="hidden sm:block">
            <div className="text-sm font-medium text-text-primary">{user?.username || '访客'}</div>
            <div className="text-xs text-text-muted">{user?.is_staff ? '管理员' : '用户'}</div>
          </div>
          {user && (
            <button
              onClick={() => {
                logout()
                navigate('/login')
              }}
              className="p-2 rounded-lg hover:bg-white/5 text-text-secondary hover:text-danger transition-colors"
              title="退出登录"
            >
              <LogOut className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </header>
  )
}
