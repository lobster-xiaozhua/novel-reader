'use client';

import { useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams, useRouter } from 'next/navigation';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { api } from '@/shared/lib/api';
import type { ApiResponse, ChapterContent, ChapterItem, PaginatedData } from '@/shared/types';

export default function ReaderPage() {
  const { bookId, chapterId } = useParams<{ bookId: string; chapterId: string }>();
  const router = useRouter();

  const currentChapterId = Number(chapterId);

  // Fetch all chapters metadata (for navigation)
  const { data: chaptersData } = useQuery({
    queryKey: ['chapters', bookId],
    queryFn: () => api.get<ApiResponse<PaginatedData<ChapterItem>>>(`/reader/books/${bookId}/chapters`),
    enabled: !!bookId,
  });

  const chapters = chaptersData?.data?.items || [];
  const chapterIndex = chapters.findIndex((c) => c.id === currentChapterId);
  const currentChapter = chapters[chapterIndex] || null;
  const prevChapter = chapterIndex > 0 ? chapters[chapterIndex - 1] : null;
  const nextChapter = chapterIndex >= 0 && chapterIndex < chapters.length - 1 ? chapters[chapterIndex + 1] : null;

  // Fetch current chapter content
  const { data: contentData, isLoading } = useQuery({
    queryKey: ['chapterContent', bookId, currentChapterId],
    queryFn: () => api.get<ApiResponse<ChapterContent>>(`/reader/books/${bookId}/chapters/${currentChapterId}`),
    enabled: !!bookId && !!currentChapterId,
  });

  // Pre-fetch next chapter
  useQuery({
    queryKey: ['chapterContent', bookId, nextChapter?.id],
    queryFn: () => api.get<ApiResponse<ChapterContent>>(`/reader/books/${bookId}/chapters/${nextChapter?.id}`),
    enabled: !!bookId && !!nextChapter?.id,
  });

  // Auto-save progress every 30s
  useEffect(() => {
    if (!bookId || !currentChapterId) return;
    const interval = setInterval(() => {
      api.post(`/reader/books/${bookId}/progress`, { chapter_id: currentChapterId, position: 0 }).catch(() => {});
    }, 30000);
    return () => clearInterval(interval);
  }, [bookId, currentChapterId]);

  const navigate = useCallback(
    (ch: ChapterItem) => {
      router.push(`/read/${bookId}/${ch.id}`, { scroll: false });
    },
    [bookId, router],
  );

  const content = contentData?.data;

  return (
    <div>
      {/* Navigation header */}
      <div className="flex items-center justify-between mb-4">
        <button
          className="btn-ghost"
          disabled={!prevChapter}
          onClick={() => prevChapter && navigate(prevChapter)}
        >
          <ChevronLeft size={16} />
          上一章
        </button>
        <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
          {currentChapter ? `第${currentChapter.chapter_number}章` : ''}
        </span>
        <button
          className="btn-ghost"
          disabled={!nextChapter}
          onClick={() => nextChapter && navigate(nextChapter)}
        >
          下一章
          <ChevronRight size={16} />
        </button>
      </div>

      {/* Content */}
      {isLoading && (
        <div className="text-center py-10" style={{ color: 'var(--text-muted)' }}>加载中...</div>
      )}
      {content && (
        <div className="glass-card">
          <h2 className="text-lg font-semibold mb-4">{content.title}</h2>
          <div className="prose-reader">{content.content}</div>
        </div>
      )}

      {/* Bottom navigation */}
      {content && (
        <div className="flex items-center justify-between mt-4 mb-8">
          <button
            className="btn-ghost"
            disabled={!prevChapter}
            onClick={() => prevChapter && navigate(prevChapter)}
          >
            <ChevronLeft size={16} />
            上一章
          </button>
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
            第 {content.chapter_number} 章 · {content.word_count} 字
          </span>
          <button
            className="btn-ghost"
            disabled={!nextChapter}
            onClick={() => nextChapter && navigate(nextChapter)}
          >
            下一章
            <ChevronRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
}
