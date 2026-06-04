import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { usePageTitle } from '@/hooks/usePageTitle'
import { BookOpen, TrendingUp, Flame, Sparkles, AlertCircle } from 'lucide-react'
import { fetchRankings } from '@/api/books'
import { Book } from '@/types'
import { Spinner } from '@/components/Loading'

const TABS = [
  { key: 'hot_today', label: '今日最热', icon: Flame },
  { key: 'hot_week', label: '本周最热', icon: TrendingUp },
  { key: 'new_arrivals', label: '最新上架', icon: Sparkles },
] as const

const MEDAL_COLORS = [
  'from-amber-400 to-amber-500',
  'from-gray-300 to-gray-400',
  'from-amber-700 to-amber-800',
]

const MEDAL_LABELS = ['金牌', '银牌', '铜牌']

function BookCover({ book, rank }: { book: Book; rank: number }) {
  const isTop3 = rank <= 3
  return (
    <div className="relative group cursor-pointer flex-shrink-0">
      <div
        className="w-16 h-20 md:w-20 md:h-28 rounded-xl overflow-hidden relative transition-transform duration-300 group-hover:scale-105"
        style={{ background: `linear-gradient(135deg, ${book.gradient?.[0] || '#667eea'}, ${book.gradient?.[1] || '#764ba2'})` }}
      >
        <div className="absolute inset-0 bg-black/10" />
        <div className="absolute inset-0 opacity-20" style={{ backgroundImage: 'radial-gradient(circle at 30% 40%, rgba(255,255,255,0.3), transparent 60%)' }} />
        <BookOpen className="w-6 h-6 md:w-8 md:h-8 text-white/80 absolute inset-0 m-auto" />
        {isTop3 && (
          <div className={`absolute top-0 left-0 w-full bg-gradient-to-r ${MEDAL_COLORS[rank - 1]} py-0.5 text-center`}>
            <span className="text-white text-xs font-bold">{MEDAL_LABELS[rank - 1]}</span>
          </div>
        )}
      </div>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-text-muted">
      <TrendingUp className="w-12 h-12 mb-3 opacity-30" />
      <p>暂无排行数据</p>
    </div>
  )
}

export default function Rankings() {
  usePageTitle('排行榜')
  const [activeTab, setActiveTab] = useState<string>('hot_today')
  const navigate = useNavigate()

  const { data, isLoading, error } = useQuery({
    queryKey: ['rankings'],
    queryFn: fetchRankings,
    staleTime: 5 * 60 * 1000,
  })

  const rankings = useMemo(
    () => data ?? { hot_today: [], hot_week: [], new_arrivals: [] },
    [data],
  )

  const books = (rankings as Record<string, Book[]>)[activeTab] || []

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center">
          <TrendingUp className="w-5 h-5 text-accent" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-text-primary">排行榜</h2>
          <p className="text-sm text-text-muted">发现热门好书</p>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-danger/10 border border-danger/20 text-danger">
          <AlertCircle className="w-4 h-4" />
          <span className="text-sm">加载失败，请稍后重试</span>
        </div>
      )}

      <div className="glass-card overflow-hidden">
        <div className="flex border-b border-border/50">
          {TABS.map((tab) => {
            const Icon = tab.icon
            const isActive = activeTab === tab.key
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-4 text-sm font-medium transition-colors relative ${
                  isActive ? 'text-accent' : 'text-text-muted hover:text-text-secondary'
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
                {isActive && (
                  <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-8 h-0.5 rounded-full bg-accent" />
                )}
              </button>
            )
          })}
        </div>

        {isLoading ? (
          <Spinner />
        ) : books.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="p-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 stagger-in">
              {books.map((book, idx) => (
                <button
                  key={book.id}
                  onClick={() => navigate(`/books/${book.id}`)}
                  className="flex items-center gap-3 p-3 rounded-xl hover:bg-accent/5 border border-transparent hover:border-accent/20 transition-all text-left group glass-card glass-card--compact"
                  style={{ animationDelay: `${idx * 0.03}s` }}
                >
                  <div className="relative flex-shrink-0">
                    {idx < 3 ? (
                      <span className={`inline-flex items-center justify-center w-7 h-7 rounded-full bg-gradient-to-br ${MEDAL_COLORS[idx]} text-white text-xs font-bold shadow-lg`}>
                        {idx + 1}
                      </span>
                    ) : (
                      <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-bg-elevated border border-border text-text-muted text-xs font-medium">
                        {idx + 1}
                      </span>
                    )}
                  </div>

                  <BookCover book={book} rank={idx + 1} />

                  <div className="flex-1 min-w-0">
                    <h3 className="text-sm font-semibold text-text-primary truncate group-hover:text-accent transition-colors">
                      {book.title}
                    </h3>
                    <p className="text-xs text-text-secondary mt-1 truncate">
                      {book.author || '未知作者'}
                    </p>
                    <div className="flex items-center gap-2 mt-2 flex-wrap">
                      {book.category && (
                        <span className="px-1.5 py-0.5 rounded bg-accent/10 text-accent text-xs">
                          {book.category}
                        </span>
                      )}
                      <span className="text-xs text-text-muted">
                        {book.chapter_count} 章
                      </span>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
