import { useCallback } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  BookOpen,
  FileText,
  Tag,
  Users,
  Bookmark,
  BarChart3,
  Heart,
  Bug,
  Menu,
  ChevronLeft,
} from 'lucide-react'
import { useAppStore } from '@/stores/appStore'
import { MenuItem } from '@/types'

const menuItems: MenuItem[] = [
  { title: 'Dashboard', icon: 'LayoutDashboard', path: '/dashboard' },
  { title: '书籍', icon: 'BookOpen', path: '/books' },
  { title: '章节', icon: 'FileText', path: '/chapters' },
  { title: '标签', icon: 'Tag', path: '/tags' },
  { title: '用户', icon: 'Users', path: '/users' },
  { title: '阅读进度', icon: 'Bookmark', path: '/progress' },
  { title: '阅读统计', icon: 'BarChart3', path: '/stats' },
  { title: '收藏', icon: 'Heart', path: '/favorites' },
  { title: '爬虫任务', icon: 'Bug', path: '/crawler' },
]

const iconMap: Record<string, React.ElementType> = {
  LayoutDashboard,
  BookOpen,
  FileText,
  Tag,
  Users,
  Bookmark,
  BarChart3,
  Heart,
  Bug,
}

export default function Sidebar() {
  const { sidebar, toggleSidebar, device } = useAppStore()
  const location = useLocation()
  const isCollapsed = !sidebar.opened

  const handleOverlayClick = useCallback(() => {
    if (device === 'mobile') {
      toggleSidebar()
    }
  }, [device, toggleSidebar])

  return (
    <>
      {/* Mobile overlay */}
      {device === 'mobile' && sidebar.opened && (
        <div
          className="fixed inset-0 bg-black/50 z-40"
          onClick={handleOverlayClick}
        />
      )}

      <aside
        className={`fixed left-0 top-0 h-full bg-sidebar-bg border-r border-white/[0.06] z-50 layout-transition flex flex-col
          ${isCollapsed ? 'w-16' : 'w-[220px]'}
          ${device === 'mobile' && !sidebar.opened ? '-translate-x-full' : ''}
        `}
      >
        {/* Logo */}
        <div className="h-[60px] flex items-center px-4 border-b border-white/[0.06]">
          <BookOpen className="w-7 h-7 text-primary-500 flex-shrink-0" />
          {!isCollapsed && (
            <span className="ml-3 text-lg font-bold text-text-primary truncate">
              小说阅读器
            </span>
          )}
        </div>

        {/* Toggle button */}
        <button
          onClick={toggleSidebar}
          className={`absolute -right-3 top-[68px] w-6 h-6 bg-primary-500 rounded-full flex items-center justify-center shadow-lg hover:bg-primary-600 transition-colors
            ${isCollapsed ? 'rotate-180' : ''}
          `}
        >
          <ChevronLeft className="w-4 h-4 text-white" />
        </button>

        {/* Menu */}
        <nav className="flex-1 py-4 overflow-y-auto">
          {menuItems.map((item) => {
            const Icon = iconMap[item.icon]
            const isActive = location.pathname === item.path

            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={`flex items-center px-4 py-3 mx-2 rounded-lg transition-colors relative group
                  ${isActive
                    ? 'bg-primary-500/10 text-primary-500'
                    : 'text-sidebar-text hover:bg-sidebar-hover hover:text-text-primary'
                  }
                `}
                onClick={() => device === 'mobile' && toggleSidebar()}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                {!isCollapsed && (
                  <span className="ml-3 text-sm font-medium truncate">{item.title}</span>
                )}
                {isActive && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-primary-500 rounded-r-full" />
                )}
              </NavLink>
            )
          })}
        </nav>

        {/* Bottom */}
        <div className="p-4 border-t border-white/[0.06]">
          <button
            onClick={toggleSidebar}
            className="flex items-center justify-center w-full py-2 rounded-lg text-sidebar-text hover:bg-sidebar-hover hover:text-text-primary transition-colors"
          >
            <Menu className="w-5 h-5" />
            {!isCollapsed && <span className="ml-2 text-sm">收起菜单</span>}
          </button>
        </div>
      </aside>
    </>
  )
}
