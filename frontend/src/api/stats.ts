import { get } from '@/utils/http'
import { StatsData, ReadingStats } from '@/types'

export function fetchStats(days?: number) {
  return get<StatsData>('/stats/', { params: { days } })
}

export function fetchReadingStats(params?: { page?: number }) {
  return get<{ items: ReadingStats[]; total: number }>('/progress/', { params })
}
