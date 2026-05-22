import { Bell, Search, User, LogOut, Menu } from 'lucide-react'
import { useAppStore } from '@/stores/appStore'
import { useUserStore } from '@/stores/userStore'

export default function Navbar() {
  const { toggleSidebar } = useAppStore()
  const { user, logout } = useUserStore()

  return (
    <header className="h-[60px] bg-navbar-bg border-b border-navbar-border flex items-center justify-between px-4 sticky top-0 z-30">
      <div className="flex items-center gap-4">
        <button
          onClick={toggleSidebar}
          className="p-2 rounded-lg text-sidebar-text hover:bg-sidebar-hover hover:text-text-primary transition-colors"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
          <input
            type="text"
            placeholder="搜索..."
            className="w-64 h-9 pl-9 pr-4 rounded-lg bg-white/5 border border-white/[0.06] text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-500/50 transition-colors"
          />
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button className="relative p-2 rounded-lg text-sidebar-text hover:bg-sidebar-hover hover:text-text-primary transition-colors">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-danger rounded-full" />
        </button>

        <div className="flex items-center gap-3 pl-3 border-l border-white/[0.06]">
          <div className="w-8 h-8 rounded-full bg-primary-500/20 flex items-center justify-center">
            <User className="w-4 h-4 text-primary-500" />
          </div>
          <div className="hidden md:block">
            <div className="text-sm font-medium text-text-primary">
              {user?.username || 'Admin'}
            </div>
            <div className="text-xs text-text-muted">
              {user?.is_staff ? '管理员' : '用户'}
            </div>
          </div>
          <button
            onClick={logout}
            className="p-2 rounded-lg text-sidebar-text hover:bg-danger/10 hover:text-danger transition-colors"
            title="退出登录"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  )
}
