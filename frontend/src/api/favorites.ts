import { get, post } from '@/utils/http'

export interface FavoriteItem {
  id: number
  book_id: number
  title: string
  author: string
  category: string
  total_chapters: number
  created_at: string
}

export function fetchFavorites() {
  return get<{ items: FavoriteItem[]; total: number }>('/favorites/')
}

export function toggleFavorite(bookId: number) {
  return post<{ success: boolean }>('/favorites/toggle/', { book_id: bookId })
}
