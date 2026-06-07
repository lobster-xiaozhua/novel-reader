'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useParams, useRouter } from 'next/navigation';
import { Heart, BookOpen, Clock, FileText } from 'lucide-react';
import { api } from '@/shared/lib/api';
import type { ApiResponse, BookDetail, ChapterItem, PaginatedData } from '@/shared/types';

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

  if (isLoading) return (
    <div className="flex items-center justify-center min-h-[50vh]">
      <div className="text-center" style={{ color: 'var(--text-muted)' }}>
        <BookOpen size={48} className="mx-auto mb-3 opacity-30 animate-pulse" />
        <p>加载中...</p>
      </div>
    </div>
  );

  if (!book) return (
    <div className="text-center py-10" style={{ color: 'var(--danger)' }}>
      <p>书籍未找到</p>
      <button className="btn-primary mt-4" onClick={() => router.push('/')}>
        返回首页
      </button>
    </div>
  );

  const progressChapterId = book.reading_progress?.chapter_id;
  const firstChapter = chapters[0];
  const gradient = book.gradient || ['#667eea', '#764ba2'];

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="glass-card mb-6 overflow-hidden">
        <div
          className="h-32 flex items-end p-6 relative"
          style={{ background: `linear-gradient(135deg, ${gradient[0]}, ${gradient[1]})` }}
        >
          <div className="absolute inset-0 bg-black/20" />
          <div className="relative z-10 flex items-end gap-4 w-full">
            <div
              className="w-20 h-28 rounded-lg shadow-lg flex items-center justify-center text-white text-3xl font-bold flex-shrink-0"
              style={{ background: `linear-gradient(135deg, ${gradient[0]}, ${gradient[1]})` }}
            >
              {book.title.charAt(0)}
            </div>
            <div className="flex-1 min-w-0">
              <h1 className="text-xl font-bold text-white truncate">{book.title}</h1>
              <p className="text-sm text-white/80 mt-1">
                {book.author} · {book.category}
              </p>
            </div>
          </div>
        </div>

        <div className="p-6">
          {/* Stats */}
          <div className="flex gap-4 mb-4 text-sm" style={{ color: 'var(--text-muted)' }}>
            <span className="flex items-center gap-1">
              <FileText size={14} /> {book.total_chapters}章
            </span>
            {book.reading_progress && (
              <span className="flex items-center gap-1">
                <Clock size={14} /> 已读至第{book.reading_progress.chapter?.chapter_number}章
              </span>
            )}
          </div>

          <p className="text-sm leading-relaxed mb-4" style={{ color: 'var(--text)' }}>
            {book.description}
          </p>

          {book.tags && book.tags.length > 0 && (
            <div className="flex gap-2 mb-4 flex-wrap">
              {book.tags.map((t) => (
                <span key={t.id} className="text-xs px-2 py-1 rounded-full" style={{ background: 'rgba(99,102,241,0.12)', color: 'var(--accent)' }}>
                  {t.name}
                </span>
              ))}
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3">
            <button
              className="btn-primary flex-1"
              onClick={() => {
                const chId = progressChapterId || firstChapter?.id;
                if (chId) router.push(`/read/${id}?chapter=${chId}`);
              }}
            >
              <BookOpen size={16} />
              {book.reading_progress ? '继续阅读' : '开始阅读'}
            </button>
            <button
              className="btn-ghost px-4"
              onClick={() => favMut.mutate(book.is_favorited)}
              disabled={favMut.isPending}
            >
              <Heart
                size={16}
                style={{ color: book.is_favorited ? 'var(--danger)' : undefined }}
                fill={book.is_favorited ? 'var(--danger)' : 'none'}
              />
              {book.is_favorited ? '已收藏' : '收藏'}
            </button>
          </div>
        </div>
      </div>

      {/* Chapter List */}
      <div className="glass-card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold">章节目录</h2>
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
            共 {chapters.length} 章
          </span>
        </div>
        <div className="grid gap-2 max-h-[500px] overflow-y-auto" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))' }}>
          {chapters.map((ch) => {
            const isReadProgress = ch.id === progressChapterId;
            return (
              <button
                key={ch.id}
                className="text-left text-sm px-3 py-2.5 rounded-lg border cursor-pointer transition-all hover:shadow-sm"
                style={{
                  background: isReadProgress ? 'var(--accent)' : 'var(--surface)',
                  borderColor: isReadProgress ? 'var(--accent)' : 'var(--border)',
                  color: isReadProgress ? '#fff' : 'var(--text)',
                }}
                onClick={() => router.push(`/read/${id}?chapter=${ch.id}`)}
              >
                <span className="truncate block">
                  {ch.title}
                </span>
                <span className="text-xs mt-1 block" style={{ color: isReadProgress ? 'rgba(255,255,255,0.7)' : 'var(--text-muted)' }}>
                  第{ch.chapter_number}章 · {ch.word_count}字
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
