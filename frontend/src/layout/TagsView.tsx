import { useEffect } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { X, RotateCcw } from 'lucide-react'
import { useTagsStore } from '@/stores/tagsStore'

const routeTitleMap: Record<string, string> = {
  '/admin-dashboard': 'Dashboard',
  '/admin-dashboard/books': '书籍',
  '/admin-dashboard/chapters': '章节',
  '/admin-dashboard/tags': '标签',
  '/admin-dashboard/users': '用户',
  '/admin-dashboard/progress': '阅读进度',
  '/admin-dashboard/stats': '阅读统计',
  '/admin-dashboard/favorites': '收藏',
  '/admin-dashboard/crawler': '爬虫任务',
}

export default function TagsView() {
  const location = useLocation()
  const navigate = useNavigate()
  const { visitedViews, addView, removeView, removeAll } = useTagsStore()

  useEffect(() => {
    const path = location.pathname
    const title = routeTitleMap[path] || '页面'
    addView({ path, title, name: path.replace(/\//g, '') || 'dashboard' })
  }, [location.pathname, addView])

  return (
    <div className="h-[44px] bg-navbar-bg border-b border-navbar-border flex items-center px-2 gap-1 overflow-x-auto">
      {visitedViews.map((view) => {
        const isActive = location.pathname === view.path

        return (
          <div
            key={view.path}
            onClick={() => navigate(view.path)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm cursor-pointer whitespace-nowrap transition-colors
              ${isActive
                ? 'bg-primary-500/10 text-primary-500 border border-primary-500/20'
                : 'text-sidebar-text hover:bg-white/5 border border-transparent'
              }
            `}
          >
            <span>{view.title}</span>
            {view.path !== '/admin-dashboard' && (
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  removeView(view)
                  if (isActive) {
                    const last = visitedViews.filter((v) => v.path !== view.path).pop()
                    navigate(last?.path || '/admin-dashboard')
                  }
                }}
                className="p-0.5 rounded hover:bg-white/10 transition-colors"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>
        )
      })}

      {visitedViews.length > 1 && (
        <button
          onClick={removeAll}
          className="ml-auto p-1.5 rounded-md text-sidebar-text hover:bg-white/5 transition-colors"
          title="关闭其他"
        >
          <RotateCcw className="w-4 h-4" />
        </button>
      )}
    </div>
  )
}
