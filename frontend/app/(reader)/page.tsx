'use client';

import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Fire, TrendingUp, Sparkles, ChevronRight, BookOpen } from 'lucide-react';
import { api } from '@/shared/lib/api';
import { SkeletonHome } from '@/shared/components/Skeleton';
import type { ApiResponse, DiscoverFeed, RankingBook } from '@/shared/types';

function BookCard({ book, rank }: { book: RankingBook; rank?: number }) {
  const router = useRouter();
  return (
    <button
      className="glass-card block text-left w-full no-underline hover:shadow-md transition-all duration-200 group"
      onClick={() => router.push(`/book/${book.id}`)}
    >
      <div className="relative">
        <div
          className="w-full aspect-[3/4] rounded-lg mb-3 flex items-center justify-center text-white text-3xl font-bold group-hover:scale-105 transition-transform duration-300"
          style={{ background: `linear-gradient(135deg, ${book.gradient?.[0] || '#667eea'}, ${book.gradient?.[1] || '#764ba2'})` }}
        >
          {book.title.charAt(0)}
        </div>
        {rank !== undefined && rank < 3 && (
          <div
            className={`absolute top-2 left-2 w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold ${
              rank === 0 ? 'bg-red-500' : rank === 1 ? 'bg-amber-500' : 'bg-blue-500'
            }`}
          >
            {rank + 1}
          </div>
        )}
      </div>
      <h3 className="text-sm font-semibold truncate">{book.title}</h3>
      <p className="text-xs mt-1 truncate text-[var(--text-muted)]">{book.author}</p>
      <div className="flex gap-1 mt-2 flex-wrap">
        {book.tags?.slice(0, 2).map((t) => (
          <span key={t.id} className="tag text-[0.65rem]">
            {t.name}
          </span>
        ))}
      </div>
    </button>
  );
}

function RankingRow({ rank, book }: { rank: number; book: RankingBook }) {
  const router = useRouter();
  const rankColors = ['bg-red-500', 'bg-amber-500', 'bg-blue-500'];
  const isTop3 = rank < 3;
  return (
    <button
      className="w-full flex items-center gap-3 p-3 rounded-lg hover:bg-[var(--bg-secondary)] transition-colors text-left"
      onClick={() => router.push(`/book/${book.id}`)}
    >
      <span
        className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
          isTop3 ? rankColors[rank] + ' text-white' : 'bg-[var(--bg-secondary)] text-[var(--text-muted)]'
        }`}
      >
        {rank + 1}
      </span>
      <div className="flex-1 min-w-0">
        <h4 className="text-sm font-medium truncate">{book.title}</h4>
        <p className="text-xs text-[var(--text-muted)]">
          {book.author} · {book.chapter_count}章
        </p>
      </div>
      <ChevronRight size={16} className="text-[var(--text-muted)] opacity-50" />
    </button>
  );
}

export default function DiscoverPage() {
  const router = useRouter();
  const { data, isLoading, error } = useQuery({
    queryKey: ['discover'],
    queryFn: () => api.get<ApiResponse<DiscoverFeed>>('/reader/discover'),
  });

  if (isLoading) return <SkeletonHome />;

  if (error) return (
    <div className="text-center py-10 text-[var(--danger)]">
      <p>加载失败，请稍后重试</p>
      <button className="btn-primary mt-4" onClick={() => window.location.reload()}>
        重新加载
      </button>
    </div>
  );

  const feed = data?.data;
  if (!feed) return null;

  const categories = ['玄幻', '都市', '仙侠', '历史', '科幻', '游戏', '言情', '悬疑'];

  return (
    <div className="space-y-8">
      {/* Hero Search Bar */}
      <section className="glass-card p-6 text-center">
        <h1 className="text-2xl font-bold mb-2">发现好书</h1>
        <p className="text-sm mb-4 text-[var(--text-muted)]">
          百万小说，一键搜索，拼音首字母也能搜
        </p>
        <button
          className="btn-primary px-6 py-2.5 mx-auto"
          onClick={() => router.push('/search')}
        >
          去搜索
        </button>
      </section>

      {/* Categories */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <Sparkles size={18} className="text-[var(--accent)]" />
          <h2 className="text-base font-semibold">分类浏览</h2>
        </div>
        <div className="flex flex-wrap gap-2">
          {categories.map((cat) => (
            <button
              key={cat}
              className="glass-card text-sm px-4 py-2 no-underline hover:shadow-md transition-all"
              onClick={() => router.push(`/search?q=${encodeURIComponent(cat)}`)}
            >
              {cat}
            </button>
          ))}
        </div>
      </section>

      {/* Hot Today */}
      {feed.hot_today?.length > 0 && (
        <section>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Fire size={18} className="text-red-500" />
              <h2 className="text-base font-semibold">今日热门</h2>
            </div>
          </div>
          <div className="glass-card p-2">
            {feed.hot_today.slice(0, 10).map((b, i) => (
              <RankingRow key={b.id} rank={i} book={b} />
            ))}
          </div>
        </section>
      )}

      {/* New Arrivals */}
      {feed.new_arrivals?.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp size={18} className="text-[var(--accent)]" />
            <h2 className="text-base font-semibold">新书推荐</h2>
          </div>
          <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))' }}>
            {feed.new_arrivals.slice(0, 8).map((b, i) => (
              <BookCard key={b.id} book={b} rank={i} />
            ))}
          </div>
        </section>
      )}

      {/* Hot Week */}
      {feed.hot_week?.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp size={18} className="text-amber-500" />
            <h2 className="text-base font-semibold">本周热门</h2>
          </div>
          <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}>
            {feed.hot_week.slice(0, 6).map((b) => (
              <RankingRow key={b.id} rank={99} book={b} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}