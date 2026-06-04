import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { usePageTitle } from '@/hooks/usePageTitle'
import {
  ArrowLeft, BookOpen, Heart, BookmarkPlus,
  FileText, Clock, PenTool, Star,
  ChevronRight, MessageSquare, MessageSquarePlus,
  Loader2, AlertCircle, Eye, Sparkles,
} from 'lucide-react'
import { fetchBook, fetchChapters, fetchSimilarBooks } from '@/api/books'
import { toggleFavorite } from '@/api/favorites'
import { Chapter, RecommendBook } from '@/types'
import { useToast } from '@/components/Toast'
import { Spinner } from '@/components/Loading'

export default function BookDetail() {
  usePageTitle('书籍详情')
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const toast = useToast()
  const queryClient = useQueryClient()

  const bookId = Number(id)

  const { data: book, isLoading: bookLoading, error: bookError } = useQuery({
    queryKey: ['book', bookId],
    queryFn: () => fetchBook(bookId),
    enabled: !!bookId,
  })

  const { data: chapters, isLoading: chaptersLoading } = useQuery({
    queryKey: ['chapters', bookId],
    queryFn: () => fetchChapters(bookId),
    enabled: !!bookId,
  })

  const { data: similarData, isLoading: similarLoading } = useQuery({
    queryKey: ['similar-books', bookId],
    queryFn: () => fetchSimilarBooks(bookId, 8),
    enabled: !!bookId,
    staleTime: 5 * 60 * 1000,
  })

  const similarBooks = similarData?.data ?? []

  const favMutation = useMutation({
    mutationFn: toggleFavorite,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['book', bookId] })
      queryClient.invalidateQueries({ queryKey: ['books'] })
    },
  })

  const handleToggleFav = async () => {
    try {
      const res = await favMutation.mutateAsync(bookId)
      toast.success(res.message)
    } catch {
      toast.error('操作失败')
    }
  }

  const handleStartReading = () => {
    if (!chapters?.length) return
    const progressChapter = book?.reading_progress?.chapter_id
    const startIdx = progressChapter
      ? chapters.findIndex((c) => c.id === progressChapter)
      : 0
    const idx = startIdx >= 0 ? startIdx : 0
    navigate(`/chapters`, { state: { bookId, chapterIdx: idx } })
  }

  const handleChapterClick = (idx: number) => {
    navigate(`/chapters`, { state: { bookId, chapterIdx: idx } })
  }

  const totalWords = chapters?.reduce((sum, c) => sum + c.word_count, 0) ?? 0

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

  if (bookLoading) {
    return <Spinner />
  }

  if (bookError || !book) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-text-muted">
        <AlertCircle className="w-12 h-12 mb-3 opacity-30" />
        <p className="text-lg font-medium">书籍加载失败</p>
        <p className="text-sm mt-1">该书籍可能不存在或已被删除</p>
        <button
          onClick={() => navigate(-1)}
          className="btn btn--secondary btn--lg mt-6"
        >
          <ArrowLeft className="w-4 h-4" />
          返回
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-text-muted">
        <Link to="/" className="hover:text-accent transition-colors">首页</Link>
        <ChevronRight className="w-3.5 h-3.5" />
        <Link to="/books" className="hover:text-accent transition-colors">书籍</Link>
        <ChevronRight className="w-3.5 h-3.5" />
        <span className="text-text-primary truncate max-w-xs">{book.title}</span>
      </nav>

      {/* Book Header — Glass Showcase Box */}
      <div className="glass-card p-8 md:p-12 relative overflow-hidden">
        {/* Background gradient */}
        <div
          className="absolute inset-0 opacity-30"
          style={{ background: `linear-gradient(135deg, ${book.gradient?.[0] || '#667eea'}, ${book.gradient?.[1] || '#764ba2'})` }}
        />
        <div className="absolute inset-0 bg-black/20" />

        <div className="relative z-10 flex flex-col md:flex-row gap-8">
          {/* Cover — glass box effect */}
          <div
            className="w-44 h-64 rounded-2xl flex-shrink-0 flex items-center justify-center shadow-2xl overflow-hidden mx-auto md:mx-0"
            style={{ background: `linear-gradient(135deg, ${book.gradient?.[0] || '#667eea'}, ${book.gradient?.[1] || '#764ba2'})` }}
          >
            <div className="absolute inset-0 bg-black/10" />
            <div className="absolute inset-0 opacity-20" style={{ backgroundImage: 'radial-gradient(circle at 20% 50%, rgba(255,255,255,0.2), transparent 60%)' }} />
            <BookOpen className="w-16 h-16 text-white/60 relative z-10" />
          </div>

          {/* Info */}
          <div className="flex-1 text-center md:text-left">
            <h1 className="text-3xl md:text-4xl font-extrabold text-white mb-2 tracking-tight">{book.title}</h1>
            <p className="text-white/70 text-lg mb-4">{book.author || '未知作者'}</p>

            <div className="flex flex-wrap items-center justify-center md:justify-start gap-2 mb-4">
              {book.category && (
                <span className="px-3 py-1 rounded-full bg-white/15 text-white text-sm font-medium backdrop-blur-sm">
                  {book.category}
                </span>
              )}
              {book.tags.map((tag) => (
                <span
                  key={tag.id}
                  className="px-3 py-1 rounded-full text-white text-sm backdrop-blur-sm"
                  style={{ backgroundColor: tag.color + '40', border: `1px solid ${tag.color}60` }}
                >
                  {tag.name}
                </span>
              ))}
            </div>

            <p className="text-white/60 text-sm leading-relaxed max-w-xl mb-6 line-clamp-3">
              {book.description || '暂无简介'}
            </p>

            {/* Action Buttons — Three-tier priority layout
                Primary (🔴): Start Reading — solid fill, most prominent
                Secondary (🟡): Favorite — glass outline, state changes
                Tertiary (🟢): Add to Shelf — subtle outline */}
            <div className="flex flex-wrap items-center justify-center md:justify-start gap-3">
              {/* 🔴 Primary: Start Reading — solid fill */}
              <button
                onClick={handleStartReading}
                disabled={!chapters?.length}
                className="btn btn--lg disabled:opacity-50 bg-white text-text-primary font-bold shadow-lg shadow-black/20 hover:bg-white/90"
              >
                <BookOpen className="w-4 h-4" />
                {book.reading_progress ? '继续阅读' : '开始阅读'}
              </button>
              {/* 🟡 Secondary: Favorite — with optimistic update state */}
              <button
                onClick={handleToggleFav}
                disabled={favMutation.isPending}
                className={`btn btn--secondary btn--lg disabled:opacity-50 ${
                  book.is_favorited
                    ? 'btn--danger'
                    : ''
                }`}
              >
                {favMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Heart className={`w-4 h-4 ${book.is_favorited ? 'fill-current' : ''}`} />
                )}
                {book.is_favorited ? '已收藏' : '收藏'}
              </button>
              {/* 🟢 Tertiary: Add to Shelf */}
              <button
                onClick={handleStartReading}
                disabled={!chapters?.length}
                className="btn btn--secondary btn--lg disabled:opacity-50 text-white border-white/20 hover:border-accent"
              >
                <BookmarkPlus className="w-4 h-4" />
                加入书架
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Row — glass cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 stagger-in">
        {[
          { icon: FileText, label: '总章节', value: `${book.total_chapters} 章` },
          { icon: PenTool, label: '总字数', value: totalWords > 0 ? `${(totalWords / 1000).toFixed(1)}K 字` : '—' },
          { icon: Clock, label: '最后更新', value: formatTime(book.updated_at) },
          { icon: Star, label: '收藏状态', value: book.is_favorited ? '已收藏' : '未收藏' },
        ].map((stat) => (
          <div key={stat.label} className="glass-card p-5 flex items-center gap-4">
            <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center flex-shrink-0">
              <stat.icon className="w-5 h-5 text-accent" />
            </div>
            <div>
              <div className="text-sm text-text-muted">{stat.label}</div>
              <div className="text-base font-semibold text-text-primary">{stat.value}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Chapter List — glass container */}
      <div className="glass-card">
        <div className="px-6 py-4 border-b border-border/50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-accent" />
            <h2 className="text-lg font-bold text-text-primary">章节目录</h2>
            <span className="text-sm text-text-muted">({chapters?.length ?? 0} 章)</span>
          </div>
          {book.reading_progress && (
            <span className="text-xs text-accent flex items-center gap-1">
              <Eye className="w-3.5 h-3.5" />
              上次阅读到: {chapters?.find((c) => c.id === book.reading_progress?.chapter_id)?.title || '未知'}
            </span>
          )}
        </div>

        {chaptersLoading ? (
          <div className="p-8"><Spinner /></div>
        ) : !chapters?.length ? (
          <div className="flex flex-col items-center justify-center py-16 text-text-muted">
            <FileText className="w-10 h-10 mb-3 opacity-30" />
            <p>暂无章节</p>
          </div>
        ) : (
          <div className="divide-y divide-white/[0.04] max-h-[520px] overflow-y-auto">
            {chapters.map((ch: Chapter, idx: number) => {
              const isReadingProgress = book.reading_progress?.chapter_id === ch.id
              return (
                <button
                  key={ch.id}
                  onClick={() => handleChapterClick(idx)}
                  className={`w-full flex items-center gap-4 px-6 py-3.5 hover:bg-accent/5 transition-colors text-left group ${
                    isReadingProgress ? 'bg-accent/5' : ''
                  }`}
                >
                  <span className="text-sm text-text-muted w-14 flex-shrink-0">第{ch.chapter_number}章</span>
                  <div className="flex-1 min-w-0">
                    <span className={`text-sm font-medium truncate block group-hover:text-accent transition-colors ${
                      isReadingProgress ? 'text-accent' : 'text-text-primary'
                    }`}>
                      {ch.title}
                    </span>
                  </div>
                  <span className="text-xs text-text-muted flex-shrink-0 w-20 text-right">
                    {ch.word_count > 0 ? `${ch.word_count} 字` : ''}
                  </span>
                  <ChevronRight className="w-4 h-4 text-text-muted opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
                </button>
              )
            })}
          </div>
        )}
      </div>

      {/* Similar Books — glass cards */}
      <div>
        <div className="flex items-center gap-2 mb-5">
          <Sparkles className="w-5 h-5 text-accent" />
          <h2 className="text-lg font-bold text-text-primary">相似推荐</h2>
        </div>

        {similarLoading ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="rounded-xl bg-bg-tertiary/50 animate-pulse h-44" />
            ))}
          </div>
        ) : similarBooks.length === 0 ? (
          <div className="glass-card p-8 text-center text-text-muted text-sm">
            暂无相似推荐
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4 stagger-in">
            {similarBooks.map((sb: RecommendBook, idx) => (
              <button
                key={sb.id}
                onClick={() => {
                  queryClient.removeQueries({ queryKey: ['book', bookId] })
                  navigate(`/books/${sb.id}`)
                  window.scrollTo(0, 0)
                }}
                className="glass-card p-4 text-left group"
                style={{ animationDelay: `${idx * 0.04}s` }}
              >
                <div
                  className="w-full h-28 rounded-xl mb-3 flex items-center justify-center relative overflow-hidden"
                  style={{ background: `linear-gradient(135deg, ${sb.gradient?.[0] || '#667eea'}, ${sb.gradient?.[1] || '#764ba2'})` }}
                >
                  <div className="absolute inset-0 bg-black/10" />
                  <BookOpen className="w-8 h-8 text-white/60 relative z-10" />
                </div>
                <h3 className="text-sm font-medium text-text-primary truncate group-hover:text-accent transition-colors">{sb.title}</h3>
                <p className="text-xs text-text-secondary mt-0.5 truncate">{sb.author || '未知作者'}</p>
                <div className="flex items-center gap-2 mt-1">
                  <p className="text-xs text-text-muted">{sb.chapter_count} 章</p>
                  {sb.reason && (
                    <span className="text-[10px] text-accent">{sb.reason}</span>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Comments Placeholder — glass */}
      <div className="glass-card">
        <div className="px-6 py-4 border-b border-border/50 flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-accent" />
          <h2 className="text-lg font-bold text-text-primary">读者评论</h2>
          <span className="text-sm text-text-muted">(功能开发中)</span>
        </div>
        <div className="p-8 flex flex-col items-center justify-center text-text-muted">
          <MessageSquarePlus className="w-12 h-12 mb-3 opacity-20" />
          <p className="text-sm">评论功能即将上线，敬请期待</p>
          <p className="text-xs mt-1">您可以在这里分享您的阅读感受</p>
        </div>
      </div>
    </div>
  )
}
