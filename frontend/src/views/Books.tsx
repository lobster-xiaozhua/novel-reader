import { useState, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { usePageTitle } from '@/hooks/usePageTitle'
import PageTitle from '@/components/PageTitle'
import { BookOpen, Search, Eye, Tag, Upload, Loader2, Heart } from 'lucide-react'
import { fetchBooks, importBooks } from '@/api/books'
import { toggleFavorite } from '@/api/favorites'
import { Book } from '@/types'
import { useToast } from '@/components/Toast'
import { Spinner } from '@/components/Loading'

export default function Books() {
  usePageTitle('书籍列表')
  const [searchParams] = useSearchParams()
  const initialSearch = searchParams.get('search') || ''
  const [search, setSearch] = useState(initialSearch)
  const [importing, setImporting] = useState(false)
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const toast = useToast()
  const fileRef = useRef<HTMLInputElement>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['books', search],
    queryFn: () => fetchBooks({ search: search || undefined }),
  })

  const books = data?.items || []

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files?.length) return
    setImporting(true)
    try {
      const result = await importBooks(Array.from(files))
      if (result.success) {
        toast.success(`成功导入 ${result.imported} 本书籍`)
        if (result.errors.length > 0) {
          result.errors.forEach((err) => toast.warning(err))
        }
        queryClient.invalidateQueries({ queryKey: ['books'] })
      }
    } catch {
      toast.error('导入失败，请重试')
    } finally {
      setImporting(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const handleToggleFav = async (e: React.MouseEvent, bookId: number) => {
    e.stopPropagation()
    try {
      const res = await toggleFavorite(bookId)
      toast.success(res.message)
      queryClient.invalidateQueries({ queryKey: ['books'] })
    } catch {
      toast.error('操作失败')
    }
  }

  return (
    <div className="space-y-6">
      <PageTitle title="书籍列表" />
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-text-primary">书籍管理</h2>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
            <input
              type="text"
              placeholder="搜索书籍..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-64 h-10 pl-9 pr-4 rounded-lg glass-input text-sm text-text-primary placeholder:text-text-muted"
            />
          </div>
          <input ref={fileRef} type="file" accept=".txt" multiple className="hidden" onChange={handleImport} />
          <button
            onClick={() => fileRef.current?.click()}
            disabled={importing}
            className="btn btn--primary btn--md"
          >
            {importing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
            导入书籍
          </button>
        </div>
      </div>

      {isLoading ? (
        <Spinner />
      ) : books.length === 0 ? (
        <div className="glass-card p-16 flex flex-col items-center justify-center text-text-muted">
          <BookOpen className="w-12 h-12 mb-3 opacity-30" />
          <p>{search ? '未找到匹配书籍' : '暂无书籍'}</p>
          <button
            onClick={() => fileRef.current?.click()}
            disabled={importing}
            className="btn btn--secondary btn--md mt-4"
          >
            {importing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
            导入书籍
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 stagger-in">
          {books.map((book: Book, idx) => (
            <div
              key={book.id}
              className="glass-card glass-card--shimmer"
              style={{ animationDelay: `${idx * 0.04}s` }}
            >
              {/* Shimmer layer */}
              <div className="shimmer-layer" />

              {/* Gradient top bar */}
              <div
                className="h-1"
                style={{
                  background: `linear-gradient(135deg, ${book.gradient?.[0] || '#667eea'}, ${book.gradient?.[1] || '#764ba2'})`,
                }}
              />

              <button
                onClick={() => navigate(`/chapters`, { state: { bookId: book.id } })}
                className="w-full p-5 text-left group"
              >
                <div className="flex items-start gap-4">
                  <div
                    className="w-14 h-14 rounded-xl flex items-center justify-center flex-shrink-0 group-hover:scale-105 transition-transform"
                    style={{ background: `linear-gradient(135deg, ${book.gradient?.[0] || '#667eea'}, ${book.gradient?.[1] || '#764ba2'})` }}
                  >
                    <BookOpen className="w-7 h-7 text-white/80" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-text-primary truncate group-hover:text-accent transition-colors">{book.title}</h3>
                    <p className="text-sm text-text-secondary mt-1">{book.author || '未知作者'}</p>
                    <div className="flex items-center gap-2 mt-2">
                      {book.category && (
                        <span className="px-2 py-0.5 rounded-md bg-accent/10 text-accent text-xs">
                          {book.category}
                        </span>
                      )}
                      <span className="text-xs text-text-muted">{book.chapter_count} 章</span>
                    </div>
                  </div>
                </div>

                {book.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-4">
                    {book.tags.map((tag) => (
                      <span key={tag.id} className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-bg-tertiary/50 text-text-secondary text-xs border border-border/50">
                        <Tag className="w-3 h-3" />
                        {tag.name}
                      </span>
                    ))}
                  </div>
                )}
              </button>

              <div className="flex items-center justify-between px-5 pb-4 pt-3 border-t border-border/50">
                <span className="text-xs text-text-muted">
                  {new Date(book.created_at).toLocaleDateString('zh-CN')}
                </span>
                <div className="flex items-center gap-2">
                  {/* Tertiary: Favorite icon button */}
                  <button
                    onClick={(e) => handleToggleFav(e, book.id)}
                    className="btn btn--tertiary btn--sm"
                    title="收藏"
                  >
                    <Heart className="w-4 h-4" />
                  </button>
                  {/* Secondary: View chapters button */}
                  <button
                    onClick={() => navigate(`/chapters`, { state: { bookId: book.id } })}
                    className="btn btn--secondary btn--sm"
                  >
                    <Eye className="w-4 h-4" />
                    查看
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
