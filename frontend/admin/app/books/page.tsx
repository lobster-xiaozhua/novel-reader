'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { api } from '@/shared/lib/api';
import type { ApiResponse, PaginatedData, AdminBook } from '@/shared/types';

export default function BooksPage() {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery<ApiResponse<PaginatedData<AdminBook>>>({
    queryKey: ['admin-books', page, search],
    queryFn: () =>
      api.get(`/admin/books?page=${page}&search=${encodeURIComponent(search)}`),
  });

  const books = data?.data?.items ?? [];
  const total = data?.data?.total ?? 0;
  const totalPages = Math.ceil(total / 10);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>书籍管理</h1>

      <input
        type="text"
        placeholder="搜索书名..."
        value={search}
        onChange={(e) => { setSearch(e.target.value); setPage(1); }}
        className="glass-input w-full max-w-md"
      />

      {isLoading ? (
        <div style={{ color: 'var(--text-muted)' }}>加载中...</div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm" style={{ color: 'var(--text-primary)' }}>
              <thead>
                <tr className="border-b" style={{ borderColor: 'var(--border)' }}>
                  <th className="text-left py-3 px-3" style={{ color: 'var(--text-muted)' }}>ID</th>
                  <th className="text-left py-3 px-3" style={{ color: 'var(--text-muted)' }}>书名</th>
                  <th className="text-left py-3 px-3" style={{ color: 'var(--text-muted)' }}>作者</th>
                  <th className="text-left py-3 px-3" style={{ color: 'var(--text-muted)' }}>分类</th>
                  <th className="text-left py-3 px-3" style={{ color: 'var(--text-muted)' }}>章节数</th>
                  <th className="text-left py-3 px-3" style={{ color: 'var(--text-muted)' }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {books.map((book) => (
                  <tr
                    key={book.id}
                    className="border-b transition-colors hover:opacity-80"
                    style={{ borderColor: 'var(--border)' }}
                  >
                    <td className="py-3 px-3" style={{ color: 'var(--text-muted)' }}>{book.id}</td>
                    <td className="py-3 px-3 font-medium">{book.title}</td>
                    <td className="py-3 px-3" style={{ color: 'var(--text-secondary)' }}>{book.author}</td>
                    <td className="py-3 px-3" style={{ color: 'var(--text-secondary)' }}>{book.category}</td>
                    <td className="py-3 px-3" style={{ color: 'var(--accent)' }}>{book.total_chapters}</td>
                    <td className="py-3 px-3">
                      <Link
                        href={`/books/${book.id}`}
                        className="text-sm font-medium transition-colors hover:underline"
                        style={{ color: 'var(--accent)' }}
                      >
                        编辑
                      </Link>
                    </td>
                  </tr>
                ))}
                {books.length === 0 && (
                  <tr>
                    <td colSpan={6} className="py-8 text-center" style={{ color: 'var(--text-muted)' }}>
                      暂无数据
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between">
            <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
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