import { get, post, del } from '@/utils/http'
import { Book, Chapter, RecommendBook, AdvancedSearchResult } from '@/types'

export function fetchBooks(params?: { tag?: string; category?: string; search?: string; page?: number }) {
  return get<{ items: Book[]; total: number }>('/books/', { params })
}

export function fetchBook(id: number) {
  return get<Book>(`/books/${id}/`)
}

export function fetchChapters(bookId: number) {
  return get<Chapter[]>(`/books/${bookId}/chapters/`)
}

export function fetchChapterContent(bookId: number, chapterId: number) {
  return get<Chapter>(`/books/${bookId}/chapters/${chapterId}/`)
}

export function importBooks(files: File[]) {
  const formData = new FormData()
  files.forEach((f) => formData.append('files', f))
  return upload<{ success: boolean; imported: number; errors: string[]; total: number }>('/books/import/', formData)
}

export function fetchRankings() {
  return get<{
    hot_today: Book[]
    hot_week: Book[]
    new_arrivals: Book[]
  }>('/books/rankings/')
}

export function fetchCategories() {
  return get<{ name: string; count: number }[]>('/books/categories/')
}

export function fetchSearch(q: string) {
  return get<{
    query: string
    results: Array<{ id: number; title: string; author: string; category: string }>
    total: number
    suggestions: string[]
  }>('/search/', { params: { q } })
}

export function fetchRecommendations(strategy: string = 'hybrid', limit: number = 20, page: number = 1) {
  return get<{
    success: boolean
    data: RecommendBook[]
    pagination: { page: number; per_page: number; total: number; has_next: boolean }
  }>('/recommendations/', { params: { strategy, limit, page } })
}

export function fetchSimilarBooks(bookId: number, limit: number = 6) {
  return get<{
    success: boolean
    data: RecommendBook[]
  }>(`/books/${bookId}/similar/`, { params: { limit } })
}

export function fetchAdvancedSearch(q: string, limit: number = 20, page: number = 1) {
  return get<{
    success: boolean
    data: AdvancedSearchResult[]
    pagination: { page: number; per_page: number; total: number; has_next: boolean }
    search_time_ms: number
  }>('/search/advanced/', { params: { q, limit, page } })
}

// ── 书籍目录管理 ──

export interface BookDirInfo {
  path: string
  type: string
  exists: boolean
  accessible?: boolean
  books: { name: string; chapters: number }[]
  file_count: number
}

export function fetchBookDirs() {
  return get<{ success: boolean; dirs: BookDirInfo[] }>('/books/dirs/')
}

export function addBookDir(path: string) {
  return post<{ success: boolean; message?: string; error?: string; scan?: BookDirInfo }>('/books/dirs/', { path })
}

export function removeBookDir(path: string) {
  return del<{ success: boolean; message?: string; error?: string }>('/books/dirs/', { path })
}

export function scanBookDirs(path?: string) {
  return post<{ success: boolean; imported: number; errors: string[] }>('/books/dirs/scan/', { path })
}
