import { useState, useRef } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { BookOpen, Search, Eye, Tag, Upload, Loader2, Heart } from 'lucide-react'
import { bookApi, favoriteApi } from '@/api'
import { Book } from '@/types'
import { useToast } from '@/components/Toast'
import { Spinner } from '@/components/Loading'

export default function Books() {
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
    queryFn: () => bookApi.list({ search: search || undefined }),
  })

  const books = data?.items || []

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files?.length) return
    setImporting(true)
    try {
      const result = await bookApi.importBooks(Array.from(files))
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
      const res = await favoriteApi.toggle(bookId)
      toast.success(res.message)
      queryClient.invalidateQueries({ queryKey: ['books'] })
    } catch {
      toast.error('操作失败')
    }
  }

  return (
    <div className="space-y-6">
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
              className="w-64 h-10 pl-9 pr-4 rounded-lg bg-card-bg border border-card-border text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-500/50 transition-colors"
            />
          </div>
          <input ref={fileRef} type="file" accept=".txt" multiple className="hidden" onChange={handleImport} />
          <button
            onClick={() => fileRef.current?.click()}
            disabled={importing}
            className="flex items-center gap-2 px-4 h-10 rounded-lg bg-primary-500 text-white text-sm font-medium hover:bg-primary-600 transition-colors disabled:opacity-50"
          >
            {importing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />}
            导入书籍
          </button>
        </div>
      </div>

      {isLoading ? (
        <Spinner />
      ) : books.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-text-muted">
          <BookOpen className="w-12 h-12 mb-3 opacity-30" />
          <p>{search ? '未找到匹配的书籍' : '暂无书籍，点击导入按钮添加'}</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {books.map((book: Book) => (
            <div key={book.id} className="bg-card-bg border border-card-border rounded-xl p-5 card-hover">
              <div
                className="w-full h-3 rounded-t-xl -mt-5 -mx-5 mb-4"
                style={{
                  background: `linear-gradient(135deg, ${book.gradient?.[0] || '#667eea'}, ${book.gradient?.[1] || '#764ba2'})`,
                  width: 'calc(100% + 40px)',
                }}
              />
              <div className="flex items-start gap-4 -mt-1">
                <div className="w-14 h-14 rounded-xl bg-primary-500/10 flex items-center justify-center flex-shrink-0">
                  <BookOpen className="w-7 h-7 text-primary-500" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-text-primary truncate">{book.title}</h3>
                  <p className="text-sm text-text-secondary mt-1">{book.author || '未知作者'}</p>
                  <div className="flex items-center gap-2 mt-2">
                    {book.category && (
                      <span className="px-2 py-0.5 rounded-md bg-primary-500/10 text-primary-500 text-xs">
                        {book.category}
                      </span>
                    )}
                    <span className="text-xs text-text-muted">{book.chapter_count} 章</span>
                  </div>
                </div>
              </div>

              {book.tags.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-3">
                  {book.tags.map((tag) => (
                    <span key={tag.id} className="flex items-center gap-1 px-2 py-0.5 rounded-md bg-white/5 text-text-secondary text-xs">
                      <Tag className="w-3 h-3" />
                      {tag.name}
                    </span>
                  ))}
                </div>
              )}

              <div className="flex items-center justify-between mt-4 pt-3 border-t border-white/[0.06]">
                <span className="text-xs text-text-muted">
                  {new Date(book.created_at).toLocaleDateString('zh-CN')}
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={(e) => handleToggleFav(e, book.id)}
                    className="p-1.5 rounded-lg hover:bg-primary-500/10 text-text-muted hover:text-primary-500 transition-colors"
                    title="收藏"
                  >
                    <Heart className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => navigate(`/chapters`, { state: { bookId: book.id } })}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-primary-500/10 text-primary-500 text-sm hover:bg-primary-500/20 transition-colors"
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
