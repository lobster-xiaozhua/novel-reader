import { useEffect, useCallback, useState } from 'react'
import { Minus, Plus, Type } from 'lucide-react'

interface NovelReaderProps {
  content: string
  onPrev?: () => void
  onNext?: () => void
  hasPrev?: boolean
  hasNext?: boolean
}

export default function NovelReader({ content, onPrev, onNext, hasPrev, hasNext }: NovelReaderProps) {
  const [fontSize, setFontSize] = useState(18)

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'ArrowLeft' && hasPrev) onPrev?.()
    if (e.key === 'ArrowRight' && hasNext) onNext?.()
  }, [hasPrev, hasNext, onPrev, onNext])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  const paragraphs = content.split(/\n+/).filter((p) => p.trim())

  return (
    <div className="relative">
      <div className="flex items-center justify-center gap-2 mb-6 sticky top-0 z-10 bg-card-bg/90 backdrop-blur-sm py-2 -mt-2">
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
      </div>

      <div className="max-w-3xl mx-auto" style={{ fontSize: `${fontSize}px`, lineHeight: 1.8 }}>
        {paragraphs.map((p, i) => (
          <p key={i} className="text-text-secondary mb-4 indent-8">{p.trim()}</p>
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
