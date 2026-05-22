import { get, post } from '@/utils/http'
import { CrawlerTask } from '@/types'

export function fetchCrawlerTasks(params?: { page?: number }) {
  return get<{ items: CrawlerTask[]; total: number }>('/crawler/', { params })
}

export function createCrawlerTask(url: string) {
  return post<CrawlerTask>('/crawler/', { url })
}

export function fetchCrawlerTask(id: number) {
  return get<CrawlerTask>(`/crawler/${id}/`)
}
