import { get, post } from '@/utils/http'
import { ProgressItem } from '@/types'

export function fetchProgress() {
  return get<{ items: ProgressItem[]; total: number }>('/progress/')
}

export function saveProgress(data: { book_id: number; chapter_id?: number; position: number }) {
  return post<ProgressItem>('/progress/', data)
}

export function trackStats(data: { seconds: number; chapter_id?: number }) {
  return post<{ message: string }>('/progress/track-stats/', data)
}
