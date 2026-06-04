import { useState, useCallback, useMemo, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { usePageTitle } from '@/hooks/usePageTitle'
import {
  Search, BookOpen, Clock, TrendingUp, Flame, Sparkles,
  ChevronRight, Eye, Calendar, Star, AlertCircle, Zap, Cpu
} from 'lucide-react'
import { fetchBooks, fetchRankings, fetchRecommendations } from '@/api/books'
import { fetchDashboard } from '@/api/stats'
import { Book, RecommendBook } from '@/types'
import { useToast } from '@/components/Toast'

const STRATEGY_TABS = [
  { key: 'hybrid', label: '智能推荐', icon: Cpu },
  { key: 'hot', label: '热门', icon: Flame },
  { key: 'new', label: '新书', icon: Zap },
] as const

const CATEGORIES = [
  { name: '玄幻', icon: '✦', color: 'from-purple-500 to-indigo-600' },
  { name: '都市', icon: '◆', color: 'from-blue-500 to-cyan-500' },
  { name: '仙侠', icon: '❋', color: 'from-emerald-500 to-teal-500' },
  { name: '科幻', icon: '◈', color: 'from-violet-500 to-purple-500' },
  { name: '武侠', icon: '⚔', color: 'from-amber-500 to-orange-500' },
  { name: '历史', icon: '◉', color: 'from-rose-500 to-pink-500' },
  { name: '游戏', icon: '⬡', color: 'from-green-500 to-lime-500' },
  { name: '奇幻', icon: '✧', color: 'from-fuchsia-500 to-pink-500' },
  { name: '灵异', icon: '☽', color: 'from-slate-500 to-gray-600' },
  { name: '同人', icon: '❂', color: 'from-sky-500 to-blue-500' },
]

const RANK_TABS = [
  { key: 'hot-today', label: '今日最热' },
  { key: 'hot-week', label: '本周最热' },
  { key: 'new-arrival', label: '最新上架' },
] as const

/* ──────────────────────────────────────────────────────
   Mouse-follow highlight hook
   ────────────────────────────────────────────────────── */
function useGlassHighlight(ref: React.RefObject<HTMLElement | null>) {
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const onMove = (e: MouseEvent) => {
      const r = el.getBoundingClientRect()
      el.style.setProperty('--mouse-x', `${e.clientX - r.left}px`)
      el.style.setProperty('--mouse-y', `${e.clientY - r.top}px`)
    }
    el.addEventListener('mousemove', onMove)
    return () => el.removeEventListener('mousemove', onMove)
  }, [ref])
}

/* ──────────────────────────────────────────────────────
   Section Header with glass treatment
   ────────────────────────────────────────────────────── */
function SectionHeader({ icon: Icon, title, action }: { icon: React.ElementType; title: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between mb-5">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-xl glass-card--compact flex items-center justify-center">
          <Icon className="w-4 h-4 text-accent" />
        </div>
        <h2 className="text-lg font-bold text-text-primary tracking-tight">{title}</h2>
      </div>
      {action}
    </div>
  )
}

/* ──────────────────────────────────────────────────────
   Recommend Card — Liquid Glass Featured
   ────────────────────────────────────────────────────── */
function RecommendCard({ book, onClick, index }: { book: RecommendBook; onClick: () => void; index: number }) {
  const cardRef = useRef<HTMLButtonElement>(null)
  useGlassHighlight(cardRef)

  const formatTime = (dateStr: string) => {
    if (!dateStr) return ''
    const now = new Date()
    const date = new Date(dateStr)
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000)
    if (diff < 60) return '刚刚'
    if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
    if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
    if (diff < 604800) return `${Math.floor(diff / 86400)}天前`
    return date.toLocaleDateString('zh-CN')
  }

  // Featured card (first one) is larger
  const isFeatured = index === 0

  return (
    <button
      ref={cardRef}
      onClick={onClick}
      data-glass-highlight
      className={`group glass-card glass-card--shimmer text-left ${
        isFeatured ? 'md:col-span-2 md:row-span-1' : ''
      }`}
      style={{ animationDelay: `${index * 0.05}s` }}
    >
      {/* Shimmer layer */}
      <div className="shimmer-layer" />

      {/* Gradient top bar */}
      <div
        className="h-1"
        style={{ background: `linear-gradient(90deg, ${book.gradient?.[0] || '#667eea'}, ${book.gradient?.[1] || '#764ba2'})` }}
      />

      {/* Reason badge */}
      {book.reason && (
        <div className="absolute top-3 right-3 z-10 flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-bg-elevated/80 backdrop-blur-sm border border-border text-xs">
          <span className="text-accent">{book.reason}</span>
          {book.score > 0 && (
            <span className="px-1.5 py-0.5 rounded-full bg-accent/10 text-accent font-bold text-[10px]">
              {book.score}分
            </span>
          )}
        </div>
      )}

      <div className={`p-5 flex gap-4 ${isFeatured ? 'md:gap-5' : ''}`}>
        {/* Cover */}
        <div
          className={`rounded-xl flex-shrink-0 flex flex-col items-center justify-center relative overflow-hidden ${
            isFeatured ? 'w-[100px] h-[132px]' : 'w-[80px] h-[106px]'
          }`}
          style={{ background: `linear-gradient(135deg, ${book.gradient?.[0] || '#667eea'}, ${book.gradient?.[1] || '#764ba2'})` }}
        >
          <span className={`font-extrabold text-white/90 relative z-10 ${isFeatured ? 'text-4xl' : 'text-3xl'}`}>
            {(book.title || '书')[0]}
          </span>
          <span className="text-[10px] text-white/70 mt-1 relative z-10">
            {book.chapter_count}章
          </span>
          <div className="absolute inset-0 bg-black/5" />
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0 flex flex-col">
          <div className="flex items-center gap-2 mb-1">
            <h3 className={`font-bold text-text-primary truncate group-hover:text-accent transition-colors ${
              isFeatured ? 'text-lg' : 'text-base'
            }`}>
              {book.title}
            </h3>
            {book.is_new && (
              <span className="px-1.5 py-0.5 rounded-full bg-danger/90 text-white text-[10px] font-bold tracking-wider">
                NEW
              </span>
            )}
          </div>

          <div className="flex items-center gap-2 text-xs text-text-secondary mb-2">
            <span>{book.author || '未知作者'}</span>
            <span className="text-text-muted">•</span>
            <span>{formatTime(book.updated_at)}</span>
          </div>

          <p className={`text-text-secondary line-clamp-2 flex-1 mb-3 ${isFeatured ? 'text-sm' : 'text-xs'}`}>
            {book.description || '暂无简介'}
          </p>

          {book.tags && book.tags.length > 0 && (
            <div className="flex gap-1.5 flex-wrap mb-3">
              {book.tags.slice(0, 3).map((tag) => (
                <span
                  key={tag.id}
                  className="px-2 py-0.5 rounded-full bg-bg-tertiary text-text-secondary text-[10px] border border-border"
                >
                  {tag.name}
                </span>
              ))}
            </div>
          )}

          {/* CTA Button — primary action */}
          <div className="flex items-center gap-2 mt-auto">
            <span className="btn btn--primary btn--sm">
              <BookOpen className="w-3.5 h-3.5" /> 查看详情
            </span>
          </div>
        </div>
      </div>
    </button>
  )
}

/* ──────────────────────────────────────────────────────
   Rank Badge with special top-3 styling
   ────────────────────────────────────────────────────── */
function RankBadge({ rank }: { rank: number }) {
  if (rank === 1) {
    return (
      <span className="rank-badge--gold w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-bold">
        {rank}
      </span>
    )
  }
  if (rank === 2) {
    return (
      <span className="rank-badge--silver w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-bold">
        {rank}
      </span>
    )
  }
  if (rank === 3) {
    return (
      <span className="rank-badge--bronze w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-bold">
        {rank}
      </span>
    )
  }
  return (
    <span className="w-7 h-7 rounded-full bg-bg-tertiary border border-border flex items-center justify-center text-text-muted text-xs font-medium">
      {rank}
    </span>
  )
}

/* ──────────────────────────────────────────────────────
   Hot Book Card — compact glass
   ────────────────────────────────────────────────────── */
function HotBookCard({ book, onClick }: { book: Book; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="glass-card glass-card--compact flex-shrink-0 w-36 text-left group cursor-pointer"
    >
      <div
        className="w-32 h-44 rounded-xl flex items-center justify-center relative overflow-hidden group-hover:scale-105 transition-transform duration-300 mx-auto"
        style={{ background: `linear-gradient(135deg, ${book.gradient?.[0] || '#667eea'}, ${book.gradient?.[1] || '#764ba2'})` }}
      >
        <div className="absolute inset-0 bg-black/10" />
        <div className="absolute inset-0 opacity-20" style={{ backgroundImage: 'radial-gradient(circle at 30% 40%, rgba(255,255,255,0.3), transparent 60%)' }} />
        <BookOpen className="w-10 h-10 text-white/80 relative z-10" />
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-2 z-10">
          <p className="text-white text-xs font-medium truncate">{book.title}</p>
        </div>
      </div>
      <div className="mt-2">
        <p className="text-sm font-medium text-text-primary truncate group-hover:text-accent transition-colors">{book.title}</p>
        <p className="text-xs text-text-secondary mt-0.5 truncate">{book.author || '未知作者'}</p>
        {book.tags?.length > 0 && (
          <p className="text-xs text-text-muted mt-0.5 truncate">{book.tags[0].name}</p>
        )}
      </div>
    </button>
  )
}

/* ──────────────────────────────────────────────────────
   Skeleton
   ────────────────────────────────────────────────────── */
function SkeletonCard({ className = '' }: { className?: string }) {
  return (
    <div className={`rounded-xl bg-bg-tertiary/50 animate-pulse ${className}`} />
  )
}

/* ═══════════════════════════════════════════════════════
   Main HomePortal Component
   ═══════════════════════════════════════════════════════ */
export default function HomePortal() {
  usePageTitle('首页')
  const [search, setSearch] = useState('')
  const [activeStrategy, setActiveStrategy] = useState<string>('hybrid')
  const [activeRankTab, setActiveRankTab] = useState<string>('hot-today')
  const hotScrollRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const toast = useToast()

  const { data: booksData, isLoading: booksLoading, error: booksError } = useQuery({
    queryKey: ['books', 'portal'],
    queryFn: () => fetchBooks({}),
  })

  const { data: rankingsData } = useQuery({
    queryKey: ['rankings'],
    queryFn: fetchRankings,
    staleTime: 5 * 60 * 1000,
  })

  const { data: dashboardData } = useQuery({
    queryKey: ['dashboard'],
    queryFn: fetchDashboard,
  })

  const { data: recData, isLoading: recLoading } = useQuery({
    queryKey: ['recommendations', activeStrategy],
    queryFn: () => fetchRecommendations(activeStrategy, 12),
    staleTime: 2 * 60 * 1000,
  })

  const books = useMemo(() => booksData?.items ?? [], [booksData])
  const rankings = useMemo(() => rankingsData ?? { hot_today: [], hot_week: [], new_arrivals: [] }, [rankingsData])
  const recommendations = useMemo(() => recData?.data ?? [], [recData])

  const hotBooks = useMemo(() => {
    const src = rankings.hot_today.length > 0 ? rankings.hot_today : books
    return src.slice(0, 15)
  }, [rankings.hot_today, books])

  const latestBooks = useMemo(
    () => {
      const src = rankings.new_arrivals.length > 0 ? rankings.new_arrivals : [...books].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
      return src.slice(0, 10)
    },
    [rankings.new_arrivals, books]
  )

  const rankTabMap: Record<string, Book[]> = {
    'hot-today': rankings.hot_today.length > 0 ? rankings.hot_today : books.slice(0, 10),
    'hot-week': rankings.hot_week.length > 0 ? rankings.hot_week : books.slice(0, 10),
    'new-arrival': rankings.new_arrivals.length > 0 ? rankings.new_arrivals : books.slice(0, 10),
  }
  const rankBooks = rankTabMap[activeRankTab]

  const handleSearch = useCallback((e: React.FormEvent) => {
    e.preventDefault()
    if (!search.trim()) {
      toast.warning('请输入搜索关键词')
      return
    }
    navigate(`/search?q=${encodeURIComponent(search.trim())}`)
  }, [search, navigate, toast])

  const scrollHot = useCallback((dir: 'left' | 'right') => {
    const el = hotScrollRef.current
    if (!el) return
    el.scrollBy({ left: dir === 'left' ? -400 : 400, behavior: 'smooth' })
  }, [])

  const formatTime = (dateStr: string) => {
    const now = new Date()
    const date = new Date(dateStr)
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000)
    if (diff < 60) return '刚刚'
    if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
    if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
    if (diff < 604800) return `${Math.floor(diff / 86400)}天前`
    return date.toLocaleDateString('zh-CN')
  }

  const totalBooks = dashboardData?.total_books ?? 0
  const totalChapters = dashboardData?.total_chapters ?? 0
  const totalWords = dashboardData?.total_words ?? 0
  const categoryStats = dashboardData?.category_stats ?? []

  return (
    <div className="min-h-[calc(100vh-var(--navbar-height))] aurora-bg">
      {/* Aurora extra orb */}
      <div className="aurora-orb aurora-orb--warm" />

      {/* ─── Hero Section ─── */}
      <section className="relative z-[1] overflow-hidden">
        <div className="relative max-w-6xl mx-auto px-6 py-16 text-center">
          {/* Pill badge */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full glass-card--compact mb-6">
            <Sparkles className="w-3.5 h-3.5 text-accent" />
            <span className="text-accent text-sm font-medium">智能推荐 · 海量好书</span>
          </div>

          <h1 className="text-4xl md:text-5xl font-extrabold text-text-primary mb-4 tracking-tight">
            发现你的下一本<span className="text-transparent bg-clip-text bg-gradient-to-r from-accent to-amber-300">好书</span>
          </h1>
          <p className="text-text-secondary text-lg mb-8 max-w-xl mx-auto">
            探索 {totalBooks > 0 ? `${totalBooks}` : '海量'} 本精彩小说，涵盖玄幻、都市、仙侠等十大分类
          </p>

          {/* Search — glass input */}
          <form onSubmit={handleSearch} className="max-w-2xl mx-auto">
            <div className="relative group">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted group-focus-within:text-accent transition-colors" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="搜索书名、作者、标签..."
                className="w-full h-14 pl-12 pr-32 rounded-2xl glass-input text-text-primary placeholder:text-text-muted text-base shadow-lg shadow-black/10"
              />
              <button
                type="submit"
                className="btn btn--primary btn--lg absolute right-2 top-1/2 -translate-y-1/2"
              >
                搜索
              </button>
            </div>
          </form>

          {/* Stats */}
          <div className="flex items-center justify-center gap-8 mt-8 text-sm text-text-secondary">
            <span className="flex items-center gap-1.5">
              <BookOpen className="w-4 h-4 text-accent/70" /> {totalBooks} 本书
            </span>
            <span className="flex items-center gap-1.5">
              <Eye className="w-4 h-4 text-accent/70" /> {totalChapters > 0 ? `${(totalChapters / 1000).toFixed(0)}K` : '0'} 章节
            </span>
            <span className="flex items-center gap-1.5">
              <Star className="w-4 h-4 text-accent/70" /> {totalWords > 0 ? `${(totalWords / 10000).toFixed(0)}万` : '0'} 字
            </span>
          </div>
        </div>
      </section>

      {/* ─── Content Sections ─── */}
      <div className="relative z-[1] max-w-6xl mx-auto px-6 pb-16 space-y-14">

        {/* AI Recommendations */}
        <section>
          <SectionHeader
            icon={Cpu}
            title="智能推荐"
            action={
              <div className="flex gap-1 p-1 rounded-xl glass-card--compact">
                {STRATEGY_TABS.map((tab) => {
                  const Icon = tab.icon
                  return (
                    <button
                      key={tab.key}
                      onClick={() => setActiveStrategy(tab.key)}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                        activeStrategy === tab.key
                          ? 'bg-accent text-white shadow-md shadow-accent/25'
                          : 'text-text-secondary hover:text-text-primary'
                      }`}
                    >
                      <Icon className="w-3 h-3" />
                      {tab.label}
                    </button>
                  )
                })}
              </div>
            }
          />

          {recLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {Array.from({ length: 6 }).map((_, i) => (
                <SkeletonCard key={i} className="h-52" />
              ))}
            </div>
          ) : recommendations.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-text-muted">
              <BookOpen className="w-10 h-10 mb-3 opacity-30" />
              <p>暂无推荐数据</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 stagger-in">
              {recommendations.map((book, idx) => (
                <RecommendCard
                  key={book.id}
                  book={book}
                  index={idx}
                  onClick={() => navigate(`/books/${book.id}`)}
                />
              ))}
            </div>
          )}
        </section>

        {/* Hot Recommendations — horizontal scroll */}
        <section>
          <SectionHeader icon={Flame} title="热门推荐" />

          {booksLoading ? (
            <div className="flex gap-4 overflow-hidden">
              {Array.from({ length: 6 }).map((_, i) => (
                <SkeletonCard key={i} className="w-36 h-56 flex-shrink-0" />
              ))}
            </div>
          ) : booksError ? (
            <div className="flex items-center justify-center gap-2 py-12 text-text-muted">
              <AlertCircle className="w-5 h-5 text-danger" />
              <span>加载失败，请稍后重试</span>
            </div>
          ) : (
            <div className="relative group/scroll">
              <button
                onClick={() => scrollHot('left')}
                className="absolute left-0 top-1/2 -translate-y-1/2 z-10 w-9 h-9 rounded-full glass-card--compact flex items-center justify-center hover:bg-accent/10 transition-colors opacity-0 group-hover/scroll:opacity-100"
                aria-label="向左滚动"
              >
                <ChevronRight className="w-4 h-4 text-text-secondary rotate-180" />
              </button>
              <button
                onClick={() => scrollHot('right')}
                className="absolute right-0 top-1/2 -translate-y-1/2 z-10 w-9 h-9 rounded-full glass-card--compact flex items-center justify-center hover:bg-accent/10 transition-colors opacity-0 group-hover/scroll:opacity-100"
                aria-label="向右滚动"
              >
                <ChevronRight className="w-4 h-4 text-text-secondary" />
              </button>

              <div
                ref={hotScrollRef}
                className="flex gap-4 overflow-x-auto pb-2 snap-x snap-mandatory"
                style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
              >
                {hotBooks.map((book) => (
                  <div key={book.id} className="snap-start">
                    <HotBookCard
                      book={book}
                      onClick={() => navigate(`/books/${book.id}`)}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* Latest Updates & Rankings */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-8">
          {/* Latest Updates */}
          <section className="lg:col-span-3">
            <SectionHeader icon={Clock} title="最新更新" />

            {booksLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 6 }).map((_, i) => (
                  <SkeletonCard key={i} className="h-14" />
                ))}
              </div>
            ) : booksError ? (
              <div className="flex items-center justify-center gap-2 py-12 text-text-muted">
                <AlertCircle className="w-5 h-5 text-danger" />
                <span>加载失败，请稍后重试</span>
              </div>
            ) : latestBooks.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-text-muted">
                <BookOpen className="w-10 h-10 mb-3 opacity-30" />
                <p>暂无书籍</p>
              </div>
            ) : (
              <div className="glass-card stagger-in">
                {latestBooks.map((book, idx) => (
                  <button
                    key={book.id}
                    onClick={() => navigate(`/books/${book.id}`)}
                    className={`w-full flex items-center gap-4 px-5 py-3.5 hover:bg-accent/5 transition-colors text-left group ${
                      idx !== latestBooks.length - 1 ? 'border-b border-border/50' : ''
                    }`}
                  >
                    <div className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: `linear-gradient(135deg, ${book.gradient?.[0] || '#667eea'}, ${book.gradient?.[1] || '#764ba2'})` }}>
                      <BookOpen className="w-5 h-5 text-white/80" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-text-primary truncate group-hover:text-accent transition-colors">{book.title}</p>
                      <p className="text-xs text-text-secondary mt-0.5">{book.author || '未知作者'}</p>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <p className="text-xs text-text-muted">{book.chapter_count} 章</p>
                      <p className="text-xs text-text-muted">{formatTime(book.updated_at)}</p>
                    </div>
                    <ChevronRight className="w-4 h-4 text-text-muted opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                  </button>
                ))}
              </div>
            )}
          </section>

          {/* Rankings */}
          <section className="lg:col-span-2">
            <SectionHeader icon={TrendingUp} title="排行榜" />

            <div className="glass-card">
              <div className="flex border-b border-border/50">
                {RANK_TABS.map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => setActiveRankTab(tab.key)}
                    className={`flex-1 px-3 py-3 text-sm font-medium transition-colors relative ${
                      activeRankTab === tab.key ? 'text-accent' : 'text-text-muted hover:text-text-secondary'
                    }`}
                  >
                    {tab.label}
                    {activeRankTab === tab.key && (
                      <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-6 h-0.5 rounded-full bg-accent" />
                    )}
                  </button>
                ))}
              </div>

              <div className="p-3 stagger-in">
                {booksLoading ? (
                  <div className="space-y-2">
                    {Array.from({ length: 8 }).map((_, i) => (
                      <SkeletonCard key={i} className="h-12" />
                    ))}
                  </div>
                ) : rankBooks.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 text-text-muted">
                    <Star className="w-8 h-8 mb-2 opacity-30" />
                    <p className="text-sm">暂无排行数据</p>
                  </div>
                ) : (
                  rankBooks.map((book, idx) => (
                    <button
                      key={`${book.id}-${idx}`}
                      onClick={() => navigate(`/books/${book.id}`)}
                      className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-accent/5 transition-colors text-left group"
                    >
                      <RankBadge rank={idx + 1} />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-text-primary truncate group-hover:text-accent transition-colors">{book.title}</p>
                        <p className="text-xs text-text-secondary mt-0.5">{book.author || '未知作者'}</p>
                      </div>
                      {book.category && (
                        <span className="px-2 py-0.5 rounded bg-accent/10 text-accent text-xs flex-shrink-0">
                          {book.category}
                        </span>
                      )}
                    </button>
                  ))
                )}
              </div>
            </div>
          </section>
        </div>

        {/* Category Navigation */}
        <section>
          <SectionHeader icon={Calendar} title="分类导航" />
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4 stagger-in">
            {CATEGORIES.map((cat) => {
              const catBookCount = categoryStats.find((s) => s.category === cat.name)?.count ?? 0
              return (
                <button
                  key={cat.name}
                  onClick={() => navigate(`/books?category=${cat.name}`)}
                  className="glass-card glass-card--shimmer p-5 text-left hover:border-accent/30 active:scale-[0.98] group"
                >
                  {/* Shimmer layer */}
                  <div className="shimmer-layer" />
                  {/* Gradient overlay */}
                  <div className={`absolute inset-0 bg-gradient-to-br ${cat.color} opacity-0 group-hover:opacity-10 transition-opacity duration-300`} />
                  <div className="relative z-10">
                    <span className="text-2xl mb-2 block group-hover:scale-110 transition-transform duration-300">{cat.icon}</span>
                    <p className="text-sm font-semibold text-text-primary group-hover:text-accent transition-colors">{cat.name}</p>
                    <p className="text-xs text-text-muted mt-1">{catBookCount > 0 ? `${catBookCount} 本` : '探索更多'}</p>
                  </div>
                </button>
              )
            })}
          </div>
        </section>
      </div>
    </div>
  )
}
