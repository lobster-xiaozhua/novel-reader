'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { api } from '@/shared/lib/api';
import { useDebounce } from '@/shared/hooks/useDebounce';
import { Plus, Search, BookOpen, Edit3, FileText } from 'lucide-react';
import type { ApiResponse, PaginatedData, AdminBook } from '@/shared/types';

export default function BooksPage() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const debouncedSearch = useDebounce(search, 300);

  const { data, isLoading } = useQuery<ApiResponse<PaginatedData<AdminBook>>>({
    queryKey: ['admin-books', page, debouncedSearch],
    queryFn: () =>
      api.get(`/admin/books?page=${page}&search=${encodeURIComponent(debouncedSearch)}`),
  });

  const books = data?.data?.items ?? [];
  const total = data?.data?.total ?? 0;
  const totalPages = Math.ceil(total / 20);

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
            书籍管理
          </h1>
          <p style={{ color: 'var(--text-tertiary)', marginTop: '0.25rem' }}>
            管理所有书籍和章节
          </p>
        </div>
        <Link
          href="/books/new"
          className="glass-btn glass-btn-primary font-medium"
        >
          <Plus size={18} />
          创建书籍
        </Link>
      </div>

      {/* Search */}
      <div className="glass-card p-3">
        <div className="flex items-center gap-3">
          <Search size={20} style={{ color: 'var(--text-tertiary)' }} />
          <input
            type="text"
            placeholder="搜索书名或作者..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="flex-1 bg-transparent border-none outline-none text-sm"
            style={{ color: 'var(--text-primary)' }}
          />
        </div>
      </div>

      {/* Books Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 border-3 border-transparent border-t-[var(--accent)] rounded-full animate-spin" />
            <p style={{ color: 'var(--text-tertiary)' }}>加载中...</p>
          </div>
        </div>
      ) : books.length === 0 ? (
        <div className="glass-card py-12 text-center">
          <BookOpen size={48} style={{ color: 'var(--text-tertiary)', margin: '0 auto 1rem' }} />
          <h3 style={{ color: 'var(--text-secondary)', fontSize: '1rem', marginBottom: '0.5rem' }}>
            暂无书籍
          </h3>
          <p style={{ color: 'var(--text-tertiary)', fontSize: '0.875rem' }}>
            创建第一本书籍开始使用
          </p>
        </div>
      ) : (
        <>
          {/* Book Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {books.map((book) => (
              <Link
                key={book.id}
                href={`/books/${book.id}`}
                className="glass-card flex items-start gap-4 no-underline"
              >
                {/* Cover Placeholder */}
                <div
                  className="w-16 h-20 rounded-lg flex items-center justify-center shrink-0"
                  style={{ 
                    background: book.gradient || 'var(--accent-soft)',
                  }}
                >
                  <BookOpen size={20} style={{ color: 'var(--accent)' }} />
                </div>
                
                {/* Content */}
                <div className="flex-1 min-w-0">
                  <h3 
                    className="font-semibold truncate"
                    style={{ color: 'var(--text-primary)', fontSize: '0.9375rem' }}
                  >
                    {book.title}
                  </h3>
                  {book.author && (
                    <p 
                      className="text-sm truncate"
                      style={{ color: 'var(--text-secondary)' }}
                    >
                      {book.author}
                    </p>
                  )}
                  
                  <div className="flex items-center gap-3 mt-3">
                    <span className="inline-flex items-center gap-1 text-xs" style={{ color: 'var(--text-tertiary)' }}>
                      <FileText size={14} />
                      {(book.chapter_count || book.total_chapters) || 0} 章节
                    </span>
                    {book.category && (
                      <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: 'var(--surface)', color: 'var(--text-secondary)' }}>
                        {book.category}
                      </span>
                    )}
                  </div>
                </div>

                {/* Edit Icon */}
                <Edit3 size={16} style={{ color: 'var(--text-tertiary)' }} />
              </Link>
            ))}
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between pt-4">
            <span className="text-sm" style={{ color: 'var(--text-tertiary)' }}>
              共 {total} 条，第 {page} / {totalPages || 1} 页
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="glass-btn text-sm disabled:opacity-40"
              >
                上一页
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages || 1, p + 1))}
                disabled={page >= totalPages || totalPages === 0}
                className="glass-btn text-sm disabled:opacity-40"
              >
                下一页
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}