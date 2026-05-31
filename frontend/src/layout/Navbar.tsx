import { useState, useRef, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Bell, User, LogOut, Menu } from 'lucide-react'
import { useUserStore } from '@/stores/userStore'
import { useAppStore } from '@/stores/appStore'
import { fetchSearch } from '@/api/books'

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debounced
}

export default function Navbar() {
  const [searchQuery, setSearchQuery] = useState('')
  const [suggestionsOpen, setSuggestionsOpen] = useState(false)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()
  const { user, logout } = useUserStore()
  const { toggleSidebar } = useAppStore()
  const inputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const debounceQuery = useDebounce(searchQuery, 300)

  useEffect(() => {
    if (!debounceQuery || debounceQuery.length < 1) {
      setSuggestions([])
      setSuggestionsOpen(false)
      return
    }
    let cancelled = false
    setLoading(true)
    fetchSearch(debounceQuery)
      .then((data) => {
        if (!cancelled) {
          setSuggestions(data.suggestions || [])
          setSuggestionsOpen(true)
          setSelectedIndex(-1)
        }
      })
      .catch(() => {
        if (!cancelled) setSuggestions([])
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [debounceQuery])

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setSuggestionsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSearch = useCallback((query?: string) => {
    const q = (query ?? searchQuery).trim()
    if (!q) return
    setSuggestionsOpen(false)
    setSearchQuery('')
    navigate(`/search?q=${encodeURIComponent(q)}`)
  }, [searchQuery, navigate])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (!suggestionsOpen || suggestions.length === 0) {
      if (e.key === 'Enter') {
        e.preventDefault()
        handleSearch()
      }
      return
    }
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedIndex((prev) => (prev < suggestions.length - 1 ? prev + 1 : prev))
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex((prev) => (prev > 0 ? prev - 1 : -1))
        break
      case 'Enter':
        e.preventDefault()
        if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
          handleSearch(suggestions[selectedIndex])
        } else {
          handleSearch()
        }
        break
      case 'Escape':
        e.preventDefault()
        setSuggestionsOpen(false)
        break
    }
  }, [suggestionsOpen, suggestions, selectedIndex, handleSearch])

  return (
    <header className="h-16 bg-card-bg/80 backdrop-blur-xl border-b border-white/[0.06] flex items-center justify-between px-6 sticky top-0 z-30">
      <div className="flex items-center gap-4">
        <button
          onClick={toggleSidebar}
          className="p-2 rounded-lg hover:bg-white/5 text-text-secondary hover:text-text-primary transition-colors lg:hidden"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div className="relative" ref={dropdownRef}>
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
          <form onSubmit={(e) => { e.preventDefault(); handleSearch() }}>
            <input
              ref={inputRef}
              type="text"
              placeholder="搜索书籍、作者..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={() => { if (suggestions.length > 0) setSuggestionsOpen(true) }}
              className="w-64 lg:w-80 h-9 pl-9 pr-4 rounded-lg bg-white/5 border border-white/[0.06] text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-500/50 transition-colors"
            />
          </form>
          {suggestionsOpen && suggestions.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-bg-elevated border border-border rounded-lg shadow-lg overflow-hidden z-50">
              {loading && (
                <div className="px-3 py-2 text-xs text-text-muted">搜索中...</div>
              )}
              {suggestions.map((s, idx) => (
                <button
                  key={s}
                  onMouseDown={(e) => { e.preventDefault(); handleSearch(s) }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`w-full text-left px-3 py-2 text-sm flex items-center gap-2 transition-colors ${
                    idx === selectedIndex ? 'bg-accent/10 text-accent' : 'text-text-primary hover:bg-white/5'
                  }`}
                >
                  <Search className="w-3.5 h-3.5 text-text-muted flex-shrink-0" />
                  <span className="truncate">{s}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <button className="relative p-2 rounded-lg hover:bg-white/5 text-text-secondary hover:text-text-primary transition-colors">
          <Bell className="w-5 h-5" />
        </button>

        <div className="w-px h-6 bg-white/[0.06]" />

        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-primary-500/20 flex items-center justify-center">
            <User className="w-4 h-4 text-primary-500" />
          </div>
          <div className="hidden sm:block">
            <div className="text-sm font-medium text-text-primary">{user?.username || '访客'}</div>
            <div className="text-xs text-text-muted">{user?.is_staff ? '管理员' : '用户'}</div>
          </div>
          {user && (
            <button
              onClick={() => {
                logout()
                navigate('/login')
              }}
              className="p-2 rounded-lg hover:bg-white/5 text-text-secondary hover:text-danger transition-colors"
              title="退出登录"
            >
              <LogOut className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </header>
  )
}
