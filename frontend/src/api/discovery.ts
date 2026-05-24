import { get } from '@/utils/http'

export interface DiscoveryBook {
  id: number
  title: string
  author: string
  category: string
  description: string
  total_chapters: number
  tags: { id: number; name: string; color: string }[]
  gradient: [string, string]
  updated_at: string
}

export interface CategoryDiscovery {
  category: string
  count: number
  books: DiscoveryBook[]
}

export interface DiscoveryData {
  hot_books: DiscoveryBook[]
  recent_books: DiscoveryBook[]
  categories: CategoryDiscovery[]
  stats: {
    total_books: number
    total_chapters: number
    total_words: number
    total_users: number
  }
}

export function fetchDiscovery(): Promise<DiscoveryData> {
  return get('/discovery/')
}
