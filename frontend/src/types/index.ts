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
