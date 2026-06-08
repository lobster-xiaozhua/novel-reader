'use client';

import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Flame, TrendingUp, Sparkles, ChevronRight, BookOpen, Search } from 'lucide-react';
import { api } from '@/shared/lib/api';
import { SkeletonHome } from '@/shared/components/Skeleton';
import type { ApiResponse, DiscoverFeed, RankingBook } from '@/shared/types';

function BookCard({ book, rank }: { book: RankingBook; rank?: number }) {
  const router = useRouter();
  return (
    <button
      className="glass-card block text-left w-full no-underline hover:shadow-md transition-all duration-300 group"
      onClick={() => router.push(`/book/${book.id}`)}
    >
      <div className="relative">
        <div
          className="w-full aspect-[3/4] rounded-xl mb-4 flex items-center justify-center text-white text-4xl font-bold group-hover:scale-105 transition-transform duration-300 shadow-lg"
          style={{ background: `linear-gradient(135deg, ${book.gradient?.[0] || '#7c3aed'}, ${book.gradient?.[1] || '#a855f7'})` }}
        >
          {book.title.charAt(0)}
        </div>
        {rank !== undefined && rank < 3 && (
          <div
            className={`absolute top-3 left-3 w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold shadow-lg ${
              rank === 0 ? 'bg-gradient-to-br from-red-400 to-red-600' : rank === 1 ? 'bg-gradient-to-br from-amber-400 to-amber-600' : 'bg-gradient-to-br from-blue-400 to-blue-600'
            }`}
          >
            {rank + 1}
          </div>
        )}
      </div>
      <h3 className="text-base font-bold truncate">{book.title}</h3>
      <p className="text-sm mt-1 truncate text-[var(--text-secondary)]">{book.author}</p>
      <div className="flex gap-1.5 mt-3 flex-wrap">
        {book.tags?.slice(0, 2).map((t) => (
          <span key={t.id} className="tag text-xs">
            {t.name}
          </span>
        ))}
      </div>
    </button>
  );
}

function RankingRow({ rank, book }: { rank: number; book: RankingBook }) {
  const router = useRouter();
  const rankColors = ['bg-gradient-to-br from-red-400 to-red-600', 'bg-gradient-to-br from-amber-400 to-amber-600', 'bg-gradient-to-br from-blue-400 to-blue-600'];
  const isTop3 = rank < 3;
  return (
    <button
      className="w-full flex items-center gap-4 p-4 rounded-xl hover:bg-[var(--bg-secondary)] transition-all duration-200 text-left group"
      onClick={() => router.push(`/book/${book.id}`)}
    >
      <span
        className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0 shadow-md ${
          isTop3 ? rankColors[rank] + ' text-white' : 'bg-[var(--bg-secondary)] text-[var(--text-muted)]'
        }`}
      >
        {rank + 1}
      </span>
      <div className="flex-1 min-w-0">
        <h4 className="text-base font-semibold truncate group-hover:text-[var(--accent)] transition-colors">{book.title}</h4>
        <p className="text-sm text-[var(--text-secondary)] mt-0.5">
          {book.author} · {book.chapter_count}章
        </p>
      </div>
      <ChevronRight size={20} className="text-[var(--text-muted)] opacity-70 group-hover:text-[var(--accent)] group-hover:opacity-100 transition-all" />
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
    <div className="text-center py-12 text-[var(--danger)]">
      <p className="text-lg">加载失败，请稍后重试</p>
      <button className="btn-primary mt-6" onClick={() => window.location.reload()}>
        重新加载
      </button>
    </div>
  );

  const feed = data?.data;
  if (!feed) return null;

  const categories = ['玄幻', '都市', '仙侠', '历史', '科幻', '游戏', '言情', '悬疑'];

  return (
    <div className="space-y-10">
      {/* Hero Search Bar */}
      <section className="glass-card p-8 text-center">
        <div className="max-w-2xl mx-auto">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-[var(--accent)] to-[var(--accent2)] flex items-center justify-center shadow-lg">
              <BookOpen size={24} className="text-white" />
            </div>
            <h1 className="text-3xl font-extrabold bg-gradient-to-r from-[var(--accent)] to-[var(--accent2)] bg-clip-text text-transparent">
              发现好书
            </h1>
          </div>
          <p className="text-base text-[var(--text-secondary)] mb-6">
            百万小说，一键搜索，拼音首字母也能搜
          </p>
          <button
            className="btn-primary px-8 py-3 text-base mx-auto flex items-center gap-2"
            onClick={() => router.push('/search')}
          >
            <Search size={18} />
            去搜索
          </button>
        </div>
      </section>

      {/* Categories */}
      <section>
        <div className="section-heading">
          <Sparkles size={20} className="text-[var(--accent)]" />
          <h2>分类浏览</h2>
        </div>
        <div className="flex flex-wrap gap-3">
          {categories.map((cat) => (
            <button
              key={cat}
              className="glass-card text-sm px-5 py-3 no-underline hover:shadow-md transition-all font-medium"
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
          <div className="section-heading justify-between">
            <div className="flex items-center gap-2">
              <Flame size={20} className="text-red-500" />
              <h2>今日热门</h2>
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
          <div className="section-heading">
            <TrendingUp size={20} className="text-[var(--accent)]" />
            <h2>新书推荐</h2>
          </div>
          <div className="grid gap-5" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))' }}>
            {feed.new_arrivals.slice(0, 8).map((b, i) => (
              <BookCard key={b.id} book={b} rank={i} />
            ))}
          </div>
        </section>
      )}

      {/* Hot Week */}
      {feed.hot_week?.length > 0 && (
        <section>
          <div className="section-heading">
            <TrendingUp size={20} className="text-amber-500" />
            <h2>本周热门</h2>
          </div>
          <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))' }}>
            {feed.hot_week.slice(0, 6).map((b) => (
              <RankingRow key={b.id} rank={99} book={b} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}