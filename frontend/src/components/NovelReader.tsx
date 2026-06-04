import { useEffect, useCallback, useState, useRef, memo } from 'react'
import {
  Minus, Plus, Type, Sun, Moon, BookOpen, Settings, List,
  Bookmark, BookmarkCheck, ChevronLeft, ChevronRight, X,
  Clock, Eye, Palette, AlignLeft, Monitor
} from 'lucide-react'
import { saveProgress, trackStats } from '@/api/progress'
import { getAccessToken } from '@/utils/http'

// ============ Types ============

export interface ChapterInfo {
  id: number
  chapter_number: number
  title: string
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
  bookTitle?: string
  chapters?: ChapterInfo[]
}

type ReaderTheme = 'dark' | 'sepia' | 'light'
type FontFamily = 'serif' | 'sans-serif' | 'mono'

interface ReaderSettings {
  fontSize: number
  theme: ReaderTheme
  fontFamily: FontFamily
  lineHeight: number
  paragraphSpacing: number
  nightMode: boolean
}

// ============ Constants ============

const THEME_COLORS: Record<ReaderTheme, {
  bg: string; text: string; textSecondary: string; textMuted: string
  accent: string; border: string; progressBg: string; hoverBg: string
  cardBg: string; name: string; icon: typeof Sun
}> = {
  dark: {
    bg: '#0d1117', text: '#e6edf3', textSecondary: '#8b949e',
    textMuted: '#484f58', accent: '#f59e0b', border: 'rgba(255,255,255,0.08)',
    progressBg: 'rgba(255,255,255,0.06)', hoverBg: 'rgba(255,255,255,0.06)',
    cardBg: '#161b22', name: '深色', icon: Moon
  },
  sepia: {
    bg: '#f4ecd8', text: '#5c4b37', textSecondary: '#7a6b5a',
    textMuted: '#9a8b7a', accent: '#b8860b', border: 'rgba(92,75,55,0.12)',
    progressBg: 'rgba(92,75,55,0.08)', hoverBg: 'rgba(92,75,55,0.06)',
    cardBg: '#eaddc8', name: '护眼', icon: BookOpen
  },
  light: {
    bg: '#ffffff', text: '#1a1a2e', textSecondary: '#4a4a6a',
    textMuted: '#8a8aaa', accent: '#d97706', border: 'rgba(0,0,0,0.08)',
    progressBg: 'rgba(0,0,0,0.04)', hoverBg: 'rgba(0,0,0,0.04)',
    cardBg: '#f8f9fa', name: '浅色', icon: Sun
  }
}

const FONT_FAMILIES: Record<FontFamily, { name: string; css: string }> = {
  'serif': {
    name: '衬线',
    css: '"Noto Serif SC", "Source Han Serif SC", "SimSun", Georgia, serif'
  },
  'sans-serif': {
    name: '无衬线',
    css: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans SC", sans-serif'
  },
  'mono': {
    name: '等宽',
    css: '"JetBrains Mono", "Fira Code", "Cascadia Code", monospace'
  }
}

const DEFAULT_SETTINGS: ReaderSettings = {
  fontSize: 18,
  theme: 'dark',
  fontFamily: 'sans-serif',
  lineHeight: 1.8,
  paragraphSpacing: 1.25,
  nightMode: false
}

// ============ Helpers ============

function loadSettings(): Partial<ReaderSettings> {
  try {
    const saved = localStorage.getItem('reader-settings')
    return saved ? JSON.parse(saved) : {}
  } catch {
    return {}
  }
}

function estimateReadingTime(wordCount: number): string {
  const minutes = Math.max(1, Math.round(wordCount / 500))
  return `${minutes}分钟`
}

function countWords(content: string): number {
  const chinese = (content.match(/[\u4e00-\u9fa5]/g) || []).length
  const english = (content.match(/[a-zA-Z]+/g) || []).length
  return chinese + english
}

// ============ Sub-components ============

const ProgressBar = memo(({ progress, colors }: { progress: number; colors: typeof THEME_COLORS.dark }) => (
  <div className="fixed top-0 left-0 right-0 z-50 h-1" style={{ background: colors.progressBg }}>
    <div
      className="h-full transition-all duration-500 ease-out"
      style={{
        width: `${Math.min(100, Math.max(0, progress))}%`,
        background: `linear-gradient(90deg, ${colors.accent}, ${colors.accent}dd)`
      }}
    />
  </div>
))

function TocDrawer({
  open, onClose, chapters, currentChapter, onJump, colors
}: {
  open: boolean
  onClose: () => void
  chapters: ChapterInfo[]
  currentChapter: number
  onJump: (chapter: ChapterInfo) => void
  colors: typeof THEME_COLORS.dark
}) {
  if (!open) return null

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm transition-opacity duration-300"
        onClick={onClose}
      />
      <div
        className="fixed top-0 right-0 bottom-0 z-50 w-80 max-w-[85vw] overflow-hidden transition-transform duration-300 ease-out"
        style={{ background: colors.cardBg, borderLeft: `1px solid ${colors.border}` }}
      >
        <div className="flex items-center justify-between p-4 border-b" style={{ borderColor: colors.border }}>
          <h3 className="text-lg font-semibold" style={{ color: colors.text }}>目录</h3>
          <button
            onClick={onClose}
            className="p-2 rounded-lg transition-colors"
            style={{ color: colors.textSecondary }}
            onMouseEnter={(e) => e.currentTarget.style.background = colors.hoverBg}
            onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
          >
            <X size={20} />
          </button>
        </div>
        <div className="overflow-y-auto h-[calc(100%-60px)] p-2">
          {chapters.map((ch) => {
            const isActive = ch.chapter_number === currentChapter
            return (
              <button
                key={ch.id}
                onClick={() => onJump(ch)}
                className="w-full text-left px-3 py-2.5 rounded-lg text-sm transition-colors mb-1"
                style={{
                  color: isActive ? colors.accent : colors.text,
                  background: isActive ? `${colors.accent}15` : 'transparent',
                  fontWeight: isActive ? 600 : 400
                }}
                onMouseEnter={(e) => {
                  if (!isActive) e.currentTarget.style.background = colors.hoverBg
                }}
                onMouseLeave={(e) => {
                  if (!isActive) e.currentTarget.style.background = 'transparent'
                }}
              >
                <span className="opacity-60 mr-2">{ch.chapter_number}</span>
                {ch.title}
              </button>
            )
          })}
        </div>
      </div>
    </>
  )
}

function SettingsPanel({
  open, onClose, settings, onChange, colors
}: {
  open: boolean
  onClose: () => void
  settings: ReaderSettings
  onChange: (s: Partial<ReaderSettings>) => void
  colors: typeof THEME_COLORS.dark
}) {
  if (!open) return null

  const sectionClass = "p-4 border-b"
  const labelClass = "text-sm font-medium mb-3 block"
  const optionBtnClass = (active: boolean) =>
    `px-3 py-2 rounded-lg text-sm transition-all duration-200 ${
      active ? 'ring-1' : ''
    }`

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      <div
        className="fixed bottom-24 left-1/2 -translate-x-1/2 z-50 w-[420px] max-w-[90vw] rounded-2xl overflow-hidden shadow-2xl"
        style={{
          background: colors.cardBg,
          border: `1px solid ${colors.border}`,
          boxShadow: `0 8px 32px rgba(0,0,0,${colors.bg === '#ffffff' ? '0.15' : '0.4'})`
        }}
      >
        <div className="flex items-center justify-between p-4 border-b" style={{ borderColor: colors.border }}>
          <div className="flex items-center gap-2">
            <Settings size={18} style={{ color: colors.accent }} />
            <h3 className="font-semibold" style={{ color: colors.text }}>阅读设置</h3>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg transition-colors"
            style={{ color: colors.textSecondary }}
            onMouseEnter={(e) => e.currentTarget.style.background = colors.hoverBg}
            onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
          >
            <X size={18} />
          </button>
        </div>

        <div className="max-h-[60vh] overflow-y-auto">
          {/* Font Size */}
          <div className={sectionClass}>
            <label className={labelClass} style={{ color: colors.textSecondary }}>
              <div className="flex items-center gap-2">
                <Type size={14} /> 字号
              </div>
            </label>
            <div className="flex items-center gap-3">
              <button
                onClick={() => onChange({ fontSize: Math.max(14, settings.fontSize - 2) })}
                className="p-2 rounded-lg transition-colors"
                style={{ color: colors.text }}
                onMouseEnter={(e) => e.currentTarget.style.background = colors.hoverBg}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                <Minus size={16} />
              </button>
              <div
                className="flex-1 h-2 rounded-full"
                style={{ background: colors.progressBg }}
              >
                <div
                  className="h-full rounded-full transition-all duration-200"
                  style={{
                    width: `${((settings.fontSize - 14) / 14) * 100}%`,
                    background: colors.accent
                  }}
                />
              </div>
              <span className="w-8 text-center text-sm font-medium tabular-nums" style={{ color: colors.text }}>
                {settings.fontSize}
              </span>
              <button
                onClick={() => onChange({ fontSize: Math.min(28, settings.fontSize + 2) })}
                className="p-2 rounded-lg transition-colors"
                style={{ color: colors.text }}
                onMouseEnter={(e) => e.currentTarget.style.background = colors.hoverBg}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              >
                <Plus size={16} />
              </button>
            </div>
          </div>

          {/* Font Family */}
          <div className={sectionClass}>
            <label className={labelClass} style={{ color: colors.textSecondary }}>
              <div className="flex items-center gap-2">
                <AlignLeft size={14} /> 字体
              </div>
            </label>
            <div className="flex gap-2">
              {(Object.entries(FONT_FAMILIES) as [FontFamily, typeof FONT_FAMILIES[FontFamily]][]).map(([key, val]) => (
                <button
                  key={key}
                  onClick={() => onChange({ fontFamily: key })}
                  className={`flex-1 ${optionBtnClass(settings.fontFamily === key)}`}
                  style={{
                    fontFamily: val.css,
                    color: settings.fontFamily === key ? colors.accent : colors.textSecondary,
                    background: settings.fontFamily === key ? `${colors.accent}15` : 'transparent',
                    borderColor: settings.fontFamily === key ? `${colors.accent}40` : colors.border,
                    fontWeight: settings.fontFamily === key ? 600 : 400
                  }}
                >
                  {val.name}
                </button>
              ))}
            </div>
          </div>

          {/* Line Height */}
          <div className={sectionClass}>
            <label className={labelClass} style={{ color: colors.textSecondary }}>
              <div className="flex items-center gap-2">
                <AlignLeft size={14} /> 行高
              </div>
            </label>
            <div className="flex gap-2">
              {[1.6, 1.8, 2.0].map((lh) => (
                <button
                  key={lh}
                  onClick={() => onChange({ lineHeight: lh })}
                  className={`flex-1 ${optionBtnClass(settings.lineHeight === lh)}`}
                  style={{
                    color: settings.lineHeight === lh ? colors.accent : colors.textSecondary,
                    background: settings.lineHeight === lh ? `${colors.accent}15` : 'transparent',
                    borderColor: settings.lineHeight === lh ? `${colors.accent}40` : colors.border,
                    fontWeight: settings.lineHeight === lh ? 600 : 400
                  }}
                >
                  {lh}
                </button>
              ))}
            </div>
          </div>

          {/* Paragraph Spacing */}
          <div className={sectionClass}>
            <label className={labelClass} style={{ color: colors.textSecondary }}>
              <div className="flex items-center gap-2">
                <Palette size={14} /> 段落间距
              </div>
            </label>
            <div className="flex gap-2">
              {[0.8, 1.25, 1.6].map((sp) => (
                <button
                  key={sp}
                  onClick={() => onChange({ paragraphSpacing: sp })}
                  className={`flex-1 ${optionBtnClass(settings.paragraphSpacing === sp)}`}
                  style={{
                    color: settings.paragraphSpacing === sp ? colors.accent : colors.textSecondary,
                    background: settings.paragraphSpacing === sp ? `${colors.accent}15` : 'transparent',
                    borderColor: settings.paragraphSpacing === sp ? `${colors.accent}40` : colors.border,
                    fontWeight: settings.paragraphSpacing === sp ? 600 : 400
                  }}
                >
                  {sp < 1 ? '紧凑' : sp < 1.5 ? '适中' : '宽松'}
                </button>
              ))}
            </div>
          </div>

          {/* Theme */}
          <div className={sectionClass}>
            <label className={labelClass} style={{ color: colors.textSecondary }}>
              <div className="flex items-center gap-2">
                <Monitor size={14} /> 主题
              </div>
            </label>
            <div className="flex gap-2">
              {(['dark', 'sepia', 'light'] as ReaderTheme[]).map((t) => {
                const c = THEME_COLORS[t]
                return (
                  <button
                    key={t}
                    onClick={() => onChange({ theme: t })}
                    className={`flex-1 py-2.5 rounded-lg text-sm transition-all duration-200 ${
                      settings.theme === t ? 'ring-1' : ''
                    }`}
                    style={{
                      color: settings.theme === t ? c.accent : c.textSecondary,
                      background: settings.theme === t ? `${c.accent}15` : c.bg,
                      borderColor: settings.theme === t ? `${c.accent}40` : c.border,
                      fontWeight: settings.theme === t ? 600 : 400
                    }}
                  >
                    {c.name}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Night Mode */}
          <div className={`${sectionClass} border-b-0`}>
            <button
              onClick={() => onChange({ nightMode: !settings.nightMode })}
              className="w-full flex items-center justify-between py-2"
              style={{ color: colors.text }}
            >
              <div className="flex items-center gap-2">
                {settings.nightMode ? <Moon size={14} style={{ color: colors.accent }} /> : <Eye size={14} />}
                <span className="text-sm font-medium">夜间模式</span>
              </div>
              <div
                className="w-10 h-6 rounded-full transition-colors duration-200 relative"
                style={{ background: settings.nightMode ? colors.accent : colors.progressBg }}
              >
                <div
                  className="absolute top-1 w-4 h-4 rounded-full transition-all duration-200 bg-white"
                  style={{ left: settings.nightMode ? 'calc(100% - 20px)' : '4px' }}
                />
              </div>
            </button>
          </div>
        </div>
      </div>
    </>
  )
}

// ============ Main Component ============

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
  bookTitle: _bookTitle,
  chapters = []
}: NovelReaderProps) {
  const saved = loadSettings()
  const [settings, setSettings] = useState<ReaderSettings>(() => ({
    ...DEFAULT_SETTINGS,
    ...saved
  }))
  const [tocOpen, setTocOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [bookmarked, setBookmarked] = useState(false)
  const [savingBookmark, setSavingBookmark] = useState(false)
  const [toast, setToast] = useState<string | null>(null)

  const contentRef = useRef<HTMLDivElement>(null)
  const readStartRef = useRef(0)
  const savedRef = useRef(false)
  const toastTimerRef = useRef<number | null>(null)
  const touchStartRef = useRef<{ x: number; y: number } | null>(null)
  const touchStartTimeRef = useRef(0)

  // Persist settings
  useEffect(() => {
    localStorage.setItem('reader-settings', JSON.stringify(settings))
  }, [settings])

  // Track read start time per chapter
  useEffect(() => {
    readStartRef.current = Date.now()
    savedRef.current = false
    setBookmarked(false)

    if (contentRef.current) {
      contentRef.current.scrollTo({ top: 0, behavior: 'smooth' })
    }
  }, [chapterId])

  // Auto-save progress
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (savedRef.current) return
      const elapsed = Math.floor((Date.now() - readStartRef.current) / 1000)
      if (elapsed > 5) {
        sendBeaconWithAuth('/api/v1/progress/', { book_id: bookId, chapter_id: chapterId, position: chapterNumber })
        sendBeaconWithAuth('/api/v1/progress/track-stats/', { seconds: elapsed, chapter_id: chapterId })
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

  // Toast helper
  const showToast = useCallback((msg: string) => {
    setToast(msg)
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current)
    toastTimerRef.current = window.setTimeout(() => setToast(null), 2000)
  }, [])

  // Navigation
  const goToPrev = useCallback(() => {
    if (hasPrev) {
      onPrev?.()
      showToast('上一章')
    }
  }, [hasPrev, onPrev, showToast])

  const goToNext = useCallback(() => {
    if (hasNext) {
      onNext?.()
      showToast('下一章')
    }
  }, [hasNext, onNext, showToast])

  // Keyboard
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (settingsOpen || tocOpen) return

      if (e.key === 'ArrowLeft' || e.key === 'PageUp') goToPrev()
      else if (e.key === 'ArrowRight' || e.key === 'PageDown') goToNext()
      else if (e.key === 't' || e.key === 'T') setTocOpen(o => !o)
      else if (e.key === 's' || e.key === 'S') setSettingsOpen(o => !o)
      else if (e.key === 'b' || e.key === 'B') handleBookmark()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [goToPrev, goToNext, settingsOpen, tocOpen])

  // Touch/Swipe
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    touchStartRef.current = { x: e.touches[0].clientX, y: e.touches[0].clientY }
    touchStartTimeRef.current = Date.now()
  }, [])

  const handleTouchEnd = useCallback((e: React.TouchEvent) => {
    if (!touchStartRef.current) return

    const dx = e.changedTouches[0].clientX - touchStartRef.current.x
    const dy = e.changedTouches[0].clientY - touchStartRef.current.y
    const elapsed = Date.now() - touchStartTimeRef.current

    const absDx = Math.abs(dx)
    const absDy = Math.abs(dy)

    // Must be horizontal swipe, not vertical scroll
    if (absDx < 50 || absDx < absDy || elapsed > 500) {
      touchStartRef.current = null
      return
    }

    const { innerWidth } = window
    const touchX = e.changedTouches[0].clientX

    // Left 1/3 swipe right = prev chapter
    if (touchX < innerWidth / 3 && dx > 0) {
      goToPrev()
    }
    // Right 1/3 swipe left = next chapter
    else if (touchX > (innerWidth * 2) / 3 && dx < 0) {
      goToNext()
    }

    touchStartRef.current = null
  }, [goToPrev, goToNext])

  // Bookmark
  const handleBookmark = useCallback(async () => {
    if (savingBookmark) return
    setSavingBookmark(true)
    try {
      // TODO: Replace with actual bookmark API call
      // await saveBookmark({ bookId, chapterId, chapterNumber })
      await new Promise(r => setTimeout(r, 300))
      setBookmarked(b => !b)
      showToast(bookmarked ? '已取消书签' : '已添加书签')
    } catch {
      showToast('书签保存失败')
    } finally {
      setSavingBookmark(false)
    }
  }, [bookmarked, savingBookmark, showToast])

  // Jump to chapter from TOC
  const handleJumpToChapter = useCallback((chapter: ChapterInfo) => {
    if (chapter.chapter_number < chapterNumber) {
      // Navigate to previous chapters
      for (let i = 0; i < chapterNumber - chapter.chapter_number; i++) {
        onPrev?.()
      }
    } else {
      for (let i = 0; i < chapter.chapter_number - chapterNumber; i++) {
        onNext?.()
      }
    }
    setTocOpen(false)
    showToast(`跳转到: ${chapter.title}`)
  }, [chapterNumber, onPrev, onNext, showToast])

  // Settings change
  const handleSettingsChange = useCallback((partial: Partial<ReaderSettings>) => {
    setSettings(prev => ({ ...prev, ...partial }))
  }, [])

  // Cleanup toast timer
  useEffect(() => {
    return () => {
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current)
    }
  }, [])

  // Derived values
  const colors = THEME_COLORS[settings.theme]
  const paragraphSpacingRem = settings.paragraphSpacing * 1.25
  const wordCount = countWords(content)
  const readTime = estimateReadingTime(wordCount)
  const progress = totalChapters > 0 ? (chapterNumber / totalChapters) * 100 : 0

  const nightOverlay = settings.nightMode ? {
    filter: 'brightness(0.75) contrast(1.1)'
  } : {}

  const paragraphs = content.split(/\n+/).filter((p) => p.trim())

  return (
    <div
      className="relative"
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
      style={{
        ...nightOverlay,
        transition: 'filter 0.3s ease'
      }}
    >
      {/* Progress Bar */}
      <ProgressBar progress={progress} colors={colors} />

      {/* Top Control Bar */}
      <div
        className="sticky top-0 z-30 backdrop-blur-md border-b"
        style={{
          background: `${colors.bg}e6`,
          borderBottomColor: colors.border
        }}
      >
        <div className="max-w-3xl mx-auto px-4 py-2">
          <div className="flex items-center justify-between gap-2">
            {/* Left: Font controls */}
            <div className="flex items-center gap-1">
              <button
                onClick={() => handleSettingsChange({ fontSize: Math.max(14, settings.fontSize - 2) })}
                className="p-2 rounded-lg transition-colors"
                style={{ color: colors.textSecondary }}
                onMouseEnter={(e) => e.currentTarget.style.background = colors.hoverBg}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                title="减小字号 [-]"
              >
                <Minus size={16} />
              </button>
              <Type size={14} style={{ color: colors.textMuted }} />
              <span
                className="text-xs w-7 text-center tabular-nums"
                style={{ color: colors.textMuted }}
              >
                {settings.fontSize}
              </span>
              <button
                onClick={() => handleSettingsChange({ fontSize: Math.min(28, settings.fontSize + 2) })}
                className="p-2 rounded-lg transition-colors"
                style={{ color: colors.textSecondary }}
                onMouseEnter={(e) => e.currentTarget.style.background = colors.hoverBg}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                title="增大字号 [+]"
              >
                <Plus size={16} />
              </button>
            </div>

            {/* Center: Chapter info + read time */}
            <div className="flex items-center gap-3 text-xs" style={{ color: colors.textMuted }}>
              <span className="tabular-nums">
                {chapterNumber}<span className="opacity-50">/{totalChapters}</span>
              </span>
              <span className="flex items-center gap-1">
                <Clock size={12} />
                {readTime}
              </span>
            </div>

            {/* Right: Action buttons */}
            <div className="flex items-center gap-1">
              {/* Bookmark */}
              <button
                onClick={handleBookmark}
                disabled={savingBookmark}
                className="p-2 rounded-lg transition-colors"
                style={{ color: bookmarked ? colors.accent : colors.textSecondary }}
                onMouseEnter={(e) => e.currentTarget.style.background = colors.hoverBg}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                title="书签 [B]"
              >
                {bookmarked ? <BookmarkCheck size={16} /> : <Bookmark size={16} />}
              </button>

              {/* TOC */}
              <button
                onClick={() => setTocOpen(o => !o)}
                className="p-2 rounded-lg transition-colors"
                style={{ color: colors.textSecondary }}
                onMouseEnter={(e) => e.currentTarget.style.background = colors.hoverBg}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                title="目录 [T]"
              >
                <List size={16} />
              </button>

              {/* Settings */}
              <button
                onClick={() => setSettingsOpen(o => !o)}
                className="p-2 rounded-lg transition-colors"
                style={{ color: colors.textSecondary }}
                onMouseEnter={(e) => e.currentTarget.style.background = colors.hoverBg}
                onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                title="设置 [S]"
              >
                <Settings size={16} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Reading Content */}
      <div
        ref={contentRef}
        className="overflow-y-auto px-4 py-6"
        style={{
          maxHeight: 'calc(100vh - 160px)',
          scrollBehavior: 'smooth'
        }}
      >
        <article
          className="max-w-3xl mx-auto"
          style={{
            fontSize: `${settings.fontSize}px`,
            fontFamily: FONT_FAMILIES[settings.fontFamily].css,
            lineHeight: settings.lineHeight,
            color: colors.text,
            letterSpacing: '0.02em',
            textRendering: 'optimizeLegibility',
            WebkitFontSmoothing: 'antialiased'
          }}
        >
          {paragraphs.length === 0 ? (
            <div className="text-center py-20" style={{ color: colors.textMuted }}>
              <BookOpen size={48} className="mx-auto mb-4 opacity-30" />
              <p className="text-lg mb-2">章节内容为空</p>
              <p className="text-sm opacity-60">该章节暂无内容或文件读取失败</p>
              <p className="text-xs mt-4 opacity-40">调试信息: content长度={content.length}, wordCount={wordCount}</p>
            </div>
          ) : (
            paragraphs.map((p, i) => (
              <p
                key={i}
                className="mb-4 first-line:indent-8"
                style={{
                  marginBottom: `${paragraphSpacingRem}rem`,
                  textAlign: 'justify',
                  textIndent: '2em',
                  lineHeight: 'inherit'
                }}
              >
                {p.trim()}
              </p>
            ))
          )}
        </article>

        {/* Bottom Navigation */}
        <nav className="max-w-3xl mx-auto mt-10 pt-6" style={{ borderTop: `1px solid ${colors.border}` }}>
          <div className="flex items-center justify-between gap-3">
            <button
              onClick={goToPrev}
              disabled={!hasPrev}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed"
              style={{
                color: hasPrev ? colors.text : colors.textMuted,
                background: hasPrev ? `${colors.accent}12` : colors.progressBg
              }}
              onMouseEnter={(e) => {
                if (hasPrev) e.currentTarget.style.background = `${colors.accent}20`
              }}
              onMouseLeave={(e) => {
                if (hasPrev) e.currentTarget.style.background = `${colors.accent}12`
              }}
            >
              <ChevronLeft size={16} />
              {chapters.length > 0 && chapterNumber > 1 && chapters[chapterNumber - 2] ? (
                <span className="truncate max-w-[200px]">
                  {chapters[chapterNumber - 2].title}
                </span>
              ) : (
                '上一章'
              )}
            </button>

            <span
              className="text-xs hidden sm:block"
              style={{ color: colors.textMuted }}
            >
              ← → 键翻页 · T 目录 · S 设置 · B 书签
            </span>

            <button
              onClick={goToNext}
              disabled={!hasNext}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 disabled:opacity-30 disabled:cursor-not-allowed"
              style={{
                color: hasNext ? colors.text : colors.textMuted,
                background: hasNext ? `${colors.accent}12` : colors.progressBg
              }}
              onMouseEnter={(e) => {
                if (hasNext) e.currentTarget.style.background = `${colors.accent}20`
              }}
              onMouseLeave={(e) => {
                if (hasNext) e.currentTarget.style.background = `${colors.accent}12`
              }}
            >
              {chapters.length > 0 && chapterNumber < totalChapters && chapters[chapterNumber] ? (
                <span className="truncate max-w-[200px]">
                  {chapters[chapterNumber].title}
                </span>
              ) : (
                '下一章'
              )}
              <ChevronRight size={16} />
            </button>
          </div>
        </nav>
      </div>

      {/* Toast */}
      {toast && (
        <div
          className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-full text-sm font-medium shadow-lg"
          style={{
            background: colors.cardBg,
            color: colors.text,
            border: `1px solid ${colors.border}`,
            boxShadow: `0 4px 16px rgba(0,0,0,${colors.bg === '#ffffff' ? '0.12' : '0.3'})`,
            animation: 'fadeInUp 0.2s ease-out'
          }}
        >
          {toast}
        </div>
      )}

      {/* Drawers */}
      <TocDrawer
        open={tocOpen}
        onClose={() => setTocOpen(false)}
        chapters={chapters}
        currentChapter={chapterNumber}
        onJump={handleJumpToChapter}
        colors={colors}
      />
      <SettingsPanel
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        settings={settings}
        onChange={handleSettingsChange}
        colors={colors}
      />

      {/* Global Styles */}
      <style>{`
        @keyframes fadeInUp {
          from { opacity: 0; transform: translate(-50%, 12px); }
          to { opacity: 1; transform: translate(-50%, 0); }
        }
      `}</style>
    </div>
  )
}

// ============ Beacon Helper ============

function sendBeaconWithAuth(url: string, data: unknown) {
  const token = getAccessToken()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`
  fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify(data),
    keepalive: true,
    credentials: 'include',
  }).catch(() => {})
}
