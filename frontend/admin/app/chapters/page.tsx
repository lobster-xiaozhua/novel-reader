'use client';

import { useState, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import { api } from '@/shared/lib/api';
import type { ApiResponse, PaginatedData, AdminBook, AdminChapter } from '@/shared/types';

export default function ChaptersPage() {
  const searchParams = useSearchParams();
  const [selectedBook, setSelectedBook] = useState<number | ''>('');
  const [page, setPage] = useState(1);
  const queryClient = useQueryClient();

  useEffect(() => {
    const bookId = searchParams.get('book_id');
    if (bookId) {
      setSelectedBook(Number(bookId));
    }
  }, [searchParams]);

  const { data: booksData, isLoading: booksLoading } = useQuery<ApiResponse<PaginatedData<AdminBook>>>({
    queryKey: ['admin-books', 1, ''],
    queryFn: () => api.get('/admin/books?per_page=100'),
  });

  const { data: chaptersData, isLoading: chaptersLoading } = useQuery<ApiResponse<PaginatedData<AdminChapter>>>({
    queryKey: ['admin-chapters', selectedBook, page],
    queryFn: () => selectedBook ? api.get(`/admin/chapters?book_id=${selectedBook}&page=${page}`) : null,
    enabled: !!selectedBook,
  });

  const books = booksData?.data?.items ?? [];
  const chapters = chaptersData?.data?.items ?? [];
  const total = chaptersData?.data?.total ?? 0;
  const totalPages = Math.ceil(total / 50);

  const deleteMutation = useMutation({
    mutationFn: (chapterId: number) => api.delete(`/admin/chapters/${chapterId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-chapters'] });
      alert('删除成功');
    },
    onError: (err: Error) => alert(`删除失败: ${err.message}`),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>章节管理</h1>

      <div className="glass-card p-4 flex items-center gap-4 flex-wrap">
        <div>
          <label className="block text-sm mb-1.5" style={{ color: 'var(--text-secondary)' }}>
            选择书籍
          </label>
          <select
            value={selectedBook}
            onChange={(e) => { setSelectedBook(e.target.value ? Number(e.target.value) : ''); setPage(1); }}
            className="glass-input"
            disabled={booksLoading}
          >
            <option value="">-- 请选择 --</option>
            {books.map((book) => (
              <option key={book.id} value={book.id}>
                {book.title} ({book.author})
              </option>
            ))}
          </select>
        </div>
      </div>

      {!selectedBook ? (
        <div className="glass-card p-8 text-center" style={{ color: 'var(--text-muted)' }}>
          请先选择一本书籍
        </div>
      ) : chaptersLoading ? (
        <div style={{ color: 'var(--text-muted)' }}>加载中...</div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm" style={{ color: 'var(--text-primary)' }}>
              <thead>
                <tr className="border-b" style={{ borderColor: 'var(--border)' }}>
                  <th className="text-left py-3 px-3" style={{ color: 'var(--text-muted)' }}>序号</th>
                  <th className="text-left py-3 px-3" style={{ color: 'var(--text-muted)' }}>章节标题</th>
                  <th className="text-left py-3 px-3" style={{ color: 'var(--text-muted)' }}>字数</th>
                  <th className="text-left py-3 px-3" style={{ color: 'var(--text-muted)' }}>操作</th>
                </tr>
              </thead>
              <tbody>
                {chapters.map((chapter) => (
                  <tr
                    key={chapter.id}
                    className="border-b transition-colors hover:opacity-80"
                    style={{ borderColor: 'var(--border)' }}
                  >
                    <td className="py-3 px-3" style={{ color: 'var(--text-muted)' }}>{chapter.chapter_number}</td>
                    <td className="py-3 px-3 font-medium">{chapter.title}</td>
                    <td className="py-3 px-3" style={{ color: 'var(--accent)' }}>{chapter.word_count || 0}</td>
                    <td className="py-3 px-3">
                      <Link
                        href={`/chapters/${chapter.id}`}
                        className="text-sm font-medium transition-colors hover:underline mr-3"
                        style={{ color: 'var(--accent)' }}
                      >
                        编辑
                      </Link>
                      <button
                        onClick={() => {
                          if (window.confirm('确定删除此章节？')) {
                            deleteMutation.mutate(chapter.id);
                          }
                        }}
                        disabled={deleteMutation.isPending}
                        className="text-sm font-medium disabled:opacity-40 transition-colors hover:underline"
                        style={{ color: 'var(--danger)' }}
                      >
                        删除
                      </button>
                    </td>
                  </tr>
                ))}
                {chapters.length === 0 && (
                  <tr>
                    <td colSpan={4} className="py-8 text-center" style={{ color: 'var(--text-muted)' }}>
                      暂无章节
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
                共 {total} 条，第 {page} / {totalPages} 页
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
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="glass-btn text-sm disabled:opacity-40"
                >
                  下一页
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
