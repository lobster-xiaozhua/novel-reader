import { get, post } from '@/utils/http'
import { FavoriteItem } from '@/types'

export function fetchFavorites() {
  return get<{ items: FavoriteItem[]; total: number }>('/favorites/')
}

export function toggleFavorite(bookId: number) {
  return post<{ message: string }>('/favorites/toggle/', { book_id: bookId })
}
