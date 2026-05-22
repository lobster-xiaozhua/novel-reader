import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { FileText, Search, BookOpen, Eye } from 'lucide-react'
import { fetchBooks, fetchChapters } from '@/api/books'
import { Book, Chapter } from '@/types'

export default function Chapters() {
  const [selectedBook, setSelectedBook] = useState<number | null>(null)
  const [search, setSearch] = useState('')

  const { data: booksData, isLoading: booksLoading } = useQuery({
    queryKey: ['books'],
    queryFn: () => fetchBooks(),
  })

  const { data: chaptersData, isLoading: chaptersLoading } = useQuery({
    queryKey: ['chapters', selectedBook],
    queryFn: () => fetchChapters(selectedBook!),
    enabled: !!selectedBook,
  })

  const books = booksData?.items || []
  const chapters = chaptersData || []
  const filteredBooks = search
    ? books.filter((b: Book) => b.title.toLowerCase().includes(search.toLowerCase()))
    : books

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold text-text-primary">章节管理</h2>
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
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Books List */}
        <div className="lg:col-span-1 bg-card-bg border border-card-border rounded-xl overflow-hidden">
          <div className="px-4 py-3 border-b border-white/[0.06] font-medium text-text-primary">选择书籍</div>
          <div className="max-h-[600px] overflow-y-auto">
            {booksLoading ? (
              <div className="text-center py-10 text-text-muted">加载中...</div>
            ) : filteredBooks.length === 0 ? (
              <div className="text-center py-10 text-text-muted">暂无书籍</div>
            ) : (
              filteredBooks.map((book: Book) => (
                <button
                  key={book.id}
                  onClick={() => setSelectedBook(book.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-colors border-b border-white/[0.04] last:border-0
                    ${selectedBook === book.id ? 'bg-primary-500/10 text-primary-500' : 'text-text-secondary hover:bg-white/[0.02]'}`}
                >
                  <BookOpen className="w-4 h-4 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">{book.title}</div>
                    <div className="text-xs text-text-muted">{book.chapter_count} 章</div>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Chapters List */}
        <div className="lg:col-span-2 bg-card-bg border border-card-border rounded-xl overflow-hidden">
          <div className="px-6 py-3 border-b border-white/[0.06] font-medium text-text-primary">
            {selectedBook ? '章节列表' : '请选择书籍'}
          </div>
          {!selectedBook ? (
            <div className="flex flex-col items-center justify-center py-20 text-text-muted">
              <FileText className="w-12 h-12 mb-3 opacity-30" />
              <p>从左侧选择一本书籍查看章节</p>
            </div>
          ) : chaptersLoading ? (
            <div className="text-center py-20 text-text-muted">加载中...</div>
          ) : chapters.length === 0 ? (
            <div className="text-center py-20 text-text-muted">暂无章节</div>
          ) : (
            <div className="max-h-[600px] overflow-y-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/[0.06]">
                    <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary">序号</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary">标题</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary">字数</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-text-secondary">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {chapters.map((chapter: Chapter) => (
                    <tr key={chapter.id} className="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors">
                      <td className="px-6 py-3 text-sm text-text-muted">{chapter.chapter_number}</td>
                      <td className="px-6 py-3 text-sm text-text-primary">{chapter.title}</td>
                      <td className="px-6 py-3 text-sm text-text-secondary">{chapter.word_count?.toLocaleString() || 0}</td>
                      <td className="px-6 py-3">
                        <button className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-primary-500/10 text-primary-500 text-xs hover:bg-primary-500/20 transition-colors">
                          <Eye className="w-3.5 h-3.5" />
                          阅读
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
