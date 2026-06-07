// ──── Generic ────
export interface ApiResponse<T = unknown> {
  success: boolean;
  data: T;
  message?: string;
}

export interface PaginatedData<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  has_next: boolean;
}

// ──── Reader ────
export interface Book {
  id: number;
  title: string;
  author: string;
  description: string;
  category: string;
  tags: string[];
  cover_gradient?: [string, string];
  chapter_count?: number;
  created_at?: string;
  updated_at?: string;
}

export interface TagItem {
  id: number;
  name: string;
}

export interface BookDetail {
  id: number;
  title: string;
  author: string;
  category: string;
  description: string;
  tags: TagItem[];
  total_chapters: number;
  gradient?: [string, string];
  is_favorited: boolean;
  reading_progress?: {
    chapter_id: number;
    chapter?: {
      chapter_number: number;
    };
  };
}

export interface ChapterItem {
  id: number;
  title: string;
  chapter_number: number;
  word_count: number;
}

export interface ChapterContent {
  id: number;
  title: string;
  content: string;
  chapter_number: number;
  word_count: number;
}

export interface RankingBook {
  id: number;
  title: string;
  author: string;
  chapter_count: number;
  gradient?: [string, string];
  tags: TagItem[];
}

export interface DiscoverFeed {
  hot_today: RankingBook[];
  new_arrivals: RankingBook[];
  hot_week: RankingBook[];
}

export interface ShelfItem {
  book_id: number;
  title: string;
  author: string;
}

export interface ShelfData {
  items: ShelfItem[];
  total: number;
}

export interface UserStats {
  total_books: number;
  favorite_count: number;
  week_chapters: number;
  today_minutes: number;
  chart: { date: string; minutes: number }[];
}

export interface AuthResponse {
  data: {
    tokens: {
      access_token: string;
      refresh_token: string;
    };
  };
}

export interface ReadingProgress {
  book?: {
    id: number;
    title: string;
  };
  chapter?: {
    id: number;
    chapter_number: number;
    title: string;
  };
}

// ──── Admin ────
export interface AdminBook {
  id: number;
  title: string;
  author: string;
  category: string;
  chapter_count: number;
  total_chapters: number;
  created_at: string;
  updated_at: string;
}

export interface CrawlerTask {
  id: number;
  name: string;
  url: string;
  status: string;
  progress: number;
  downloaded_chapters: number;
  total_chapters: number;
  created_at: string;
  updated_at?: string;
}

export interface PerfMetrics {
  cpu: number;
  memory: number;
  uptime: number;
  avg_response_time: number;
  requests: number;
}

export interface HealthStatus {
  status: string;
  version: string;
  timestamp: string;
  database: string;
  cache: string;
}

export interface TagWithCount {
  id: number;
  name: string;
  color: string;
  book_count: number;
}

export interface AdminUser {
  id: number;
  username: string;
  email: string;
  is_staff: boolean;
  created_at: string;
}