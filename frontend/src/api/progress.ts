import { get, post } from '@/utils/http'

export interface ProgressItem {
  id: number
  book_id: number
  book_title: string
  book_author: string
  chapter_id?: number
  chapter_title?: string
  position: number
  total_chapters: number
  updated_at: string
}

export function fetchProgress() {
  return get<{ items: ProgressItem[]; total: number }>('/progress/')
}

export function saveProgress(data: { book_id: number; chapter_id?: number; position: number }) {
  return post<ProgressItem>('/progress/', data)
}
