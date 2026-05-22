import { useQuery } from '@tanstack/react-query'
import { Bookmark, BookOpen, Clock, ChevronRight } from 'lucide-react'
import { fetchProgress, type ProgressItem } from '@/api/progress'

export default function Progress() {
  const { data, isLoading } = useQuery({
    queryKey: ['progress'],
    queryFn: fetchProgress,
  })

  const items = data?.items || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-text-primary">阅读进度</h2>
        <div className="text-sm text-text-muted">
          共 {items.length} 本书在阅读中
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-20 text-text-muted">加载中...</div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-text-muted">
          <Bookmark className="w-12 h-12 mb-3 opacity-30" />
          <p>暂无阅读进度</p>
          <p className="text-sm mt-1">开始阅读书籍后将在此显示</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((item: ProgressItem) => {
            const progress = item.total_chapters > 0
              ? Math.round(((item.chapter_id ? item.position : 0) / item.total_chapters) * 100)
              : 0

            return (
              <div
                key={item.id}
                className="bg-card-bg border border-card-border rounded-xl p-5 card-hover"
              >
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-xl bg-primary-500/10 flex items-center justify-center flex-shrink-0">
                    <BookOpen className="w-6 h-6 text-primary-500" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-text-primary truncate">{item.book_title}</h3>
                    <p className="text-sm text-text-secondary mt-0.5">{item.book_author}</p>
                  </div>
                </div>

                <div className="mt-4">
                  <div className="flex items-center justify-between text-sm mb-2">
                    <span className="text-text-secondary flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5" />
                      {item.chapter_title || '尚未开始'}
                    </span>
                    <span className="text-primary-500 font-medium">{progress}%</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-white/5 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-primary-500 transition-all"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                  <div className="flex items-center justify-between mt-2 text-xs text-text-muted">
                    <span>共 {item.total_chapters} 章</span>
                    <span>更新于 {new Date(item.updated_at).toLocaleDateString('zh-CN')}</span>
                  </div>
                </div>

                <button className="w-full mt-4 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-primary-500/10 text-primary-500 text-sm font-medium hover:bg-primary-500/20 transition-colors">
                  继续阅读
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
