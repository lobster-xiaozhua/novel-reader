'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams, useSearchParams, useRouter } from 'next/navigation';
import { ChevronLeft, ChevronRight, Settings } from 'lucide-react';
import { api } from '@/lib/api';
import type { ApiResponse, ChapterContent, ChapterItem, PaginatedData } from '@/types';

const FONT_SIZES = [14, 16, 18, 20, 22, 24];
const LINE_HEIGHTS = [1.5, 1.75, 2, 2.25, 2.5];
const THEMES = [
  { name: '默认', bg: 'var(--bg)', color: '#d1d5db' },
  { name: '暖色', bg: '#1a1510', color: '#d4c5a9' },
  { name: '护眼', bg: '#0d1a0d', color: '#a9d4a9' },
];

interface ReaderSettings {
  fontSize: number;
  lineHeight: number;
  themeIdx: number;
}

function loadSettings(): ReaderSettings {
  if (typeof window === 'undefined') return { fontSize: 17, lineHeight: 2, themeIdx: 0 };
  try {
    const saved = localStorage.getItem('reader-settings');
    if (saved) return JSON.parse(saved);
  } catch {}
  return { fontSize: 17, lineHeight: 2, themeIdx: 0 };
}

export default function ReaderPage() {
  const { id } = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();

  const initialChapterId = searchParams.get('chapter');
  const [currentChapterId, setCurrentChapterId] = useState<number | null>(
    initialChapterId ? Number(initialChapterId) : null,
  );
  const [showSettings, setShowSettings] = useState(false);
  const [settings, setSettings] = useState<ReaderSettings>(loadSettings);

  // 使用 useRef 避免闭包过期
  const currentChapterIdRef = useRef(currentChapterId);
  useEffect(() => { currentChapterIdRef.current = currentChapterId; }, [currentChapterId]);

  const saveSettings = (s: ReaderSettings) => {
    setSettings(s);
    localStorage.setItem('reader-settings', JSON.stringify(s));
  };

  // Fetch chapters metadata
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

  // Set initial chapter
  useEffect(() => {
    if (!currentChapterId && chapters.length > 0) {
      setCurrentChapterId(chapters[0].id);
    }
  }, [chapters, currentChapterId]);

  // 自动保存进度（30s），使用 ref 避免闭包过期
  useEffect(() => {
    if (!id) return;
    const interval = setInterval(() => {
      const chId = currentChapterIdRef.current;
      if (chId) {
        api.post(`/reader/books/${id}/progress`, { book_id: Number(id), chapter_id: chId, position: 0 }).catch(() => {});
      }
    }, 30000);
    return () => clearInterval(interval);
  }, [id]);

  // 离开页面前保存进度
  useEffect(() => {
    const handleBeforeUnload = () => {
      const chId = currentChapterIdRef.current;
      if (id && chId) {
        const payload = JSON.stringify({ book_id: Number(id), chapter_id: chId, position: 0 });
        navigator.sendBeacon('/api/reader/books/' + id + '/progress', payload);
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
  const theme = THEMES[settings.themeIdx];

  return (
    <div>
      {/* 导航栏 */}
      <div className="flex items-center justify-between mb-4">
        <button
          className="btn-ghost"
          disabled={!prevChapter}
          onClick={() => prevChapter && navigate(prevChapter)}
          aria-label="上一章"
        >
          <ChevronLeft size={16} />
          上一章
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
        <button
          className="btn-ghost"
          disabled={!nextChapter}
          onClick={() => nextChapter && navigate(nextChapter)}
          aria-label="下一章"
        >
          下一章
          <ChevronRight size={16} />
        </button>
      </div>

      {/* 阅读设置面板 */}
      {showSettings && (
        <div className="glass-card mb-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm" style={{ color: 'var(--text-muted)' }}>字号</span>
            <div className="flex gap-1">
              {FONT_SIZES.map(s => (
                <button
                  key={s}
                  className="px-2 py-1 text-xs rounded"
                  style={{
                    background: settings.fontSize === s ? 'var(--accent)' : 'var(--surface)',
                    color: settings.fontSize === s ? '#fff' : 'var(--text-muted)',
                    border: '1px solid var(--border)',
                  }}
                  onClick={() => saveSettings({ ...settings, fontSize: s })}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm" style={{ color: 'var(--text-muted)' }}>行距</span>
            <div className="flex gap-1">
              {LINE_HEIGHTS.map(h => (
                <button
                  key={h}
                  className="px-2 py-1 text-xs rounded"
                  style={{
                    background: settings.lineHeight === h ? 'var(--accent)' : 'var(--surface)',
                    color: settings.lineHeight === h ? '#fff' : 'var(--text-muted)',
                    border: '1px solid var(--border)',
                  }}
                  onClick={() => saveSettings({ ...settings, lineHeight: h })}
                >
                  {h}
                </button>
              ))}
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm" style={{ color: 'var(--text-muted)' }}>主题</span>
            <div className="flex gap-1">
              {THEMES.map((t, i) => (
                <button
                  key={i}
                  className="px-2 py-1 text-xs rounded"
                  style={{
                    background: settings.themeIdx === i ? 'var(--accent)' : t.bg,
                    color: settings.themeIdx === i ? '#fff' : t.color,
                    border: '1px solid var(--border)',
                  }}
                  onClick={() => saveSettings({ ...settings, themeIdx: i })}
                >
                  {t.name}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 内容 */}
      {isLoading && (
        <div className="text-center py-10" style={{ color: 'var(--text-muted)' }}>加载中...</div>
      )}
      {content && (
        <div className="glass-card" style={{ background: theme.bg }}>
          <h2 className="text-lg font-semibold mb-4" style={{ color: theme.color }}>{content.title}</h2>
          <div
            className="prose-reader"
            style={{
              fontSize: `${settings.fontSize}px`,
              lineHeight: settings.lineHeight,
              color: theme.color,
            }}
          >
            {content.content}
          </div>
        </div>
      )}

      {/* 底部导航 */}
      {content && (
        <div className="flex items-center justify-between mt-4 mb-8">
          <button
            className="btn-ghost"
            disabled={!prevChapter}
            onClick={() => prevChapter && navigate(prevChapter)}
            aria-label="上一章"
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
            aria-label="下一章"
          >
            下一章
            <ChevronRight size={16} />
          </button>
        </div>
      )}
    </div>
  );
}
