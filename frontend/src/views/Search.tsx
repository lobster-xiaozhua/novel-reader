import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Search, BookOpen, User, AlertCircle } from 'lucide-react'
import { fetchSearch } from '@/api/books'
import { Spinner } from '@/components/Loading'

const FILTER_TABS = [
  { key: 'all', label: '全部', icon: Search },
  { key: 'books', label: '书籍', icon: BookOpen },
  { key: 'authors', label: '作者', icon: User },
]

function highlightText(text: string, query: string): React.ReactNode {
  if (!query || !text) return text
  const idx = text.toLowerCase().indexOf(query.toLowerCase())
  if (idx === -1) return text
  return (
    <>
      {text.slice(0, idx)}
      <mark className="bg-accent/30 text-accent rounded px-0.5">{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length)}
    </>
  )
}

function ResultCard({ book, query }: { book: { id: number; title: string; author: string; category: string }; query: string }) {
  const navigate = useNavigate()
  return (
    <button
      onClick={() => navigate(`/books/${book.id}`)}
      className="flex items-center gap-4 p-4 rounded-xl bg-bg-tertiary/50 border border-border hover:border-accent/30 hover:bg-accent/5 transition-all text-left group"
    >
      <div
        className="w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0"
        style={{ background: 'linear-gradient(135deg, #667eea, #764ba2)' }}
      >
        <BookOpen className="w-5 h-5 text-white/80" />
      </div>
      <div className="flex-1 min-w-0">
        <h3 className="text-sm font-semibold text-text-primary truncate group-hover:text-accent transition-colors">
          {highlightText(book.title, query)}
        </h3>
        <p className="text-xs text-text-secondary mt-0.5">
          {highlightText(book.author || '未知作者', query)}
        </p>
        {book.category && (
          <span className="inline-block mt-1 px-1.5 py-0.5 rounded bg-accent/10 text-accent text-xs">
            {book.category}
          </span>
        )}
      </div>
    </button>
  )
}

export default function SearchPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const q = searchParams.get('q') || ''
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    if (!q) return
    setFilter('all')
  }, [q])

  const { data, isLoading } = useQuery({
    queryKey: ['search', q],
    queryFn: () => fetchSearch(q),
    enabled: q.length > 0,
    staleTime: 2 * 60 * 1000,
  })

  const results = data?.results ?? []
  const total = data?.total ?? 0

  const filteredResults = filter === 'all'
    ? results
    : filter === 'authors'
      ? results.filter((b) => b.author?.toLowerCase().includes(q.toLowerCase()))
      : results

  if (!q) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-text-muted">
        <Search className="w-12 h-12 mb-3 opacity-30" />
        <p className="text-lg">请输入搜索关键词</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-text-primary">搜索结果</h2>
        <p className="text-sm text-text-muted mt-1">
          {isLoading ? '搜索中...' : `找到 ${total} 本书籍`}
          {q && <>，关键词：<span className="text-accent">"{q}"</span></>}
        </p>
      </div>

      {total > 0 && (
        <div className="flex gap-2">
          {FILTER_TABS.map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.key}
                onClick={() => setFilter(tab.key)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  filter === tab.key
                    ? 'bg-accent/10 text-accent border border-accent/20'
                    : 'text-text-muted hover:text-text-secondary border border-transparent'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            )
          })}
        </div>
      )}

      {isLoading ? (
        <Spinner />
      ) : filteredResults.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-text-muted">
          <AlertCircle className="w-10 h-10 mb-3 opacity-30" />
          <p>{total === 0 ? '未找到相关书籍' : '当前筛选条件下无结果'}</p>
          <button
            onClick={() => navigate('/')}
            className="mt-4 px-4 py-2 rounded-lg bg-accent/10 text-accent text-sm hover:bg-accent/20 transition-colors"
          >
            返回首页
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {filteredResults.map((book) => (
            <ResultCard key={book.id} book={book} query={q} />
          ))}
        </div>
      )}
    </div>
  )
}
