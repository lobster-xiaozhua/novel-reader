export interface Book {
  id: number
  title: string
  author: string
  category: string
  description: string
  total_chapters: number
  chapter_count: number
  tags: Tag[]
  gradient: [string, string]
  is_favorited: boolean
  reading_progress: { chapter_id: number; position: number } | null
  created_at: string
  updated_at: string
}

export interface Tag {
  id: number
  name: string
  color: string
}

export interface Chapter {
  id: number
  chapter_number: number
  title: string
  word_count: number
  content?: string
}

export interface CrawlerTask {
  id: number
  url: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  total_chapters: number
  downloaded_chapters: number
  error_message: string
  logs?: unknown[]
  created_at: string
  updated_at: string
}

export interface ReadingStats {
  id: number
  date: string
  read_seconds: number
  chapters_read: number
  words_read: number
}

export interface User {
  id: number
  username: string
  email: string
  is_staff: boolean
}

export interface FavoriteItem {
  id: number
  book_id: number
  title: string
  author: string
  category: string
  total_chapters: number
  created_at: string
}

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

export interface TagItem {
  id: number
  name: string
  color: string
  book_count: number
}

export interface UserItem {
  id: number
  username: string
  email: string
  is_staff: boolean
  date_joined: string
  last_login?: string
  book_count: number
}

export interface MenuItem {
  title: string
  icon: string
  path: string
  children?: MenuItem[]
}

export interface TagView {
  path: string
  title: string
  name: string
}

export interface CategoryStat {
  category: string
  count: number
}

export interface DashboardStats {
  total_books: number
  total_users: number
  total_chapters: number
  total_words: number
  category_stats: CategoryStat[]
}

export interface RecommendBook {
  id: number
  title: string
  author: string
  category: string
  description: string
  tags: Tag[]
  gradient: [string, string]
  chapter_count: number
  reason: string
  score: number
  is_new: boolean
  updated_at: string
  created_at: string
}

export interface AdvancedSearchResult {
  id: number
  book_id: number
  title: string
  author: string
  category: string
  description: string
  tags: string[]
  total_score: number
  matched_chapters: Array<{
    id: number
    title: string
    score: number
    content_preview: string
    chapter_number: number
    total_occurrences: number
  }>
  total_matches: number
  match_reasons: string[]
}
