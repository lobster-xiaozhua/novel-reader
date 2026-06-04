import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { usePageTitle } from '@/hooks/usePageTitle'
import { Heart, BookOpen, Clock, Trash2, ChevronRight } from 'lucide-react'
import { fetchFavorites, toggleFavorite } from '@/api/favorites'
import { FavoriteItem } from '@/types'
import { useToast } from '@/components/Toast'
import { Spinner } from '@/components/Loading'
import { useNavigate } from 'react-router-dom'

export default function Favorites() {
  usePageTitle('我的收藏')
  const queryClient = useQueryClient()
  const toast = useToast()
  const navigate = useNavigate()

  const { data, isLoading } = useQuery({
    queryKey: ['favorites'],
    queryFn: fetchFavorites,
  })

  const toggleMutation = useMutation({
    mutationFn: toggleFavorite,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['favorites'] })
      toast.success('已取消收藏')
    },
    onError: () => toast.error('操作失败'),
  })

  const items = data?.items || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl glass-card--compact flex items-center justify-center">
            <Heart className="w-4 h-4 text-accent" />
          </div>
          <h2 className="text-xl font-bold text-text-primary">我的收藏</h2>
        </div>
        <span className="text-sm text-text-muted">共 {items.length} 本收藏</span>
      </div>

      {isLoading ? <Spinner /> : items.length === 0 ? (
        <div className="glass-card p-16 flex flex-col items-center justify-center text-text-muted">
          <Heart className="w-12 h-12 mb-3 opacity-30" />
          <p className="text-lg">暂无收藏</p>
          <p className="text-sm mt-1">在书籍页面点击收藏按钮添加</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 stagger-in">
          {items.map((item: FavoriteItem, idx: number) => (
            <div
              key={item.id}
              className="glass-card glass-card--shimmer"
              style={{ animationDelay: `${idx * 0.04}s` }}
            >
              {/* Shimmer layer */}
              <div className="shimmer-layer" />

              <button
                onClick={() => navigate(`/books/${item.book_id}`)}
                className="w-full p-5 text-left group"
              >
                <div className="flex items-start gap-4">
                  <div
                    className="w-14 h-14 rounded-xl flex items-center justify-center flex-shrink-0 group-hover:scale-105 transition-transform"
                    style={{ background: 'linear-gradient(135deg, #667eea, #764ba2)' }}
                  >
                    <BookOpen className="w-7 h-7 text-white/80" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-text-primary truncate group-hover:text-accent transition-colors">{item.title}</h3>
                    <p className="text-sm text-text-secondary mt-1">{item.author}</p>
                    <div className="flex items-center gap-2 mt-2">
                      <span className="px-2 py-0.5 rounded-md bg-accent/10 text-accent text-xs">{item.category}</span>
                      <span className="text-xs text-text-muted">{item.total_chapters} 章</span>
                    </div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-text-muted opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                </div>
              </button>

              <div className="flex items-center justify-between px-5 pb-4 pt-3 border-t border-border/50">
                <span className="text-xs text-text-muted flex items-center gap-1">
                  <Clock className="w-3 h-3" />{new Date(item.created_at).toLocaleDateString('zh-CN')}
                </span>
                {/* Danger button: confirm before remove (pessimistic update) */}
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    if (window.confirm(`确定取消收藏《${item.title}》？`)) {
                      toggleMutation.mutate(item.book_id)
                    }
                  }}
                  disabled={toggleMutation.isPending}
                  className="btn btn--danger btn--sm"
                >
                  <Trash2 className="w-3.5 h-3.5" />取消收藏
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
