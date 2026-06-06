'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useRouter } from 'next/navigation';
import { Heart, BookOpen } from 'lucide-react';
import { api } from '@/lib/api';
import type { ApiResponse, BookDetail, ChapterItem, PaginatedData } from '@/types';

export default function BookDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();

  const { data: bookData, isLoading: bookLoading } = useQuery({
    queryKey: ['book', id],
    queryFn: () => api.get<ApiResponse<BookDetail>>(`/reader/books/${id}`),
    enabled: !!id,
  });

  const { data: chaptersData, isLoading: chaptersLoading } = useQuery({
    queryKey: ['chapters', id],
    queryFn: () => api.get<ApiResponse<PaginatedData<ChapterItem>>>(`/reader/books/${id}/chapters`),
    enabled: !!id,
  });

  const favMut = useMutation({
    mutationFn: (favorited: boolean) =>
      favorited
        ? api.delete(`/reader/books/${id}/favorite`)
        : api.post(`/reader/books/${id}/favorite`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['book', id] });
    },
  });

  const book = bookData?.data;
  const chapters = chaptersData?.data?.items || [];

  const isLoading = bookLoading || chaptersLoading;

  if (isLoading) return <div className="text-center py-10" style={{ color: 'var(--text-muted)' }}>加载中...</div>;
  if (!book) return <div className="text-center py-10" style={{ color: 'var(--danger)' }}>书籍未找到</div>;

  const progressChapterId = book.reading_progress?.chapter_id;
  const firstChapter = chapters[0];

  return (
    <div>
      {/* Header */}
      <div className="glass-card mb-6">
        <div
          className="gradient-bar"
          style={{ background: `linear-gradient(90deg, ${book.gradient[0]}, ${book.gradient[1]})` }}
        />
        <h1 className="text-xl font-bold mt-1">{book.title}</h1>
        <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
          {book.author} · {book.category} · {book.total_chapters}章
        </p>
        <p className="text-sm mt-2 leading-relaxed" style={{ color: 'var(--text)' }}>
          {book.description}
        </p>

        <div className="flex gap-3 mt-4">
          <button
            className="btn-primary"
            onClick={() => {
              const chId = progressChapterId || firstChapter?.id;
              if (chId) router.push(`/read/${id}?chapter=${chId}`);
            }}
          >
            <BookOpen size={16} />
            {book.reading_progress ? '继续阅读' : '开始阅读'}
          </button>
          <button
            className="btn-ghost"
            onClick={() => favMut.mutate(book.is_favorited)}
            disabled={favMut.isPending}
          >
            <Heart
              size={16}
              style={{ color: book.is_favorited ? 'var(--danger)' : undefined }}
              fill={book.is_favorited ? 'var(--danger)' : 'none'}
            />
            {book.is_favorited ? '取消收藏' : '收藏'}
          </button>
        </div>
      </div>

      {/* Chapter List */}
      <div className="glass-card">
        <h2 className="text-base font-semibold mb-3">章节目录</h2>
        <div className="grid gap-2 max-h-96 overflow-y-auto" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))' }}>
          {chapters.map((ch) => (
            <button
              key={ch.id}
              className="text-left text-sm px-3 py-2 rounded-lg border cursor-pointer"
              style={{
                background: 'var(--surface)',
                borderColor: 'var(--border)',
                color: 'var(--text)',
              }}
              onClick={() => router.push(`/read/${id}?chapter=${ch.id}`)}
            >
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>第{ch.chapter_number}章</span>
              <br />
              <span className="truncate block">{ch.title}</span>
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{ch.word_count}字</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
