import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { BookOpen, Clock, FileText, Users, BookMarked, ChevronRight, Star, Sparkles } from 'lucide-react'
import { fetchDiscovery, type DiscoveryBook } from '@/api/discovery'
import { useUserStore } from '@/stores/userStore'
import { Spinner } from '@/components/Loading'

function BookCard({ book, size = 'md' }: { book: DiscoveryBook; size?: 'sm' | 'md' }) {
  const [c, d] = book.gradient
  const h = size === 'sm' ? 'h-44' : 'h-52'

  return (
    <Link
      to={`/books/${book.id}`}
      className="group relative rounded-xl overflow-hidden border border-card-border bg-card-bg card-hover flex-shrink-0"
      style={{ minWidth: size === 'sm' ? 160 : 200, maxWidth: size === 'sm' ? 160 : 200 }}
    >
      <div className={`${h} w-full`} style={{ background: `linear-gradient(135deg, ${c}, ${d})` }}>
        <div className="absolute inset-0 flex flex-col items-center justify-center p-3">
          <BookOpen className="w-8 h-8 text-white/80 mb-2" />
          <p className="text-white font-bold text-center text-sm leading-tight line-clamp-2">{book.title}</p>
          <p className="text-white/70 text-xs mt-1">{book.author || '佚名'}</p>
        </div>
      </div>
      <div className="p-3">
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <FileText className="w-3 h-3" />
          <span>{book.total_chapters} 章</span>
        </div>
        {book.category && (
          <span className="inline-block mt-1.5 text-[10px] px-1.5 py-0.5 rounded bg-primary-500/10 text-primary-500">
            {book.category}
          </span>
        )}
      </div>
    </Link>
  )
}

function SectionTitle({ icon: Icon, title, subtitle }: { icon: React.ElementType; title: string; subtitle?: string }) {
  return (
    <div className="flex items-center gap-3 mb-5">
      <div className="w-10 h-10 rounded-xl bg-primary-500/10 flex items-center justify-center">
        <Icon className="w-5 h-5 text-primary-500" />
      </div>
      <div>
        <h2 className="text-xl font-bold text-text-primary">{title}</h2>
        {subtitle && <p className="text-xs text-text-muted">{subtitle}</p>}
      </div>
    </div>
  )
}

export default function Discovery() {
  const { isLoggedIn } = useUserStore()
  const navigate = useNavigate()
  const [data, setData] = useState<Awaited<ReturnType<typeof fetchDiscovery>> | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDiscovery()
      .then(setData)
      .catch((e) => console.error('[Discovery] 加载失败:', e))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (isLoggedIn) navigate('/dashboard')
  }, [isLoggedIn, navigate])

  if (loading) return <Spinner />
  if (!data) return <div className="min-h-screen flex items-center justify-center text-text-muted">加载失败</div>

  const fmt = (n: number) => n >= 10000 ? `${(n / 10000).toFixed(1)}万` : n.toLocaleString()

  return (
    <div className="min-h-screen bg-content-bg">
      {/* Nav */}
      <header className="sticky top-0 z-40 bg-card-bg/80 backdrop-blur-xl border-b border-card-border">
        <div className="max-w-7xl mx-auto h-14 flex items-center justify-between px-4 sm:px-6">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-primary-500/10 flex items-center justify-center">
              <BookOpen className="w-5 h-5 text-primary-500" />
            </div>
            <span className="font-bold text-text-primary">发现</span>
          </Link>
          <div className="flex items-center gap-3">
            <Link to="/login" className="text-sm text-text-secondary hover:text-primary-500 transition-colors">
              登录
            </Link>
            <Link
              to="/login"
              className="text-sm px-4 py-1.5 rounded-lg bg-primary-500 text-white font-medium hover:bg-primary-600 transition-colors"
            >
              注册
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary-500/5 via-transparent to-info/5" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-16 sm:py-24">
          <div className="text-center mb-12">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary-500/10 text-primary-500 text-xs font-medium mb-6">
              <Sparkles className="w-3.5 h-3.5" />
              <span>探索无限好书</span>
            </div>
            <h1 className="text-3xl sm:text-5xl font-extrabold text-text-primary tracking-tight">
              发现你的下一本
              <span className="text-primary-500"> 好书</span>
            </h1>
            <p className="mt-4 text-text-secondary max-w-lg mx-auto">
              海量小说资源，沉浸式阅读体验，随时随地开启你的阅读之旅
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 max-w-2xl mx-auto">
            {[
              { label: '总书籍', value: data.stats.total_books, icon: BookMarked },
              { label: '总章节', value: fmt(data.stats.total_chapters), icon: FileText },
              { label: '总字数', value: fmt(data.stats.total_words), icon: BookOpen },
              { label: '用户数', value: fmt(data.stats.total_users), icon: Users },
            ].map(({ label, value, icon: Icon }) => (
              <div key={label} className="bg-card-bg/60 border border-card-border rounded-xl p-4 text-center">
                <Icon className="w-5 h-5 text-primary-500 mx-auto mb-1.5" />
                <div className="text-xl font-bold text-text-primary">{value}</div>
                <div className="text-xs text-text-muted">{label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 pb-20 space-y-16">
        {/* Hot Books */}
        {data.hot_books.length > 0 && (
          <section>
            <SectionTitle icon={Star} title="热门精选" subtitle="章节最多的经典作品" />
            <div className="flex gap-4 overflow-x-auto pb-2 snap-x snap-mandatory scrollbar-hide" style={{ scrollbarWidth: 'none' }}>
              {data.hot_books.map((b) => (
                <div key={b.id} className="snap-start">
                  <BookCard book={b} />
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Recent Updated */}
        {data.recent_books.length > 0 && (
          <section>
            <SectionTitle icon={Clock} title="最新更新" subtitle="最近更新的书籍" />
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.recent_books.slice(0, 6).map((b) => (
                <Link key={b.id} to={`/books/${b.id}`} className="group flex gap-4 p-4 rounded-xl border border-card-border bg-card-bg card-hover">
                  <div
                    className="w-16 h-20 rounded-lg flex-shrink-0 flex items-center justify-center"
                    style={{ background: `linear-gradient(135deg, ${b.gradient[0]}, ${b.gradient[1]})` }}
                  >
                    <BookOpen className="w-6 h-6 text-white/80" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-text-primary truncate group-hover:text-primary-500 transition-colors">
                      {b.title}
                    </h3>
                    <p className="text-xs text-text-muted mt-0.5">{b.author || '佚名'}</p>
                    {b.description && (
                      <p className="text-xs text-text-muted mt-1 line-clamp-2">{b.description}</p>
                    )}
                    <div className="flex items-center gap-3 mt-2 text-[11px] text-text-muted">
                      <span className="flex items-center gap-1"><FileText className="w-3 h-3" />{b.total_chapters}章</span>
                      {b.category && <span className="px-1.5 py-0.5 rounded bg-primary-500/10 text-primary-500">{b.category}</span>}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* Categories */}
        {data.categories.length > 0 && (
          <section>
            <SectionTitle icon={Sparkles} title="分类探索" subtitle="按分类发现好书" />
            <div className="space-y-8">
              {data.categories.map((cat) => (
                <div key={cat.category}>
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2">
                      <h3 className="text-lg font-bold text-text-primary">{cat.category}</h3>
                      <span className="text-xs text-text-muted">({cat.count} 本)</span>
                    </div>
                    <ChevronRight className="w-4 h-4 text-text-muted" />
                  </div>
                  <div className="flex gap-4 overflow-x-auto pb-2 snap-x snap-mandatory scrollbar-hide" style={{ scrollbarWidth: 'none' }}>
                    {cat.books.map((b) => (
                      <div key={b.id} className="snap-start">
                        <BookCard book={b} size="sm" />
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* All recent - compact list */}
        {data.recent_books.length > 6 && (
          <section>
            <SectionTitle icon={FileText} title="更多更新" />
            <div className="bg-card-bg border border-card-border rounded-xl divide-y divide-card-border">
              {data.recent_books.slice(6).map((b) => (
                <Link key={b.id} to={`/books/${b.id}`} className="flex items-center gap-4 p-4 hover:bg-white/[0.02] transition-colors group">
                  <div
                    className="w-10 h-10 rounded-lg flex-shrink-0 flex items-center justify-center"
                    style={{ background: `linear-gradient(135deg, ${b.gradient[0]}, ${b.gradient[1]})` }}
                  >
                    <BookOpen className="w-4 h-4 text-white/80" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-text-primary truncate group-hover:text-primary-500 transition-colors">
                      {b.title}
                    </p>
                    <p className="text-xs text-text-muted">{b.author || '佚名'}</p>
                  </div>
                  <div className="text-xs text-text-muted flex-shrink-0">
                    {b.total_chapters} 章
                  </div>
                  <ChevronRight className="w-4 h-4 text-text-muted flex-shrink-0" />
                </Link>
              ))}
            </div>
          </section>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-card-border py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 text-center text-xs text-text-muted">
          小说阅读器 · 发现好书，享受阅读
        </div>
      </footer>
    </div>
  )
}
