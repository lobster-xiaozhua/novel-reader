'use client';

import { useState, useDeferredValue } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { Search as SearchIcon } from 'lucide-react';
import { api } from '@/lib/api';
import type { ApiResponse, PaginatedData, BookListItem } from '@/types';

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const deferredSearchTerm = useDeferredValue(searchTerm);

  const { data, isLoading, error } = useQuery({
    queryKey: ['search', deferredSearchTerm],
    queryFn: () => api.get<ApiResponse<PaginatedData<BookListItem>>>(`/reader/search?q=${encodeURIComponent(deferredSearchTerm)}`),
    enabled: deferredSearchTerm.length > 0,
  });

  const results = data?.data?.items || [];

  const handleSearch = () => {
    if (query.trim()) setSearchTerm(query.trim());
  };

  return (
    <div>
      <div className="flex gap-2 mb-6">
        <input
          aria-label="搜索书名、作者"
          className="glass-input flex-1"
          type="text"
          placeholder="搜索书名、作者..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
        />
        <button className="btn-primary" onClick={handleSearch}>
          <SearchIcon size={16} />
          搜索
        </button>
      </div>

      {isLoading && <div className="text-center py-6" style={{ color: 'var(--text-muted)' }}>搜索中...</div>}
      {error && <div className="text-center py-6" style={{ color: 'var(--danger)' }}>搜索失败，请稍后重试</div>}
      {deferredSearchTerm && !isLoading && results.length === 0 && (
        <div className="text-center py-6" style={{ color: 'var(--text-muted)' }}>未找到相关结果</div>
      )}

      <div className="flex flex-col gap-2">
        {results.map((book) => (
          <Link key={book.id} href={`/book/${book.id}`} className="glass-card flex gap-3 no-underline">
            <div
              className="gradient-bar w-1 flex-shrink-0 self-stretch"
              style={{
                width: 4, height: 'auto', marginBottom: 0,
                background: `linear-gradient(180deg, ${book.gradient[0]}, ${book.gradient[1]})`,
              }}
            />
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-semibold" style={{ color: 'var(--text)' }}>{book.title}</h3>
              <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                {book.author} · {book.category} · {book.total_chapters}章
              </p>
              <p className="text-xs mt-1 truncate" style={{ color: 'var(--text-muted)' }}>{book.description}</p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
