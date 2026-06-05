import { useState, useCallback, useMemo, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { usePageTitle } from '@/hooks/usePageTitle'
import PageTitle from '@/components/PageTitle'
import {
  Search, BookOpen, Clock, TrendingUp, Flame, Sparkles,
  ChevronRight, Eye, Calendar, Star, AlertCircle, Zap, Cpu
} from 'lucide-react'
import { fetchBooks, fetchRankings, fetchRecommendations } from '@/api/books'
import { fetchDashboard } from '@/api/stats'
import { Book, RecommendBook } from '@/types'
import { useToast } from '@/components/Toast'

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

/* ─── Mouse-follow highlight ─── */
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

/* ─── Section Header ─── */
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

/* ─── Recommend Card ─── */
function RecommendCard({ book, onClick, index }: { book: RecommendBook; onClick: () => void; index: number }) {
  const cardRef = useRef<HTMLButtonElement>(null)
  useGlassHighlight(cardRef)

  return (
    <button
      ref={cardRef}
      onClick={onClick}
      data-glass-highlight
      className="group glass-card glass-card--shimmer text-left"
      style={{ animationDelay: `${index * 0.05}s` }}
    >
      <div className="shimmer-layer" />
      <div
        className="h-1"
        style={{ background: `linear-gradient(90deg, ${book.gradient?.[0] || '#667eea'}, ${book.gradient?.[1] || '#764ba2'})` }}
      />
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
      <div className="p-4 flex gap-3">
        <div
          className="w-[72px] h-[96px] rounded-xl flex-shrink-0 flex flex-col items-center justify-center relative overflow-hidden"
          style={{ background: `linear-gradient(135deg, ${book.gradient?.[0] || '#667eea'}, ${book.gradient?.[1] || '#764ba2'})` }}
        >
          <span className="font-extrabold text-white/90 relative z-10 text-2xl">
            {(book.title || '书')[0]}
          </span>
          <span className="text-[10px] text-white/70 mt-1 relative z-10">
            {book.chapter_count}章
          </span>
          <div className="absolute inset-0 bg-black/5" />
        </div>
        <div className="flex-1 min-w-0 flex flex-col">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-bold text-text-primary truncate group-hover:text-accent transition-colors text-sm">
              {book.title}
            </h3>
            {book.is_new && (
              <span className="px-1.5 py-0.5 rounded-full bg-danger/90 text-white text-[10px] font-bold">NEW</span>
            )}
          </div>
          <div className="flex items-center gap-2 text-xs text-text-secondary mb-1.5">
            <span>{book.author || '未知作者'}</span>
          </div>
          <p className="text-text-secondary line-clamp-2 flex-1 mb-2 text-xs">
            {book.description || '暂无简介'}
          </p>
          {book.tags && book.tags.length > 0 && (
            <div className="flex gap-1 flex-wrap mb-2">
              {book.tags.slice(0, 2).map((tag) => (
                <span key={tag.id} className="px-1.5 py-0.5 rounded-full bg-bg-tertiary text-text-secondary text-[10px] border border-border">
                  {tag.name}
                </span>
              ))}
            </div>
          )}
          <span className="btn btn--primary btn--sm w-fit">
            <BookOpen className="w-3 h-3" /> 阅读
          </span>
        </div>
      </div>
    </button>
  )
}

/* ─── Rank Badge ─── */
function RankBadge({ rank }: { rank: number }) {
  if (rank <= 3) {
    const cls = rank === 1 ? 'rank-badge--gold' : rank === 2 ? 'rank-badge--silver' : 'rank-badge--bronze'
    return (
      <span className={`${cls} w-6 h-6 rounded-full flex items-center justify-center text-white text-[10px] font-bold`}>
        {rank}
      </span>
    )
  }
  return (
    <span className="w-6 h-6 rounded-full bg-bg-tertiary border border-border flex items-center justify-center text-text-muted text-[10px]">
      {rank}
    </span>
  )
}

/* ─── Skeleton ─── */
function SkeletonCard({ className = '' }: { className?: string }) {
  return <div className={`rounded-xl bg-bg-tertiary/50 animate-pulse ${className}`} />
}

/* ─── Rank List Card (无标签页，直接展示) ─── */
function RankListCard({ title, icon: Icon, books, loading, onBookClick }: {
  title: string
  icon: React.ElementType
  books: Book[]
  loading: boolean
  onBookClick: (id: number) => void
}) {
  return (
    <div className="glass-card flex flex-col">
      <div className="flex items-center gap-2.5 px-5 py-4 border-b border-border/50">
        <Icon className="w-4 h-4 text-accent" />
        <h3 className="text-sm font-bold text-text-primary">{title}</h3>
      </div>
      <div className="flex-1 p-3">
        {loading ? (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <SkeletonCard key={i} className="h-10" />
            ))}
          </div>
        ) : books.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-text-muted">
            <Star className="w-6 h-6 mb-2 opacity-30" />
            <p className="text-xs">暂无数据</p>
          </div>
        ) : (
          books.slice(0, 8).map((book, idx) => (
            <button
              key={`${book.id}-${idx}`}
              onClick={() => onBookClick(book.id)}
              className="w-full flex items-center gap-2.5 px-2 py-2 rounded-lg hover:bg-accent/5 transition-colors text-left group"
            >
              <RankBadge rank={idx + 1} />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-text-primary truncate group-hover:text-accent transition-colors">{book.title}</p>
                <p className="text-[10px] text-text-secondary">{book.author || '未知作者'}</p>
              </div>
              {book.category && (
                <span className="px-1.5 py-0.5 rounded bg-accent/10 text-accent text-[10px] flex-shrink-0">
                  {book.category}
                </span>
              )}
            </button>
          ))
        )}
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════
   Main HomePortal — 全卡片组合布局，无标签页
   ═══════════════════════════════════════════════════════ */
export default function HomePortal() {
  usePageTitle('首页')
  const [search, setSearch] = useState('')
  const navigate = useNavigate()
  const toast = useToast()

  const { data: booksData, isLoading: booksLoading } = useQuery({
    queryKey: ['books', 'portal'],
    queryFn: () => fetchBooks({}),
  })

  const { data: rankingsData, isLoading: rankLoading } = useQuery({
    queryKey: ['rankings'],
    queryFn: fetchRankings,
    staleTime: 5 * 60 * 1000,
  })

  const { data: dashboardData } = useQuery({
    queryKey: ['dashboard'],
    queryFn: fetchDashboard,
  })

  // 同时请求三种推荐策略
  const { data: recHybrid } = useQuery({
    queryKey: ['recommendations', 'hybrid'],
    queryFn: () => fetchRecommendations('hybrid', 6),
    staleTime: 2 * 60 * 1000,
  })

  const { data: recHot } = useQuery({
    queryKey: ['recommendations', 'hot'],
    queryFn: () => fetchRecommendations('hot', 6),
    staleTime: 2 * 60 * 1000,
  })

  const { data: recNew } = useQuery({
    queryKey: ['recommendations', 'new'],
    queryFn: () => fetchRecommendations('new', 6),
    staleTime: 2 * 60 * 1000,
  })

  const books = useMemo(() => booksData?.items ?? [], [booksData])
  const rankings = useMemo(() => rankingsData ?? { hot_today: [], hot_week: [], new_arrivals: [] }, [rankingsData])
  const hybridRecs = useMemo(() => recHybrid?.data ?? [], [recHybrid])
  const hotRecs = useMemo(() => recHot?.data ?? [], [recHot])
  const newRecs = useMemo(() => recNew?.data ?? [], [recNew])

  const latestBooks = useMemo(() => {
    const src = rankings.new_arrivals.length > 0 ? rankings.new_arrivals : [...books].sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
    return src.slice(0, 10)
  }, [rankings.new_arrivals, books])

  const handleSearch = useCallback((e: React.FormEvent) => {
    e.preventDefault()
    if (!search.trim()) {
      toast.warning('请输入搜索关键词')
      return
    }
    navigate(`/search?q=${encodeURIComponent(search.trim())}`)
  }, [search, navigate, toast])

  const handleBookClick = useCallback((id: number) => navigate(`/books/${id}`), [navigate])

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

  const totalBooks = dashboardData?.total_books ?? 0
  const totalChapters = dashboardData?.total_chapters ?? 0
  const totalWords = dashboardData?.total_words ?? 0
  const categoryStats = dashboardData?.category_stats ?? []

  const recLoading = !recHybrid && !recHot && !recNew

  return (
    <div className="min-h-[calc(100vh-var(--navbar-height))] aurora-bg">
      <PageTitle title="首页" />
      <div className="aurora-orb aurora-orb--warm" />

      {/* ─── Hero ─── */}
      <section className="relative z-[1] overflow-hidden">
        <div className="relative max-w-6xl mx-auto px-6 py-14 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full glass-card--compact mb-5">
            <Sparkles className="w-3.5 h-3.5 text-accent" />
            <span className="text-accent text-sm font-medium">智能推荐 · 海量好书</span>
          </div>

          <h1 className="text-4xl md:text-5xl font-extrabold text-text-primary mb-3 tracking-tight">
            发现你的下一本<span className="text-transparent bg-clip-text bg-gradient-to-r from-accent to-amber-300">好书</span>
          </h1>
          <p className="text-text-secondary text-lg mb-7 max-w-xl mx-auto">
            探索 {totalBooks > 0 ? `${totalBooks}` : '海量'} 本精彩小说，涵盖玄幻、都市、仙侠等十大分类
          </p>

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
              <button type="submit" className="btn btn--primary btn--lg absolute right-2 top-1/2 -translate-y-1/2">
                搜索
              </button>
            </div>
          </form>

          <div className="flex items-center justify-center gap-8 mt-7 text-sm text-text-secondary">
            <span className="flex items-center gap-1.5"><BookOpen className="w-4 h-4 text-accent/70" /> {totalBooks} 本书</span>
            <span className="flex items-center gap-1.5"><Eye className="w-4 h-4 text-accent/70" /> {totalChapters > 0 ? `${(totalChapters / 1000).toFixed(0)}K` : '0'} 章节</span>
            <span className="flex items-center gap-1.5"><Star className="w-4 h-4 text-accent/70" /> {totalWords > 0 ? `${(totalWords / 10000).toFixed(0)}万` : '0'} 字</span>
          </div>
        </div>
      </section>

      {/* ─── Content: 全卡片组合，无标签页 ─── */}
      <div className="relative z-[1] max-w-6xl mx-auto px-6 pb-16 space-y-10">

        {/* ── 三栏推荐卡片 ── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 智能推荐 */}
          <section>
            <SectionHeader icon={Cpu} title="智能推荐" action={
              <button onClick={() => navigate('/books')} className="text-xs text-accent hover:underline">查看全部</button>
            } />
            {recLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} className="h-40" />)}
              </div>
            ) : hybridRecs.length === 0 ? (
              <div className="glass-card flex flex-col items-center justify-center py-12 text-text-muted">
                <Cpu className="w-8 h-8 mb-2 opacity-30" />
                <p className="text-sm">暂无推荐</p>
              </div>
            ) : (
              <div className="space-y-3 stagger-in">
                {hybridRecs.slice(0, 4).map((book, idx) => (
                  <RecommendCard key={book.id} book={book} index={idx} onClick={() => navigate(`/books/${book.id}`)} />
                ))}
              </div>
            )}
          </section>

          {/* 热门推荐 */}
          <section>
            <SectionHeader icon={Flame} title="热门推荐" action={
              <button onClick={() => navigate('/rankings')} className="text-xs text-accent hover:underline">查看全部</button>
            } />
            {recLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} className="h-40" />)}
              </div>
            ) : hotRecs.length === 0 ? (
              <div className="glass-card flex flex-col items-center justify-center py-12 text-text-muted">
                <Flame className="w-8 h-8 mb-2 opacity-30" />
                <p className="text-sm">暂无热门</p>
              </div>
            ) : (
              <div className="space-y-3 stagger-in">
                {hotRecs.slice(0, 4).map((book, idx) => (
                  <RecommendCard key={book.id} book={book} index={idx} onClick={() => navigate(`/books/${book.id}`)} />
                ))}
              </div>
            )}
          </section>

          {/* 新书推荐 */}
          <section>
            <SectionHeader icon={Zap} title="新书推荐" action={
              <button onClick={() => navigate('/books')} className="text-xs text-accent hover:underline">查看全部</button>
            } />
            {recLoading ? (
              <div className="space-y-3">
                {Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} className="h-40" />)}
              </div>
            ) : newRecs.length === 0 ? (
              <div className="glass-card flex flex-col items-center justify-center py-12 text-text-muted">
                <Zap className="w-8 h-8 mb-2 opacity-30" />
                <p className="text-sm">暂无新书</p>
              </div>
            ) : (
              <div className="space-y-3 stagger-in">
                {newRecs.slice(0, 4).map((book, idx) => (
                  <RecommendCard key={book.id} book={book} index={idx} onClick={() => navigate(`/books/${book.id}`)} />
                ))}
              </div>
            )}
          </section>
        </div>

        {/* ── 排行榜三卡片 ── */}
        <section>
          <SectionHeader icon={TrendingUp} title="排行榜" action={
            <button onClick={() => navigate('/rankings')} className="text-xs text-accent hover:underline">完整榜单</button>
          } />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <RankListCard
              title="今日最热"
              icon={Flame}
              books={rankings.hot_today.length > 0 ? rankings.hot_today : books.slice(0, 8)}
              loading={rankLoading}
              onBookClick={handleBookClick}
            />
            <RankListCard
              title="本周最热"
              icon={TrendingUp}
              books={rankings.hot_week.length > 0 ? rankings.hot_week : books.slice(0, 8)}
              loading={rankLoading}
              onBookClick={handleBookClick}
            />
            <RankListCard
              title="最新上架"
              icon={Zap}
              books={rankings.new_arrivals.length > 0 ? rankings.new_arrivals : books.slice(0, 8)}
              loading={rankLoading}
              onBookClick={handleBookClick}
            />
          </div>
        </section>

        {/* ── 最新更新 ── */}
        <section>
          <SectionHeader icon={Clock} title="最新更新" action={
            <button onClick={() => navigate('/books')} className="text-xs text-accent hover:underline">更多</button>
          } />
          {booksLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => <SkeletonCard key={i} className="h-14" />)}
            </div>
          ) : latestBooks.length === 0 ? (
            <div className="glass-card flex flex-col items-center justify-center py-12 text-text-muted">
              <BookOpen className="w-8 h-8 mb-2 opacity-30" />
              <p className="text-sm">暂无书籍</p>
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

        {/* ── 分类导航 ── */}
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
                  <div className="shimmer-layer" />
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
