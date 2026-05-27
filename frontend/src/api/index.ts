import { get, post, del, upload } from '@/utils/http'
import type { Book, Chapter, CrawlerTask, FavoriteItem, ProgressItem, StatsData, DashboardStats, TagItem, UserItem } from '@/types'

export const bookApi = {
  list: (params?: { tag?: string; category?: string; search?: string; page?: number }) =>
    get<{ items: Book[]; total: number }>('/books/', { params }),
  detail: (id: number) => get<Book>(`/books/${id}/`),
  chapters: (bookId: number) => get<Chapter[]>(`/books/${bookId}/chapters/`),
  chapterContent: (bookId: number, chapterId: number) => get<Chapter>(`/books/${bookId}/chapters/${chapterId}/`),
  importBooks: (files: File[]) => {
    const formData = new FormData()
    files.forEach((f) => formData.append('files', f))
    return upload<{ success: boolean; imported: number; errors: string[]; total: number }>('/books/import/', formData)
  },
}

export const crawlerApi = {
  list: (params?: { page?: number }) => get<{ items: CrawlerTask[]; total: number }>('/crawler/', { params }),
  create: (url: string) => post<CrawlerTask>('/crawler/', { url }),
  detail: (id: number) => get<CrawlerTask>(`/crawler/${id}/`),
}

export const favoriteApi = {
  list: () => get<{ items: FavoriteItem[]; total: number }>('/favorites/'),
  toggle: (bookId: number) => post<{ message: string }>('/favorites/toggle/', { book_id: bookId }),
}

export const progressApi = {
  list: () => get<{ items: ProgressItem[]; total: number }>('/progress/'),
  save: (data: { book_id: number; chapter_id?: number; position: number }) => post<ProgressItem>('/progress/', data),
  trackStats: (data: { seconds: number; chapter_id?: number }) => post<{ message: string }>('/progress/track-stats/', data),
}

export const statsApi = {
  user: (days?: number) => get<StatsData>('/stats/', { params: { days } }),
  dashboard: () => get<DashboardStats>('/dashboard/'),
}

export const tagApi = {
  list: () => get<{ items: TagItem[]; total: number }>('/tags/'),
  create: (data: { name: string; color: string }) => post<TagItem>('/tags/', data),
  delete: (id: number) => del<void>(`/tags/${id}/`),
}

export const userApi = {
  list: () => get<{ items: UserItem[]; total: number }>('/users/'),
}
