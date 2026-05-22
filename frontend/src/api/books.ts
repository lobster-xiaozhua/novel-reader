import { get } from '@/utils/http'
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
