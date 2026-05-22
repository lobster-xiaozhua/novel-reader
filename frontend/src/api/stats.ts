import { get } from '@/utils/http'
import { ReadingStats } from '@/types'

export interface StatsData {
  total_books: number
  reading_count: number
  favorite_count: number
  today_chapters: number
  today_minutes: number
  week_chapters: number
  total_words: number
  chart: Array<{
    date: string
    minutes: number
    chapters: number
    words: number
  }>
}

export function fetchStats(days?: number) {
  return get<StatsData>('/stats/', { params: { days } })
}

export function fetchReadingStats(params?: { page?: number }) {
  return get<{ items: ReadingStats[]; total: number }>('/progress/', { params })
}
