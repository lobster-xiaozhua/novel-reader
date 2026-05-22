import { get } from '@/utils/http'
import { StatsData, DashboardStats } from '@/types'

export function fetchStats(days?: number) {
  return get<StatsData>('/stats/', { params: { days } })
}

export function fetchDashboard() {
  return get<DashboardStats>('/dashboard/')
}
