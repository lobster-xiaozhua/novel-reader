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
