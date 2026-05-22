import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Heart, BookOpen, Clock, Trash2 } from 'lucide-react'
import { fetchFavorites, toggleFavorite, type FavoriteItem } from '@/api/favorites'

export default function Favorites() {
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['favorites'],
    queryFn: fetchFavorites,
  })

  const toggleMutation = useMutation({
    mutationFn: toggleFavorite,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['favorites'] }),
  })

  const items = data?.items || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-text-primary">我的收藏</h2>
        <div className="text-sm text-text-muted">
          共 {items.length} 本收藏
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-20 text-text-muted">加载中...</div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-text-muted">
          <Heart className="w-12 h-12 mb-3 opacity-30" />
          <p>暂无收藏</p>
          <p className="text-sm mt-1">在书籍页面点击收藏按钮添加</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {items.map((item: FavoriteItem) => (
            <div
              key={item.id}
              className="bg-card-bg border border-card-border rounded-xl p-5 card-hover"
            >
              <div className="flex items-start gap-4">
                <div className="w-14 h-14 rounded-xl bg-primary-500/10 flex items-center justify-center flex-shrink-0">
                  <BookOpen className="w-7 h-7 text-primary-500" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-text-primary truncate">{item.title}</h3>
                  <p className="text-sm text-text-secondary mt-1">{item.author}</p>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="px-2 py-0.5 rounded-md bg-primary-500/10 text-primary-500 text-xs">
                      {item.category}
                    </span>
                    <span className="text-xs text-text-muted">{item.total_chapters} 章</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between mt-4 pt-3 border-t border-white/[0.06]">
                <span className="text-xs text-text-muted flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {new Date(item.created_at).toLocaleDateString('zh-CN')}
                </span>
                <button
                  onClick={() => toggleMutation.mutate(item.book_id)}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-danger/10 text-danger text-sm hover:bg-danger/20 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                  取消收藏
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
