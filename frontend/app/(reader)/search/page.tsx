'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useRouter, useSearchParams } from 'next/navigation';
import { Search, BookOpen, Clock, X, TrendingUp } from 'lucide-react';
import { api } from '@/shared/lib/api';
import { SkeletonSearch } from '@/shared/components/Skeleton';
import type { ApiResponse, Book, PaginatedData } from '@/shared/types';

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

export default function SearchPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get('q') || '';
  const [query, setQuery] = useState(initialQuery);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const { history, addHistory, removeHistory, clearHistory } = useSearchHistory();

  // Fetch search results from backend
  const { data: searchData, refetch } = useQuery({
    queryKey: ['search', query],
    queryFn: async () => {
      const res = await api.get<ApiResponse<{ books: Book[]; total: number }>>(
        `/reader/search?q=${encodeURIComponent(query)}`,
      );
      return res.data;
    },
    enabled: false,
  });

  // Auto-suggestions based on query
  const suggestions = query.length > 0 ? history.filter(h =>
    h.toLowerCase().includes(query.toLowerCase()) && h !== query
  ).slice(0, 5) : [];

  // Hot searches (popular queries)
  const hotSearches = [
    '斗破', '斗破苍', '斗破苍', '三', '凡人', '仙', '遮天', '完', '星', '吞',
  ].slice(0, 10);

  const handleSearch = async (searchQuery?: string) => {
    const q = searchQuery || query;
    if (!q.trim()) return;

    setIsSearching(true);
    addHistory(q);
    router.push(`/search?q=${encodeURIComponent(q)}`);
    await refetch();
    setIsSearching(false);
    setShowSuggestions(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
    }
  };

  useEffect(() => {
    if (initialQuery) {
      handleSearch(initialQuery);
    }
  }, []);

  const books = searchData?.books || [];

  return (
    <div className="max-w-3xl mx-auto">
      {/* Search Input */}
      <div className="relative mb-6">
        <div className="flex items-center gap-2 glass-card p-2">
          <Search size={20} className="text-[var(--text-muted)]" />
          <input
            ref={inputRef}
            type="text"
            className="flex-1 outline-none bg-transparent"
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
              className="p-1 rounded-full hover:bg-[var(--bg-primary)]"
              onClick={() => {
                setQuery('');
                inputRef.current?.focus();
              }}
            >
              <X size={16} className="text-[var(--text-muted)]" />
            </button>
          )}
          <button
            className="btn-primary px-4 py-1.5"
            onClick={() => handleSearch()}
            disabled={isSearching}
          >
            {isSearching ? '搜索中...' : '搜索'}
          </button>
        </div>

        {/* Suggestions Dropdown */}
        {showSuggestions && (query || history.length > 0) && (
          <div className="absolute top-full left-0 right-0 mt-2 glass-card p-3 z-10">
            {suggestions.length > 0 && (
              <div className="mb-3">
                <div className="text-xs mb-2 text-[var(--text-muted)]">搜索建议</div>
                {suggestions.map((s, i) => (
                  <button
                    key={i}
                    className="w-full text-left px-2 py-1.5 rounded text-sm hover:bg-[var(--bg-primary)] flex items-center gap-2"
                    onClick={() => {
                      setQuery(s);
                      handleSearch(s);
                    }}
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
                      className="flex-1 text-left text-sm"
                      onClick={() => {
                        setQuery(h);
                        handleSearch(h);
                      }}
                    >
                      {h}
                    </button>
                    <button
                      className="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-[var(--bg-secondary)]"
                      onClick={() => removeHistory(h)}
                    >
                      <X size={12} className="text-[var(--text-muted)]" />
                    </button>
                  </div>
                ))}
              </div>
            )}
            {!query && history.length === 0 && (
              <div>
                <div className="text-xs mb-2 flex items-center gap-1 text-[var(--text-muted)]">
                  <TrendingUp size={12} /> 热搜
                </div>
                <div className="flex flex-wrap gap-2">
                  {hotSearches.map((h, i) => (
                    <button
                      key={i}
                      className="px-3 py-1 rounded-full text-sm hover:bg-[var(--bg-primary)]"
                      style={{ backgroundColor: i < 3 ? 'var(--accent)' : 'var(--bg-secondary)' }}
                      onClick={() => {
                        setQuery(h);
                        handleSearch(h);
                      }}
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

      {/* Search Results */}
      {query && (
        <div>
          {isSearching && <SkeletonSearch />}
          {!isSearching && books.length === 0 && (
            <div className="text-center py-10 text-[var(--text-muted)]">
              <BookOpen size={48} className="mx-auto mb-3 opacity-30" />
              未找到相关书籍
              <p className="text-sm mt-2">尝试其他关键词或拼音首字母搜索</p>
            </div>
          )}
          {books.length > 0 && (
            <div>
              <p className="text-sm mb-3 text-[var(--text-muted)]">
                找到 {books.length} 本书
              </p>
              <div className="space-y-3">
                {books.map(book => (
                  <button
                    key={book.id}
                    className="w-full glass-card p-4 flex gap-4 text-left hover:shadow-md transition-shadow"
                    onClick={() => router.push(`/book/${book.id}`)}
                  >
                    <div
                      className="w-16 h-20 rounded flex-shrink-0 flex items-center justify-center text-white font-bold"
                      style={{
                        background: `linear-gradient(135deg, ${book.cover_gradient?.[0] || '#667eea'}, ${book.cover_gradient?.[1] || '#764ba2'})`,
                      }}
                    >
                      {book.title.charAt(0)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium truncate">{book.title}</h3>
                      <p className="text-sm mt-1 text-[var(--text-muted)]">
                        {book.author}
                      </p>
                      <p className="text-xs mt-1 line-clamp-2 text-[var(--text-muted)]">
                        {book.description}
                      </p>
                      {book.tags && book.tags.length > 0 && (
                        <div className="flex gap-1 mt-2 flex-wrap">
                          {book.tags.slice(0, 3).map(tag => (
                            <span key={tag} className="tag text-[0.65rem]">
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}