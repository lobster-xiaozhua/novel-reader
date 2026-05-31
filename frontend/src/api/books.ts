import { get, upload } from '@/utils/http'
import { Book, Chapter } from '@/types'

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
