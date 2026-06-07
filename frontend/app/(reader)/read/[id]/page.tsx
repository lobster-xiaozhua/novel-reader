'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams, useSearchParams, useRouter } from 'next/navigation';
import { ChevronLeft, ChevronRight, Settings, X, Plus, Minus, Sun, Moon, BookOpen } from 'lucide-react';
import { api } from '@/shared/lib/api';
import type { ApiResponse, ChapterContent, ChapterItem, PaginatedData } from '@/shared/types';

const THEMES = {
  light: { bg: '#faf9f6', text: '#1a1a1a', label: '浅色' },
  paper: { bg: '#f5f0e1', text: '#2c2c2c', label: '羊皮纸' },
  dark: { bg: '#1a1a1a', text: '#d4d4d4', label: '深色' },
  green: { bg: '#c7edcc', text: '#1a1a1a', label: '护眼绿' },
  night: { bg: '#0d0d0d', text: '#888888', label: '夜间' },
} as const;

type ThemeName = keyof typeof THEMES;

function useReaderSettings() {
  const [fontSize, setFontSize] = useState(() => {
    if (typeof window !== 'undefined') {
      return Number(localStorage.getItem('reader-font-size')) || 18;
    }
    return 18;
  });
  const [theme, setTheme] = useState<ThemeName>(() => {
    if (typeof window !== 'undefined') {
      return (localStorage.getItem('reader-theme') as ThemeName) || 'light';
    }
    return 'light';
  });

  useEffect(() => { localStorage.setItem('reader-font-size', String(fontSize)); }, [fontSize]);
  useEffect(() => { localStorage.setItem('reader-theme', theme); }, [theme]);

  return { fontSize, setFontSize, theme, setTheme };
}

export default function ReaderPage() {
  const { id } = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const contentRef = useRef<HTMLDivElement>(null);

  const initialChapterId = searchParams.get('chapter');
  const [currentChapterId, setCurrentChapterId] = useState<number | null>(
    initialChapterId ? Number(initialChapterId) : null,
  );
  const [showSettings, setShowSettings] = useState(false);
  const { fontSize, setFontSize, theme, setTheme } = useReaderSettings();
  const currentTheme = THEMES[theme];

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

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowLeft' && prevChapter) {
        navigate(prevChapter);
      } else if (e.key === 'ArrowRight' && nextChapter) {
        navigate(nextChapter);
      } else if (e.key === 'Escape') {
        setShowSettings(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [prevChapter, nextChapter]);

  const navigate = useCallback(
    (ch: ChapterItem) => {
      setCurrentChapterId(ch.id);
      contentRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
      router.replace(`/read/${id}?chapter=${ch.id}`, { scroll: false });
    },
    [id, router],
  );

  const content = contentData?.data;

  return (
    <div
      data-reader-theme={theme}
      style={{
        backgroundColor: 'var(--reader-bg)',
        color: 'var(--reader-text)',
        minHeight: '100vh',
        transition: 'background-color 0.3s, color 0.3s',
      }}
    >
      {/* Navigation header */}
      <div
        className="flex items-center justify-between mb-4 sticky top-0 z-10 py-2"
        style={{
          backgroundColor: `${currentTheme.bg}cc`,
          backdropFilter: 'blur(8px)',
        }}
      >
        <button
          className="px-3 py-1.5 rounded-lg flex items-center gap-1.5 text-sm transition-opacity"
          style={{ opacity: prevChapter ? 1 : 0.3 }}
          disabled={!prevChapter}
          onClick={() => prevChapter && navigate(prevChapter)}
        >
          <ChevronLeft size={16} /> 上一章
        </button>
        <span className="text-sm opacity-60">
          {currentChapter ? `第${currentChapter.chapter_number}章` : ''}
        </span>
        <div className="flex items-center gap-2">
          <button
            className="px-3 py-1.5 rounded-lg flex items-center gap-1.5 text-sm transition-opacity"
            style={{ opacity: nextChapter ? 1 : 0.3 }}
            disabled={!nextChapter}
            onClick={() => nextChapter && navigate(nextChapter)}
          >
            下一章 <ChevronRight size={16} />
          </button>
          <button
            className="p-2 rounded-lg transition-colors"
            style={{ backgroundColor: `${currentTheme.text}15` }}
            onClick={() => setShowSettings(!showSettings)}
          >
            {showSettings ? <X size={18} /> : <Settings size={18} />}
          </button>
        </div>
      </div>

      {/* Settings Panel */}
      {showSettings && (
        <div className="glass-card mb-4 p-4 space-y-4" style={{ backgroundColor: `${currentTheme.text}10` }}>
          {/* Font Size */}
          <div className="flex items-center justify-between">
            <span className="text-sm flex items-center gap-2">
              <BookOpen size={16} /> 字体大小
            </span>
            <div className="flex items-center gap-3">
              <button
                className="p-1.5 rounded-full transition-colors"
                style={{ backgroundColor: `${currentTheme.text}15` }}
                onClick={() => setFontSize(Math.max(14, fontSize - 1))}
              >
                <Minus size={16} />
              </button>
              <span className="text-sm w-8 text-center">{fontSize}</span>
              <button
                className="p-1.5 rounded-full transition-colors"
                style={{ backgroundColor: `${currentTheme.text}15` }}
                onClick={() => setFontSize(Math.min(28, fontSize + 1))}
              >
                <Plus size={16} />
              </button>
            </div>
          </div>

          {/* Theme */}
          <div className="flex items-center justify-between">
            <span className="text-sm flex items-center gap-2">
              <Sun size={16} /> 阅读主题
            </span>
            <div className="flex gap-2">
              {(Object.entries(THEMES) as [ThemeName, (typeof THEMES)[ThemeName]][]).map(([name, t]) => (
                <button
                  key={name}
                  className="w-8 h-8 rounded-full border-2 transition-all flex items-center justify-center"
                  style={{
                    backgroundColor: t.bg,
                    borderColor: theme === name ? currentTheme.text : 'transparent',
                    transform: theme === name ? 'scale(1.15)' : 'scale(1)',
                  }}
                  onClick={() => setTheme(name)}
                  title={t.label}
                >
                  {theme === name && <Moon size={12} style={{ color: t.text }} />}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Content */}
      {isLoading && (
        <div className="text-center py-10 opacity-50">加载中...</div>
      )}
      {content && (
        <div
          ref={contentRef}
          className="rounded-xl p-6 md:p-8"
          style={{ backgroundColor: `${currentTheme.text}08` }}
        >
          <h2 className="text-xl font-semibold mb-6 text-center">{content.title}</h2>
          <div
            style={{
              fontSize: `${fontSize}px`,
              lineHeight: '1.8',
              letterSpacing: '0.02em',
            }}
          >
            {content.content.split('\n').map((paragraph, i) => (
              <p key={i} className="mb-4 text-justify">
                {paragraph}
              </p>
            ))}
          </div>
        </div>
      )}

      {/* Bottom navigation */}
      {content && (
        <div className="flex items-center justify-between mt-6 mb-8 pt-4"
          style={{ borderTop: `1px solid ${currentTheme.text}20` }}
        >
          <button
            className="px-4 py-2 rounded-lg flex items-center gap-1.5 text-sm transition-opacity"
            style={{ opacity: prevChapter ? 1 : 0.3 }}
            disabled={!prevChapter}
            onClick={() => prevChapter && navigate(prevChapter)}
          >
            <ChevronLeft size={16} /> 上一章
          </button>
          <span className="text-xs opacity-50">
            第 {content.chapter_number} 章 · {content.word_count} 字
          </span>
          <button
            className="px-4 py-2 rounded-lg flex items-center gap-1.5 text-sm transition-opacity"
            style={{ opacity: nextChapter ? 1 : 0.3 }}
            disabled={!nextChapter}
            onClick={() => nextChapter && navigate(nextChapter)}
          >
            下一章 <ChevronRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
}