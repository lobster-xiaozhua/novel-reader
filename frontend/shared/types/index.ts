// ──── Auth ────

export interface User {
  id: number;
  username: string;
  email: string;
  role?: string;
  is_staff: boolean;
}

export interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type?: string;
}

export interface AuthResponse {
  success: boolean;
  user?: User;
  error?: string;
  access_token?: string;
  refresh_token?: string;
}

export interface LoginInput {
  username: string;
  password: string;
}

export interface RegisterInput {
  username: string;
  password: string;
  email?: string;
}

// ──── Api ────

export interface ApiMeta {
  page: number;
  total_pages: number;
  total_items: number;
}

export interface ApiResponse<T = unknown> {
  success: boolean;
  data: T | null;
  meta?: ApiMeta;
  error?: string;
}

export interface PaginatedData<T = unknown> {
  items: T[];
  total: number;
}

// ──── Tags ────

export interface Tag {
  id: number;
  name: string;
  color?: string;
}

export interface TagWithCount extends Tag {
  book_count: number;
}

// ──── Books ────

export interface BookListItem {
  id: number;
  title: string;
  author: string;
  category: string;
  description: string;
  total_chapters: number;
  chapter_count: number;
  tags: Tag[];
  gradient: [string, string];
  created_at: string;
  updated_at: string;
}

export interface BookDetail {
  id: number;
  title: string;
  author: string;
  category: string;
  description: string;
  total_chapters: number;
  tags: Tag[];
  gradient: [string, string];
  is_favorited: boolean;
  reading_progress: ReadingProgress | null;
  created_at: string;
  updated_at: string;
}

export interface ChapterItem {
  id: number;
  chapter_number: number;
  title: string;
  word_count: number;
}

export interface ChapterContent {
  id: number;
  chapter_number: number;
  title: string;
  word_count: number;
  content: string;
}

// ──── Progress ────

export interface ReadingProgress {
  id: number;
  book_id: number;
  book_title: string;
  book_author: string;
  chapter_id: number | null;
  chapter_title: string | null;
  position: number;
  total_chapters: number;
  updated_at: string;
}

// ──── Shelf / Favorites ────

export interface ShelfItem {
  id: number;
  book_id: number;
  title: string;
  author: string;
  category: string;
  total_chapters: number;
  created_at: string;
}

export interface ShelfData {
  items: ShelfItem[];
  total: number;
}

// ──── Discover ────

export interface DiscoverFeed {
  hot_today: RankingBook[];
  hot_week: RankingBook[];
  new_arrivals: RankingBook[];
}

export interface RankingBook {
  id: number;
  title: string;
  author: string;
  category: string;
  gradient: [string, string];
  tags: Tag[];
  chapter_count: number;
}

// ──── Stats ────

export interface DailyStat {
  date: string;
  minutes: number;
  chapters: number;
  words: number;
}

export interface UserStats {
  total_books: number;
  reading_count: number;
  favorite_count: number;
  today_chapters: number;
  today_minutes: number;
  week_chapters: number;
  total_words: number;
  chart: DailyStat[];
}

// ──── Crawler ────

export interface CrawlerTask {
  id: number;
  url: string;
  status: string;
  total_chapters: number;
  downloaded_chapters: number;
  error_message: string;
  logs?: string[];
  created_at: string;
  updated_at: string;
}

// ──── Admin ────

export interface AdminBook {
  id: number;
  title: string;
  author: string;
  category: string;
  total_chapters: number;
  created_at: string;
}

export interface AdminUser {
  id: number;
  username: string;
  email: string;
  is_staff: boolean;
  date_joined: string;
  last_login: string | null;
  book_count: number;
}

// ──── Health ────

export interface HealthStatus {
  status: string;
  database: string;
  cache: string;
  disk_usage: string;
  version: string;
}

export interface PerfMetrics {
  cpu: number;
  memory: number;
  uptime: number;
  requests: number;
  avg_response_time: number;
}