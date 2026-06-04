import { useState, useCallback, useMemo } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Search, BookOpen, User, AlertCircle,
  FileText, ChevronRight, Cpu, Zap, ArrowLeft
} from 'lucide-react'
import { fetchSearch, fetchAdvancedSearch } from '@/api/books'
import { AdvancedSearchResult } from '@/types'
import { Spinner } from '@/components/Loading'

const FILTER_TABS = [
  { key: 'all', label: '全部', icon: Search },
  { key: 'books', label: '书籍', icon: BookOpen },
  { key: 'chapters', label: '章节', icon: FileText },
  { key: 'authors', label: '作者', icon: User },
]

const SEARCH_MODES = [
  { key: 'basic', label: '快速', icon: Zap },
  { key: 'advanced', label: '深度', icon: Cpu },
] as const

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

function BasicResultCard({ book, query }: { book: { id: number; title: string; author: string; category: string }; query: string }) {
  const navigate = useNavigate()
  return (
    <button
      onClick={() => navigate(`/books/${book.id}`)}
      className="flex items-center gap-4 p-4 rounded-xl bg-bg-secondary/50 backdrop-blur-sm border border-border hover:border-accent/30 hover:bg-accent/5 transition-all text-left group"
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
      <ChevronRight className="w-4 h-4 text-text-muted opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
    </button>
  )
}

function AdvancedResultCard({ result, query }: { result: AdvancedSearchResult; query: string }) {
  const navigate = useNavigate()
  return (
    <div className="rounded-xl bg-bg-secondary/50 backdrop-blur-sm border border-border overflow-hidden hover:border-accent/30 transition-all">
      <button
        onClick={() => navigate(`/books/${result.book_id}`)}
        className="w-full flex items-center gap-4 p-4 text-left group"
      >
        <div
          className="w-14 h-14 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ background: 'linear-gradient(135deg, #667eea, #764ba2)' }}
        >
          <BookOpen className="w-6 h-6 text-white/80" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-text-primary truncate group-hover:text-accent transition-colors">
              {highlightText(result.title, query)}
            </h3>
            <span className="px-1.5 py-0.5 rounded-full bg-accent/10 text-accent text-[10px] font-bold">
              {result.total_score}分
            </span>
          </div>
          <p className="text-xs text-text-secondary mt-0.5">
            {result.author || '未知作者'} {result.category && `· ${result.category}`}
          </p>
          <div className="flex gap-1.5 mt-1.5 flex-wrap">
            {result.match_reasons.map((reason, i) => (
              <span key={i} className="px-1.5 py-0.5 rounded-full bg-bg-tertiary text-text-muted text-[10px] border border-border/50">
                {reason}
              </span>
            ))}
          </div>
        </div>
        <ChevronRight className="w-4 h-4 text-text-muted opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
      </button>

      {result.matched_chapters.length > 0 && (
        <div className="border-t border-border/50 px-4 py-3 space-y-2">
          {result.matched_chapters.slice(0, 2).map((ch) => (
            <button
              key={ch.id}
              onClick={() => navigate(`/chapters?book=${result.book_id}&chapter=${ch.chapter_number}`)}
              className="w-full flex items-start gap-2 text-left group/ch hover:bg-accent/5 rounded-lg p-2 -mx-1 transition-colors"
            >
              <FileText className="w-3.5 h-3.5 text-text-muted mt-0.5 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-text-primary group-hover/ch:text-accent transition-colors truncate">
                  第{ch.chapter_number}章 {ch.title}
                </p>
                {ch.content_preview && (
                  <p className="text-[11px] text-text-muted mt-0.5 line-clamp-1">
                    {ch.content_preview}
                  </p>
                )}
              </div>
              <span className="text-[10px] text-text-muted flex-shrink-0">{ch.score}分</span>
            </button>
          ))}
          {result.total_matches > 2 && (
            <button
              onClick={() => navigate(`/books/${result.book_id}`)}
              className="text-[11px] text-accent hover:text-accent/80 transition-colors pl-5"
            >
              还有 {result.total_matches - 2} 个匹配章节 →
            </button>
          )}
        </div>
      )}
    </div>
  )
}

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const q = searchParams.get('q') || ''
  const [inputVal, setInputVal] = useState(q)
  const [filter, setFilter] = useState('all')
  const [searchMode, setSearchMode] = useState<'basic' | 'advanced'>('basic')

  const { data: basicData, isLoading: basicLoading } = useQuery({
    queryKey: ['search', q],
    queryFn: () => fetchSearch(q),
    enabled: q.length > 0 && searchMode === 'basic',
    staleTime: 2 * 60 * 1000,
  })

  const { data: advData, isLoading: advLoading } = useQuery({
    queryKey: ['search-advanced', q],
    queryFn: () => fetchAdvancedSearch(q, 30),
    enabled: q.length >= 2 && searchMode === 'advanced',
    staleTime: 2 * 60 * 1000,
  })

  const basicResults = useMemo(() => basicData?.results ?? [], [basicData])
  const basicTotal = basicData?.total ?? 0
  const advResults = useMemo(() => advData?.data ?? [], [advData])
  const advTotal = advData?.pagination?.total ?? 0
  const searchTimeMs = advData?.search_time_ms ?? 0

  const isLoading = searchMode === 'basic' ? basicLoading : advLoading
  const total = searchMode === 'basic' ? basicTotal : advTotal

  const filteredResults = useMemo(() => {
    if (searchMode === 'advanced') {
      if (filter === 'chapters') return advResults.filter((r: AdvancedSearchResult) => r.matched_chapters.length > 0)
      if (filter === 'authors') return advResults.filter((r: AdvancedSearchResult) => r.author?.toLowerCase().includes(q.toLowerCase()))
      return advResults
    }
    if (filter === 'authors') return basicResults.filter((b: { author?: string }) => b.author?.toLowerCase().includes(q.toLowerCase()))
    return basicResults
  }, [searchMode, filter, advResults, basicResults, q])

  const handleSearch = useCallback((e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = inputVal.trim()
    if (!trimmed) return
    setSearchParams({ q: trimmed })
  }, [inputVal, setSearchParams])

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
        <div className="flex items-center gap-3 mb-4">
          <button
            onClick={() => navigate('/')}
            className="w-8 h-8 rounded-lg bg-bg-secondary border border-border flex items-center justify-center hover:bg-accent/10 transition-colors"
          >
            <ArrowLeft className="w-4 h-4 text-text-secondary" />
          </button>
          <form onSubmit={handleSearch} className="flex-1 relative group">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted group-focus-within:text-accent transition-colors" />
            <input
              type="text"
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              placeholder="搜索书名、作者、标签、章节内容..."
              className="w-full h-10 pl-9 pr-20 rounded-xl bg-bg-secondary border border-border text-text-primary placeholder:text-text-muted text-sm focus:outline-none focus:border-accent/50 focus:ring-2 focus:ring-accent/20 transition-all"
            />
            <div className="absolute right-2 top-1/2 -translate-y-1/2 flex gap-1">
              {SEARCH_MODES.map((mode) => {
                const Icon = mode.icon
                return (
                  <button
                    key={mode.key}
                    type="button"
                    onClick={() => setSearchMode(mode.key as 'basic' | 'advanced')}
                    className={`flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-semibold transition-all ${
                      searchMode === mode.key
                        ? 'bg-accent text-white'
                        : 'text-text-muted hover:text-text-secondary'
                    }`}
                  >
                    <Icon className="w-3 h-3" />
                    {mode.label}
                  </button>
                )
              })}
            </div>
          </form>
        </div>

        <div className="flex items-center justify-between">
          <p className="text-sm text-text-muted">
            {isLoading ? '搜索中...' : (
              <>
                找到 <span className="text-accent font-semibold">{total}</span> 个结果
                {searchMode === 'advanced' && searchTimeMs > 0 && (
                  <span className="ml-2 text-text-muted">· {searchTimeMs.toFixed(0)}ms</span>
                )}
              </>
            )}
            ，关键词：<span className="text-accent">"{q}"</span>
          </p>
        </div>
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
      ) : searchMode === 'advanced' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {(filteredResults as AdvancedSearchResult[]).map((result) => (
            <AdvancedResultCard key={result.id} result={result} query={q} />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {(filteredResults as Array<{ id: number; title: string; author: string; category: string }>).map((book) => (
            <BasicResultCard key={book.id} book={book} query={q} />
          ))}
        </div>
      )}
    </div>
  )
}
