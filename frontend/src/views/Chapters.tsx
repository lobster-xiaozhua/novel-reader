import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useLocation } from 'react-router-dom'
import { FileText, BookOpen, ArrowLeft } from 'lucide-react'
import { fetchBooks } from '@/api/books'
import { fetchChapters, fetchChapterContent } from '@/api/books'
import { Chapter, Book } from '@/types'
import NovelReader from '@/components/NovelReader'
import { Spinner } from '@/components/Loading'

export default function Chapters() {
  const location = useLocation()
  const initialBookId = (location.state as { bookId?: number })?.bookId || null
  const [selectedBookId, setSelectedBookId] = useState<number | null>(initialBookId)
  const [readingChapterIdx, setReadingChapterIdx] = useState<number | null>(null)

  const { data: booksData } = useQuery({
    queryKey: ['books'],
    queryFn: () => fetchBooks(),
  })

  const { data: chaptersData, isLoading: chaptersLoading } = useQuery({
    queryKey: ['chapters', selectedBookId],
    queryFn: () => fetchChapters(selectedBookId!),
    enabled: !!selectedBookId,
  })

  const chapters = chaptersData || []
  const readingChapter = readingChapterIdx !== null ? chapters[readingChapterIdx] : null

  const { data: chapterContent, isLoading: contentLoading } = useQuery({
    queryKey: ['chapter-content', selectedBookId, readingChapter?.id],
    queryFn: () => fetchChapterContent(selectedBookId!, readingChapter!.id),
    enabled: !!selectedBookId && !!readingChapter,
  })

  const books = booksData?.items || []

  if (readingChapter) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setReadingChapterIdx(null)}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-card-bg border border-card-border text-sm text-text-secondary hover:text-text-primary transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            返回目录
          </button>
          <h2 className="text-lg font-semibold text-text-primary">{readingChapter.title}</h2>
        </div>
        <div className="bg-card-bg border border-card-border rounded-xl p-8 max-w-4xl mx-auto">
          {contentLoading ? (
            <Spinner />
          ) : (
            <NovelReader
              content={chapterContent?.content || ''}
              hasPrev={readingChapterIdx! > 0}
              hasNext={readingChapterIdx! < chapters.length - 1}
              onPrev={() => setReadingChapterIdx((i) => (i !== null && i > 0 ? i - 1 : i))}
              onNext={() => setReadingChapterIdx((i) => (i !== null && i < chapters.length - 1 ? i + 1 : i))}
            />
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-bold text-text-primary">章节管理</h2>
      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-3">
          <div className="bg-card-bg border border-card-border rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-white/[0.06]">
              <h3 className="text-sm font-medium text-text-secondary">选择书籍</h3>
            </div>
            <div className="max-h-[600px] overflow-y-auto">
              {books.map((book: Book) => (
                <button
                  key={book.id}
                  onClick={() => { setSelectedBookId(book.id); setReadingChapterIdx(null) }}
                  className={`w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-white/[0.02] transition-colors ${
                    selectedBookId === book.id ? 'bg-primary-500/10 border-l-2 border-primary-500' : ''
                  }`}
                >
                  <BookOpen className="w-4 h-4 text-text-muted flex-shrink-0" />
                  <div className="min-w-0">
                    <div className="text-sm text-text-primary truncate">{book.title}</div>
                    <div className="text-xs text-text-muted">{book.chapter_count} 章</div>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="col-span-9">
          <div className="bg-card-bg border border-card-border rounded-xl overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  <th className="px-6 py-4 text-left text-sm font-medium text-text-secondary">章节号</th>
                  <th className="px-6 py-4 text-left text-sm font-medium text-text-secondary">标题</th>
                  <th className="px-6 py-4 text-left text-sm font-medium text-text-secondary">字数</th>
                  <th className="px-6 py-4 text-right text-sm font-medium text-text-secondary">操作</th>
                </tr>
              </thead>
              <tbody>
                {!selectedBookId ? (
                  <tr><td colSpan={4} className="text-center py-20 text-text-muted">请先选择书籍</td></tr>
                ) : chaptersLoading ? (
                  <tr><td colSpan={4}><Spinner /></td></tr>
                ) : chapters.length === 0 ? (
                  <tr><td colSpan={4} className="text-center py-20 text-text-muted">暂无章节</td></tr>
                ) : (
                  chapters.map((ch: Chapter, idx: number) => (
                    <tr key={ch.id} className="border-b border-white/[0.06] hover:bg-white/[0.02] transition-colors cursor-pointer" onClick={() => setReadingChapterIdx(idx)}>
                      <td className="px-6 py-4"><span className="text-sm text-text-muted">第{ch.chapter_number}章</span></td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-2">
                          <FileText className="w-4 h-4 text-text-muted" />
                          <span className="text-sm text-text-primary">{ch.title}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-text-secondary">{ch.word_count > 0 ? `${ch.word_count} 字` : '-'}</td>
                      <td className="px-6 py-4 text-right">
                        <span className="text-sm text-primary-500">阅读 →</span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
