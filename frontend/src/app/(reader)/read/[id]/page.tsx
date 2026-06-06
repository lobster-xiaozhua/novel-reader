'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams, useSearchParams, useRouter } from 'next/navigation';
import { ChevronLeft, ChevronRight, Settings } from 'lucide-react';
import { api } from '@/lib/api';
import type { ApiResponse, ChapterContent, ChapterItem, PaginatedData } from '@/types';

type ReaderTheme = 'light' | 'sepia' | 'dark';

const READER_THEMES: Record<ReaderTheme, { bg: string; text: string; label: string }> = {
  light: { bg: '#ffffff', text: '#1a1a1a', label: '日间' },
  sepia: { bg: '#f5f0e8', text: '#3d3225', label: '护眼' },
  dark: { bg: '#1a1a2e', text: '#d1d5db', label: '夜间' },
};

export default function ReaderPage() {
  const { id } = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();

  const initialChapterId = searchParams.get('chapter');
  const [currentChapterId, setCurrentChapterId] = useState<number | null>(
    initialChapterId ? Number(initialChapterId) : null,
  );

  // 阅读器设置
  const [fontSize, setFontSize] = useState(18);
  const [lineHeight, setLineHeight] = useState(2);
  const [theme, setTheme] = useState<ReaderTheme>('dark');
  const [showSettings, setShowSettings] = useState(false);

  // P1-6: 使用 useRef 保存最新 currentChapterId，避免 setInterval 闭包过期
  const currentChapterIdRef = useRef(currentChapterId);
  useEffect(() => { currentChapterIdRef.current = currentChapterId; }, [currentChapterId]);

  // 从 localStorage 恢复阅读设置
  useEffect(() => {
    try {
      const saved = localStorage.getItem('reader-settings');
      if (saved) {
        const s = JSON.parse(saved);
        if (s.fontSize) setFontSize(s.fontSize);
        if (s.lineHeight) setLineHeight(s.lineHeight);
        if (s.theme) setTheme(s.theme);
      }
    } catch {}
  }, []);

  // 保存阅读设置到 localStorage
  useEffect(() => {
    try {
      localStorage.setItem('reader-settings', JSON.stringify({ fontSize, lineHeight, theme }));
    } catch {}
  }, [fontSize, lineHeight, theme]);

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

  const { data: contentData, isLoading } = useQuery({
    queryKey: ['chapterContent', id, currentChapterId],
    queryFn: () => api.get<ApiResponse<ChapterContent>>(`/reader/books/${id}/chapters/${currentChapterId}`),
    enabled: !!id && !!currentChapterId,
  });

  useQuery({
    queryKey: ['chapterContent', id, nextChapter?.id],
    queryFn: () => api.get<ApiResponse<ChapterContent>>(`/reader/books/${id}/chapters/${nextChapter?.id}`),
    enabled: !!id && !!nextChapter?.id,
  });

  useEffect(() => {
    if (!currentChapterId && chapters.length > 0) {
      setCurrentChapterId(chapters[0].id);
    }
  }, [chapters, currentChapterId]);

  // P1-6: 自动保存进度，使用 ref 获取最新 chapterId
  useEffect(() => {
    if (!id) return;
    const interval = setInterval(() => {
      const chId = currentChapterIdRef.current;
      if (chId) {
        api.post(`/reader/books/${id}/progress`, { chapter_id: chId, position: 0 }).catch(() => {});
      }
    }, 30000);
    return () => clearInterval(interval);
  }, [id]);

  // P1-5: 离开页面前保存进度
  useEffect(() => {
    const handleBeforeUnload = () => {
      const chId = currentChapterIdRef.current;
      if (id && chId) {
        navigator.sendBeacon(
          `/api/v2/reader/books/${id}/progress`,
          JSON.stringify({ chapter_id: chId, position: 0 }),
        );
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [id]);

  const navigate = useCallback(
    (ch: ChapterItem) => {
      setCurrentChapterId(ch.id);
      router.replace(`/read/${id}?chapter=${ch.id}`, { scroll: false });
    },
    [id, router],
  );

  const content = contentData?.data;
  const themeConfig = READER_THEMES[theme];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <button className="btn-ghost" disabled={!prevChapter} onClick={() => prevChapter && navigate(prevChapter)}>
          <ChevronLeft size={16} /> 上一章
        </button>
        <div className="flex items-center gap-2">
          <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
            {currentChapter ? `第${currentChapter.chapter_number}章` : ''}
          </span>
          <button
            className="btn-ghost"
            onClick={() => setShowSettings(!showSettings)}
            aria-label="阅读设置"
          >
            <Settings size={16} />
          </button>
        </div>
        <button className="btn-ghost" disabled={!nextChapter} onClick={() => nextChapter && navigate(nextChapter)}>
          下一章 <ChevronRight size={16} />
        </button>
      </div>

      {showSettings && (
        <div className="glass-card mb-4 flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>字号</span>
            <input type="range" min={14} max={24} value={fontSize} onChange={(e) => setFontSize(Number(e.target.value))} aria-label="字号" />
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{fontSize}px</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>行距</span>
            <input type="range" min={15} max={30} value={lineHeight * 10} onChange={(e) => setLineHeight(Number(e.target.value) / 10)} step={1} aria-label="行距" />
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{lineHeight.toFixed(1)}</span>
          </div>
          <div className="flex items-center gap-1">
            {(Object.entries(READER_THEMES) as [ReaderTheme, typeof READER_THEMES[ReaderTheme]][]).map(([key, val]) => (
              <button
                key={key}
                onClick={() => setTheme(key)}
                className="px-2 py-1 text-xs rounded"
                style={{
                  background: theme === key ? 'var(--accent)' : 'var(--surface)',
                  color: theme === key ? '#fff' : 'var(--text-muted)',
                  border: '1px solid var(--border)',
                }}
              >
                {val.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {isLoading && <div className="text-center py-10" style={{ color: 'var(--text-muted)' }}>加载中...</div>}
      {content && (
        <div className="glass-card" style={{ background: themeConfig.bg }}>
          <h2 className="text-lg font-semibold mb-4" style={{ color: themeConfig.text }}>{content.title}</h2>
          <div
            className="prose-reader"
            style={{
              fontSize: `${fontSize}px`,
              lineHeight: lineHeight,
              color: themeConfig.text,
            }}
          >
            {content.content}
          </div>
        </div>
      )}

      {content && (
        <div className="flex items-center justify-between mt-4 mb-8">
          <button className="btn-ghost" disabled={!prevChapter} onClick={() => prevChapter && navigate(prevChapter)}>
            <ChevronLeft size={16} /> 上一章
          </button>
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
            第 {content.chapter_number} 章 · {content.word_count} 字
          </span>
          <button className="btn-ghost" disabled={!nextChapter} onClick={() => nextChapter && navigate(nextChapter)}>
            下一章 <ChevronRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
}
