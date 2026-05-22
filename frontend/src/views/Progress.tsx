import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Bookmark, BookOpen, ChevronRight } from 'lucide-react'
import { fetchProgress } from '@/api/progress'
import { ProgressItem } from '@/types'

export default function Progress() {
  const navigate = useNavigate()
  const { data, isLoading } = useQuery({
    queryKey: ['progress'],
    queryFn: fetchProgress,
  })

  const items = data?.items || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-text-primary">阅读进度</h2>
      </div>

      <div className="bg-card-bg border border-card-border rounded-xl overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-white/[0.06]">
              <th className="px-6 py-4 text-left text-sm font-medium text-text-secondary">书籍</th>
              <th className="px-6 py-4 text-left text-sm font-medium text-text-secondary">作者</th>
              <th className="px-6 py-4 text-left text-sm font-medium text-text-secondary">当前章节</th>
              <th className="px-6 py-4 text-left text-sm font-medium text-text-secondary">进度</th>
              <th className="px-6 py-4 text-right text-sm font-medium text-text-secondary">操作</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr>
                <td colSpan={5} className="text-center py-20 text-text-muted">加载中...</td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={5} className="text-center py-20 text-text-muted">
                  <Bookmark className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p>暂无阅读进度</p>
                </td>
              </tr>
            ) : (
              items.map((item: ProgressItem) => {
                const progress = item.total_chapters > 0
                  ? Math.round(((item.position || 0) / item.total_chapters) * 100)
                  : 0
                return (
                  <tr key={item.id} className="border-b border-white/[0.06] hover:bg-white/[0.02] transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <BookOpen className="w-4 h-4 text-text-muted" />
                        <span className="text-sm font-medium text-text-primary">{item.book_title}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-text-secondary">{item.book_author || '-'}</td>
                    <td className="px-6 py-4 text-sm text-text-secondary">{item.chapter_title || '-'}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-24 h-2 rounded-full bg-white/5 overflow-hidden">
                          <div
                            className="h-full rounded-full bg-primary-500 transition-all"
                            style={{ width: `${progress}%` }}
                          />
                        </div>
                        <span className="text-sm text-text-muted">{progress}%</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() => navigate('/chapters', { state: { bookId: item.book_id } })}
                        className="flex items-center gap-1 ml-auto px-3 py-1.5 rounded-lg bg-primary-500/10 text-primary-500 text-sm hover:bg-primary-500/20 transition-colors"
                      >
                        <ChevronRight className="w-4 h-4" />
                        继续阅读
                      </button>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
