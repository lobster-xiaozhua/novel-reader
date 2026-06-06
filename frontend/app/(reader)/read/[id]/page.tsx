'use client';

import { useEffect, useState, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams, useSearchParams, useRouter } from 'next/navigation';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { api } from '@/shared/lib/api';
import type { ApiResponse, ChapterContent, ChapterItem, PaginatedData } from '@/shared/types';

export default function ReaderPage() {
  const { id } = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();

  const initialChapterId = searchParams.get('chapter');
  const [currentChapterId, setCurrentChapterId] = useState<number | null>(
    initialChapterId ? Number(initialChapterId) : null,
  );

  // Fetch all chapters metadata (for navigation)
  const { data: chaptersData } = useQuery({
    queryKey: ['chapters', id],
    queryFn: () => api.get<ApiResponse<PaginatedData<ChapterItem>>>(`/reader/books/${id}/chapters`),
    enabled: !!id,
  });

  const chapters = chaptersData?.data?.items || [];
  const chapterIndex = chapters.findIndex((c) => c.id === currentChapterId);
  const currentChapter = chapters[chapterIndex] || null;
  const prevChapter = chapterIndex > 0 ? chapters[chapterIndex - 1] : null;
  const nextChapter = chapterIndex >= 0 && chapterIndex < chapters.length - 1 ? chapters[chapterIndex + 1] : null;

  // Fetch current chapter content
  const { data: contentData, isLoading } = useQuery({
    queryKey: ['chapterContent', id, currentChapterId],
    queryFn: () => api.get<ApiResponse<ChapterContent>>(`/reader/books/${id}/chapters/${currentChapterId}`),
    enabled: !!id && !!currentChapterId,
  });

  // Pre-fetch next chapter
  useQuery({
    queryKey: ['chapterContent', id, nextChapter?.id],
    queryFn: () => api.get<ApiResponse<ChapterContent>>(`/reader/books/${id}/chapters/${nextChapter?.id}`),
    enabled: !!id && !!nextChapter?.id,
  });

  // Set initial chapter on first load
  useEffect(() => {
    if (!currentChapterId && chapters.length > 0) {
      setCurrentChapterId(chapters[0].id);
    }
  }, [chapters, currentChapterId]);

  // Auto-save progress every 30s
  useEffect(() => {
    if (!id || !currentChapterId) return;
    const interval = setInterval(() => {
      api.post(`/reader/books/${id}/progress`, { chapter_id: currentChapterId, position: 0 }).catch(() => {});
    }, 30000);
    return () => clearInterval(interval);
  }, [id, currentChapterId]);

  const navigate = useCallback(
    (ch: ChapterItem) => {
      setCurrentChapterId(ch.id);
      router.replace(`/read/${id}?chapter=${ch.id}`, { scroll: false });
    },
    [id, router],
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