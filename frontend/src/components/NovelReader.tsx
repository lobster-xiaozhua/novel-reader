import { useEffect, useCallback, useState, useRef } from 'react'
import { Minus, Plus, Type, Sun, Moon, BookOpen } from 'lucide-react'
import { saveProgress, trackStats } from '@/api/progress'

type ReaderTheme = 'dark' | 'sepia' | 'light'

const themeConfig: Record<ReaderTheme, { bg: string; text: string; name: string }> = {
  dark: { bg: 'bg-card-bg', text: 'text-text-secondary', name: '深色' },
  sepia: { bg: 'bg-[#f5e6c8]', text: 'text-[#5b4636]', name: '护眼' },
  light: { bg: 'bg-white', text: 'text-gray-800', name: '浅色' },
}

interface NovelReaderProps {
  content: string
  bookId: number
  chapterId: number
  chapterNumber: number
  totalChapters: number
  onPrev?: () => void
  onNext?: () => void
  hasPrev?: boolean
  hasNext?: boolean
}

export default function NovelReader({
  content,
  bookId,
  chapterId,
  chapterNumber,
  totalChapters,
  onPrev,
  onNext,
  hasPrev,
  hasNext,
}: NovelReaderProps) {
  const [fontSize, setFontSize] = useState(() => {
    const saved = localStorage.getItem('reader-fontSize')
    return saved ? parseInt(saved, 10) : 18
  })
  const [theme, setTheme] = useState<ReaderTheme>(() => {
    return (localStorage.getItem('reader-theme') as ReaderTheme) || 'dark'
  })
  const readStartRef = useRef(0)
  const savedRef = useRef(false)

  useEffect(() => {
    localStorage.setItem('reader-fontSize', String(fontSize))
  }, [fontSize])

  useEffect(() => {
    localStorage.setItem('reader-theme', theme)
  }, [theme])

  useEffect(() => {
    readStartRef.current = Date.now()
    savedRef.current = false
  }, [chapterId])

  useEffect(() => {
    const handleBeforeUnload = () => {
      if (savedRef.current) return
      const elapsed = Math.floor((Date.now() - readStartRef.current) / 1000)
      if (elapsed > 5) {
        const payload = JSON.stringify({ book_id: bookId, chapter_id: chapterId, position: chapterNumber })
        navigator.sendBeacon('/api/v1/progress/', new Blob([payload], { type: 'application/json' }))
        const statsPayload = JSON.stringify({ seconds: elapsed, chapter_id: chapterId })
        navigator.sendBeacon('/api/v1/progress/track-stats/', new Blob([statsPayload], { type: 'application/json' }))
      }
    }
    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [bookId, chapterId, chapterNumber])

  useEffect(() => {
    const interval = setInterval(() => {
      if (savedRef.current) return
      const elapsed = Math.floor((Date.now() - readStartRef.current) / 1000)
      if (elapsed >= 30) {
        savedRef.current = true
        saveProgress({ book_id: bookId, chapter_id: chapterId, position: chapterNumber }).catch(() => {})
        trackStats({ seconds: elapsed, chapter_id: chapterId }).catch(() => {})
      }
    }, 10000)
    return () => clearInterval(interval)
  }, [bookId, chapterId, chapterNumber])

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'ArrowLeft' && hasPrev) onPrev?.()
    if (e.key === 'ArrowRight' && hasNext) onNext?.()
  }, [hasPrev, hasNext, onPrev, onNext])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  const paragraphs = content.split(/\n+/).filter((p) => p.trim())
  const currentTheme = themeConfig[theme]
  const themes: ReaderTheme[] = ['dark', 'sepia', 'light']

  return (
    <div className="relative">
      <div className={`flex items-center justify-center gap-2 mb-6 sticky top-0 z-10 ${currentTheme.bg}/90 backdrop-blur-sm py-2 -mt-2`}>
        <button
          onClick={() => setFontSize((s) => Math.max(14, s - 2))}
          className="p-1.5 rounded-lg hover:bg-white/5 text-text-muted hover:text-text-primary transition-colors"
        >
          <Minus className="w-4 h-4" />
        </button>
        <Type className="w-4 h-4 text-text-muted" />
        <span className="text-xs text-text-muted w-8 text-center">{fontSize}</span>
        <button
          onClick={() => setFontSize((s) => Math.min(28, s + 2))}
          className="p-1.5 rounded-lg hover:bg-white/5 text-text-muted hover:text-text-primary transition-colors"
        >
          <Plus className="w-4 h-4" />
        </button>

        <div className="w-px h-5 bg-white/10 mx-1" />

        {themes.map((t) => (
          <button
            key={t}
            onClick={() => setTheme(t)}
            className={`p-1.5 rounded-lg transition-colors ${theme === t ? 'bg-primary-500/20 text-primary-500' : 'hover:bg-white/5 text-text-muted hover:text-text-primary'}`}
            title={themeConfig[t].name}
          >
            {t === 'dark' ? <Moon className="w-4 h-4" /> : t === 'sepia' ? <BookOpen className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
          </button>
        ))}

        {totalChapters > 0 && (
          <>
            <div className="w-px h-5 bg-white/10 mx-1" />
            <span className="text-xs text-text-muted">
              {chapterNumber}/{totalChapters}
            </span>
          </>
        )}
      </div>

      <div className={`max-w-3xl mx-auto rounded-xl p-6 ${currentTheme.bg} ${currentTheme.text}`} style={{ fontSize: `${fontSize}px`, lineHeight: 1.8 }}>
        {paragraphs.map((p, i) => (
          <p key={i} className="mb-4 indent-8">{p.trim()}</p>
        ))}
      </div>

      {(hasPrev || hasNext) && (
        <div className="flex items-center justify-between mt-8 pt-4 border-t border-white/[0.06]">
          <button
            onClick={onPrev}
            disabled={!hasPrev}
            className="px-4 py-2 rounded-lg bg-white/5 text-text-secondary text-sm hover:bg-white/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            ← 上一章
          </button>
          <span className="text-xs text-text-muted">← → 键翻页</span>
          <button
            onClick={onNext}
            disabled={!hasNext}
            className="px-4 py-2 rounded-lg bg-white/5 text-text-secondary text-sm hover:bg-white/10 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            下一章 →
          </button>
        </div>
      )}
    </div>
  )
}
