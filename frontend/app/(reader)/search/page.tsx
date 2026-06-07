'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Search, BookOpen, Clock, X, TrendingUp, ChevronRight, Hash, Zap, Loader2 } from 'lucide-react';
import { api } from '@/shared/lib/api';
import { SkeletonSearch } from '@/shared/components/Skeleton';
import type { ApiResponse } from '@/shared/types';

// ──── Advanced Search Types ────
interface MatchedChapter {
  id: number;
  title: string;
  score: number;
  content_preview: string;
  chapter_number: number;
  total_occurrences: number;
}

interface SearchResultItem {
  id: number;
  book_id: number;
  title: string;
  author: string;
  category: string;
  description: string;
  tags: string[];
  total_score: number;
  matched_chapters: MatchedChapter[];
  total_matches: number;
  match_reasons: string[];
}

interface SearchPagination {
  page: number;
  per_page: number;
  total: number;
  has_next: boolean;
}

interface AdvancedSearchData {
  data: SearchResultItem[];
  pagination: SearchPagination;
  search_time_ms: number;
}

// ──── Match Reason Badge Colors ────
const REASON_BADGES: Record<string, string> = {
  '书名匹配': 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  '作者匹配': 'bg-green-500/20 text-green-400 border-green-500/30',
  '拼音匹配': 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  '简介匹配': 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  '标签匹配': 'bg-pink-500/20 text-pink-400 border-pink-500/30',
  '章节匹配': 'bg-teal-500/20 text-teal-400 border-teal-500/30',
};
const DEFAULT_BADGE = 'bg-gray-500/20 text-gray-400 border-gray-500/30';

// ──── Gradient Pairs for Cover Fallback ────
const GRADIENT_PAIRS: [string, string][] = [
  ['#667eea', '#764ba2'],
  ['#f093fb', '#f5576c'],
  ['#4facfe', '#00f2fe'],
  ['#43e97b', '#38f9d7'],
  ['#fa709a', '#fee140'],
  ['#a18cd1', '#fbc2eb'],
  ['#fccb90', '#d57eeb'],
  ['#e0c3fc', '#8ec5fc'],
  ['#f5576c', '#ff6f00'],
  ['#667eea', '#38f9d7'],
];

function getGradient(title: string): [string, string] {
  let hash = 0;
  for (let i = 0; i < title.length; i++) {
    hash = title.charCodeAt(i) + ((hash << 5) - hash);
  }
  return GRADIENT_PAIRS[Math.abs(hash) % GRADIENT_PAIRS.length];
}

// ──── Search History Hook ────
function useSearchHistory() {
  const [history, setHistory] = useState<string[]>(() => {
    if (typeof window !== 'undefined') {
      try {
        return JSON.parse(localStorage.getItem('search-history') || '[]');
      } catch {
        return [];
      }
    }
    return [];
  });

  const addHistory = useCallback((query: string) => {
    setHistory(prev => {
      const updated = [query, ...prev.filter(q => q !== query)].slice(0, 20);
      if (typeof window !== 'undefined') {
        localStorage.setItem('search-history', JSON.stringify(updated));
      }
      return updated;
    });
  }, []);

  const removeHistory = useCallback((query: string) => {
    setHistory(prev => {
      const updated = prev.filter(q => q !== query);
      if (typeof window !== 'undefined') {
        localStorage.setItem('search-history', JSON.stringify(updated));
      }
      return updated;
    });
  }, []);

  const clearHistory = useCallback(() => {
    setHistory([]);
    if (typeof window !== 'undefined') {
      localStorage.removeItem('search-history');
    }
  }, []);

  return { history, addHistory, removeHistory, clearHistory };
}

// ──── Page Component ────
export default function SearchPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get('q') || '';
  const [query, setQuery] = useState(initialQuery);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [pagination, setPagination] = useState<SearchPagination | null>(null);
  const [searchTime, setSearchTime] = useState(0);
  const [hasSearched, setHasSearched] = useState(false);
  const [searchError, setSearchError] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const { history, addHistory, removeHistory, clearHistory } = useSearchHistory();

  // ── Suggestions ──
  const suggestions = query.length > 0
    ? history.filter(h => h.toLowerCase().includes(query.toLowerCase()) && h !== query).slice(0, 5)
    : [];

  const hotSearches = [
    '斗破', '斗破苍', '三', '凡人', '仙', '遮天', '完', '星', '吞',
  ].slice(0, 10);

  // ── Core search logic ──
  const doSearch = useCallback(async (searchQuery: string, page: number = 1) => {
    if (!searchQuery.trim()) return;

    if (page === 1) {
      setIsSearching(true);
      setSearchError('');
    } else {
      setIsLoadingMore(true);
    }

    try {
      const res = await api.get<ApiResponse<AdvancedSearchData>>(
        `/search/advanced?q=${encodeURIComponent(searchQuery)}&limit=20&page=${page}`,
      );
      const { data, pagination: pag, search_time_ms } = res.data;

      if (page === 1) {
        setResults(data);
      } else {
        setResults(prev => [...prev, ...data]);
      }
      setPagination(pag);
      setSearchTime(search_time_ms);
      setHasSearched(true);
    } catch (err) {
      console.error('[搜索] 请求失败:', err);
      if (page === 1) {
        setResults([]);
        setPagination(null);
        setSearchError(err instanceof Error ? err.message : '搜索请求失败，请稍后重试');
      }
    } finally {
      setIsSearching(false);
      setIsLoadingMore(false);
    }
  }, []);

  const handleSearch = useCallback((searchQuery?: string) => {
    const q = (searchQuery || query).trim();
    if (!q) return;

    addHistory(q);
    setQuery(q);
    router.push(`/search?q=${encodeURIComponent(q)}`);
    setShowSuggestions(false);
    doSearch(q, 1);
  }, [query, addHistory, router, doSearch]);

  const handleLoadMore = useCallback(() => {
    if (!pagination?.has_next || !query.trim()) return;
    doSearch(query.trim(), pagination.page + 1);
  }, [pagination, query, doSearch]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
    }
  };

  // ── Auto-search on mount if URL has query ──
  useEffect(() => {
    if (initialQuery) {
      handleSearch(initialQuery);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-0 pb-20">
      {/* ═══════ Search Input ═══════ */}
      <div className="relative mb-6">
        <div className="flex items-center gap-2 glass-card p-2">
          <Search size={20} className="text-[var(--text-muted)] flex-shrink-0" />
          <input
            ref={inputRef}
            type="text"
            className="flex-1 outline-none bg-transparent text-sm sm:text-base min-w-0 placeholder:text-[var(--text-muted)]"
            placeholder="搜索书名、作者、拼音首字母..."
            value={query}
            onChange={e => {
              setQuery(e.target.value);
              setShowSuggestions(true);
            }}
            onFocus={() => setShowSuggestions(true)}
            onKeyDown={handleKeyDown}
          />
          {query && (
            <button
              className="p-1 rounded-full hover:bg-[var(--bg-primary)] flex-shrink-0"
              onClick={() => {
                setQuery('');
                inputRef.current?.focus();
              }}
              aria-label="清除搜索"
            >
              <X size={16} className="text-[var(--text-muted)]" />
            </button>
          )}
          <button
            className="btn-primary px-4 py-1.5 text-sm flex-shrink-0"
            onClick={() => handleSearch()}
            disabled={isSearching}
          >
            {isSearching ? '搜索中...' : '搜索'}
          </button>
        </div>

        {/* ═══════ Suggestions Dropdown ═══════ */}
        {showSuggestions && (query || history.length > 0) && (
          <div className="absolute top-full left-0 right-0 mt-2 glass-card p-3 z-10">
            {suggestions.length > 0 && (
              <div className="mb-3">
                <p className="text-xs mb-2 text-[var(--text-muted)]">搜索建议</p>
                {suggestions.map((s, i) => (
                  <button
                    key={i}
                    className="w-full text-left px-2 py-1.5 rounded text-sm hover:bg-[var(--bg-primary)] flex items-center gap-2"
                    onClick={() => { setQuery(s); handleSearch(s); }}
                  >
                    <Clock size={14} className="text-[var(--text-muted)]" />
                    {s}
                  </button>
                ))}
              </div>
            )}
            {history.length > 0 && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-[var(--text-muted)]">搜索历史</span>
                  <button
                    className="text-xs hover:underline text-[var(--accent)]"
                    onClick={clearHistory}
                  >
                    清空
                  </button>
                </div>
                {history.slice(0, 8).map((h, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between px-2 py-1.5 rounded hover:bg-[var(--bg-primary)] group"
                  >
                    <button
                      className="flex-1 text-left text-sm truncate"
                      onClick={() => { setQuery(h); handleSearch(h); }}
                    >
                      {h}
                    </button>
                    <button
                      className="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-[var(--bg-secondary)] flex-shrink-0"
                      onClick={() => removeHistory(h)}
                      aria-label="删除历史记录"
                    >
                      <X size={12} className="text-[var(--text-muted)]" />
                    </button>
                  </div>
                ))}
              </div>
            )}
            {!query && history.length === 0 && (
              <div>
                <p className="text-xs mb-2 flex items-center gap-1 text-[var(--text-muted)]">
                  <TrendingUp size={12} /> 热搜
                </p>
                <div className="flex flex-wrap gap-2">
                  {hotSearches.map((h, i) => (
                    <button
                      key={i}
                      className="px-3 py-1 rounded-full text-sm hover:opacity-80 transition-opacity"
                      style={{ backgroundColor: i < 3 ? 'var(--accent)' : 'var(--bg-secondary)', color: i < 3 ? '#fff' : 'var(--text)' }}
                      onClick={() => { setQuery(h); handleSearch(h); }}
                    >
                      {h}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ═══════ Search Results ═══════ */}
      {hasSearched && (
        <div>
          {/* Loading skeleton */}
          {isSearching && <SkeletonSearch />}

          {/* Error state */}
          {!isSearching && searchError && (
            <div className="text-center py-16 text-[var(--text-muted)]">
              <div className="text-4xl mb-3 opacity-30">⚠</div>
              <p className="text-lg font-medium text-[var(--danger)]">搜索出错</p>
              <p className="text-sm mt-2">{searchError}</p>
              <button
                className="btn-primary mt-4"
                onClick={() => doSearch(query.trim(), 1)}
              >
                重试
              </button>
            </div>
          )}

          {/* Empty state */}
          {!isSearching && !searchError && results.length === 0 && (
            <div className="text-center py-16 text-[var(--text-muted)]">
              <BookOpen size={48} className="mx-auto mb-3 opacity-30" />
              <p className="text-lg font-medium">未找到相关书籍</p>
              <p className="text-sm mt-2">尝试其他关键词或拼音首字母搜索</p>
            </div>
          )}

          {/* Results */}
          {!isSearching && results.length > 0 && (
            <div>
              {/* Results header */}
              <div className="flex items-center justify-between mb-4">
                <p className="text-sm text-[var(--text-muted)]">
                  找到 <span className="text-[var(--text-primary)] font-medium">{pagination?.total ?? results.length}</span> 本书
                  {searchTime > 0 && (
                    <span className="ml-1 text-xs text-[var(--text-muted)]">({searchTime.toFixed(0)}ms)</span>
                  )}
                </p>
              </div>

              {/* Book cards */}
              <div className="space-y-3">
                {results.map((item) => {
                  const [g1, g2] = getGradient(item.title);
                  return (
                    <button
                      key={`${item.book_id}-${item.id}`}
                      className="w-full glass-card p-4 text-left group"
                      onClick={() => router.push(`/book/${item.book_id}`)}
                    >
                      <div className="flex gap-3 sm:gap-4">
                        {/* Cover */}
                        <div
                          className="w-16 h-20 sm:w-20 sm:h-24 rounded-lg flex-shrink-0 flex items-center justify-center text-white font-bold text-lg shadow-lg"
                          style={{ background: `linear-gradient(135deg, ${g1}, ${g2})` }}
                        >
                          {item.title.charAt(0)}
                        </div>

                        {/* Info */}
                        <div className="flex-1 min-w-0">
                          {/* Title & Score */}
                          <div className="flex items-start justify-between gap-2">
                            <h3 className="font-semibold text-[var(--text-primary)] truncate group-hover:text-[var(--accent)] transition-colors">
                              {item.title}
                            </h3>
                            {item.total_score > 0 && (
                              <span className="text-xs font-mono text-[var(--accent)] flex-shrink-0 mt-0.5 flex items-center gap-0.5">
                                <Zap size={12} />
                                {item.total_score}
                              </span>
                            )}
                          </div>

                          {/* Author & Category */}
                          <p className="text-sm mt-0.5 text-[var(--text-muted)] flex items-center gap-2 flex-wrap">
                            <span>{item.author}</span>
                            {item.category && (
                              <span className="px-1.5 py-0.5 rounded text-xs bg-[var(--accent-soft)] text-[var(--accent)]">
                                {item.category}
                              </span>
                            )}
                          </p>

                          {/* Description */}
                          {item.description && (
                            <p className="text-xs mt-1.5 line-clamp-2 text-[var(--text-secondary)] leading-relaxed">
                              {item.description}
                            </p>
                          )}

                          {/* Tags */}
                          {item.tags && item.tags.length > 0 && (
                            <div className="flex gap-1 mt-2 flex-wrap">
                              {item.tags.slice(0, 4).map(tag => (
                                <span key={tag} className="tag text-[0.65rem]">{tag}</span>
                              ))}
                            </div>
                          )}

                          {/* Match reasons */}
                          {item.match_reasons && item.match_reasons.length > 0 && (
                            <div className="flex gap-1.5 mt-2 flex-wrap">
                              {item.match_reasons.map(reason => (
                                <span
                                  key={reason}
                                  className={`text-[0.65rem] px-1.5 py-0.5 rounded-full border ${REASON_BADGES[reason] || DEFAULT_BADGE}`}
                                >
                                  {reason}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Matched chapters */}
                      {item.matched_chapters && item.matched_chapters.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-[var(--border)]">
                          <p className="text-xs text-[var(--text-muted)] mb-2 flex items-center gap-1">
                            <Hash size={12} />
                            匹配章节 ({item.matched_chapters.length})
                          </p>
                          <div className="space-y-1.5">
                            {item.matched_chapters.slice(0, 3).map(ch => (
                              <div
                                key={ch.id}
                                className="text-xs p-2 rounded-lg bg-[var(--bg-primary)] hover:bg-[var(--bg-secondary)] cursor-pointer transition-colors"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  router.push(`/book/${item.book_id}/chapter/${ch.id}`);
                                }}
                              >
                                <div className="flex items-center justify-between gap-2">
                                  <span className="font-medium text-[var(--text-primary)] truncate">
                                    第{ch.chapter_number}章 {ch.title}
                                  </span>
                                  <span className="text-[0.6rem] text-[var(--text-muted)] flex-shrink-0">
                                    {ch.total_occurrences}处匹配
                                  </span>
                                </div>
                                {ch.content_preview && (
                                  <p className="mt-1 text-[var(--text-muted)] line-clamp-1 leading-relaxed">
                                    {ch.content_preview}
                                  </p>
                                )}
                              </div>
                            ))}
                            {item.matched_chapters.length > 3 && (
                              <p className="text-xs text-[var(--text-muted)] pl-2">
                                ...还有 {item.matched_chapters.length - 3} 个匹配章节
                              </p>
                            )}
                          </div>
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>

              {/* Load more */}
              {pagination?.has_next && (
                <div className="mt-6 text-center">
                  <button
                    className="btn-ghost px-8 py-2.5 text-sm"
                    onClick={handleLoadMore}
                    disabled={isLoadingMore}
                  >
                    {isLoadingMore ? (
                      <>
                        <Loader2 size={16} className="animate-spin" />
                        加载中...
                      </>
                    ) : (
                      <>
                        加载更多
                        <ChevronRight size={16} />
                      </>
                    )}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}