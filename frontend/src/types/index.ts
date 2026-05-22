export interface Book {
  id: number
  title: string
  author: string
  category: string
  description: string
  total_chapters: number
  chapter_count: number
  tags: Tag[]
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

export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}
